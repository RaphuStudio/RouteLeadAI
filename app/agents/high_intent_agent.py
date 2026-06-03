import os
from typing import Dict, Any, Optional
import json
from langchain_community.chat_models import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.models.lead import Lead, LeadStatus
from app.config import Settings


def _get_llm_for_agent(provider: Optional[str] = None):
    """为高意向Agent获取LLM实例，不使用Google模型"""
    settings = Settings()
    provider = provider or os.getenv("LLM_PROVIDER", settings.llm_provider or "openai").lower()

    if provider == "anthropic":
        api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        model_name = settings.anthropic_model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        api_base = settings.anthropic_api_base or os.getenv("ANTHROPIC_API_BASE", "")
        if not api_key:
            raise ValueError("未找到 ANTHROPIC_API_KEY")
        return ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            anthropic_api_url=api_base if api_base else None,
            temperature=0.3,
            max_tokens=800
        )

    elif provider == "qwen":
        api_key = settings.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")
        if not api_key:
            raise ValueError("未找到 DASHSCOPE_API_KEY")
        model_name = settings.qwen_model or os.getenv("QWEN_MODEL", "qwen-turbo")
        api_base = settings.qwen_api_base or os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.3,
            max_tokens=800
        )

    elif provider == "deepseek":
        api_key = settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("未找到 DEEPSEEK_API_KEY")
        model_name = settings.deepseek_model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        api_base = settings.deepseek_api_base or os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.3,
            max_tokens=800
        )

    elif provider == "custom":
        api_key = settings.custom_api_key or os.getenv("CUSTOM_API_KEY", "")
        model_name = settings.custom_model or os.getenv("CUSTOM_MODEL", "default")
        api_base = settings.custom_api_base or os.getenv("CUSTOM_API_BASE", "")
        if not api_base:
            raise ValueError("未找到 CUSTOM_API_BASE")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            openai_api_base=api_base,
            temperature=0.3,
            max_tokens=800
        )

    else:  # openai default
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("未找到 OPENAI_API_KEY")
        model_name = settings.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_base = settings.openai_api_base or os.getenv("OPENAI_API_BASE", "")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base if api_base else None,
            temperature=0.3,
            max_tokens=800
        )


class HighIntentAgent:
    """高意向线索极速跟进 Agent (15分钟内触达)"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", None)
        self.settings = Settings()
        self.provider = self.provider or self.settings.llm_provider or "openai"
        self.llm = _get_llm_for_agent(self.provider)

    def set_provider(self, provider: str):
        """运行时切换模型"""
        self.provider = provider.lower()
        self.llm = _get_llm_for_agent(self.provider)

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

        print(f"[HighIntentAgent] 处理线索 {lead.id}，意向分: {lead.intent_score}")
        print(f"[HighIntentAgent] 生成消息: {message[:100]}...")

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
