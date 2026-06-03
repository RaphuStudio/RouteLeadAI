from .models import LeadCreate, LeadUpdate
from pydantic import Field, validator
from typing import Optional

def validate_score(score: int) -> int:
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100")
    return score

class LeadCreateWithValidation(LeadCreate):
    @validator('budget_score', 'authority_score', 'need_score', 'timeline_score', 'intent_score')
    def check_score_range(cls, v):
        validate_score(v)
        return v

class LeadUpdateWithValidation(LeadUpdate):
    @validator('budget_score', 'authority_score', 'need_score', 'timeline_score', 'intent_score')
    def check_score_range(cls, v: Optional[int]):
        if v is not None:
            validate_score(v)
        return v