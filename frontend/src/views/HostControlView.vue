<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const metrics = ref(null);
const error = ref('');
let pollInterval = null;

const maxDataPoints = 60;
const history = ref({
  labels: [],
  cpu: [],
  mem: [],
  netSent: [],
  netRecv: []
});

let lastNet = { sent: 0, recv: 0, time: 0 };
const currentNetSpeed = ref({ sent: 0, recv: 0 });

const fetchMetrics = async () => {
  try {
    const token = localStorage.getItem('nr_token');
    const res = await fetch('/api/v1/system/host', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error('Failed to fetch host metrics');
    metrics.value = await res.json();
    error.value = '';

    // Update history
    const now = new Date().toLocaleTimeString();
    
    // Net speed calculation
    if (metrics.value.network) {
      const nowMs = Date.now();
      if (lastNet.time > 0) {
        const dt = (nowMs - lastNet.time) / 1000;
        currentNetSpeed.value.sent = (metrics.value.network.bytes_sent - lastNet.sent) / 1024 / dt;
        currentNetSpeed.value.recv = (metrics.value.network.bytes_recv - lastNet.recv) / 1024 / dt;
      }
      lastNet.sent = metrics.value.network.bytes_sent;
      lastNet.recv = metrics.value.network.bytes_recv;
      lastNet.time = nowMs;
    }

    history.value.labels.push(now);
    history.value.cpu.push(metrics.value.cpu.percent);
    history.value.mem.push(metrics.value.memory.used_gb);
    history.value.netSent.push(currentNetSpeed.value.sent || 0);
    history.value.netRecv.push(currentNetSpeed.value.recv || 0);

    if (history.value.labels.length > maxDataPoints) {
      history.value.labels.shift();
      history.value.cpu.shift();
      history.value.mem.shift();
      history.value.netSent.shift();
      history.value.netRecv.shift();
    }
  } catch (err) {
    error.value = err.message;
  }
};

const formatUptime = (seconds) => {
  if (!seconds) return '0s';
  const d = Math.floor(seconds / (3600*24));
  const h = Math.floor(seconds % (3600*24) / 3600);
  const m = Math.floor(seconds % 3600 / 60);
  const s = Math.floor(seconds % 60);
  return `${d}d ${h}h ${m}m ${s}s`;
};

// Chart Data Computed
const cpuChartData = computed(() => ({
  labels: [...history.value.labels],
  datasets: [{
    label: 'CPU Usage (%)',
    data: [...history.value.cpu],
    borderColor: '#00e5ff',
    backgroundColor: 'rgba(0, 229, 255, 0.15)',
    tension: 0.4,
    fill: true,
    pointRadius: 0
  }]
}));

const memChartData = computed(() => ({
  labels: [...history.value.labels],
  datasets: [{
    label: 'Memory (GB)',
    data: [...history.value.mem],
    borderColor: '#00ff88',
    backgroundColor: 'rgba(0, 255, 136, 0.15)',
    tension: 0.4,
    fill: true,
    pointRadius: 0
  }]
}));

const netChartData = computed(() => ({
  labels: [...history.value.labels],
  datasets: [
    {
      label: 'TX (KB/s)',
      data: [...history.value.netSent],
      borderColor: '#ff0055',
      backgroundColor: 'transparent',
      tension: 0.4,
      pointRadius: 0
    },
    {
      label: 'RX (KB/s)',
      data: [...history.value.netRecv],
      borderColor: '#ffaa00',
      backgroundColor: 'transparent',
      tension: 0.4,
      pointRadius: 0
    }
  ]
}));

const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { display: false },
    y: { 
      grid: { color: 'rgba(255,255,255,0.05)' },
      ticks: { color: '#a0aab5', font: { family: 'monospace', size: 10 } },
      beginAtZero: true
    }
  }
};

const cpuChartOptions = { ...baseChartOptions, scales: { ...baseChartOptions.scales, y: { ...baseChartOptions.scales.y, max: 100 } } };
const memChartOptions = computed(() => ({
  ...baseChartOptions,
  scales: { ...baseChartOptions.scales, y: { ...baseChartOptions.scales.y, max: metrics.value?.memory?.total_gb || 100 } }
}));

onMounted(() => {
  fetchMetrics();
  pollInterval = setInterval(fetchMetrics, 1000);
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<template>
  <div class="host-control-container">
    <div class="page-header cyber-panel">
      <h2>HOST CONTROL ROOM</h2>
      <p>Local hypervisor monitoring & USB device recon</p>
    </div>

    <div v-if="error" class="scan-error">{{ error }}</div>

    <div class="metrics-grid" v-if="metrics">
      
      <!-- CPU Panel -->
      <div class="cyber-panel metric-card">
        <div class="card-header">
          <h3 class="panel-title">CPU USAGE</h3>
          <span class="header-value">{{ metrics.cpu.percent.toFixed(1) }}%</span>
        </div>
        <div class="metric-sub">{{ metrics.cpu.physical_cores }} Cores / {{ metrics.cpu.cores }} Threads <span v-if="metrics.cpu.loadavg">| Load: {{ metrics.cpu.loadavg.join(', ') }}</span></div>
        <div class="chart-container mt-2">
          <Line :data="cpuChartData" :options="cpuChartOptions" />
        </div>
      </div>

      <!-- RAM Panel -->
      <div class="cyber-panel metric-card">
        <div class="card-header">
          <h3 class="panel-title">MEMORY ALLOCATION</h3>
          <span class="header-value" style="color: var(--green);">{{ metrics.memory.used_gb }} GB</span>
        </div>
        <div class="metric-sub">Total: {{ metrics.memory.total_gb }} GB <span v-if="metrics.memory.swap_used_gb !== undefined">| Swap: {{ metrics.memory.swap_used_gb }} GB</span></div>
        <div class="chart-container mt-2">
          <Line :data="memChartData" :options="memChartOptions" />
        </div>
      </div>

      <!-- Network Panel -->
      <div class="cyber-panel metric-card">
        <div class="card-header">
          <h3 class="panel-title">NETWORK I/O</h3>
          <span class="header-value" style="color: var(--pink);">{{ currentNetSpeed.sent.toFixed(0) }} ↑ {{ currentNetSpeed.recv.toFixed(0) }} ↓</span>
        </div>
        <div class="metric-sub">KB/s (TX / RX)</div>
        <div class="chart-container mt-2">
          <Line :data="netChartData" :options="baseChartOptions" />
        </div>
      </div>

      <!-- Disk & Uptime Row -->
      <div class="cyber-panel metric-card flex-row" v-if="metrics.disk">
        <div class="half-panel">
          <h3 class="panel-title">MAIN STORAGE</h3>
          <div class="metric-body">
            <div class="metric-value">{{ metrics.disk.used_gb }} / {{ metrics.disk.total_gb }} GB</div>
            <div class="metric-sub">{{ metrics.disk.free_gb }} GB Free</div>
            <div class="progress-bar mt-2">
              <div class="progress-fill" 
                   :style="{ width: metrics.disk.percent + '%' }"
                   :class="{ warning: metrics.disk.percent > 80, critical: metrics.disk.percent > 95 }">
              </div>
            </div>
          </div>
        </div>
        <div class="half-panel uptime-panel">
          <h3 class="panel-title">SYSTEM UPTIME</h3>
          <div class="metric-value uptime-val">{{ formatUptime(metrics.uptime) }}</div>
        </div>
      </div>

    </div>

    <!-- USB Devices Panel -->
    <div class="cyber-panel usb-panel">
      <div class="card-header">
        <h3 class="panel-title">USB DEVICE RECONNAISSANCE</h3>
        <span class="status-badge online" v-if="metrics">{{ metrics.usb_devices?.length || 0 }} DETECTED</span>
      </div>
      <div class="card-body">
        <p class="usb-desc">Auto-detecting connected serial peripherals (Arduino, ESP32, debugging cables).</p>
        
        <div v-if="!metrics?.usb_devices?.length" class="no-usb">
          No USB serial devices detected.
        </div>
        
        <div class="usb-grid" v-else>
          <div class="usb-card" v-for="(usb, idx) in metrics.usb_devices" :key="idx">
            <div class="usb-icon">🔌</div>
            <div class="usb-info">
              <div class="usb-port">{{ usb.device }}</div>
              <div class="usb-name">{{ usb.description || usb.name }}</div>
              <div class="usb-hwid" v-if="usb.hwid">{{ usb.hwid }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.host-control-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.metric-card {
  display: flex;
  flex-direction: column;
}

.metric-body {
  margin-top: 15px;
}

.centered-metric {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.metric-value {
  font-family: var(--font-hd);
  font-size: 24px;
  color: var(--cyan);
  font-weight: bold;
}

.uptime-val {
  font-size: 28px;
  color: var(--green);
}

.metric-sub {
  font-family: var(--font-co);
  font-size: 13px;
  color: var(--textbr);
  margin-top: 5px;
}

.header-value {
  font-family: var(--font-hd);
  font-size: 20px;
  color: var(--cyan);
  font-weight: bold;
}

.chart-container {
  position: relative;
  height: 120px;
  width: 100%;
}

.flex-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  grid-column: 1 / -1;
}

.half-panel {
  flex: 1;
  padding: 0 15px;
}

.half-panel:first-child {
  border-right: 1px dashed var(--border);
}

.uptime-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.mt-2 {
  margin-top: 15px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: var(--cyan);
  transition: width 0.3s ease, background-color 0.3s ease;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

.progress-fill.warning {
  background: #f39c12;
  box-shadow: 0 0 10px rgba(243, 156, 18, 0.5);
}

.progress-fill.critical {
  background: var(--pink);
  box-shadow: 0 0 10px rgba(255, 0, 85, 0.5);
}

.usb-panel {
  margin-top: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.usb-desc {
  color: var(--textbr);
  font-family: var(--font-co);
  font-size: 14px;
  margin-bottom: 20px;
}

.no-usb {
  padding: 20px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--border);
  color: var(--textbr);
  border-radius: 4px;
  font-family: var(--font-co);
}

.usb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
}

.usb-card {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border);
  padding: 15px;
  border-radius: 4px;
  transition: all 0.2s;
}

.usb-card:hover {
  border-color: var(--cyan);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.1);
  transform: translateY(-2px);
}

.usb-icon {
  font-size: 32px;
  margin-right: 15px;
  filter: drop-shadow(0 0 5px rgba(0, 229, 255, 0.5));
}

.usb-info {
  display: flex;
  flex-direction: column;
}

.usb-port {
  color: var(--cyan);
  font-weight: bold;
  font-family: var(--font-hd);
  font-size: 16px;
}

.usb-name {
  color: var(--text);
  font-size: 13px;
  font-family: var(--font-co);
  margin-top: 4px;
}

.usb-hwid {
  color: var(--textbr);
  font-size: 11px;
  font-family: monospace;
  margin-top: 4px;
  word-break: break-all;
}

.scan-error {
  padding: 12px;
  background: rgba(255, 0, 85, 0.1);
  border: 1px solid var(--pink);
  color: var(--pink);
  border-radius: 4px;
  font-family: var(--font-co);
  font-size: 13px;
}
</style>
