import asyncio
import json
import sys
import os
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

# Add the project root to the sys.path so that we can import from the 'app' package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
import asyncpg

from app.config import Settings
from app.agents.classifier import LeadClassifier
from app.agents.router import LeadRouter
from app.agents.outreach_agent import OutreachAgent
from app.agents.nurture_agent import NurtureAgent
from app.agents.longtail_agent import LongTailNurtureAgent
from app.models.lead import Lead
from app.services.lead_service import get_stats
from app.services.dingtalk_service import DingTalkService
from app.services.wework_service import WeWorkService
from app.log_utils import ISO8601Formatter

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(ISO8601Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
# 防止重复添加 handler
logger.propagate = False

settings = Settings()
redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db, password=settings.redis_password or None, decode_responses=True)

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
            max_size=2,
        )
    return _pool

# 初始化告警服务
dingtalk_service = DingTalkService()
wework_service = WeWorkService()

classifier = LeadClassifier()
router = LeadRouter()


async def process_lead_task(task_data: dict):
    lead_dict = task_data.get("payload")
    if not lead_dict:
        return
    lead = Lead(**lead_dict)
    logger.info(f"Processing lead {lead.id} with agent {task_data.get('agent')}")

    # Trigger the appropriate agent based on task_data["agent"]
    agent_name = task_data.get("agent")
    if agent_name == "high_intent_agent":
        trigger = OutreachAgent()
        # Execute outreach synchronously (it's not async in our current impl)
        trigger.execute(lead.model_dump())
        lead.assigned_agent = "high_intent_agent"
        lead.status = "contacted"
    elif agent_name == "normal_nurture_agent":
        trigger = NurtureAgent()
        # Execute nurturing campaign
        trigger.execute(lead.model_dump())
        lead.assigned_agent = "normal_nurture_agent"
        lead.status = "nurturing"
    elif agent_name == "longtail_nurture_agent":
        agent = LongTailNurtureAgent()
        # LongTail agent 是同步的
        agent.execute(lead.model_dump())
        lead.assigned_agent = "longtail_nurture_agent"
        lead.status = "nurturing"
    else:
        # 未知 agent，记录日志
        logger.warning(f"Unknown or unimplemented agent: {agent_name}")

    # Save updated lead back to PostgreSQL
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE leads SET status=$1, assigned_agent=$2, updated_at=NOW() WHERE id=$3",
                lead.status, lead.assigned_agent or "", lead.id)
        logger.info(f"[Worker] Lead {lead.id} updated in PostgreSQL: status={lead.status}, agent={lead.assigned_agent}")
    except Exception as e:
        logger.error(f"[Worker] Failed to update lead {lead.id} in PostgreSQL: {e}")

    logger.info(f"Lead {lead.id} processed.")





async def check_consistency() -> dict:
    """从 PostgreSQL 检查数据一致性"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM leads")
            high = await conn.fetchval("SELECT COUNT(*) FROM leads WHERE intent_score >= 100")
            medium = await conn.fetchval("SELECT COUNT(*) FROM leads WHERE intent_score >= 62 AND intent_score < 100")
            low = await conn.fetchval("SELECT COUNT(*) FROM leads WHERE intent_score < 62")
            rows = await conn.fetch("SELECT assigned_agent, COUNT(*) AS cnt FROM leads GROUP BY assigned_agent")

        by_agent = {r["assigned_agent"]: r["cnt"] for r in rows}
        api_stats = await get_stats()

        issues = []
        if total != api_stats["total"]:
            issues.append(f"总数不一致：PG={total}, API={api_stats['total']}")
        if high != api_stats["by_intent"]["high (100+)"]:
            issues.append(f"高意向不一致：PG={high}, API={api_stats['by_intent']['high (100+)']}")
        if medium != api_stats["by_intent"]["medium (62-99)"]:
            issues.append(f"中意向不一致：PG={medium}, API={api_stats['by_intent']['medium (62-99)']}")
        if low != api_stats["by_intent"]["low (<62)"]:
            issues.append(f"低意向不一致：PG={low}, API={api_stats['by_intent']['low (<62)']}")

        return {"success": len(issues) == 0, "issues": issues}
    except Exception as e:
        logger.exception("检查一致性失败")
        return {"success": False, "issues": [f"检查异常: {str(e)}"]}


async def check_data_integrity() -> dict:
    """从 PostgreSQL 检查数据完整性"""
    issues = []
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, intent_score, assigned_agent FROM leads")

        for row in rows:
            score = row["intent_score"]
            agent = row["assigned_agent"]
            if score >= 100 and agent != "high_intent_agent":
                issues.append(f"线索 {row['id'][:8]} 分数{score}≥100但agent={agent}")
            elif 62 <= score < 100 and agent != "normal_nurture_agent":
                issues.append(f"线索 {row['id'][:8]} 分数{score}在62-99但agent={agent}")
            elif score < 62 and agent != "longtail_nurture_agent":
                issues.append(f"线索 {row['id'][:8]} 分数{score}<62但agent={agent}")

        return {"success": len(issues) == 0, "issues": issues, "total": len(rows)}
    except Exception as e:
        logger.exception("检查数据完整性失败")
        return {"success": False, "issues": [f"检查异常: {str(e)}"]}


async def send_alert(message: str):
    """发送告警消息（钉钉+企微）"""
    # 钉钉机器人关键词：消息必须包含 "AI Sales" 才能通过
    alert_msg = f"AI Sales\n⚠️ 系统告警\n{message}"
    
    # 钉钉告警
    ding_result = dingtalk_service.send_text(alert_msg)
    if ding_result.get("success"):
        logger.info("钉钉告警发送成功")
    else:
        logger.error(f"钉钉告警发送失败: {ding_result}")
    
    # 企微告警
    wework_result = wework_service.send_message(alert_msg)
    if wework_result.get("success"):
        logger.info("企微告警发送成功")
    else:
        logger.error(f"企微告警发送失败: {wework_result}")


async def monitoring_loop():
    """监控循环（每5分钟检查一次）"""
    logger.info("监控服务启动，每5分钟检查一次")
    
    while True:
        await asyncio.sleep(300)  # 5分钟
        
        # 检查一致性
        consistency = await check_consistency()
        if not consistency["success"]:
            msg = "统计一致性告警：\n" + "\n".join(consistency["issues"])
            logger.warning(msg)
            await send_alert(msg)
        
        # 检查数据完整性
        integrity = await check_data_integrity()
        if not integrity["success"]:
            msg = "数据完整性告警：\n" + "\n".join(integrity["issues"])
            logger.warning(msg)
            await send_alert(msg)
        
        logger.info(f"监控检查完成：{consistency.get('real_stats', {}).get('total', 0)} 条线索有效")




async def worker_loop():
    """Worker 主循环，处理 Redis 队列中的任务"""
    logger.info("Worker started, waiting for tasks...")
    loop = asyncio.get_event_loop()
    while True:
        # Blocking pop from Redis list (run in executor to avoid blocking)
        task_json = await loop.run_in_executor(None, lambda: redis_client.brpop("lead_queue", timeout=5))
        if task_json:
            task = json.loads(task_json[1])
            await process_lead_task(task)

if __name__ == "__main__":
    async def main():
        # 启动监控任务
        asyncio.create_task(monitoring_loop())
        # 启动 worker 主循环
        await worker_loop()

    asyncio.run(main())