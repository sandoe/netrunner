<template>
  <div class="nosql-document-wrapper" style="padding: 12px; display: flex; flex-direction: column; overflow: hidden; height: calc(100% - 40px); min-height: 320px;">
    <div class="crt-terminal-container" style="flex: 1; min-height: 320px; background: radial-gradient(circle, #081208 0%, #020502 100%); border: 1px solid var(--green); border-radius: 4px; padding: 16px; font-family: var(--font-co); font-size: 11px; color: var(--green); position: relative; overflow-y: auto; box-shadow: inset 0 0 20px rgba(0,255,157,0.15); max-height: 480px;">
      <!-- scanlines overlay -->
      <div style="position: absolute; top:0; left:0; width:100%; height:100%; background: linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.15) 50%), linear-gradient(90deg, rgba(255,0,0,0.03), rgba(0,255,0,0.01), rgba(0,0,255,0.03)); background-size: 100% 3px, 6px 100%; pointer-events: none;"></div>
      
      <pre style="margin: 0; white-space: pre-wrap; font-family: var(--font-co); line-height: 1.5; color: #39ff14; text-shadow: 0 0 5px rgba(57, 255, 20, 0.5);">{{ rawNosqlOutput || '[TOMT SVAR ELLER INGEN DATA]' }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDatabaseQuery } from '@/composables/useDatabaseQuery'

const { rawNosqlOutput } = useDatabaseQuery()
</script>

<style scoped>
.nosql-document-wrapper {
  box-sizing: border-box;
}

.crt-terminal-container {
  position: relative;
  overflow: hidden;
}

.crt-terminal-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 120px;
  background: linear-gradient(to bottom, transparent, rgba(57, 255, 20, 0.03) 50%, rgba(57, 255, 20, 0.06) 95%, transparent);
  animation: crt-scanline 7s linear infinite;
  pointer-events: none;
  z-index: 5;
}

@keyframes crt-scanline {
  0% { transform: translateY(-120px); }
  100% { transform: translateY(480px); }
}
</style>
