<template>
  <div class="threat-timeline glass-panel">
    <div class="header">
      <h3>Historical Threat Analysis</h3>
      <button @click="fetchHistory" class="btn-refresh">
        <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> Refresh
      </button>
    </div>

    <div class="chart-container" v-if="!loading && chartData.labels.length">
      <Bar :data="chartData" :options="chartOptions" />
    </div>
    <div v-else-if="loading" class="loading-state">
      Loading historical data...
    </div>
    <div v-else class="empty-state">
      No historical threats found.
    </div>

    <div class="timeline-list">
      <h4>Recent Events</h4>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Type</th>
            <th>Source IP</th>
            <th>Target</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in events.slice(0, 50)" :key="event.id" :class="event.severity">
            <td>{{ formatTime(event.timestamp) }}</td>
            <td>{{ event.type }}</td>
            <td class="mono">{{ event.source_ip }}</td>
            <td class="mono">{{ event.target_ip }}</td>
            <td>
              <span class="badge" :class="event.severity">{{ event.severity }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
} from 'chart.js';
import { Bar } from 'vue-chartjs';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const events = ref<any[]>([]);
const loading = ref(false);

const fetchHistory = async () => {
  loading.value = true;
  try {
    const token = localStorage.getItem('nr_token');
    const res = await fetch('/api/threats/history?limit=1000', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      events.value = await res.json();
    }
  } catch (err) {
    console.error('Failed to fetch threat history:', err);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchHistory();
});

const formatTime = (ts: number) => {
  return new Date(ts * 1000).toLocaleString();
};

const chartData = computed(() => {
  // Group by hour
  const counts: Record<string, number> = {};
  events.value.forEach(ev => {
    const d = new Date(ev.timestamp * 1000);
    // Format as "MM/DD HH:00"
    const hourKey = `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:00`;
    counts[hourKey] = (counts[hourKey] || 0) + 1;
  });

  // Sort chronologically
  const labels = Object.keys(counts).sort();
  const data = labels.map(l => counts[l]);

  return {
    labels,
    datasets: [
      {
        label: 'Threats per Hour',
        backgroundColor: '#f87171',
        data
      }
    ]
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: '#e5e7eb' }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: { color: '#9ca3af' },
      grid: { color: '#374151' }
    },
    x: {
      ticks: { color: '#9ca3af' },
      grid: { display: false }
    }
  }
};
</script>

<style scoped>
.threat-timeline {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h3 {
  margin: 0;
  color: #60a5fa;
  font-family: 'Orbitron', sans-serif;
}

.btn-refresh {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid #3b82f6;
  color: #60a5fa;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover {
  background: rgba(59, 130, 246, 0.4);
}

.chart-container {
  height: 250px;
  width: 100%;
}

.loading-state, .empty-state {
  height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-style: italic;
}

.timeline-list {
  flex-grow: 1;
  overflow-y: auto;
}

.timeline-list h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #e5e7eb;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th {
  text-align: left;
  padding: 0.75rem;
  background: rgba(17, 24, 39, 0.8);
  color: #9ca3af;
  font-weight: 500;
  border-bottom: 1px solid #374151;
  position: sticky;
  top: 0;
}

td {
  padding: 0.75rem;
  border-bottom: 1px solid #1f2937;
  color: #d1d5db;
}

tr:hover td {
  background: rgba(255, 255, 255, 0.05);
}

.mono {
  font-family: 'Fira Code', monospace;
  font-size: 0.85rem;
}

.badge {
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.critical { background: rgba(220, 38, 38, 0.2); color: #ef4444; border: 1px solid #dc2626; }
.badge.high { background: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid #f97316; }
.badge.medium { background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid #eab308; }
.badge.low { background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid #22c55e; }
</style>
