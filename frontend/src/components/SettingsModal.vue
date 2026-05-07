<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <div class="modal-title">SYSTEM SETTINGS</div>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div class="form-group">
          <label>OPENAI API KEY</label>
          <div class="input-with-hint">
            <input 
              v-model="apiKey" 
              type="password" 
              placeholder="sk-..." 
              class="form-input"
            />
            <div class="hint" v-if="currentKeyMasked">
              Current: <span class="masked-text">{{ currentKeyMasked }}</span>
            </div>
          </div>
          <p class="form-help">REQUIRED FOR AI ASSISTANT. KEYS ARE STORED LOCALLY IN data/settings.json.</p>
        </div>

        <div class="form-group">
          <label>GNS3 SERVER URL</label>
          <input 
            v-model="gns3Url" 
            placeholder="http://127.0.0.1:3080" 
            class="form-input"
          />
          <p class="form-help">USED TO DISCOVER L2 SWITCHES AND SYNC TOPOLOGY DIRECTLY FROM GNS3.</p>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">CANCEL</button>
        <button class="btn-save" @click="save" :disabled="saving">
          {{ saving ? 'SAVING...' : 'SAVE CONFIG' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

const emit = defineEmits(['close', 'saved'])

const apiKey = ref('')
const gns3Url = ref('http://127.0.0.1:3080')
const currentKeyMasked = ref('')
const saving = ref(false)

async function load() {
  try {
    const res = await api.getSettings()
    if (res.openai_api_key_set) {
      currentKeyMasked.value = res.masked_key
    }
    if (res.gns3_server_url) {
      gns3Url.value = res.gns3_server_url
    }
  } catch (e) {
    console.error('Failed to load settings', e)
  }
}

async function save() {
  saving.value = true
  try {
    const payload: any = { gns3_server_url: gns3Url.value }
    if (apiKey.value) payload.openai_api_key = apiKey.value
    await api.updateSettings(payload)
    emit('saved')
    emit('close')
  } catch (e) {
    alert(String(e))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 8, 15, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}

.modal-content {
  width: 100%;
  max-width: 450px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r2);
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  overflow: hidden;
  animation: modal-pop 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modal-pop {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-header {
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-family: var(--font-hd);
  font-size: 13px;
  letter-spacing: 2px;
  color: var(--cyan);
  text-shadow: 0 0 8px var(--cyan);
}

.btn-close {
  background: none;
  border: none;
  color: var(--text);
  font-size: 20px;
  cursor: pointer;
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  font-family: var(--font-hd);
  font-size: 9px;
  letter-spacing: 1.5px;
  color: var(--text);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--r);
  color: var(--textwh);
  font-family: var(--font-co);
  font-size: 12px;
  outline: none;
}

.form-input:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.1);
}

.form-help {
  margin-top: 10px;
  font-size: 9px;
  color: var(--text);
  line-height: 1.4;
}

.hint {
  margin-top: 6px;
  font-size: 10px;
  color: var(--text);
  font-family: var(--font-co);
}

.masked-text {
  color: var(--green);
}

.modal-footer {
  padding: 18px 24px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: var(--bg3);
}

.btn-cancel {
  background: none;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 8px 16px;
  border-radius: var(--r);
  font-family: var(--font-hd);
  font-size: 10px;
  cursor: pointer;
}

.btn-save {
  background: var(--cyan);
  color: var(--bg);
  border: none;
  padding: 8px 20px;
  border-radius: var(--r);
  font-family: var(--font-hd);
  font-size: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save:hover:not(:disabled) {
  box-shadow: var(--shadow-c);
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
