<template>
  <div class="terminal-wrap" ref="wrapEl">
    <div class="terminal-toolbar">
      <span class="term-node-name">{{ node?.name }}</span>
      <span class="term-status" :class="connected ? 'ok' : 'off'">
        {{ connected ? 'connected' : 'disconnected' }}
      </span>
      <button @click="reconnect" :disabled="connecting" class="btn-sm">
        {{ connecting ? 'connecting…' : connected ? 'reconnect' : 'connect' }}
      </button>
      <button @click="clearTerminal" class="btn-sm">clear</button>
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
      background: '#0d1117',
      foreground: '#c9d1d9',
      cursor: '#58a6ff',
      black: '#0d1117',
      brightBlack: '#6e7681',
      red: '#ff7b72',
      brightRed: '#ff7b72',
      green: '#3fb950',
      brightGreen: '#3fb950',
      yellow: '#d29922',
      brightYellow: '#e3b341',
      blue: '#388bfd',
      brightBlue: '#58a6ff',
      magenta: '#bc8cff',
      brightMagenta: '#d2a8ff',
      cyan: '#39c5cf',
      brightCyan: '#56d364',
      white: '#b1bac4',
      brightWhite: '#f0f6fc',
    },
    fontFamily: '"Cascadia Code", "Fira Code", "JetBrains Mono", monospace',
    fontSize: 13,
    lineHeight: 1.3,
    cursorBlink: true,
    scrollback: 5000,
    allowProposedApi: true,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())
  term.open(termEl.value)
  fitAddon.fit()

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
          term?.write('\r\n\x1b[1;32m── connected ──\x1b[0m\r\n')
        }
      } else if (msg.type === 'error') {
        term?.write(`\r\n\x1b[1;31m[error] ${msg.data}\x1b[0m\r\n`)
        connecting.value = false
      }
    } catch {
      term?.write(ev.data)
    }
  }

  ws.onopen = () => {
    term?.write(`\r\n\x1b[90m── connecting to ${nodeId} …\x1b[0m\r\n`)
  }

  ws.onerror = () => {
    term?.write('\r\n\x1b[1;31m[WebSocket error]\x1b[0m\r\n')
    connected.value  = false
    connecting.value = false
  }

  ws.onclose = () => {
    if (connected.value) {
      term?.write('\r\n\x1b[90m── disconnected ──\x1b[0m\r\n')
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
  background: #0d1117;
}
.terminal-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
  font-size: 12px;
}
.term-node-name { font-weight: 600; color: #58a6ff; }
.term-status { padding: 1px 6px; border-radius: 10px; font-size: 11px; }
.term-status.ok  { background: #1f6823; color: #3fb950; }
.term-status.off { background: #441111; color: #f85149; }
.btn-sm {
  padding: 2px 8px; font-size: 11px; border-radius: 4px;
  background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
  cursor: pointer;
}
.btn-sm:hover:not(:disabled) { background: #30363d; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.xterm-container { flex: 1; overflow: hidden; padding: 4px 8px; }
</style>
