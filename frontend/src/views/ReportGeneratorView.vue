<template>
  <div class="report-generator-wrapper">
    <div class="top-controls">
      <button class="btn-action" @click="viewMode = 'builder'" :class="{ active: viewMode === 'builder' }">
        [ BUILDER ]
      </button>
      <button class="btn-action" @click="viewMode = 'current'" :class="{ active: viewMode === 'current' }">
        [ CURRENT STATUS ]
      </button>
      <button class="btn-action" @click="loadHistory" :class="{ active: viewMode === 'history' }">
        [ HISTORY ]
      </button>

      <div v-if="viewMode === 'current'" class="current-actions">
        <button class="btn-action" @click="saveReport" :disabled="saving">
          {{ saving ? 'SAVING...' : '[ SAVE TO ARCHIVE ]' }}
        </button>
        <button class="btn-pdf" @click="downloadPDF">
          [ EXPORT PDF ]
        </button>
        <button class="btn-pdf" @click="downloadTXT" v-if="hasGeneratedReport">
          [ EXPORT TXT ]
        </button>
      </div>
    </div>

    <!-- CURRENT REPORT VIEW -->
    <div v-if="viewMode === 'current'" class="report-container" ref="reportContainer">
      <div class="stamp-classified">TOP SECRET // CLASSIFIED</div>

      <div class="report-header">
        <h1>SECURITY ASSESSMENT REPORT</h1>
        <div class="meta-data">
          <p><strong>DATE:</strong> {{ new Date().toLocaleDateString() }}</p>
          <p><strong>AUTHORIZATION:</strong> CLEARANCE LEVEL 5</p>
          <p><strong>TARGET:</strong> {{ hasGeneratedReport ? (selectedNodesForReport.length > 1 ? 'MULTIPLE NODES' : 'SINGLE NODE') : 'MULTIPLE NODES' }}</p>
          <p><strong>REFERENCE:</strong> {{ currentReference }}-SEC</p>
          <p v-if="hasGeneratedReport && reportAuthor"><strong>CONFIGURATION BY:</strong> {{ reportAuthor }}</p>
        </div>
      </div>

      <div class="report-body">
        <div v-if="loading" class="loading-state">
          <span>DECRYPTING DATA STREAM...</span>
        </div>

        <div v-else>
          <div class="report-entry">
            <h3>[ LIVE SYSTEM SUMMARY ]</h3>
            <table class="data-table">
              <tbody>
                <tr>
                  <td><strong>TOTAL NODES</strong></td>
                  <td class="alert-val">{{ summary.nodesCount }}</td>
                </tr>
                <tr>
                  <td><strong>TOTAL ALERTS</strong></td>
                  <td class="alert-val">{{ summary.totalAlerts }}</td>
                </tr>
                <tr>
                  <td><strong>CRITICAL SEVERITY</strong></td>
                  <td class="alert-val" style="color:#c00;">{{ summary.criticalAlerts }}</td>
                </tr>
                <tr>
                  <td><strong>HIGH SEVERITY</strong></td>
                  <td class="alert-val" style="color:#f80;">{{ summary.highAlerts }}</td>
                </tr>
              </tbody>
            </table>

            <div v-if="summary.criticalAlerts > 0" class="critical-warning">
              WARNING: CRITICAL VULNERABILITIES DETECTED. IMMEDIATE ACTION REQUIRED.
            </div>
          </div>

          <div v-if="hasGeneratedReport && generatedNodesData.length > 0" class="report-entry">
            <h3>[ TABLE OF CONTENTS ]</h3>
            <div class="toc-body">
              <div v-for="nodeData in generatedNodesData" :key="'toc-' + nodeData.nodeId" class="toc-node">
                <a :href="'#node-' + nodeData.nodeId" class="toc-link node-link">► NODE: {{ nodeData.nodeName }} ({{ nodeData.nodeId }})</a>
                <div class="toc-items">
                  <div v-for="item in nodeData.items" :key="'toc-' + item.type">
                    <a :href="'#item-' + nodeData.nodeId + '-' + item.type" class="toc-link item-link">└ {{ item.label }}</a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-for="nodeData in generatedNodesData" :key="nodeData.nodeId" :id="'node-' + nodeData.nodeId" class="report-entry node-details-entry">
            <h3 class="node-header" @click.prevent="openNodeDesktop(nodeData.nodeId)" style="cursor: pointer;" title="Open Node Desktop">=============================================================</h3>
            <h3 class="node-header" @click.prevent="openNodeDesktop(nodeData.nodeId)" style="cursor: pointer;" title="Open Node Desktop">[ NODE: {{ nodeData.nodeName || nodeData.nodeId }} ]</h3>
            <h3 class="node-header" @click.prevent="openNodeDesktop(nodeData.nodeId)" style="cursor: pointer;" title="Open Node Desktop">=============================================================</h3>

            <div v-for="item in nodeData.items" :key="item.label" :id="'item-' + nodeData.nodeId + '-' + item.type" class="node-diag-section">
              <h4>&gt;&gt;&gt; [ {{ item.label.toUpperCase() }} ] &lt;&lt;&lt;</h4>
              <pre class="diag-output">{{ item.output }}</pre>
            </div>
          </div>
        </div>
      </div>

      <div class="report-footer">
        <p>END OF REPORT.</p>
        <div class="stamp-classified small">RESTRICTED ACCESS</div>
      </div>
    </div>

    <!-- BUILDER VIEW -->
    <div v-else-if="viewMode === 'builder'" class="builder-container">
      <h2 class="builder-title">REPORT BUILDER</h2>

      <div class="form-group">
        <label>Author / Initials:</label>
        <input v-model="reportAuthor" placeholder="e.g. ASO" class="tech-input" />
      </div>

      <div class="form-group">
        <label>Select Nodes to Include:</label>
        <div class="report-checkbox-grid">
          <label v-for="node in allNodes" :key="node.id" class="report-checkbox" style="display: flex; align-items: center; gap: 8px;">
            <input type="checkbox" :value="node.id" v-model="selectedNodesForReport" />
            <span @click.prevent="openNodeDesktop(node.id)" style="cursor: pointer; color: var(--cyan);" title="Open Node Desktop">{{ node.name || node.id }}</span>
          </label>
        </div>
      </div>

      <div class="form-group">
        <label>Select Diagnostics to Include:</label>
        <div class="report-checkbox-grid">
          <label v-for="item in availableReportItems" :key="item.type" class="report-checkbox">
            <input type="checkbox" :value="item.type" v-model="selectedReportItems" />
            {{ item.label }} <span class="cat-label">({{ item.catLabel }})</span>
          </label>
        </div>
      </div>

      <div class="modal-actions" style="margin-top: 30px;">
        <button class="btn-submit" @click="generateCustomReport" :disabled="selectedNodesForReport.length === 0 || selectedReportItems.length === 0">
          GENERATE & VIEW REPORT
        </button>
      </div>
    </div>

    <!-- HISTORY VIEW -->
    <div v-else-if="viewMode === 'history'" class="history-container">
      <h2>SAVED REPORTS HISTORY</h2>

      <div v-if="loading" class="loading-state">
        <span>LOADING ARCHIVES...</span>
      </div>

      <div v-else>
        <div v-if="history.length === 0" class="no-data">
          NO ARCHIVED REPORTS FOUND.
        </div>

        <table v-else class="history-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>DATE</th>
              <th>CRITICAL</th>
              <th>EXPORTS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rep in history" :key="rep.id">
              <td>{{ rep.id.substring(0, 8) }}</td>
              <td>{{ new Date(rep.created_at * 1000).toLocaleString() }}</td>
              <td style="color:#c00; font-weight:bold;">{{ rep.summary_json?.critical || 0 }}</td>
              <td class="export-actions">
                <a :href="`/api/v1/reports/${rep.id}/export?format=md`" target="_blank" class="btn-export">MD</a>
                <a :href="`/api/v1/reports/${rep.id}/export?format=latex`" target="_blank" class="btn-export">LaTeX</a>
                <a :href="`/api/v1/reports/${rep.id}/export?format=docx`" target="_blank" class="btn-export">Word</a>
                <button class="btn-delete" @click="deleteReport(rep.id)">DEL</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api/client'
import html2pdf from 'html2pdf.js'
import { READ_CATEGORIES } from '@/types'
import type { ReadType, NrNode } from '@/types'
import { useNodesStore } from '@/stores/nodes'

const viewMode = ref<'builder'|'current'|'history'>('builder')
const loading = ref(false)
const saving = ref(false)
const reportContainer = ref<HTMLElement | null>(null)

const rawData = ref<any>(null)
const history = ref<any[]>([])
const currentReference = ref(Math.random().toString(36).substring(2, 10).toUpperCase())

const reportAuthor = ref('')
const allNodes = ref<NrNode[]>([])
const selectedNodesForReport = ref<string[]>([])
const availableReportItems = ref<{type: string, label: string, catLabel: string}[]>([])
const selectedReportItems = ref<string[]>([])
const generatedNodesData = ref<{ nodeId: string, nodeName: string, items: { type: string, label: string, output: string }[] }[]>([])
const hasGeneratedReport = ref(false)

const nodesStore = useNodesStore()

const openNodeDesktop = (nodeId: string) => {
  nodesStore.select(nodeId)
}

const summary = computed(() => {
  if (!rawData.value) return { nodesCount: 0, totalAlerts: 0, criticalAlerts: 0, highAlerts: 0 }

  const nodesCount = hasGeneratedReport.value ? selectedNodesForReport.value.length : Object.keys(rawData.value.nodes || {}).length
  const alerts = rawData.value.alerts || []
  const totalAlerts = alerts.length
  const criticalAlerts = alerts.filter((a: any) => a.severity === 'critical').length
  const highAlerts = alerts.filter((a: any) => a.severity === 'high').length

  return { nodesCount, totalAlerts, criticalAlerts, highAlerts }
})

const generateMarkdown = () => {
  return `# Pentest Report
**Date**: ${new Date().toLocaleDateString()}
**Reference**: ${currentReference.value}-SEC

## Summary
- **Nodes Analyzed**: ${summary.value.nodesCount}
- **Total Alerts**: ${summary.value.totalAlerts}
- **Critical Alerts**: ${summary.value.criticalAlerts}
- **High Alerts**: ${summary.value.highAlerts}

## Details
This report was automatically generated by Netrunner AI Orchestrator.
`
}

const loadCurrent = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/v1/reports')
    rawData.value = data
  } catch (e) {
    console.error("Failed to load live data", e)
  } finally {
    loading.value = false
  }
}

const loadHistory = async () => {
  viewMode.value = 'history'
  loading.value = true
  try {
    const { data } = await api.get('/v1/reports/history')
    history.value = data
  } catch (e) {
    console.error("Failed to load history", e)
  } finally {
    loading.value = false
  }
}

const deleteReport = async (id: string) => {
  if (!confirm('Are you sure you want to delete this report?')) return;
  try {
    await api.delete(`/v1/reports/${id}`)
    history.value = history.value.filter(r => r.id !== id)
  } catch (e) {
    console.error('Failed to delete report:', e)
    alert('Failed to delete report.')
  }
}

async function generateCustomReport() {
  viewMode.value = 'current'
  loading.value = true
  hasGeneratedReport.value = true

  generatedNodesData.value = []

  try {
    for (const nodeId of selectedNodesForReport.value) {
      const nodeObj = allNodes.value.find(n => n.id === nodeId);
      const nodeName = nodeObj ? (nodeObj.name || nodeId) : nodeId;
      const nodeItems = []

      for (const item of availableReportItems.value) {
        if (!selectedReportItems.value.includes(item.type)) continue;

        try {
          const data = await api.readNode(nodeId, item.type as ReadType)
          const out = data.results.map(r => (r.output || r.error || '')).join('\n\n').trim()
          nodeItems.push({ type: item.type, label: item.label, output: out || 'No output or tool not installed.' })
        } catch (e) {
          nodeItems.push({ type: item.type, label: item.label, output: `Error: ${e}` })
        }
      }
      generatedNodesData.value.push({ nodeId, nodeName, items: nodeItems })
    }
  } catch (err) {
    console.error('Failed to generate report data', err)
  } finally {
    loading.value = false
  }
}

const saveReport = async () => {
  saving.value = true
  try {
    const payload = {
      timerange_hours: 24,
      summary_json: {
        total: summary.value.totalAlerts,
        critical: summary.value.criticalAlerts,
        high: summary.value.highAlerts
      },
      markdown_content: generateMarkdown()
    }
    await api.post('/v1/reports/save', payload)
    alert("Report saved to database successfully!")
  } catch (e) {
    console.error("Failed to save report", e)
    alert("Error saving report.")
  } finally {
    saving.value = false
  }
}

const downloadPDF = () => {
  if (!reportContainer.value) return

  const element = reportContainer.value
  const opt = {
    margin:       10,
    filename:     'classified_pentest_report.pdf',
    image:        { type: 'jpeg', quality: 0.98 },
    html2canvas:  { scale: 2, useCORS: true },
    jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
  }

  html2pdf().set(opt).from(element).save()
}

const downloadTXT = () => {
  let reportText = `SECURITY ASSESSMENT REPORT\n`
  const d = new Date()
  reportText += `DATE: ${d.getDate()}.${d.getMonth()+1}.${d.getFullYear()}\n\n`
  reportText += `AUTHORIZATION: CLEARANCE LEVEL 5\n\n`
  reportText += `TARGET: ${selectedNodesForReport.value.length > 1 ? 'MULTIPLE NODES' : 'SINGLE NODE'}\n\n`
  reportText += `REFERENCE: ${currentReference.value}-SEC\n\n`

  if (reportAuthor.value) {
    reportText += `CONFIGURATION BY: ${reportAuthor.value}\n\n`
  }

  reportText += `[ LIVE SYSTEM SUMMARY ]\n`
  reportText += `TOTAL NODES\t${selectedNodesForReport.value.length}\n`
  reportText += `TOTAL ALERTS\t${summary.value.totalAlerts}\n`
  reportText += `CRITICAL SEVERITY\t${summary.value.criticalAlerts}\n`
  reportText += `HIGH SEVERITY\t${summary.value.highAlerts}\n`
  if (summary.value.criticalAlerts > 0) {
    reportText += `WARNING: CRITICAL VULNERABILITIES DETECTED. IMMEDIATE ACTION REQUIRED.\n\n`
  } else {
    reportText += `\n`
  }

  reportText += `[ TABLE OF CONTENTS ]\n`
  for (const node of generatedNodesData.value) {
    reportText += `► NODE: ${node.nodeName} (${node.nodeId})\n`
    for (const item of node.items) {
      reportText += `  └ ${item.label}\n`
    }
  }
  reportText += `\n`

  for (const node of generatedNodesData.value) {
    reportText += `======================================================================\n`
    reportText += `[ NODE: ${node.nodeName || node.nodeId} ]\n`
    reportText += `======================================================================\n\n`

    for (const item of node.items) {
      reportText += `>>> [ ${item.label.toUpperCase()} ] <<<\n`
      reportText += `----------------------------------------------------------------------\n`
      reportText += `${item.output}\n`
      reportText += `----------------------------------------------------------------------\n\n`
    }
  }

  reportText += `END OF REPORT.\n`

  const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `security_report_${currentReference.value}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  const flattenedItems = Object.values(READ_CATEGORIES).flatMap(cat => cat.types.map(t => ({ ...t, catLabel: cat.label })))
  availableReportItems.value = flattenedItems
  selectedReportItems.value = []

  try {
    const nodesMap = await api.listNodes()
    allNodes.value = Object.values(nodesMap)
  } catch (e) {
    console.error("Failed to list nodes", e)
  }

  loadCurrent()
})
</script>

<style scoped>
.report-generator-wrapper {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #111;
  color: #fff;
  font-family: 'Courier New', Courier, monospace;
  overflow-y: auto;
}

.top-controls {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 20px;
  gap: 10px;
}

.current-actions {
  margin-left: auto;
  display: flex;
  gap: 10px;
}

.btn-action, .btn-pdf {
  background: #000;
  border: 1px solid #0f0;
  color: #0f0;
  padding: 10px 20px;
  font-family: inherit;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}

.btn-action.active, .btn-action:hover, .btn-pdf:hover {
  background: #0f0;
  color: #000;
  box-shadow: 0 0 10px #0f0;
}

.btn-pdf:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

/* --- History View --- */
.history-container {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.history-table th, .history-table td {
  border: 1px solid #333;
  padding: 12px;
  text-align: left;
}

.history-table th {
  background: #222;
  color: #0f0;
}

.export-actions {
  display: flex;
  gap: 10px;
}

.btn-export {
  background: #222;
  color: #0ff;
  border: 1px solid #0ff;
  padding: 5px 10px;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-export:hover {
  background: #0ff;
  color: #000;
}

.btn-delete {
  background: #222;
  color: #f00;
  border: 1px solid #f00;
  text-decoration: none;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-delete:hover {
  background: #f00;
  color: #fff;
}

/* --- Report Container --- */
.report-container {
  background: #f4f4f0; /* Slight off-white paper color */
  color: #111;
  padding: 40px;
  border: 4px double #111;
  position: relative;
  max-width: 800px;
  margin: 0 auto;
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
  width: 100%;
}

.stamp-classified {
  position: absolute;
  top: 30px;
  right: 30px;
  color: #c00;
  border: 4px solid #c00;
  padding: 8px 20px;
  font-size: 28px;
  font-weight: bold;
  transform: rotate(-10deg);
  opacity: 0.85;
  pointer-events: none;
  font-family: 'Impact', sans-serif;
  letter-spacing: 3px;
  text-transform: uppercase;
  z-index: 10;
}

.stamp-classified.small {
  top: auto;
  bottom: 30px;
  left: 30px;
  right: auto;
  font-size: 18px;
  border-width: 3px;
  padding: 5px 15px;
  transform: rotate(5deg);
}

.report-header {
  border-bottom: 3px solid #111;
  margin-bottom: 40px;
  padding-bottom: 20px;
}

.report-header h1 {
  font-size: 32px;
  margin: 0 0 20px 0;
  text-align: center;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.meta-data {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.meta-data p {
  margin: 0;
  font-size: 14px;
}

.report-body {
  min-height: 500px;
}

.loading-state {
  text-align: center;
  margin-top: 150px;
  font-size: 24px;
  font-weight: bold;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.report-entry {
  margin-bottom: 40px;
  border: 2px solid #111;
  padding: 20px;
  background: #fff;
  position: relative;
}

.report-entry h3 {
  margin-top: 0;
  border-bottom: 2px dashed #111;
  padding-bottom: 15px;
  font-size: 18px;
  letter-spacing: 1px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}

.data-table td {
  padding: 12px 8px;
  border-bottom: 1px dotted #888;
  font-size: 15px;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.alert-val {
  font-weight: bold;
  text-align: right;
  font-size: 16px;
}

.critical-warning {
  margin-top: 20px;
  padding: 12px;
  background: #c00;
  color: #fff;
  font-weight: bold;
  text-align: center;
  font-size: 15px;
  letter-spacing: 1px;
}

.no-data {
  text-align: center;
  font-style: italic;
  margin-top: 80px;
  font-size: 18px;
}

.report-footer {
  margin-top: 60px;
  border-top: 3px solid #111;
  padding-top: 30px;
  text-align: center;
  font-weight: bold;
  font-size: 16px;
  letter-spacing: 1px;
}

/* Builder styles */
.builder-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.builder-title {
  color: var(--cyan);
  font-family: var(--font-hd);
  text-shadow: 0 0 10px rgba(0,255,255,0.4);
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.form-group label {
  font-size: 12px;
  font-family: var(--font-hd);
  color: var(--cyan);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.tech-input {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border);
  color: #fff;
  padding: 12px;
  font-family: var(--font-ui);
  border-radius: 4px;
  outline: none;
  transition: all 0.2s;
}
.tech-input:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}
.report-checkbox-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  background: rgba(0, 0, 0, 0.3);
  padding: 16px;
  border-radius: 4px;
  border: 1px solid var(--border);
  max-height: 350px;
  overflow-y: auto;
}
.report-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #ccc;
  cursor: pointer;
  user-select: none;
}
.report-checkbox input[type="checkbox"] {
  accent-color: var(--cyan);
  cursor: pointer;
}
.report-checkbox:hover {
  color: var(--cyan);
}
.cat-label {
  font-size: 10px;
  color: #888;
  margin-left: 4px;
}

.btn-submit {
  background: var(--cyan);
  color: #000;
  border: none;
  padding: 12px 24px;
  font-family: var(--font-hd);
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  box-shadow: 0 0 10px rgba(0,255,255,0.2);
}
.btn-submit:hover:not(:disabled) {
  background: #fff;
  box-shadow: 0 0 15px rgba(255,255,255,0.5);
}
.btn-submit:disabled {
  background: #555;
  color: #888;
  cursor: not-allowed;
  box-shadow: none;
}

.node-details-entry {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}

.node-header {
  border-bottom: none !important;
  margin: 0 !important;
  padding: 0 !important;
  text-align: center;
  font-size: 20px !important;
}

.node-diag-section {
  margin-top: 30px;
}

.node-diag-section h4 {
  font-size: 16px;
  margin: 0 0 10px 0;
  color: #333;
}

.diag-output {
  background: #eaeae5;
  padding: 15px;
  border: 1px solid #ccc;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.4;
  overflow-x: auto;
}

.toc-body {
  margin-top: 15px;
  padding: 10px 20px;
  background: #eaeae5;
  border: 1px solid #ccc;
}

.toc-node {
  margin-bottom: 10px;
}

.toc-items {
  margin-left: 20px;
  margin-top: 5px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.toc-link {
  color: #111;
  text-decoration: none;
  transition: color 0.2s;
}

.toc-link:hover {
  color: #c00;
  text-decoration: underline;
}

.node-link {
  font-weight: bold;
  font-size: 15px;
}

.item-link {
  font-size: 13px;
  color: #333;
}
</style>
