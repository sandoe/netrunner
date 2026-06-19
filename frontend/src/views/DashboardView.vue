<template>
  <div class="dashboard-container" :class="{ 'war-room-mode': warRoomMode }">
    <div class="header">
      <div>
        <h2><span class="glitch-text" data-text="EXECUTIVE">EXECUTIVE</span> DASHBOARD</h2>
        <p class="subtitle">CISO Level Network Overview</p>
      </div>
      <button class="btn-war-room" @click="warRoomMode = !warRoomMode" :aria-pressed="warRoomMode">
        <span aria-hidden="true">{{ warRoomMode ? '🔥' : '🛡️' }}</span> {{ warRoomMode ? 'DISABLE WAR ROOM' : 'ACTIVATE WAR ROOM' }}
      </button>
    </div>

    <!-- Quick Stats from WelcomeView -->
    <div class="dashboard-stats dashboard-stats-margin">
      <button class="dash-stat-box" @click="$router.push('/node')">
        <div class="ds-value">{{ store.nodeList.length }}</div>
        <div class="ds-label">REGISTERED NODES</div>
      </button>
      <button class="dash-stat-box" @click="$router.push('/pulse')">
        <div class="ds-value text-green">{{ store.connectedCount }}</div>
        <div class="ds-label">ACTIVE CONNECTIONS</div>
      </button>
      <button class="dash-stat-box" @click="warRoomMode = !warRoomMode">
        <div class="ds-value" :class="warRoomMode ? 'text-pink' : 'text-cyan'">{{ warRoomMode ? 'ACTIVE' : 'STANDBY' }}</div>
        <div class="ds-label">WAR ROOM STATUS</div>
      </button>
      <button class="dash-stat-box border-pink" @click="$router.push('/alerts')">
        <div class="ds-value text-pink">!</div>
        <div class="ds-label">ALERT INBOX</div>
      </button>
    </div>

    <div v-if="loading" class="loading">Loading Analytics...</div>
    <div v-else-if="errorMsg" class="error-state">{{ errorMsg }}</div>
    <div v-else-if="metrics" class="dashboard-content">
      
      <!-- Metrics Grid -->
      <div class="metrics-grid">
        <div class="metric-card warning">
          <div class="icon"><span aria-hidden="true">🔥</span></div>
          <div class="data">
            <h3>{{ metrics.critical_alerts }}</h3>
            <span>Critical Threats</span>
          </div>
        </div>
        <div class="metric-card success">
          <div class="icon"><span aria-hidden="true">🛡️</span></div>
          <div class="data">
            <h3>{{ metrics.mitigation_rate_percent }}%</h3>
            <span>Mitigation Rate</span>
          </div>
        </div>
        <div class="metric-card">
          <div class="icon"><span aria-hidden="true">🤖</span></div>
          <div class="data">
            <h3>{{ metrics.active_playbooks }}</h3>
            <span>Active Playbooks</span>
          </div>
        </div>
        <div class="metric-card info">
          <div class="icon"><span aria-hidden="true">📊</span></div>
          <div class="data">
            <h3>{{ metrics.total_alerts }}</h3>
            <span>Total Events</span>
          </div>
        </div>
      </div>

      <!-- Charts Area -->
      <div class="charts-area">
        <div class="chart-container">
          <h3>THREAT TRENDS (LAST 7 DAYS)</h3>
          <div class="chart-wrapper">
            <div v-if="!trends || trends.labels.length === 0" class="empty-state">No data available for the last 7 days</div>
            <Line v-else :data="lineChartData" :options="chartOptions" aria-label="Threat Trends Line Chart" role="img" />
          </div>
        </div>
        
        <div class="chart-container">
          <h3>ALERT TRIAGE STATUS</h3>
          <div class="chart-wrapper doughnut-wrapper">
            <div v-if="!metrics || (metrics.new_alerts === 0 && metrics.investigating_alerts === 0 && metrics.closed_alerts === 0 && metrics.false_positives === 0)" class="empty-state">No alert data available</div>
            <Doughnut v-else :data="doughnutChartData" :options="chartOptions" aria-label="Alert Triage Status Doughnut Chart" role="img" />
          </div>
        </div>
      </div>
      
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { getDashboardSummaryAnalyticsSummaryGet } from '@/api_client'
import { useNodesStore } from '@/stores/nodes'
import { useRouter } from 'vue-router'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js'
import { Line, Doughnut } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

interface MetricData {
  critical_alerts: number;
  mitigation_rate_percent: number;
  active_playbooks: number;
  total_alerts: number;
  new_alerts: number;
  investigating_alerts: number;
  closed_alerts: number;
  false_positives: number;
}

interface TrendDataset {
  label: string;
  data: number[];
}

interface TrendData {
  labels: string[];
  datasets: TrendDataset[];
}

const store = useNodesStore()
const router = useRouter()

const loading = ref(true)
const errorMsg = ref<string | null>(null)
const metrics = ref<MetricData | null>(null)
const trends = ref<TrendData | null>(null)
const summary = ref<any>(null)

const warRoomMode = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const fetchData = async () => {
  try {
    errorMsg.value = null
    const res = await getDashboardSummaryAnalyticsSummaryGet()
    summary.value = res.data
    metrics.value = res.metrics
    trends.value = res.trends
  } catch (err) {
    console.error("Error loading dashboard", err)
    errorMsg.value = "Failed to load dashboard data. Please try again later."
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
  // Poll every 30 seconds for live feeling
  pollTimer = setInterval(fetchData, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  color: '#aaa',
  plugins: {
    legend: {
      labels: { color: '#ccc', font: { family: 'Orbitron' } }
    }
  },
  scales: {
    x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#aaa' } },
    y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#aaa' } }
  }
}

const lineChartData = computed(() => {
  if (!trends.value) return { labels: [], datasets: [] }
  return {
    labels: trends.value.labels,
    datasets: [
      {
        label: trends.value.datasets[0].label,
        backgroundColor: warRoomMode.value ? 'rgba(255, 51, 102, 0.4)' : 'rgba(255, 51, 102, 0.2)',
        borderColor: '#ff3366',
        data: trends.value.datasets[0].data,
        tension: 0.4,
        fill: true
      },
      {
        label: trends.value.datasets[1].label,
        backgroundColor: warRoomMode.value ? 'rgba(255, 170, 0, 0.4)' : 'rgba(0, 240, 255, 0.2)',
        borderColor: warRoomMode.value ? '#ffaa00' : '#00f0ff',
        data: trends.value.datasets[1].data,
        tension: 0.4,
        fill: true
      }
    ]
  }
})

const doughnutChartData = computed(() => {
  if (!metrics.value) return { labels: [], datasets: [] }
  return {
    labels: ['New', 'Investigating', 'Closed', 'False Positive'],
    datasets: [
      {
        backgroundColor: warRoomMode.value 
          ? ['#ff3366', '#ff0000', '#aa0000', '#550000']
          : ['#ff3366', '#ffaa00', '#00f0ff', '#555555'],
        borderColor: '#111827',
        borderWidth: 2,
        data: [
          metrics.value.new_alerts,
          metrics.value.investigating_alerts,
          metrics.value.closed_alerts,
          metrics.value.false_positives
        ]
      }
    ]
  }
})
</script>

<style scoped>
.dashboard-container {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  color: #fff;
  transition: all 0.3s ease;
  min-height: 100vh;
}

/* War Room Mode Styling */
.dashboard-container.war-room-mode {
  background: radial-gradient(circle at center, #2a0808 0%, #050000 100%);
}
.dashboard-container.war-room-mode .header h2 {
  color: #ff3366;
  text-shadow: 0 0 15px rgba(255, 51, 102, 0.6);
  animation: pulse-red 2s infinite;
}
.dashboard-container.war-room-mode .metric-card {
  border-color: rgba(255, 51, 102, 0.4);
  box-shadow: 0 4px 15px rgba(255, 51, 102, 0.1);
}
.dashboard-container.war-room-mode .chart-container {
  border-color: rgba(255, 51, 102, 0.4);
}

.header {
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--cyan, #00f0ff);
  padding-bottom: 1rem;
  transition: border-color 0.3s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
@media (max-width: 600px) {
  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
}
.dashboard-container.war-room-mode .header {
  border-bottom-color: var(--pink, #ff3366);
}

.header h2 {
  font-family: 'Orbitron', sans-serif;
  color: var(--cyan, #00f0ff);
  margin: 0;
  font-size: 2rem;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}
.subtitle {
  color: #ccc;
  margin-top: 0.5rem;
  letter-spacing: 1px;
}

.btn-war-room {
  background: transparent;
  border: 2px solid var(--accent-blue, #00f0ff);
  color: var(--accent-blue, #00f0ff);
  padding: 10px 20px;
  border-radius: 4px;
  font-family: 'Orbitron', sans-serif;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
}
.dashboard-container.war-room-mode .btn-war-room {
  border-color: #ff3366;
  color: #ff3366;
  background: rgba(255, 51, 102, 0.1);
  box-shadow: 0 0 15px rgba(255, 51, 102, 0.4);
}
.dashboard-container.war-room-mode .btn-war-room:hover {
  background: rgba(255, 51, 102, 0.3);
}

/* Dashboard Stats from WelcomeView */
.dashboard-stats {
  display: flex;
  gap: 20px;
  justify-content: flex-start;
  flex-wrap: wrap;
}
.dashboard-stats-margin {
  margin-bottom: 2rem;
}
@media (max-width: 600px) {
  .dashboard-stats {
    flex-direction: column;
  }
  .dash-stat-box {
    width: 100%;
  }
}

.dash-stat-box {
  background: rgba(10, 14, 23, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 20px;
  min-width: 150px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 4px;
  text-align: center;
  flex: 1;
  color: inherit;
  display: block;
}
.dash-stat-box:focus-visible {
  outline: 2px solid var(--cyan, #00f0ff);
  outline-offset: 2px;
}
.dashboard-container.war-room-mode .dash-stat-box {
  background: rgba(30, 5, 10, 0.8);
  border-color: rgba(255, 51, 102, 0.3);
}

.dash-stat-box:hover {
  transform: translateY(-2px);
  border-color: var(--cyan, #00f0ff);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
}
.dashboard-container.war-room-mode .dash-stat-box:hover {
  border-color: var(--pink, #ff3366);
  box-shadow: 0 0 15px rgba(255, 51, 102, 0.3);
}

.ds-value {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--cyan, #00f0ff);
  margin-bottom: 10px;
}
.text-green { color: var(--green, #00ff00); }
.text-pink { color: var(--pink, #ff3366); }
.text-cyan { color: var(--cyan, #00f0ff); }
.border-pink { border-color: var(--pink, #ff3366); }

.dashboard-container.war-room-mode .ds-value {
  color: var(--pink, #ff3366);
}

.ds-label {
  font-size: 0.8rem;
  color: #8892b0;
  letter-spacing: 1px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: rgba(10, 15, 30, 0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}
.dashboard-container.war-room-mode .metric-card {
  background: rgba(30, 5, 10, 0.8);
}

.metric-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 2px;
  background: rgba(255,255,255,0.2);
}

.metric-card.warning::after { background: #ff3366; box-shadow: 0 0 10px #ff3366; }
.metric-card.success::after { background: #00f0ff; box-shadow: 0 0 10px #00f0ff; }
.dashboard-container.war-room-mode .metric-card.success::after { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; }
.metric-card.info::after { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; }

.metric-card .icon {
  font-size: 2.5rem;
  opacity: 0.8;
}

.metric-card .data h3 {
  margin: 0;
  font-size: 2.2rem;
  font-family: 'Orbitron', sans-serif;
}
.metric-card .data span {
  color: #aaa;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.charts-area {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 900px) {
  .charts-area {
    grid-template-columns: 1fr;
  }
}

.chart-container {
  background: rgba(10, 15, 30, 0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.chart-container h3 {
  margin-top: 0;
  color: #888;
  font-size: 1rem;
  letter-spacing: 1px;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  padding-bottom: 0.5rem;
}

.chart-wrapper {
  height: 350px;
  position: relative;
}
.doughnut-wrapper {
  display: flex;
  justify-content: center;
}

@keyframes pulse-red {
  0% { text-shadow: 0 0 10px rgba(255, 51, 102, 0.4); }
  50% { text-shadow: 0 0 25px rgba(255, 51, 102, 0.8); }
  100% { text-shadow: 0 0 10px rgba(255, 51, 102, 0.4); }
}

.loading {
  font-size: 1.2rem;
  color: var(--cyan, #00f0ff);
  text-align: center;
  padding: 3rem;
  animation: pulse 1.5s infinite ease-in-out;
}

.error-state {
  color: var(--pink, #ff3366);
  background: rgba(255, 51, 102, 0.1);
  border: 1px solid var(--pink, #ff3366);
  padding: 2rem;
  text-align: center;
  border-radius: 8px;
  margin: 2rem 0;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
  font-style: italic;
  text-align: center;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}
</style>
