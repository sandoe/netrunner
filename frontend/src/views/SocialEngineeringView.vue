<template>
  <div class="se-view">
    <div class="header">
      <h1>🎯 Social Engineering</h1>
      <p class="subtitle">Phishing simulation & awareness training</p>
    </div>

    <div class="tabs">
      <button v-for="tab in tabs" :key="tab.id" :class="['tab-btn', { active: activeTab === tab.id }]" @click="activeTab = tab.id">
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- Campaigns -->
    <div v-if="activeTab === 'campaigns'" class="tab-content">
      <div class="panel">
        <h2>Campaigns</h2>
        <div v-for="camp in campaigns" :key="camp.id" class="campaign-card">
          <div class="campaign-header">
            <span class="campaign-name">{{ camp.name }}</span>
            <span :class="['status-badge', camp.status]">{{ camp.status }}</span>
          </div>
          <div class="campaign-stats">
            <span>Sent: {{ camp.stats?.sent || 0 }}</span>
            <span>Clicked: {{ camp.stats?.clicked || 0 }}</span>
            <span>Rate: {{ camp.stats?.total ? ((camp.stats?.clicked || 0) / camp.stats.total * 100).toFixed(1) : 0 }}%</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <h2>Create Campaign</h2>
        <div class="form-group">
          <label>Campaign Name</label>
          <input v-model="campaignForm.name" type="text" placeholder="Q4 Phishing Test" />
        </div>
        <div class="form-group">
          <label>Template</label>
          <select v-model="campaignForm.template_id">
            <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }} — {{ t.description }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>Targets (JSON array of {name, email})</label>
          <textarea v-model="targetsJson" rows="4" placeholder='[{"name": "John", "email": "john@corp.com"}]'></textarea>
        </div>
        <button @click="createCampaign" class="btn-primary">Create Campaign</button>
      </div>
    </div>

    <!-- Templates -->
    <div v-if="activeTab === 'templates'" class="tab-content">
      <div class="panel">
        <h2>Phishing Templates</h2>
        <div class="template-grid">
          <div v-for="t in templates" :key="t.id" class="template-card">
            <h3>{{ t.name }}</h3>
            <span class="template-category">{{ t.category }}</span>
            <p>{{ t.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Pretexting -->
    <div v-if="activeTab === 'pretexting'" class="tab-content">
      <div class="panel">
        <h2>Pretexting Scenarios</h2>
        <div v-for="s in scenarios" :key="s.id" class="scenario-card">
          <h3>{{ s.name }}</h3>
          <span class="scenario-category">{{ s.category }}</span>
          <p>{{ s.description }}</p>
          <div class="script-steps">
            <div v-for="(step, idx) in s.script" :key="idx" class="script-step">
              <span class="step-num">{{ idx + 1 }}</span>
              <span>{{ step }}</span>
            </div>
          </div>
          <p class="tips"><strong>Tips:</strong> {{ s.tips }}</p>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="activeTab === 'stats'" class="tab-content">
      <div class="panel">
        <h2>Statistics</h2>
        <div class="stats-grid" v-if="stats">
          <div class="stat-card"><span class="stat-value">{{ stats.total_campaigns }}</span><span class="stat-label">Campaigns</span></div>
          <div class="stat-card"><span class="stat-value">{{ stats.total_emails }}</span><span class="stat-label">Emails</span></div>
          <div class="stat-card"><span class="stat-value">{{ stats.total_clicked }}</span><span class="stat-label">Clicked</span></div>
          <div class="stat-card"><span class="stat-value">{{ stats.click_rate }}%</span><span class="stat-label">Click Rate</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const tabs = [
  { id: 'campaigns', label: 'Campaigns', icon: '📧' },
  { id: 'templates', label: 'Templates', icon: '📝' },
  { id: 'pretexting', label: 'Pretexting', icon: '🎭' },
  { id: 'stats', label: 'Stats', icon: '📊' },
]

const activeTab = ref('campaigns')
const campaigns = ref<any[]>([])
const templates = ref<any[]>([])
const scenarios = ref<any[]>([])
const stats = ref<any>(null)
const campaignForm = ref({ name: '', template_id: 'password_expire' })
const targetsJson = ref('[{"name": "Test User", "email": "test@corp.com"}]')

onMounted(async () => {
  try {
    const [campRes, templRes, scenRes, statsRes] = await Promise.all([
      api.get('/se/campaigns'),
      api.get('/se/templates'),
      api.get('/se/pretexting'),
      api.get('/se/stats'),
    ])
    campaigns.value = campRes.data?.campaigns || []
    templates.value = templRes.data?.templates || []
    scenarios.value = scenRes.data?.scenarios || []
    stats.value = statsRes.data
  } catch (e) {
    console.error('Failed to load SE data', e)
  }
})

async function createCampaign() {
  try {
    const targets = JSON.parse(targetsJson.value)
    await api.post('/se/campaigns', { ...campaignForm.value, targets })
    const res = await api.get('/se/campaigns')
    campaigns.value = res.data?.campaigns || []
  } catch (e: any) {
    alert(e.message || 'Failed to create campaign')
  }
}
</script>

<style scoped>
.se-view { padding: 20px; color: #e0e0e0; }
.header h1 { color: #00ff88; margin-bottom: 4px; }
.subtitle { color: #888; margin-bottom: 20px; }
.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 8px; }
.tab-btn { padding: 8px 16px; background: #1a1a2e; border: 1px solid #333; color: #aaa; cursor: pointer; border-radius: 4px 4px 0 0; }
.tab-btn.active { background: #0f3460; color: #00ff88; border-color: #00ff88; }
.panel { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.panel h2 { color: #00ff88; margin-bottom: 16px; }
.campaign-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.campaign-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.campaign-name { font-weight: bold; }
.status-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }
.status-badge.created { background: #0f3460; color: #00ff88; }
.status-badge.active { background: #1a4a1a; color: #88ff00; }
.campaign-stats { display: flex; gap: 16px; font-size: 0.9em; color: #888; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 4px; color: #aaa; }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px; background: #0d1117; border: 1px solid #333; color: #e0e0e0; border-radius: 4px; font-family: monospace; }
.btn-primary { padding: 10px 20px; background: #00ff88; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.template-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; }
.template-card h3 { margin-bottom: 4px; }
.template-category { background: #0f3460; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; color: #00ff88; }
.scenario-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.scenario-card h3 { margin-bottom: 4px; }
.scenario-category { background: #4a1a1a; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; color: #ff8800; }
.script-steps { margin: 12px 0; }
.script-step { display: flex; gap: 8px; margin-bottom: 4px; padding: 6px; background: #111; border-radius: 4px; }
.step-num { color: #00ff88; font-weight: bold; }
.tips { font-size: 0.9em; color: #888; font-style: italic; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card { text-align: center; padding: 16px; background: #0d1117; border: 1px solid #333; border-radius: 6px; }
.stat-value { font-size: 2em; font-weight: bold; color: #00ff88; display: block; }
.stat-label { font-size: 0.85em; color: #888; }
</style>
