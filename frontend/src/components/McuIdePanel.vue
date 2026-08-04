<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import { VueMonacoEditor } from '@guolao/vue-monaco-editor';
import SerialMonitorPanel from './SerialMonitorPanel.vue';

import { computed } from 'vue';
const props = defineProps({
  nodeId: { type: String, required: false },
  port: { type: String, required: false },
  viewMode: { type: String, default: 'full' },
  params: { type: Object, required: false }
});

const activeNodeId = computed(() => props.nodeId || props.params?.nodeId);
const activePort = computed(() => props.port || props.params?.port);
const activeViewMode = computed(() => props.params?.viewMode || props.viewMode);


const emit = defineEmits(['disconnect-serial', 'reconnect-serial']);
const emitDisconnect = () => {
  serialEvents.dispatchEvent(new Event('disconnect'));
  emit('disconnect-serial');
};
const emitReconnect = (opts) => {
  const e = new Event('reconnect');
  e.options = opts;
  serialEvents.dispatchEvent(e);
  emit('reconnect-serial', opts);
};


import { toRefs } from 'vue';
import { sharedState, flashFile, serialEvents } from './mcuState.ts';

const { 
  mcuFiles, currentPath, activeFile, openFiles, fileContent, fileLanguage, 
  loading, error, success, aiExplanation, sudoPassword,
  flashTool, flashChip, flashOffset, autoFirmware, isWorkspaceMode, workspaceTemplate } = toRefs(sharedState);
const showFlashMenu = ref(false);
const showExplorer = ref(true);
const showEditor = ref(true);
const showTerminal = ref(true);
const showSerialMonitor = ref(false);

const bottomSplitRatio = ref(50);
const isDraggingBottom = ref(false);

const startBottomDrag = (e) => {
  isDraggingBottom.value = true;
  document.body.style.cursor = 'col-resize';
  const onMouseMove = (ev) => {
    if (!isDraggingBottom.value) return;
    const container = document.querySelector('.ide-bottom-panels');
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const newRatio = ((ev.clientX - rect.left) / rect.width) * 100;
    if (newRatio > 10 && newRatio < 90) {
      bottomSplitRatio.value = newRatio;
    }
  };
  const onMouseUp = () => {
    isDraggingBottom.value = false;
    document.body.style.cursor = '';
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
    if (term && term._handleResize) term._handleResize();
  };
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
};


// Editor Config
const editorOptions = {
  theme: 'vs-dark',
  automaticLayout: true,
  fontSize: 14,
  minimap: { enabled: false }
};

const microPythonDefs = {
  time: ['sleep', 'sleep_ms', 'sleep_us', 'ticks_ms', 'ticks_us', 'ticks_cpu', 'ticks_add', 'ticks_diff', 'time', 'localtime'],
  machine: ['Pin', 'ADC', 'PWM', 'I2C', 'SPI', 'UART', 'Timer', 'RTC', 'reset', 'freq', 'idle', 'sleep', 'deepsleep', 'WDT'],
  network: ['WLAN', 'STA_IF', 'AP_IF', 'LAN', 'PHY_LAN8720'],
  neopixel: ['NeoPixel'],
  dht: ['DHT11', 'DHT22'],
  os: ['uname', 'urandom', 'listdir', 'mkdir', 'remove', 'rmdir', 'rename', 'stat', 'statvfs', 'dupterm'],
  uos: ['uname', 'urandom', 'listdir', 'mkdir', 'remove', 'rmdir', 'rename', 'stat', 'statvfs', 'dupterm'],
  sys: ['path', 'argv', 'version', 'version_info', 'implementation', 'platform', 'byteorder', 'maxsize', 'exit', 'stdin', 'stdout', 'stderr', 'modules', 'print_exception'],
  usys: ['path', 'argv', 'version', 'version_info', 'implementation', 'platform', 'byteorder', 'maxsize', 'exit', 'stdin', 'stdout', 'stderr', 'modules', 'print_exception'],
  json: ['dumps', 'loads'],
  ujson: ['dumps', 'loads'],
  math: ['e', 'pi', 'sqrt', 'pow', 'exp', 'log', 'cos', 'sin', 'tan', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'copysign', 'fabs', 'floor', 'fmod', 'frexp', 'ldexp', 'modf', 'isfinite', 'isinf', 'isnan', 'trunc', 'radians', 'degrees'],
  binascii: ['hexlify', 'unhexlify', 'a2b_base64', 'b2a_base64'],
  hashlib: ['sha256', 'sha1', 'md5'],
  socket: ['socket', 'getaddrinfo', 'AF_INET', 'AF_INET6', 'SOCK_STREAM', 'SOCK_DGRAM', 'IPPROTO_TCP', 'IPPROTO_UDP']
};

const handleEditorBeforeMount = (monaco) => {
  monaco.languages.registerCompletionItemProvider('python', {
    triggerCharacters: ['.'],
    provideCompletionItems: (model, position) => {
      const line = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column
      });
      
      const suggestions = [];
      
      // Look for any word followed by a dot, e.g. "time.", "machine.", "dht."
      const match = line.match(/([a-zA-Z0-9_]+)\.$/);
      if (match) {
        const modName = match[1];
        if (microPythonDefs[modName]) {
          microPythonDefs[modName].forEach(fn => {
            suggestions.push({
              label: fn,
              kind: monaco.languages.CompletionItemKind.Method,
              insertText: fn,
              detail: `${modName}.${fn}`
            });
          });
        }
      }

      return { suggestions };
    }
  });
};

// Terminal state
const terminalRef = ref(null);
let term = null;
let fitAddon = null;
let wsRepl = null;

const authHeaders = () => {
  const token = localStorage.getItem('nr_token');
  return { 'Authorization': `Bearer ${token}` };
};

// ========================
// TERMINAL & WEBSOCKET
// ========================
const initTerminal = () => {
  if (!terminalRef.value) return;
  term = new Terminal({
    theme: {
      background: '#0a0a0a',
      foreground: '#00e5ff',
      cursor: '#ff0055'
    },
    cursorBlink: true,
    fontFamily: '"Courier New", Courier, monospace',
    fontSize: 14
  });
  fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.open(terminalRef.value);
  fitAddon.fit();
  
  term.writeln('Welcome to NeoThonny REPL...');
  term.writeln('Connecting to MCU...');
  

  const handleResize = () => {
    if (fitAddon) fitAddon.fit();
  };
  window.addEventListener('resize', handleResize);
  term._handleResize = handleResize; // Store reference for unmounting
};

const connectRepl = () => {
  if (wsRepl) {
    wsRepl.close();
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = localStorage.getItem('nr_token') || '';
  const wsUrl = `${protocol}//${window.location.host}/ws/mcu_repl?port=${encodeURIComponent(activePort.value)}&node_id=${encodeURIComponent(activeNodeId.value)}&token=${encodeURIComponent(token)}`;
  wsRepl = new WebSocket(wsUrl);

  wsRepl.onopen = () => {
    term.writeln('\r\n[Connected to REPL via WebSocket]\r\n');
  };

  wsRepl.onmessage = (event) => {
    term.write(event.data);
  };

  wsRepl.onclose = () => {
    term.writeln('\r\n[REPL connection closed]\r\n');
  };

  wsRepl.onerror = (err) => {
    console.error('REPL WebSocket Error:', err);
    term.writeln('\r\n[REPL connection error]\r\n');
  };

  term.onData(data => {
    if (wsRepl && wsRepl.readyState === WebSocket.OPEN) {
      wsRepl.send(data);
    }
  });
};

const disconnectRepl = () => {
  if (wsRepl) {
    wsRepl.close();
    wsRepl = null;
  }
};

// ========================
// FILE OPS
// ========================
const getFullPath = (filename) => {
  const p = currentPath.value.replace(/\/+$/, '');
  // Skip leading slash to support all MicroPython vfs implementations
  if (p === '' || p === '/') return filename;
  // If p already doesn't have a leading slash, just append
  if (p.startsWith('/')) {
    return p === '/' ? filename : p.substring(1) + '/' + filename;
  }
  return p + '/' + filename;
};

const listFiles = async () => {
  disconnectRepl(); // Let API use the port
  emitDisconnect();
  loading.value = true;
  mcuFiles.value = [];
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  try {
    const endpoint = isWorkspaceMode.value 
      ? `/api/v1/workspace/list?node_id=${encodeURIComponent(activeNodeId.value)}&path=${encodeURIComponent(currentPath.value)}`
      : `/api/v1/mcu/${activeNodeId.value}/files?port=${encodeURIComponent(activePort.value)}&path=${encodeURIComponent(currentPath.value)}&sudo_password=${encodeURIComponent(sudoPassword.value)}`;
    
    const res = await fetch(endpoint, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    mcuFiles.value = data.files || [];
    if (currentPath.value !== '/' && currentPath.value !== '.') {
      mcuFiles.value.unshift({ name: '..', is_dir: true, size: 0 });
    }
  } catch(err) {
    error.value = 'Failed to list files: ' + err.message;
  } finally {
    loading.value = false;
    
     // Resume REPL
  }
};

const openFileOrDir = async (f) => {
  const oldPath = currentPath.value;
  if (f.name === '..') {
    const parts = currentPath.value.replace(/\/+$/, '').split('/');
    parts.pop();
    currentPath.value = parts.join('/') || '/';
    try {
      await listFiles();
    } catch(e) {
      currentPath.value = oldPath;
    }
  } else if (f.is_dir) {
    currentPath.value = getFullPath(f.name);
    try {
      await listFiles();
    } catch(e) {
      currentPath.value = oldPath;
    }
  } else {
    readFile(getFullPath(f.name));
  }
};

const readFile = async (fullPath) => {
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  try {
    const endpoint = isWorkspaceMode.value
      ? `/api/v1/workspace/read?node_id=${encodeURIComponent(activeNodeId.value)}&path=${encodeURIComponent(fullPath)}`
      : `/api/v1/mcu/${activeNodeId.value}/read?port=${encodeURIComponent(activePort.value)}&path=${encodeURIComponent(fullPath)}&sudo_password=${encodeURIComponent(sudoPassword.value)}`;
      
    const res = await fetch(endpoint, { headers: authHeaders() });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    
    // Switch to tab if already open, else create
    const existing = openFiles.value.find(f => f.path === fullPath);
    if (existing) {
      existing.content = data.content || '';
      activeFile.value = fullPath;
      fileContent.value = existing.content;
    } else {
      openFiles.value.push({ path: fullPath, content: data.content || '' });
      activeFile.value = fullPath;
      fileContent.value = data.content || '';
    }
    
    if (fullPath.endsWith('.py')) fileLanguage.value = 'python';
    else if (fullPath.endsWith('.json')) fileLanguage.value = 'json';
    else if (fullPath.endsWith('.html')) fileLanguage.value = 'html';
    else if (fullPath.endsWith('.js')) fileLanguage.value = 'javascript';
    else if (fullPath.endsWith('.css')) fileLanguage.value = 'css';
    else fileLanguage.value = 'plaintext';
    
  } catch(err) {
    error.value = 'Failed to read file: ' + err.message;
  } finally {
    loading.value = false;
  }
};

const switchTab = (path) => {
  const tab = openFiles.value.find(f => f.path === path);
  if (tab) {
    activeFile.value = tab.path;
    fileContent.value = tab.content;
    if (path.endsWith('.py')) fileLanguage.value = 'python';
    else if (path.endsWith('.json')) fileLanguage.value = 'json';
    else if (path.endsWith('.html')) fileLanguage.value = 'html';
    else if (path.endsWith('.js')) fileLanguage.value = 'javascript';
    else if (path.endsWith('.css')) fileLanguage.value = 'css';
    else fileLanguage.value = 'plaintext';
  }
};

const closeTab = (path) => {
  const idx = openFiles.value.findIndex(f => f.path === path);
  if (idx !== -1) {
    openFiles.value.splice(idx, 1);
    if (activeFile.value === path) {
      if (openFiles.value.length > 0) {
        // Switch to the previous tab, or the first one
        const newIdx = Math.max(0, idx - 1);
        switchTab(openFiles.value[newIdx].path);
      } else {
        activeFile.value = '';
        fileContent.value = '';
      }
    }
  }
};

import { watch } from 'vue';
watch(fileContent, (newVal) => {
  if (activeFile.value) {
    const tab = openFiles.value.find(f => f.path === activeFile.value);
    if (tab) {
      tab.content = newVal;
    }
  }
});

const saveFile = async () => {
  if (!activeFile.value) return;
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  success.value = '';
  try {
    const endpoint = isWorkspaceMode.value
      ? `/api/v1/workspace/write?node_id=${encodeURIComponent(activeNodeId.value)}&path=${encodeURIComponent(activeFile.value)}`
      : `/api/v1/mcu/${activeNodeId.value}/write`;
      
    const bodyPayload = isWorkspaceMode.value
      ? { content: fileContent.value }
      : { port: activePort.value, path: activeFile.value, content: fileContent.value, sudo_password: sudoPassword.value };

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(bodyPayload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    success.value = 'File saved successfully!';
    await listFiles();
  } catch(err) {
    error.value = 'Failed to save file: ' + err.message;
  } finally {
    loading.value = false;
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const runScript = async () => {
  if (!fileContent.value) return;
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  success.value = '';
  aiExplanation.value = '';
  try {
    if (isWorkspaceMode.value) {
      if (!workspaceTemplate.value) {
        throw new Error("No template selected for workspace. Did you init a project?");
      }
      // WebSocket builder
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const token = localStorage.getItem('nr_token') || '';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/workspace/build?node_id=${encodeURIComponent(activeNodeId.value)}&template=${encodeURIComponent(workspaceTemplate.value)}&token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => { term.write(e.data); };
      ws.onerror = (e) => { error.value = "Builder WebSocket error. The connection was lost, but the build might still be running on the server."; };
      ws.onclose = () => { 
        // We don't set success here anymore, because onclose fires on error as well.
        // Success is now only indicated by the terminal output itself.
      };
      
      // Connect terminal to builder mode visually
      term.writeln('\\r\\n[Starting Workspace Build...]\\r\\n');
      return;
    }

    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/run_script`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        port: activePort.value,
        language: fileLanguage.value === 'python' ? 'micropython' : fileLanguage.value,
        code: fileContent.value,
        sudo_password: sudoPassword.value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    
    let outStr = data.output || '';
    try {
      const parsed = JSON.parse(outStr);
      if (parsed && parsed.error) {
        throw new Error(parsed.error);
      }
      if (parsed && parsed.output !== undefined) {
        outStr = parsed.output;
      }
    } catch(e) {
      if (e.message !== "Unexpected token" && !e.message.includes("JSON")) {
        throw e; // Rethrow if it was the parsed.error being thrown
      }
    }

    success.value = 'Script executed successfully!\\n' + outStr;
    
    // Mock AI check if there is Traceback
    if (outStr && outStr.includes('Traceback')) {
      error.value = 'Crash detected in output! Use AI Assistant to explain.';
    }
  } catch(err) {
    error.value = 'Failed to run script: ' + err.message;
  } finally {
    loading.value = false;
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const explainErrorAI = () => {
  aiExplanation.value = "🤖 AI Assistant: I see a crash! It looks like you forgot to import a module or have an indentation error. Check line numbers in the Traceback above.";
};

const stopMcu = async () => {
  // If REPL is connected, we can just send Ctrl-C directly!
  if (wsRepl && wsRepl.readyState === WebSocket.OPEN) {
    wsRepl.send('\x03'); // Ctrl-C
    success.value = 'Sent Ctrl-C to REPL';
    return;
  }
  
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  try {
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/stop`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ port: activePort.value, sudo_password: sudoPassword.value })
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Error stopping MCU');
    }
  } catch(err) {
    error.value = 'Failed to stop MCU: ' + err.message;
  } finally {
    loading.value = false;
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const resetMcu = async () => {
  disconnectRepl();
  loading.value = true;
  error.value = '';
  try {
    // This tells UsbPanel to ensure Serial Monitor is connected
    // and passing {reset: true} tells the Serial Monitor to either:
    // a) connect and run a startup hard reset immediately
    // b) trigger the backend reset endpoint if it's already connected
    emitReconnect({ force: true, reset: true });
    success.value = 'Sent Hard Reset signal';
  } catch(err) {
    error.value = 'Failed to reset MCU: ' + err.message;
  } finally {
    loading.value = false;
  }
};

const newScript = () => {
  activeFile.value = getFullPath('untitled.py');
  fileContent.value = '# New MicroPython Script\n\nprint("NeoThonny is ready")';
  fileLanguage.value = 'python';
};

const newFolder = async () => {
  const folderName = prompt('Enter folder name:');
  if (!folderName) return;
  
  const fullPath = getFullPath(folderName);
  
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  try {
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/mkdir`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        port: activePort.value,
        path: fullPath,
        sudo_password: sudoPassword.value
      })
    });
    if (!res.ok) throw new Error('Error creating folder');
    await listFiles();
  } catch(err) {
    error.value = 'Failed to create folder: ' + err.message;
  } finally {
    loading.value = false;
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const injectOtaScript = () => {
  activeFile.value = 'ota_update.py';
  fileContent.value = `import network
import urequests
import os
import machine
import time

# --- OTA Update Configuration ---
WIFI_SSID = "dit_wifi_navn"
WIFI_PASS = "din_wifi_kode"
FIRMWARE_URL = "http://din-server.dk/firmware.py" # URL til din nye kode

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Forbinder til WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(1)
    print("Netværk klar:", wlan.ifconfig())

def download_and_install():
    print("Henter opdatering fra:", FIRMWARE_URL)
    try:
        response = urequests.get(FIRMWARE_URL)
        if response.status_code == 200:
            print("Download succesfuld. Skriver til main.py...")
            with open("main.py", "w") as f:
                f.write(response.text)
            print("Opdatering installeret! Genstarter...")
            machine.reset()
        else:
            print("Download fejlede. Status:", response.status_code)
    except Exception as e:
        print("Fejl under opdatering:", e)

def check_for_updates():
    connect_wifi()
    # Her kan du evt. tilføje logik der tjekker et versionsnummer
    download_and_install()

    check_for_updates()
`;
  fileLanguage.value = 'python';
};

const hostAsOta = async () => {
  if (!fileContent.value) return;
  loading.value = true;
  error.value = '';
  success.value = '';
  try {
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/ota`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: fileContent.value })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    const host = window.location.host;
    const proto = window.location.protocol;
    success.value = `Hosted! Access OTA via: ${proto}//${host}/api/v1/mcu/${activeNodeId.value}/ota?token=${data.token}`;
  } catch(err) {
    error.value = 'Failed to host OTA: ' + err.message;
  } finally {
    loading.value = false;
  }
};

const deleteFile = async (f) => {
  if (!confirm(`Are you sure you want to delete ${f.name}?`)) return;
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  try {
    const fullPath = getFullPath(f.name);
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/delete?port=${encodeURIComponent(activePort.value)}&path=${encodeURIComponent(fullPath)}&sudo_password=${encodeURIComponent(sudoPassword.value)}`, {
      method: 'DELETE',
      headers: authHeaders()
    });
    if (!res.ok) throw new Error('Error deleting file');
    await listFiles();
  } catch(err) {
    error.value = 'Failed to delete file: ' + err.message;
  } finally {
    loading.value = false;
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const installTools = async () => {
  loading.value = true;
  error.value = '';
  success.value = '';
  try {
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/install_tools`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ tools: ["mpremote", "esptool", "pyserial"], sudo_password: sudoPassword.value })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    success.value = 'MCU tools installed successfully!';
  } catch(err) {
    error.value = 'Failed to install tools: ' + err.message;
  } finally {
    loading.value = false;
  }
};

const libUploadInput = ref(null);
const handleLibFile = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  success.value = '';
  
  try {
    const formData = new FormData();
    formData.append('port', activePort.value);
    formData.append('path', currentPath.value);
    formData.append('sudo_password', sudoPassword.value);
    formData.append('file', file);
    
    const token = localStorage.getItem('nr_token');
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/upload_lib`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }, // Do NOT set Content-Type for FormData
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    
    success.value = `Library ${file.name} uploaded successfully!`;
    await listFiles();
  } catch(err) {
    error.value = 'Library upload failed: ' + err.message;
  } finally {
    loading.value = false;
    e.target.value = null; // reset input
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const toggleFlashMenu = () => {
  showFlashMenu.value = !showFlashMenu.value;
};

const handleFlashFile = (e) => {
  flashFile.value = e.target.files[0];
};

const flashManual = async () => {
  if (!flashFile.value) return;
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  success.value = '';
  try {
    const fileData = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result.split(',')[1]);
      reader.onerror = () => reject(new Error("File read error"));
      reader.readAsDataURL(flashFile.value);
    });
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/flash`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        port: activePort.value,
        tool: flashTool.value,
        chip: flashChip.value,
        offset: flashOffset.value,
        file_b64: fileData,
        sudo_password: sudoPassword.value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Flash failed');
    success.value = 'Firmware flashed successfully!';
  } catch(err) {
    error.value = 'Flash error: ' + err.message;
  } finally {
    loading.value = false;
    showFlashMenu.value = false;
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const flashAuto = async () => {
  if (!autoFirmware.value) {
    if (flashTool.value === 'esptool') {
      autoFirmware.value = "https://micropython.org/resources/firmware/ESP32_GENERIC-20240602-v1.23.0.bin";
    } else {
      error.value = "Hov! Du skal skrive en URL til din firmware (.bin fil) først!";
      return;
    }
  }
  disconnectRepl();
  emitDisconnect();
  loading.value = true;
  await new Promise(r => setTimeout(r, 1500));
  error.value = '';
  success.value = '';
  try {
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/flash_auto`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        port: activePort.value,
        tool: flashTool.value,
        url: autoFirmware.value,
        offset: flashOffset.value,
        sudo_password: sudoPassword.value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Auto flash failed');
    success.value = 'Auto flash completed!';
  } catch(err) {
    error.value = 'Auto flash error: ' + err.message;
  } finally {
    loading.value = false;
    showFlashMenu.value = false;
    await new Promise(r => setTimeout(r, 1000));
    
    
  }
};

const initProject = async (template) => {
  loading.value = true;
  error.value = '';
  try {
    const res = await fetch(`/api/v1/workspace/init?node_id=${encodeURIComponent(activeNodeId.value)}`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ template })
    });
    if (!res.ok) throw new Error(await res.text());
    workspaceTemplate.value = template;
    success.value = `Project initialized with ${template}`;
    currentPath.value = '/';
    openFiles.value = [];
    activeFile.value = '';
    fileContent.value = '';
    await listFiles();
  } catch (err) {
    error.value = "Init error: " + err.message;
  } finally {
    loading.value = false;
  }
};

const flashWorkspace = async () => {
  loading.value = true;
  error.value = '';
  success.value = '';
  try {
    const res = await fetch(`/api/v1/mcu/${activeNodeId.value}/flash_workspace`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        port: activePort.value,
        template: workspaceTemplate.value,
        sudo_password: sudoPassword.value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Flash failed");
    success.value = "Flash completed!\n" + data.output;
  } catch (err) {
    error.value = "Flash error: " + err.message;
  } finally {
    loading.value = false;
  }
};

import { watch as vueWatch } from 'vue';
vueWatch(isWorkspaceMode, (val) => {
  currentPath.value = '/';
  openFiles.value = [];
  activeFile.value = '';
  fileContent.value = '';
  listFiles();
});

onMounted(() => {
  nextTick(() => {
    initTerminal();
    listFiles();
  });
});

onBeforeUnmount(() => {
  disconnectRepl();
  if (term && term._handleResize) {
    window.removeEventListener('resize', term._handleResize);
  }
  if (term) term.dispose();
});
</script>

<template>
  <div class="mcu-ide">
    <!-- TOP TOOLBAR -->
    <div class="ide-toolbar">
      <div class="brand" style="display: flex; align-items: center; gap: 10px;">
        <span style="display: flex; gap: 6px; align-items: center;">
          Netrunner IDE 
          <span v-if="isWorkspaceMode && workspaceTemplate" class="env-badge" :class="workspaceTemplate">
            <span v-if="workspaceTemplate === 'rust-std'">🦀 RUST</span>
            <span v-else-if="workspaceTemplate === 'esp-idf-c'">⚙️ C++</span>
            <span v-else>🐍 PYTHON</span>
          </span>
        </span>
        <div class="led-box" :title="loading ? 'System working...' : 'System ready'">
          <div class="led" :class="{'led-yellow': loading, 'led-green': !loading}"></div>
        </div>
      </div>
      <div class="toolbar-modes">
        <button class="btn btn-sm" :class="{active: !isWorkspaceMode}" @click="isWorkspaceMode = false">🐍 MCU FS</button>
        <button class="btn btn-sm" :class="{active: isWorkspaceMode}" @click="isWorkspaceMode = true">🚀 Workspace</button>
        <div style="border-left: 1px solid #444; margin: 0 5px;"></div>
        <button class="btn btn-sm" :class="{active: showExplorer}" @click="showExplorer = !showExplorer">📁 Explorer</button>
        <button class="btn btn-sm" :class="{active: showEditor}" @click="showEditor = !showEditor">📝 Editor</button>
        <button class="btn btn-sm" :class="{active: showTerminal}" @click="showTerminal = !showTerminal">🖥️ Terminal</button>
        <button class="btn btn-sm" :class="{active: showSerialMonitor}" @click="showSerialMonitor = !showSerialMonitor">📟 Serial Monitor</button>
      </div>
      <input type="password" v-model="sudoPassword" class="input-bare" style="width: 100px; border-bottom: 1px solid #555;" placeholder="Sudo Pass" title="Sudo password for serial port access" />
      <button class="btn" @click="installTools" :disabled="loading" title="Run this first to install mpremote on the node!" v-if="!isWorkspaceMode">📦 Install Tools</button>
      <button class="btn" @click="listFiles" :disabled="loading">🔄 Refresh</button>
      <button class="btn btn-primary" @click="saveFile" :disabled="!activeFile || loading">💾 Save File</button>
      
      <template v-if="!isWorkspaceMode">
        <button class="btn btn-flash" @click="toggleFlashMenu">⚡ Flash Firmware</button>
      </template>
      <template v-else>
        <select v-model="workspaceTemplate" class="input-bare" style="margin-right: 5px; background: #333; color: white;">
          <option value="" disabled>-- Template --</option>
          <option value="esp-idf-c">C++ ESP-IDF</option>
          <option value="rust-std">Rust (STD)</option>
        </select>
        <button class="btn btn-primary" @click="initProject(workspaceTemplate)" :disabled="!workspaceTemplate || loading">🆕 Init Project</button>
        <button class="btn btn-flash" @click="flashWorkspace" :disabled="!workspaceTemplate || loading">⚡ Flash Workspace</button>
      </template>
    </div>

    <!-- FLASH MENU (TOGGLEABLE) -->
    <div class="flash-menu" v-if="showFlashMenu && (activeViewMode === 'full' || activeViewMode === 'editor')">
      <div class="flash-row">
        <label>Tool:</label>
        <select v-model="flashTool" class="input-bare">
          <option value="esptool">esptool (ESP32/8266)</option>
          <option value="avrdude">avrdude (Arduino)</option>
          <option value="espflash">espflash (Rust)</option>
          <option value="probe-rs">probe-rs (STM32/RP2040)</option>
        </select>
        
        <label>Offset:</label>
        <input type="text" v-model="flashOffset" class="input-bare" style="width: 80px" />
      </div>

      <div class="flash-row">
        <strong>Auto Flash:</strong>
        <input type="text" v-model="autoFirmware" placeholder="Firmware URL (e.g. MicroPython .bin)" class="input-bare url-input" />
        <button class="btn btn-primary btn-sm" @click="flashAuto" :disabled="loading">Auto Download & Flash</button>
      </div>

      <div class="flash-row">
        <strong>Manual Flash:</strong>
        <input type="file" @change="handleFlashFile" accept=".bin,.hex" class="file-input" />
        <button class="btn btn-primary btn-sm" @click="flashManual" :disabled="!flashFile || loading">Upload Local .bin</button>
      </div>
    </div>

    <!-- MAIN IDE SPLIT -->
    <div class="ide-body" v-if="activeViewMode === 'full' || activeViewMode === 'explorer' || activeViewMode === 'editor'">
      <!-- SIDEBAR -->
      <div class="ide-sidebar" v-show="showExplorer && (activeViewMode === 'full' || activeViewMode === 'explorer')">
        <div class="sidebar-title">
          <span>Explorer</span>
          <div style="display: flex; gap: 8px;">
            <input type="file" ref="libUploadInput" @change="handleLibFile" accept=".zip" style="display: none" />
            <button class="btn-icon" @click="libUploadInput.click()" title="Upload Library (.zip)">📦</button>
            <button class="btn-icon" @click="injectOtaScript" title="Inject OTA Script">☁️</button>
            <button class="btn-icon" @click="newFolder" title="New Folder">📁</button>
            <button class="btn-icon" @click="newScript" title="New File">➕</button>
          </div>
        </div>
        <div class="current-path" style="padding: 4px 10px; font-size: 11px; background: #222; color: #aaa; border-bottom: 1px solid #333;">
          {{ currentPath }}
        </div>
        <div v-if="mcuFiles.length === 0" class="no-files">No files found.</div>
        <div v-for="f in mcuFiles" :key="f.name" 
             class="file-item" 
             :class="{active: activeFile === getFullPath(f.name)}"
             @click="openFileOrDir(f)">
          <span class="file-icon">{{ f.is_dir ? '📁' : '📄' }}</span>
          <span class="file-name">{{ f.name }}</span>
          <span class="file-size" v-if="!f.is_dir">{{ f.size }}</span>
          <button class="btn-delete" @click.stop="deleteFile(f)" title="Delete" v-if="f.name !== '..'">🗑️</button>
        </div>
      </div>

      <!-- EDITOR AREA -->
      <div class="ide-editor-area" v-show="showEditor && (activeViewMode === 'full' || activeViewMode === 'editor')">
        <div class="editor-header">
          <div class="tab-active">
            <input type="text" v-model="activeFile" placeholder="Filename (e.g. main.py)" class="input-bare" />
          </div>
          <div class="editor-actions">
            <select v-model="fileLanguage" class="select-bare">
              <option value="python">Python</option>
              <option value="cpp">C++</option>
              <option value="rust">Rust</option>
            </select>
            <button class="btn btn-ai" @click="hostAsOta" :disabled="loading || !activeFile">☁️ Host as OTA</button>
            <button class="btn btn-ai" @click="explainErrorAI" title="Ask AI to fix crash">🤖 AI Explain</button>
            <button class="btn btn-stop" @click="stopMcu" :disabled="loading" title="Ctrl-C">🛑 STOP</button>
            <button class="btn btn-reset" @click="resetMcu" :disabled="loading" title="Ctrl-D">🔄 RESTART</button>
            <button class="btn btn-play" @click="runScript" :disabled="loading || !activeFile">▶ RUN / BUILD</button>
          </div>
        </div>
        
        <!-- STATUS MESSAGES -->
        <div class="ide-status" v-if="error || success || aiExplanation || loading">
          <span class="loading" v-if="loading">Processing... </span>
          <span class="error" v-if="error">{{ error }} </span>
          <span class="success" v-if="success">{{ success }} </span>
          <div class="ai-box" v-if="aiExplanation">{{ aiExplanation }}</div>
        </div>

        <!-- TABS -->
        <div class="editor-tabs" v-if="openFiles.length > 0">
          <div class="editor-tab" 
               v-for="tab in openFiles" :key="tab.path"
               :class="{ active: tab.path === activeFile }"
               @click="switchTab(tab.path)">
            <span class="tab-title">{{ tab.path.split('/').pop() }}</span>
            <span class="tab-close" @click.stop="closeTab(tab.path)">✕</span>
          </div>
        </div>

        <!-- MONACO EDITOR -->
        <div class="editor-container">
          <vue-monaco-editor
            v-model:value="fileContent"
            :language="fileLanguage"
            :options="editorOptions"
            @beforeMount="handleEditorBeforeMount"
            height="100%"
          />
        </div>
      </div>
    </div>

    <!-- BOTTOM PANELS (Side by Side) -->
    <div class="ide-bottom-panels" v-show="(showTerminal && (activeViewMode === 'full' || activeViewMode === 'repl')) || showSerialMonitor" style="display: flex; flex-direction: row; height: 35%; min-height: 150px; flex-shrink: 0; border-top: 2px solid var(--border);">
      
      <!-- REPL TERMINAL -->
      <div class="ide-repl" v-show="showTerminal && (activeViewMode === 'full' || activeViewMode === 'repl')" :style="{ flex: showSerialMonitor ? `0 0 ${bottomSplitRatio}%` : 1, minWidth: 0 }">
        <div class="repl-header">
          Terminal / Serial REPL (Interactive)
          <span style="font-size: 11px; opacity: 0.7;">| Connected to: {{ port }}</span>
        </div>
        <div class="repl-container" ref="terminalRef"></div>
      </div>
      
      <!-- HORIZONTAL RESIZER -->
      <div v-show="showTerminal && (activeViewMode === 'full' || activeViewMode === 'repl') && showSerialMonitor" 
           @mousedown="startBottomDrag"
           style="width: 6px; background: #333; cursor: col-resize; flex-shrink: 0; z-index: 10; border-left: 1px solid #111; border-right: 1px solid #111;"
           class="bottom-resizer">
      </div>
      
      <!-- SERIAL MONITOR PANEL -->
      <div class="ide-serial-monitor" v-show="showSerialMonitor" style="flex: 1; min-width: 0; padding: 10px; background: #111; overflow: hidden; display: flex; flex-direction: column;">
        <SerialMonitorPanel :nodeId="activeNodeId" :port="activePort" style="flex: 1; height: 100%;" />
      </div>

    </div>
  </div>
</template>

<style scoped>
.mcu-ide {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-height: 100%;
  background: #1e1e1e;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  font-family: var(--font-co);
}

.ide-toolbar {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 8px 15px;
  background: #2d2d2d;
  border-bottom: 1px solid #000;
}

.brand {
  font-family: var(--font-hd);
  color: var(--cyan);
  font-weight: bold;
  font-size: 16px;
  margin-right: auto;
}

.btn {
  background: #3c3c3c;
  color: #ccc;
  border: 1px solid #555;
  padding: 5px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-hd);
  transition: all 0.2s;
}
.btn:hover:not(:disabled) { background: #4a4a4a; color: #fff; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--cyan); color: #000; border-color: var(--cyan); }
.btn-primary:hover:not(:disabled) { background: #00b3cc; }
.btn-sm { padding: 3px 8px; font-size: 11px; }
.btn-flash { background: rgba(255, 215, 0, 0.2); color: gold; border-color: gold; margin-left: auto; }

/* FLASH MENU */
.flash-menu {
  background: #1a1a1a;
  border-bottom: 2px solid #333;
  padding: 10px 15px;
  font-size: 13px;
}
.flash-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.flash-row:last-child { margin-bottom: 0; }
.flash-row label { color: #888; }
.url-input { flex: 1; min-width: 200px; background: #222; border: 1px solid #444; padding: 4px; }
.file-input { color: #ccc; font-size: 12px; }

.led-box {
  display: flex;
  align-items: center;
  justify-content: center;
}
.led {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 0 5px rgba(0,0,0,0.5);
  transition: all 0.3s;
}
.led-green {
  background-color: #0f0;
  box-shadow: 0 0 8px #0f0;
}
.led-yellow {
  background-color: #ff0;
  box-shadow: 0 0 8px #ff0;
  animation: pulse-yellow 1s infinite;
}
@keyframes pulse-yellow {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.ide-body {
  display: flex;
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

/* SIDEBAR */
.ide-sidebar {
  width: 250px;
  background: #252526;
  border-right: 1px solid #1e1e1e;
  display: flex;
  flex-direction: column;
}
.sidebar-title {
  padding: 10px 15px;
  font-size: 11px;
  text-transform: uppercase;
  color: #bbb;
  font-weight: bold;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.btn-icon { background: transparent; border: none; cursor: pointer; opacity: 0.6; }
.btn-icon:hover { opacity: 1; }

.no-files { padding: 15px; color: #666; font-size: 12px; }
.file-item {
  padding: 6px 15px;
  font-size: 13px;
  color: #ccc;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-item:hover { background: #2a2d2e; }
.file-item.active { background: #37373d; color: #fff; }
.file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { color: #888; font-size: 10px; }
.btn-delete { background: none; border: none; opacity: 0; cursor: pointer; }
.file-item:hover .btn-delete { opacity: 1; color: #ff5555; }

/* EDITOR AREA */
.ide-editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
}

.editor-header {
  display: flex;
  background: #2d2d2d;
  height: 40px;
  align-items: center;
  justify-content: space-between;
  padding-right: 15px;
}

.tab-active {
  background: #1e1e1e;
  height: 100%;
  padding: 0 20px;
  display: flex;
  align-items: center;
  border-top: 2px solid var(--cyan);
}
.input-bare {
  background: transparent;
  border: none;
  color: #fff;
  font-family: var(--font-co);
  outline: none;
  width: 150px;
}

.editor-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.select-bare {
  background: transparent;
  border: 1px solid #555;
  color: #ccc;
  border-radius: 4px;
  padding: 3px;
}

.btn-ai { background: rgba(138, 43, 226, 0.2); color: #b48ced; border-color: #8a2be2; }
.btn-stop { background: rgba(255, 0, 85, 0.2); color: #ff0055; border-color: #ff0055; }
.btn-reset { background: rgba(255, 165, 0, 0.2); color: orange; border-color: orange; }
.btn-play { background: rgba(0, 255, 0, 0.1); color: #00ff00; border-color: #00ff00; }

.editor-container {
  flex: 1;
  overflow: hidden;
}

.ide-status {
  background: #111;
  padding: 10px 15px;
  font-size: 13px;
  border-bottom: 1px solid #333;
}
.loading { color: var(--cyan); }
.error { color: #ff5555; }
.success { color: #55ff55; }
.ai-box {
  margin-top: 8px;
  padding: 10px;
  background: rgba(138, 43, 226, 0.1);
  border-left: 3px solid #8a2be2;
  color: #d8b4fe;
}

/* REPL TERMINAL */
.ide-repl {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
}
.repl-header {
  padding: 5px 15px;
  background: #1a1a1a;
  color: #888;
  font-size: 11px;
  text-transform: uppercase;
  border-bottom: 1px solid #222;
}
.repl-container {
  flex: 1;
  padding: 10px;
  overflow: hidden;
}

.panel-toggles { display: flex; gap: 5px; margin-left: 15px; border-left: 1px solid #444; padding-left: 15px; }
.btn.active { background: var(--cyan); color: #000; border-color: var(--cyan); }

.editor-tabs {
  display: flex;
  background: #1e1e1e;
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}
.editor-tab {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #2d2d2d;
  border-right: 1px solid var(--border);
  cursor: pointer;
  color: #ccc;
  font-family: var(--font-co);
  font-size: 13px;
  user-select: none;
}
.editor-tab.active {
  background: #1e1e1e;
  color: #fff;
  border-top: 2px solid var(--cyan);
}
.editor-tab:hover:not(.active) {
  background: #3a3a3a;
}
.tab-title {
  margin-right: 10px;
}
.tab-close {
  opacity: 0.5;
  font-size: 10px;
}
.tab-close:hover {
  opacity: 1;
  color: #ff5555;
}
</style>
