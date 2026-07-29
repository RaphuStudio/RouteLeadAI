# RouteLeadAI 识途线索AI

> **智能辨线索成色，自动规划跟进坦途**

AI 驱动的销售线索智能跟进系统。基于 **BANTP 评分框架** 自动分级、路由与多渠道触达。

## 操作流程

用户在页面上提交一条线索后，系统自动完成：

```
填写表单 → 提交
  │
  ├─ 1. LLM 分析原始诉求 → BANTP 五维评分
  │    （如"预算50万，我是总监，有决策权"→ 高意向高分）
  │
  ├─ 2. 计算总分 → 自动路由：
  │     ≥100 高意向 → 邮件+企微+钉钉 即时通知销售
  │     62-99 中等   → 培育邮件 + 企微通知
  │     <62 长尾     → 仅一封欢迎邮件
  │
  ├─ 3. 存入 PostgreSQL → 页面自动刷新
  └─ 4. 可查看 BANTP 评分明细
```

## 前端页面
| 组件 | 功能 |
|------|------|
| 统计面板 | 总线索数 / 高意向 / 培育中 / 长尾 |
| 线索表格 | 线索列表，评分/状态/Agent |
| 添加表单 | 弹窗表单：来源/公司/联系人/邮箱/电话/原始诉求 |
| 详情弹窗 | BANTP 五维评分明细 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd frontend && npm install

# 2. 配置环境变量
cp .env.example .env   # 编辑填入真实密钥

# 3. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
python -m app.worker
cd frontend && npm run dev
```

## BANTP 评分体系

| 维度 | 说明 | 分值 |
|------|------|------|
| **B**udget（预算） | 客户预算充足程度 | 0-25 |
| **A**uthority（决策权） | 联系人在决策链中的位置 | 0-25 |
| **N**eed（需求） | 客户需求的明确和紧迫程度 | 0-25 |
| **T**imeline（时间线） | 采购决策的时间紧迫性 | 0-25 |
| **P**osition（职位） | 联系人的职位影响力 | 0-25 |

**总分 125 分**：≥100 即时触达 | 62-99 培育 | <62 长尾培育

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api` | 健康检查 |
| GET | `/api/health` | 健康检查 |
| POST | `/api/leads` | 创建新线索 |
| GET | `/api/leads` | 获取所有线索 |
| GET | `/api/leads/{id}` | 获取线索详情 |
| GET | `/api/stats` | 线索统计 |

## 环境变量

LLM 配置（改后 `systemctl restart route-lead-app` 生效）：

| 变量 | 说明 | 当前值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供者 | `qwen`（DashScope） |
| `DASHSCOPE_API_KEY` | DashScope API Key | 见 `.env` |
| `LLM_MODEL` | 模型名称 | `qwen3.7-max` |
| `QWEN_API_BASE` | API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

其他必填：
- `RESEND_API_KEY` — 邮件服务
- `WECHAT_WEBHOOK_URL` — 企业微信机器人
- `DINGTALK_WEBHOOK_URL` — 钉钉机器人

## 腾讯云部署

### 服务器信息
- **域名**：`https://rout.lbai.tech`
- **OS**：Ubuntu 24.04，4 核 / 3.6G 内存

### 部署方式
- **API 服务**：systemd `route-lead-app.service`，端口 8003
- **Worker 服务**：systemd `route-lead-worker.service`，Redis 队列消费
- **前端**：Nginx 静态文件（`/var/www/route-lead/frontend/`）
- **数据库**：PostgreSQL 16（`route_lead` 库），线索数据持久化
- **Redis**：仅用于任务队列
- **LLM**：DashScope qwen3.7-max

### 部署路径
| 组件 | 路径 |
|------|------|
| 项目代码 | `/var/www/route-lead/` |
| 虚拟环境 | `/var/www/route-lead/.venv/` |
| Nginx 配置 | `/etc/nginx/sites-enabled/route-lead.conf` |
| systemd | `/etc/systemd/system/route-lead-app.service` |
| systemd | `/etc/systemd/system/route-lead-worker.service` |

### 维护命令
```bash
# 查看状态
systemctl status route-lead-app.service route-lead-worker.service

# 查看日志
journalctl -u route-lead-app.service -n 50 --no-pager
journalctl -u route-lead-worker.service -n 50 --no-pager

# 重启
systemctl restart route-lead-app.service route-lead-worker.service
```
## 技术栈

- **后端**：Python FastAPI + asyncpg + Redis
- **前端**：Vue 3 + Vite + Axios
- **LLM**：DashScope qwen3.7-max（OpenAI 兼容接口）
- **存储**：PostgreSQL（线索数据）+ Redis（任务队列）
- **推送**：Resend（邮件）+ 企微/钉钉机器人

## 文档索引
- [BANTP 评分体系](docs/BANTP_scoring.md)
- [监控与告警](docs/monitoring.md)
