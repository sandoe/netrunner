<template>
  <div class="logs">
    <div class="logs-bar">
      <button class="lb-btn" :class="{ on: !paused }" @click="paused = !paused">
        {{ paused ? '▶ RESUME' : '⏸ PAUSE' }}
      </button>
      <button class="lb-btn" @click="load">🔄 REFRESH</button>
      <label class="lb-auto"><input type="checkbox" v-model="autoscroll" /> autoscroll</label>
      <span class="lb-status">{{ lines.length }} lines</span>
    </div>
    <div ref="con" class="logs-con">
      <div class="cyber-guide" style="margin-bottom: 12px; font-size: 11px; border-left: 2px solid var(--textbr); padding-left: 8px; background: rgba(255, 255, 255, 0.05);">
        <strong style="color: var(--textbr);">🎓 Cyber Guide: System Logs (Event Auditing)</strong><br/>
        <span style="color: #ccc;">Logfiler indeholder spor (breadcrumbs) fra alt, der sker på systemet. I en større virksomhed sendes alle logs centralt til en SIEM (Security Information and Event Management) server, så SOC-analytikere kan lede efter mønstre og Indicators of Compromise (IoC). Hackere forsøger ofte at slette disse logs (T1070) for at skjule deres spor.</span>
      </div>
      <div v-if="!lines.length" class="logs-empty">{{ note }}</div>
      <div v-for="(l, i) in lines" :key="i" class="log-line" :class="lineClass(l)">{{ l }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ nodeId: string }>()
const lines = ref<string[]>([])
const paused = ref(false)
const autoscroll = ref(true)
const note = ref('Loading logs…')
const con = ref<HTMLElement | null>(null)
let timer: any = null

function lineClass(l: string) {
  const s = l.toLowerCase()
  if (/\b(error|fail|fatal|denied|critical|panic)\b/.test(s)) return 'err'
  if (/\b(warn|warning|deprecated)\b/.test(s)) return 'warn'
  return ''
}

async function load() {
  try {
    const res = await api.nodeLogs(props.nodeId, 150)
    lines.value = (res.lines || []).filter(l => l.trim().length)
    note.value = lines.value.length ? '' : (res.error || 'No logs available.')
    if (autoscroll.value) nextTick(() => { if (con.value) con.value.scrollTop = con.value.scrollHeight })
  } catch (e: any) {
    note.value = String(e?.message || e)
  }
}

watch(() => props.nodeId, () => { lines.value = []; note.value = 'Loading logs…'; load() })
onMounted(() => { load(); timer = setInterval(() => { if (!paused.value) load() }, 3000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.logs { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.logs-bar { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-bottom: 1px solid var(--border); background: var(--bg2); }
.lb-btn { background: var(--bg3); border: 1px solid var(--border); color: var(--text); font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
.lb-btn:hover { color: var(--textwh); border-color: var(--cyan); }
.lb-btn.on { color: var(--green); border-color: var(--green); }
.lb-auto { font-size: 10px; color: var(--text); display: flex; align-items: center; gap: 4px; cursor: pointer; }
.lb-status { margin-left: auto; font-size: 10px; color: var(--text); font-family: var(--font-co); }
.logs-con { flex: 1; min-height: 0; overflow-y: auto; padding: 8px 12px; background: #04060a; font-family: var(--font-co); font-size: 11px; line-height: 1.5; }
.log-line { white-space: pre-wrap; word-break: break-all; color: #9fb0c8; }
.log-line.err { color: #ff6b9c; }
.log-line.warn { color: #ffce5a; }
.logs-empty { color: var(--text); font-size: 12px; padding: 12px; }
</style>
