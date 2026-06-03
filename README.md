# RouteLeadAI 识途线索AI

> **智能辨线索成色，自动规划跟进坦途**

## 项目简介

RouteLeadAI（识途线索AI）是一个 **AI 驱动的销售线索智能跟进系统**，基于 **BANTP 评分框架** 自动对线索进行智能分级、路由与培育，通过多渠道触达（邮件、企业微信、钉钉）提升销售转化率。

**核心能力**

- **智能评分**：基于 BANTP 框架（Budget/Authority/Need/Timeline/Position，满分125）
- **自动路由**：高意向（≥100）→ 即时触达，中等（62-99）→ 培育，长尾（<62）→ 长期培育
- **多渠道触达**：邮件（Resend API）、企业微信机器人、钉钉机器人
- **异步处理**：Redis 队列 + Worker 后台任务
- **实时监控**：每5分钟检查线索状态，钉钉+企微双通道告警
- **前端可视化**：Vue 3 + Vite 模块化前端，实时查看线索状态

## 目录结构

```
ai_sales_followup_system/
├── .env                     # 运行时环境变量（含密钥，已加入 .gitignore）
├── .env.example             # 环境变量模板
├── .gitignore
├── requirements.txt         # Python 依赖
├── README.md               # 本文档
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 入口
│   ├── config.py                   # Pydantic Settings 配置
│   ├── log_utils.py                # 日志工具（ISO 8601 Formatter）
│   ├── worker.py                   # Worker 服务（Redis 队列消费）
│   │
│   ├── models/
│   │   └── lead.py                 # 线索 Pydantic 模型
│   │
│   ├── services/
│   │   ├── lead_service.py         # 线索处理主逻辑
│   │   ├── email_service.py        # Resend 邮件服务
│   │   ├── wework_service.py       # 企业微信 Webhook
│   │   └── dingtalk_service.py     # 钉钉 Webhook
│   │
│   └── agents/
│       ├── classifier.py           # BANTP 评分分类器（LLM）
│       ├── router.py               # 线索路由
│       ├── outreach_agent.py       # 高意向触达 Agent
│       ├── nurture_agent.py       # 中等意向培育 Agent
│       └── longtail_agent.py     # 长尾线索培育 Agent
│
├── frontend/                   # Vue 3 + Vite 前端
│   ├── Dockerfile              # 多阶段构建（Node → Nginx）
│   ├── nginx.conf              # Nginx 配置 + API 代理
│   ├── dist/                   # 构建产物（已加入 .gitignore）
│   ├── src/
│   │   ├── components/
│   │   │   ├── StatsPanel.vue      # 统计面板
│   │   │   ├── LeadTable.vue      # 线索表格
│   │   │   ├── LeadForm.vue       # 线索创建表单
│   │   │   └── LeadDetail.vue     # 线索详情
│   │   ├── main.js
│   │   └── App.vue
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── docs/
│   ├── BANTP_scoring.md        # BANTP 评分体系文档
│   ├── monitoring.md           # 系统监控和告警文档
│   └── BANT_scoring_flow.md   # BANT 评分流程图（历史）
│
├── asfs/                      # Python 虚拟环境（已加入 .gitignore）
├── api.log                    # FastAPI 业务日志（ISO 8601 格式）
├── worker.log                 # Worker 日志（ISO 8601 格式）
└── dump.rdb                  # Redis 数据快照（已加入 .gitignore）
```

## 快速开始

### 1. 环境准备

```bash
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system

# 创建 Python 虚拟环境（asfs）
python3 -m venv asfs

# 激活虚拟环境
source asfs/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入真实的密钥与配置
# 必填项：
#   - DEEPSEEK_API_KEY       （DeepSeek API Key）
#   - DEEPSEEK_API_BASE      （DeepSeek API 地址）
#   - LLM_MODEL              （模型名称，如 deepseek-v4-flash）
#   - RESEND_API_KEY        （Resend API Key）
#   - EMAIL_FROM            （发件邮箱）
#   - TEST_EMAIL            （测试邮箱）
#   - WECHAT_WEBHOOK_URL    （企业微信 Webhook URL）
#   - DINGTALK_WEBHOOK_URL  （钉钉 Webhook URL）
```

#### 前端依赖安装（本地部署）

```bash
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system/frontend

# 安装前端依赖
npm install
```

### 2. 启动服务

⚠️ **重要：所有服务必须在项目虚拟环境 `asfs` 中运行，且必须重定向日志以便跟踪错误**

#### 启动 Redis

```bash
redis-server --daemonize yes
```

#### 启动 FastAPI 服务

```bash
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system
source asfs/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
```

- 日志位置：`api.log`（ISO 8601 +08:00 格式）
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/`（根路径）

#### 启动 Worker 服务

```bash
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system
source asfs/bin/activate
nohup python -m app.worker > worker.log 2>&1 &
```

- 日志位置：`worker.log`（ISO 8601 +08:00 格式）
- 监控循环：每5分钟自动检查线索状态

#### 启动前端（Docker 部署自动启动）

```bash
# Docker 部署时前端自动启动，无需单独操作
# 访问地址：http://localhost:3000

# 本地开发模式（可选）
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system/frontend
npm install
nohup npm run dev > /tmp/vite.log 2>&1 &
```

- **Docker 部署**：前端通过 Nginx 提供静态文件，自动代理 `/api/` 到后端
- **本地开发**：Vite 开发服务器，支持热更新
- 访问地址：`http://localhost:3000`

### 3. 验证服务

```bash
# 检查 FastAPI 是否运行
curl http://localhost:8000/

# 查看线索统计
curl http://localhost:8000/stats

# 创建测试线索
curl -X POST http://localhost:8000/leads \
  -H "Content-Type: application/json" \
  -d '{
    "source": "website",
    "raw_content": "高意向线索：需要企业级CRM系统，预算充足，决策人直接联系",
    "company_name": "测试有限公司",
    "contact_name": "张经理",
    "position": "CEO",
    "email": "test@example.com"
  }'
```

### 4. Docker Compose 部署

⚠️ **前提：确保已创建 `.env` 文件并填入真实密钥**

#### 一键启动（后台运行）

```bash
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system

# 启动所有服务（FastAPI + Worker + Redis + 前端）
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app      # FastAPI 日志
docker-compose logs -f worker   # Worker 日志
docker-compose logs -f frontend # 前端 Nginx 日志
docker-compose logs -f redis    # Redis 日志

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

#### 服务说明

| 服务 | 说明 | 端口 |
|------|------|------|
| `app` | FastAPI 应用（自动构建镜像） | 8000 |
| `worker` | Worker 后台任务处理 | - |
| `frontend` | Vue 3 前端（Nginx 静态服务） | 3000→80 |
| `redis` | Redis 队列和存储 | 6379 |

#### 前端环境变量（可选）

| 变量名 | 说明 | 默认值 |
|--------|------|-------|
| `VITE_API_URL` | 后端 API 地址 | http://app:8000 |

> Docker 部署中前端通过 Nginx 自动代理 `/api/` 到后端，无需额外配置。

#### 环境变量

Docker Compose 会从 `.env` 文件自动加载环境变量，确保以下变量已配置：
- `DEEPSEEK_API_KEY` - DeepSeek API Key
- `RESEND_API_KEY` - Resend API Key
- `EMAIL_FROM` - 发件邮箱
- `WECHAT_WEBHOOK_URL` - 企业微信 Webhook URL
- `DINGTALK_WEBHOOK_URL` - 钉钉 Webhook URL

详细配置参考 `.env.example` 文件。

#### 数据持久化

- **Redis 数据**：通过 `redis-data` 命名卷持久化，容器重启后数据不丢失
- **日志文件**：`api.log` 和 `worker.log` 通过源码挂载自动同步

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径（健康检查） |
| POST | `/leads` | 创建新线索 |
| GET | `/leads` | 获取所有线索 |
| GET | `/leads/{id}` | 获取单个线索详情 |
| GET | `/stats` | 获取线索统计信息 |

## BANTP 评分体系

本项目使用 **BANTP 框架**（在 BANT 基础上增加 Position 维度）：

| 维度 | 说明 | 分值 |
|------|------|------|
| **B**udget（预算） | 客户预算充足程度 | 0-25 |
| **A**uthority（决策权） | 联系人在决策链中的位置 | 0-25 |
| **N**eed（需求） | 客户需求的明确和紧迫程度 | 0-25 |
| **T**imeline（时间线） | 采购决策的时间紧迫性 | 0-25 |
| **P**osition（职位） | 联系人的职位影响力 | 0-25 |

**总分：125 分**

### 路由规则

| 分数范围 | 分配 Agent | 处理方式 |
|---------|----------|---------|
| ≥100 分 | `high_intent_agent` | 即时触达（邮件+企微+钉钉） |
| 62-99 分 | `normal_nurture_agent` | 培育序列（软性触达+价值内容） |
| <62 分 | `longtail_nurture_agent` | 长期培育（低频率触达+品牌认知） |

详细文档：→ `docs/BANTP_scoring.md`

## 日志系统

所有业务日志统一使用 **ISO 8601 格式带时区标识**（CST +08:00）：

```
2026-05-06T21:27:40+08:00 [INFO] Lead processed successfully: xxx
2026-05-06T21:27:40+08:00 [INFO] [LeadService] After classification: lead xxx has intent_score 0
2026-05-06T21:15:03+08:00 [INFO] Processing lead xxx with agent longtail_nurture_agent
```

### 日志文件

| 文件/服务 | 用途 | 格式 |
|----------|------|------|
| `api.log` | FastAPI 业务日志 + LeadService 日志 + uvicorn 访问日志 | ISO 8601（业务日志） |
| `worker.log` | Worker 后台任务处理日志 | ISO 8601 +08:00 |
| `frontend` (Docker) | Nginx 访问日志（通过 `docker-compose logs -f frontend` 查看） | Nginx 默认格式 |
| `/tmp/vite.log` | Vite 开发服务器日志（本地部署） | Vite 默认格式 |

⚠️ **必须重定向日志**：启动服务时务必使用 `> api.log 2>&1` 或 `> worker.log 2>&1` 重定向，否则无法跟踪错误。

## 监控与告警

系统内置监控循环，每5分钟自动检查：

- 线索状态一致性（前端 vs 后端）
- 服务运行状态（FastAPI + Worker + Redis）
- 异常线索自动告警

### 告警渠道

- **钉钉机器人**：推送格式化消息（需配置 `DINGTALK_WEBHOOK_URL`）
- **企业微信机器人**：推送格式化消息（需配置 `WECHAT_WEBHOOK_URL`）

详细文档：→ `docs/monitoring.md`

## 环境变量说明

### 必填项

| 变量名 | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `DEEPSEEK_API_BASE` | DeepSeek API 地址（如 https://api.deepseek.com/v1） |
| `LLM_MODEL` | LLM 模型名称（如 deepseek-v4-flash） |
| `RESEND_API_KEY` | Resend API Key（邮件服务） |
| `EMAIL_FROM` | 发件邮箱地址 |
| `TEST_EMAIL` | 测试邮箱（Resend 测试模式限制） |
| `WECHAT_WEBHOOK_URL` | 企业微信机器人 Webhook URL |
| `DINGTALK_WEBHOOK_URL` | 钉钉机器人 Webhook URL |

### 选填项

| 变量名 | 说明 | 默认值 |
|--------|------|-------|
| `REDIS_HOST` | Redis 主机地址 | localhost |
| `REDIS_PORT` | Redis 端口 | 6379 |
| `REDIS_DB` | Redis 数据库编号 | 0 |

## 已放弃功能

- **短信渠道**：阿里云短信服务（alibabacloud-dysmsapi），因 SDK 未安装且需求优先级低

## 前端功能

Vue 3 + Vite 模块化前端，包含4个组件：

- **StatsPanel.vue**：统计面板（总线索数、各意向级别分布）
- **LeadTable.vue**：线索表格（支持 ISO 8601 时间显示、BANTP 分数颜色标识）
- **LeadForm.vue**：线索创建表单
- **LeadDetail.vue**：线索详情查看

## 开发与贡献

### 本地开发规范

- **代码风格**：遵循项目根目录 `CLAUDE.md` 与 `.claude/rules/` 中的规范
- **错误处理**：所有对外调用必须 try/except，记录详细日志
- **安全性**：**禁止硬编码密钥**，全部通过环境变量注入
- **日志格式**：使用 `logger` 调用 + ISO 8601 Formatter，禁止 `print()`

### 虚拟环境

项目使用 `asfs` 虚拟环境，所有 Python 命令必须在激活该环境后执行：

```bash
cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system
source asfs/bin/activate
```

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue 或 Pull Request。
