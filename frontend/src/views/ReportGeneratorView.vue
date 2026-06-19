<template>
  <div class="report-generator">
    <div class="rg-header">
      <h2><span class="icon">📄</span> ENTERPRISE REPORT GENERATOR</h2>
    </div>

    <div class="controls-panel">
      <div class="control-group">
        <label>TIME RANGE</label>
        <select v-model="timerange">
          <option :value="24">Last 24 Hours</option>
          <option :value="168">Last 7 Days (168h)</option>
          <option :value="720">Last 30 Days (720h)</option>
        </select>
      </div>
      <div class="control-group" style="justify-content: flex-end;">
        <button class="btn btn-primary" @click="generateReport" :disabled="isGenerating">
          {{ isGenerating ? 'GENERATING...' : 'GENERATE NEW REPORT' }}
        </button>
      </div>
    </div>

    <div class="reports-list">
      <div v-if="loading" class="r-loading">LOADING REPORTS...</div>
      <table class="r-table" v-else-if="reports.length > 0">
        <tr>
          <th>GENERATED AT</th>
          <th>TIME RANGE</th>
          <th>TOTAL ALERTS</th>
          <th>ACTIONS</th>
        </tr>
        <tr v-for="report in reports" :key="report.id">
          <td>{{ new Date(report.created_at * 1000).toLocaleString() }}</td>
          <td>Last {{ report.timerange_hours }}h</td>
          <td>{{ report.summary_json.alerts_summary.total }}</td>
          <td class="action-buttons">
            <button @click="download(report.id, 'md')" class="btn btn-sm">.MD</button>
            <button @click="download(report.id, 'tex')" class="btn btn-sm">.TEX</button>
            <button @click="download(report.id, 'pdf')" class="btn btn-sm btn-pink">.PDF</button>
            <button @click="download(report.id, 'docx')" class="btn btn-sm">.DOCX</button>
          </td>
        </tr>
      </table>
      <div v-else class="no-reports">
        No reports generated yet.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

const reports = ref<any[]>([])
const loading = ref(false)
const isGenerating = ref(false)
const timerange = ref(24)

const loadReports = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/reports')
    reports.value = data
  } catch (e) {
    console.error("Failed to load reports", e)
  } finally {
    loading.value = false
  }
}

const generateReport = async () => {
  isGenerating.value = true
  try {
    await api.post('/reports/generate', {
      query: { timerange_hours: timerange.value }
    })
    await loadReports()
  } catch (e) {
    console.error("Failed to generate report", e)
  } finally {
    isGenerating.value = false
  }
}

const download = (reportId: string, format: string) => {
  // We can just open the download link in a new tab, the backend handles the response attachment
  // Make sure to include authentication if required, here we assume it's cookie based or we pass the token.
  // We will construct the URL directly:
  const token = localStorage.getItem('token') || ''
  const url = `/api/v1/reports/${reportId}/download?format=${format}&token=${token}`
  window.open(url, '_blank')
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.report-generator {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: rgba(10, 15, 20, 0.9);
  color: var(--text-color);
  font-family: 'Inter', sans-serif;
}

.rg-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 15px;
  margin-bottom: 20px;
}

.rg-header h2 {
  margin: 0;
  font-size: 1.5rem;
  letter-spacing: 2px;
  color: var(--cyan);
}

.controls-panel {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  background: rgba(0, 0, 0, 0.3);
  padding: 15px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.control-group label {
  font-size: 0.8rem;
  color: #888;
}

.control-group select {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border-color);
  color: #fff;
  padding: 8px;
  border-radius: 3px;
  outline: none;
}

.reports-list {
  background: rgba(0, 0, 0, 0.3);
  padding: 20px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  flex-grow: 1;
  overflow-y: auto;
}

.no-reports {
  text-align: center;
  padding: 40px;
  color: #666;
  font-style: italic;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.8rem;
}

.btn-pink {
  border-color: var(--pink);
  color: var(--pink);
}
.btn-pink:hover {
  background: var(--pink);
  color: #000;
  box-shadow: 0 0 10px var(--pink);
}

.r-table {
  width: 100%;
  border-collapse: collapse;
}

.r-table th, .r-table td {
  padding: 15px;
  text-align: left;
  border-bottom: 1px solid #222;
}

.r-table th {
  color: var(--cyan);
  font-size: 0.85rem;
  letter-spacing: 1px;
}

.r-table tr:hover {
  background: rgba(0, 240, 255, 0.05);
}

.r-loading {
  text-align: center;
  padding: 50px;
  color: var(--cyan);
  font-style: italic;
  animation: pulse 1.5s infinite;
}
</style>


