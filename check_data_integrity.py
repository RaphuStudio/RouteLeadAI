#!/usr/bin/env python3
"""
数据完整性检查脚本
- 可以手动运行
- 检查 Redis 索引与数据是否匹配
- 检查 intent_score 与 assigned_agent 是否匹配
- 输出检查报告
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import redis
from app.config import Settings
from app.services.lead_service import get_stats

settings = Settings()
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True
)

def check_index_data_consistency():
    """检查 lead:index 与 lead:{id} 是否匹配"""
    print("\n=== 1. 检查索引与数据一致性 ===")

    lead_ids = redis_client.smembers("lead:index")
    print(f"索引中有 {len(lead_ids)} 个线索 ID")

    missing_data = []
    valid_count = 0

    for lead_id in lead_ids:
        data = redis_client.hgetall(f"lead:{lead_id}")
        if not data:
            missing_data.append(lead_id)
        else:
            valid_count += 1

    if missing_data:
        print(f"❌ 发现 {len(missing_data)} 个 ID 无对应数据：")
        for lid in missing_data[:5]:  # 只显示前5个
            print(f"  - {lid}")
        if len(missing_data) > 5:
            print(f"  ... 还有 {len(missing_data) - 5} 个")
    else:
        print(f"✅ 所有 {valid_count} 个线索数据完整")

    return len(missing_data) == 0, missing_data


def check_score_agent_match():
    """检查 intent_score 与 assigned_agent 是否匹配"""
    print("\n=== 2. 检查分数与 Agent 匹配 ===")

    lead_ids = redis_client.smembers("lead:index")

    mismatch = []
    valid_count = 0

    for lead_id in lead_ids:
        data = redis_client.hgetall(f"lead:{lead_id}")
        if not data:
            continue

        try:
            score = int(data.get("intent_score", 0))
            agent = data.get("assigned_agent", "")

            # BANTP 评分体系（满分125）：≥100=高意向，62-99=培育，<62=长尾
            if score >= 100 and agent != "high_intent_agent":
                mismatch.append((lead_id, score, agent, "应为 high_intent_agent"))
            elif 62 <= score < 100 and agent != "normal_nurture_agent":
                mismatch.append((lead_id, score, agent, "应为 normal_nurture_agent"))
            elif score < 62 and agent != "longtail_nurture_agent":
                mismatch.append((lead_id, score, agent, "应为 longtail_nurture_agent"))
            else:
                valid_count += 1

        except ValueError:
            mismatch.append((lead_id, data.get("intent_score"), "格式错误", "intent_score 格式错误"))

    if mismatch:
        print(f"❌ 发现 {len(mismatch)} 个不匹配：")
        for lid, score, agent, expected in mismatch[:10]:  # 只显示前10个
            print(f"  - {lid[:8]}：分数={score}，agent={agent}，{expected}")
        if len(mismatch) > 10:
            print(f"  ... 还有 {len(mismatch) - 10} 个")
    else:
        print(f"✅ 所有 {valid_count} 个线索分数与 Agent 匹配正确")

    return len(mismatch) == 0, mismatch


def check_required_fields():
    """检查必填字段"""
    print("\n=== 3. 检查必填字段 ===")

    lead_ids = redis_client.smembers("lead:index")

    missing_fields = []
    valid_count = 0

    required_fields = ["id", "source", "status", "assigned_agent", "intent_score"]

    for lead_id in lead_ids:
        data = redis_client.hgetall(f"lead:{lead_id}")
        if not data:
            continue

        missing = []
        for field in required_fields:
            if not data.get(field):
                missing.append(field)

        if missing:
            missing_fields.append((lead_id, missing))
        else:
            valid_count += 1

    if missing_fields:
        print(f"❌ 发现 {len(missing_fields)} 个线索缺少必填字段：")
        for lid, fields in missing_fields[:10]:
            print(f"  - {lid[:8]}：缺少 {', '.join(fields)}")
        if len(missing_fields) > 10:
            print(f"  ... 还有 {len(missing_fields) - 10} 个")
    else:
        print(f"✅ 所有 {valid_count} 个线索必填字段完整")

    return len(missing_fields) == 0, missing_fields


def compare_with_api_stats():
    """对比 Redis 原始数据与 /stats 接口统计"""
    print("\n=== 4. 对比 Redis 与 API 统计 ===")

    # 从 Redis 原始数据计算
    lead_ids = redis_client.smembers("lead:index")
    real_total = 0
    real_by_score = {"high": 0, "medium": 0, "low": 0}

    for lead_id in lead_ids:
        data = redis_client.hgetall(f"lead:{lead_id}")
        if not data:
            continue
        real_total += 1

        score = int(data.get("intent_score", 0))
        if score >= 100:
            real_by_score["high"] += 1
        elif score >= 62:
            real_by_score["medium"] += 1
        else:
            real_by_score["low"] += 1

    # 获取 API 统计
    api_stats = get_stats()

    print(f"Redis 原始数据：总数={real_total}")
    print(f"  - 高意向（≥100）：{real_by_score['high']}")
    print(f"  - 中意向（62-99）：{real_by_score['medium']}")
    print(f"  - 低意向（<62）：{real_by_score['low']}")

    print(f"\nAPI /stats 接口：总数={api_stats['total']}")
    print(f"  - 高意向：{api_stats['by_intent']['high (80+)']}")
    print(f"  - 中意向：{api_stats['by_intent']['medium (50-79)']}")
    print(f"  - 低意向：{api_stats['by_intent']['low (<50)']}")

    issues = []
    if real_total != api_stats["total"]:
        issues.append(f"总数不一致：Redis={real_total}, API={api_stats['total']}")
    if real_by_score["high"] != api_stats["by_intent"]["high (80+)"]:
        issues.append(f"高意向计数不一致")
    if real_by_score["medium"] != api_stats["by_intent"]["medium (50-79)"]:
        issues.append(f"中意向计数不一致")
    if real_by_score["low"] != api_stats["by_intent"]["low (<50)"]:
        issues.append(f"低意向计数不一致")

    if issues:
        print(f"\n❌ 发现 {len(issues)} 个不一致：")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ Redis 与 API 统计完全一致")

    return len(issues) == 0, issues


def main():
    """主函数"""
    print("="*50)
    print("数据完整性检查报告")
    print("="*50)

    results = []

    # 1. 检查索引与数据一致性
    ok1, _ = check_index_data_consistency()
    results.append(("索引与数据一致性", ok1))

    # 2. 检查分数与 Agent 匹配
    ok2, _ = check_score_agent_match()
    results.append(("分数与 Agent 匹配", ok2))

    # 3. 检查必填字段
    ok3, _ = check_required_fields()
    results.append(("必填字段完整性", ok3))

    # 4. 对比 API 统计
    ok4, _ = compare_with_api_stats()
    results.append(("Redis 与 API 统计一致", ok4))

    # 总结
    print("\n" + "="*50)
    print("检查总结")
    print("="*50)

    all_ok = True
    for name, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"{status} - {name}")
        if not ok:
            all_ok = False

    print("\n" + "="*50)
    if all_ok:
        print("✅ 所有检查通过！数据完整性良好。")
        return 0
    else:
        print("❌ 发现数据完整性问题，请检查上方详情。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
