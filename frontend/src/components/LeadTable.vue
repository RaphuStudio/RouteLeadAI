<template>
  <div class="table-container">
    <div class="toolbar">
      <div class="filter-group">
        <select v-model="currentFilter" class="btn" @change="$emit('filter', currentFilter)">
          <option value="">全部</option>
          <option value="high_intent_agent">高意向</option>
          <option value="normal_nurture_agent">培育中</option>
          <option value="longtail_nurture_agent">长尾</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="$emit('add')">添加线索</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <table v-else>
      <thead>
        <tr>
          <th>公司</th>
          <th>联系人</th>
          <th>职位</th>
          <th>邮箱</th>
          <th>电话</th>
          <th>评分</th>
          <th>状态</th>
          <th>Agent</th>
          <th>时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="lead in filteredLeads" :key="lead.id">
          <td>{{ lead.company_name || '-' }}</td>
          <td>{{ lead.contact_name || '-' }}</td>
          <td>{{ lead.position || '-' }}</td>
          <td>{{ lead.email || '-' }}</td>
          <td>{{ lead.phone || '-' }}</td>
          <td>
            <span :style="{ color: getScoreColor(lead.intent_score) }">
              {{ lead.intent_score || 0 }}
            </span>
          </td>
          <td>
            <span class="status-dot" :class="'status-' + getStatusClass(lead.status)"></span>
            {{ lead.status }}
          </td>
          <td>
            <span class="agent-tag" v-if="lead.assigned_agent" :class="getAgentClass(lead.assigned_agent)">
              {{ lead.assigned_agent }}
            </span>
          </td>
          <td>{{ formatTime(lead.created_at) }}</td>
          <td>
            <button class="btn btn-sm" @click="$emit('view', lead)">查看</button>
          </td>
        </tr>
        <tr v-if="filteredLeads.length === 0">
          <td colspan="7" class="empty">暂无线索，点击上方"添加线索"创建</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  props: {
    leads: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['add', 'view', 'filter'],
  data() {
    return {
      currentFilter: ''
    }
  },
  computed: {
    filteredLeads() {
      if (!this.currentFilter) return this.leads
      return this.leads.filter(lead => lead.assigned_agent === this.currentFilter)
    }
  },
  methods: {
    getScoreColor(score) {
      if (score >= 100) return '#f5222d'
      if (score >= 62) return '#1890ff'
      return '#722ed1'
    },
    getStatusClass(status) {
      return status === 'contacted' ? 'contacted' : status
    },
    getAgentClass(agent) {
      if (agent.includes('high')) return 'agent-high'
      if (agent.includes('nurture')) return 'agent-nurture'
      return 'agent-longtail'
    },
    formatTime(time) {
      if (!time) return '-'
      // 后端返回 UTC 时间，转换为 ISO 8601 格式（北京时间 UTC+8）
      const utcDate = new Date(time)
      const cstDate = new Date(utcDate.getTime() + 8 * 60 * 60 * 1000)
      // 格式：2026-05-06T15:14:54+08:00
      const pad = (num) => String(num).padStart(2, '0')
      return cstDate.getFullYear() + '-' +
             pad(cstDate.getMonth() + 1) + '-' +
             pad(cstDate.getDate()) + 'T' +
             pad(cstDate.getHours()) + ':' +
             pad(cstDate.getMinutes()) + ':' +
             pad(cstDate.getSeconds()) + '+08:00'
    }
  }
}
</script>

<style scoped>
.table-container {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
}

.btn {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}

.btn-primary {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.btn-sm {
  padding: 2px 8px;
  font-size: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
  font-weight: 500;
}

td {
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
}

tr:hover {
  background: #fafafa;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.status-new { background: #faad14; }
.status-contacted { background: #1890ff; }
.status-qualified { background: #52c41a; }
.status-nurturing { background: #722ed1; }
.status-closed { background: #999; }

.agent-tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.agent-high { background: #fff1f0; color: #f5222d; }
.agent-nurture { background: #f0f5ff; color: #1890ff; }
.agent-longtail { background: #f9f0ff; color: #722ed1; }

.empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
