<template>
  <div class="results-table-wrapper">
    <table class="cyber-table">
      <thead>
        <tr>
          <th v-for="(h, idx) in resultsHeaders" :key="h" class="resizable-th">
            {{ h }}
            <div class="resize-handle" @mousedown="startResize($event, idx)"></div>
          </th>
          <th v-if="!isReadOnly" class="actions-header">HANDLINGER</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in resultsRows" :key="idx" class="result-row">
          <!-- Columns rendering -->
          <td 
            v-for="h in resultsHeaders" 
            :key="h" 
            :class="['mono', 'text-cell', { 'read-only': isReadOnly }]"
            @dblclick="!isReadOnly && startInlineEdit(idx, h, row[h])"
          >
            <!-- Inline Editor -->
            <div v-if="!isReadOnly && inlineEditRow === idx && inlineEditCol === h" class="inline-edit-input-box">
              <input 
                v-model="inlineEditValue" 
                ref="inlineInputRef"
                @blur="confirmInlineEdit(row, nodeId)" 
                @keyup.enter="confirmInlineEdit(row, nodeId)"
                @keyup.esc="cancelInlineEdit"
                class="inline-edit-input"
              />
            </div>
            <span v-else :class="getCellClass(row[h])">{{ formatCellValue(row[h]) }}</span>
          </td>
          
          <!-- Actions Column -->
          <td v-if="!isReadOnly">
            <div class="row-actions-cell">
              <button class="btn-icon-action btn-delete-row" title="Slet række" @click="deleteRow(row, nodeId)">✕</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDatabaseQuery } from '@/composables/useDatabaseQuery'
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'

const props = defineProps<{ nodeId: string }>()

const { isReadOnly } = useDatabaseConfig()

const {
  resultsHeaders,
  resultsRows,
  inlineEditRow,
  inlineEditCol,
  inlineEditValue,
  inlineInputRef,
  formatCellValue,
  getCellClass,
  startInlineEdit,
  cancelInlineEdit,
  confirmInlineEdit,
  deleteRow
} = useDatabaseQuery()

// Resizable columns logic
let startX = 0
let startWidth = 0
let activeColIdx = -1

function startResize(e: MouseEvent, index: number) {
  e.preventDefault()
  activeColIdx = index
  startX = e.clientX
  
  const handle = e.currentTarget as HTMLElement
  const th = handle.parentElement as HTMLTableCellElement
  startWidth = th.offsetWidth
  
  window.addEventListener('mousemove', handleResize)
  window.addEventListener('mouseup', stopResize)
}

function handleResize(e: MouseEvent) {
  if (activeColIdx === -1) return
  const diff = e.clientX - startX
  const newWidth = Math.max(50, startWidth + diff)
  
  // Find all th elements in the results data grid
  const ths = document.querySelectorAll('.results-table-wrapper th') as NodeListOf<HTMLTableCellElement>
  if (ths && ths[activeColIdx]) {
    ths[activeColIdx].style.width = `${newWidth}px`
    ths[activeColIdx].style.minWidth = `${newWidth}px`
  }
}

function stopResize() {
  activeColIdx = -1
  window.removeEventListener('mousemove', handleResize)
  window.removeEventListener('mouseup', stopResize)
}
</script>

<style scoped>
.results-table-wrapper {
  overflow-x: auto;
  max-height: 480px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: rgba(4, 7, 14, 0.4);
}

.cyber-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.cyber-table th {
  background: rgba(13, 20, 38, 0.7);
  border-bottom: 2px solid var(--cyan);
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 1px;
  padding: 10px 14px;
  font-weight: 700;
  text-shadow: 0 0 4px rgba(0, 229, 255, 0.3);
  position: relative;
}

.cyber-table td {
  padding: 10px 14px;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
  transition: background 0.2s;
}

.result-row {
  transition: all 0.2s;
}

.result-row:hover {
  background: rgba(0, 229, 255, 0.03) !important;
}

.mono {
  font-family: var(--font-co);
}

.font-green {
  color: var(--green) !important;
}

.font-gray {
  color: var(--text) !important;
}

.font-small {
  font-size: 10.5px;
}

.italic {
  font-style: italic;
}

.text-cell {
  position: relative;
}

.text-cell:not(.read-only) {
  cursor: cell;
}

.text-cell:not(.read-only):hover {
  background: rgba(255, 255, 255, 0.02) !important;
}

.inline-edit-input-box {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #020408;
  z-index: 10;
}

.inline-edit-input {
  width: 100%;
  height: 100%;
  border: 1px solid var(--cyan);
  background: transparent;
  color: var(--textwh);
  padding: 0 8px;
  font-family: var(--font-co);
  font-size: 11px;
  outline: none;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
}

.actions-header {
  width: 80px;
  text-align: center;
}

.row-actions-cell {
  display: flex;
  justify-content: center;
}

.btn-icon-action {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--border);
  color: var(--textwh);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-icon-action:hover {
  border-color: var(--cyan);
  color: #fff;
  background: rgba(0, 229, 255, 0.15);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
  transform: translateY(-1px);
}

.btn-delete-row:hover {
  border-color: var(--pink) !important;
  color: #fff !important;
  background: rgba(255, 45, 110, 0.2) !important;
  box-shadow: 0 0 8px rgba(255, 45, 110, 0.4) !important;
}

.resizable-th {
  position: relative;
  user-select: none;
}

.resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 10;
  transition: background 0.15s;
}

.resize-handle:hover {
  background: rgba(0, 229, 255, 0.5);
}
</style>
