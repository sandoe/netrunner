<template>
  <div class="exec-panel">
    <div class="exec-input-area">
      <textarea
        v-model="script"
        placeholder="# Shell commands, one per line (Ctrl+Enter to run)
ip addr show
ping -c 3 8.8.8.8"
        rows="6"
        spellcheck="false"
        @keydown.ctrl.enter.prevent="run"
      />
      <div class="exec-actions">
        <button @click="run" :disabled="running || !script.trim()" class="btn-run">
          {{ running ? '▶ running…' : '▶ run' }}
        </button>
        <button @click="clear" class="btn-secondary">clear</button>
      </div>
    </div>
    <div class="exec-results" v-if="results.length">
      <div v-for="(r, i) in results" :key="i" class="result-block">
        <div class="result-cmd">$ {{ r.command }}</div>
        <pre v-if="r.output" class="result-out">{{ r.output }}</pre>
        <pre v-if="r.error"  class="result-err">{{ r.error }}</pre>
      </div>
    </div>
    <div v-if="execError" class="exec-error">{{ execError }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import type { CommandResult } from '@/types'

const props = defineProps<{ nodeId: string }>()

const script   = ref('')
const running  = ref(false)
const results  = ref<CommandResult[]>([])
const execError = ref('')

async function run() {
  running.value   = true
  execError.value = ''
  results.value   = []
  try {
    const cmds = script.value.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'))
    const data = await api.executeNode(props.nodeId, cmds)
    results.value = data.results
  } catch (e) {
    execError.value = String(e)
  } finally {
    running.value = false
  }
}

function clear() {
  script.value  = ''
  results.value = []
  execError.value = ''
}
</script>

<style scoped>
.exec-panel { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.exec-input-area { padding: 12px; border-bottom: 1px solid #30363d; }
textarea {
  width: 100%; box-sizing: border-box;
  background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
  color: #c9d1d9; font-family: "Cascadia Code", "Fira Code", monospace;
  font-size: 12px; padding: 8px 10px; resize: vertical;
}
textarea:focus { outline: none; border-color: #388bfd; }
.exec-actions { display: flex; gap: 8px; margin-top: 8px; }
.btn-run {
  padding: 6px 16px; background: #1f6feb; color: #fff;
  border: none; border-radius: 6px; font-size: 13px; cursor: pointer;
}
.btn-run:hover:not(:disabled) { background: #388bfd; }
.btn-run:disabled { opacity: .5; cursor: not-allowed; }
.btn-secondary {
  padding: 6px 12px; background: #21262d; border: 1px solid #30363d;
  border-radius: 6px; color: #c9d1d9; font-size: 13px; cursor: pointer;
}
.btn-secondary:hover { background: #30363d; }
.exec-results { flex: 1; overflow-y: auto; padding: 8px 12px; }
.result-block { margin-bottom: 12px; }
.result-cmd {
  font-family: monospace; font-size: 12px; color: #58a6ff;
  padding: 3px 8px; background: #1c2128; border-radius: 4px; margin-bottom: 2px;
}
.result-out, .result-err {
  margin: 0; padding: 6px 8px;
  font-family: "Cascadia Code", "Fira Code", monospace;
  font-size: 12px; line-height: 1.4;
  border-radius: 4px; white-space: pre-wrap; word-break: break-all;
}
.result-out { background: #0d1117; color: #c9d1d9; }
.result-err { background: #1a0a0a; color: #f85149; }
.exec-error {
  margin: 12px; padding: 10px 14px;
  background: #1a0a0a; border: 1px solid #f85149;
  border-radius: 6px; color: #f85149; font-size: 12px;
}
</style>
