<template>
  <div class="stats-panel">
    <h3>RADIO TELEMETRY</h3>
    <div class="stat-row">
      <span>Data Source:</span>
      <span :class="isRealData ? 'highlight' : 'highlight-alert'">
        {{ isSimulation ? 'SIMULATION' : (csiSource === 'nexmon' ? 'REAL CSI' : 'SYNTHETIC') }}
      </span>
    </div>
    <div class="stat-row" v-if="!isSimulation && dataStatus">
      <span>Link Status:</span>
      <span class="highlight" style="font-size:0.75rem;">{{ dataStatus }}</span>
    </div>
    <div class="stat-row" v-if="selectedTelemetry">
      <span>WiFi Chip:</span>
      <span class="highlight">{{ selectedTelemetry.capabilities?.wifi_chip || 'unknown' }}</span>
    </div>
    <div class="stat-row" v-if="selectedTelemetry">
      <span>Nexmon CSI:</span>
      <span :class="selectedTelemetry.capabilities?.nexmon ? 'highlight' : 'highlight-alert'">
        {{ selectedTelemetry.capabilities?.nexmon ? 'SUPPORTED' : 'NO' }}
      </span>
    </div>
    <div class="stat-row">
      <span>Status:</span>
      <span class="highlight">MONITOR MODE</span>
    </div>
    <div class="stat-row">
      <span>Band:</span>
      <span class="highlight">5 GHz (Ch 36)</span>
    </div>
    <div class="stat-row">
      <span>Bandwidth:</span>
      <span class="highlight">20 MHz</span>
    </div>
    <div class="stat-row">
      <span>Subcarriers:</span>
      <span class="highlight">64 (OFDM)</span>
    </div>
    <div class="stat-row">
      <span>Motion Detect:</span>
      <span :class="motionDetected ? 'highlight-alert' : 'highlight'" aria-live="polite">
        {{ motionDetected ? 'ALERT' : 'CLEAR' }}
      </span>
    </div>
    <div class="stat-row">
      <span>Keylogger:</span>
      <span :class="typingActive ? 'highlight-alert' : 'highlight'" aria-live="polite">
        {{ typingActive ? 'INTERCEPTING' : 'IDLE' }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  isRealData: boolean;
  isSimulation: boolean;
  csiSource: string;
  dataStatus: string;
  selectedTelemetry: any;
  motionDetected: boolean;
  typingActive: boolean;
}>();
</script>
