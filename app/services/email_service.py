import requests
import logging
import json
import mistune

from app.config import settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# mistune Markdown 渲染器
_md = mistune.create_markdown()

logger = logging.getLogger(__name__)


class EmailService:
    """
    邮件服务 - 集成 Resend API 服务
    用于高意向线索触达的邮件渠道
    """

    def __init__(self):
        self.api_key = settings.resend_api_key
        self.from_email = settings.email_from
        self.from_name = settings.email_from_name
        self.api_url = "https://api.resend.com/emails"

        # 初始化 LLM（使用 DeepSeek，通过 OpenAI 兼容接口）
        self.llm = ChatOpenAI(
            model=settings.llm_model or "deepseek-v4-flash",
            openai_api_key=settings.deepseek_api_key,
            openai_api_base=settings.deepseek_api_base or "https://api.deepseek.com/v1",
            temperature=0.2,
            max_tokens=1024
        )

    def send_email(self, to_email: str, subject: str, content: str) -> dict:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容

        Returns:
            dict: {"success": bool, "message": str, "status_code": int}
        """
        if not self.api_key:
            logger.error("Resend API Key 未配置")
            return {"success": False, "message": "Resend API Key 未配置", "status_code": 500}

        if not self.from_email:
            logger.error("发件邮箱未配置")
            return {"success": False, "message": "发件邮箱未配置", "status_code": 500}

        try:
            payload = {
                "from": f"{self.from_name} <{self.from_email}>" if self.from_name else f"AI Sales Outreach <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": _md(content)  # Markdown → HTML
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            logger.debug(f"To: {to_email}, Subject: {subject}")
            response = requests.post(self.api_url, json=payload, headers=headers)
            logger.info(f"Email response: status={response.status_code}, to={to_email}")

            if response.status_code == 200:
                logger.info(f"邮件发送成功: {to_email}")
                return {"success": True, "message": "邮件发送成功", "status_code": response.status_code}
            else:
                logger.error(f"邮件发送失败: {to_email}, 响应: {response.text}")
                return {"success": False, "message": f"Resend API 错误: {response.text}", "status_code": response.status_code}

        except Exception as e:
            logger.error(f"邮件发送失败: {to_email}, 错误: {str(e)}")
            return {"success": False, "message": str(e), "status_code": 500}

    def _generate_email_content(self, lead: dict) -> tuple:
        """使用 LLM 根据线索数据生成个性化邮件内容"""
        system_msg = SystemMessage(content=(
            "You are a professional sales outreach specialist. "
            "Generate personalized outreach email content based on lead information. "
            "Return ONLY a valid JSON object with 'subject' and 'content' keys."
        ))
        human_msg = HumanMessage(content=(
            f"Lead data:\n"
            f"company_name={lead.get('company_name', 'N/A')}\n"
            f"contact_name={lead.get('contact_name', 'N/A')}\n"
            f"intent_score={lead.get('intent_score', 0)}\n"
            f"raw_content={lead.get('raw_content', '')}\n"
            "Generate a personalized email with: "
            "1) A subject line mentioning company name and BANT score. "
            "2) A professional email body with: "
            "   - Personalized greeting with contact_name "
            "   - Reference to company_name and intent_score "
            "   - 3 key value points (quick deployment, industry best practices, dedicated support) "
            "   - Suggested meeting times (tomorrow 10:00-11:00, 14:00-15:00, day after tomorrow 09:00-10:00) "
            "   - Professional closing. "
            "Keep content concise and professional. Use markdown for formatting."
        ))

        try:
            resp = self.llm.invoke([system_msg, human_msg])
            result = json.loads(resp.content)
            return result.get('subject', ''), result.get('content', '')
        except Exception as e:
            logger.error(f"LLM 生成邮件内容失败: {e}")
            # 降级到模板
            company_name = lead.get('company_name', '贵公司')
            contact_name = lead.get('contact_name', '负责人')
            intent_score = lead.get('intent_score', 0)

            subject = f"【高意向线索跟进】{company_name} - BANT评分: {intent_score}"

            content = f"""
尊敬的 {contact_name} 先生/女士：

您好！

感谢您对我们产品的关注。我们注意到 {company_name} 在相关领域的业务需求，
基于您的线索信息（BANT综合评分: {intent_score}），我们为您准备了专属的解决方案建议。

【核心价值点】
✓ 快速部署，即刻见效
✓ 行业最佳实践，降低实施风险
✓ 专属客户成功团队全程支持，

【下一步建议】
我们建议安排一次15分钟的简短沟通，详细了解您的具体需求，
并为您提供定制化的演示方案。

您可以选择以下时间进行沟通：
• 明日 10:00-11:00
• 明日 14:00-15:00
• 后日 09:00-10:00，

期待您的回复！

此致
敬礼！

销售跟进团队
"""
            return subject, content

    def send_outreach_email(self, lead: dict) -> dict:
        """
        发送高意向线索跟进邮件（使用 LLM 生成个性化内容）

        Args:
            lead: 线索数据字典

        Returns:
            dict: 发送结果
        """
        if not lead.get('email'):
            return {"success": False, "message": "线索无邮箱地址", "status_code": 400}

        # 使用 LLM 生成个性化邮件内容
        subject, content = self._generate_email_content(lead)

        return self.send_email(lead['email'], subject, content)

    def _generate_nurturing_content(self, lead: dict) -> tuple:
        """使用 LLM 根据线索数据生成培育邮件内容（教育、价值导向）"""
        system_msg = SystemMessage(content=(
            "You are a professional sales nurturing specialist. "
            "Generate educational, value-driven email content for medium-intent leads (50-79 score). "
            "Focus on industry insights, best practices, and gentle brand awareness. "
            "Return ONLY a valid JSON object with 'subject' and 'content' keys."
        ))
        human_msg = HumanMessage(content=(
            f"Lead data:\n"
            f"company_name={lead.get('company_name', 'N/A')}\n"
            f"contact_name={lead.get('contact_name', 'N/A')}\n"
            f"intent_score={lead.get('intent_score', 0)}\n"
            f"raw_content={lead.get('raw_content', '')}\n"
            "Generate a nurturing email with: "
            "1) A subject line about industry insights or best practices (mention company name) "
            "2) A warm email body with: "
            "   - Personalized greeting with contact_name "
            "   - Reference to company_name and that they're in evaluation phase "
            "   - 2-3 valuable industry insights or best practices "
            "   - Gentle mention of how our solution helps (not pushy) "
            "   - Soft CTA: welcome to reply with questions "
            "Keep content educational, warm, not aggressive. Use markdown for formatting."
        ))

        try:
            resp = self.llm.invoke([system_msg, human_msg])
            result = json.loads(resp.content)
            return result.get('subject', ''), result.get('content', '')
        except Exception as e:
            logger.error(f"LLM 生成培育邮件内容失败: {e}")
            # 降级到培育模板
            company_name = lead.get('company_name', '贵公司')
            contact_name = lead.get('contact_name', '负责人')
            intent_score = lead.get('intent_score', 0)

            subject = f"【培育跟进】{company_name} - 行业洞察与最佳实践"

            content = f"""
尊敬的 {contact_name} 先生/女士：

您好！

感谢您近期对我们产品的关注。{company_name} 作为行业内的活跃探索者（BANT评分: {intent_score}），
我们特别为您整理了以下行业洞察与最佳实践：

【行业趋势洞察】
✓ 数字化转型加速，80% 企业计划在未来6个月内启动相关项目
✓ 最佳实践显示：早期规划的企业实施成功率提升40%
✓ 专业团队的全程支持是项目成功的关键因素

【价值建议】
我们建议您可以：
• 评估当前业务流程中的优化空间
• 了解同行业成功案例的最佳实践
• 与专业顾问交流获取定制化建议

【下一步】
如您有任何疑问或想深入了解，欢迎随时回复本邮件，
我们的客户成功团队将为您提供专业解答。

此致
敬礼！

销售培育团队
"""
            return subject, content

    def send_nurturing_email(self, lead: dict) -> dict:
        """
        发送中等意向线索培育邮件（使用 LLM 生成个性化教育内容）

        Args:
            lead: 线索数据字典

        Returns:
            dict: 发送结果
        """
        if not lead.get('email'):
            return {"success": False, "message": "线索无邮箱地址", "status_code": 400}

        # 使用 LLM 生成培育邮件内容
        subject, content = self._generate_nurturing_content(lead)

        return self.send_email(lead['email'], subject, content)
