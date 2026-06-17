<template>
  <div class="clients-view">
    <div class="panel-header">
      <h2>💻 CLIENT MANAGEMENT</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel">
        <table class="data-table">
          <thead>
            <tr>
              <th>HOSTNAME</th>
              <th>IP ADDRESS</th>
              <th>MAC ADDRESS</th>
              <th>EXPERIENCE</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colspan="5" style="text-align: center; color: var(--text-muted);">No clients discovered yet.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.clients-view { padding: 20px; height: 100%; color: var(--textbr); }
.panel-header { margin-bottom: 20px; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 10px; }
.glass-panel { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 229, 255, 0.2); padding: 20px; border-radius: 4px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(0, 229, 255, 0.1); }
</style>
