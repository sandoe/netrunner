<template>
  <div class="infrastructure-view">
    <div class="panel-header">
      <h2>🔌 INFRASTRUCTURE & SDN</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel">
        <h3>VLANs & Networks</h3>
        <p>No networks configured yet.</p>
        <button class="btn-cyan">Create Network</button>
      </div>
      <div class="glass-panel" style="margin-top: 15px;">
        <h3>Firmware & Agents</h3>
        <p>All nodes up to date.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

// Dummy logic for now
</script>

<style scoped>
.infrastructure-view {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  color: var(--textbr);
}
.panel-header {
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  padding-bottom: 10px;
}
.glass-panel {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(0, 229, 255, 0.2);
  padding: 20px;
  border-radius: 4px;
}
.btn-cyan {
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 8px 16px;
  cursor: pointer;
  margin-top: 10px;
}
.btn-cyan:hover {
  background: var(--cyan);
  color: #000;
}
</style>
