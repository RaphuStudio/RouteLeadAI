# BANTP 评分体系

> 从 **BANT（4维度，满分100）** 升级到 **BANTP（5维度，满分125）**
> 新增 **Position（职位影响力）** 维度，评分更精准。

---

## 一、评分流程

```
用户提交线索（raw_content）
        ↓
Classifier.classify() 调用 LLM（DeepSeek API）
        ↓
LLM 分析 raw_content，返回 JSON：
{
  "budget": 24,        // 预算 (0-25)
  "authority": 20,     // 决策权 (0-25)
  "need": 25,           // 需求 (0-25)
  "timeline": 25,      // 时间线 (0-25)
  "position": 22,        // 职位影响力 (0-25)
  "position_title": "技术总监",  // 职位名称
  "intent": 116         // 总分 (0-125)，LLM 同时返回
}
        ↓
更新 Lead 对象字段
        ↓
Router.route() 根据 intent_score 路由
        ↓
┌─────────┬──────────────┬───────────────┐
│ 分数段   │ Agent           │ 状态        │
├─────────┼──────────────┼───────────────┤
│ ≥100分   │ high_intent_agent │ contacted    │
│ 62-99分  │ normal_nurture_agent │ nurturing    │
│ <62分    │ longtail_nurture_agent │ new         │
└─────────┴──────────────┴───────────────┘
```

---

## 二、BANTP 五个维度详解

### 1. B — Budget（预算，满分 25）

| 分数 | 标准 | 示例 |
|------|------|------|
| 0 | 无预算 / 预算不明 | "暂无预算" |
| 10 | 预算有限 | "预算10万以内" |
| 15 | 预算中等 | "预算20-30万" |
| 20 | 预算充足 | "预算40-50万" |
| 25 | 预算充足且明确 | "预算50万以上，已批准" |

### 2. A — Authority（决策权，满分 25）

| 分数 | 标准 | 示例 |
|------|------|------|
| 0 | 无决策权 | "我只是了解，决策人是老板" |
| 10 | 有影响力但无决定权 | "我参与评估，最终老板定" |
| 15 | 共同决策 | "我和CTO一起决定" |
| 20 | 主要决策人 | "我是CTO，技术选型我说了算" |
| 25 | 完全决策权 | "决策权在我，可以直接签单" |

### 3. N — Need（需求，满分 25）

| 分数 | 标准 | 示例 |
|------|------|------|
| 0 | 无需求 | "只是随便看看" |
| 10 | 潜在需求 | "有考虑，但还没确定" |
| 15 | 明确需求 | "我们需要引入AI销售系统" |
| 20 | 强烈需求 | "急需解决销售效率问题" |
| 25 | 强烈需求且紧迫 | "必须在这个季度上线" |

### 4. T — Timeline（时间线，满分 25）

| 分数 | 标准 | 示例 |
|------|------|------|
| 0 | 无时间要求 | "时间还没定" |
| 10 | 6个月以上 | "明年再考虑" |
| 15 | 3-6个月 | "今年下半年计划上线" |
| 20 | 1-3个月 | "3个月内要决定" |
| 25 | 1个月内 | "急需，1个月内上线" |

### 5. P — Position（职位影响力，满分 25）⭐ 新增

| 分数 | 标准 | 示例 |
|------|------|------|
| 0 | 未知 / 无职位信息 | 未提供职位 |
| 10 | 普通员工 | "我是开发工程师" |
| 15 | 主管 / 经理 | "我是技术经理" |
| 20 | 总监 / VP | "我是技术总监" |
| 25 | CXO / 决策者 | "我是CTO" |

---

## 三、总分计算与路由规则

### 1. 总分计算公式

```python
intent_score = budget + authority + need + timeline + position
# 范围：0-125分
```

### 2. 路由阈值（满分 125）

| 分数段 | Agent | 状态 | 说明 |
|--------|-------|------|------|
| **≥100分** | `high_intent_agent` | `contacted` | 高意向（满分80%+） |
| **62-99分** | `normal_nurture_agent` | `nurturing` | 培育中（满分50%-79%） |
| **<62分** | `longtail_nurture_agent` | `new` | 长尾（满分50%以下） |

### 3. 与旧版 BANT 对比

| 项目 | BANT（旧） | BANTP（新） |
|------|-----------|-----------|
| 维度数量 | 4 | **5** ⭐ |
| 满分 | 100 | **125** |
| 高意向阈值 | ≥80 | **≥100** |
| 培育阈值 | 50-79 | **62-99** |
| 长尾阈值 | <50 | **<62** |
| Position 维度 | ❌ 无 | ✅ 有 |

---

## 四、LLM 提示词与返回格式

### 1. System Message（发给 LLM）

```
You are a sales-lead classifier using the BANTP framework (Budget, Authority, Need, Timeline, Position).
Score each component on a 0-25 scale.
Position is job title impact score (0-25). Also return position_title (job title name).
Total Intent is sum of 5 components (0-125).
Return ONLY a valid JSON object, no extra text.
```

### 2. Human Message（发给 LLM）

```
Lead data:
company_name=(not provided)
contact_name=(not provided)
position=(not provided)
raw_content=我是技术总监，公司需要考虑引入AI销售系统，预算40万左右，3个月内决定
Provide JSON with keys: budget, authority, need, timeline, position, position_title, intent.
```

### 3. LLM 返回格式（JSON）

```json
{
  "budget": 24,
  "authority": 20,
  "need": 25,
  "timeline": 25,
  "position": 22,
  "position_title": "技术总监",
  "intent": 116
}
```

- `position`：职位影响力分数（0-25），参与 `intent_score` 计算
- `position_title`：职位名称（如"技术总监"），存储到 `lead.position` 字段

---

## 五、代码实现位置

| 功能 | 文件 | 行数 |
|------|------|------|
| LLM 评分提示词 | `app/agents/classifier.py` | 108-120 |
| 评分后路由逻辑 | `app/agents/router.py` | 8-15 |
| 默认值设置 | `app/services/lead_service.py` | 27-39 |
| 前端分数颜色 | `frontend/src/components/LeadTable.vue` | 85-88 |
| Lead 数据模型 | `app/models/lead.py` | 24-48 |

---

## 六、测试验证

### 用例 1：技术总监（高意向）

**输入**：
```json
{
  "source": "website",
  "raw_content": "我是技术总监，公司需要考虑引入AI销售系统，预算40万左右，3个月内决定",
  "email": "test@example.com"
}
```

**输出**：
```json
{
  "position": "技术总监",      // ✅ LLM 解析出职位名称
  "budget_score": 24,
  "authority_score": 20,
  "need_score": 25,
  "timeline_score": 25,
  "intent_score": 116,         // ✅ 5维度之和：24+20+25+25+22=116
  "status": "contacted",
  "assigned_agent": "high_intent_agent"  // ✅ 116 ≥ 100，路由正确
}
```

### 用例 2：普通员工（培育中）

**输入**：
```json
{
  "source": "website",
  "raw_content": "我们对AI销售系统有兴趣，预算大概20万，需要和业务部门商量，预计3个月内会有决定",
  "email": "test2@example.com"
}
```

**预期输出**：
```json
{
  "position": "未提供",         // LLM 未解析到职位
  "intent_score": 约66,         // 预计在 62-99 区间
  "status": "nurturing",
  "assigned_agent": "normal_nurture_agent"
}
```

### 用例 3：无职位信息（长尾）

**输入**：
```json
{
  "source": "website",
  "raw_content": "测试默认值功能，不提供公司名和联系人",
  "email": "test3@example.com"
}
```

**预期输出**：
```json
{
  "position": "未提供",         // 使用默认值
  "intent_score": 0,            // 无有效信息
  "status": "new",
  "assigned_agent": "longtail_nurture_agent"
}
```

---

## 七、默认值规则

| 字段 | 默认值 | 优先级 |
|------|--------|--------|
| `position` | `"未提供"` | LLM 解析 → 默认值 |
| `company_name` | `"未知公司"` | API 提供 → 默认值 |
| `contact_name` | `"未知联系人"` | API 提供 → 默认值 |
| `email` | `"未提供"` | API 提供 → 默认值 |
| `phone` | `"未提供"` | API 提供 → 默认值 |
| `raw_content` | `"需要重新询问客户需求"` | API 提供 → 默认值 |

> **注意**：默认值在 `classify()` **之后**设置，确保 LLM 解析的字段优先。

---

## 八、前端显示

### 表格列顺序

```
公司 | 联系人 | 职位 | 邮箱 | 电话 | 评分 | 状态 | Agent | 时间 | 操作
```

### 分数颜色标识

| 分数段 | 颜色 | 说明 |
|--------|------|------|
| **≥100分** | 🔴 红色 | 高意向 |
| **62-99分** | 🔵 蓝色 | 培育中 |
| **<62分** | 🟣 紫色 | 长尾 |

---

## 九、相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目记忆 | `~/.claude/projects/.../MEMORY.md` | 简短说明，指向详细文档 |
| BANTP 评分详细文档 | `~/.claude/projects/.../BANTP_scoring.md` | 记忆目录版本 |
| **本项目文档** | `docs/BANTP_scoring.md` | **本文件**，项目内版本 |
| 前端迁移文档 | `frontend-migration.md` | Vue3+Vite 迁移记录 |

---

*最后更新：2026-05-06*
