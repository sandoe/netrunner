<template>
  <div class="hunting-container">
    <div class="header">
      <h2><span class="glitch-text" data-text="THREAT">THREAT</span> HUNTING</h2>
      <p class="subtitle">Search SIEM logs, alerts, and audit trails</p>
    </div>

    <div class="search-box">
      <input 
        v-model="query" 
        @keyup.enter="performSearch"
        type="text" 
        class="cyber-input" 
        placeholder="e.g. 'critical', '192.168.', 'botnet'"
      >
      <button class="cyber-button primary" @click="performSearch" :disabled="loading">
        {{ loading ? 'SCANNING...' : 'HUNT' }}
      </button>
    </div>

    <div class="results" v-if="results">
      <div class="stats">
        <span>Alerts Found: {{ results.alerts_found }}</span>
        <span>Audit Logs Found: {{ results.audit_logs_found }}</span>
      </div>

      <div class="tabs">
        <button 
          :class="['tab', { active: activeTab === 'alerts' }]" 
          @click="activeTab = 'alerts'">
          Alerts
        </button>
        <button 
          :class="['tab', { active: activeTab === 'audits' }]" 
          @click="activeTab = 'audits'">
          Audit Logs
        </button>
      </div>

      <div class="tab-content" v-if="activeTab === 'alerts'">
        <table v-if="results.alerts.length > 0">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Severity</th>
              <th>Title</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="alert in results.alerts" :key="alert.id">
              <td>{{ new Date(alert.created_at * 1000).toLocaleString() }}</td>
              <td><span :class="['badge', alert.severity]">{{ alert.severity }}</span></td>
              <td>{{ alert.title }}</td>
              <td>{{ alert.status }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="no-data">No alerts matched the query.</div>
      </div>

      <div class="tab-content" v-if="activeTab === 'audits'">
        <table v-if="results.audit_logs.length > 0">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User</th>
              <th>Action</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in results.audit_logs" :key="log.id">
              <td>{{ new Date(log.timestamp * 1000).toLocaleString() }}</td>
              <td>{{ log.user_id }}</td>
              <td><span class="badge info">{{ log.action }}</span></td>
              <td>{{ log.details }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="no-data">No audit logs matched the query.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { searchThreatsHuntingSearchGet } from '@/api_client'

const query = ref('')
const loading = ref(false)
const results = ref<any>(null)
const activeTab = ref('alerts')

const performSearch = async () => {
  if (!query.value.trim()) return
  loading.value = true
  try {
    const res = await searchThreatsHuntingSearchGet({ query: { q: query.value, limit: 100 } })
    results.value = res.data || []
    // Auto switch to whichever tab has data
    if (results.value.alerts_found === 0 && results.value.audit_logs_found > 0) {
      activeTab.value = 'audits'
    } else {
      activeTab.value = 'alerts'
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hunting-container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  color: #fff;
}

.header {
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--accent-blue);
  padding-bottom: 1rem;
}
.header h2 {
  font-family: 'Orbitron', sans-serif;
  color: var(--accent-blue);
  margin: 0;
  font-size: 2rem;
}

.search-box {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.cyber-input {
  flex: 1;
  background: rgba(0, 20, 40, 0.5);
  border: 1px solid var(--accent-blue);
  color: #fff;
  padding: 1rem;
  font-size: 1.2rem;
  font-family: monospace;
  outline: none;
  border-radius: 4px;
}
.cyber-input:focus {
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
}

.stats {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.5rem;
  font-family: monospace;
  color: #00f0ff;
}

.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.tab {
  background: none;
  border: none;
  color: #888;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-size: 1.1rem;
}
.tab.active {
  color: #00f0ff;
  border-bottom: 2px solid #00f0ff;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(10, 15, 30, 0.8);
}
th, td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
th {
  color: #aaa;
  font-weight: normal;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  font-size: 0.8rem;
  text-transform: uppercase;
}
.badge.critical { background: rgba(255, 0, 0, 0.2); color: #ff3333; border: 1px solid #ff3333; }
.badge.high { background: rgba(255, 165, 0, 0.2); color: #ffa500; border: 1px solid #ffa500; }
.badge.medium { background: rgba(255, 255, 0, 0.2); color: #ffff00; border: 1px solid #ffff00; }
.badge.low { background: rgba(0, 255, 0, 0.2); color: #00ff00; border: 1px solid #00ff00; }
.badge.info { background: rgba(0, 240, 255, 0.2); color: #00f0ff; border: 1px solid #00f0ff; }

.no-data {
  padding: 2rem;
  text-align: center;
  color: #888;
  font-style: italic;
}
</style>
