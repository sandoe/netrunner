<template>
  <div class="terminal-wrap" ref="wrapEl" @click="focusTerminal">
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
        <button @click="reconnect" :disabled="connecting" class="btn-sm" tabindex="-1">
          {{ connecting ? 'ESTABLISHING...' : connected ? 'RECONNECT' : 'CONNECT' }}
        </button>
        <button @click="clearTerminal" class="btn-sm" tabindex="-1">CLEAR</button>
      </div>
    </div>
    <div ref="termEl" class="xterm-container" @click="focusTerminal" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick, onActivated } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import { wsTerminalUrl } from '@/api/client'
import type { NrNode } from '@/types'

const props = defineProps<{ node: NrNode | null; active?: boolean }>()

const wrapEl    = ref<HTMLElement>()
const termEl    = ref<HTMLElement>()
const connected = ref(false)
const connecting = ref(false)

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null
let outputBuffer = ''
let bufferFlushFrame: number | null = null
let focusTimer: ReturnType<typeof setTimeout> | null = null
let fitFrame: number | null = null
let fitSoonTimer: ReturnType<typeof setTimeout> | null = null
let fitTries = 0

function flushBuffer() {
  if (outputBuffer && term) {
    term.write(outputBuffer)
    outputBuffer = ''
  }
  bufferFlushFrame = null
}

function initTerminal() {
  if (!termEl.value) return
  if (term) {
    term.dispose()
    term = null
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
    cursorInactiveStyle: 'block',
    scrollback: 10000,
    allowProposedApi: true,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())
  term.open(termEl.value)

  // Guard against xterm internal Viewport.syncScrollArea throwing after dispose during fake timer advances
  try {
    const core = (term as any)._core
    if (core && core.viewport) {
      const vp = core.viewport
      const origSync = vp.syncScrollArea
      if (typeof origSync === 'function') {
        vp.syncScrollArea = function (...args: any[]) {
          if (!this._renderService || core._isDisposed) return
          try {
            return origSync.apply(this, args)
          } catch {
            /* ignore disposed syncScrollArea */
          }
        }
      }
    }
  } catch {
    /* ignore */
  }

  // Fit only once the container actually has dimensions — fitting synchronously
  // on mount (before flex layout settles) yields 0 rows and hides the cursor.
  fitSoon()

  // Clicking anywhere in the padded container should focus the terminal,
  // otherwise the block cursor renders as inactive/invisible.
  termEl.value.addEventListener('mousedown', () => {
    if (term) term.focus()
  })

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

  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  resizeObserver = new ResizeObserver(() => fitSoon())
  if (wrapEl.value) {
    resizeObserver.observe(wrapEl.value)
  }
}

function focusTerminal() {
  if (!term || !termEl.value) return

  if (focusTimer) {
    clearTimeout(focusTimer)
    focusTimer = null
  }

  // Use a longer delay to ensure all Vue renders, layout calculations,
  // and browser mouseup/click focus events have completely finished.
  focusTimer = setTimeout(() => {
    focusTimer = null
    if (!term || !termEl.value) return

    // Fit first
    try {
      if (fitAddon && termEl.value.clientWidth >= 10) {
        fitAddon.fit()
      }
    } catch {
      /* ignore */
    }

    // Then focus
    term.focus()
  }, 250) as unknown as ReturnType<typeof setTimeout>
}

// Fit + focus on the next frame, but only when the element has a real size.
// Retries briefly while the layout is still 0×0 (e.g. tab just became visible).
function fitSoon() {
  if (fitFrame) {
    cancelAnimationFrame(fitFrame)
    fitFrame = null
  }
  fitFrame = requestAnimationFrame(() => {
    fitFrame = null
    const el = termEl.value
    if (!term || !fitAddon || !el) return

    if (el.clientWidth < 10 || el.clientHeight < 10) {
      if (fitTries < 20) {
        fitTries++
        if (fitSoonTimer) {
          clearTimeout(fitSoonTimer)
        }
        fitSoonTimer = setTimeout(fitSoon, 50) as unknown as ReturnType<typeof setTimeout>
      }
      return
    }

    fitTries = 0
    try {
      if (term && fitAddon) {
        fitAddon.fit()
      }
    } catch {
      /* ignore */
    }
    if (term) {
      term.focus()
    }
  })
}

function connect(nodeId: string) {
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  term?.reset()
  connecting.value = true
  connected.value  = false

  const tryConnect = () => {
    if (!termEl.value || termEl.value.clientWidth < 10) {
      setTimeout(tryConnect, 50)
      return
    }

    try {
      if (fitAddon) fitAddon.fit()
    } catch {}

    const cols = term?.cols || 120
    const rows = term?.rows || 40
    ws = new WebSocket(`${wsTerminalUrl(nodeId)}&cols=${cols}&rows=${rows}`)

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'output') {
          outputBuffer += msg.data
          if (!bufferFlushFrame) {
            bufferFlushFrame = requestAnimationFrame(flushBuffer)
          }
        } else if (msg.type === 'status') {
          connected.value  = msg.connected
          connecting.value = false
          if (msg.connected) {
            term?.write('\r\n\x1b[1;32m[SYSTEM] Neural link established.\x1b[0m\r\n')
            fitSoon()
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

  tryConnect()
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
  } else {
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
    connecting.value = false
  }
})

watch(() => props.active, (val) => {
  if (val) {
    focusTerminal()
  }
})

onActivated(() => {
  focusTerminal()
})

onMounted(() => {
  initTerminal()
  if (props.node) connect(props.node.id)
  focusTerminal()
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (focusTimer) {
    clearTimeout(focusTimer)
    focusTimer = null
  }
  if (fitSoonTimer) {
    clearTimeout(fitSoonTimer)
    fitSoonTimer = null
  }
  if (fitFrame) {
    cancelAnimationFrame(fitFrame)
    fitFrame = null
  }
  if (bufferFlushFrame) {
    cancelAnimationFrame(bufferFlushFrame)
    bufferFlushFrame = null
  }
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  if (term) {
    term.dispose()
    term = null
  }
  fitAddon = null
})

defineExpose({
  focus: focusTerminal,
  fit: fitSoon
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
