<template>
  <div class="system-panel">
    <div class="tabs-nav">
      <button 
        v-if="isGns3" 
        class="tab-btn" 
        :class="{ active: activeTab === 'gns3' }" 
        @click="activeTab = 'gns3'"
      >
        🌐 GNS3
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'vitals' }" 
        @click="activeTab = 'vitals'"
      >
        ⚡ VITALS & DIAG
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'services' }" 
        @click="activeTab = 'services'"
      >
        🧩 SERVICES
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'logs' }" 
        @click="activeTab = 'logs'"
      >
        📜 LOGS
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'config' }" 
        @click="activeTab = 'config'"
      >
        🛠️ CONFIG
      </button>
    </div>

    <div class="tab-content">
      <div v-show="activeTab === 'gns3'" class="tab-pane" v-if="isGns3">
        <Gns3Panel :node-id="nodeId" />
      </div>

      <div v-show="activeTab === 'vitals'" class="tab-pane dual-pane">
        <div class="vitals-half">
          <SystemVitals :node-id="nodeId" />
        </div>
        <div class="diag-half">
          <DiagPanel :node-id="nodeId" />
        </div>
      </div>

      <div v-show="activeTab === 'services'" class="tab-pane">
        <SystemServices :node-id="nodeId" />
      </div>

      <div v-show="activeTab === 'logs'" class="tab-pane">
        <SystemLogs :node-id="nodeId" />
      </div>

      <div v-show="activeTab === 'config'" class="tab-pane">
        <ConfigPanel :node-id="nodeId" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import DiagPanel from './DiagPanel.vue'
import ConfigPanel from './ConfigPanel.vue'
import SystemVitals from './SystemVitals.vue'
import SystemServices from './SystemServices.vue'
import SystemLogs from './SystemLogs.vue'
import Gns3Panel from './Gns3Panel.vue'

const props = defineProps<{ nodeId: string }>()
const store = useNodesStore()
const isGns3 = computed(() => store.nodes[props.nodeId]?.device_type === 'gns3')

const activeTab = ref(isGns3.value ? 'gns3' : 'vitals')
</script>

<style scoped>
.system-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: var(--bg);
  overflow: hidden;
}

.tabs-nav {
  display: flex;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  padding: 0 8px;
  flex-shrink: 0;
  overflow-x: auto;
}

.tab-btn {
  background: none;
  border: none;
  color: var(--text);
  padding: 12px 16px;
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-btn:hover {
  color: var(--textwh);
  background: rgba(255, 255, 255, 0.03);
}

.tab-btn.active {
  color: var(--cyan);
  border-bottom-color: var(--cyan);
}

.tab-content {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-pane {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.dual-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.vitals-half {
  flex: 0 0 auto;
}

.diag-half {
  flex: 1 1 auto;
  min-height: 300px;
}
</style>
