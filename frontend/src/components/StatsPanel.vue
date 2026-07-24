<template>
  <div class="stats" v-if="stats">
    <div class="stat-card">
      <div class="num">{{ stats.total }}</div>
      <div class="label">全部线索</div>
    </div>
    <div class="stat-card">
      <div class="num" style="color: #f5222d">{{ stats.by_agent['high_intent_agent'] || 0 }}</div>
      <div class="label">高意向 (100+)</div>
    </div>
    <div class="stat-card">
      <div class="num" style="color: #1890ff">{{ stats.by_agent['normal_nurture_agent'] || 0 }}</div>
      <div class="label">培育中 (62-99)</div>
    </div>
    <div class="stat-card">
      <div class="num" style="color: #722ed1">{{ stats.by_agent['longtail_nurture_agent'] || 0 }}</div>
      <div class="label">长尾 (<62)</div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    stats: {
      type: Object,
      default: null
    }
  }
}
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  padding: 16px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.stat-card .num {
  font-size: 24px;
  font-weight: 600;
}

.stat-card .label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}
</style>
