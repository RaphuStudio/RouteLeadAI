import json
import logging
import os
from typing import Optional, Dict

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from app.models.lead import Lead, LeadStatus
from app.config import Settings
from app.llm_utils import get_llm, parse_json_from_llm

# 阈值常量
HIGH_INTENT_THRESHOLD = 100  # >=100 高意向
NURTURE_THRESHOLD_MIN = 62   # 62-99 培育
# < 62 长尾


class LeadClassifier:
    """基于 BANT 评分的意向分类 Agent，支持多模型"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", None)
        self.settings = Settings()
        self.provider = self.provider or self.settings.llm_provider or "openai"
        self.llm = get_llm(self.provider)

    def set_provider(self, provider: str):
        """运行时切换模型"""
        self.provider = provider.lower()
        self.llm = get_llm(self.provider)

    async def classify(self, lead: Lead) -> Lead:
        """给出 BANT 评分并写回 Lead 对象"""
        system_msg = SystemMessage(content=(
            "You are a sales-lead classifier using the BANTP framework (Budget, Authority, Need, Timeline, Position). "
            "Score each component (Budget, Authority, Need, Timeline, Position) on a 0-25 scale. "
            "Position is job title impact score (0-25). Also return position_title (job title name). "
            "Total Intent is sum of 5 components (0-125). "
            "Return ONLY a valid JSON object, no extra text."
        ))
        human_msg = HumanMessage(content=(
            f"Lead data:\n"
            f"company_name={lead.company_name or '(not provided)'}\n"
            f"contact_name={lead.contact_name or '(not provided)'}\n"
            f"position={lead.position or '(not provided)'}\n"
            f"raw_content={lead.raw_content}\n"
            "Provide JSON with keys: budget, authority, need, timeline, position, position_title, intent."
        ))

        resp = await self.llm.ainvoke([system_msg, human_msg])

        # 容错解析 LLM 输出
        scores = parse_json_from_llm(resp.content)
        if scores is None:
            logger.warning(f"LLM 返回非法 JSON，使用默认评分 0")
            scores = {}

        # 更新 Lead
        lead.budget_score    = int(scores.get("budget", 0))
        lead.authority_score = int(scores.get("authority", 0))
        lead.need_score      = int(scores.get("need", 0))
        lead.timeline_score  = int(scores.get("timeline", 0))
        position_score = int(scores.get("position", 0))
        lead.intent_score    = (
            int(scores.get("budget", 0)) +
            int(scores.get("authority", 0)) +
            int(scores.get("need", 0)) +
            int(scores.get("timeline", 0)) +
            position_score
        )

        # 更新职位名称
        if scores.get("position_title"):
            lead.position = str(scores.get("position_title"))

        # 根据 intent_score 给状态打标（满分125：100+=高意向，62-99=培育，<62=长尾）
        if lead.intent_score >= HIGH_INTENT_THRESHOLD:
            lead.status = LeadStatus.CONTACTED
            lead.assigned_agent = "high_intent_agent"
        elif lead.intent_score >= NURTURE_THRESHOLD_MIN:
            lead.status = LeadStatus.CONTACTED
            lead.assigned_agent = "normal_nurture_agent"
        else:
            lead.status = LeadStatus.NEW
            lead.assigned_agent = None

        return lead
