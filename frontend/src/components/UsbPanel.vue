<script setup>
import { ref, onMounted, onUnmounted, useTemplateRef, nextTick, markRaw } from 'vue';
import McuIdePanel from './McuIdePanel.vue';
import SerialMonitorPanel from './SerialMonitorPanel.vue';

const props = defineProps({ nodeId: { type: String, required: true } });






const monitorRef = useTemplateRef('monitorRef');



const usbDevices = ref([]);
const loading = ref(true);
const error = ref('');
const sendError = ref('');
const dockError = ref('');
const sendSuccess = ref('');
const writingPort = ref(null);
const payload = ref('');
const selectedPort = ref(null);
const showMonitor = ref(true);
const wasConnected = ref(false);
let pollInterval = null;

const handleIdeDisconnect = () => {
  if (monitorRef.value && monitorRef.value.connected) {
    wasConnected.value = true;
    monitorRef.value.disconnect();
  } else {
    wasConnected.value = false;
  }
};

const handleIdeReconnect = (options = {}) => {
  const force = options.force || options === true;
  const reset = options.reset || false;
  
  if ((wasConnected.value || force) && monitorRef.value) {
    if (!monitorRef.value.connected) {
      monitorRef.value.connect(reset);
    } else {
      if (reset) monitorRef.value.triggerBackendReset();
    }
    wasConnected.value = true;
  }
};

const fetchUsb = async () => {
  try {
    const token = localStorage.getItem('nr_token');
    if (!token) return;
    const res = await fetch(`/api/v1/usb/${props.nodeId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    usbDevices.value = data.devices || [];
    error.value = '';
  } catch (err) {
    error.value = 'Failed to scan USB ports: ' + err.message;
  } finally {
    loading.value = false;
  }
};

const sendPayload = async (port) => {
  if (!payload.value) return;
  writingPort.value = port;
  sendError.value = '';
  sendSuccess.value = '';
  try {
    const token = localStorage.getItem('nr_token');
    const res = await fetch(`/api/v1/usb/${props.nodeId}/write`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        port: port,
        data: payload.value
      })
    });
    
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }
    
    sendSuccess.value = `Payload dispatched to ${port} successfully.`;
    payload.value = '';
  } catch (err) {
    sendError.value = 'Write failed: ' + err.message;
  } finally {
    writingPort.value = null;
  }
};

const nukeUsb = async (port) => {
  sendError.value = '';
  sendSuccess.value = '';
  try {
    const token = localStorage.getItem('nr_token');
    const res = await fetch(`/api/v1/usb/${props.nodeId}/nuke`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        port: port
      })
    });
    
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    
    sendSuccess.value = `☢️ NUKED ${port}! Port is now free and permissions granted.`;
  } catch (err) {
    sendError.value = 'Nuke failed: ' + err.message;
  }
};

onMounted(() => {
  fetchUsb();
  pollInterval = setInterval(fetchUsb, 3000); // Check for new USBs every 3s
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<template>
  <div class="usb-panel scroll-y">
    <div class="panel-header">
      <div class="panel-title">
        <span class="icon">🔌</span>
        REMOTE USB / SERIAL RECONNAISSANCE
      </div>
      <div class="panel-actions">
        <span class="status-badge" :class="usbDevices.length > 0 ? 'online' : 'offline'">
          {{ usbDevices.length }} DEVICES DETECTED
        </span>
      </div>
    </div>

    <div v-if="loading && !selectedPort" class="scan-state">Scanning remote hardware...</div>
    <div v-else-if="error && !selectedPort" class="scan-error">{{ error }}</div>
    <div v-else-if="usbDevices.length === 0 && !selectedPort" class="scan-empty">
      No USB Serial interfaces found on this node.
      <br>Ensure the Netrunner agent is running on the target.
    </div>

    <div v-else-if="!selectedPort" class="usb-list">
      <div v-for="dev in usbDevices" :key="dev.device" class="usb-card">
        <div class="usb-info">
          <div class="usb-port">{{ dev.device }}</div>
          <div class="usb-name">{{ dev.name || 'Unknown Serial Device' }}</div>
        </div>
        
        <div class="usb-attack-bay">
          <input 
            type="text" 
            v-model="payload" 
            class="payload-input" 
            placeholder="Enter payload/command (e.g., ATTACK 1)..."
            @keyup.enter="sendPayload(dev.device)"
          />
          <button 
            class="btn-attack" 
            :disabled="writingPort === dev.device || !payload"
            @click="sendPayload(dev.device)"
          >
            <span v-if="writingPort === dev.device">SENDING...</span>
            <span v-else>TRANSMIT</span>
          </button>
          <button class="btn-nuke" @click="nukeUsb(dev.device)" title="Force kill processes holding the port and fix permissions">☢️ NUKE</button>
          <button class="btn-mcu" @click="selectedPort = dev.device">MCU LAB</button>
        </div>
      </div>
    </div>
    
    <div v-else class="mcu-lab-view">
      <div class="lab-header">
        <button class="btn-back" @click="selectedPort = null">← BACK TO USB LIST</button>
        <div class="lab-port">Active Port: {{ selectedPort }}</div>
      </div>
      <div class="lab-split" style="width:100%; position: relative; height: calc(100vh - 100px); overflow-y: auto;">
        <McuIdePanel :nodeId="props.nodeId" :port="selectedPort" />
        
      </div>
    </div>
    
    <div v-if="sendSuccess" class="success-msg mt-3">{{ sendSuccess }}</div>
    <div v-if="sendError" class="error-msg mt-3">{{ sendError }}</div>
    <div v-if="dockError" class="error-msg mt-3" style="color:red; white-space:pre-wrap">{{ dockError }}</div>
  </div>
</template>

<style scoped>
.usb-panel {
  padding: 15px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
  flex-shrink: 0;
}

.mcu-lab-view {
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.lab-header {
  display: flex;
  gap: 15px;
  align-items: center;
}
.btn-back {
  background: transparent;
  color: #fff;
  border: 1px solid #555;
  padding: 4px 10px;
  cursor: pointer;
  border-radius: 4px;
}
.btn-back:hover { background: #333; }

.lab-split {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 700px;
}

.panel-title {
  font-family: var(--font-hd);
  color: var(--cyan);
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.scan-state, .scan-empty {
  text-align: center;
  padding: 40px;
  color: var(--textbr);
  font-family: var(--font-co);
  background: rgba(0,0,0,0.2);
  border: 1px dashed var(--border);
}

.scan-error {
  padding: 15px;
  background: rgba(255, 0, 85, 0.1);
  color: var(--pink);
  border: 1px solid var(--pink);
  font-family: var(--font-co);
}

.usb-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.usb-card {
  background: rgba(0, 229, 255, 0.02);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.usb-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.usb-port {
  font-family: var(--font-hd);
  color: var(--cyan);
  font-size: 18px;
  font-weight: bold;
}

.usb-name {
  color: var(--textbr);
  font-size: 12px;
  font-family: var(--font-co);
}

.usb-attack-bay {
  display: flex;
  gap: 10px;
}

.payload-input {
  flex: 1;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 8px 12px;
  font-family: monospace;
  font-size: 13px;
}

.payload-input:focus {
  border-color: var(--cyan);
  outline: none;
  box-shadow: 0 0 5px rgba(0, 229, 255, 0.3);
}

.btn-attack {
  background: rgba(255, 0, 85, 0.1);
  border: 1px solid var(--pink);
  color: var(--pink);
  padding: 8px 20px;
  font-family: var(--font-hd);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-mcu {
  background: rgba(0, 229, 255, 0.1);
  color: var(--cyan);
  border: 1px solid var(--cyan);
  font-family: var(--font-hd);
  font-weight: bold;
  padding: 8px 15px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
  text-shadow: 0 0 5px var(--cyan);
  animation: pulse-glow 2s infinite alternate;
}

.btn-mcu:hover {
  background: var(--cyan);
  color: #000;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.8);
  text-shadow: none;
  transform: scale(1.02);
}

@keyframes pulse-glow {
  from { box-shadow: 0 0 5px rgba(0, 229, 255, 0.2); }
  to { box-shadow: 0 0 12px rgba(0, 229, 255, 0.6); }
}

.btn-attack:hover:not(:disabled) {
  background: var(--pink);
  color: #000;
}

.btn-nuke {
  background: rgba(255, 165, 0, 0.1);
  border: 1px solid orange;
  color: orange;
  padding: 8px 15px;
  font-family: var(--font-hd);
  cursor: pointer;
  transition: all 0.2s;
  font-weight: bold;
}

.btn-nuke:hover {
  background: orange;
  color: #000;
  box-shadow: 0 0 10px rgba(255, 165, 0, 0.6);
}

.btn-attack:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mt-3 { margin-top: 15px; }

.success-msg {
  color: var(--green);
  font-family: var(--font-co);
  font-size: 13px;
}

.error-msg {
  color: var(--pink);
  font-family: var(--font-co);
  font-size: 13px;
}
</style>
