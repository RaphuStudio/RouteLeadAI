import json
import os
import re
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.config import Settings


def get_llm(provider: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 512):
    """根据 provider 动态创建 LLM 实例，所有配置均从环境变量通过 Settings 获取"""
    settings = Settings()
    provider = provider or os.getenv("LLM_PROVIDER", settings.llm_provider or "openai").lower()

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
            temperature=temperature,
            max_tokens=max_tokens
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
            temperature=temperature,
            max_tokens=max_tokens
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
            temperature=temperature,
            max_tokens=max_tokens
        )

    elif provider == "custom":
        api_key = settings.custom_api_key or os.getenv("CUSTOM_API_KEY", "")
        model_name = settings.custom_model or os.getenv("CUSTOM_MODEL", "default")
        api_base = settings.custom_api_base or os.getenv("CUSTOM_API_BASE", "")
        if not api_key:
            raise ValueError("未在 .env 中配置 CUSTOM_API_KEY")
        if not api_base:
            raise ValueError("未在 .env 中配置 CUSTOM_API_BASE")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens
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
            temperature=temperature,
            max_tokens=max_tokens
        )


def parse_json_from_llm(content: str) -> Optional[Dict[str, Any]]:
    """安全解析 LLM 输出的 JSON，支持代码块包裹、多余文本等容错"""
    if not content:
        return None
    # 尝试去掉 markdown 代码块标记
    text = content.strip()
    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_block:
        text = code_block.group(1).strip()
    # 尝试从字符串中提取第一个 { } 对
    brace_start = text.find('{')
    brace_end = text.rfind('}')
    if brace_start != -1 and brace_end > brace_start:
        text = text[brace_start:brace_end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
