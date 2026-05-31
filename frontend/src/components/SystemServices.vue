<template>
  <div class="svc">
    <div class="svc-bar">
      <input v-model="filter" class="svc-filter" placeholder="Filter services…" />
      <button class="svc-refresh" @click="load" :disabled="loading">{{ loading ? '…' : '🔄' }}</button>
      <span class="svc-count">{{ shown.length }}/{{ services.length }}</span>
    </div>
    <div class="svc-list">
      <div v-for="s in shown" :key="s.name" class="svc-row">
        <span class="svc-dot" :class="s.sub"></span>
        <div class="svc-meta">
          <div class="svc-name">{{ s.name }}</div>
          <div class="svc-desc">{{ s.desc }}</div>
        </div>
        <span class="svc-state" :class="s.sub">{{ s.sub }}</span>
        <div class="svc-actions">
          <button title="Start" @click="act(s, 'start')">▶</button>
          <button title="Restart" @click="act(s, 'restart')">↻</button>
          <button title="Stop" @click="act(s, 'stop')">■</button>
        </div>
      </div>
      <div v-if="!loading && shown.length === 0" class="svc-empty">{{ note }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ nodeId: string }>()
const services = ref<any[]>([])
const filter = ref('')
const loading = ref(false)
const note = ref('Loading services…')

const shown = computed(() => {
  const q = filter.value.trim().toLowerCase()
  const list = q ? services.value.filter(s => (s.name + ' ' + s.desc).toLowerCase().includes(q)) : services.value
  return list
})

async function load() {
  loading.value = true
  try {
    const res = await api.nodeServices(props.nodeId)
    services.value = (res.services || []).sort((a, b) =>
      (a.sub === 'running' ? -1 : 1) - (b.sub === 'running' ? -1 : 1) || a.name.localeCompare(b.name))
    note.value = services.value.length ? '' : (res.error || 'No services (need systemd + permissions).')
  } catch (e: any) {
    note.value = String(e?.message || e)
  } finally {
    loading.value = false
  }
}

async function act(s: any, action: string) {
  if (action === 'stop' && !confirm(`Stop ${s.name} on this node?`)) return
  try {
    const r = await api.nodeServiceAction(props.nodeId, s.name, action)
    if (r.error && r.output && /not permitted|denied|authentication/i.test(r.output + r.error))
      alert('Permission denied — the SSH user needs sudo/systemd rights.')
    setTimeout(load, 700)
  } catch (e) { alert('Action failed: ' + String(e)) }
}

watch(() => props.nodeId, () => { services.value = []; note.value = 'Loading services…'; load() })
onMounted(load)
</script>

<style scoped>
.svc { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.svc-bar { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--border); background: var(--bg2); }
.svc-filter { flex: 1; background: rgba(0,0,0,0.4); border: 1px solid var(--border); color: var(--textwh); padding: 6px 10px; border-radius: 4px; font-family: var(--font-co); font-size: 12px; outline: none; }
.svc-filter:focus { border-color: var(--cyan); }
.svc-refresh { background: var(--bg3); border: 1px solid var(--border); color: var(--text); padding: 6px 10px; border-radius: 4px; cursor: pointer; }
.svc-count { font-size: 10px; color: var(--text); font-family: var(--font-co); }
.svc-list { flex: 1; min-height: 0; overflow-y: auto; padding: 6px; }
.svc-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-bottom: 1px solid rgba(26,37,64,0.5); }
.svc-dot { width: 8px; height: 8px; border-radius: 50%; background: #4a5a72; flex-shrink: 0; }
.svc-dot.running { background: var(--green); box-shadow: 0 0 6px var(--green); }
.svc-dot.dead, .svc-dot.failed { background: var(--pink); }
.svc-meta { flex: 1; min-width: 0; }
.svc-name { color: var(--textwh); font-family: var(--font-co); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.svc-desc { color: var(--text); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.svc-state { font-family: var(--font-co); font-size: 9px; letter-spacing: 1px; text-transform: uppercase; color: var(--text); width: 64px; text-align: right; }
.svc-state.running { color: var(--green); }
.svc-state.dead, .svc-state.failed { color: var(--pink); }
.svc-actions { display: flex; gap: 4px; }
.svc-actions button { background: none; border: 1px solid var(--border); color: var(--text); width: 24px; height: 24px; border-radius: 4px; cursor: pointer; font-size: 10px; }
.svc-actions button:hover { border-color: var(--cyan); color: var(--cyan); }
.svc-empty { padding: 16px; color: var(--text); font-size: 12px; text-align: center; }
</style>
