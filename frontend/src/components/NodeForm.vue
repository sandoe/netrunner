<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h3>{{ isEdit ? 'Edit Node' : 'Add Node' }}</h3>
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
            <option value="rpi">Raspberry Pi</option>
            <option value="gns3">GNS3 / Network device</option>
          </select>
        </label>
        <label>Tags <span class="hint">(comma-separated)</span>
          <input v-model="tagsInput" placeholder="lab, router, core" />
        </label>
        <div v-if="error" class="error">{{ error }}</div>
        <div class="actions">
          <button type="button" class="btn-secondary" @click="$emit('close')">Cancel</button>
          <button type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Save' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import type { NrNode } from '@/types'

const props = defineProps<{ node?: NrNode | null }>()
const emit  = defineEmits<{ close: [] }>()

const store  = useNodesStore()
const saving = ref(false)
const error  = ref('')
const isEdit = computed(() => !!props.node)

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
    const payload = {
      ...form.value,
      tags: tagsInput.value.split(',').map(t => t.trim()).filter(Boolean),
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
  background: rgba(0,0,0,.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.modal {
  background: #161b22; border: 1px solid #30363d; border-radius: 10px;
  padding: 24px; width: 420px; max-width: 95vw; max-height: 90vh; overflow-y: auto;
}
h3 { margin: 0 0 16px; color: #e6edf3; font-size: 16px; }
label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; font-size: 13px; color: #8b949e; }
.hint { font-size: 11px; color: #6e7681; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
input, select {
  background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
  color: #e6edf3; padding: 7px 10px; font-size: 13px;
}
input:focus, select:focus { outline: none; border-color: #58a6ff; }
.error { background: #330a0a; border: 1px solid #f85149; color: #f85149; border-radius: 6px; padding: 8px 12px; font-size: 13px; margin-bottom: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
button { padding: 7px 16px; border-radius: 6px; font-size: 13px; cursor: pointer; border: none; background: #1f6feb; color: #fff; }
button:hover:not(:disabled) { background: #388bfd; }
button:disabled { opacity: .5; cursor: not-allowed; }
.btn-secondary { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; }
.btn-secondary:hover { background: #30363d; }
</style>
