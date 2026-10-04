from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.common.utils import normalize_name, slugify
from aptum.core.exceptions import AptumError, ConflictError, NotFoundError
from aptum.core.permissions import Actor
from aptum.modules.audit.service import AuditService, diff, snapshot
from aptum.modules.companies.models import Company, Industry
from aptum.modules.companies.policy import can_edit_company, check_edit_company
from aptum.modules.companies.repository import CompanyRepository
from aptum.modules.companies.schemas import CompanyCreate, CompanyRead, CompanyUpdate
from aptum.modules.users.models import User

# Snapshot stored in the audit log when a company disappears (merge, delete).
COMPANY_FIELDS = (
    "name",
    "normalized_name",
    "industry_id",
    "city",
    "country_code",
    "website",
    "logo_url",
    "is_consultancy",
    "created_by_user_id",
)


class CompanyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CompanyRepository(db)
        self.audit = AuditService(db)

    def get_or_create(self, user_id: int, data: CompanyCreate) -> Company:
        normalized = normalize_name(data.name)
        existing = self.repository.get_by_normalized_name(normalized)
        if existing is not None:
            return existing
        if data.industry_id is not None and self.repository.get_industry(data.industry_id) is None:
            raise NotFoundError("Industry not found")
        return self.repository.create(
            **data.model_dump(),
            normalized_name=normalized,
            created_by_user_id=user_id,
        )

    def update(self, user: User, company_id: int, data: CompanyUpdate) -> Company:
        """See policy.check_edit_company for who may edit."""
        company = self.repository.get(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        check_edit_company(user, company, self.repository.is_used_by_experiences(company.id))
        fields = data.model_dump(exclude_unset=True)
        for required in ("name", "is_consultancy"):
            if required in fields and fields[required] is None:
                raise ConflictError(f"{required} cannot be null")
        if fields.get("industry_id") is not None and (
            self.repository.get_industry(fields["industry_id"]) is None
        ):
            raise NotFoundError("Industry not found")
        changes = diff(snapshot(company, fields), fields)
        if "name" in fields:
            normalized = normalize_name(fields["name"])
            clash = self.repository.get_by_normalized_name(normalized)
            if clash is not None and clash.id != company.id:
                raise ConflictError("A company with that name already exists")
            fields["normalized_name"] = normalized
        if changes:
            self.audit.record(user.id, AuditAction.company_update, AuditEntity.company, company.id, changes)
        return self.repository.update(company, **fields)

    def merge(self, actor: Actor, source_id: int, target_id: int) -> Company:
        """Fold a duplicate into `target`: repoint experiences, then delete the duplicate, in one
        transaction (`company:merge`, checked by the router)."""
        if source_id == target_id:
            raise ConflictError("Cannot merge a company into itself")
        locked = self.repository.lock_pair(source_id, target_id)
        source, target = locked.get(source_id), locked.get(target_id)
        if source is None or target is None:
            self.db.rollback()
            raise NotFoundError("Company not found")
        moved = self.repository.repoint_experiences(source.id, target.id)
        self.audit.record(
            actor.id,
            AuditAction.company_merge,
            AuditEntity.company,
            source.id,
            {"merged_into": target.id, "experiences": moved, "deleted": snapshot(source, COMPANY_FIELDS)},
        )
        self.repository.delete(source)
        self.db.commit()
        self.db.refresh(target)
        return target

    def delete(self, actor: Actor, company_id: int) -> None:
        """Delete a company no experience uses (`company:delete`, checked by the router)."""
        company = self.repository.get(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        if self.repository.is_used_by_experiences(company.id):
            raise ConflictError("Company is in use by experiences; merge it instead")
        self.audit.record(
            actor.id,
            AuditAction.company_delete,
            AuditEntity.company,
            company.id,
            {"deleted": snapshot(company, COMPANY_FIELDS)},
        )
        self.repository.delete(company)
        try:
            self.db.commit()
        except IntegrityError as exc:  # an experience started using it meanwhile (FK RESTRICT)
            self.db.rollback()
            raise ConflictError("Company is in use by experiences; merge it instead") from exc

    def search(self, query: str, limit: int = 20) -> list[Company]:
        return self.repository.search(normalize_name(query), limit)

    def to_read(self, user: User, companies: list[Company]) -> list[CompanyRead]:
        """API view with `can_edit` for this caller. "In use" is fetched in one query for all."""
        used = self.repository.used_ids([company.id for company in companies])
        return [
            CompanyRead.model_validate(company).model_copy(
                update={"can_edit": can_edit_company(user, company, company.id in used)}
            )
            for company in companies
        ]

    def get(self, company_id: int) -> Company:
        company = self.repository.get(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company

    def list_industries(self) -> list[Industry]:
        return self.repository.list_industries()

    def _check_industry_name(self, name: str, industry_id: int | None) -> tuple[str, str]:
        """Clean name and slug, or 409 when another industry has the same normalized name or slug.
        The catalog is small, so it is compared in memory with the same normalization as companies."""
        name = name.strip()
        slug = slugify(name)
        if not slug:
            raise AptumError("Industry name must contain letters or numbers")
        for other in self.repository.list_industries():
            if other.id != industry_id and (
                normalize_name(other.name) == normalize_name(name) or other.slug == slug
            ):
                raise ConflictError("An industry with that name already exists")
        return name, slug

    def create_industry(self, actor: Actor, name: str) -> Industry:
        """`industry:manage`, checked by the router."""
        name, slug = self._check_industry_name(name, None)
        industry = self.repository.create_industry(name, slug)
        self.audit.record(
            actor.id,
            AuditAction.industry_create,
            AuditEntity.industry,
            industry.id,
            {"name": {"before": None, "after": name}, "slug": {"before": None, "after": slug}},
        )
        return self._commit_industry(industry)

    def rename_industry(self, actor: Actor, industry_id: int, name: str) -> Industry:
        """`industry:manage`, checked by the router. The slug follows the name."""
        industry = self.repository.get_industry(industry_id)
        if industry is None:
            raise NotFoundError("Industry not found")
        name, slug = self._check_industry_name(name, industry.id)
        fields = {"name": name, "slug": slug}
        changes = diff(snapshot(industry, fields), fields)
        if not changes:
            return industry
        self.audit.record(actor.id, AuditAction.industry_update, AuditEntity.industry, industry.id, changes)
        for key, value in fields.items():
            setattr(industry, key, value)
        return self._commit_industry(industry)

    def _commit_industry(self, industry: Industry) -> Industry:
        try:
            self.db.commit()
        except IntegrityError as exc:  # concurrent create/rename to the same name
            self.db.rollback()
            raise ConflictError("An industry with that name already exists") from exc
        self.db.refresh(industry)
        return industry
