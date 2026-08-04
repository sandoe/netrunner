import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { Terminal } from '@xterm/xterm'
import TerminalComponent from '../Terminal.vue'

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
Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
  configurable: true,
  get() { return 800 }
})
Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
  configurable: true,
  get() { return 600 }
})

class MockWebSocket {
  static readonly OPEN = 1
  static readonly CLOSED = 3

  readyState = MockWebSocket.OPEN
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null

  constructor(public readonly url: string) {}

  send() {}

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  }
}

describe('Terminal.vue', () => {
  let focusSpy: any

  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', MockWebSocket)
    focusSpy = vi.spyOn(Terminal.prototype, 'focus')
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('calls Terminal.prototype.focus on mount', async () => {
    const wrapper = mount(TerminalComponent, {
      props: {
        node: { id: 'node-1', name: 'Test Node', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' }
      }
    })

    await nextTick()
    vi.advanceTimersByTime(100)

    expect(focusSpy).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('calls Terminal.prototype.focus when active prop becomes true', async () => {
    const wrapper = mount(TerminalComponent, {
      props: {
        node: { id: 'node-1', name: 'Test Node', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' },
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

  it('calls Terminal.prototype.focus when mousedown occurs on the terminal container', async () => {
    const wrapper = mount(TerminalComponent, {
      props: {
        node: { id: 'node-1', name: 'Test Node', host: '127.0.0.1', port: 22, transport: 'ssh', device_type: 'linux' }
      }
    })

    await nextTick()
    vi.advanceTimersByTime(100)
    focusSpy.mockClear()

    const termContainer = wrapper.find('.xterm-container')
    expect(termContainer.exists()).toBe(true)

    await termContainer.trigger('mousedown')

    expect(focusSpy).toHaveBeenCalled()
    wrapper.unmount()
  })
})
