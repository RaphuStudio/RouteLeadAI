-- RouteLeadAI 线索数据迁移：Redis → PostgreSQL
-- 用法：psql -U route_lead -d route_lead -f scripts/migration_leads.sql

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY,
    source VARCHAR(20) NOT NULL,
    raw_content TEXT DEFAULT '',
    company_name VARCHAR(200) DEFAULT '未知公司',
    contact_name VARCHAR(100) DEFAULT '未知联系人',
    position VARCHAR(100) DEFAULT '未提供',
    email VARCHAR(200) DEFAULT '',
    phone VARCHAR(50) DEFAULT '',
    budget_score INTEGER DEFAULT 0,
    authority_score INTEGER DEFAULT 0,
    need_score INTEGER DEFAULT 0,
    timeline_score INTEGER DEFAULT 0,
    intent_score INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'new',
    assigned_agent VARCHAR(50) DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_intent_score ON leads(intent_score);
CREATE INDEX IF NOT EXISTS idx_leads_assigned_agent ON leads(assigned_agent);
