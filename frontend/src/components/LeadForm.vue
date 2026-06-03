<template>
  <div class="modal-mask" @click.self="$emit('cancel')">
    <div class="modal">
      <h3>添加线索</h3>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>来源</label>
          <select v-model="form.source" class="form-control">
            <option value="website">网站</option>
            <option value="chat">聊天</option>
            <option value="import">导入</option>
            <option value="referral">转介绍</option>
          </select>
        </div>

        <div class="form-group">
          <label>公司名称</label>
          <input v-model="form.company_name" class="form-control" placeholder="输入公司名称">
        </div>

        <div class="form-group">
          <label>联系人</label>
          <input v-model="form.contact_name" class="form-control" placeholder="输入联系人">
        </div>

        <div class="form-group">
          <label>邮箱（测试模式仅支持 hejibo061@gmail.com）</label>
          <input v-model="form.email" class="form-control" placeholder="hejibo061@gmail.com">
        </div>

        <div class="form-group">
          <label>电话</label>
          <input v-model="form.phone" class="form-control" placeholder="输入电话">
        </div>

        <div class="form-group">
          <label>原始内容</label>
          <textarea v-model="form.raw_content" class="form-control" placeholder="输入线索详情..." rows="4"></textarea>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn" @click="$emit('cancel')">取消</button>
          <button type="submit" class="btn btn-primary">提交</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['submit', 'cancel'],
  data() {
    return {
      form: {
        source: 'website',
        company_name: '',
        contact_name: '',
        email: '',
        phone: '',
        raw_content: ''
      }
    }
  },
  methods: {
    handleSubmit() {
      this.$emit('submit', { ...this.form })
    }
  }
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
  width: 500px;
  padding: 24px;
}

.modal h3 {
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
}

.form-control {
  width: 100%;
  padding: 6px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
}

textarea.form-control {
  resize: vertical;
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

.btn-primary {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}
</style>
