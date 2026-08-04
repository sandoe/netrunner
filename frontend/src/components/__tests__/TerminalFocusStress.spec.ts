import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { Terminal } from '@xterm/xterm'
import TerminalComponent from '../Terminal.vue'
import ShellPanelComponent from '../ShellPanel.vue'

// Polyfill ResizeObserver for JSDOM
if (!global.ResizeObserver) {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as any
}

// Polyfill matchMedia for JSDOM
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

// Override clientWidth and clientHeight for JSDOM
let mockElementWidth = 800
Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
  configurable: true,
  get() { return mockElementWidth }
})
Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
  configurable: true,
  get() { return 600 }
})

// Mock WebSocket
class MockWebSocket {
  url: string
  readyState: number = 1 // OPEN
  onopen: any = null
  onmessage: any = null
  onerror: any = null
  onclose: any = null
  static instances: MockWebSocket[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send(data: string) {}
  close() {
    this.readyState = 3 // CLOSED
    if (this.onclose) this.onclose()
  }
}

(global as any).WebSocket = MockWebSocket

describe('Terminal Focus & Propagation Stress Tests', () => {
  let focusSpy: any
  let disposeSpy: any

  beforeEach(() => {
    mockElementWidth = 800
    vi.useFakeTimers()
    MockWebSocket.instances = []
    focusSpy = vi.spyOn(Terminal.prototype, 'focus')
    disposeSpy = vi.spyOn(Terminal.prototype, 'dispose')
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
    localStorage.clear()
  })

  describe('1. Null Node Props Handling', () => {
    it('handles initial mount with null node prop without crashing', async () => {
      const wrapper = mount(TerminalComponent, {
        props: { node: null, active: true }
      })
      await nextTick()
      vi.advanceTimersByTime(100)

      expect(wrapper.find('.term-node-name').text()).toBe('')
      expect(wrapper.find('.term-status').text()).toBe('DISCONNECTED')
      expect(focusSpy).toHaveBeenCalled()
      wrapper.unmount()
    })

    it('cleans up WebSocket when node prop transitions from valid node to null', async () => {
      const wrapper = mount(TerminalComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()
      expect(MockWebSocket.instances.length).toBe(1)
      const wsInstance = MockWebSocket.instances[0]
      const closeSpy = vi.spyOn(wsInstance, 'close')

      // Transition node prop to null
      await wrapper.setProps({ node: null })
      await nextTick()

      // VERIFY if websocket connection was closed when node became null
      expect(closeSpy).toHaveBeenCalled()
      wrapper.unmount()
    })

    it('handles reconnect button click when node is null', async () => {
      const wrapper = mount(TerminalComponent, {
        props: { node: null, active: true }
      })
      await nextTick()
      const reconnectBtn = wrapper.findAll('button').find(b => b.text().includes('CONNECT'))
      expect(reconnectBtn).toBeDefined()

      // Click reconnect when node is null
      await reconnectBtn?.trigger('click')
      await nextTick()
      expect(MockWebSocket.instances.length).toBe(0)
      wrapper.unmount()
    })
  })

  describe('2. Rapid Mode Switching in ShellPanel.vue', () => {
    it('handles rapid switching between interactive and script mode', async () => {
      const wrapper = mount(ShellPanelComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()
      vi.advanceTimersByTime(100)

      const modeBtns = wrapper.findAll('.mode-btn')
      const interactiveBtn = modeBtns[0]
      const scriptBtn = modeBtns[1]

      // Switch rapidly back and forth 10 times
      for (let i = 0; i < 10; i++) {
        await scriptBtn.trigger('click')
        await nextTick()
        await interactiveBtn.trigger('click')
        await nextTick()
      }

      focusSpy.mockClear()
      vi.advanceTimersByTime(300)

      // Should focus terminal after returning to interactive mode
      expect(focusSpy).toHaveBeenCalled()
      wrapper.unmount()
    })

    it('does not crash if mode switches to script while focus timeout is pending', async () => {
      const wrapper = mount(ShellPanelComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()
      const modeBtns = wrapper.findAll('.mode-btn')

      // Click interactive, which triggers watch(mode) -> terminalRef.value?.focus() -> setTimeout(250)
      await modeBtns[0].trigger('click')
      await nextTick()

      // Immediately switch to script before the 250ms timer fires
      await modeBtns[1].trigger('click')
      await nextTick()

      // Advance timers to trigger the pending focus callback
      expect(() => {
        vi.advanceTimersByTime(300)
      }).not.toThrow()

      wrapper.unmount()
    })
  })

  describe('3. Tab Activation & Focus Propagation State Changes', () => {
    it('triggers focus when active prop becomes true', async () => {
      const wrapper = mount(TerminalComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: false
        }
      })
      await nextTick()
      vi.advanceTimersByTime(100)
      focusSpy.mockClear()

      await wrapper.setProps({ active: true })
      await nextTick()
      vi.advanceTimersByTime(300)

      expect(focusSpy).toHaveBeenCalled()
      wrapper.unmount()
    })

    it('does not attempt focus if active becomes false', async () => {
      const wrapper = mount(TerminalComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()
      vi.advanceTimersByTime(100)
      focusSpy.mockClear()

      await wrapper.setProps({ active: false })
      await nextTick()
      vi.advanceTimersByTime(100)

      expect(focusSpy).not.toHaveBeenCalled()
      wrapper.unmount()
    })
  })

  describe('4. Module-Scoped State & Retry Leaks', () => {
    it('does not bleed fitTries counter across hidden terminal instances', async () => {
      // 1. Mount terminal 1 in hidden container (clientWidth = 0)
      mockElementWidth = 0
      const wrapper1 = mount(TerminalComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()
      // Run timers so fitTries increments to 20
      vi.advanceTimersByTime(1200)

      // 2. Now mount terminal 2 while hidden initially
      const wrapper2 = mount(TerminalComponent, {
        props: {
          node: { id: 'node-2', name: 'Node 2', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()

      // Make terminal 2 visible after 100ms
      mockElementWidth = 800
      vi.advanceTimersByTime(100)

      // Terminal 2 should be able to retry and fit once visible!
      expect(focusSpy).toHaveBeenCalled()

      wrapper1.unmount()
      wrapper2.unmount()
    })
  })

  describe('5. Unmount & Race Condition Safety', () => {
    it('handles unmount while fitSoon/focusTerminal timers are pending', async () => {
      const wrapper = mount(TerminalComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()

      // Unmount immediately while initial timers might be queued
      wrapper.unmount()

      expect(() => {
        try {
          vi.advanceTimersByTime(1000)
        } catch (e: any) {
          const t = (wrapper.vm as any)
          console.log('Error caught:', e)
          throw e
        }
      }).not.toThrow()
    })

    it('handles output buffer flushing when unmounted before frame callback', async () => {
      const wrapper = mount(TerminalComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()
      const wsInstance = MockWebSocket.instances[0]

      // Receive message from WS (buffers data into outputBuffer and schedules requestAnimationFrame(flushBuffer))
      wsInstance.onmessage({ data: JSON.stringify({ type: 'output', data: 'hello world' }) })

      // Immediately unmount before rAF flushes
      wrapper.unmount()

      expect(() => {
        vi.advanceTimersByTime(100)
      }).not.toThrow()
    })

    it('disposes terminal and closes websocket on unmount', async () => {
      const wrapper = mount(TerminalComponent, {
        props: {
          node: { id: 'node-1', name: 'Node 1', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
          active: true
        }
      })
      await nextTick()
      expect(MockWebSocket.instances.length).toBe(1)
      const wsInstance = MockWebSocket.instances[0]
      const closeSpy = vi.spyOn(wsInstance, 'close')

      wrapper.unmount()

      expect(disposeSpy).toHaveBeenCalled()
      expect(closeSpy).toHaveBeenCalled()
    })
  })
})
