<template>
  <div class="analytics-center-container">
    <header class="analytics-header">
      <h2><span class="glitch-text" data-text="ANALYTICS">ANALYTICS</span> CENTER</h2>
      <div class="header-actions">
        <button class="cyber-button" @click="fetchData">
          <span class="material-icons">refresh</span> SYNC
        </button>
      </div>
    </header>

    <div v-if="loading && !data" class="loading-state">
      <div class="spinner"></div>
      <div>AGGREGATING TELEMETRY...</div>
    </div>

    <div v-else-if="!data" class="loading-state" style="color: var(--red);">
      <span class="material-icons" style="font-size: 48px; margin-bottom: 16px;">error_outline</span>
      <div>NO ANALYTICS DATA AVAILABLE</div>
      <div style="font-size: 12px; margin-top: 8px; opacity: 0.7;">Check backend connection</div>
    </div>

    <div v-else class="analytics-grid">
      <!-- Threat Trends -->
      <div class="panel cyber-panel trends-panel">
        <div class="panel-header">
          <span class="material-icons">timeline</span>
          <h3>THREAT TRENDS (7 DAYS)</h3>
        </div>
        <div class="panel-content">
          <div class="trend-chart-container">
            <div class="y-axis">
              <span>25</span>
              <span>20</span>
              <span>15</span>
              <span>10</span>
              <span>5</span>
              <span>0</span>
            </div>
            <div class="chart-area">
              <div class="bar-group" v-for="(label, i) in data.trends.labels" :key="i">
                <div
                  class="bar warning"
                  :style="{ height: (data.trends.datasets[1].data[i] / 25) * 100 + '%' }"
                  :title="'Warning: ' + data.trends.datasets[1].data[i]"
                ></div>
                <div
                  class="bar critical"
                  :style="{ height: (data.trends.datasets[0].data[i] / 25) * 100 + '%' }"
                  :title="'Critical: ' + data.trends.datasets[0].data[i]"
                ></div>
                <div class="x-label">{{ label }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="side-panels">
        <!-- Protocol Distribution -->
        <div class="panel cyber-panel">
          <div class="panel-header">
            <span class="material-icons">pie_chart</span>
            <h3>PROTOCOL DISTRIBUTION</h3>
          </div>
          <div class="panel-content">
            <div class="protocol-list">
              <div v-for="proto in data.protocols" :key="proto.name" class="proto-row">
                <div class="proto-label">{{ proto.name }}</div>
                <div class="proto-bar-wrap">
                  <div class="proto-bar" :style="{ width: proto.value + '%' }"></div>
                </div>
                <div class="proto-value">{{ proto.value }}%</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Top Talkers -->
        <div class="panel cyber-panel">
          <div class="panel-header">
            <span class="material-icons">router</span>
            <h3>TOP TALKERS (BY VOLUME)</h3>
          </div>
          <div class="panel-content">
            <div class="talker-list">
              <div v-for="talker in data.top_talkers" :key="talker.ip" class="talker-row">
                <div class="talker-ip">{{ talker.ip }}</div>
                <div class="talker-bar-wrap">
                  <div class="talker-bar" :style="{ width: (talker.bytes / data.top_talkers[0].bytes) * 100 + '%' }"></div>
                </div>
                <div class="talker-vol">{{ formatBytes(talker.bytes) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'

const loading = ref(true)
const data = ref<any>(null)
let refreshInterval: any = null

const fetchData = async () => {
  if (!data.value) loading.value = true
  try {
    const res = await api.get('/analytics/summary')
    data.value = res.data
  } catch (err) {
    console.error('Failed to fetch analytics', err)
  } finally {
    loading.value = false
  }
}

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  const k = bytes / 1024
  if (k < 1024) return k.toFixed(1) + ' KB'
  const m = k / 1024
  return m.toFixed(1) + ' MB'
}

onMounted(() => {
  fetchData()
  refreshInterval = setInterval(fetchData, 5000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<style scoped>
.analytics-center-container {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  color: var(--text-color);
}

.analytics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--cyan);
  padding-bottom: 16px;
  margin-bottom: 24px;
}

.analytics-header h2 {
  font-family: var(--font-hd);
  color: var(--cyan);
  margin: 0;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--cyan);
  font-family: var(--font-co);
  letter-spacing: 2px;
}

.analytics-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  flex: 1;
}

@media (max-width: 1000px) {
  .analytics-grid {
    grid-template-columns: 1fr;
  }
}

.cyber-panel {
  background: rgba(10, 15, 30, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
}

.panel-header {
  background: rgba(0, 229, 255, 0.1);
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-header h3 {
  margin: 0;
  font-family: var(--font-hd);
  font-size: 14px;
  color: var(--cyan);
  letter-spacing: 1px;
}

.panel-header .material-icons {
  color: var(--cyan);
  font-size: 20px;
}

.panel-content {
  padding: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.side-panels {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Trend Chart */
.trend-chart-container {
  display: flex;
  flex: 1;
  gap: 16px;
  min-height: 250px;
}

.y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #666;
  font-size: 12px;
  font-family: var(--font-co);
  padding-bottom: 30px; /* Space for x-labels */
}

.chart-area {
  flex: 1;
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  padding-bottom: 0;
  margin-bottom: 30px;
}

.bar-group {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
  width: 100%;
  height: 100%;
  position: relative;
}

.bar {
  width: 20px;
  background: #333;
  border-radius: 2px 2px 0 0;
  transition: height 0.5s ease;
}

.bar.critical {
  background: rgba(255, 0, 85, 0.8);
  box-shadow: 0 0 10px rgba(255, 0, 85, 0.4);
}

.bar.warning {
  background: rgba(255, 170, 0, 0.8);
  box-shadow: 0 0 10px rgba(255, 170, 0, 0.4);
}

.x-label {
  position: absolute;
  bottom: -25px;
  font-size: 11px;
  color: #888;
  font-family: var(--font-co);
}

/* Protocol List */
.protocol-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.proto-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.proto-label {
  width: 60px;
  font-family: var(--font-co);
  font-size: 12px;
  color: #ccc;
}

.proto-bar-wrap {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.proto-bar {
  height: 100%;
  background: var(--cyan);
  box-shadow: 0 0 10px var(--cyan);
  border-radius: 4px;
}

.proto-value {
  width: 40px;
  text-align: right;
  font-family: var(--font-co);
  font-size: 12px;
  color: var(--cyan);
}

/* Top Talkers */
.talker-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.talker-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.talker-ip {
  width: 100px;
  font-family: var(--font-co);
  font-size: 12px;
  color: var(--green);
}

.talker-bar-wrap {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.talker-bar {
  height: 100%;
  background: var(--green);
  box-shadow: 0 0 10px var(--green);
  border-radius: 4px;
}

.talker-vol {
  width: 60px;
  text-align: right;
  font-family: var(--font-co);
  font-size: 12px;
  color: var(--green);
}

.cyber-button {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 6px 16px;
  font-family: var(--font-hd);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
}

.cyber-button:hover {
  background: rgba(0, 229, 255, 0.2);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
}
</style>
