from typing import Dict
from app.models.lead import Lead, LeadStatus


class LeadRouter:
    """根据意向分数把 lead 交给对应的 Agent"""

    async def route(self, lead: Lead) -> str:
        # BANTP 评分（满分125）：100+=高意向，62-99=培育，<62=长尾
        if lead.intent_score >= 100:
            return "high_intent_agent"
        elif 62 <= lead.intent_score < 100:
            return "normal_nurture_agent"
        else:
            return "longtail_nurture_agent"
