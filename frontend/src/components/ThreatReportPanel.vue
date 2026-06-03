<template>
  <div class="threat-report-panel">
    <div class="panel-header">
      <h3>Vulnerability Analysis</h3>
      <button class="btn-analyze" @click="runAnalysis" :disabled="loading">
        <span class="icon">☢️</span>
        {{ loading ? 'SCANNING...' : 'ANALYZE VULNERABILITIES' }}
      </button>
    </div>

    <div v-if="error" class="error-box">
      {{ error }}
    </div>

    <div v-if="loading" class="scanning-overlay">
      <div class="scanner-line"></div>
      <div class="scanner-text">CROSS-REFERENCING CVE DATABASES...</div>
    </div>

    <div v-else-if="findings.length > 0" class="findings-list">
      <div class="summary-banner" :class="{ 'has-critical': hasCritical }">
        <span class="summary-icon">⚠️</span>
        <div>
          <div class="summary-title">{{ findings.length }} VULNERABILITIES DETECTED</div>
          <div class="summary-sub">Immediate remediation required for CRITICAL threats.</div>
        </div>
      </div>
      
      <div v-for="(f, i) in findings" :key="i" class="finding-card" :class="f.severity.toLowerCase()">
        <div class="finding-header">
          <span class="finding-cve">{{ f.cve }}</span>
          <span class="finding-severity">{{ f.severity }} (CVSS: {{ f.cvss.toFixed(1) }})</span>
        </div>
        <div class="finding-title">{{ f.title }}</div>
        <div class="finding-target">Target: Port {{ f.port }} / {{ f.service }}</div>
        <div class="finding-desc">{{ f.description }}</div>
        <div class="finding-remediation"><strong>REMEDIATION:</strong> {{ f.remediation }}</div>
      </div>
    </div>
    
    <div v-else-if="hasScanned" class="secure-box">
      <span class="secure-icon">🛡️</span>
      <div class="secure-text">NO KNOWN VULNERABILITIES DETECTED</div>
      <div class="secure-sub">Target appears hardened against known CVEs.</div>
    </div>
    
    <div v-else class="empty-state">
      <p>Initiate a vulnerability scan to cross-reference open ports with the CVE database.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'

const props = defineProps<{ nodeId: string }>()
const store = useNodesStore()

const loading = ref(false)
const error = ref('')
const hasScanned = ref(false)
const findings = ref<any[]>([])

const hasCritical = computed(() => findings.value.some(f => f.severity === 'CRITICAL'))

async function runAnalysis() {
  loading.value = true
  error.value = ''
  hasScanned.value = false
  findings.value = []
  
  try {
    const res = await fetch(`/api/threats/analyze/${props.nodeId}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    })
    
    if (!res.ok) {
      throw new Error(`API Error: ${res.statusText}`)
    }
    
    const data = await res.json()
    findings.value = data.findings || []
    hasScanned.value = true
    
    // Refresh nodes store to pick up the new "vulnerable" tag
    await store.refresh()
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.threat-report-panel {
  padding: 16px;
  color: #c9d1d9;
  position: relative;
  min-height: 400px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #30363d;
  padding-bottom: 12px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #ff2d6e;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.btn-analyze {
  background: #ff2d6e;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.4);
  transition: all 0.2s;
}

.btn-analyze:hover:not(:disabled) {
  background: #ff4785;
  box-shadow: 0 0 15px rgba(255, 45, 110, 0.6);
  transform: translateY(-1px);
}

.btn-analyze:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  animation: pulse 1s infinite alternate;
}

@keyframes pulse {
  from { opacity: 0.6; }
  to { opacity: 1; }
}

.scanning-overlay {
  position: absolute;
  top: 70px; left: 0; right: 0; bottom: 0;
  background: rgba(13, 17, 23, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.scanner-line {
  width: 80%;
  height: 2px;
  background: #ff2d6e;
  box-shadow: 0 0 10px #ff2d6e;
  margin-bottom: 20px;
  animation: scan 1.5s infinite linear;
}

@keyframes scan {
  0% { transform: translateY(-50px); opacity: 0; }
  50% { opacity: 1; }
  100% { transform: translateY(50px); opacity: 0; }
}

.scanner-text {
  color: #ff2d6e;
  font-family: monospace;
  letter-spacing: 2px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.summary-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #330a0a;
  border: 1px solid #f85149;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.summary-icon {
  font-size: 24px;
}

.summary-title {
  color: #ff7b72;
  font-weight: bold;
  font-size: 14px;
}

.summary-sub {
  color: #c9d1d9;
  font-size: 12px;
  margin-top: 4px;
}

.finding-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-left: 4px solid #30363d;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}

.finding-card.critical { border-left-color: #ff2d6e; }
.finding-card.high { border-left-color: #f85149; }
.finding-card.medium { border-left-color: #d29922; }
.finding-card.low { border-left-color: #2ea043; }
.finding-card.warning { border-left-color: #d29922; }

.finding-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.finding-cve {
  font-weight: bold;
  color: #58a6ff;
  font-family: monospace;
}

.finding-severity {
  font-size: 12px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.1);
}

.critical .finding-severity { background: rgba(255, 45, 110, 0.2); color: #ff2d6e; }
.warning .finding-severity { background: rgba(210, 153, 34, 0.2); color: #d29922; }

.finding-title {
  font-size: 15px;
  font-weight: bold;
  margin-bottom: 8px;
  color: #e6edf3;
}

.finding-target {
  font-family: monospace;
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 12px;
  background: #0d1117;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

.finding-desc {
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 12px;
  color: #c9d1d9;
}

.finding-remediation {
  font-size: 13px;
  background: rgba(46, 160, 67, 0.1);
  border: 1px solid rgba(46, 160, 67, 0.2);
  padding: 8px;
  border-radius: 4px;
  color: #3fb950;
}

.secure-box {
  text-align: center;
  padding: 40px 20px;
  background: rgba(46, 160, 67, 0.05);
  border: 1px solid rgba(46, 160, 67, 0.2);
  border-radius: 6px;
}

.secure-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.secure-text {
  color: #3fb950;
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 8px;
}

.secure-sub {
  color: #8b949e;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8b949e;
  font-style: italic;
}

.error-box {
  background: #330a0a;
  border: 1px solid #f85149;
  color: #f85149;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 16px;
}
</style>
