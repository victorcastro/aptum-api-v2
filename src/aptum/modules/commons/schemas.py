from pydantic import BaseModel


class CountryRead(BaseModel):
    code: str
    name: str
