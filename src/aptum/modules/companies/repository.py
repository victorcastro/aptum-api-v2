from collections.abc import Collection

from sqlalchemy import select, union, update
from sqlalchemy.orm import Session

from aptum.modules.companies.models import Company, Industry
from aptum.modules.profile.models import Experience


class CompanyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, company_id: int) -> Company | None:
        return self.db.get(Company, company_id)

    def get_by_normalized_name(self, normalized_name: str) -> Company | None:
        return (
            self.db.query(Company).filter(Company.normalized_name == normalized_name).first()
        )

    def search(self, normalized_query: str, limit: int) -> list[Company]:
        return (
            self.db.query(Company)
            .filter(Company.normalized_name.contains(normalized_query, autoescape=True))
            .order_by(Company.name)
            .limit(limit)
            .all()
        )

    def used_ids(self, company_ids: Collection[int]) -> set[int]:
        """Which of these companies some experience uses, as employer or client. One query."""
        if not company_ids:
            return set()
        as_employer = select(Experience.employer_id).where(Experience.employer_id.in_(company_ids))
        as_client = select(Experience.client_id).where(Experience.client_id.in_(company_ids))
        return set(self.db.scalars(union(as_employer, as_client)))

    def is_used_by_experiences(self, company_id: int) -> bool:
        return company_id in self.used_ids([company_id])

    def lock_pair(self, first_id: int, second_id: int) -> dict[int, Company]:
        """Lock both companies in id order (no deadlock between concurrent merges)."""
        rows = self.db.scalars(
            select(Company)
            .where(Company.id.in_((first_id, second_id)))
            .order_by(Company.id)
            .with_for_update(of=Company)  # the joined industry is not locked (nullable side)
        )
        return {company.id: company for company in rows}

    def repoint_experiences(self, source_id: int, target_id: int) -> dict[str, int]:
        """Move every experience from `source` to `target`, as employer and as client. Where that
        makes client == employer, the client is cleared (one company cannot hire itself through
        itself). No commit."""
        employer = self.db.execute(
            update(Experience).where(Experience.employer_id == source_id).values(employer_id=target_id)
        ).rowcount
        client = self.db.execute(
            update(Experience).where(Experience.client_id == source_id).values(client_id=target_id)
        ).rowcount
        cleared = self.db.execute(
            update(Experience)
            .where(Experience.employer_id == target_id, Experience.client_id == target_id)
            .values(client_id=None)
        ).rowcount
        return {"employer": employer, "client": client, "client_cleared": cleared}

    def delete(self, company: Company) -> None:
        """No commit."""
        self.db.delete(company)

    def get_industry(self, industry_id: int) -> Industry | None:
        return self.db.get(Industry, industry_id)

    def create_industry(self, name: str, slug: str) -> Industry:
        """No commit."""
        industry = Industry(name=name, slug=slug)
        self.db.add(industry)
        self.db.flush()
        return industry

    def list_industries(self) -> list[Industry]:
        return self.db.query(Industry).order_by(Industry.name).all()

    def create(self, **fields) -> Company:
        company = Company(**fields)
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def update(self, company: Company, **fields) -> Company:
        for key, value in fields.items():
            setattr(company, key, value)
        self.db.commit()
        self.db.refresh(company)
        return company
