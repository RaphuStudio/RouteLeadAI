import json
import os
from typing import Optional, Dict
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.models.lead import Lead, LeadStatus
from app.config import Settings


def _get_llm(provider: Optional[str] = None):
    """根据 provider 动态创建 LLM 实例，所有配置均从环境变量通过 Settings 获取"""
    settings = Settings()
    provider = provider or os.getenv("LLM_PROVIDER", settings.llm_provider or "openai").lower()

    # 从 Settings 中统一获取 API Key 和 Base URL
    if provider == "anthropic":
        api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        model_name = settings.anthropic_model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        api_base = settings.anthropic_api_base or os.getenv("ANTHROPIC_API_BASE", "")
        if not api_key:
            raise ValueError("未在 .env 中配置 ANTHROPIC_API_KEY")
        return ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            anthropic_api_url=api_base if api_base else None,
            temperature=0.2,
            max_tokens=512
        )

    elif provider == "qwen":
        api_key = settings.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")
        model_name = settings.qwen_model or os.getenv("QWEN_MODEL", "qwen-turbo")
        api_base = settings.qwen_api_base or os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            raise ValueError("未在 .env 中配置 DASHSCOPE_API_KEY")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.2,
            max_tokens=512
        )

    elif provider == "deepseek":
        api_key = settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "")
        model_name = settings.deepseek_model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        api_base = settings.deepseek_api_base or os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        if not api_key:
            raise ValueError("未在 .env 中配置 DEEPSEEK_API_KEY")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.2,
            max_tokens=512
        )

    elif provider == "custom":
        api_key = settings.custom_api_key or os.getenv("CUSTOM_API_KEY", "")
        model_name = settings.custom_model or os.getenv("CUSTOM_MODEL", "default")
        api_base = settings.custom_api_base or os.getenv("CUSTOM_API_BASE", "")
        if not api_key:
            raise ValueError("未在 .env 中配置 CUSTOM_API_KEY")
        if not api_base:
            raise ValueError("未在 .env 中配置 CUSTOM_API_BASE")
        if not model_name:
            model_name = "default"
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.2,
            max_tokens=512
        )

    else:  # openai default
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        model_name = settings.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_base = settings.openai_api_base or os.getenv("OPENAI_API_BASE", "")
        if not api_key:
            raise ValueError("未在 .env 中配置 OPENAI_API_KEY")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base if api_base else None,
            temperature=0.2,
            max_tokens=512
        )


class LeadClassifier:
    """基于 BANT 评分的意向分类 Agent，支持多模型"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", None)
        self.settings = Settings()
        self.provider = self.provider or self.settings.llm_provider or "openai"
        self.llm = _get_llm(self.provider)

    def set_provider(self, provider: str):
        """运行时切换模型"""
        self.provider = provider.lower()
        self.llm = _get_llm(self.provider)

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
        scores: Dict = json.loads(resp.content)

        # 更新 Lead
        lead.budget_score    = int(scores.get("budget", 0))
        lead.authority_score = int(scores.get("authority", 0))
        lead.need_score      = int(scores.get("need", 0))
        lead.timeline_score  = int(scores.get("timeline", 0))
        # 获取 position 分数（0-25）
        position_score = int(scores.get("position", 0))
        # 计算 intent_score：5个维度之和（0-125）
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
        if lead.intent_score >= 100:
            lead.status = LeadStatus.CONTACTED
            lead.assigned_agent = "high_intent_agent"
        elif 62 <= lead.intent_score < 100:
            lead.status = LeadStatus.CONTACTED
            lead.assigned_agent = "normal_nurture_agent"
        else:
            lead.status = LeadStatus.NEW
            lead.assigned_agent = None

        return lead
