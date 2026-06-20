<template>
  <div class="ir-view">
    <div class="header">
      <h1>🚨 Incident Response</h1>
      <p class="subtitle">Structured IR workflow & tracking</p>
    </div>

    <div class="tabs">
      <button v-for="tab in tabs" :key="tab.id" :class="['tab-btn', { active: activeTab === tab.id }]" @click="activeTab = tab.id">
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- Incidents -->
    <div v-if="activeTab === 'incidents'" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <h2>Incidents</h2>
          <button @click="showCreateForm = !showCreateForm" class="btn-secondary">+ New Incident</button>
        </div>

        <div v-if="showCreateForm" class="create-form">
          <div class="form-group">
            <label>Title</label>
            <input v-model="createForm.title" type="text" placeholder="Incident title" />
          </div>
          <div class="form-group">
            <label>Description</label>
            <textarea v-model="createForm.description" rows="3" placeholder="Describe the incident..."></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Severity</label>
              <select v-model="createForm.severity">
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div class="form-group">
              <label>Type</label>
              <select v-model="createForm.incident_type">
                <option value="malware">Malware</option>
                <option value="ransomware">Ransomware</option>
                <option value="data_breach">Data Breach</option>
                <option value="insider_threat">Insider Threat</option>
                <option value="ddos">DDoS</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div class="form-group">
              <label>Playbook</label>
              <select v-model="createForm.playbook_id">
                <option value="">None</option>
                <option v-for="p in playbooks" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
          </div>
          <button @click="createIncident" class="btn-primary">Create Incident</button>
        </div>

        <div v-for="inc in incidents" :key="inc.id" class="incident-card" @click="viewIncident(inc.id)">
          <div class="incident-header">
            <span class="incident-id">{{ inc.id }}</span>
            <span class="incident-title">{{ inc.title }}</span>
            <span :class="['severity', inc.severity]">{{ inc.severity }}</span>
            <span :class="['status', inc.status]">{{ inc.status }}</span>
          </div>
          <div class="incident-meta">
            <span>Phase: {{ inc.current_phase }}</span>
            <span>Type: {{ inc.type }}</span>
            <span>{{ formatDate(inc.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Incident Detail -->
    <div v-if="activeTab === 'detail' && currentIncident" class="tab-content">
      <div class="panel">
        <div class="incident-detail-header">
          <h2>{{ currentIncident.title }}</h2>
          <span :class="['severity', currentIncident.severity]">{{ currentIncident.severity }}</span>
        </div>
        <p>{{ currentIncident.description }}</p>

        <!-- Phase Progress -->
        <div class="phase-progress">
          <div v-for="phase in phases" :key="phase.id" :class="['phase-step', { active: phase.id === currentIncident.current_phase, completed: isPhaseCompleted(phase.id) }]">
            <span class="phase-name">{{ phase.name }}</span>
          </div>
        </div>

        <div class="form-group">
          <label>Update Phase</label>
          <select v-model="newPhase" @change="updatePhase">
            <option v-for="phase in phases" :key="phase.id" :value="phase.id">{{ phase.name }}</option>
          </select>
        </div>

        <!-- Timeline -->
        <h3>Timeline</h3>
        <div class="timeline">
          <div v-for="event in currentIncident.timeline" :key="event.timestamp" class="timeline-event">
            <span class="event-time">{{ formatDate(event.timestamp) }}</span>
            <span class="event-action">{{ event.action }}</span>
            <span class="event-details">{{ event.details }}</span>
          </div>
        </div>

        <!-- Evidence -->
        <h3>Evidence ({{ currentIncident.evidence?.length || 0 }})</h3>
        <div class="form-row">
          <select v-model="evidenceForm.evidence_type">
            <option value="memory_dump">Memory Dump</option>
            <option value="disk_image">Disk Image</option>
            <option value="pcap">Network Capture</option>
            <option value="log">Log File</option>
            <option value="screenshot">Screenshot</option>
          </select>
          <input v-model="evidenceForm.description" placeholder="Description" />
          <button @click="addEvidence" class="btn-small">Add</button>
        </div>

        <div v-for="ev in currentIncident.evidence" :key="ev.id" class="evidence-item">
          <span class="ev-type">{{ ev.type }}</span>
          <span class="ev-desc">{{ ev.description }}</span>
        </div>

        <!-- Actions -->
        <h3>Actions</h3>
        <div class="form-row">
          <select v-model="actionForm.phase">
            <option value="containment">Containment</option>
            <option value="eradication">Eradication</option>
            <option value="recovery">Recovery</option>
          </select>
          <input v-model="actionForm.description" placeholder="Action description" />
          <button @click="addAction" class="btn-small">Add</button>
        </div>
      </div>
    </div>

    <!-- Playbooks -->
    <div v-if="activeTab === 'playbooks'" class="tab-content">
      <div class="panel">
        <h2>IR Playbooks</h2>
        <div v-for="p in playbooks" :key="p.id" class="playbook-card">
          <h3>{{ p.name }}</h3>
          <p>{{ p.description }}</p>
          <div class="playbook-phases">
            <div v-for="(steps, phase) in p.phases" :key="phase" class="playbook-phase">
              <h4>{{ phase }}</h4>
              <ul>
                <li v-for="(step, idx) in steps" :key="idx">{{ step }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="activeTab === 'stats'" class="tab-content">
      <div class="panel">
        <h2>IR Statistics</h2>
        <div class="stats-grid" v-if="irStats">
          <div class="stat-card"><span class="stat-value">{{ irStats.total }}</span><span class="stat-label">Total</span></div>
          <div class="stat-card"><span class="stat-value open">{{ irStats.open }}</span><span class="stat-label">Open</span></div>
          <div class="stat-card"><span class="stat-value closed">{{ irStats.closed }}</span><span class="stat-label">Closed</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

const tabs = [
  { id: 'incidents', label: 'Incidents', icon: '📋' },
  { id: 'detail', label: 'Detail', icon: '🔍' },
  { id: 'playbooks', label: 'Playbooks', icon: '📖' },
  { id: 'stats', label: 'Stats', icon: '📊' },
]

const activeTab = ref('incidents')
const incidents = ref<any[]>([])
const currentIncident = ref<any>(null)
const phases = ref<any[]>([])
const playbooks = ref<any[]>([])
const irStats = ref<any>(null)
const showCreateForm = ref(false)
const newPhase = ref('')

const createForm = ref({ title: '', description: '', severity: 'high', incident_type: 'malware', playbook_id: '' })
const evidenceForm = ref({ evidence_type: 'memory_dump', description: '' })
const actionForm = ref({ phase: 'containment', description: '' })

onMounted(async () => {
  try {
    const [incRes, phRes, pbRes, stRes] = await Promise.all([
      api.get('/ir/incidents'),
      api.get('/ir/phases'),
      api.get('/ir/playbooks'),
      api.get('/ir/stats'),
    ])
    incidents.value = incRes.data?.incidents || []
    phases.value = phRes.data?.phases || []
    playbooks.value = pbRes.data?.playbooks || []
    irStats.value = stRes.data
  } catch (e) {
    console.error('Failed to load IR data', e)
  }
})

async function createIncident() {
  try {
    await api.post('/ir/incidents', createForm.value)
    const res = await api.get('/ir/incidents')
    incidents.value = res.data?.incidents || []
    showCreateForm.value = false
  } catch (e: any) {
    alert(e.response?.data?.detail || 'Failed')
  }
}

async function viewIncident(id: string) {
  try {
    const res = await api.get(`/ir/incidents/${id}`)
    currentIncident.value = res.data
    newPhase.value = res.data.current_phase
    activeTab.value = 'detail'
  } catch (e) {
    console.error('Failed', e)
  }
}

async function updatePhase() {
  if (!currentIncident.value) return
  try {
    await api.post(`/ir/incidents/${currentIncident.value.id}/phase`, { phase: newPhase.value })
    await viewIncident(currentIncident.value.id)
  } catch (e) {
    console.error('Failed', e)
  }
}

async function addEvidence() {
  if (!currentIncident.value) return
  try {
    await api.post(`/ir/incidents/${currentIncident.value.id}/evidence`, evidenceForm.value)
    await viewIncident(currentIncident.value.id)
    evidenceForm.value.description = ''
  } catch (e) {
    console.error('Failed', e)
  }
}

async function addAction() {
  if (!currentIncident.value) return
  try {
    await api.post(`/ir/incidents/${currentIncident.value.id}/action`, {
      ...actionForm.value,
      action_type: 'manual',
    })
    await viewIncident(currentIncident.value.id)
    actionForm.value.description = ''
  } catch (e) {
    console.error('Failed', e)
  }
}

function isPhaseCompleted(phaseId: string) {
  const order = ['detection', 'containment', 'eradication', 'recovery', 'post_incident']
  const currentIdx = order.indexOf(currentIncident.value?.current_phase || '')
  const phaseIdx = order.indexOf(phaseId)
  return phaseIdx < currentIdx
}

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleString()
}
</script>

<style scoped>
.ir-view { padding: 20px; color: #e0e0e0; }
.header h1 { color: #00ff88; margin-bottom: 4px; }
.subtitle { color: #888; margin-bottom: 20px; }
.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 8px; }
.tab-btn { padding: 8px 16px; background: #1a1a2e; border: 1px solid #333; color: #aaa; cursor: pointer; border-radius: 4px 4px 0 0; }
.tab-btn.active { background: #0f3460; color: #00ff88; border-color: #00ff88; }
.panel { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.panel h2 { color: #00ff88; margin-bottom: 16px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 4px; color: #aaa; }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px; background: #0d1117; border: 1px solid #333; color: #e0e0e0; border-radius: 4px; }
.form-row { display: flex; gap: 8px; margin-bottom: 12px; }
.form-row select, .form-row input { flex: 1; }
.btn-primary { padding: 10px 20px; background: #00ff88; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-secondary { padding: 8px 16px; background: #0f3460; color: #00ff88; border: 1px solid #00ff88; border-radius: 4px; cursor: pointer; }
.btn-small { padding: 6px 12px; background: #0f3460; color: #00ff88; border: 1px solid #00ff88; border-radius: 4px; cursor: pointer; }
.severity { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; text-transform: uppercase; }
.severity.critical { background: #ff4444; color: #fff; }
.severity.high { background: #ff8800; color: #000; }
.severity.medium { background: #ffaa00; color: #000; }
.severity.low { background: #00ff88; color: #000; }
.status { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
.status.open { background: #ff4444; color: #fff; }
.status.closed { background: #00ff88; color: #000; }
.incident-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 8px; cursor: pointer; }
.incident-card:hover { border-color: #00ff88; }
.incident-header { display: flex; gap: 12px; align-items: center; margin-bottom: 4px; }
.incident-id { color: #888; font-family: monospace; font-size: 0.85em; }
.incident-title { font-weight: bold; flex: 1; }
.incident-meta { display: flex; gap: 16px; font-size: 0.85em; color: #888; }
.incident-detail-header { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.phase-progress { display: flex; gap: 4px; margin-bottom: 20px; }
.phase-step { flex: 1; padding: 8px; text-align: center; background: #0d1117; border: 1px solid #333; border-radius: 4px; font-size: 0.85em; }
.phase-step.active { border-color: #00ff88; color: #00ff88; background: #0a1a0a; }
.phase-step.completed { border-color: #00ff88; background: rgba(0, 255, 136, 0.1); }
.timeline { margin-bottom: 20px; }
.timeline-event { display: flex; gap: 12px; padding: 8px; border-bottom: 1px solid #222; font-size: 0.85em; }
.event-time { color: #888; min-width: 140px; }
.event-action { color: #00ff88; min-width: 120px; }
.evidence-item { display: flex; gap: 12px; padding: 8px; background: #0d1117; border-radius: 4px; margin-bottom: 4px; }
.ev-type { background: #0f3460; padding: 2px 8px; border-radius: 4px; color: #00ff88; font-size: 0.85em; }
.playbook-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.playbook-card h3 { color: #00ff88; margin-bottom: 4px; }
.playbook-phases { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top: 12px; }
.playbook-phase h4 { color: #00ff88; margin-bottom: 4px; font-size: 0.85em; }
.playbook-phase ul { padding-left: 16px; font-size: 0.8em; color: #aaa; }
.playbook-phase li { margin-bottom: 2px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-card { text-align: center; padding: 16px; background: #0d1117; border: 1px solid #333; border-radius: 6px; }
.stat-value { font-size: 2em; font-weight: bold; color: #00ff88; display: block; }
.stat-value.open { color: #ff4444; }
.stat-value.closed { color: #00ff88; }
.stat-label { font-size: 0.85em; color: #888; }
</style>
