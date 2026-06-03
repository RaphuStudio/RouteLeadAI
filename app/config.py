from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # LLM API Keys - 请在.env文件中填入实际值
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    dashscope_api_key: str = ""  # 阿里云通义千问/灵积
    custom_api_key: str = ""     # 自定义模型
    deepseek_api_key: str = ""   # DeepSeek API Key

    # LLM API Base URLs - 自定义模型服务端点
    openai_api_base: str = ""
    anthropic_api_base: str = ""
    qwen_api_base: str = ""
    custom_api_base: str = ""
    deepseek_api_base: str = ""  # DeepSeek Base URL

    # LLM Configuration
    llm_provider: str = "openai"  # openai, anthropic, qwen, custom, deepseek
    llm_model: str = "deepseek-v4-flash"  # 使用的模型名称
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-haiku-20240307"
    qwen_model: str = "qwen-turbo"
    custom_model: str = "openai:gpt-4o"        # 自定义模型名称
    deepseek_model: str = "deepseek-v3-flash"  # DeepSeek 模型名称

    # Email Service (Resend)
    resend_api_key: str = ""
    email_from: str = ""
    email_from_name: str = ""

    # WeChat (企业微信) Webhook
    wechat_webhook_url: str = ""

    # DingTalk (钉钉) Webhook
    dingtalk_webhook_url: str = ""
    dingtalk_webhook: str = ""
    dingtalk_secret: str = ""

    # SMS Service (阿里云 - 已放弃)
    ali_access_key: str = ""
    ali_secret_key: str = ""
    ali_endpoint: str = ""
    ali_sign_name: str = ""
    ali_sms_template_code: str = ""
    ali_region: str = ""

    # LongTail Nurture Agent (optional)
    longtail_enable_llm: bool = False  # 是否启用 LLM 生成长尾线索邮件

    # CRM (optional)
    crm_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略 .env 中未定义的字段，避免启动失败


# 全局设置实例
settings = Settings()
