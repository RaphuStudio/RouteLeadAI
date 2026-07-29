<template>
  <div class="app">
    <header class="header" style="display: flex; align-items: center; gap: 12px;">
      <img src="/logo.png" alt="RouteLeadAI" style="height: 40px; width: 40px; border-radius: 8px;" />
      <div>
        <h1 style="margin: 0; font-size: 20px; font-weight: 600;">识途线索AI</h1>
        <p style="margin: 0; font-size: 12px; color: #666;">智能辨线索成色，自动规划跟进坦途</p>
      </div>
    </header>

    <main class="main">
      <StatsPanel :stats="stats" />
      <LeadTable
        :leads="leads"
        :loading="loading"
        @add="showAdd = true"
        @view="viewLead"
        @filter="handleFilter"
      />
    </main>

    <LeadForm
      v-if="showAdd"
      @submit="handleSubmit"
      @cancel="showAdd = false"
    />

    <LeadDetail
      v-if="showDetail"
      :lead="detailLead"
      @close="showDetail = false"
    />

    <!-- 备案 -->
    <div style="text-align:center;padding:12px 0 24px;font-size:12px">
      <a href="https://beian.mps.gov.cn/#/query/webSearch?code=33019202003154" rel="noreferrer" target="_blank" style="color:#999;text-decoration:none;display:inline-flex;align-items:center;gap:4px">
        <img src="/beian-icon.png" style="width:16px;height:16px"> 浙公网安备33019202003154号
      </a>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import StatsPanel from './components/StatsPanel.vue'
import LeadTable from './components/LeadTable.vue'
import LeadForm from './components/LeadForm.vue'
import LeadDetail from './components/LeadDetail.vue'

const API = '/api'

export default {
  components: { StatsPanel, LeadTable, LeadForm, LeadDetail },
  setup() {
    const leads = ref([])
    const stats = ref(null)
    const loading = ref(false)
    const showAdd = ref(false)
    const showDetail = ref(false)
    const detailLead = ref(null)
    const filterAgent = ref('')

    async function loadLeads() {
      loading.value = true
      try {
        const res = await axios.get(`${API}/leads`)
        leads.value = res.data.leads || []
      } catch (e) {
        console.error('加载线索失败:', e)
      } finally {
        loading.value = false
      }
    }

    async function loadStats() {
      try {
        const res = await axios.get(`${API}/stats`)
        stats.value = res.data
      } catch (e) {
        console.error('加载统计失败:', e)
      }
    }

    async function handleSubmit(form) {
      if (!form.raw_content) {
        alert('请填写原始内容')
        return
      }
      try {
        await axios.post(`${API}/leads`, form)
        showAdd.value = false
        loadLeads()
        loadStats()
      } catch (e) {
        alert('提交失败: ' + (e.response?.data?.detail || e.message))
      }
    }

    function viewLead(lead) {
      detailLead.value = lead
      showDetail.value = true
    }

    function handleFilter(agent) {
      filterAgent.value = agent
      // 这里可以添加按 agent 筛选的逻辑
    }

    onMounted(() => {
      loadLeads()
      loadStats()
    })

    return {
      leads, stats, loading, showAdd, showDetail, detailLead,
      handleSubmit, viewLead, handleFilter
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 14px;
  color: #333;
  background: #f5f5f5;
}

.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #000;
}

.main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
</style>
