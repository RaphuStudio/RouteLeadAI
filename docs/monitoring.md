# 系统监测和告警

## 概述

为 AI 销售跟进系统实现**系统监测**和**告警推送**功能，确保前后端统计一致性、数据完整性，并在发现问题时通过钉钉/企业微信推送告警。

---

## 一、监控功能架构

```
定时监控（每5分钟）
        ↓
┌───────────────┬───────────────┐
│ 检查一致性       │ 检查数据完整性   │
└───────────────┴───────────────┘
        ↓                   ↓
   发现不一致?       发现数据问题?
        ↓ 是             ↓ 是
   发送告警消息（钉钉+企微）
```

---

## 二、监控内容

### 1. 前后端统计一致性检查（`check_consistency()`）

**检查项**：
- Redis 原始数据总数 vs `/stats` 接口返回总数
- 各分数段计数（高意向/中意向/低意向）
- 各 Agent 计数（high_intent_agent / normal_nurture_agent / longtail_nurture_agent）

**实现位置**：`app/worker.py` → `check_consistency()` 函数

**检查逻辑**：
```python
# 1. 从 Redis 原始数据计算真实统计
lead_ids = redis_client.smembers("lead:index")
real_total = 0
real_by_score = {"high": 0, "medium": 0, "low": 0}
real_by_agent = {"high_intent_agent": 0, "normal_nurture_agent": 0, "longtail_nurture_agent": 0}

for lead_id in lead_ids:
    data = redis_client.hgetall(f"lead:{lead_id}")
    if not data:
        issues.append(f"索引 {lead_id} 无对应数据")
        continue
    real_total += 1

    score = int(data.get("intent_score", 0))
    if score >= 100: real_by_score["high"] += 1
    elif score >= 62: real_by_score["medium"] += 1
    else: real_by_score["low"] += 1

    agent = data.get("assigned_agent", "")
    if agent in real_by_agent:
        real_by_agent[agent] += 1

# 2. 获取 /stats 接口统计
api_stats = get_stats()

# 3. 对比
if real_total != api_stats["total"]:
    issues.append(f"总数不一致：Redis={real_total}, API={api_stats['total']}")
# ... 类似检查各分数段和 Agent 计数
```

### 2. 数据完整性检查（`check_data_integrity()`）

**检查项**：
- `lead:index` 中的 ID 是否都有对应的 `lead:{id}` 哈希表
- 每条线索的必填字段（`id`、`source`、`status`、`assigned_agent`）
- `intent_score` 与 `assigned_agent` 是否匹配（如 score≥100 则 agent 应为 high_intent_agent）

**实现位置**：`app/worker.py` → `check_data_integrity()` 函数

**检查逻辑**：
```python
lead_ids = redis_client.smembers("lead:index")

for lead_id in lead_ids:
    lead_key = f"lead:{lead_id}"
    data = redis_client.hgetall(lead_key)

    if not data:
        issues.append(f"线索 {lead_id} 数据缺失")
        continue

    # 检查必填字段
    required_fields = ["id", "source", "status", "assigned_agent"]
    for field in required_fields:
        if not data.get(field):
            issues.append(f"线索 {lead_id} 缺少字段 {field}")

    # 检查 intent_score 与 assigned_agent 是否匹配
    try:
        score = int(data.get("intent_score", 0))
        agent = data.get("assigned_agent", "")

        if score >= 100 and agent != "high_intent_agent":
            issues.append(f"线索 {lead_id} 分数{score}≥100但agent={agent}")
        elif 62 <= score < 100 and agent != "normal_nurture_agent":
            issues.append(f"线索 {lead_id} 分数{score}在62-99但agent={agent}")
        elif score < 62 and agent != "longtail_nurture_agent":
            issues.append(f"线索 {lead_id} 分数{score}<62但agent={agent}")
    except ValueError:
        issues.append(f"线索 {lead_id} intent_score 格式错误")
```

---

## 三、告警推送

### 1. 推送渠道

| 渠道 | 服务类 | 方法 | 配置项 |
|------|--------|------|--------|
| **钉钉** | `DingTalkService` | `send_text()` | `DINGTALK_WEBHOOK_URL` 或 `DINGTALK_WEBHOOK + DINGTALK_SECRET` |
| **企业微信** | `WeWorkService` | `send_message()` | `WECHAT_WEBHOOK_URL` |

### 2. 告警消息格式

```
⚠️ 系统告警
[具体告警内容，每条问题一行]
```

### 3. 实现逻辑（`send_alert()` 函数）

```python
async def send_alert(message: str):
    """发送告警消息（钉钉+企微）"""
    alert_msg = f"⚠️ 系统告警\n{message}"

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
```

---

## 四、监控循环

### 1. 定时任务（`monitoring_loop()` 函数）

```python
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
```

### 2. 启动监控（`__main__` 部分）

```python
if __name__ == "__main__":
    async def main():
        # 启动监控任务
        asyncio.create_task(monitoring_loop())
        # 启动 worker 主循环
        await worker_loop()

    asyncio.run(main())
```

---

## 五、独立检查脚本

### 1. 脚本路径

```
/Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system/check_data_integrity.py
```

### 2. 功能

- 可以手动运行（不依赖 Worker 服务）
- 执行 4 项检查：
  1. 索引与数据一致性
  2. 分数与 Agent 匹配
  3. 必填字段完整性
  4. 与 API 统计对比
- 输出检查报告（控制台）

### 3. 使用方法

```bash
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system
asfs/bin/python check_data_integrity.py
```

### 4. 输出示例

```
==================================================
数据完整性检查报告
==================================================

=== 1. 检查索引与数据一致性 ===
✅ 所有 11 个线索数据完整

=== 2. 检查分数与 Agent 匹配 ===
✅ 所有 11 个线索分数与 Agent 匹配正确

=== 3. 检查必填字段 ===
✅ 所有 11 个线索必填字段完整

=== 4. 对比 Redis 与 API 统计 ===
Redis 原始数据：总数=11
  - 高意向（≥100）：3
  - 中意向（62-99）：5
  - 低意向（<62）：3

API /stats 接口：总数=11
  - 高意向：3
  - 中意向：5
  - 低意向：3

✅ Redis 与 API 统计完全一致

==================================================
检查总结
==================================================
✅ 通过 - 索引与数据一致性
✅ 通过 - 分数与 Agent 匹配
✅ 通过 - 必填字段完整性
✅ 通过 - Redis 与 API 统计一致

✅ 所有检查通过！数据完整性良好。
```

---

## 六、修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `app/worker.py` | 1. 添加导入（`get_stats`、`DingTalkService`、`WeWorkService`）<br>2. 初始化告警服务（`dingtalk_service`、`wework_service`）<br>3. 添加 `check_consistency()` 函数<br>4. 添加 `check_data_integrity()` 函数<br>5. 添加 `send_alert()` 函数<br>6. 添加 `monitoring_loop()` 函数<br>7. 修改 `__main__` 启动监控任务 |
| `check_data_integrity.py` | 新建独立检查脚本（手动运行） |
| `docs/monitoring.md` | 本文档，记录监控功能实现 |

---

## 七、告警场景示例

### 场景1：索引与数据不匹配

**告警消息**：
```
⚠️ 系统告警
数据完整性告警：
线索 123e4567-e89b-12d3-a456-426614174000 数据缺失
线索 987f6543-e21c-34d5-b678-426614174001 数据缺失
```

### 场景2：统计不一致

**告警消息**：
```
⚠️ 系统告警
统计一致性告警：
总数不一致：Redis=10, API=8
高意向计数不一致：Redis=3, API=2
```

### 场景3：分数与 Agent 不匹配

**告警消息**：
```
⚠️ 系统告警
数据完整性告警：
线索 123e4567-e89b-12d3-a456-426614174000 分数85≥100但agent=longtail_nurture_agent
```

---

## 八、相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 监控文档 | `docs/monitoring.md` | 本文档 |
| BANTP 评分体系 | `docs/BANTP_scoring.md` | 评分标准（满分125） |
| 项目记忆 | `~/.claude/projects/.../MEMORY.md` | 简短说明，指向详细文档 |

---

*最后更新：2026-05-06*
