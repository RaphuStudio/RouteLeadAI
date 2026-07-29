from typing import Dict
import logging
import json
import time

from app.services.email_service import EmailService
from app.services.wework_service import WeWorkService
from app.services.dingtalk_service import DingTalkService
from app.config import settings
from app.llm_utils import get_llm

logger = logging.getLogger(__name__)

# Redis 连接（用于记录培育时间）
import redis
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True
)

# 培育时间间隔（秒）：30 天
NURTURE_INTERVAL = 30 * 24 * 60 * 60


class NurtureAgent:
    """
    中等意向线索培育 Agent（50-79 分）
    负责培育跟进：定期触达、内容营销、价值传递
    相比高意向触达，更侧重教育和软性引导
    """

    def __init__(self):
        self.email_service = EmailService()
        self.wework_service = WeWorkService()
        self.dingtalk_service = DingTalkService()

        # 初始化 LLM
        self.llm = get_llm(temperature=0.3, max_tokens=768)

    def execute(self, lead: Dict) -> Dict:
        """
        对中等意向线索进行培育触达

        Args:
            lead: 线索字典，需包含 email、phone、company_name、contact_name、intent_score 等

        Returns:
            dict: 各渠道发送结果汇总
        """
        results = {
            "email": {"success": False},
            "wework": {"success": False},
            "dingtalk": {"success": False},
        }

        # 1. 邮件培育（发送价值内容）
        if lead.get("email"):
            try:
                results["email"] = self.email_service.send_nurturing_email(lead)
            except Exception as e:
                logger.error(f"培育邮件发送异常: {e}")
                results["email"] = {"success": False, "message": str(e)}

        # 2. 企业微信培育（软性触达）
        try:
            content = self._generate_wework_nurture(lead)
            results["wework"] = self.wework_service.send_message(content)
        except Exception as e:
            logger.error(f"企微培育触达异常: {e}")
            results["wework"] = {"success": False, "message": str(e)}

        # 3. 钉钉培育（价值提醒）
        try:
            content = self._generate_dingtalk_nurture(lead)
            results["dingtalk"] = self.dingtalk_service.send_text(content)
        except Exception as e:
            logger.error(f"钉钉培育触达异常: {e}")
            results["dingtalk"] = {"success": False, "message": str(e)}

        logger.info(f"线索 {lead.get('contact_name')} 培育完成: {results}")

        # 记录培育时间到 Redis（用于定期提醒）
        self._record_nurture_time(lead.get("id"), lead)

        return {
            "lead_id": lead.get("id"),
            "timestamp": lead.get("created_at"),
            "agent": "normal_nurture_agent",
            "results": results,
            "overall_success": any(r.get("success") for r in results.values())
        }

    def _record_nurture_time(self, lead_id: str, lead: Dict):
        """记录培育时间到 Redis，用于定期提醒"""
        if not lead_id:
            return
        try:
            current_time = int(time.time())
            # 存储最后培育时间
            redis_client.hset("nurture:last_sent", str(lead_id), str(current_time))
            # 存储线索信息（用于定时任务重新发送）
            lead_key = f"nurture:lead:{lead_id}"
            redis_client.hset(lead_key, mapping={
                "id": str(lead.get("id") or ""),
                "company_name": str(lead.get("company_name") or ""),
                "contact_name": str(lead.get("contact_name") or ""),
                "email": str(lead.get("email") or ""),
                "intent_score": str(lead.get("intent_score", 0)),
                "last_nurture": str(current_time)
            })
            # 设置过期时间（180 天，避免数据堆积）
            redis_client.expire(lead_key, 180 * 24 * 60 * 60)
            logger.info(f"[Nurture] 已记录培育时间: {lead_id}")
        except Exception as e:
            logger.error(f"[Nurture] 记录培育时间失败: {e}")

    def _generate_wework_nurture(self, lead: Dict) -> str:
        """使用 LLM 生成企业微信通知（面向销售团队，告知培育状态 + 建议话术）"""
        from langchain_core.messages import HumanMessage, SystemMessage
        system_msg = SystemMessage(content=(
            "You are a sales team notification assistant. "
            "Generate WeChat (企业微信) messages for the SALES TEAM about a medium-intent lead (50-79 score) in nurturing. "
            "This message is for SALES PEOPLE, not the customer. "
            "Message MUST start with 【培育中】. "
            "Return ONLY the message text, no extra formatting."
        ))
        human_msg = HumanMessage(content=(
            f"Lead data:\n"
            f"company_name={lead.get('company_name', 'N/A')}\n"
            f"contact_name={lead.get('contact_name', 'N/A')}\n"
            f"intent_score={lead.get('intent_score', 0)}\n"
            f"raw_content={lead.get('raw_content', '')}\n"
            "Generate a sales team notification with:\n"
            "1) Header: 【培育中】\n"
            "2) Customer info: company name, contact name, intent score (50-79)\n"
            "3) Status: 已自动发送培育邮件（价值内容/行业洞察）\n"
            "4) Suggested sales talk: provide 2-3 personalized follow-up phrases for the sales team\n"
            "   Example: '张经理，看到贵司在评估CRM，我们最近有个客户案例...'\n"
            "   Example: '王总，关于您关心的自动化流程，我们整理了...'\n"
            "5) CTA: 销售可适时介入 / 建议本周内联系\n"
            "Keep it informative and actionable for the sales team."
        ))

        try:
            resp = self.llm.invoke([system_msg, human_msg])
            return resp.content.strip() if resp.content else self._fallback_wework(lead)
        except Exception as e:
            logger.error(f"LLM 生成企微销售通知失败: {e}")
            return self._fallback_wework(lead)

    def _generate_dingtalk_nurture(self, lead: Dict) -> str:
        """使用 LLM 生成钉钉通知（面向销售团队，告知培育状态 + 建议话术）"""
        from langchain_core.messages import HumanMessage, SystemMessage
        system_msg = SystemMessage(content=(
            "You are a sales team notification assistant. "
            "Generate DingTalk (钉钉) messages for the SALES TEAM about a medium-intent lead (50-79 score) in nurturing. "
            "This message is for SALES PEOPLE; not the customer. "
            "Message MUST start with 'AI Sales'. "
            "Return ONLY the message text, no extra formatting."
        ))
        human_msg = HumanMessage(content=(
            f"Lead data:\n"
            f"company_name={lead.get('company_name', 'N/A')}\n"
            f"contact_name={lead.get('contact_name', 'N/A')}\n"
            f"intent_score={lead.get('intent_score', 0)}\n"
            f"raw_content={lead.get('raw_content', '')}\n"
            "Generate a sales team notification with:\n"
            "1) MUST start with 'AI Sales'\n"
            "2) Header: 【培育中】\n"
            "3) Customer info: company name, contact name, intent score (50-79)\n"
            "4) Status: 已自动发送培育邮件（价值内容/行业洞察）\n"
            "5) Suggested sales talk (2-3 personalized phrases):\n"
            "   Example: '张经理，看到贵司在评估CRM，我们最近有个客户案例...'\n"
            "   Example: '王总，关于您关心的自动化流程，我们整理了...'\n"
            "6) CTA: 销售可适时介入 / 建议本月内联系\n"
            "Keep it informative and actionable for the sales team."
        ))

        try:
            resp = self.llm.invoke([system_msg, human_msg])
            return resp.content.strip() if resp.content else self._fallback_dingtalk(lead)
        except Exception as e:
            logger.error(f"LLM 生成钉钉销售通知失败: {e}")
            return self._fallback_dingtalk(lead)

    def _fallback_wework(self, lead: Dict) -> str:
        """企微培育消息降级模板"""
        company = lead.get("company_name", "贵公司")
        contact = lead.get("contact_name", "负责人")
        score = lead.get("intent_score", 0)
        return (
            f"【培育跟进】\n"
            f"公司：{company}\n"
            f"联系人：{contact}\n"
            f"意向评分：{score}（培育中）\n"
            f"温馨提示：我们持续为您提供行业洞察与价值内容，欢迎随时交流探讨！"
        )

    def _fallback_dingtalk(self, lead: Dict) -> str:
        """钉钉培育消息降级模板"""
        company = lead.get("company_name", "贵公司")
        contact = lead.get("contact_name", "负责人")
        score = lead.get("intent_score", 0)
        return (
            f"AI Sales【培育跟进提醒】\n"
            f"公司：{company}\n"
            f"联系人：{contact}\n"
            f"意向评分：{score}（培育中）\n"
            f"我们将定期为您推送行业趋势与产品价值内容，如有疑问欢迎交流！"
        )
