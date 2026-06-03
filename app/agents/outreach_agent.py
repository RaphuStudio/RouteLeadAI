from typing import Dict
import os
import logging

from app.services.email_service import EmailService
from app.services.wework_service import WeWorkService
from app.services.dingtalk_service import DingTalkService
from app.services.sms_service import SMSService
from app.config import settings

logger = logging.getLogger(__name__)


class OutreachAgent:
    """
    高意向线索触达 Agent
    负责多渠道发送：邮件、企业微信、钉钉、短信
    """

    def __init__(self):
        self.email_service = EmailService()
        self.wework_service = WeWorkService()
        self.dingtalk_service = DingTalkService()
        self.sms_service = SMSService()

        # 初始化 LLM（使用 DeepSeek，通过 OpenAI 兼容接口）
        from langchain_openai import ChatOpenAI
        self.llm = ChatOpenAI(
            model=settings.llm_model or "deepseek-v4-flash",
            openai_api_key=settings.deepseek_api_key,
            openai_api_base=settings.deepseek_api_base or "https://api.deepseek.com/v1",
            temperature=0.2,
            max_tokens=512
        )

    def execute(self, lead: Dict) -> Dict:
        """
        对单条高意向线索进行多渠道触达

        Args:
            lead: 线索字典，需包含 email、phone、company_name、contact_name、intent_score 等

        Returns:
            dict: 各渠道发送结果汇总
        """
        results = {
            "email": {"success": False},
            "wework": {"success": False},
            "dingtalk": {"success": False},
            "sms": {"success": False},
        }

        # 1. 邮件触达
        if lead.get("email"):
            try:
                results["email"] = self.email_service.send_outreach_email(lead)
            except Exception as e:
                logger.error(f"邮件触达异常: {e}")
                results["email"] = {"success": False, "message": str(e)}

        # 2. 企业微信触达
        try:
            content = self._format_wework_message(lead)
            results["wework"] = self.wework_service.send_message(content)
        except Exception as e:
            logger.error(f"企业微信触达异常: {e}")
            results["wework"] = {"success": False, "message": str(e)}

        # 3. 钉钉触达
        try:
            content = self._format_dingtalk_message(lead)
            # 可选：@销售负责人，如果有 mobile 信息
            results["dingtalk"] = self.dingtalk_service.send_text(content)
        except Exception as e:
            logger.error(f"钉钉触达异常: {e}")
            results["dingtalk"] = {"success": False, "message": str(e)}

        # 4. 短信触达
        if lead.get("phone"):
            try:
                results["sms"] = self.sms_service.send_template(
                    phone_number=lead["phone"],
                    template_code=os.getenv('ALI_SMS_TEMPLATE_CODE', 'SMS_12345678'),
                    template_params={"name": lead.get("contact_name", "客户"), "company": lead.get("company_name", "")}
                )
            except Exception as e:
                logger.error(f"短信触达异常: {e}")
                results["sms"] = {"success": False, "message": str(e)}

        logger.info(f"线索 {lead.get('contact_name')} 触达完成: {results}")
        return {
            "lead_id": lead.get("id"),
            "timestamp": lead.get("created_at"),
            "results": results,
            "overall_success": any(r.get("success") for r in results.values())
        }


    def _generate_wework_message(self, lead: Dict) -> str:
        """使用 LLM 生成企业微信个性化消息"""
        from langchain_core.messages import HumanMessage, SystemMessage
        system_msg = SystemMessage(content=(
            "You are a professional sales outreach specialist. "
            "Generate concise WeChat (企业微信) messages for high-intent leads. "
            "Message MUST start with 【高意向线索】. "
            "Return ONLY the message text, no extra formatting."
        ))
        human_msg = HumanMessage(content=(
            f"Lead data:\n"
            f"company_name={lead.get('company_name', 'N/A')}\n"
            f"contact_name={lead.get('contact_name', 'N/A')}\n"
            f"intent_score={lead.get('intent_score', 0)}\n"
            f"raw_content={lead.get('raw_content', '')}\n"
            "Generate a concise WeChat message with:\n"
            "1) Header: 【高意向线索】\n"
            "2) Company name and contact name\n"
            "3) Intent score\n"
            "4) Call to action: 建议15分钟内跟进！\n"
            "Keep it short and professional."
        ))

        try:
            resp = self.llm.invoke([system_msg, human_msg])
            return resp.content.strip() if resp.content else self._fallback_wework(lead)
        except Exception as e:
            logger.error(f"LLM 生成企微消息失败: {e}")
            return self._fallback_wework(lead)

    def _fallback_wework(self, lead: Dict) -> str:
        """企微消息降级模板"""
        company = lead.get("company_name", "贵公司")
        contact = lead.get("contact_name", "负责人")
        score = lead.get("intent_score", 0)
        return (
            f"【高意向线索】\n"
            f"公司：{company}\n"
            f"联系人：{contact}\n"
            f"意向评分：{score}\n"
            f"建议15分钟内跟进！"
        )

    def _generate_dingtalk_message(self, lead: Dict) -> str:
        """使用 LLM 生成钉钉个性化消息"""
        from langchain_core.messages import HumanMessage, SystemMessage
        system_msg = SystemMessage(content=(
            "You are a professional sales outreach specialist. "
            "Generate concise DingTalk (钉钉) messages for high-intent leads. "
            "Message MUST start with 'AI Sales'. "
            "Return ONLY the message text, no extra formatting."
        ))
        human_msg = HumanMessage(content=(
            f"Lead data:\n"
            f"company_name={lead.get('company_name', 'N/A')}\n"
            f"contact_name={lead.get('contact_name', 'N/A')}\n"
            f"intent_score={lead.get('intent_score', 0)}\n"
            f"raw_content={lead.get('raw_content', '')}\n"
            "Generate a concise DingTalk message with:\n"
            "1) MUST start with 'AI Sales'\n"
            "2) Header: 【高意向线索提醒】\n"
            "3) Company name and contact name\n"
            "4) Intent score\n"
            "5) Call to action: 请及时跟进！\n"
            "Keep it short and professional."
        ))

        try:
            resp = self.llm.invoke([system_msg, human_msg])
            return resp.content.strip() if resp.content else self._fallback_dingtalk(lead)
        except Exception as e:
            logger.error(f"LLM 生成钉钉消息失败: {e}")
            return self._fallback_dingtalk(lead)

    def _fallback_dingtalk(self, lead: Dict) -> str:
        """钉钉消息降级模板"""
        company = lead.get("company_name", "贵公司")
        contact = lead.get("contact_name", "负责人")
        score = lead.get("intent_score", 0)
        return (
            f"AI Sales【高意向线索提醒】\n"
            f"公司：{company}\n"
            f"联系人：{contact}\n"
            f"意向评分：{score}\n"
            f"请及时跟进！"
        )

    def _format_wework_message(self, lead: Dict) -> str:
        """向企业微信机器人推送文本消息（使用 LLM 生成）"""
        return self._generate_wework_message(lead)

    def _format_dingtalk_message(self, lead: Dict) -> str:
        """钉钉消息（使用 LLM 生成）"""
        return self._generate_dingtalk_message(lead)
