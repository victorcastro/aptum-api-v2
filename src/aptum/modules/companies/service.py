from sqlalchemy.orm import Session

from aptum.common.utils import normalize_name
from aptum.core.exceptions import NotFoundError
from aptum.modules.companies.models import Company, Industry
from aptum.modules.companies.repository import CompanyRepository
from aptum.modules.companies.schemas import CompanyCreate


class CompanyService:
    def __init__(self, db: Session) -> None:
        self.repository = CompanyRepository(db)

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

    def search(self, query: str, limit: int = 20) -> list[Company]:
        return self.repository.search(normalize_name(query), limit)

    def get(self, company_id: int) -> Company:
        company = self.repository.get(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company

    def list_industries(self) -> list[Industry]:
        return self.repository.list_industries()
