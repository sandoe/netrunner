<template>
  <div class="traffic-analytics-view">
    <div class="panel-header">
      <h2>📈 LAYER-7 TRAFFIC ANALYTICS</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel text-center">
        <p style="color: var(--text-muted);">Awaiting deep packet inspection data from nodes...</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.traffic-analytics-view { padding: 20px; height: 100%; color: var(--textbr); }
.panel-header { margin-bottom: 20px; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 10px; }
.glass-panel { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 229, 255, 0.2); padding: 20px; border-radius: 4px; }
.text-center { text-align: center; }
</style>
