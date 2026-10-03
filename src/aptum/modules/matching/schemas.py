from pydantic import BaseModel


class MatchRequest(BaseModel):
    job_description: str


class MatchResult(BaseModel):
    score: float
    tailored_cv: str
