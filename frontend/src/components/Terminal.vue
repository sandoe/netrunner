<template>
  <div class="terminal-wrap" ref="wrapEl">
    <div class="terminal-toolbar">
      <div class="term-info">
        <span class="term-label">NODE:</span>
        <span class="term-node-name">{{ node?.name }}</span>
      </div>
      <div class="term-info">
        <span class="term-label">STATUS:</span>
        <span class="term-status" :class="connected ? 'ok' : 'off'">
          {{ connected ? 'CONNECTED' : 'DISCONNECTED' }}
        </span>
      </div>
      <div class="term-actions">
        <button @click="reconnect" :disabled="connecting" class="btn-sm">
          {{ connecting ? 'ESTABLISHING...' : connected ? 'RECONNECT' : 'CONNECT' }}
        </button>
        <button @click="clearTerminal" class="btn-sm">CLEAR</button>
      </div>
    </div>
    <div ref="termEl" class="xterm-container" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import { wsTerminalUrl } from '@/api/client'
import type { NrNode } from '@/types'

const props = defineProps<{ node: NrNode | null }>()

const wrapEl    = ref<HTMLElement>()
const termEl    = ref<HTMLElement>()
const connected = ref(false)
const connecting = ref(false)

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

function initTerminal() {
  if (!termEl.value) return
  if (term) {
    term.dispose()
  }

  term = new Terminal({
    theme: {
      background: '#020408',
      foreground: '#00ff9d',
      cursor: '#00e5ff',
      cursorAccent: '#020408',
      black: '#05080f',
      brightBlack: '#1a2540',
      red: '#ff2d6e',
      brightRed: '#ff2d6e',
      green: '#00ff9d',
      brightGreen: '#00ff9d',
      yellow: '#ffbe0b',
      brightYellow: '#ffbe0b',
      blue: '#00e5ff',
      brightBlue: '#00e5ff',
      magenta: '#a855f7',
      brightMagenta: '#a855f7',
      cyan: '#00e5ff',
      brightCyan: '#00e5ff',
      white: '#e2e8f0',
      brightWhite: '#ffffff',
    },
    fontFamily: '"JetBrains Mono", "Cascadia Code", monospace',
    fontSize: 14,
    lineHeight: 1.2,
    cursorBlink: true,
    cursorStyle: 'block',
    cursorInactiveStyle: 'outline',
    scrollback: 10000,
    allowProposedApi: true,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())
  term.open(termEl.value)
  fitAddon.fit()
  term.focus()

  term.onData((data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', data }))
    }
  })

  term.onResize(({ cols, rows }) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'resize', cols, rows }))
    }
  })

  resizeObserver = new ResizeObserver(() => fitAddon?.fit())
  resizeObserver.observe(wrapEl.value!)
}

function connect(nodeId: string) {
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  connecting.value = true
  connected.value  = false

  ws = new WebSocket(wsTerminalUrl(nodeId))

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.type === 'output') {
        term?.write(msg.data)
      } else if (msg.type === 'status') {
        connected.value  = msg.connected
        connecting.value = false
        if (msg.connected) {
          term?.write('\r\n\x1b[1;32m[SYSTEM] Neural link established.\x1b[0m\r\n')
          term?.focus()
        }
      } else if (msg.type === 'error') {
        term?.write(`\r\n\x1b[1;31m[ERROR] Connection failed: ${msg.data}\x1b[0m\r\n`)
        connecting.value = false
      }
    } catch {
      term?.write(ev.data)
    }
  }

  ws.onopen = () => {
    term?.write(`\r\n\x1b[1;36m[SYSTEM] Initiating link to ${nodeId}...\x1b[0m\r\n`)
  }

  ws.onerror = () => {
    term?.write('\r\n\x1b[1;31m[SYSTEM] WebSocket protocol error.\x1b[0m\r\n')
    connected.value  = false
    connecting.value = false
  }

  ws.onclose = () => {
    if (connected.value) {
      term?.write('\r\n\x1b[1;31m[SYSTEM] Neural link terminated.\x1b[0m\r\n')
    }
    connected.value  = false
    connecting.value = false
  }
}

function reconnect() {
  if (props.node) connect(props.node.id)
}

function clearTerminal() {
  term?.clear()
}

watch(() => props.node?.id, (newId) => {
  if (newId) {
    connect(newId)
  }
})

onMounted(() => {
  initTerminal()
  if (props.node) connect(props.node.id)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  ws?.close()
  term?.dispose()
})
</script>

<style scoped>
.terminal-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  position: relative;
}
.terminal-toolbar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 8px 16px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
}
.term-info { display: flex; align-items: center; gap: 8px; }
.term-label { font-family: var(--font-hd); font-size: 8px; color: var(--text); letter-spacing: 1px; }
.term-node-name { font-family: var(--font-co); font-size: 11px; font-weight: 600; color: var(--cyan); }
.term-status { font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; }
.term-status.ok  { color: var(--green); text-shadow: 0 0 8px var(--green); }
.term-status.off { color: var(--pink); text-shadow: 0 0 8px var(--pink); }

.term-actions { margin-left: auto; display: flex; gap: 8px; }

.btn-sm {
  padding: 4px 10px; font-family: var(--font-hd); font-size: 8px; letter-spacing: 1px; border-radius: 4px;
  background: var(--bg3); border: 1px solid var(--border); color: var(--textwh);
  cursor: pointer; transition: all .2s;
}
.btn-sm:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); box-shadow: var(--shadow-c); }
.btn-sm:disabled { opacity: 0.4; cursor: not-allowed; }

.xterm-container {
  flex: 1;
  overflow: hidden;
  padding: 8px;
  background: var(--bg);
}
:deep(.xterm-viewport) {
  background: var(--bg) !important;
}
</style>
