from collections.abc import Collection

from sqlalchemy import select, union
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

    def get_industry(self, industry_id: int) -> Industry | None:
        return self.db.get(Industry, industry_id)

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
