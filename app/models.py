from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class LeadSource(str):
    WEBSITE = "website"
    FORM = "form"
    REFERRAL = "referral"
    EVENT = "event"
    SOCIAL_MEDIA = "social_media"
    COLD_OUTREACH = "cold_outreach"

class LeadStatus(str):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    NURTURING = "nurturing"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

class LeadBase(BaseModel):
    source: LeadSource
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    budget_score: int = Field(default=0, ge=0, le=100)
    authority_score: int = Field(default=0, ge=0, le=100)
    need_score: int = Field(default=0, ge=0, le=100)
    timeline_score: int = Field(default=0, ge=0, le=100)
    intent_score: int = Field(default=0, ge=0, le=100)
    status: LeadStatus = LeadSource.NEW
    assigned_agent: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    budget_score: Optional[int] = Field(default=None, ge=0, le=100)
    authority_score: Optional[int] = Field(default=None, ge=0, le=100)
    need_score: Optional[int] = Field(default=None, ge=0, le=100)
    timeline_score: Optional[int] = Field(default=None, ge=0, le=100)
    intent_score: Optional[int] = Field(default=None, ge=0, le=100)
    status: Optional[LeadStatus] = None
    assigned_agent: Optional[str] = None

class LeadInDBBase(LeadBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class Lead(LeadInDBBase):
    pass

class LeadOutreachResult(BaseModel):
    lead_id: str
    timestamp: datetime
    email_success: bool = False
    wework_success: bool = False
    dingtalk_success: bool = False
    sms_success: bool = False
    overall_success: bool = False
    message: Optional[str] = None
