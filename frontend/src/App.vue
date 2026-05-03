<template>
  <div class="app">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">⚡</span>
          <span class="logo-text">netrunner</span>
        </div>
        <button class="btn-add" @click="showAddForm = true" title="Add node">+</button>
      </div>

      <div v-if="store.loading" class="sidebar-info">loading…</div>
      <div v-if="store.error" class="sidebar-error">{{ store.error }}</div>

      <div class="sidebar-search">
        <input v-model="searchQuery" placeholder="Search nodes…" class="search-input" />
      </div>

      <div class="node-list">
        <div
          v-for="node in filteredNodes"
          :key="node.id"
          class="node-item"
          :class="{ active: store.selectedId === node.id }"
          @click="store.select(node.id)"
        >
          <span class="node-icon">{{ deviceIcon(node.device_type) }}</span>
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
          No nodes yet.<br>Click + to add one.
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="main">
      <div v-if="!store.selected" class="welcome">
        <div class="welcome-inner">
          <div class="welcome-logo">⚡ netrunner</div>
          <p>Select a node from the sidebar, or add a new one to get started.</p>
        </div>
      </div>

      <template v-else>
        <!-- Node header bar -->
        <div class="node-header">
          <div class="node-title">
            <span class="node-icon-lg">{{ deviceIcon(store.selected.device_type) }}</span>
            <div>
              <div class="node-title-name">{{ store.selected.name }}</div>
              <div class="node-title-sub">
                {{ store.selected.host }}:{{ store.selected.port }} · {{ store.selected.transport }}
                <span class="device-badge" :class="store.selected.device_type">{{ store.selected.device_type }}</span>
              </div>
            </div>
          </div>
          <div class="header-actions">
            <button @click="detectType" class="btn-action" title="Auto-detect device type">🔍 detect</button>
            <button @click="doBackup"   class="btn-action">💾 backup</button>
            <button @click="doRollback" class="btn-action">↩ rollback</button>
            <button @click="showEdit = true" class="btn-action">✏️ edit</button>
            <button @click="deleteNode" class="btn-action btn-danger">✕</button>
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
          <DiagPanel    v-if="activeTab === 'diag'"     :node-id="store.selected.id" />
          <ConfigPanel  v-if="activeTab === 'config'"   :node-id="store.selected.id" />
          <ExecPanel    v-if="activeTab === 'exec'"     :node-id="store.selected.id" />
          <Terminal     v-if="activeTab === 'terminal'" :node="store.selected" />
        </div>
      </template>
    </main>

    <!-- Modals -->
    <NodeForm v-if="showAddForm" @close="showAddForm = false" />
    <NodeForm v-if="showEdit"    :node="store.selected" @close="showEdit = false" />

    <!-- Flash messages -->
    <div class="flash-stack">
      <div v-for="msg in flashes" :key="msg.id" class="flash" :class="msg.type">{{ msg.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'
import DiagPanel from './components/DiagPanel.vue'
import ExecPanel from './components/ExecPanel.vue'
import ConfigPanel from './components/ConfigPanel.vue'
import Terminal  from './components/Terminal.vue'
import NodeForm  from './components/NodeForm.vue'
import type { NrNode } from '@/types'

const store       = useNodesStore()
const activeTab   = ref<'diag' | 'config' | 'exec' | 'terminal'>('diag')
const showAddForm = ref(false)
const showEdit    = ref(false)
const searchQuery = ref('')

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
  { id: 'diag',     label: '🔎 Diagnostics' },
  { id: 'config',   label: '🛠 Config' },
  { id: 'exec',     label: '⚙️ Execute' },
  { id: 'terminal', label: '⚡ Terminal' },
] as const

interface Flash { id: number; text: string; type: 'ok' | 'err' }
const flashes = ref<Flash[]>([])
let flashId = 0

function flash(text: string, type: 'ok' | 'err' = 'ok') {
  const id = flashId++
  flashes.value.push({ id, text, type })
  setTimeout(() => { flashes.value = flashes.value.filter(f => f.id !== id) }, 3500)
}

function deviceIcon(type: NrNode['device_type']) {
  return { linux: '🐧', rpi: '🍓', gns3: '🌐', unknown: '❓' }[type] ?? '❓'
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

watch(() => store.selectedId, () => { activeTab.value = 'diag' })

onMounted(() => store.refresh())
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #app { height: 100%; }
body {
  background: #0d1117;
  color: #c9d1d9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #484f58; }
</style>

<style scoped>
.app { display: flex; height: 100vh; overflow: hidden; }

.sidebar { width: 240px; min-width: 240px; background: #010409; border-right: 1px solid #21262d; display: flex; flex-direction: column; }
.sidebar-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 12px 8px; border-bottom: 1px solid #21262d; }
.logo { display: flex; align-items: center; gap: 6px; }
.logo-icon { font-size: 18px; }
.logo-text { font-size: 15px; font-weight: 700; color: #58a6ff; letter-spacing: -.02em; }
.btn-add { width: 26px; height: 26px; border-radius: 6px; background: #1f6feb; border: none; color: #fff; font-size: 18px; line-height: 1; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.btn-add:hover { background: #388bfd; }
.sidebar-info, .sidebar-empty { padding: 16px 12px; color: #6e7681; font-size: 12px; }
.sidebar-error { padding: 8px 12px; background: #1a0a0a; color: #f85149; font-size: 12px; }
.node-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.node-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; border-left: 3px solid transparent; }
.node-item:hover { background: #0d1117; }
.node-item.active { background: #1c2128; border-left-color: #58a6ff; }
.node-icon { font-size: 18px; }
.node-meta { flex: 1; min-width: 0; }
.node-name { font-size: 13px; font-weight: 500; color: #e6edf3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-host { font-size: 11px; color: #6e7681; }
.node-transport { font-size: 10px; padding: 2px 5px; border-radius: 3px; font-weight: 500; flex-shrink: 0; }
.sidebar-search { padding: 6px 8px; border-bottom: 1px solid #21262d; }
.search-input { width: 100%; padding: 5px 8px; font-size: 12px; background: #1c2128; border: 1px solid #30363d; border-radius: 4px; color: #c9d1d9; outline: none; box-sizing: border-box; }
.search-input:focus { border-color: #58a6ff; }
.node-tags { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 3px; }
.tag-chip { font-size: 9px; padding: 1px 5px; border-radius: 3px; background: #21262d; color: #6e7681; border: 1px solid #30363d; }
.node-transport.ssh    { background: #1c3a5c; color: #79c0ff; }
.node-transport.telnet { background: #2d1b00; color: #d29922; }

.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.welcome { flex: 1; display: flex; align-items: center; justify-content: center; }
.welcome-inner { text-align: center; color: #6e7681; }
.welcome-logo { font-size: 28px; font-weight: 700; color: #58a6ff; margin-bottom: 12px; }

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid #21262d; background: #010409; }
.node-title { display: flex; align-items: center; gap: 10px; }
.node-icon-lg { font-size: 24px; }
.node-title-name { font-size: 16px; font-weight: 600; color: #e6edf3; }
.node-title-sub { font-size: 12px; color: #8b949e; margin-top: 1px; }
.device-badge { display: inline-block; padding: 1px 6px; border-radius: 8px; font-size: 10px; margin-left: 6px; font-weight: 500; }
.device-badge.linux   { background: #1f3a1f; color: #3fb950; }
.device-badge.rpi     { background: #3a1f2e; color: #e85480; }
.device-badge.gns3    { background: #1f2a3a; color: #58a6ff; }
.device-badge.unknown { background: #1f1f1f; color: #6e7681; }
.header-actions { display: flex; gap: 6px; }
.btn-action { padding: 5px 10px; font-size: 12px; border-radius: 6px; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; cursor: pointer; }
.btn-action:hover { background: #30363d; }
.btn-danger { border-color: #491c1c; color: #f85149; }
.btn-danger:hover { background: #1a0000; }

.tab-bar { display: flex; border-bottom: 1px solid #21262d; background: #010409; padding: 0 12px; }
.tab { padding: 8px 14px; font-size: 13px; background: none; border: none; border-bottom: 2px solid transparent; color: #8b949e; cursor: pointer; }
.tab:hover { color: #c9d1d9; }
.tab.active { color: #e6edf3; border-bottom-color: #58a6ff; }
.tab-content { flex: 1; overflow: hidden; display: flex; flex-direction: column; }

.flash-stack { position: fixed; bottom: 16px; right: 16px; display: flex; flex-direction: column; gap: 8px; z-index: 200; }
.flash { padding: 10px 16px; border-radius: 8px; font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,.4); }
.flash.ok  { background: #1f3a1f; border: 1px solid #3fb950; color: #3fb950; }
.flash.err { background: #1a0a0a; border: 1px solid #f85149; color: #f85149; }
</style>
