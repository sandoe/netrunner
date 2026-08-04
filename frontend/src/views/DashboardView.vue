<template>
  <div class="dashboard-container">
    <div class="crt-overlay"></div>

    <div class="dashboard-content">
      <div class="header">
        <div>
          <h2>GLOBAL DASHBOARD</h2>
          <p class="subtitle">System Analytics & Threat Intel</p>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="dashboard-stats dashboard-stats-margin">
        <button class="dash-stat-box glass-panel" @click="$router.push('/topology')">
          <div class="ds-value">{{ store.nodeList.length }}</div>
          <div class="ds-label">NODES ONLINE</div>
        </button>
        <div class="dash-stat-box glass-panel">
          <div class="ds-value hud-primary-text">{{ store.connectedCount }}</div>
          <div class="ds-label">ACTIVE CONNECTIONS</div>
        </div>
        <button class="dash-stat-box glass-panel" @click="$router.push('/alerts')">
          <div class="ds-value" style="color: #ff3366">!</div>
          <div class="ds-label">ALERT INBOX</div>
        </button>
      </div>

      <div v-if="loading" class="loading">SYNCING TELEMETRY...</div>
      <div v-else-if="errorMsg" class="error-state">DATA STREAM COMPROMISED</div>
      <div v-else-if="metrics" class="hud-main">

        <!-- Metrics Grid -->
        <div class="metrics-grid">
          <div class="metric-card warning glass-panel">
            <div class="data">
              <h3>{{ metrics.critical_alerts }}</h3>
              <span>Critical Events</span>
            </div>
            <div class="spark-mini">
              <SparklineGraph :data="liveData.critical" color="#ff3366" />
            </div>
          </div>

          <div class="metric-card glass-panel">
            <div class="data">
              <h3>{{ metrics.mitigation_rate_percent }}%</h3>
              <span>Mitigation Rate</span>
            </div>
            <div class="spark-mini">
              <SparklineGraph :data="liveData.mitigation" color="var(--hud-primary)" />
            </div>
          </div>

          <div class="metric-card info glass-panel">
            <div class="data">
              <h3>{{ metrics.total_alerts }}</h3>
              <span>Total Volume</span>
            </div>
            <div class="spark-mini">
              <SparklineGraph :data="liveData.volume" color="#ffaa00" />
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDashboardSummaryAnalyticsSummaryGet } from '@/api_client'
import { useNodesStore } from '@/stores/nodes'
import { useRouter } from 'vue-router'
import SparklineGraph from '@/components/SparklineGraph.vue'

const store = useNodesStore()
const router = useRouter()

const loading = ref(true)
const errorMsg = ref<string | null>(null)
const metrics = ref<any>(null)

const fetchData = async () => {
  try {
    errorMsg.value = null
    const res = await getDashboardSummaryAnalyticsSummaryGet()
    metrics.value = res.metrics
  } catch (err) {
    console.error("Error loading dashboard", err)
    errorMsg.value = "Failed to load dashboard data."
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
/* CSS Variables driven by DEFCON State */
.dashboard-container {
  --hud-primary: #00f0ff;
  --hud-bg: rgba(10, 15, 30, 0.85);
  --hud-text: #fff;
  --hud-danger: #ff3366;

  position: relative;
  min-height: 100vh;
  background: #050505;
  color: var(--hud-text);
  overflow: hidden;
  transition: all 0.5s ease;
  font-family: 'Orbitron', 'Inter', sans-serif;
}

.crt-overlay {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  pointer-events: none;
  z-index: 1;
  background: repeating-linear-gradient(
    rgba(0, 0, 0, 0.15) 0px,
    rgba(0, 0, 0, 0.15) 1px,
    transparent 1px,
    transparent 2px
  );
}

.dashboard-content {
  position: relative;
  z-index: 2;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 2px solid var(--hud-primary);
  padding-bottom: 1rem;
  margin-bottom: 2rem;
  transition: border-color 0.5s;
}

.header h2 {
  margin: 0;
  font-size: 2.5rem;
  text-shadow: 0 0 15px var(--hud-primary);
}

.subtitle {
  color: var(--hud-primary);
  margin-top: 0.5rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  font-size: 0.9rem;
}

/* Glitch CSS */
.glitch-text {
  position: relative;
  display: inline-block;
  color: var(--hud-primary);
}
.dashboard-container[data-defcon="1"] .glitch-text::before,
.dashboard-container[data-defcon="1"] .glitch-text::after,
.dashboard-container[data-defcon="2"] .glitch-text::before,
.dashboard-container[data-defcon="2"] .glitch-text::after {
  content: attr(data-text);
  position: absolute;
  top: 0;
  left: 0;
  opacity: 0.8;
}
.glitch-text::before {
  color: #0ff;
  z-index: -1;
  animation: glitch-anim-1 2s infinite linear alternate-reverse;
}
.glitch-text::after {
  color: #f0f;
  z-index: -2;
  animation: glitch-anim-2 3s infinite linear alternate-reverse;
}

@keyframes glitch-anim-1 {
  0% { clip-path: inset(20% 0 80% 0); transform: translate(-2px, 1px); }
  20% { clip-path: inset(60% 0 10% 0); transform: translate(2px, -1px); }
  40% { clip-path: inset(40% 0 50% 0); transform: translate(-2px, 2px); }
  60% { clip-path: inset(80% 0 5% 0); transform: translate(2px, -2px); }
  80% { clip-path: inset(10% 0 70% 0); transform: translate(-1px, 1px); }
  100% { clip-path: inset(30% 0 50% 0); transform: translate(1px, -1px); }
}

@keyframes glitch-anim-2 {
  0% { clip-path: inset(10% 0 60% 0); transform: translate(2px, -1px); }
  20% { clip-path: inset(30% 0 20% 0); transform: translate(-2px, 1px); }
  40% { clip-path: inset(70% 0 10% 0); transform: translate(2px, -2px); }
  60% { clip-path: inset(20% 0 50% 0); transform: translate(-2px, 2px); }
  80% { clip-path: inset(50% 0 30% 0); transform: translate(1px, -1px); }
  100% { clip-path: inset(5% 0 80% 0); transform: translate(-1px, 1px); }
}

.dashboard-stats {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}
.dashboard-stats-margin {
  margin-bottom: 2rem;
}

.dash-stat-box {
  background: var(--hud-bg);
  border: 1px solid rgba(255,255,255,0.1);
  border-bottom: 3px solid var(--hud-primary);
  padding: 20px;
  flex: 1;
  min-width: 150px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}
div.dash-stat-box {
  cursor: default;
}
.dash-stat-box:not(div):hover {
  transform: translateY(-2px);
  border-color: var(--hud-primary);
  box-shadow: 0 5px 20px rgba(0,0,0,0.5), 0 0 15px inset rgba(255,255,255,0.05);
}

.ds-value {
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 10px;
}
.hud-primary-text {
  color: var(--hud-primary);
  text-shadow: 0 0 10px var(--hud-primary);
}
.ds-label {
  font-size: 0.8rem;
  color: #8892b0;
  letter-spacing: 2px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: var(--hud-bg);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  overflow: hidden;
}
.metric-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 4px; height: 100%;
  background: var(--hud-primary);
  box-shadow: 0 0 10px var(--hud-primary);
}
.metric-card.warning::before { background: var(--hud-danger); box-shadow: 0 0 10px var(--hud-danger); }
.metric-card.info::before { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; }

.metric-card .data h3 {
  margin: 0 0 5px 0;
  font-size: 2rem;
}
.metric-card .data span {
  color: #aaa;
  font-size: 0.8rem;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.spark-mini {
  width: 100px;
  height: 40px;
}

.streams-area {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-top: 20px;
}
.stream-container, .engines-panel {
  background: var(--hud-bg);
  border: 1px solid var(--hud-border);
  padding: 15px;
  border-radius: 4px;
}
.engines-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  margin-top: 15px;
}
.engine-card {
  background: rgba(0,0,0,0.4);
  border: 1px solid var(--hud-primary);
  padding: 15px;
  border-radius: 4px;
  text-align: center;
}
.engine-card h4 {
  color: var(--hud-primary);
  margin: 0 0 5px 0;
  font-family: 'Share Tech Mono', monospace;
  font-size: 1.1em;
}
.engine-card p {
  color: #a0a0a0;
  font-size: 0.85em;
  margin-bottom: 15px;
}
.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 0.8em;
  font-weight: bold;
}
.status-badge.active {
  background: rgba(0, 255, 204, 0.2);
  color: var(--hud-primary);
  border: 1px solid var(--hud-primary);
  box-shadow: 0 0 5px var(--hud-primary);
}

@media (max-width: 900px) {
  .streams-area {
    grid-template-columns: 1fr;
  }
}

.stream-container {
  background: var(--hud-bg);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 1.5rem;
  border-top: 1px solid var(--hud-primary);
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.stream-header h3 {
  margin: 0;
  font-size: 1rem;
  letter-spacing: 2px;
  color: #ccc;
}
.live-indicator {
  font-size: 0.7rem;
  color: var(--hud-primary);
  border: 1px solid var(--hud-primary);
  padding: 2px 6px;
  border-radius: 2px;
  animation: blink 1s infinite step-end;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.stream-graph {
  height: 150px;
}

.loading, .error-state {
  text-align: center;
  padding: 4rem;
  font-size: 1.5rem;
  letter-spacing: 5px;
  color: var(--hud-primary);
  animation: pulse 1.5s infinite;
}
.error-state {
  color: var(--hud-danger);
}
</style>
