<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { serialEvents } from './mcuState.ts';

const props = defineProps({
  nodeId: { type: String, required: false },
  port: { type: String, required: false },
  params: { type: Object, required: false }
});

const activeNodeId = computed(() => props.nodeId || props.params?.nodeId);
const activePort = computed(() => props.port || props.params?.port);


const baudrate = ref(115200);
const termRef = ref(null);
const connected = ref(false);
const error = ref('');
let ws = null;
let term = null;
let fitAddon = null;

const connect = async (doReset = false) => {
  if (ws) ws.close();
  if (term) term.clear();
  
  const token = localStorage.getItem('nr_token');
  
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${wsProtocol}//${window.location.host}/api/v1/usb/monitor/${activeNodeId.value}?port=${encodeURIComponent(activePort.value)}&baud=${baudrate.value}&token=${token}&reset=${doReset}`;
  
  ws = new WebSocket(url);
  
  ws.onopen = () => {
    connected.value = true;
    term.write(`\x1b[36m[SYSTEM] Connected to ${activePort.value} at ${baudrate.value} baud\x1b[0m\r\n\r\n`);
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'output') {
        term.write(msg.data);
      } else if (msg.type === 'error') {
        term.write(`\r\n\x1b[31m[ERROR] ${msg.data}\x1b[0m\r\n`);
      } else if (msg.type === 'status') {
        connected.value = msg.connected;
      }
    } catch (e) {}
  };
  ws.onclose = () => { connected.value = false; term.write('\r\n\x1b[33m[SYSTEM] Disconnected\x1b[0m\r\n'); };
  ws.onerror = () => { error.value = 'WebSocket connection error'; };
};

const triggerBackendReset = async () => {
  if (ws && connected.value) {
    // Send Ctrl+C exactly once like a human would
    ws.send(JSON.stringify({ type: "input", data: String.fromCharCode(3) }));
    setTimeout(() => {
      // Send Ctrl+D exactly once
      ws.send(JSON.stringify({ type: "input", data: String.fromCharCode(4) }));
    }, 200);
  } else {
    try {
      const token = localStorage.getItem('nr_token');
      await fetch(`/api/v1/mcu/${activeNodeId.value}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ port: activePort.value })
      });
    } catch(e) {}
  }
};

const disconnect = () => { if (ws) ws.close(); };


const handleDisconnectEvent = () => disconnect();
const handleReconnectEvent = (e) => connect(e.options?.reset);

onMounted(() => {
  serialEvents.addEventListener('disconnect', handleDisconnectEvent);
  serialEvents.addEventListener('reconnect', handleReconnectEvent);
  term = new Terminal({
    theme: { background: '#050505', foreground: '#0f0', cursor: '#0f0' },
    fontFamily: 'var(--font-co), monospace',
    fontSize: 14,
    cursorBlink: true
  });
  fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.open(termRef.value);
  fitAddon.fit();
  
  const handleResize = () => {
    if (fitAddon) fitAddon.fit();
  };
  window.addEventListener('resize', handleResize);
  term._handleResize = handleResize;

  term.onData(data => {
    if (ws && connected.value) {
      ws.send(JSON.stringify({ type: "input", data: data }));
    }
  });

  term.onKey(e => {
    if (!ws || !connected.value) return
    const ctrlCodes = { c: 3, x: 24, d: 4, z: 26, u: 21, k: 11 }
    if (e.domEvent.ctrlKey && ctrlCodes[e.key]) {
      ws.send(JSON.stringify({ type: "input", data: String.fromCharCode(ctrlCodes[e.key]) }))
      e.domEvent.preventDefault()
    }
  })

  // connect(); // Removed to prevent auto-connect
});
onUnmounted(() => {
  serialEvents.removeEventListener('disconnect', handleDisconnectEvent);
  serialEvents.removeEventListener('reconnect', handleReconnectEvent);
  disconnect();
  if (term && term._handleResize) {
    window.removeEventListener('resize', term._handleResize);
  }
});

defineExpose({
  connect,
  disconnect,
  triggerBackendReset,
  connected
});
</script>

<template>
  <div class="serial-monitor">
    <div class="monitor-header">
      <div class="monitor-title">
        <span class="icon">📟</span> SERIAL: {{ port }}
      </div>
      <div class="monitor-controls">
        <select v-model="baudrate" class="baud-select">
          <option :value="9600">9600</option>
          <option :value="19200">19200</option>
          <option :value="38400">38400</option>
          <option :value="57600">57600</option>
          <option :value="115200">115200</option>
          <option :value="460800">460800</option>
          <option :value="921600">921600</option>
        </select>
        <button class="btn-connect" @click="connected ? disconnect() : connect()">
          {{ connected ? 'DISCONNECT' : 'CONNECT' }}
        </button>
      </div>
    </div>
    
    <div v-if="error" class="monitor-error" style="background: red; color: white; padding: 5px; font-family: var(--font-hd); font-size: 12px; text-align: center;">
      {{ error }}
    </div>
    
    <div class="terminal-view" ref="termRef"></div>
  </div>
</template>

<style scoped>
.serial-monitor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
}
.monitor-header {
  display: flex;
  justify-content: space-between;
  padding: 10px 15px;
  border-bottom: 1px solid var(--border);
  background: rgba(0, 229, 255, 0.05);
  overflow-x: auto;
}
.monitor-title { font-family: var(--font-hd); color: var(--cyan); display: flex; align-items: center; gap: 8px; flex-shrink: 0;}
.monitor-controls { display: flex; gap: 10px; flex-shrink: 0;}
.baud-select {
  background: var(--bg);
  color: var(--cyan);
  border: 1px solid var(--border);
  padding: 2px 5px;
  font-family: var(--font-co);
}
.btn-connect {
  background: transparent;
  color: var(--cyan);
  border: 1px solid var(--cyan);
  cursor: pointer;
  font-family: var(--font-hd);
  padding: 2px 10px;
}
.btn-connect:hover { background: var(--cyan); color: #000; }
.terminal-view {
  flex: 1;
  padding: 10px;
  background: #050505;
  overflow: hidden;
}
</style>
