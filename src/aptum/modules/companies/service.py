from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.common.utils import normalize_name
from aptum.core.exceptions import ConflictError, NotFoundError
from aptum.modules.audit.service import AuditService, diff, snapshot
from aptum.modules.companies.models import Company, Industry
from aptum.modules.companies.policy import can_edit_company, check_edit_company
from aptum.modules.companies.repository import CompanyRepository
from aptum.modules.companies.schemas import CompanyCreate, CompanyRead, CompanyUpdate
from aptum.modules.users.models import User


class CompanyService:
    def __init__(self, db: Session) -> None:
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
