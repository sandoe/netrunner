<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="cyber-modal-card sniffer-modal" role="dialog" aria-modal="true" aria-labelledby="sniffer-title">
      <div class="cyber-modal-header">
        <div class="modal-title" id="sniffer-title">📡 NETWORK SNIFFER: LIVE STREAM</div>
        <button class="btn-close-modal" @click="$emit('close')">×</button>
      </div>
      <div class="cyber-modal-body">
        <div class="packet-table-wrapper">
          <table class="packet-table">
            <thead>
              <tr>
                <th>TIMESTAMP</th>
                <th>SOURCE</th>
                <th>DNS QUERY</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(pkt, idx) in packets" :key="idx" class="pkt-row">
                <td class="col-time">{{ pkt.time_str || '-' }}</td>
                <td class="col-src">{{ pkt.source || 'UNKNOWN' }}</td>
                <td class="col-qry">{{ pkt.query || '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="packets.length === 0" class="empty-state">NO PACKETS INTERCEPTED YET...</div>
        </div>
      </div>
      <div class="cyber-modal-footer">
        <button class="btn-action" @click="$emit('close')">DISCONNECT</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  dataRaw: string
}>()

const emit = defineEmits(['close'])

onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))
function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

const packets = ref<any[]>([])

function parseData(raw: string) {
  const lines = raw.split('\n').filter(l => l.trim())
  const pkts = []
  for (const line of lines) {
    try {
      pkts.push(JSON.parse(line))
    } catch (e) {}
  }
  // Reverse to show newest first
  packets.value = pkts.reverse()
}

watch(() => props.dataRaw, (newVal) => {
  parseData(newVal)
}, { immediate: true })

</script>

<style scoped>
.sniffer-modal {
  width: 800px;
  max-width: 95vw;
}

.packet-table-wrapper {
  max-height: 50vh;
  overflow-y: auto;
  background: rgba(10, 15, 20, 0.9);
  border: 1px solid var(--border);
}

.packet-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-co);
  font-size: 11px;
}

.packet-table th {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--cyan);
  position: sticky;
  top: 0;
  background: rgba(10, 15, 20, 0.95);
  letter-spacing: 1px;
}

.packet-table td {
  padding: 6px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: var(--textwh);
}

.pkt-row:hover td {
  background: rgba(0, 229, 255, 0.1);
}

.col-time { color: var(--text) !important; }
.col-src { color: var(--textbr) !important; }
.col-qry { color: var(--yellow) !important; font-weight: bold; }

.empty-state {
  padding: 20px;
  text-align: center;
  color: var(--text);
  font-family: var(--font-hd);
  letter-spacing: 2px;
}
button:focus-visible, .btn-action:focus-visible, .btn-close:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
</style>
