<template>
  <div class="ai-sidebar" :class="{ open: isOpen }" :style="{ width: sidebarWidth + 'px', right: isOpen ? '0' : `-${sidebarWidth}px` }" role="dialog" aria-label="AI Assistant Sidebar">
    <div class="ai-resizer" 
         role="separator" 
         tabindex="0" 
         aria-orientation="vertical" 
         :aria-valuenow="sidebarWidth" 
         :aria-valuemin="Math.min(300, windowWidth)" 
         :aria-valuemax="windowWidth"
         @mousedown="startResize" 
         @touchstart="startResizeTouch"
         @dblclick="resetWidth"
         @keydown="handleResizerKeydown">
    </div>
    <button class="ai-toggle" @click="isOpen = !isOpen">
      <span class="ai-toggle-icon" aria-hidden="true">🤖</span>
      <span class="ai-toggle-text">AI ASSISTANT</span>
    </button>

    <div class="ai-content">
      <div class="ai-header">
        <div class="ai-title">NEURAL LINK v1.0 (TERMINAL MODE)</div>
        
        <div class="ai-context-toggle">
          <label title="When enabled, your clicks and page views are logged to the AI">
            <input type="checkbox" v-model="contextEnabled" @change="toggleContext" />
            <span class="toggle-text">SHARE UI CONTEXT</span>
          </label>
        </div>

        <div class="ai-status" :class="connected ? 'ok' : 'off'">
          {{ connected ? 'CONNECTED' : 'DISCONNECTED' }}
        </div>
        <button class="btn-close" aria-label="Close AI Assistant" @click="isOpen = false"><span aria-hidden="true">×</span></button>
      </div>

      <div class="ai-terminal-wrap" ref="wrapEl">
        <div v-if="copyToast" class="ai-toast">{{ copyToast }}</div>
        <div ref="termEl" class="xterm-container" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import { wsBase, wsTokenParam, isUiContextEnabled, setUiContextEnabled } from '@/api/client'

const isOpen = ref(false)
const connected = ref(false)
const wrapEl = ref<HTMLElement>()
const termEl = ref<HTMLElement>()
const windowWidth = ref(window.innerWidth)
const sidebarWidth = ref(Math.min(500, window.innerWidth))
const contextEnabled = ref(isUiContextEnabled())

function updateWindowWidth() {
  windowWidth.value = window.innerWidth
  if (sidebarWidth.value > windowWidth.value) {
    sidebarWidth.value = windowWidth.value
  }
}

function resetWidth() {
  sidebarWidth.value = Math.min(500, window.innerWidth)
}

function toggleContext() {
  setUiContextEnabled(contextEnabled.value)
}

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

function initTerminal() {
  if (!termEl.value) return
  if (term) term.dispose()

  const styles = getComputedStyle(document.body)
  const getVar = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback

  term = new Terminal({
    theme: {
      background: getVar('--bg', '#020408'),
      foreground: getVar('--text', '#00ff9d'),
      cursor: getVar('--cyan', '#00e5ff'),
      cursorAccent: getVar('--bg', '#020408'),
      black: '#05080f',
      brightBlack: '#1a2540',
      red: getVar('--pink', '#ff2d6e'),
      brightRed: getVar('--pink', '#ff2d6e'),
      green: getVar('--green', '#00ff9d'),
      brightGreen: getVar('--green', '#00ff9d'),
      yellow: '#ffbe0b',
      brightYellow: '#ffbe0b',
      blue: getVar('--cyan', '#00e5ff'),
      brightBlue: getVar('--cyan', '#00e5ff'),
      magenta: '#a855f7',
      brightMagenta: '#a855f7',
      cyan: getVar('--cyan', '#00e5ff'),
      brightCyan: getVar('--cyan', '#00e5ff'),
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

  const copyToast = ref('')

  function showToast(msg: string) {
    copyToast.value = msg
    setTimeout(() => { copyToast.value = '' }, 2000)
  }

  async function safeCopy(text: string) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      } else {
        const el = document.createElement('textarea')
        el.value = text
        document.body.appendChild(el)
        el.select()
        document.execCommand('copy')
        document.body.removeChild(el)
        term?.focus() // Return focus to terminal
      }
      showToast('Copied!')
    } catch (err) {
      console.error('Copy failed:', err)
      showToast('Copy failed')
    }
  }

  // Handle Copy/Paste (Ctrl+C, Ctrl+V)
  term.attachCustomKeyEventHandler((e) => {
    if ((e.ctrlKey || e.metaKey) && e.code === 'KeyC' && e.type === 'keydown') {
      if (term!.hasSelection()) {
        safeCopy(term!.getSelection())
        // Do not clear selection, so user doesn't think it got deleted
        return false // Prevent sending SIGINT
      }
    }
    if ((e.ctrlKey || e.metaKey) && e.code === 'KeyV' && e.type === 'keydown') {
      if (navigator.clipboard && navigator.clipboard.readText) {
        navigator.clipboard.readText().then(text => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'input', data: text }))
          }
        }).catch(() => {})
      }
      return false
    }
    return true
  })

  // Right-click to Copy (if selection) or Paste
  termEl.value.addEventListener('contextmenu', (e) => {
    e.preventDefault()
    if (term!.hasSelection()) {
      safeCopy(term!.getSelection())
    } else {
      if (navigator.clipboard && navigator.clipboard.readText) {
        navigator.clipboard.readText().then(text => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'input', data: text }))
          }
        }).catch(() => {})
      }
    }
  })

  resizeObserver = new ResizeObserver(() => fitSoon())
  resizeObserver.observe(wrapEl.value!)
}

let isResizing = false

function startResize(e: MouseEvent) {
  isResizing = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.userSelect = 'none'
}

function startResizeTouch(e: TouchEvent) {
  isResizing = true
  document.addEventListener('touchmove', onResize, { passive: false })
  document.addEventListener('touchend', stopResizeTouch)
  document.body.style.userSelect = 'none'
}

function onResize(e: MouseEvent | TouchEvent) {
  if (!isResizing) return
  let clientX = e instanceof MouseEvent ? e.clientX : e.touches[0].clientX
  let newWidth = window.innerWidth - clientX
  let minWidth = Math.min(300, window.innerWidth)
  let maxWidth = window.innerWidth
  if (newWidth < minWidth) newWidth = minWidth
  if (newWidth > maxWidth) newWidth = maxWidth
  sidebarWidth.value = newWidth
}

function stopResize() {
  isResizing = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.userSelect = ''
  fitSoon()
}

function stopResizeTouch() {
  isResizing = false
  document.removeEventListener('touchmove', onResize)
  document.removeEventListener('touchend', stopResizeTouch)
  document.body.style.userSelect = ''
  fitSoon()
}

function handleResizerKeydown(e: KeyboardEvent) {
  let step = 20
  if (e.key === 'ArrowLeft') {
    sidebarWidth.value = Math.min(window.innerWidth, sidebarWidth.value + step)
  } else if (e.key === 'ArrowRight') {
    sidebarWidth.value = Math.max(Math.min(300, window.innerWidth), sidebarWidth.value - step)
  }
}

let fitTries = 0
function fitSoon() {
  requestAnimationFrame(() => {
    const el = termEl.value
    if (!term || !fitAddon || !el) return
    if (el.clientWidth < 10 || el.clientHeight < 10) {
      if (fitTries++ < 20) setTimeout(fitSoon, 50)
      return
    }
    fitTries = 0
    try { fitAddon.fit() } catch { /* ignore */ }
    if (isOpen.value) term.focus()
  })
}

function connectWS() {
  if (ws) {
    ws.onclose = null
    ws.close()
  }
  
  term?.reset()
  connected.value = false
  
  // Use current host for websocket
  const wsUrl = `${wsBase()}/api/ai/ws${wsTokenParam()}`
  
  ws = new WebSocket(wsUrl)
  
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.type === 'output') {
        term?.write(msg.data)
      } else if (msg.type === 'status') {
        connected.value = msg.connected
        if (msg.connected) {
          fitSoon()
        }
      } else if (msg.type === 'error') {
        term?.write(`\r\n\x1b[1;31m[ERROR] ${msg.data}\x1b[0m\r\n`)
      }
    } catch {
      term?.write(ev.data)
    }
  }

  ws.onopen = () => {
    term?.write(`\r\n\x1b[1;36m[SYSTEM] Starting AI Terminal Session...\x1b[0m\r\n`)
  }

  ws.onerror = () => {
    term?.write('\r\n\x1b[1;31m[SYSTEM] WebSocket protocol error.\x1b[0m\r\n')
    connected.value = false
  }

  ws.onclose = () => {
    term?.write('\r\n\x1b[1;31m[SYSTEM] AI Session terminated.\x1b[0m\r\n')
    connected.value = false
  }
}

function disconnectWS() {
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  connected.value = false
}

watch(isOpen, (val) => {
  if (val) {
    nextTick(() => {
      if (!term) initTerminal()
      fitSoon()
      connectWS()
    })
  } else {
    disconnectWS()
  }
})

onMounted(() => {
  window.addEventListener('resize', updateWindowWidth)
  if (isOpen.value) {
    initTerminal()
    connectWS()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', updateWindowWidth)
  resizeObserver?.disconnect()
  disconnectWS()
  term?.dispose()
})
</script>

<style scoped>
.ai-sidebar {
  position: fixed;
  top: 0;
  height: 100vh;
  background: var(--bg2);
  border-left: 1px solid var(--border);
  z-index: 2000;
  transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 30px rgba(0,0,0,0.5);
}

.ai-resizer {
  position: absolute;
  left: -5px;
  top: 0;
  bottom: 0;
  width: 10px;
  cursor: ew-resize;
  z-index: 10;
  background: transparent;
  outline: none;
}

.ai-resizer::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 0;
  bottom: 0;
  width: 4px;
  background: transparent;
  transition: background 0.2s;
}

.ai-resizer:hover::after, .ai-resizer:active::after, .ai-resizer:focus-visible::after {
  background: var(--cyan);
  opacity: 0.8;
}

.ai-toggle {
  position: absolute;
  left: -40px;
  top: 50%;
  transform: translateY(-50%);
  background: var(--bg2);
  border: 1px solid var(--border);
  border-right: none;
  padding: 15px 10px;
  cursor: pointer;
  writing-mode: vertical-rl;
  border-radius: var(--r) 0 0 var(--r);
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 2px;
}

.ai-toggle:hover {
  background: var(--bg3);
  color: var(--green);
}

.ai-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.ai-header {
  padding: 15px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-title {
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--cyan);
  text-shadow: 0 0 8px var(--cyan);
}

.ai-status {
  font-family: var(--font-hd);
  font-size: 9px;
  letter-spacing: 1px;
}
.ai-status.ok { color: var(--green); text-shadow: 0 0 8px var(--green); }
.ai-status.off { color: var(--pink); text-shadow: 0 0 8px var(--pink); }

.ai-context-toggle {
  display: flex;
  align-items: center;
  font-family: var(--font-hd);
  font-size: 9px;
  letter-spacing: 1px;
  color: var(--text);
  margin-right: auto;
  margin-left: 20px;
}
.ai-context-toggle label {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 6px;
  transition: color 0.2s;
}
.ai-context-toggle label:hover {
  color: var(--cyan);
}
.ai-context-toggle input[type="checkbox"] {
  accent-color: var(--cyan);
  cursor: pointer;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text);
  font-size: 20px;
  cursor: pointer;
}

.ai-terminal-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  background: var(--bg);
  padding: 12px;
  box-sizing: border-box;
  overflow: hidden;
  min-height: 0;
}

.xterm-container {
  flex: 1;
  overflow: hidden;
  background: var(--bg);
  height: 100%;
  width: 100%;
}

.ai-toast {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 255, 157, 0.2);
  border: 1px solid var(--green);
  color: var(--green);
  padding: 8px 16px;
  border-radius: var(--r);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 1px;
  z-index: 1000;
  pointer-events: none;
  animation: fadeInOut 2s ease-in-out forwards;
}

@keyframes fadeInOut {
  0% { opacity: 0; transform: translate(-50%, -10px); }
  10% { opacity: 1; transform: translate(-50%, 0); }
  90% { opacity: 1; transform: translate(-50%, 0); }
  100% { opacity: 0; transform: translate(-50%, -10px); }
}

:deep(.xterm-viewport) {
  background: var(--bg) !important;
}

/* Focus indicators */
.ai-toggle:focus-visible,
.btn-close:focus-visible,
input[type="checkbox"]:focus-visible,
.ai-resizer:focus-visible {
  outline: 2px solid var(--cyan);
  outline-offset: 2px;
}
</style>
