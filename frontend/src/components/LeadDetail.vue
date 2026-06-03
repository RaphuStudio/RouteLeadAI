<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div class="modal">
      <h3>线索详情</h3>
      <div v-if="lead" class="detail-content">
        <div class="detail-row">
          <span class="detail-label">公司：</span>
          <span>{{ lead.company_name }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">联系人：</span>
          <span>{{ lead.contact_name }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">邮箱：</span>
          <span>{{ lead.email || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">电话：</span>
          <span>{{ lead.phone || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">意向评分：</span>
          <span>{{ lead.intent_score }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态：</span>
          <span>{{ lead.status }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Agent：</span>
          <span>{{ lead.assigned_agent }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">BANT 评分：</span>
          <div class="bant-scores">
            <div>预算 {{ lead.budget_score }}</div>
            <div>决策权 {{ lead.authority_score }}</div>
            <div>需求 {{ lead.need_score }}</div>
            <div>时间线 {{ lead.timeline_score }}</div>
          </div>
        </div>
        <div class="detail-row">
          <span class="detail-label">原始内容：</span>
          <div class="raw-content">{{ lead.raw_content }}</div>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    lead: {
      type: Object,
      default: null
    }
  },
  emits: ['close']
}
</script>

<style scoped>
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: #fff;
  border-radius: 4px;
  width: 600px;
  padding: 24px;
}

.modal h3 {
  margin-bottom: 16px;
}

.detail-content {
  font-size: 14px;
}

.detail-row {
  margin-bottom: 12px;
  line-height: 1.6;
}

.detail-label {
  font-weight: 600;
  margin-right: 8px;
}

.bant-scores {
  display: inline-block;
  margin-left: 8px;
}

.bant-scores div {
  margin-bottom: 4px;
}

.raw-content {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 13px;
  margin-top: 4px;
  white-space: pre-wrap;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.btn {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
</style>
