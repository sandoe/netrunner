<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal cyber-glass" role="dialog" aria-modal="true" aria-labelledby="node-form-title">
      <h3 id="node-form-title">{{ isEdit ? 'Edit Node' : 'Add Node' }}</h3>
      <form @submit.prevent="submit">
        <label>Name
          <input v-model="form.name" required placeholder="Router-1" />
        </label>
        <label>Host / IP
          <input v-model="form.host" required placeholder="192.168.1.1" />
        </label>
        <div class="row">
          <label>Port
            <input v-model.number="form.port" type="number" min="1" max="65535" required />
          </label>
          <label>Transport
            <select v-model="form.transport">
              <option value="ssh">SSH</option>
              <option value="telnet">Telnet</option>
            </select>
          </label>
        </div>
        <label>Username
          <input v-model="form.username" placeholder="root" />
        </label>
        <label>Password <span class="hint">{{ isEdit ? '(leave blank to keep)' : '' }}</span>
          <input v-model="form.password" type="password" placeholder="••••••" />
        </label>
        <label>Device type
          <select v-model="form.device_type">
            <option value="unknown">Unknown (auto-detect)</option>
            <option value="linux">Linux</option>
            <option value="windows">Windows</option>
            <option value="rpi">Raspberry Pi</option>
            <option value="gns3">GNS3 / Network device</option>
          </select>
        </label>
        <label>Tags <span class="hint">(comma-separated)</span>
          <input v-model="tagsInput" placeholder="lab, router, core" />
        </label>
        <div v-if="error" class="error">{{ error }}</div>
        <div class="actions">
          <button type="button" v-if="isEdit" class="btn-connect" @click="connectNode" :disabled="connecting">
            <span v-if="connecting" class="spinner"></span>
            <span v-else>Connect</span>
          </button>
          <button type="button" class="btn-secondary" @click="$emit('close')">Cancel</button>
          <button type="submit" :disabled="saving">
            <span v-if="saving" class="spinner"></span>
            <span v-else>Save</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'
import type { NrNode } from '@/types'

const props = defineProps<{ node?: NrNode | null }>()
const emit  = defineEmits<{ close: [] }>()

onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))
function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

const store  = useNodesStore()
const saving = ref(false)
const connecting = ref(false)
const error  = ref('')
const isEdit = computed(() => !!props.node)

async function connectNode() {
  if (!props.node) return
  connecting.value = true
  error.value = ''
  try {
    await api.connectNode(props.node.id)
    store.manuallyDisconnected.delete(props.node.id)
    await store.refreshConnections()
    // Select the node so the UI switches to it immediately
    store.select(props.node.id)
    emit('close')
  } catch (e) {
    error.value = String(e)
  } finally {
    connecting.value = false
  }
}

const form = ref({
  name: props.node?.name ?? '',
  host: props.node?.host ?? '',
  port: props.node?.port ?? 22,
  transport: props.node?.transport ?? 'ssh' as 'ssh' | 'telnet',
  username: props.node?.username ?? 'root',
  password: '',
  device_type: props.node?.device_type ?? 'unknown' as NrNode['device_type'],
})
const tagsInput = ref(props.node?.tags?.join(', ') ?? '')

async function submit() {
  saving.value = true
  error.value  = ''
  try {
    const payload: any = {
      ...form.value,
      tags: tagsInput.value.split(',').map(t => t.trim()).filter(Boolean),
    }
    // On edit, a blank password means "keep the existing one" — don't send it,
    // otherwise the backend would overwrite the stored password with empty.
    if (isEdit.value && !form.value.password) {
      delete payload.password
    }
    if (isEdit.value) {
      await store.update(props.node!.id, payload)
    } else {
      await store.create(payload)
    }
    emit('close')
  } catch (e) {
    error.value = String(e)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(5, 8, 15, 0.85);
  backdrop-filter: blur(12px);
  display: flex; align-items: center; justify-content: center;
  z-index: 3000;
}
.modal {
  background: rgba(10, 14, 25, 0.8); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 12px;
  box-shadow: 0 24px 80px rgba(0, 229, 255, 0.1), inset 0 0 30px rgba(0, 229, 255, 0.05);
  padding: 24px; width: 420px; max-width: 95vw; max-height: 90vh; overflow-y: auto;
}
h3 { margin: 0 0 16px; color: var(--textwh); font-size: 16px; font-family: var(--font-hd); letter-spacing: 2px; }
label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; font-size: 13px; color: var(--textbr); font-family: var(--font-hd); }
.hint { font-size: 11px; color: var(--textbr); font-family: var(--font-ui); }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
input, select {
  background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px;
  color: var(--textwh); padding: 7px 10px; font-size: 13px; font-family: var(--font-co); transition: all 0.2s;
}
input:focus, select:focus { outline: none; border-color: var(--cyan); box-shadow: 0 0 12px rgba(0,229,255,0.15); background: rgba(0, 0, 0, 0.5); }
.error { background: rgba(255, 45, 110, 0.1); border-left: 3px solid var(--pink); color: var(--pink); padding: 8px 12px; font-size: 13px; margin-bottom: 12px; font-family: var(--font-co); }
.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
button { padding: 7px 16px; border-radius: 6px; font-size: 13px; cursor: pointer; border: 1px solid var(--cyan); background: rgba(0, 229, 255, 0.15); color: var(--cyan); font-family: var(--font-hd); transition: all 0.2s; }
button:focus, button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
button:hover:not(:disabled) { background: var(--cyan); color: #000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.4); }
button:disabled { opacity: .5; cursor: not-allowed; border-color: rgba(0, 229, 255, 0.3); color: rgba(0, 229, 255, 0.5); background: transparent; }
.btn-secondary { background: none; border: 1px solid rgba(255, 255, 255, 0.1); color: var(--text); }
.btn-secondary:hover { background: rgba(255, 255, 255, 0.05); color: var(--textwh); box-shadow: none; }
.btn-connect { background: rgba(0, 255, 157, 0.15); color: var(--green); border: 1px solid var(--green); margin-right: auto; }
.btn-connect:hover:not(:disabled) { background: var(--green); color: #000; box-shadow: 0 0 20px rgba(0, 255, 157, 0.4); }
</style>
