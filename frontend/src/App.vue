<template>
  <div class="app">
    <div class="scanline"></div>
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-title">NETRUNNER</span>
          <span class="logo-sub">OS v1.0.0</span>
        </div>
        <div class="header-tools">
          <button class="btn-icon" @click="showSettings = true" title="Settings">⚙️</button>
          <button class="btn-add" @click="showAddForm = true" title="Add node">+</button>
        </div>
      </div>

      <div class="sidebar-stats">
        <div class="sidebar-stat">
          <div class="stat-label">NODES</div>
          <div class="stat-value">{{ store.nodeList.length }}</div>
        </div>
        <div class="sidebar-stat">
          <div class="stat-label">LIVE</div>
          <div class="stat-value" :class="{ 'text-green': store.connectedCount > 0 }">{{ store.connectedCount }}</div>
        </div>
      </div>

      <div class="sidebar-nav">
        <button 
          class="btn-nav" 
          :class="{ active: viewMode === 'node' }" 
          @click="viewMode = 'node'"
        >NODES</button>
        <button 
          class="btn-nav" 
          :class="{ active: viewMode === 'topology' }" 
          @click="viewMode = 'topology'"
        >TOPOLOGY</button>
      </div>

      <div v-if="store.loading" class="sidebar-info">SCANNING NEURAL LINK...</div>
      <div v-if="store.error" class="sidebar-error">{{ store.error }}</div>

      <div class="sidebar-search">
        <input v-model="searchQuery" placeholder="FILTER NODES..." class="search-input" />
      </div>

      <div class="node-list">
        <div
          v-for="node in filteredNodes"
          :key="node.id"
          class="node-item"
          :class="{ active: store.selectedId === node.id }"
          @click="store.select(node.id)"
        >
          <div 
            class="node-dot" 
            :class="{ 
              connected: store.isConnected(node.id),
              'manually-off': !store.isConnected(node.id) && store.manuallyDisconnected.has(node.id)
            }"
          ></div>
          <div class="node-meta">
            <div class="node-name">{{ node.name }}</div>
            <div class="node-host">{{ node.host }}:{{ node.port }}</div>
            <div class="node-tags" v-if="node.tags && node.tags.length">
              <span v-for="tag in node.tags.slice(0, 3)" :key="tag" class="tag-chip">{{ tag }}</span>
            </div>
          </div>
          <span class="node-transport" :class="node.transport">{{ node.transport }}</span>
        </div>
        <div v-if="!store.loading && filteredNodes.length === 0" class="sidebar-empty">
          NO NODES DETECTED.
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="main">
      <TopologyView v-if="viewMode === 'topology'" />
      
      <div v-else-if="!store.selected" class="welcome">
        <div class="welcome-inner">
          <div class="welcome-logo">NETRUNNER</div>
          <div class="welcome-sub">AWAITING NEURAL CONNECTION...</div>
        </div>
      </div>

      <template v-else>
        <!-- Node header bar -->
        <div class="node-header">
          <div class="node-title">
            <div class="node-dot-lg" :class="{ connected: store.isConnected(store.selected.id) }"></div>
            <div>
              <div class="node-title-name">{{ store.selected.name }}</div>
              <div class="node-title-sub">
                {{ store.selected.host }}:{{ store.selected.port }} · {{ store.selected.transport }}
                <span class="device-badge" :class="store.selected.device_type">{{ store.selected.device_type }}</span>
              </div>
            </div>
          </div>
          <div class="header-actions">
            <button v-if="!store.isConnected(store.selected.id)" @click="doConnect" class="btn-action" :disabled="connBusy">CONNECT</button>
            <button v-else @click="doDisconnect" class="btn-action" :disabled="connBusy">DISCONNECT</button>
            <button @click="detectType" class="btn-action">DETECT</button>
            <button @click="doBackup"   class="btn-action">BACKUP</button>
            <button @click="doRollback" class="btn-action">ROLLBACK</button>
            <button @click="deleteNode" class="btn-action btn-danger">NUKE CONFIG</button>
          </div>
        </div>

        <!-- Tab bar -->
        <div class="tab-bar">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="tab"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >{{ tab.label }}</button>
        </div>

        <!-- Tab content -->
        <div class="tab-content">
          <OverviewPanel v-if="activeTab === 'overview'" :node-id="store.selected.id" />
          <DiagPanel    v-if="activeTab === 'diag'"     :node-id="store.selected.id" />
          <ConfigPanel  v-if="activeTab === 'config'"   :node-id="store.selected.id" />
          <ExecPanel    v-if="activeTab === 'exec'"     :node-id="store.selected.id" />
          <CapturePanel v-if="activeTab === 'capture'"  :node-id="store.selected.id" />
          <Terminal     v-if="activeTab === 'terminal'" :node="store.selected" />
        </div>
      </template>
    </main>

    <!-- Modals -->
    <NodeForm v-if="showAddForm" @close="showAddForm = false" />
    <NodeForm v-if="showEdit"    :node="store.selected" @close="showEdit = false" />
    <SettingsModal v-if="showSettings" @close="showSettings = false" />

    <!-- Flash messages -->
    <div class="flash-stack">
      <div v-for="msg in flashes" :key="msg.id" class="flash" :class="msg.type">{{ msg.text }}</div>
    </div>

    <!-- AI Sidebar -->
    <AiChatSidebar />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'
import DiagPanel from './components/DiagPanel.vue'
import ExecPanel from './components/ExecPanel.vue'
import ConfigPanel from './components/ConfigPanel.vue'
import CapturePanel from './components/CapturePanel.vue'
import OverviewPanel from './components/OverviewPanel.vue'
import Terminal  from './components/Terminal.vue'
import NodeForm  from './components/NodeForm.vue'
import TopologyView from './components/TopologyView.vue'
import AiChatSidebar from './components/AiChatSidebar.vue'
import SettingsModal from './components/SettingsModal.vue'
import type { NrNode } from '@/types'

const store       = useNodesStore()
const viewMode    = ref<'node' | 'topology'>('node')
const activeTab   = ref<'overview' | 'diag' | 'config' | 'exec' | 'capture' | 'terminal'>('overview')
const showAddForm = ref(false)
const showEdit    = ref(false)
const showSettings = ref(false)
const searchQuery = ref('')
const connBusy    = ref(false)
const exporting   = ref(false)

const filteredNodes = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return store.nodeList
  return store.nodeList.filter(n =>
    n.name.toLowerCase().includes(q) ||
    n.host.toLowerCase().includes(q) ||
    (n.tags ?? []).some(t => t.toLowerCase().includes(q))
  )
})

const tabs = [
  { id: 'overview', label: 'OVERVIEW' },
  { id: 'diag',     label: 'DIAGNOSTICS' },
  { id: 'config',   label: 'CONFIG' },
  { id: 'exec',     label: 'EXECUTE' },
  { id: 'capture',  label: 'CAPTURE' },
  { id: 'terminal', label: 'TERMINAL' },
] as const

interface Flash { id: number; text: string; type: 'ok' | 'err' }
const flashes = ref<Flash[]>([])
let flashId = 0

function flash(text: string, type: 'ok' | 'err' = 'ok') {
  const id = flashId++
  flashes.value.push({ id, text, type })
  setTimeout(() => { flashes.value = flashes.value.filter(f => f.id !== id) }, 3500)
}

async function doConnect() {
  if (!store.selected) return
  connBusy.value = true
  try {
    await api.connectNode(store.selected.id)
    store.manuallyDisconnected.delete(store.selected.id)
    await store.refreshConnections()
    flash(`Connected to ${store.selected.name}`)
  } catch (e) {
    flash(String(e), 'err')
  } finally {
    connBusy.value = false
  }
}

async function doDisconnect() {
  if (!store.selected) return
  connBusy.value = true
  try {
    await api.disconnectNode(store.selected.id)
    store.manuallyDisconnected.add(store.selected.id)
    await store.refreshConnections()
    flash(`Disconnected ${store.selected.name}`)
  } catch (e) {
    flash(String(e), 'err')
  } finally {
    connBusy.value = false
  }
}

async function detectType() {
  if (!store.selected) return
  try {
    const t = await store.detectType(store.selected.id)
    flash(`Device detected: ${t}`)
  } catch (e) {
    flash(String(e), 'err')
  }
}

async function doBackup() {
  if (!store.selected) return
  try {
    await api.backupNode(store.selected.id)
    flash('Backup created')
  } catch (e) {
    flash(String(e), 'err')
  }
}

async function doExport() {
  if (!store.selected) return
  exporting.value = true
  try {
    const res = await api.exportNode(store.selected.id, {})
    const errs = Object.keys(res.diagnostic_errors || {}).length
    flash(errs ? `Export ready (${errs} diag errors)` : 'Export ready')
    const a = document.createElement('a')
    a.href = api.exportDownloadUrl(res.name)
    a.download = res.name
    document.body.appendChild(a); a.click(); a.remove()
  } catch (e) {
    flash(String(e), 'err')
  } finally {
    exporting.value = false
  }
}

async function doRollback() {
  if (!store.selected) return
  if (!confirm(`Rollback ${store.selected.name}? This restores the last backup.`)) return
  try {
    await api.rollbackNode(store.selected.id)
    flash('Rollback complete')
  } catch (e) {
    flash(String(e), 'err')
  }
}

async function deleteNode() {
  if (!store.selected) return
  if (!confirm(`Delete node "${store.selected.name}"?`)) return
  try {
    await store.remove(store.selected.id)
    flash('Node deleted')
  } catch (e) {
    flash(String(e), 'err')
  }
}

watch(() => store.selectedId, () => {
  activeTab.value = 'overview'
  store.refreshConnections()
})

let connTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  store.refresh()
  connTimer = setInterval(() => store.refreshConnections(), 4000)
})
onUnmounted(() => { if (connTimer) clearInterval(connTimer) })
</script>

<style scoped>
.app { display: flex; height: 100vh; overflow: hidden; position: relative; z-index: 1; }

/* Sidebar */
.sidebar { width: 270px; min-width: 270px; background: var(--bg2); border-right: 1px solid var(--border); display: flex; flex-direction: column; position: relative; }
.sidebar::after { content: ''; position: absolute; top: 0; right: 0; width: 1px; height: 100%; background: linear-gradient(to bottom, transparent, var(--cyan), transparent); opacity: .4; }

.sidebar-header { padding: 22px 20px 18px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.header-tools { display: flex; align-items: center; gap: 10px; }
.logo { line-height: 1; }
.logo-title { font-family: var(--font-hd); font-size: 15px; font-weight: 900; letter-spacing: 3px; color: var(--green); text-shadow: 0 0 12px rgba(0,255,157,.6); }
.logo-sub { display: block; font-family: var(--font-co); font-size: 9px; letter-spacing: 2px; color: var(--text); margin-top: 5px; text-transform: uppercase; }

.btn-icon { background: none; border: none; font-size: 16px; cursor: pointer; opacity: 0.6; transition: opacity 0.2s; padding: 0; display: flex; align-items: center; justify-content: center; }
.btn-icon:hover { opacity: 1; filter: drop-shadow(0 0 5px var(--cyan)); }

.btn-add { width: 28px; height: 28px; border-radius: 50%; background: none; border: 1px solid var(--cyan); color: var(--cyan); font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .2s; }
.btn-add:hover { background: var(--cyan); color: var(--bg); box-shadow: var(--shadow-c); }

.sidebar-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 14px 20px; border-bottom: 1px solid var(--border); }
.sidebar-stat { background: linear-gradient(180deg, rgba(0,229,255,.08), rgba(16,24,40,.5)); border: 1px solid var(--border); border-radius: var(--r); padding: 10px; }
.stat-label { font-family: var(--font-hd); font-size: 8px; letter-spacing: 1.5px; color: var(--text); text-transform: uppercase; }
.stat-value { margin-top: 4px; font-family: var(--font-co); font-size: 16px; color: var(--textwh); }
.text-green { color: var(--green); text-shadow: 0 0 8px var(--green); }

.sidebar-nav { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--border); padding: 1px; border-bottom: 1px solid var(--border); }
.btn-nav { background: var(--bg2); border: none; color: var(--text); padding: 10px; font-family: var(--font-hd); font-size: 9px; letter-spacing: 1.5px; cursor: pointer; transition: all .2s; }
.btn-nav:hover { color: var(--textwh); background: var(--bg3); }
.btn-nav.active { color: var(--cyan); background: var(--bg3); box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.05); }

.sidebar-search { padding: 12px 14px; }
.search-input { width: 100%; padding: 10px 12px; background: var(--bg3); border: 1px solid var(--border); border-radius: var(--r); color: var(--textwh); font-family: var(--font-co); font-size: 11px; outline: none; }
.search-input:focus { border-color: var(--cyan); box-shadow: 0 0 8px rgba(0,229,255,.2); }

.node-list { flex: 1; overflow-y: auto; padding: 4px 10px; }
.node-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: var(--r); cursor: pointer; border: 1px solid transparent; margin-bottom: 4px; transition: all .18s; position: relative; }
.node-item:hover { background: var(--bg3); border-color: var(--border); }
.node-item.active { background: rgba(0,255,157,.06); border-color: rgba(0,255,157,.3); }
.node-item.active::before { content: ''; position: absolute; left: 0; top: 20%; height: 60%; width: 2px; background: var(--green); box-shadow: 0 0 8px var(--green); }

.node-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--border2); flex-shrink: 0; }
.node-dot.connected { background: var(--green); box-shadow: 0 0 8px var(--green); animation: pulse-green 2s infinite; }
.node-dot.manually-off { background: var(--pink); box-shadow: 0 0 8px var(--pink); }

@keyframes pulse-green { 0% { opacity: 1; } 50% { opacity: .5; } 100% { opacity: 1; } }

.node-meta { flex: 1; min-width: 0; }
.node-name { font-family: var(--font-co); font-size: 12px; color: var(--textwh); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-host { font-family: var(--font-co); font-size: 10px; color: var(--text); }
.node-transport { font-family: var(--font-hd); font-size: 8px; letter-spacing: 1px; padding: 2px 6px; border-radius: 4px; background: var(--bg4); border: 1px solid var(--border); text-transform: uppercase; }
.node-transport.ssh { color: var(--cyan); border-color: var(--cyan-d); }
.node-transport.telnet { color: var(--yellow); border-color: var(--orange); }

.sidebar-info, .sidebar-empty { padding: 20px; text-align: center; font-family: var(--font-hd); font-size: 10px; color: var(--text); letter-spacing: 1px; }

/* Main */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg); position: relative; }

.welcome { flex: 1; display: flex; align-items: center; justify-content: center; }
.welcome-logo { font-family: var(--font-hd); font-size: 42px; font-weight: 900; letter-spacing: 8px; color: var(--green); text-shadow: 0 0 20px var(--green); margin-bottom: 10px; }
.welcome-sub { font-family: var(--font-co); font-size: 11px; letter-spacing: 3px; color: var(--text); }

.node-header { padding: 16px 24px; background: var(--bg2); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.node-title { display: flex; align-items: center; gap: 14px; }
.node-dot-lg { width: 12px; height: 12px; border-radius: 50%; background: var(--border2); }
.node-dot-lg.connected { background: var(--green); box-shadow: 0 0 12px var(--green); }
.node-title-name { font-family: var(--font-hd); font-size: 18px; font-weight: 700; color: var(--textwh); letter-spacing: 1px; }
.node-title-sub { font-family: var(--font-co); font-size: 11px; color: var(--text); margin-top: 4px; }
.device-badge { margin-left: 8px; padding: 2px 8px; border-radius: 4px; font-size: 9px; text-transform: uppercase; font-family: var(--font-hd); border: 1px solid var(--border); }
.device-badge.linux { color: var(--green); border-color: var(--green); }
.device-badge.rpi { color: var(--pink); border-color: var(--pink); }
.device-badge.gns3 { color: var(--cyan); border-color: var(--cyan); }

.header-actions { display: flex; gap: 8px; }
.btn-action { background: var(--bg3); border: 1px solid var(--border); color: var(--textwh); padding: 6px 12px; border-radius: var(--r); font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; cursor: pointer; transition: all .2s; }
.btn-action:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); box-shadow: var(--shadow-c); }
.btn-action:disabled { opacity: .4; cursor: not-allowed; }

.btn-danger { border-color: var(--pink); color: var(--pink); }
.btn-danger:hover:not(:disabled) { 
  background: rgba(255, 45, 110, 0.2); 
  border-color: #ff0055; 
  color: #ff0055; 
  box-shadow: 0 0 15px #ff0055, inset 0 0 10px rgba(255, 0, 85, 0.3);
  text-shadow: 0 0 5px #ff0055;
}

.tab-bar { background: var(--bg2); border-bottom: 1px solid var(--border); display: flex; padding: 0 14px; }
.tab { background: none; border: none; padding: 12px 18px; font-family: var(--font-hd); font-size: 10px; letter-spacing: 2px; color: var(--text); cursor: pointer; position: relative; transition: color .2s; }
.tab:hover { color: var(--textwh); }
.tab.active { color: var(--cyan); }
.tab.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: var(--cyan); box-shadow: 0 0 8px var(--cyan); }

.tab-content { flex: 1; overflow: hidden; position: relative; }

.flash-stack { position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; gap: 10px; z-index: 1000; }
.flash { padding: 14px 20px; border-radius: var(--r); font-family: var(--font-co); font-size: 12px; border: 1px solid var(--border); min-width: 240px; box-shadow: 0 8px 32px rgba(0,0,0,.5); backdrop-filter: blur(8px); animation: slide-in .3s ease-out; }
@keyframes slide-in { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.flash.ok { background: rgba(0,255,157,.1); border-color: var(--green); color: var(--green); }
.flash.err { background: rgba(255,45,110,.1); border-color: var(--pink); color: var(--pink); }
</style>
