<template>
  <div class="db-performance-workspace" style="display: flex; flex-direction: column; gap: 20px; font-family: var(--font-ui); margin-top: 10px; margin-bottom: 20px;">
    
    <div class="cyber-card" style="display: flex; flex-direction: column;">
      <div class="card-title-bar">
        <span>📈 LIVE YDEEVNE OVERVÅGNING (PERFORMANCE)</span>
        <div style="display: flex; gap: 10px; align-items: center;">
          <label style="font-size: 10px; display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--textbr);">
            <input type="checkbox" v-model="autoRefresh" style="width: auto; margin: 0;" />
            Auto-refresh (5s)
          </label>
          <button class="btn-action-sm btn-insert" style="font-size: 8px; height: 22px; padding: 0 8px;" :disabled="loading || !connected" @click="fetchMetrics">🔄 OPDATER NU</button>
        </div>
      </div>

      <div class="performance-content" style="padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 16px; min-height: 500px;">
        <div v-if="!connected" class="empty-warning" style="text-align: center; padding: 40px; border: 1px dashed var(--pink); border-radius: 4px; background: rgba(255,45,110,0.03); color: var(--pink); font-family: var(--font-co); font-size: 11px;">
          ⚠️ KONSOL DISCONNECTED<br>Forbind til en database for at se live-ydeevne.
        </div>
        
        <div v-else-if="dbConfig.type === 'sqlite'" class="empty-warning" style="text-align: center; padding: 40px; border: 1px dashed var(--cyan); border-radius: 4px; background: rgba(0,229,255,0.03); color: var(--cyan); font-family: var(--font-co); font-size: 11px;">
          ℹ️ SQLITE ENGINE INFO<br>SQLite er filbaseret og har ingen aktiv server-proces at overvåge.
        </div>

        <div v-else-if="loading && timeLabels.length === 0" class="terminal-loader" style="margin: 40px auto;">
          <div class="spinner"></div>
          <div class="loading-text" style="font-family: var(--font-co); font-size: 10px; color: var(--cyan);">HENTER METRIKKER...</div>
        </div>

        <template v-else>
          <!-- Dual Chart Workspace -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; flex: 1;">
            
            <!-- Chart 1: Memory -->
            <div class="chart-container" style="background: rgba(8, 16, 32, 0.4); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 4px; padding: 12px; display: flex; flex-direction: column; min-height: 250px;">
              <div style="font-family: var(--font-co); font-size: 10px; color: var(--cyan); text-transform: uppercase; margin-bottom: 10px;">💾 RAM Allocation (Heap / Buffer)</div>
              <div style="position: relative; flex: 1;">
                <Line v-if="timeLabels.length > 0" :data="memChartData" :options="chartOptions" />
                <div v-else style="color: rgba(0,229,255,0.4); text-align: center; margin-top: 60px; font-family: var(--font-co); font-size: 10px;">VENTER PÅ DATA...</div>
              </div>
            </div>

            <!-- Chart 2: Operations / Connections -->
            <div class="chart-container" style="background: rgba(8, 16, 32, 0.4); border: 1px solid rgba(255, 45, 110, 0.2); border-radius: 4px; padding: 12px; display: flex; flex-direction: column; min-height: 250px;">
              <div style="font-family: var(--font-co); font-size: 10px; color: var(--pink); text-transform: uppercase; margin-bottom: 10px;">⚡ Operations & Queries</div>
              <div style="position: relative; flex: 1;">
                <Line v-if="timeLabels.length > 0" :data="opsChartData" :options="chartOptionsOps" />
                <div v-else style="color: rgba(255,45,110,0.4); text-align: center; margin-top: 60px; font-family: var(--font-co); font-size: 10px;">VENTER PÅ DATA...</div>
              </div>
            </div>

          </div>

          <!-- Raw Data Expander -->
          <details style="margin-top: 10px; border: 1px solid rgba(0,255,157,0.2); border-radius: 4px; background: rgba(0,0,0,0.3);">
            <summary style="font-family: var(--font-co); font-size: 10px; color: var(--green); padding: 8px 12px; cursor: pointer; user-select: none;">Vis Rå Diagnostics Data</summary>
            <div style="padding: 12px; border-top: 1px solid rgba(0,255,157,0.2); max-height: 200px; overflow-y: auto;">
               <pre style="margin: 0; font-family: var(--font-co); font-size: 9px; color: rgba(0,255,157,0.6); white-space: pre-wrap;">{{ rawStatsText }}</pre>
            </div>
          </details>

        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { api } from '@/api/client'
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps<{ nodeId: string }>()

const { 
  dbConfig, 
  connected, 
  loading, 
  showFlashMsg,
  buildDbCommand 
} = useDatabaseConfig()

const rawStatsText = ref('')
const autoRefresh = ref(false)
let refreshTimer: any = null

// Chart Data Stores
const timeLabels = ref<string[]>([])
const memData = ref<number[]>([])
const opsData = ref<number[]>([])
const MAX_POINTS = 30

function pushData(memMb: number, ops: number) {
  const time = new Date().toLocaleTimeString('da-DK', { hour12: false })
  timeLabels.value.push(time)
  memData.value.push(memMb)
  opsData.value.push(ops)

  if (timeLabels.value.length > MAX_POINTS) {
    timeLabels.value.shift()
    memData.value.shift()
    opsData.value.shift()
  }
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  scales: {
    x: { grid: { color: 'rgba(0, 229, 255, 0.1)' }, ticks: { color: 'rgba(0, 229, 255, 0.6)', font: { family: 'Courier New', size: 9 } } },
    y: { grid: { color: 'rgba(0, 229, 255, 0.1)' }, ticks: { color: 'rgba(0, 229, 255, 0.6)', font: { family: 'Courier New', size: 9 } } }
  },
  plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } }
}

const chartOptionsOps = {
  ...chartOptions,
  scales: {
    x: { grid: { color: 'rgba(255, 45, 110, 0.1)' }, ticks: { color: 'rgba(255, 45, 110, 0.6)', font: { family: 'Courier New', size: 9 } } },
    y: { grid: { color: 'rgba(255, 45, 110, 0.1)' }, ticks: { color: 'rgba(255, 45, 110, 0.6)', font: { family: 'Courier New', size: 9 } } }
  }
}

const memChartData = computed(() => ({
  labels: timeLabels.value,
  datasets: [{
    label: 'Heap Allocated (MB)',
    data: memData.value,
    borderColor: '#00e5ff',
    backgroundColor: 'rgba(0, 229, 255, 0.15)',
    borderWidth: 2,
    pointRadius: 2,
    pointBackgroundColor: '#00e5ff',
    fill: true,
    tension: 0.3
  }]
}))

const opsChartData = computed(() => ({
  labels: timeLabels.value,
  datasets: [{
    label: 'Operations / Connections',
    data: opsData.value,
    borderColor: '#ff2d6e',
    backgroundColor: 'rgba(255, 45, 110, 0.15)',
    borderWidth: 2,
    pointRadius: 2,
    pointBackgroundColor: '#ff2d6e',
    fill: true,
    tension: 0.3
  }]
}))

async function fetchMetrics() {
  if (!connected.value) return
  const type = dbConfig.value.type
  if (type === 'sqlite') {
    rawStatsText.value = ''
    return
  }

  const isAuto = !!refreshTimer && autoRefresh.value
  if (!isAuto && timeLabels.value.length === 0) loading.value = true
  
  try {
    let sql = ''
    if (type === 'mysql') sql = 'SHOW GLOBAL STATUS;'
    else if (type === 'postgresql') sql = 'SELECT * FROM pg_stat_activity;'
    else if (type === 'mssql') sql = 'SELECT * FROM sys.dm_os_performance_counters;'
    else if (type === 'influxdb') sql = 'SHOW STATS;'
    else if (type === 'mongodb') sql = 'db.serverStatus()'
    else if (type === 'redis') sql = 'INFO'
    else { loading.value = false; return; }

    const cmd = buildDbCommand(sql, true)
    const res = await api.executeNode(props.nodeId, [cmd])
    const out = res.results?.[0]?.output || ''
    const err = res.results?.[0]?.error || ''

    if (err || (out.toLowerCase().startsWith('error') || out.toLowerCase().includes('err: error parsing query'))) {
      throw new Error(err || out || 'Kunne ikke hente ydeevne-data.')
    }

    rawStatsText.value = out

    // PARSE METRICS
    let currentMem = 0
    let currentOps = 0

    if (type === 'influxdb') {
      const rows = out.split('\n').map(r => r.split(','))
      for (let i = 0; i < rows.length; i++) {
        if (!rows[i] || rows[i].length === 0) continue
        const head = rows[i][0]

        // Parse memory from 'runtime' block
        if (head === 'runtime' && i > 0) {
           const headerRow = rows[i-1]
           const heapIdx = headerRow.indexOf('HeapAlloc')
           if (heapIdx !== -1) {
             const bytes = parseInt(rows[i][heapIdx] || '0', 10)
             currentMem = parseFloat((bytes / 1024 / 1024).toFixed(2)) // MB
           }
        }

        // Parse operations from 'write' or 'httpd' block
        if (head === 'httpd' && i > 0) {
           const headerRow = rows[i-1]
           const reqIdx = headerRow.indexOf('reqActive')
           const queryIdx = headerRow.indexOf('queryReq')
           if (reqIdx !== -1) currentOps += parseInt(rows[i][reqIdx] || '0', 10)
           if (queryIdx !== -1) currentOps += parseInt(rows[i][queryIdx] || '0', 10)
        }
      }
    } else if (type === 'mysql') {
      const rows = out.split('\n').map(r => r.split('\t'))
      for (const row of rows) {
        if (row[0] === 'Threads_connected') currentOps += parseInt(row[1] || '0', 10)
        if (row[0] === 'Bytes_received') currentMem += parseFloat((parseInt(row[1] || '0', 10) / 1024 / 1024).toFixed(2))
      }
    } else if (type === 'postgresql') {
      const rows = out.split('\n')
      // Subtract header and empty lines for active connections
      currentOps = rows.filter(r => r.trim() !== '').length - 1
      currentMem = 0 // Postgres memory is tracked by the OS, not pg_stat_activity
    } else if (type === 'mssql') {
      const rows = out.split('\n').map(r => r.split('\t'))
      for (const row of rows) {
        const counterName = (row[1] || '').trim()
        const counterValue = parseInt(row[3] || '0', 10)
        if (counterName === 'User Connections') currentOps += counterValue
        if (counterName === 'Target Server Memory (KB)') currentMem = parseFloat((counterValue / 1024).toFixed(2))
      }
    } else if (type === 'redis') {
      const lines = out.split('\n')
      for (const line of lines) {
        if (line.startsWith('used_memory:')) currentMem = parseFloat((parseInt(line.split(':')[1] || '0', 10) / 1024 / 1024).toFixed(2))
        if (line.startsWith('connected_clients:')) currentOps = parseInt(line.split(':')[1] || '0', 10)
      }
    } else if (type === 'mongodb') {
      try {
        // Strip shell wrapper noise if present
        const jsonStr = out.substring(out.indexOf('{'), out.lastIndexOf('}') + 1)
        const parsed = JSON.parse(jsonStr)
        currentMem = parsed?.mem?.resident || 0
        currentOps = parsed?.connections?.current || 0
      } catch (e) {
        // Fallback if parsing fails
      }
    }

    pushData(currentMem, currentOps)

  } catch (err: any) {
    if (!isAuto) showFlashMsg(`Fejl i ydeevne overvågning: ${err.message || err}`, true)
  } finally {
    if (!isAuto) loading.value = false
  }
}

watch(autoRefresh, (val) => {
  if (val) {
    fetchMetrics()
    refreshTimer = setInterval(() => {
      if (connected.value) {
        fetchMetrics()
      } else {
        autoRefresh.value = false
      }
    }, 5000)
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
})

watch(() => props.nodeId, () => {
  if (connected.value) {
    timeLabels.value = []
    memData.value = []
    opsData.value = []
    fetchMetrics()
  }
})

watch(() => connected.value, (newConn) => {
  if (newConn) {
    timeLabels.value = []
    memData.value = []
    opsData.value = []
    fetchMetrics()
  } else {
    rawStatsText.value = ''
    autoRefresh.value = false
    timeLabels.value = []
  }
})

onMounted(() => {
  if (connected.value) {
    fetchMetrics()
  }
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.empty-warning {
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

.btn-action-sm {
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--border);
  color: var(--textbr);
  padding: 6px 12px;
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  text-transform: uppercase;
}

.btn-insert {
  border-color: rgba(0, 255, 157, 0.3);
  color: var(--green);
}

.btn-insert:hover:not(:disabled) {
  border-color: var(--green) !important;
  color: white !important;
  background: rgba(0, 255, 157, 0.15) !important;
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.3) !important;
}

.terminal-loader {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid rgba(0, 229, 255, 0.1);
  border-top-color: var(--cyan);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
