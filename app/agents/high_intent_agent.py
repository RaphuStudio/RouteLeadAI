import logging
import os
from typing import Dict, Any, Optional
import json
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)
from app.models.lead import Lead, LeadStatus
from app.config import Settings
from app.llm_utils import get_llm


class HighIntentAgent:
    """高意向线索极速跟进 Agent (15分钟内触达)"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", None)
        self.settings = Settings()
        self.provider = self.provider or self.settings.llm_provider or "openai"
        self.llm = get_llm(self.provider, temperature=0.3, max_tokens=800)

    def set_provider(self, provider: str):
        """运行时切换模型"""
        self.provider = provider.lower()
        self.llm = get_llm(self.provider, temperature=0.3, max_tokens=800)

    async def process(self, lead: Lead) -> Dict[str, Any]:
        """
        处理高意向线索：
        1. 生成个性化跟进消息
        2. 准备多渠道触达内容
        3. 返回待发送的任务
        """
        # 生成个性化消息
        message = await self._generate_message(lead)

        # 构造返回结果
        result = {
            "lead_id": lead.id,
            "intent_score": lead.intent_score,
            "message": message,
            "channels": ["email", "wechat", "sms"],
            "followup_time_minutes": 15,
            "status": "ready_to_send"
        }

        logger.info(f"[HighIntentAgent] 处理线索 {lead.id}，意向分: {lead.intent_score}")

        return result

    async def _generate_message(self, lead: Lead) -> str:
        """生成个性化跟进消息"""
        system_msg = SystemMessage(content=(
            "你是专业的销售顾问。根据线索信息，生成个性化的首次跟进消息。"
            "要求：专业、热情、简洁（<200字），包含会议邀约（提供3个时间选项）。"
        ))
        human_msg = HumanMessage(content=(
            f"线索信息：\n"
            f"公司：{lead.company_name or '未知'}\n"
            f"联系人：{lead.contact_name or '未知'}\n"
            f"意向分：{lead.intent_score}\n"
            f"原始内容：{lead.raw_content}\n\n"
            "请生成跟进消息："
        ))

        resp = await self.llm.ainvoke([system_msg, human_msg])
        return resp.content.strip()
