"""
Nurture Scheduler - 定期提醒调度器

功能：
1. 扫描 Redis 中超过 30 天未培育的线索
2. 重新发送培育邮件给客户
3. 通知销售团队（企微/钉钉）

使用方式：
- 定时任务：cron 每月执行一次
- 或常驻进程：while True + sleep(86400) 每日检查
"""

import time
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
from app.config import Settings
from app.services.email_service import EmailService
from app.services.wework_service import WeWorkService
from app.services.dingtalk_service import DingTalkService

settings = Settings()

# Redis 连接
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True
)

# 培育间隔（秒）：30 天
NURTURE_INTERVAL = 30 * 24 * 60 * 60


def scan_nurture_leads():
    """扫描需要培育的线索"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始扫描需要培育的线索...")

    # 获取所有正在培育的线索 ID
    lead_ids = redis_client.hkeys("nurture:last_sent")
    print(f"  当前培育中的线索数: {len(lead_ids)}")

    current_time = int(time.time())
    needs_nurture = []

    for lead_id in lead_ids:
        last_sent = redis_client.hget("nurture:last_sent", lead_id)
        if not last_sent:
            continue

        last_sent = int(float(last_sent))
        if current_time - last_sent >= NURTURE_INTERVAL:
            needs_nurture.append(lead_id)

    print(f"  需要培育的线索数: {len(needs_nurture)}")
    return needs_nurture


def process_nurture_lead(lead_id: str):
    """处理单个线索的定期培育"""
    # 从 Redis 获取线索信息
    lead_key = f"nurture:lead:{lead_id}"
    lead_data = redis_client.hgetall(lead_key)

    if not lead_data:
        print(f"  [WARN] 线索 {lead_id} 数据不存在，跳过")
        return False

    # 构造线索字典
    lead = {
        "id": lead_id,
        "company_name": lead_data.get("company_name", ""),
        "contact_name": lead_data.get("contact_name", ""),
        "email": lead_data.get("email", ""),
        "intent_score": int(lead_data.get("intent_score", 0)),
    }

    print(f"  处理线索: {lead['company_name']} ({lead['contact_name']})")
    print(f"  意向评分: {lead['intent_score']}")

    success = True

    # 1. 发送培育邮件给客户
    if lead.get("email"):
        try:
            email_service = EmailService()
            result = email_service.send_nurturing_email(lead)
            if result.get("success"):
                print(f"  ✅ 培育邮件发送成功: {lead['email']}")
            else:
                print(f"  ❌ 培育邮件发送失败: {result.get('message')}")
                success = False
        except Exception as e:
            print(f"  ❌ 培育邮件发送异常: {e}")
            success = False
    else:
        print(f"  ⚠️ 线索无邮箱，跳过邮件发送")

    # 2. 通知销售团队（企微）
    try:
        wework_service = WeWorkService()
        content = _generate_sales_notification(lead, is_periodic=True)
        result = wework_service.send_message(content)
        if result.get("success"):
            print(f"  ✅ 企微销售通知发送成功")
        else:
            print(f"  ⚠️ 企微销售通知发送失败: {result.get('message')}")
    except Exception as e:
        print(f"  ⚠️ 企微销售通知异常: {e}")

    # 3. 通知销售团队（钉钉）
    try:
        dingtalk_service = DingTalkService()
        content = _generate_dingtalk_sales_notification(lead, is_periodic=True)
        result = dingtalk_service.send_text(content)
        if result.get("success"):
            print(f"  ✅ 钉钉销售通知发送成功")
        else:
            print(f"  ⚠️ 钉钉销售通知发送失败: {result.get('message')}")
    except Exception as e:
        print(f"  ⚠️ 钉钉销售通知异常: {e}")

    # 4. 更新培育时间
    if success and lead.get("email"):
        redis_client.hset("nurture:last_sent", lead_id, int(time.time()))
        print(f"  ✅ 已更新培育时间")

    return success


def _generate_sales_notification(lead: dict, is_periodic: bool = False) -> str:
    """生成面向销售团队的通知（企微）"""
    periodic_tag = "【定期培育】" if is_periodic else "【培育中】"
    company = lead.get("company_name", "贵公司")
    contact = lead.get("contact_name", "负责人")
    score = lead.get("intent_score", 0)

    return (
        f"{periodic_tag} 客户培育提醒\n"
        f"公司：{company}\n"
        f"联系人：{contact}\n"
        f"意向评分：{score}（培育中）\n"
        f"已自动发送定期培育邮件（价值内容/行业洞察）\n"
        f"建议话术：\n"
        f"  「{contact}，上次交流后我们整理了最新的行业案例，特别适合{company}的情况...」\n"
        f"  「{contact}您好，关于您关心的自动化流程，我们刚发布了新的实践指南...」\n"
        f"销售可适时介入，建议本月内联系✅"
    )


def _generate_dingtalk_sales_notification(lead: dict, is_periodic: bool = False) -> str:
    """生成面向销售团队的通知（钉钉）"""
    periodic_tag = "【定期培育】" if is_periodic else "【培育中】"
    company = lead.get("company_name", "贵公司")
    contact = lead.get("contact_name", "负责人")
    score = lead.get("intent_score", 0)

    return (
        f"AI Sales {periodic_tag}\n"
        f"公司：{company}\n"
        f"联系人：{contact}\n"
        f"意向评分：{score}（培育中）\n"
        f"已自动发送定期培育邮件（价值内容/行业洞察）\n"
        f"建议话术：\n"
        f"  「{contact}，看到{company}在评估CRM，我们最近有个客户案例...」\n"
        f"  「{contact}您好，关于您关心的自动化流程，我们整理了...」\n"
        f"销售可适时介入，建议本月内联系✅"
    )


def run_once():
    """执行一次扫描（可用于 cron）"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Nurture Scheduler 开始执行...")
    print()

    leads = scan_nurture_leads()

    if not leads:
        print("没有需要培育的线索。")
        return

    print(f"\n开始处理 {len(leads)} 个线索...")
    success_count = 0

    for lead_id in leads:
        print(f"\n--- 处理线索 {lead_id} ---")
        if process_nurture_lead(lead_id):
            success_count += 1

    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行完成")
    print(f"  总计: {len(leads)}, 成功: {success_count}, 失败: {len(leads) - success_count}")


def run_daemon():
    """作为常驻进程运行（每天检查一次）"""
    print("Nurture Scheduler 常驻模式启动...")
    print("每天检查一次需要培育的线索\n")

    while True:
        try:
            run_once()
            print(f"\n下次检查时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + 86400))}")
            time.sleep(86400)  # 24 小时
        except KeyboardInterrupt:
            print("\n调度器已停止。")
            break
        except Exception as e:
            print(f"执行异常: {e}")
            time.sleep(3600)  # 异常后 1 小时重试


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Nurture Scheduler - 定期培育调度器")
    parser.add_argument("--daemon", action="store_true", help="常驻模式（每天检查）")
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    else:
        run_once()
