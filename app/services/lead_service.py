from typing import Any, List, Optional
import json
import redis
import asyncio
import asyncpg
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

# Redis 仅用于任务队列
redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db, password=settings.redis_password or None, decode_responses=True)
classifier = LeadClassifier()
router = LeadRouter()

# 阈值常量
HIGH_INTENT_THRESHOLD = 100
NURTURE_THRESHOLD_MIN = 62

# PostgreSQL 连接池
_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.pg_host,
            port=settings.pg_port,
            database=settings.pg_database,
            user=settings.pg_user,
            password=settings.pg_password,
            min_size=1,
            max_size=5,
        )
    return _pool


INSERT_SQL = """
    INSERT INTO leads (id, source, raw_content, company_name, contact_name, position,
                       email, phone, budget_score, authority_score, need_score,
                       timeline_score, intent_score, status, assigned_agent, created_at)
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
    ON CONFLICT (id) DO UPDATE SET
        status=EXCLUDED.status, assigned_agent=EXCLUDED.assigned_agent,
        updated_at=NOW()
"""

SELECT_ALL_SQL = "SELECT * FROM leads ORDER BY created_at DESC"
SELECT_BY_ID_SQL = "SELECT * FROM leads WHERE id = $1"
STATS_BY_INTENT_SQL = """
    SELECT
        COUNT(*) FILTER (WHERE intent_score >= $1) AS high,
        COUNT(*) FILTER (WHERE intent_score >= $2 AND intent_score < $1) AS medium,
        COUNT(*) FILTER (WHERE intent_score < $2) AS low
    FROM leads
"""
STATS_BY_AGENT_SQL = """
    SELECT assigned_agent, COUNT(*) AS cnt FROM leads GROUP BY assigned_agent
"""


def _row_to_dict(row) -> dict:
    """将 asyncpg 行转为 dict"""
    return dict(row) if row else None


async def process_lead(lead: Lead) -> Lead:
    """处理线索：分类、路由、持久化到 PG、推入 Redis 队列"""
    # 分类（LLM 打分）
    lead = await classifier.classify(lead)
    logger.info(f"[LeadService] After classification: lead {lead.id} has intent_score {lead.intent_score}")

    # 路由
    target_agent = await router.route(lead)
    lead.assigned_agent = target_agent
    logger.info(f"[LeadService] Routing lead {lead.id} to agent: {target_agent}")

    # 默认值
    if not lead.company_name: lead.company_name = "未知公司"
    if not lead.contact_name: lead.contact_name = "未知联系人"
    if not lead.position: lead.position = "未提供"
    if not lead.raw_content: lead.raw_content = "需要重新询问客户需求"

    # 保存到 PostgreSQL
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(INSERT_SQL,
            lead.id, lead.source, lead.raw_content, lead.company_name,
            lead.contact_name, lead.position, lead.email or "", lead.phone or "",
            lead.budget_score, lead.authority_score, lead.need_score,
            lead.timeline_score, lead.intent_score, lead.status,
            lead.assigned_agent, lead.created_at)
    logger.info(f"[LeadService] Lead {lead.id} saved to PostgreSQL")

    # 推入 Redis 队列（异步任务）
    task = {"lead_id": lead.id, "agent": target_agent, "payload": lead.model_dump()}
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: redis_client.lpush("lead_queue", json.dumps(task, default=str)))
    logger.info(f"[LeadService] Task pushed to lead_queue for lead {lead.id}")

    return lead


async def get_all_leads() -> List[dict]:
    """获取所有线索"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(SELECT_ALL_SQL)
            return [_row_to_dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[LeadService] Failed to get leads: {e}")
        return []


async def get_lead_by_id(lead_id: str) -> Optional[dict]:
    """获取单条线索"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(SELECT_BY_ID_SQL, lead_id)
            return _row_to_dict(row)
    except Exception as e:
        logger.error(f"[LeadService] Failed to get lead {lead_id}: {e}")
        return None


async def get_stats() -> dict:
    """获取统计信息"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            intent_row = await conn.fetchrow(STATS_BY_INTENT_SQL, HIGH_INTENT_THRESHOLD, NURTURE_THRESHOLD_MIN)
            agent_rows = await conn.fetch(STATS_BY_AGENT_SQL)
            total_row = await conn.fetchval("SELECT COUNT(*) FROM leads")

        by_agent = {}
        for r in agent_rows:
            by_agent[r["assigned_agent"]] = r["cnt"]

        return {
            "total": total_row,
            "by_intent": {
                "high (100+)": intent_row["high"],
                "medium (62-99)": intent_row["medium"],
                "low (<62)": intent_row["low"],
            },
            "by_agent": by_agent,
        }
    except Exception as e:
        logger.error(f"[LeadService] Failed to get stats: {e}")
        return {"total": 0, "by_intent": {}, "by_agent": {}}
