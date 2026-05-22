<template>
  <div class="dpi-dashboard">
    <div class="dpi-header">
      <span class="dpi-title">DEEP PACKET INSPECTION</span>
      <span class="dpi-total">{{ data.total_packets }} PACKETS ANALYZED</span>
    </div>
    
    <div class="dpi-grid">
      <!-- Protocols -->
      <div class="dpi-card">
        <div class="card-title">PROTOCOLS</div>
        <div class="bars">
          <div v-for="p in sortedProtocols" :key="p.name" class="bar-row">
            <div class="bar-label">{{ p.name }}</div>
            <div class="bar-track">
              <div class="bar-fill cyan" :style="{ width: percent(p.count) + '%' }"></div>
            </div>
            <div class="bar-value">{{ p.count }}</div>
          </div>
          <div v-if="!data.protocols?.length" class="empty-msg">NO PROTOCOLS</div>
        </div>
      </div>
      
      <!-- Top Sources -->
      <div class="dpi-card">
        <div class="card-title">TOP SOURCES</div>
        <div class="bars">
          <div v-for="s in data.top_sources" :key="s.ip" class="bar-row">
            <div class="bar-label ip" :title="s.ip">{{ s.ip }}</div>
            <div class="bar-track">
              <div class="bar-fill pink" :style="{ width: percent(s.count) + '%' }"></div>
            </div>
            <div class="bar-value">{{ s.count }}</div>
          </div>
          <div v-if="!data.top_sources?.length" class="empty-msg">NO DATA</div>
        </div>
      </div>
      
      <!-- Top Destinations -->
      <div class="dpi-card">
        <div class="card-title">TOP DESTINATIONS</div>
        <div class="bars">
          <div v-for="d in data.top_destinations" :key="d.ip" class="bar-row">
            <div class="bar-label ip" :title="d.ip">{{ d.ip }}</div>
            <div class="bar-track">
              <div class="bar-fill green" :style="{ width: percent(d.count) + '%' }"></div>
            </div>
            <div class="bar-value">{{ d.count }}</div>
          </div>
          <div v-if="!data.top_destinations?.length" class="empty-msg">NO DATA</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ data: any }>()

const sortedProtocols = computed(() => {
  if (!props.data?.protocols) return []
  return [...props.data.protocols].sort((a, b) => b.count - a.count)
})

function percent(count: number) {
  if (!props.data?.total_packets) return 0
  return Math.max(2, (count / props.data.total_packets) * 100)
}
</script>

<style scoped>
.dpi-dashboard {
  margin-top: 16px;
  background: rgba(8, 26, 21, 0.5); /* subtle green tint */
  border: 1px solid var(--green);
  border-radius: var(--r);
  padding: 16px;
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
.dpi-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
  border-bottom: 1px dashed rgba(0, 255, 157, 0.3);
  padding-bottom: 8px;
}
.dpi-title {
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--green);
  letter-spacing: 2px;
  text-shadow: 0 0 8px rgba(0, 255, 157, 0.4);
}
.dpi-total {
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--textwh);
}
.dpi-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1.2fr;
  gap: 16px;
}
.dpi-card {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 4px;
  border: 1px solid rgba(0, 255, 157, 0.1);
}
.card-title {
  font-family: var(--font-hd);
  font-size: 9px;
  color: var(--text);
  letter-spacing: 1px;
  margin-bottom: 12px;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bar-label {
  width: 45px;
  font-family: var(--font-co);
  font-size: 9px;
  color: var(--textwh);
}
.bar-label.ip {
  width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-track {
  flex: 1;
  height: 6px;
  background: var(--bg);
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.bar-fill.cyan { background: var(--cyan); box-shadow: 0 0 5px var(--cyan); }
.bar-fill.pink { background: var(--pink); box-shadow: 0 0 5px var(--pink); }
.bar-fill.green { background: var(--green); box-shadow: 0 0 5px var(--green); }
.bar-value {
  width: 30px;
  text-align: right;
  font-family: var(--font-co);
  font-size: 9px;
  color: var(--text);
}
.empty-msg {
  font-family: var(--font-co);
  font-size: 9px;
  color: var(--text);
  text-align: center;
  padding: 10px;
}
</style>
