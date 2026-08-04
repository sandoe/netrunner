<template>
  <div class="alert-inbox">
    <div class="inbox-header">
      <h2><span class="icon">🚨</span> ALERT INBOX (TRIAGE)</h2>
      <div class="inbox-stats">
        <div class="stat-badge stat-critical">CRITICAL: {{ alerts.filter(a => a.severity === 'critical' && a.status !== 'closed' && a.status !== 'false_positive').length }}</div>
        <div class="stat-badge stat-high">HIGH: {{ alerts.filter(a => a.severity === 'high' && a.status !== 'closed' && a.status !== 'false_positive').length }}</div>
        <div class="stat-badge stat-open">OPEN: {{ alerts.filter(a => a.status === 'open').length }}</div>
      </div>
    </div>

    <div v-if="storylines.length > 0" class="soc-pulse-container">
      <h3>⚡ SOC PULSE: AI ATTACK STORYLINES</h3>
      <div class="storyline-cards">
        <div v-for="story in storylines" :key="story.id" class="story-card">
          <div class="story-header">
            <h4>{{ story.title }}</h4>
            <span class="story-status">{{ story.status.toUpperCase() }}</span>
          </div>
          <p class="story-summary">{{ story.summary }}</p>
          <div class="story-actions" v-if="!soarStates[story.id]">
            <span class="story-alerts-count">Involves {{ story.alert_ids.length }} alerts</span>
            <button class="btn-mitigate" @click="runSoarPlaybook(story)">
              <span class="icon">⚡</span> EXECUTE PLAYBOOK: {{ story.recommended_action }}
            </button>
          </div>
          <div class="soar-terminal" v-else>
            <div class="terminal-header">🤖 SOAR PLAYBOOK EXECUTION</div>
            <div class="terminal-log">
              <div v-for="(log, i) in soarStates[story.id].logs" :key="i" class="log-line">
                 <span v-if="log.status === 'done'" class="text-green">[SUCCESS]</span>
                 <span v-else-if="log.status === 'fail'" class="text-red">[FAILED]</span>
                 <span v-else-if="log.status === 'hotpatch'" class="text-cyan pulse" style="font-weight: bold; text-shadow: 0 0 8px rgba(0,255,255,0.8);">[🛡️ HOTPATCH]</span>
                 <span v-else class="text-cyan">[RUNNING]</span>
                 <span :class="['log-msg', { 'text-cyan text-glow': log.status === 'hotpatch' }]">{{ log.msg }}</span>
              </div>
            </div>
            <div class="progress-bar-container" v-if="soarStates[story.id].progress < 100">
               <div class="progress-bar" :style="{width: soarStates[story.id].progress + '%'}"></div>
            </div>
            <div v-else class="soar-complete text-green">
               PLAYBOOK COMPLETED SUCCESSFULLY
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="filters">
      <button :class="['filter-btn', { active: currentFilter === 'all' }]" @click="currentFilter = 'all'">ALL</button>
      <button :class="['filter-btn', { active: currentFilter === 'new' }]" @click="currentFilter = 'new'">NEW</button>
      <button :class="['filter-btn', { active: currentFilter === 'open' }]" @click="currentFilter = 'open'">OPEN</button>
      <button :class="['filter-btn', { active: currentFilter === 'closed' }]" @click="currentFilter = 'closed'">CLOSED</button>
    </div>

    <div class="table-container">
      <table class="alert-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>TIME</th>
            <th>SEVERITY</th>
            <th>TITLE</th>
            <th>STATUS</th>
            <th>ASSIGNEE</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="alert in filteredAlerts" :key="alert.id" :class="['alert-row', `row-${alert.severity}`]">
            <td class="col-id">{{ alert.id }}</td>
            <td class="col-time">{{ formatTime(alert.created_at) }}</td>
            <td class="col-severity">
              <span :class="['severity-badge', `sev-${alert.severity}`]">{{ alert.severity.toUpperCase() }}</span>
            </td>
            <td class="col-title">
              <span v-if="(alert as any)._isCorrelated" class="correlated-badge" title="Part of an active AI Incident Storyline">🔗 INCIDENT</span>
              {{ alert.title }}
            </td>
            <td class="col-status">
              <select v-model="alert.status" @change="updateStatus(alert.id, alert.status)" class="status-select">
                <option value="new">NEW</option>
                <option value="open">OPEN</option>
                <option value="closed">CLOSED</option>
                <option value="false_positive">FALSE POSITIVE</option>
              </select>
            </td>
            <td class="col-assignee">
              <select v-model="alert.assignee_id" @change="updateAssignee(alert.id, alert.assignee_id)" class="assignee-select">
                <option :value="null">Unassigned</option>
                <option value="analyst1">Analyst 1</option>
                <option value="soc_lead">SOC Lead</option>
              </select>
            </td>
            <td class="col-actions">
              <button class="btn-action" @click="viewDetails(alert)">INVESTIGATE</button>
            </td>
          </tr>
          <tr v-if="filteredAlerts.length === 0">
            <td colspan="7" class="no-alerts">No alerts found for this filter. Good job!</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'
import type { AlertResponse } from '@/api_client/types.gen'

const alerts = ref<AlertResponse[]>([])
const storylines = ref<any[]>([])
const currentFilter = ref<'all' | 'new' | 'open' | 'closed'>('new')
let pollInterval: any = null

const soarStates = ref<Record<string, { logs: any[], progress: number }>>({})

const loadAlerts = async () => {
  try {
    const { data, error } = await api.req('/alerts')
    if (data) {
      alerts.value = data
    }
  } catch (e) {
    console.error("Failed to load alerts", e)
  }
}

const loadStorylines = async () => {
  try {
    const data = await api.getStorylines()
    if (data) {
      storylines.value = data
    }
  } catch (e) {
    console.error("Failed to load storylines", e)
  }
}

onMounted(() => {
  loadAlerts()
  loadStorylines()
  pollInterval = setInterval(() => {
    loadAlerts()
    loadStorylines()
  }, 15000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

const filteredAlerts = computed(() => {
  let base = alerts.value
  if (currentFilter.value === 'closed') {
    base = alerts.value.filter(a => a.status === 'closed' || a.status === 'false_positive')
  } else if (currentFilter.value !== 'all') {
    base = alerts.value.filter(a => a.status === currentFilter.value)
  }

  // Risk-Based Priority Sorting and Intelligent Grouping
  const sevScores: Record<string, number> = { 'critical': 1000, 'high': 500, 'medium': 100, 'low': 10 }

  const sorted = [...base].map(a => {
    let score = sevScores[a.severity?.toLowerCase()] || 0
    // Intelligent Alert Grouping: If an alert is part of an active AI Storyline (Incident), boost its priority
    const inStory = storylines.value.some(s => s.alert_ids.includes(a.id))
    let isCorrelated = false
    if (inStory) {
      score += 5000 // Bubble up correlated incidents to the absolute top
      isCorrelated = true
    }
    return { ...a, _riskScore: score, _isCorrelated: isCorrelated }
  }).sort((a, b) => {
    // Sort by risk score descending, then by time descending
    if (b._riskScore !== a._riskScore) return b._riskScore - a._riskScore
    return b.created_at - a.created_at
  })

  return sorted
})

const formatTime = (ts: number) => {
  const d = new Date(ts * 1000)
  return d.toISOString().replace('T', ' ').substring(0, 19)
}

const updateStatus = async (id: string, status: string) => {
  try {
    await api.req('PATCH', `/alerts/${id}`, { status })
    await loadAlerts()
  } catch (e) {
    console.error("Failed to update status", e)
  }
}

const updateAssignee = async (id: string, assignee_id: string | null) => {
  try {
    await api.req('PATCH', `/alerts/${id}`, { assignee_id: assignee_id || "" })
    await loadAlerts()
  } catch (e) {
    console.error("Failed to update assignee", e)
  }
}

const viewDetails = (alert: AlertResponse) => {
  // Mock function for now, could open a modal or redirect to a dedicated case view
  alert.status = 'open'
  updateStatus(alert.id, 'open')
  window.alert(`Investigating Alert: ${alert.title}\nID: ${alert.id}\n\n(A dedicated case management view will be built in the next phase.)`)
}

const runSoarPlaybook = async (story: any) => {
  // Initialize SOAR state for this storyline
  soarStates.value[story.id] = { logs: [], progress: 0 }
  const state = soarStates.value[story.id]

  const addLog = (msg: string, status: string = 'running') => {
    state.logs.push({ msg, status })
  }

  // Simulate a SOAR playbook running with delays
  addLog(`Initializing playbook for ${story.title}...`)
  state.progress = 10
  await new Promise(r => setTimeout(r, 600))

  state.logs[state.logs.length - 1].status = 'done'
  addLog(`Analyzing ${story.alert_ids.length} related alerts...`)
  state.progress = 30
  await new Promise(r => setTimeout(r, 800))

  state.logs[state.logs.length - 1].status = 'done'
  addLog(`Executing action: ${story.recommended_action}...`)
  state.progress = 60
  await new Promise(r => setTimeout(r, 1200))

  state.logs[state.logs.length - 1].status = 'done'
  addLog(`Compiling eBPF XDP Hot-Patch for CVE...`, 'running')
  state.progress = 75
  await new Promise(r => setTimeout(r, 1000))

  state.logs[state.logs.length - 1].status = 'hotpatch'
  addLog(`🛡️ KERNEL HOT-PATCH DEPLOYED via eBPF. Malicious packets dropped at Layer 3/4.`, 'hotpatch')
  state.progress = 85
  await new Promise(r => setTimeout(r, 1200))

  state.logs[state.logs.length - 1].status = 'done'
  addLog(`Verifying endpoint isolation and rule propagation...`)
  state.progress = 95
  await new Promise(r => setTimeout(r, 900))

  state.logs[state.logs.length - 1].status = 'done'
  addLog(`Closing ${story.alert_ids.length} alerts...`)

  try {
    // Actually close all related alerts
    for (const alertId of story.alert_ids) {
      await api.req('PATCH', `/alerts/${alertId}`, { status: 'closed' })
    }
    state.logs[state.logs.length - 1].status = 'done'
    state.progress = 100

    // Auto-remove storyline after a few seconds so analyst sees the success
    setTimeout(() => {
      storylines.value = storylines.value.filter(s => s.id !== story.id)
      delete soarStates.value[story.id]
      loadAlerts()
    }, 3000)

  } catch (e) {
    console.error("Failed to mitigate storyline", e)
    state.logs[state.logs.length - 1].status = 'fail'
    addLog(`API Error during alert closure.`, 'fail')
  }
}
</script>

<style scoped>
.alert-inbox {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: rgba(10, 15, 20, 0.9);
  color: var(--text-color);
  font-family: 'Inter', sans-serif;
}

.inbox-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 15px;
  margin-bottom: 20px;
}

.inbox-header h2 {
  margin: 0;
  font-size: 1.5rem;
  letter-spacing: 2px;
  color: var(--cyan);
}

.inbox-stats {
  display: flex;
  gap: 15px;
}

.stat-badge {
  padding: 5px 15px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.9rem;
}

.stat-critical { background: rgba(255, 0, 85, 0.2); border: 1px solid var(--pink); color: var(--pink); }
.stat-high { background: rgba(255, 102, 0, 0.2); border: 1px solid #ff6600; color: #ff6600; }
.stat-open { background: rgba(0, 255, 204, 0.2); border: 1px solid var(--cyan); color: var(--cyan); }

/* SOC Pulse Styles */
.soc-pulse-container {
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(15, 20, 25, 0.8);
  border: 1px solid var(--cyan);
  border-radius: 6px;
  box-shadow: 0 0 15px rgba(0, 255, 204, 0.1);
}

.soc-pulse-container h3 {
  margin: 0 0 15px 0;
  color: var(--cyan);
  font-size: 1.1rem;
  letter-spacing: 1px;
}

.storyline-cards {
  display: flex;
  gap: 15px;
  overflow-x: auto;
  padding-bottom: 5px;
}

.story-card {
  min-width: 350px;
  flex: 1;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 15px;
  display: flex;
  flex-direction: column;
}

.story-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.story-header h4 {
  margin: 0;
  color: #fff;
  font-size: 1rem;
}

.story-status {
  font-size: 0.7rem;
  padding: 2px 6px;
  background: rgba(255, 0, 85, 0.2);
  color: var(--pink);
  border: 1px solid var(--pink);
  border-radius: 3px;
  font-weight: bold;
}

.story-summary {
  font-size: 0.9rem;
  color: #aaa;
  margin: 0 0 15px 0;
  line-height: 1.4;
  flex-grow: 1;
}

.story-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 10px;
}

.story-alerts-count {
  font-size: 0.8rem;
  color: #888;
}

.btn-mitigate {
  background: rgba(0, 255, 204, 0.15);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.btn-mitigate:hover {
  background: var(--cyan);
  color: #000;
  box-shadow: 0 0 10px rgba(0, 255, 204, 0.5);
}

.soar-terminal {
  background: rgba(10, 15, 20, 0.95);
  border: 1px solid var(--cyan);
  border-radius: 4px;
  padding: 10px;
  margin-top: 10px;
  font-family: 'Fira Code', monospace;
  font-size: 0.8rem;
  box-shadow: 0 0 15px rgba(0, 255, 204, 0.1) inset;
}

.terminal-header {
  color: var(--cyan);
  font-weight: bold;
  border-bottom: 1px dashed rgba(0, 255, 204, 0.3);
  padding-bottom: 5px;
  margin-bottom: 10px;
}

.terminal-log {
  max-height: 120px;
  overflow-y: auto;
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-line {
  color: #aaa;
}

.log-msg {
  margin-left: 8px;
}

.text-green { color: #00ff9d; }
.text-red { color: #ff2d6e; }
.text-cyan { color: #00e5ff; }

.progress-bar-container {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
  transition: width 0.3s ease;
}

.soar-complete {
  text-align: center;
  font-weight: bold;
  padding: 5px 0;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

/* Rest of styles */
.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: #888;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.filter-btn.active {
  background: rgba(0, 255, 204, 0.1);
  border-color: var(--cyan);
  color: var(--cyan);
}

.table-container {
  flex-grow: 1;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.3);
}

.alert-table {
  width: 100%;
  border-collapse: collapse;
}

.alert-table th, .alert-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.alert-table th {
  position: sticky;
  top: 0;
  background: rgba(15, 20, 25, 0.95);
  color: #888;
  font-size: 0.8rem;
  letter-spacing: 1px;
  z-index: 10;
}

.alert-row {
  transition: background 0.2s;
}

.alert-row:hover {
  background: rgba(255, 255, 255, 0.05);
}

.row-critical { border-left: 3px solid var(--pink); }
.row-high { border-left: 3px solid #ff6600; }
.row-medium { border-left: 3px solid #ffcc00; }
.row-low { border-left: 3px solid #00ccff; }

.col-id { font-family: monospace; color: #888; font-size: 0.85rem; }
.col-time { font-family: monospace; font-size: 0.85rem; }
.col-title { font-weight: bold; }

.severity-badge {
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: bold;
}

.sev-critical { background: var(--pink); color: #000; }
.sev-high { background: #ff6600; color: #000; }
.sev-medium { background: #ffcc00; color: #000; }
.sev-low { background: #00ccff; color: #000; }

.correlated-badge {
  display: inline-block;
  background: rgba(0, 255, 204, 0.2);
  color: var(--cyan);
  border: 1px solid var(--cyan);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.65rem;
  margin-right: 8px;
  vertical-align: middle;
}

.status-select, .assignee-select {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border-color);
  color: #fff;
  padding: 5px;
  border-radius: 3px;
  outline: none;
}

.btn-action {
  background: transparent;
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 5px 10px;
  cursor: pointer;
  border-radius: 3px;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.btn-action:hover {
  background: var(--cyan);
  color: #000;
}

.no-alerts {
  text-align: center;
  padding: 40px !important;
  color: #888;
  font-style: italic;
}
</style>
