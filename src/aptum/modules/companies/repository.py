from sqlalchemy.orm import Session

from aptum.modules.companies.models import Company, Industry


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
