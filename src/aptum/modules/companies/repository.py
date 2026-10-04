from sqlalchemy import or_
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

    def is_used_by_experiences(self, company_id: int) -> bool:
        return (
            self.db.query(Experience.id)
            .filter(or_(Experience.employer_id == company_id, Experience.client_id == company_id))
            .first()
            is not None
        )

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
