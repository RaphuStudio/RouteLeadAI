from typing import Dict
import logging

from app.config import settings
from app.llm_utils import get_llm

logger = logging.getLogger(__name__)


class LongTailNurtureAgent:
    """
    长尾线索培育 Agent（<50 分）
    负责长尾线索的轻型触达：价值内容推送、品牌认知、低频率跟进
    相比中等意向培育，更侧重品牌曝光和极低频次触达
    """

    def __init__(self):
        # 长尾线索不需要复杂的 LLM 生成，使用轻量级模板
        # 如需偶尔生成内容，可初始化 LLM
        self.enable_llm = settings.longtail_enable_llm or False

        if self.enable_llm:
            from langchain_core.messages import HumanMessage, SystemMessage
            self.llm = get_llm(temperature=0.5, max_tokens=512)
            self.SystemMessage = SystemMessage
            self.HumanMessage = HumanMessage

    def execute(self, lead: Dict) -> Dict:
        """
        对长尾线索进行轻型培育触达

        Args:
            lead: 线索字典，意向评分 <50

        Returns:
            dict: 执行结果
        """
        lead_id = lead.get("id", "unknown")
        logger.info(f"[LongTail] 处理长尾线索 {lead_id}，意向评分: {lead.get('intent_score', 0)}")

        results = {
            "email": {"success": False, "message": "skipped"},
            "wework": {"success": False, "message": "skipped"},
            "dingtalk": {"success": False, "message": "skipped"},
            "sms": {"success": False, "message": "skipped"},
        }

        # 长尾线索策略：
        # 1. 不主动触达，仅记录到 CRM 或添加到期自动营销序列
        # 2. 可以选择发送一封"欢迎+价值内容"邮件（低频）
        # 3. 企业微信/钉钉不发送（避免过度打扰）

        # 可选：发送一封欢迎邮件（包含价值内容）
        if lead.get("email") and self._should_send_welcome(lead):
            try:
                from app.services.email_service import EmailService
                email_service = EmailService()
                results["email"] = self._send_welcome_email(email_service, lead)
            except Exception as e:
                logger.error(f"[LongTail] 欢迎邮件发送异常: {e}")
                results["email"] = {"success": False, "message": str(e)}
        else:
            results["email"] = {"success": True, "message": "长尾线索，跳过邮件触达"}

        # 企微和钉钉：不发送（避免过度打扰）
        results["wework"] = {"success": True, "message": "长尾线索，跳过企微触达"}
        results["dingtalk"] = {"success": True, "message": "长尾线索，跳过钉钉触达"}

        logger.info(f"[LongTail] 线索 {lead_id} 处理完成: {results}")

        return {
            "lead_id": lead_id,
            "timestamp": lead.get("created_at"),
            "agent": "longtail_nurture_agent",
            "intent_score": lead.get("intent_score", 0),
            "strategy": "low-frequency nurturing, brand awareness",
            "results": results,
            "overall_success": all(r.get("success") for r in results.values() if r.get("message") != "skipped")
        }

    def _should_send_welcome(self, lead: Dict) -> bool:
        """
        判断是否需要发送欢迎邮件
        长尾线索策略：仅发送 1 次欢迎邮件，后续不再主动触达
        """
        # 这里可以检查 Redis 或数据库，判断是否已发送过欢迎邮件
        # 简化实现：始终发送（实际生产中应检查历史记录）
        return True

    def _send_welcome_email(self, email_service, lead: Dict) -> Dict:
        """发送欢迎邮件（长尾线索专用，内容更通用）"""
        if self.enable_llm:
            return self._send_welcome_email_llm(email_service, lead)
        else:
            return self._send_welcome_email_template(email_service, lead)

    def _send_welcome_email_template(self, email_service, lead: Dict) -> Dict:
        """使用模板发送欢迎邮件（降级方案）"""
        company = lead.get("company_name", "贵公司")
        contact = lead.get("contact_name", "负责人")
        score = lead.get("intent_score", 0)

        subject = f"【行业洞察】致 {company}：销售自动化趋势与最佳实践"

        content = f"""
尊敬的 {contact} 先生/女士：

您好！

感谢您对销售自动化领域的关注。我们注意到 {company} 正在探索相关解决方案（BANT评分: {score}），
特意为您准备了以下行业洞察内容：

【行业趋势】
✓ 2026年，85% 的企业将销售自动化纳入数字化转型核心战略
✓ 智能线索评分可提升转化率 35% 以上
✓ 全渠道触达（邮件/企微/钉钉）成行业标配

【免费资源】
我们为您准备了《销售自动化最佳实践指南》，涵盖：
• 线索评分体系设计（BANT 框架详解）
• 多渠道触达策略（邮件/企微/钉钉组合拳）
• ROI 测算模型与案例分享

【保持联系】
我们将以极低频率（每季度 1-2 次）为您推送行业干货，
绝不打扰您的正常工作。如有任何需求，欢迎随时回复本邮件。

此致
敬礼！

AI Sales 团队
"""

        html_content = content.replace('\n', '<br>')
        return email_service.send_email(lead['email'], subject, html_content)

    def _send_welcome_email_llm(self, email_service, lead: Dict) -> Dict:
        """使用 LLM 生成个性化欢迎邮件"""
        try:
            system_msg = self.SystemMessage(content=(
                "You are a professional sales nurturing specialist. "
                "Generate a ONE-TIME welcome email for low-intent leads (<50 BANT score). "
                "Focus on: industry insights, educational content, brand awareness. "
                "Keep it warm, not pushy. Mention this is a one-time outreach. "
                "Return ONLY a valid JSON object with 'subject' and 'content' keys."
            ))
            human_msg = self.HumanMessage(content=(
                f"Lead data:\n"
                f"company_name={lead.get('company_name', 'N/A')}\n"
                f"contact_name={lead.get('contact_name', 'N/A')}\n"
                f"intent_score={lead.get('intent_score', 0)}\n"
                f"raw_content={lead.get('raw_content', '')}\n"
                "Generate a ONE-TIME welcome email with: "
                "1) A subject line about industry insights or trends "
                "2) A warm email body: "
                "   - Personalized greeting "
                "   - Acknowledge they're in early exploration phase "
                "   - 2-3 valuable industry insights "
                "   - Mention: one-time outreach, we'll only send quarterly updates "
                "   - Soft CTA: reply if they have questions "
                "Keep it educational, low-pressure. Use markdown for formatting."
            ))

            resp = self.llm.invoke([system_msg, human_msg])
            import json
            result = json.loads(resp.content)
            subject = result.get('subject', '')
            content = result.get('content', '')
            return email_service.send_email(lead['email'], subject, content.replace('\n', '<br>'))

        except Exception as e:
            logger.error(f"[LongTail] LLM 生成欢迎邮件失败: {e}")
            # 降级到模板
            return self._send_welcome_email_template(email_service, lead)
