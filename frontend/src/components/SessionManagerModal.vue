<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal cyber-glass session-modal" role="dialog">
      <div class="modal-header">
        <h3>ACTIVE TERMINAL SESSIONS</h3>
        <button class="btn-close" @click="$emit('close')">X</button>
      </div>

      <div class="session-list">
        <div v-if="activeSessions.length === 0" class="no-sessions">
          NO ACTIVE SESSIONS DETECTED
        </div>
        <div v-for="session in activeSessions" :key="session.id" class="session-row">
          <div class="session-info">
            <span class="session-name">{{ session.name }}</span>
            <span class="session-ip">{{ session.host }}:{{ session.port }} ({{ session.transport }})</span>
          </div>
          <button class="btn-disconnect" @click="disconnect(session.id)">DISCONNECT</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'

const emit = defineEmits(['close'])
const store = useNodesStore()

const activeSessions = computed(() => {
  return Object.keys(store.connections)
    .filter(nid => store.connections[nid].connected)
    .map(nid => store.nodes[nid])
    .filter(Boolean)
})

async function disconnect(nid: string) {
  try {
    store.manuallyDisconnected.add(nid)
    await api.disconnectNode(nid)
    await store.refreshConnections()
  } catch (e) {
    console.error('Failed to disconnect', e)
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(5, 8, 15, 0.85);
  backdrop-filter: blur(12px);
  display: flex; align-items: center; justify-content: center;
  z-index: 3000;
}
.session-modal {
  background: rgba(10, 14, 25, 0.9); border: 1px solid var(--cyan); border-radius: 12px;
  box-shadow: 0 0 40px rgba(0, 229, 255, 0.15), inset 0 0 20px rgba(0, 229, 255, 0.05);
  padding: 24px; width: 500px; max-width: 95vw; max-height: 80vh; display: flex; flex-direction: column;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 12px; margin-bottom: 16px;
}
h3 { margin: 0; color: var(--cyan); font-family: var(--font-hd); letter-spacing: 2px; }
.btn-close { background: transparent; color: var(--textbr); border: none; font-size: 16px; cursor: pointer; }
.btn-close:hover { color: var(--pink); }

.session-list {
  display: flex; flex-direction: column; gap: 8px; overflow-y: auto;
}
.no-sessions {
  text-align: center; color: var(--textbr); font-family: var(--font-co); padding: 20px; font-style: italic;
}
.session-row {
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 12px 16px; border-radius: 6px;
}
.session-row:hover { border-color: rgba(0, 229, 255, 0.3); background: rgba(0, 229, 255, 0.05); }
.session-info { display: flex; flex-direction: column; gap: 4px; }
.session-name { color: var(--textwh); font-weight: bold; font-family: var(--font-hd); }
.session-ip { color: var(--textbr); font-size: 12px; font-family: var(--font-co); }

.btn-disconnect {
  background: rgba(255, 45, 110, 0.15); color: var(--pink); border: 1px solid var(--pink);
  padding: 6px 12px; border-radius: 4px; cursor: pointer; font-family: var(--font-hd); font-size: 12px; transition: all 0.2s;
}
.btn-disconnect:hover {
  background: var(--pink); color: #000; box-shadow: 0 0 15px rgba(255, 45, 110, 0.4);
}
</style>
