<template>
  <div class="diag-panel">
    <div class="diag-sidebar">
      <div v-for="(cat, key) in READ_CATEGORIES" :key="key" class="cat-group">
        <div class="cat-label">{{ cat.icon }} {{ cat.label }}</div>
        <button
          v-for="item in cat.types"
          :key="item.type"
          class="read-btn"
          :class="{ active: activeType === item.type, loading: loadingType === item.type }"
          @click="readType(item.type)"
        >{{ item.label }}</button>
      </div>
    </div>
    <div class="diag-output">
      <div v-if="!activeType" class="placeholder">Select a diagnostic type →</div>
      <div v-else>
        <div class="output-header">
          <span>{{ activeType }}</span>
          <div class="header-btns">
            <button class="clear-btn" @click="clearOutput">clear</button>
            <button class="copy-btn" :class="{ ok: copied }" @click="copyOutput">{{ copied ? '✓ copied' : 'copy' }}</button>
          </div>
        </div>
        <div v-if="loadingType === activeType" class="loader">loading…</div>
        <div v-else-if="outputError" class="output-error">{{ outputError }}</div>
        <pre v-else class="output-pre">{{ output }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '@/api/client'
import { READ_CATEGORIES } from '@/types'
import type { ReadType } from '@/types'

const props = defineProps<{ nodeId: string }>()

const activeType  = ref<ReadType | null>(null)
const loadingType = ref<string | null>(null)
const output      = ref('')
const outputError = ref('')
const copied      = ref(false)

watch(() => props.nodeId, () => {
  activeType.value  = null
  loadingType.value = null
  output.value      = ''
  outputError.value = ''
  copied.value      = false
})

async function readType(type: ReadType) {
  activeType.value  = type
  loadingType.value = type
  outputError.value = ''
  output.value      = ''
  try {
    const data = await api.readNode(props.nodeId, type)
    output.value = data.results.map(r => (r.output || r.error || '')).join('\n\n').trim()
  } catch (e) {
    outputError.value = String(e)
  } finally {
    loadingType.value = null
  }
}

function copyOutput() {
  navigator.clipboard.writeText(output.value).then(() => {
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  }).catch(() => {})
}

function clearOutput() {
  activeType.value = null
  output.value = ''
  outputError.value = ''
}
</script>

<style scoped>
.diag-panel {
  display: flex;
  height: 100%;
  overflow: hidden;
}
.diag-sidebar {
  width: 180px;
  min-width: 180px;
  overflow-y: auto;
  border-right: 1px solid #30363d;
  padding: 8px 0;
}
.cat-group { margin-bottom: 8px; }
.cat-label {
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  color: #6e7681;
  letter-spacing: .04em;
  text-transform: uppercase;
}
.read-btn {
  display: block; width: 100%;
  padding: 5px 14px; text-align: left;
  background: none; border: none; color: #8b949e;
  font-size: 12px; cursor: pointer;
}
.read-btn:hover { background: #161b22; color: #c9d1d9; }
.read-btn.active { background: #1c2128; color: #58a6ff; }
.read-btn.loading { opacity: .5; }
.diag-output { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.placeholder { color: #6e7681; font-size: 13px; padding: 24px; }
.output-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 12px; border-bottom: 1px solid #30363d;
  font-size: 12px; color: #6e7681;
}
.header-btns { display: flex; gap: 8px; }
.copy-btn, .clear-btn {
  font-size: 11px; padding: 2px 8px;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 4px; color: #c9d1d9; cursor: pointer; transition: background .15s, color .15s;
}
.copy-btn:hover, .clear-btn:hover { background: #30363d; }
.clear-btn:hover { color: #f85149; border-color: rgba(248, 81, 73, 0.4); }
.copy-btn.ok { background: #1f3a1f; border-color: #3fb950; color: #3fb950; }
.loader { padding: 24px; color: #6e7681; font-size: 13px; }
.output-error {
  margin: 12px; padding: 10px 14px;
  background: #1a0a0a; border: 1px solid #f85149;
  border-radius: 6px; color: #f85149; font-size: 12px;
}
.output-pre {
  flex: 1; overflow: auto; margin: 0;
  padding: 12px 14px;
  font-family: "Cascadia Code", "Fira Code", monospace;
  font-size: 12px; line-height: 1.5;
  color: #c9d1d9; white-space: pre-wrap; word-break: break-all;
}
</style>
