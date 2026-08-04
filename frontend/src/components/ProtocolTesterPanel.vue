<template>
  <div class="protocol-tester-panel">
    <div class="panel-header">
      <div class="glitch-title">PROTOCOL TOOLS</div>
    </div>

    <div style="display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 10px;">
      <button :class="activeTab === 'dpi' ? 'hack-btn primary' : 'hack-btn'" @click="activeTab = 'dpi'">[ DPI TESTER ]</button>
      <button :class="activeTab === 'sandbox' ? 'hack-btn primary' : 'hack-btn'" @click="activeTab = 'sandbox'">[ OT SANDBOX (DOCKER) ]</button>
    </div>

    <!-- DPI TESTER TAB -->
    <div v-if="activeTab === 'dpi'" class="panel-content" style="display: flex; gap: 20px; flex-wrap: wrap;">
      <div class="glass-panel" style="flex: 1; min-width: 300px;">
        <h3>Configuration</h3>
        <div style="margin-bottom: 10px;">
          <label style="display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 12px;">TARGET IP</label>
          <input type="text" v-model="form.target_ip" class="hack-input" placeholder="127.0.0.1" style="width: 100%" />
        </div>
        <div style="margin-bottom: 10px;">
          <label style="display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 12px;">TARGET PORT</label>
          <input type="number" v-model="form.target_port" class="hack-input" placeholder="1883" style="width: 100%" />
        </div>
        <div style="margin-bottom: 10px;">
          <label style="display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 12px;">PROTOCOL TYPE</label>
          <select v-model="form.protocol" class="hack-select" style="width: 100%; appearance: auto;" @change="populatePayload">
            <option value="mqtt">MQTT (Connect)</option>
            <option value="amqp">AMQP</option>
            <option value="coap">CoAP</option>
            <option value="modbus_tcp">Modbus TCP</option>
            <option value="modbus_rtu">Modbus RTU</option>
            <option value="quic">QUIC</option>
            <option value="udp">Raw UDP</option>
            <option value="tcp">Raw TCP</option>
          </select>
        </div>
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 12px;">PAYLOAD (HEX)</label>
          <textarea v-model="form.payload_hex" rows="3" class="hack-input" style="width: 100%; font-family: monospace; resize: vertical;"></textarea>
        </div>
        <button @click="sendTraffic" class="hack-btn primary" style="width: 100%">
          [ TRANSMIT PAYLOAD & ANALYZE ]
        </button>
      </div>

      <div class="glass-panel" style="flex: 1; min-width: 300px;">
        <h3>DPI Engine Results</h3>
        <div v-if="loading" style="color: var(--pink); font-family: monospace; margin-top: 10px;">
          <span class="pulse-alert" style="display: inline-block; width: 8px; height: 8px; background: var(--pink); border-radius: 50%; margin-right: 5px; animation: pulse 1s infinite;"></span>
          ANALYZING TRAFFIC PATTERNS...
        </div>
        <div v-else-if="result" style="margin-top: 10px; font-family: monospace; font-size: 13px;">
          <div style="margin-bottom: 5px;"><span style="color: var(--cyan);">STATUS:</span> {{ result.status }}</div>
          <div v-if="result.message" style="margin-bottom: 5px;"><span style="color: var(--cyan);">MESSAGE:</span> {{ result.message }}</div>
          <div v-if="result.dpi_analysis" style="margin-bottom: 5px;"><span style="color: var(--cyan);">DETECTED PROTOCOL:</span> <span style="color: var(--pink); font-weight: bold;">{{ result.dpi_analysis }}</span></div>
          <div v-if="result.sent_bytes !== undefined" style="margin-bottom: 5px;"><span style="color: var(--cyan);">SENT BYTES:</span> {{ result.sent_bytes }}</div>
        </div>
        <div v-else style="color: var(--text-muted); margin-top: 10px; font-family: monospace; font-size: 13px;">
          No traffic sent yet. Select a protocol and execute transmission.
        </div>
      </div>
    </div>

    <!-- OT SANDBOX TAB -->
    <div v-if="activeTab === 'sandbox'" class="panel-content" style="display: flex; gap: 20px; flex-wrap: wrap;">
      <div class="glass-panel" style="flex: 1; min-width: 300px;">
        <h3>Container Control</h3>
        <div style="margin-bottom: 10px;">
          <label style="display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 12px;">SERVICE</label>
          <select v-model="sandboxForm.service" class="hack-select" style="width: 100%; appearance: auto;">
            <option value="mqtt-broker">MQTT Broker (Server)</option>
            <option value="mqtt-pub">MQTT Publisher (Client)</option>
            <option value="mqtt-sub">MQTT Subscriber (Client)</option>

            <option value="modbus-server">Modbus TCP Server</option>
            <option value="modbus-client">Modbus Client (Poller)</option>

            <option value="opcua-server">OPC UA Server</option>
            <option value="opcua-client">OPC UA Client</option>

            <option value="coap-server">CoAP Server</option>
            <option value="coap-client">CoAP Client</option>

            <option value="amqp-broker">AMQP Broker (RabbitMQ)</option>
            <option value="amqp-pub">AMQP Publisher (Client)</option>
            <option value="amqp-sub">AMQP Subscriber (Client)</option>
          </select>
        </div>

        <div style="margin-bottom: 15px;" v-if="sandboxForm.service.includes('client') || sandboxForm.service.includes('pub') || sandboxForm.service.includes('sub')">
          <label style="display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 12px;">TARGET IP (NODE IP)</label>
          <input type="text" v-model="sandboxForm.target_ip" class="hack-input" placeholder="192.168.1.10" style="width: 100%" />
        </div>

        <div style="margin-bottom: 15px;" v-if="sandboxForm.service.includes('opcua')">
          <label style="display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 12px;">OPC TAGS (Comma separated, e.g. temp=45,pressure)</label>
          <input type="text" v-model="sandboxForm.tags" class="hack-input" placeholder="tag1=10,tag2" style="width: 100%" />
        </div>

        <div style="display: flex; gap: 10px;">
          <button @click="startContainer" class="hack-btn primary" style="flex: 1;" :disabled="sandboxLoading">
            [ SPIN UP ]
          </button>
          <button @click="stopContainer" class="hack-btn" style="flex: 1; color: var(--pink); border-color: var(--pink);" :disabled="sandboxLoading">
            [ TEAR DOWN ]
          </button>
        </div>

        <div v-if="sandboxLoading" style="margin-top: 10px; color: var(--cyan); font-size: 12px;">Processing...</div>
      </div>

      <div class="glass-panel" style="flex: 2; min-width: 400px; display: flex; flex-direction: column;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <h3>Logs: {{ sandboxForm.service }}</h3>
          <button @click="fetchLogs" class="hack-btn" style="padding: 2px 8px; font-size: 11px;">[ REFRESH LOGS ]</button>
        </div>
        <div class="terminal-output" style="flex-grow: 1; min-height: 250px; background: rgba(0,0,0,0.5); padding: 10px; font-family: monospace; font-size: 12px; color: #aaa; white-space: pre-wrap; overflow-y: auto; border: 1px solid var(--border-color);">
          {{ sandboxLogs || 'No logs available. Start the container or click Refresh.' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue';

const activeTab = ref('sandbox');

// DPI Tester State
const form = reactive({
  target_ip: '127.0.0.1',
  target_port: 1883,
  protocol: 'mqtt',
  payload_hex: '101000044d5154540402003c000474657374'
});
const loading = ref(false);
const result = ref<any>(null);

// Sandbox State
const sandboxForm = reactive({
  service: 'modbus-server',
  target_ip: '',
  tags: ''
});
const sandboxLoading = ref(false);
const sandboxLogs = ref('');
let logInterval: any = null;

const populatePayload = () => {
  const payloads: Record<string, string> = {
    'mqtt': '101000044d5154540402003c000474657374',
    'amqp': '414d515000010000',
    'coap': '40010000',
    'modbus_tcp': '00010000000601030000000a',
    'modbus_rtu': '01030000000ac5cd',
    'quic': 'c000000001',
    'udp': 'deadbeef',
    'tcp': 'deadbeef'
  };

  if (form.protocol === 'mqtt') form.target_port = 1883;
  else if (form.protocol === 'amqp') form.target_port = 5672;
  else if (form.protocol === 'coap') form.target_port = 5683;
  else if (form.protocol === 'modbus_tcp') form.target_port = 502;
  else if (form.protocol === 'quic') form.target_port = 443;

  form.payload_hex = payloads[form.protocol] || '';
};

const sendTraffic = async () => {
  loading.value = true;
  result.value = null;
  try {
    const token = localStorage.getItem('token');
    const response = await fetch('/api/protocol-tester/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(form)
    });
    result.value = await response.json();
  } catch (error: any) {
    result.value = { status: 'error', message: error.message };
  } finally {
    loading.value = false;
  }
};

const startContainer = async () => {
  sandboxLoading.value = true;
  try {
    const token = localStorage.getItem('token');
    await fetch('/api/protocol-containers/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ service: sandboxForm.service, target_ip: sandboxForm.target_ip, tags: sandboxForm.tags })
    });
    fetchLogs();

    // Auto-refresh logs every 2 seconds when started
    if (!logInterval) {
      logInterval = setInterval(fetchLogs, 2000);
    }
  } catch (err) {
    console.error(err);
  } finally {
    sandboxLoading.value = false;
  }
};

const stopContainer = async () => {
  sandboxLoading.value = true;
  try {
    const token = localStorage.getItem('token');
    await fetch('/api/protocol-containers/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ service: sandboxForm.service })
    });
    if (logInterval) {
      clearInterval(logInterval);
      logInterval = null;
    }
    fetchLogs();
  } catch (err) {
    console.error(err);
  } finally {
    sandboxLoading.value = false;
  }
};

const fetchLogs = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await fetch(`/api/protocol-containers/logs/${sandboxForm.service}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    if (data.status === 'success') {
      sandboxLogs.value = data.logs;
    }
  } catch (err) {
    console.error(err);
  }
};

onMounted(() => {
  fetchLogs();
});

onUnmounted(() => {
  if (logInterval) clearInterval(logInterval);
});
</script>

<style scoped>
.btn-outline {
  background: transparent;
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 8px 15px;
  cursor: pointer;
  font-family: monospace;
}
.btn-outline:hover {
  background: rgba(0, 255, 255, 0.1);
}
</style>
