<template>
  <div class="hotspot-manager-view">
    <div class="panel-header">
      <h2>🎟️ GUEST HOTSPOT MANAGER</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel">
        <h3>Generate Vouchers</h3>
        <button class="btn-cyan">Create New Voucher</button>
      </div>
      <div class="glass-panel" style="margin-top: 15px;">
        <h3>Active Guest Sessions</h3>
        <p style="color: var(--text-muted);">No active guests.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hotspot-manager-view { padding: 20px; height: 100%; color: var(--textbr); }
.panel-header { margin-bottom: 20px; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 10px; }
.glass-panel { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 229, 255, 0.2); padding: 20px; border-radius: 4px; }
.btn-cyan { background: rgba(0, 229, 255, 0.1); border: 1px solid var(--cyan); color: var(--cyan); padding: 8px 16px; cursor: pointer; margin-top: 10px; }
.btn-cyan:hover { background: var(--cyan); color: #000; }
</style>
