<template>
  <div class="diag-panel">
    <div class="diag-sidebar">
      <div v-for="(cat, key) in READ_CATEGORIES" :key="key" class="cat-group">
        <div class="cat-label" @click="toggleCat(key as string)">
          <span>{{ cat.icon }} {{ cat.label }}</span>
          <span class="cat-chevron" :class="{ collapsed: collapsedCats.has(key as string) }">⌃</span>
        </div>
        <div v-if="!collapsedCats.has(key as string)" class="cat-items">
          <button
            v-for="item in cat.types"
            :key="item.type"
            class="read-btn"
            :class="{ active: activeType === item.type, loading: loadingType === item.type }"
            @click="readType(item.type)"
          >{{ item.label }}</button>
        </div>
      </div>
    </div>
    <div class="diag-output">
      <div v-if="!activeType" class="placeholder">Select a diagnostic type →</div>
      <div v-else class="output-container">
        <div class="output-header">
          <span class="output-title">
            <span class="pulse-indicator"></span>
            {{ activeType }}
          </span>
          <div class="header-search">
            <span class="search-icon">🔍</span>
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Search/Filter output..." 
              class="search-input"
            />
          </div>
          <div class="header-btns">
            <button class="refresh-btn" :disabled="loadingType === activeType" @click="readType(activeType!)" title="Re-run diagnostic">
              <span>🔄</span> Refresh
            </button>
            <button class="copy-btn" :class="{ ok: copied }" @click="copyOutput" title="Copy output">
              <span>{{ copied ? '✓' : '📋' }}</span> {{ copied ? 'Copied' : 'Copy' }}
            </button>
            <button class="clear-btn" @click="clearOutput" title="Clear console">
              <span>🗑️</span> Clear
            </button>
          </div>
        </div>
        
        <!-- WireGuard Quick Controls -->
        <div v-if="activeType === 'wireguard' && !outputError && !isMissingTool && loadingType !== activeType" class="wg-quick-controls">
          <div class="wg-control-info">
            <span class="control-label">⚡ WIREGUARD CONTROLS (wg0):</span>
          </div>
          <div class="wg-control-btns">
            <button class="btn-wg-up" :disabled="wgRunningAction" @click="runWgAction('up')">
              🟢 WG-QUICK UP
            </button>
            <button class="btn-wg-down" :disabled="wgRunningAction" @click="runWgAction('down')">
              🔴 WG-QUICK DOWN
            </button>
          </div>
        </div>

        <div v-if="loadingType === activeType" class="loader-scanner">
          <div class="loader-grid"></div>
          <div class="loader-line"></div>
          <div class="loader-text">> SCANNING TELEMETRY...</div>
        </div>
        <div v-else-if="outputError" class="output-error">{{ outputError }}</div>
        <div v-else-if="isMissingTool" class="output-fix-box">
            <div class="fix-msg">It looks like <strong>{{ activeType }}</strong> is not installed on this node.</div>
            <button class="btn-install-tool" @click="installTool" :disabled="installing">
                {{ installing ? 'INSTALLING...' : 'INSTALL ' + activeType?.toUpperCase() }}
            </button>
            <pre class="raw-err">{{ output }}</pre>
        </div>
        <pre v-else class="output-pre" v-html="highlightedOutput"></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { api } from '@/api/client'
import { READ_CATEGORIES } from '@/types'
import type { ReadType } from '@/types'

const props = defineProps<{ nodeId: string }>()

const activeType    = ref<ReadType | null>(null)
const loadingType   = ref<string | null>(null)
const output        = ref('')
const outputError   = ref('')
const copied        = ref(false)
const installing    = ref(false)
const collapsedCats = ref<Set<string>>(new Set())
const searchQuery   = ref('')

const isMissingTool = computed(() => {
    const raw = output.value.toLowerCase()
    const indicators = ['not found', 'no such file', 'not installed', 'unable to locate', 'command not found']
    return indicators.some(ind => raw.includes(ind))
})

function escapeHtml(unsafe: string) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
}

function highlightTerminalOutput(text: string): string {
  // UP, active (running), SUCCESS, OK
  const greenReg = /\b(UP|active \(running\)|active|SUCCESS|OK|ok|success|online|connected)\b/g
  // DOWN, inactive (dead), ERROR, FAILED, not found
  const redReg = /\b(DOWN|inactive \(dead\)|inactive|ERROR|FAILED|failed|error|offline|disconnected|not found|command not found|no such file)\b/g
  // IP Address / Subnet
  const ipReg = /\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:\/\d{1,2})?)\b/g
  // MAC addresses
  const macReg = /\b([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})\b/g
  // Interface names/system objects
  const interfaceReg = /\b(eth\d+|br\d+|wlan\d+|wg\d+|lo|bond\d+|vlan\d+)\b/g
  
  let highlighted = text
  highlighted = highlighted.replace(greenReg, '<span class="term-ok">$1</span>')
  highlighted = highlighted.replace(redReg, '<span class="term-err">$1</span>')
  highlighted = highlighted.replace(ipReg, '<span class="term-ip">$1</span>')
  highlighted = highlighted.replace(macReg, '<span class="term-mac">$1</span>')
  highlighted = highlighted.replace(interfaceReg, '<span class="term-int">$1</span>')
  
  return highlighted
}

const highlightedOutput = computed(() => {
  if (!output.value) return ''
  
  let text = output.value
  
  // Escape HTML to prevent XSS
  text = escapeHtml(text)
  
  // Line-by-line filtering if search query is active
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    const lines = text.split('\n')
    const filteredLines = lines.filter(line => line.toLowerCase().includes(q))
    text = filteredLines.length > 0 
      ? filteredLines.join('\n') 
      : '-- NO MATCHES FOUND --'
  }
  
  // Apply regular terminal formatting highlights
  text = highlightTerminalOutput(text)
  
  // Search query highlight
  if (searchQuery.value.trim()) {
    const q = escapeHtml(searchQuery.value.trim())
    const escQ = q.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')
    const regex = new RegExp(`(${escQ})`, 'gi')
    text = text.replace(regex, '<mark class="search-match">$1</mark>')
  }
  
  return text
})

function toggleCat(key: string) {
  if (collapsedCats.value.has(key)) {
    collapsedCats.value.delete(key)
  } else {
    collapsedCats.value.add(key)
  }
}

watch(() => props.nodeId, () => {
  activeType.value  = null
  loadingType.value = null
  output.value      = ''
  outputError.value = ''
  copied.value      = false
  searchQuery.value = ''
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

async function installTool() {
    if (!activeType.value) return
    installing.value = true
    try {
        await api.installTool(props.nodeId, activeType.value)
        await readType(activeType.value)
    } catch (e) {
        alert('Installation failed: ' + e)
    } finally {
        installing.value = false
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
  searchQuery.value = ''
}

const wgRunningAction = ref(false)

async function runWgAction(action: 'up' | 'down') {
  wgRunningAction.value = true
  try {
    let cmd = ''
    if (action === 'up') {
      // Gracefully clear any potential stale interfaces or routes first, then run wg-quick up
      cmd = `(wg-quick down wg0 2>/dev/null || ip link delete wg0 2>/dev/null || true) && wg-quick up wg0 && echo "__SUCCESS__" || echo "__FAILED__"`
    } else {
      cmd = `wg-quick down wg0 && echo "__SUCCESS__" || echo "__FAILED__"`
    }
    const res = await api.executeNode(props.nodeId, [cmd])
    const r = res.results?.[0]
    
    if (r) {
      if (r.error) {
        alert(`Failed to run wg-quick ${action}: ` + r.error)
      } else {
        const outputText = r.output || ''
        if (outputText.includes('__FAILED__') || !outputText.includes('__SUCCESS__')) {
          const cleanOutput = outputText
            .replace('__FAILED__', '')
            .replace('__SUCCESS__', '')
            .trim()
          alert(`Failed to run wg-quick ${action}:\n${cleanOutput || 'Unknown error'}`)
        }
      }
    }
    
    // Always refresh the diagnostic view to show current state
    await readType('wireguard')
  } catch (e: any) {
    alert(`Failed to run wg-quick ${action}: ` + (e.message || e))
  } finally {
    wgRunningAction.value = false
  }
}
</script>

<style scoped>
.diag-panel {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: var(--bg2);
}
.diag-sidebar {
  width: 200px;
  min-width: 200px;
  overflow-y: auto;
  border-right: 1px solid var(--border);
  background: rgba(8, 13, 24, 0.5);
  padding: 12px 0;
  backdrop-filter: blur(10px);
}
.cat-group { margin-bottom: 12px; }
.cat-label {
  padding: 8px 16px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: .08em;
  text-transform: uppercase;
  font-family: var(--font-hd);
  cursor: pointer;
  display: flex; justify-content: space-between; align-items: center;
  user-select: none; transition: color .2s;
}
.cat-label:hover { color: var(--cyan); text-shadow: 0 0 8px rgba(0, 229, 255, 0.4); }
.cat-chevron { font-size: 10px; transition: transform .3s; }
.cat-chevron.collapsed { transform: rotate(180deg); }
.cat-items {
  padding: 4px 8px;
}
.read-btn {
  display: block; width: 100%;
  padding: 6px 16px; text-align: left;
  background: none; border: none; color: var(--textbr);
  font-size: 12px; cursor: pointer;
  border-radius: 4px;
  margin-bottom: 2px;
  transition: all .2s;
  font-family: var(--font-ui);
}
.read-btn:hover { background: rgba(0, 229, 255, 0.05); color: var(--cyan); }
.read-btn.active { 
  background: rgba(0, 229, 255, 0.1); 
  color: var(--cyan); 
  border-left: 2px solid var(--cyan); 
  box-shadow: inset 2px 0 8px rgba(0, 229, 255, 0.05);
}
.read-btn.loading { opacity: .5; }
.diag-output { flex: 1; overflow: hidden; display: flex; flex-direction: column; background: var(--bg); }
.output-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.placeholder { 
  color: var(--text); 
  font-size: 14px; 
  padding: 32px; 
  font-family: var(--font-hd);
  letter-spacing: 1px;
}
.output-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px; border-bottom: 1px solid var(--border);
  background: var(--bg3);
  font-size: 12px; color: var(--textwh);
  font-family: var(--font-hd);
  letter-spacing: 0.5px;
}
.output-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--cyan);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
}
.pulse-indicator {
  width: 6px;
  height: 6px;
  background: var(--cyan);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--cyan);
  animation: pulse-cyan 1.5s infinite alternate;
}
@keyframes pulse-cyan {
  from { opacity: 0.4; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1.2); }
}
.header-search {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  width: 240px;
  transition: all 0.2s;
}
.header-search:focus-within {
  border-color: var(--cyan);
  box-shadow: var(--shadow-c);
}
.search-icon {
  font-size: 11px;
  margin-right: 6px;
  opacity: 0.6;
}
.search-input {
  background: none;
  border: none;
  outline: none;
  color: var(--textwh);
  font-size: 11px;
  font-family: var(--font-ui);
  width: 100%;
}
.header-btns { display: flex; gap: 8px; }
.copy-btn, .clear-btn, .refresh-btn {
  font-family: var(--font-ui);
  font-size: 11px; padding: 4px 10px;
  background: var(--bg4); border: 1px solid var(--border);
  border-radius: 4px; color: var(--textbr); cursor: pointer; transition: all .15s;
  display: flex; align-items: center; gap: 4px;
}
.copy-btn:hover, .refresh-btn:hover { 
  background: var(--border); 
  color: var(--cyan); 
  border-color: var(--cyan);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.1);
}
.clear-btn:hover { 
  background: var(--border);
  color: var(--pink); 
  border-color: var(--pink); 
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.1);
}
.copy-btn.ok { background: rgba(0, 255, 157, 0.1); border-color: var(--green); color: var(--green); }

/* Loader scanner styles */
.loader-scanner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  flex: 1;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at center, rgba(0, 229, 255, 0.04) 0%, transparent 75%);
}
.loader-grid {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-size: 24px 24px;
  background-image: 
    linear-gradient(to right, rgba(0, 229, 255, 0.02) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(0, 229, 255, 0.02) 1px, transparent 1px);
  pointer-events: none;
}
.loader-line {
  position: absolute;
  left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--cyan), transparent);
  box-shadow: 0 0 8px var(--cyan), 0 0 16px var(--cyan);
  animation: scan-anim 2.5s infinite linear;
  opacity: 0.7;
}
@keyframes scan-anim {
  0% { top: 0%; }
  50% { top: 100%; }
  100% { top: 0%; }
}
.loader-text {
  font-family: var(--font-co);
  font-size: 13px;
  color: var(--cyan);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
  letter-spacing: 0.15em;
  margin-top: 16px;
  animation: blink-anim 1s infinite alternate;
}
@keyframes blink-anim {
  from { opacity: 0.5; }
  to { opacity: 1; }
}

.output-error {
  margin: 16px; padding: 12px 16px;
  background: rgba(255, 45, 110, 0.06); border: 1px solid var(--pink);
  border-radius: 6px; color: var(--pink); font-size: 12px;
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.05);
}
.output-fix-box {
    margin: 20px; padding: 20px;
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: 8px; text-align: center;
}
.fix-msg { font-size: 13px; color: var(--textwh); margin-bottom: 16px; }
.btn-install-tool {
    padding: 10px 24px; background: var(--green); color: var(--bg);
    border: none; border-radius: 4px; font-family: var(--font-hd);
    font-size: 11px; cursor: pointer; transition: all 0.2s;
}
.btn-install-tool:hover:not(:disabled) { box-shadow: var(--shadow-g); }
.btn-install-tool:disabled { opacity: 0.5; cursor: wait; }
.raw-err { margin-top: 20px; font-size: 10px; color: var(--text); text-align: left; opacity: 0.5; }
.output-pre {
  flex: 1; overflow: auto; margin: 0;
  padding: 16px;
  font-family: var(--font-co);
  font-size: 12px; line-height: 1.6;
  color: var(--textbr); white-space: pre-wrap; word-break: break-all;
  background: var(--bg);
}

/* Terminal colors */
:deep(.term-ok) {
  color: var(--green);
  text-shadow: 0 0 6px rgba(0, 255, 157, 0.4);
  font-weight: 600;
}
:deep(.term-err) {
  color: var(--pink);
  text-shadow: 0 0 6px rgba(255, 45, 110, 0.4);
  font-weight: 600;
}
:deep(.term-ip) {
  color: var(--cyan);
  text-shadow: 0 0 4px rgba(0, 229, 255, 0.3);
}
:deep(.term-mac) {
  color: var(--yellow);
}
:deep(.term-int) {
  color: var(--orange);
  font-weight: 600;
}
:deep(.search-match) {
  background: rgba(255, 190, 11, 0.25);
  border-bottom: 1px solid var(--yellow);
  color: var(--textwh);
  padding: 1px 2px;
  border-radius: 2px;
  text-shadow: 0 0 4px rgba(255, 190, 11, 0.5);
}

.wg-quick-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(8, 13, 24, 0.4);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(10px);
}
.wg-control-info {
  display: flex;
  align-items: center;
}
.control-label {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.05em;
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}
.wg-control-btns {
  display: flex;
  gap: 12px;
}
.btn-wg-up, .btn-wg-down {
  padding: 6px 14px;
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  border-radius: 4px;
  cursor: pointer;
  background: none;
  transition: all 0.2s ease-in-out;
  letter-spacing: 0.05em;
}
.btn-wg-up {
  border: 1px solid var(--green);
  color: var(--green);
}
.btn-wg-up:hover:not(:disabled) {
  background: rgba(0, 255, 157, 0.1);
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.3);
  text-shadow: 0 0 4px rgba(0, 255, 157, 0.5);
}
.btn-wg-down {
  border: 1px solid var(--pink);
  color: var(--pink);
}
.btn-wg-down:hover:not(:disabled) {
  background: rgba(255, 45, 110, 0.1);
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.3);
  text-shadow: 0 0 4px rgba(255, 45, 110, 0.5);
}
.btn-wg-up:disabled, .btn-wg-down:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
