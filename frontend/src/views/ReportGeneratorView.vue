<template>
  <div class="report-generator">
    <div class="rg-header">
      <h2><span class="icon">📄</span> ENTERPRISE REPORT GENERATOR</h2>
      <button class="btn btn-primary" @click="generatePDF" :disabled="isGenerating">
        {{ isGenerating ? 'GENERATING PDF...' : 'DOWNLOAD C-LEVEL REPORT' }}
      </button>
    </div>

    <div class="controls-panel">
      <div class="control-group">
        <label>TIME RANGE</label>
        <select v-model="timerange" @change="loadReportData">
          <option :value="24">Last 24 Hours</option>
          <option :value="168">Last 7 Days (168h)</option>
          <option :value="720">Last 30 Days (720h)</option>
        </select>
      </div>
    </div>

    <!-- The actual report template that will be captured by html2pdf -->
    <div class="report-preview-container">
      <div class="report-page" ref="reportContent">
        <div class="r-header">
          <div class="r-logo">NETRUNNER<span style="color: var(--cyan); font-size: 0.5em; vertical-align: top;">OS</span></div>
          <div class="r-title">SECURITY OPERATIONS REPORT</div>
          <div class="r-meta">
            <div><strong>GENERATED:</strong> {{ new Date(reportData?.generated_at * 1000).toLocaleString() }}</div>
            <div><strong>PERIOD:</strong> Last {{ reportData?.timerange_hours }} Hours</div>
          </div>
        </div>

        <div v-if="loading" class="r-loading">GATHERING INTELLIGENCE...</div>
        
        <div v-else-if="reportData" class="r-body">
          <div class="r-section">
            <h3>EXECUTIVE SUMMARY</h3>
            <div class="r-stats-grid">
              <div class="r-stat">
                <div class="r-stat-val">{{ reportData.alerts_summary.total }}</div>
                <div class="r-stat-label">TOTAL ALERTS</div>
              </div>
              <div class="r-stat">
                <div class="r-stat-val" style="color: var(--pink)">{{ reportData.alerts_summary.by_severity.critical }}</div>
                <div class="r-stat-label">CRITICAL THREATS</div>
              </div>
              <div class="r-stat">
                <div class="r-stat-val" style="color: var(--cyan)">{{ reportData.total_active_nodes }}</div>
                <div class="r-stat-label">ACTIVE NODES</div>
              </div>
              <div class="r-stat">
                <div class="r-stat-val">{{ reportData.threats_summary.total_events }}</div>
                <div class="r-stat-label">RAW THREAT EVENTS</div>
              </div>
            </div>
          </div>

          <div class="r-section r-flex-row">
            <div class="r-col">
              <h3>ALERTS BY SEVERITY</h3>
              <table class="r-table">
                <tr><th>SEVERITY</th><th>COUNT</th></tr>
                <tr><td><span class="severity-dot" style="background: var(--pink)"></span> Critical</td><td>{{ reportData.alerts_summary.by_severity.critical }}</td></tr>
                <tr><td><span class="severity-dot" style="background: #ff6600"></span> High</td><td>{{ reportData.alerts_summary.by_severity.high }}</td></tr>
                <tr><td><span class="severity-dot" style="background: #ffcc00"></span> Medium</td><td>{{ reportData.alerts_summary.by_severity.medium }}</td></tr>
                <tr><td><span class="severity-dot" style="background: #00ccff"></span> Low</td><td>{{ reportData.alerts_summary.by_severity.low }}</td></tr>
              </table>
            </div>
            <div class="r-col">
              <h3>ALERTS BY STATUS</h3>
              <table class="r-table">
                <tr><th>STATUS</th><th>COUNT</th></tr>
                <tr><td>Open</td><td>{{ reportData.alerts_summary.by_status.open }}</td></tr>
                <tr><td>New</td><td>{{ reportData.alerts_summary.by_status.new }}</td></tr>
                <tr><td>Closed</td><td>{{ reportData.alerts_summary.by_status.closed }}</td></tr>
                <tr><td>False Positive</td><td>{{ reportData.alerts_summary.by_status.false_positive }}</td></tr>
              </table>
            </div>
          </div>

          <div class="r-section">
            <h3>TOP TARGETED NODES</h3>
            <table class="r-table">
              <tr>
                <th>TARGET IP / NODE ID</th>
                <th>THREAT EVENTS</th>
              </tr>
              <tr v-for="node in reportData.threats_summary.top_targets" :key="node.target">
                <td>{{ node.target }}</td>
                <td>{{ node.hits }}</td>
              </tr>
              <tr v-if="reportData.threats_summary.top_targets.length === 0">
                <td colspan="2">No threat events detected in this period.</td>
              </tr>
            </table>
          </div>
        </div>
        
        <div class="r-footer">
          Netrunner OS Enterprise Security Platform - CONFIDENTIAL
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'
// @ts-ignore
import html2pdf from 'html2pdf.js'

const reportData = ref<any>(null)
const loading = ref(false)
const isGenerating = ref(false)
const timerange = ref(24)
const reportContent = ref<HTMLElement | null>(null)

const loadReportData = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/reports/summary', {
      query: { timerange_hours: timerange.value }
    })
    reportData.value = data
  } catch (e) {
    console.error("Failed to load report data", e)
  } finally {
    loading.value = false
  }
}

const generatePDF = async () => {
  if (!reportContent.value) return
  isGenerating.value = true
  
  const element = reportContent.value
  const opt = {
    margin:       10,
    filename:     `Netrunner_Security_Report_${new Date().toISOString().split('T')[0]}.pdf`,
    image:        { type: 'jpeg', quality: 0.98 },
    html2canvas:  { scale: 2, useCORS: true, logging: false },
    jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
  }

  try {
    await html2pdf().set(opt).from(element).save()
  } catch (e) {
    console.error("Failed to generate PDF", e)
  } finally {
    isGenerating.value = false
  }
}

onMounted(() => {
  loadReportData()
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

.report-preview-container {
  flex-grow: 1;
  overflow-y: auto;
  display: flex;
  justify-content: center;
  padding: 20px;
  background: #111;
}

/* The actual PDF page layout */
.report-page {
  width: 210mm; /* A4 width */
  min-height: 297mm; /* A4 height */
  background: #0a0a0c;
  border: 1px solid #333;
  box-shadow: 0 0 20px rgba(0,0,0,0.8);
  padding: 40px;
  position: relative;
  color: #e0e0e0;
}

.r-header {
  border-bottom: 2px solid var(--cyan);
  padding-bottom: 20px;
  margin-bottom: 30px;
}

.r-logo {
  font-size: 2rem;
  font-weight: 900;
  letter-spacing: 2px;
}

.r-title {
  font-size: 1.2rem;
  color: #888;
  letter-spacing: 5px;
  margin-top: 5px;
}

.r-meta {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: #aaa;
}

.r-section {
  margin-bottom: 30px;
}

.r-section h3 {
  color: var(--cyan);
  font-size: 1.1rem;
  letter-spacing: 2px;
  border-bottom: 1px solid #333;
  padding-bottom: 5px;
  margin-bottom: 15px;
}

.r-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
}

.r-stat {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #333;
  padding: 15px;
  text-align: center;
}

.r-stat-val {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.r-stat-label {
  font-size: 0.8rem;
  color: #888;
}

.r-flex-row {
  display: flex;
  gap: 30px;
}

.r-col {
  flex: 1;
}

.r-table {
  width: 100%;
  border-collapse: collapse;
}

.r-table th, .r-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #222;
}

.r-table th {
  color: #888;
  font-size: 0.8rem;
}

.severity-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
}

.r-footer {
  position: absolute;
  bottom: 20px;
  left: 40px;
  right: 40px;
  text-align: center;
  border-top: 1px solid #333;
  padding-top: 10px;
  font-size: 0.8rem;
  color: #555;
}

.r-loading {
  text-align: center;
  padding: 50px;
  color: var(--cyan);
  font-style: italic;
  animation: pulse 1.5s infinite;
}
</style>
