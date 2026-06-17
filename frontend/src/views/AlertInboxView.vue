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
            <td class="col-title">{{ alert.title }}</td>
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
const currentFilter = ref<'all' | 'new' | 'open' | 'closed'>('new')
let pollInterval: any = null

const loadAlerts = async () => {
  try {
    const { data, error } = await api.get('/alerts')
    if (data) {
      alerts.value = data
    }
  } catch (e) {
    console.error("Failed to load alerts", e)
  }
}

onMounted(() => {
  loadAlerts()
  pollInterval = setInterval(loadAlerts, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

const filteredAlerts = computed(() => {
  if (currentFilter.value === 'all') return alerts.value
  if (currentFilter.value === 'closed') {
    return alerts.value.filter(a => a.status === 'closed' || a.status === 'false_positive')
  }
  return alerts.value.filter(a => a.status === currentFilter.value)
})

const formatTime = (ts: number) => {
  const d = new Date(ts * 1000)
  return d.toISOString().replace('T', ' ').substring(0, 19)
}

const updateStatus = async (id: string, status: string) => {
  try {
    await api.patch(`/alerts/${id}`, { status })
    await loadAlerts()
  } catch (e) {
    console.error("Failed to update status", e)
  }
}

const updateAssignee = async (id: string, assignee_id: string | null) => {
  try {
    await api.patch(`/alerts/${id}`, { assignee_id: assignee_id || "" })
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
