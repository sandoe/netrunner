<template>
  <div class="wifi-sidebar">
    <h2>WIFI & CSI ANALYSIS</h2>

    <div class="node-status">
      <h3>ACTIVE NODES</h3>
      <div class="node-item" v-for="node in activeNodes" :key="node.id" :class="{'selected-node': selectedNodeId === node.id}" @click="$emit('update:selectedNodeId', node.id)" tabindex="0" @keydown.enter="$emit('update:selectedNodeId', node.id)" @keydown.space.prevent="$emit('update:selectedNodeId', node.id)" role="button">
        <div class="node-dot" :style="{ backgroundColor: isNodeActive(node.id) ? 'var(--cyan)' : 'var(--pink)' }"></div>
        <div class="node-info">
          <div class="node-name">{{ node.ip }}</div>
          <div class="node-controls">
            <button @click.stop="$emit('startNode', node.id)" class="ctrl-btn start-btn" aria-label="Deploy / Start" title="Deploy / Start">▶</button>
            <button @click.stop="$emit('stopNode', node.id)" class="ctrl-btn stop-btn" aria-label="Kill Process" title="Kill Process">■</button>
            <button @click.stop="$emit('deleteNode', node.id)" class="ctrl-btn delete-btn" aria-label="Remove Config" title="Remove Config">✕</button>
          </div>
        </div>
      </div>
      <div v-if="activeNodes.length === 0" style="color:#555; font-size:11px; padding: 5px;">No beacons configured.</div>
    </div>

    <NodeStatsPanel
      :isRealData="isRealData"
      :isSimulation="isSimulation"
      :csiSource="csiSource"
      :dataStatus="dataStatus"
      :selectedTelemetry="selectedTelemetry"
      :motionDetected="motionDetected"
      :typingActive="typingActive"
    />
  </div>
</template>

<script setup lang="ts">
import NodeStatsPanel from './NodeStatsPanel.vue';

defineProps<{
  activeNodes: any[];
  selectedNodeId: string;
  isNodeActive: (id: string) => boolean;
  isRealData: boolean;
  isSimulation: boolean;
  csiSource: string;
  dataStatus: string;
  selectedTelemetry: any;
  motionDetected: boolean;
  typingActive: boolean;
}>();

defineEmits<{
  (e: 'update:selectedNodeId', id: string): void;
  (e: 'startNode', id: string): void;
  (e: 'stopNode', id: string): void;
  (e: 'deleteNode', id: string): void;
}>();
</script>
