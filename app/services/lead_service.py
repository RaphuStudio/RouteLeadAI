from typing import Any, List, Optional
import json
import redis
import asyncio
import logging
from datetime import datetime
from app.models.lead import Lead
from app.agents.classifier import LeadClassifier
from app.agents.router import LeadRouter
from app.config import Settings
from app.log_utils import ISO8601Formatter

logger = logging.getLogger("lead_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(ISO8601Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

settings = Settings()
redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db, decode_responses=True)
classifier = LeadClassifier()
router = LeadRouter()

# 阈值常量（与 classifier.py 保持一致）
HIGH_INTENT_THRESHOLD = 100   # >=100 高意向
NURTURE_THRESHOLD_MIN = 62     # 62-99 培育


async def process_lead(lead: Lead) -> Lead:
    """
    Process an incoming lead: classify, route, and push to appropriate queue.
    """
    # Classify lead (compute intent score, assign agent)
    lead = await classifier.classify(lead)
    logger.info(f"[LeadService] After classification: lead {lead.id} has intent_score {lead.intent_score}")
    # Determine target agent
    target_agent = await router.route(lead)
    lead.assigned_agent = target_agent
    logger.info(f"[LeadService] Routing lead {lead.id} to agent: {target_agent}")
    # 为空的字段设置默认值（在 classify 之后，确保 LLM 解析的字段优先）
    if not lead.company_name:
        lead.company_name = "未知公司"
    if not lead.contact_name:
        lead.contact_name = "未知联系人"
    if not lead.position:
        lead.position = "未提供"
    if not lead.raw_content:
        lead.raw_content = "需要重新询问客户需求"

    # Save lead to Redis
    _save_lead(lead)
    # Push to Redis queue as JSON string
    task = {
        "lead_id": lead.id,
        "agent": target_agent,
        "payload": lead.model_dump()
    }
    logger.info(f"[LeadService] Pushing task to Redis: {task}")
    # Use synchronous Redis call in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: redis_client.lpush("lead_queue", json.dumps(task, default=str)))
    logger.info(f"[LeadService] Task pushed to lead_queue for lead {lead.id}")
    return lead


def _save_lead(lead: Lead):
    """Save lead to Redis for query"""
    try:
        lead_key = f"lead:{lead.id}"
        redis_client.hset(lead_key, mapping={
            "id": lead.id,
            "source": lead.source,
            "raw_content": lead.raw_content or "",
            "company_name": lead.company_name or "未知公司",
            "contact_name": lead.contact_name or "未知联系人",
            "position": lead.position or "未提供",
            "email": lead.email or "",
            "phone": lead.phone or "",
            "budget_score": str(lead.budget_score),
            "authority_score": str(lead.authority_score),
            "need_score": str(lead.need_score),
            "timeline_score": str(lead.timeline_score),
            "intent_score": str(lead.intent_score),
            "status": lead.status,
            "assigned_agent": lead.assigned_agent or "",
            "created_at": lead.created_at.isoformat() if lead.created_at else "",
        })
        # Add to lead index set
        redis_client.sadd("lead:index", lead.id)
        logger.info(f"[LeadService] Lead {lead.id} saved to Redis")
    except Exception as e:
        logger.error(f"[LeadService] Failed to save lead {lead.id}: {e}")


def get_all_leads() -> List[dict]:
    """Get all leads from Redis"""
    try:
        lead_ids = redis_client.smembers("lead:index")
        leads = []
        for lead_id in lead_ids:
            lead_key = f"lead:{lead_id}"
            data = redis_client.hgetall(lead_key)
            if data:
                leads.append(data)
        # Sort by created_at descending
        leads.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return leads
    except Exception as e:
        logger.error(f"[LeadService] Failed to get leads: {e}")
        return []


def get_lead_by_id(lead_id: str) -> Optional[dict]:
    """Get single lead by ID"""
    try:
        lead_key = f"lead:{lead_id}"
        data = redis_client.hgetall(lead_key)
        return data if data else None
    except Exception as e:
        logger.error(f"[LeadService] Failed to get lead {lead_id}: {e}")
        return None


def get_stats() -> dict:
    """Get lead statistics"""
    try:
        leads = get_all_leads()
        total = len(leads)

        # Count by intent score range（满分125：100+=高意向，62-99=培育，<62=长尾）
        high = sum(1 for l in leads if int(l.get("intent_score", 0)) >= HIGH_INTENT_THRESHOLD)
        medium = sum(1 for l in leads if NURTURE_THRESHOLD_MIN <= int(l.get("intent_score", 0)) < HIGH_INTENT_THRESHOLD)
        low = sum(1 for l in leads if int(l.get("intent_score", 0)) < NURTURE_THRESHOLD_MIN)

        # Count by agent
        high_agent = sum(1 for l in leads if l.get("assigned_agent") == "high_intent_agent")
        nurture_agent = sum(1 for l in leads if l.get("assigned_agent") == "normal_nurture_agent")
        longtail_agent = sum(1 for l in leads if l.get("assigned_agent") == "longtail_nurture_agent")

        return {
            "total": total,
            "by_intent": {
                "high (100+)": high,
                "medium (62-99)": medium,
                "low (<62)": low,
            },
            "by_agent": {
                "high_intent_agent": high_agent,
                "normal_nurture_agent": nurture_agent,
                "longtail_nurture_agent": longtail_agent,
            }
        }
    except Exception as e:
        logger.error(f"[LeadService] Failed to get stats: {e}")
        return {"total": 0, "by_intent": {}, "by_agent": {}}
