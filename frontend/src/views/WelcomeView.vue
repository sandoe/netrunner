<template>
  <div class="welcome">
    <div class="welcome-inner">
      <div class="welcome-logo">NETRUNNER<span style="color: var(--cyan); font-size: 0.4em; vertical-align: top; margin-left: 10px;">OS</span></div>
      <div class="welcome-sub">COMMAND CENTER ONLINE</div>
      
      <div class="dashboard-stats">
        <div class="dash-stat-box" @click="$router.push('/node')">
          <div class="ds-value">{{ store.nodeList.length }}</div>
          <div class="ds-label">REGISTERED NODES</div>
        </div>
        <div class="dash-stat-box" @click="$router.push('/pulse')">
          <div class="ds-value" style="color: var(--green);">{{ store.connectedCount }}</div>
          <div class="ds-label">ACTIVE CONNECTIONS</div>
        </div>
        <div class="dash-stat-box" @click="$router.push('/warroom')">
          <div class="ds-value" :style="{ color: systemState.chaos ? 'var(--pink)' : 'var(--cyan)' }">{{ systemState.chaos ? 'ACTIVE' : 'STANDBY' }}</div>
          <div class="ds-label">WAR ROOM STATUS</div>
        </div>
        <div class="dash-stat-box" @click="$router.push('/alerts')" style="border-color: var(--pink)">
          <div class="ds-value" style="color: var(--pink);">!</div>
          <div class="ds-label">ALERT INBOX</div>
        </div>
      </div>
      
      <div style="margin-top: 40px; display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
        <button class="btn btn-primary stagger-item" style="padding: 15px 30px; font-size: 14px;" @click="$router.push('/topology')">🕸️ OPEN TOPOLOGY</button>
        <button class="btn btn-recon stagger-item" style="padding: 15px 30px; font-size: 14px; animation-delay: 0.1s;" @click="$router.push('/pulse')">⚡ NETWORK PULSE</button>
        <button class="btn btn-danger stagger-item" style="padding: 15px 30px; font-size: 14px; animation-delay: 0.2s;" @click="$router.push('/alerts')">🚨 TRIAGE ALERTS</button>
        <button class="btn stagger-item" style="padding: 15px 30px; font-size: 14px; animation-delay: 0.3s; border-color: #fff; color: #fff;" @click="$router.push('/reports')">📄 GENERATE REPORT</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useNodesStore } from '@/stores/nodes'
const store = useNodesStore()
const props = defineProps({
  systemState: {
    type: Object,
    required: true
  }
})
</script>
