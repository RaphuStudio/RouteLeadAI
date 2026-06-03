from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid
from typing import Optional


class LeadSource(str, Enum):
    WEBSITE = "website"
    CHAT = "chat"
    IMPORT = "import"
    REFERRAL = "referral"


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class Lead(BaseModel):
    # 基础标识
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: LeadSource

    # 原始内容
    raw_content: str

    # 解析字段
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # BANT 评分 (0-25 each)
    budget_score: int = Field(default=0, ge=0, le=25)
    authority_score: int = Field(default=0, ge=0, le=25)
    need_score: int = Field(default=0, ge=0, le=25)
    timeline_score: int = Field(default=0, ge=0, le=25)
    intent_score: int = Field(default=0, ge=0, le=125)

    # 流程状态
    status: LeadStatus = LeadStatus.NEW
    assigned_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
