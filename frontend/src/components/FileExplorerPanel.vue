<template>
  <div class="file-explorer-panel">
    <div class="panel-header border-cyan">
      <span class="panel-title">📂 REMOTE FS / DATA EXTRACTOR</span>
      <div class="path-bar">
        <span class="path-label">TARGET PATH:</span>
        <div class="breadcrumb">
          <span 
            v-for="(part, i) in pathParts" 
            :key="i"
            class="crumb"
            @click="navigateToIndex(i)"
          >
            {{ part || '/' }}
          </span>
        </div>
        <input 
          v-model="inputPath" 
          @keyup.enter="loadDir(inputPath)" 
          class="cyber-input path-input" 
          placeholder="/var/log..." 
        />
        <button class="btn-cyber-submit sm" @click="loadDir(inputPath)" :disabled="loadingDir">
          GO
        </button>
      </div>
    </div>

    <div class="panel-body dual-pane">
      <!-- Left side: Directory listing -->
      <div class="dir-pane">
        <div v-if="loadingDir" class="loading-overlay">
          <span class="spinner"></span> SCANNING...
        </div>
        <div v-else-if="dirError" class="error-msg">{{ dirError }}</div>
        <div v-else class="file-list">
          <!-- Parent dir link -->
          <div 
            v-if="currentPath !== '/'" 
            class="file-row parent-row" 
            @click="navigateUp"
          >
            <span class="file-icon">📁</span>
            <span class="file-name">..</span>
          </div>

          <!-- Entries -->
          <div 
            v-for="entry in dirEntries" 
            :key="entry.name"
            class="file-row"
            :class="{ selected: selectedFile === entry.name }"
            @click="selectEntry(entry)"
            @dblclick="openEntry(entry)"
          >
            <span class="file-icon">{{ entry.is_dir ? '📁' : '📄' }}</span>
            <div class="file-info">
              <span class="file-name">{{ entry.name }}</span>
              <div class="file-meta">
                <span>{{ entry.permissions }}</span>
                <span>{{ entry.is_dir ? '-' : formatBytes(entry.size) }}</span>
              </div>
            </div>
          </div>
          
          <div v-if="dirEntries.length === 0" class="empty-state">
            DIRECTORY IS EMPTY
          </div>
        </div>
      </div>

      <!-- Right side: File preview -->
      <div class="preview-pane">
        <div v-if="loadingFile" class="loading-overlay">
          <span class="spinner"></span> EXTRACTING DATA...
        </div>
        <div v-else-if="fileError" class="error-msg">{{ fileError }}</div>
        <div v-else-if="fileContent !== null" class="content-viewer">
          <div class="content-header">
            <span>{{ selectedFile }}</span>
            <span class="content-size">{{ formatBytes(selectedFileSize) }}</span>
          </div>
          <textarea 
            class="content-textarea" 
            readonly 
            :value="fileContent"
            spellcheck="false"
          ></textarea>
        </div>
        <div v-else class="empty-preview">
          SELECT A FILE TO INITIATE DATA EXTRACTION
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ nodeId: string }>()

const currentPath = ref('/')
const inputPath = ref('/')
const dirEntries = ref<any[]>([])
const loadingDir = ref(false)
const dirError = ref('')

const selectedFile = ref('')
const selectedFileSize = ref(0)
const fileContent = ref<string | null>(null)
const loadingFile = ref(false)
const fileError = ref('')

const pathParts = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  return [''].concat(parts)
})

function formatBytes(bytes: number, decimals = 1) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

async function loadDir(path: string) {
  loadingDir.value = true
  dirError.value = ''
  try {
    const res = await api.listFiles(props.nodeId, path)
    currentPath.value = res.path
    inputPath.value = res.path
    dirEntries.value = res.entries
    // Clear preview if navigating away
    fileContent.value = null
    selectedFile.value = ''
    selectedFileSize.value = 0
    fileError.value = ''
  } catch (e: any) {
    dirError.value = e.message || String(e)
  } finally {
    loadingDir.value = false
  }
}

async function loadFile(path: string, size: number) {
  loadingFile.value = true
  fileError.value = ''
  try {
    const res = await api.readFile(props.nodeId, path)
    fileContent.value = res.content
    selectedFileSize.value = size
  } catch (e: any) {
    fileError.value = e.message || String(e)
    fileContent.value = null
  } finally {
    loadingFile.value = false
  }
}

function navigateToIndex(index: number) {
  const newParts = pathParts.value.slice(0, index + 1)
  let p = newParts.join('/')
  if (!p) p = '/'
  loadDir(p)
}

function navigateUp() {
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  let p = '/' + parts.join('/')
  loadDir(p)
}

function selectEntry(entry: any) {
  if (entry.is_dir) return
  selectedFile.value = entry.name
  let fullPath = currentPath.value
  if (!fullPath.endsWith('/')) fullPath += '/'
  fullPath += entry.name
  loadFile(fullPath, entry.size)
}

function openEntry(entry: any) {
  if (entry.is_dir) {
    let p = currentPath.value
    if (!p.endsWith('/')) p += '/'
    p += entry.name
    loadDir(p)
  }
}

watch(() => props.nodeId, () => {
  currentPath.value = '/'
  inputPath.value = '/'
  loadDir('/')
})

onMounted(() => {
  loadDir('/')
})
</script>

<style scoped>
.file-explorer-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(10, 16, 30, 0.7);
  border: 1px solid var(--border);
  border-radius: var(--r);
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.panel-header {
  padding: 10px 16px;
  background: rgba(8, 13, 24, 0.6);
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-header.border-cyan {
  border-left: 3px solid var(--cyan);
}

.panel-title {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 2px;
  color: var(--textwh);
}

.path-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg3);
  padding: 6px 12px;
  border-radius: var(--r);
  border: 1px solid var(--border);
}

.path-label {
  font-family: var(--font-hd);
  font-size: 9px;
  color: var(--cyan);
  letter-spacing: 1px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  font-family: var(--font-co);
  font-size: 11px;
  color: var(--text);
  overflow-x: auto;
  white-space: nowrap;
}

.crumb {
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}

.crumb:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--textwh);
}

.crumb::after {
  content: '/';
  margin: 0 4px;
  color: var(--border);
  pointer-events: none;
}

.crumb:last-child::after {
  display: none;
}

.path-input {
  flex: 1;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--cyan);
  color: var(--textwh);
  font-family: var(--font-co);
  font-size: 11px;
  padding: 4px;
  outline: none;
}

.btn-cyber-submit.sm {
  padding: 4px 10px;
  font-size: 9px;
}

.panel-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.dual-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--border);
}

@media (max-width: 900px) {
  .dual-pane {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
}

.dir-pane, .preview-pane {
  background: var(--bg);
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: all 0.2s;
}

.file-row:hover {
  background: rgba(255, 255, 255, 0.05);
}

.file-row.selected {
  background: rgba(0, 229, 255, 0.1);
  border-left-color: var(--cyan);
}

.file-icon {
  font-size: 14px;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.file-name {
  font-family: var(--font-co);
  font-size: 11px;
  color: var(--textwh);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-co);
  font-size: 9px;
  color: var(--text);
}

.empty-state, .empty-preview {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-hd);
  font-size: 10px;
  color: var(--text);
  letter-spacing: 2px;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(10, 16, 30, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 10;
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--cyan);
}

.error-msg {
  padding: 16px;
  color: var(--pink);
  font-family: var(--font-co);
  font-size: 11px;
}

.content-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.content-header {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  font-family: var(--font-co);
  font-size: 11px;
  color: var(--cyan);
}

.content-size {
  color: var(--text);
}

.content-textarea {
  flex: 1;
  background: transparent;
  border: none;
  padding: 16px;
  font-family: var(--font-co);
  font-size: 11px;
  color: var(--textwh);
  resize: none;
  outline: none;
  white-space: pre;
  overflow: auto;
}
</style>
