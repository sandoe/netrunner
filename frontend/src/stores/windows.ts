import { defineStore } from 'pinia'

export interface WindowState {
  id: string
  title: string
  component: string // Either 'RouterView' or a custom component name like 'NodePanel'
  icon?: string
  width: number
  height: number
  x: number
  y: number
  zIndex: number
  isMinimized: boolean
  isMaximized: boolean
  props?: Record<string, any>
}

export const useWindowStore = defineStore('windows', {
  state: () => ({
    windows: [] as WindowState[],
    nextZIndex: 100,
  }),
  getters: {
    activeWindows: (state) => state.windows.filter(w => !w.isMinimized),
  },
  actions: {
    openWindow(win: Partial<WindowState>) {
      // Check if a window with this id already exists
      const existing = this.windows.find(w => w.id === win.id)
      if (existing) {
        this.focusWindow(existing.id)
        if (existing.isMinimized) {
          existing.isMinimized = false
        }
        return
      }

      const defaultW = Math.min(1200, window.innerWidth * 0.85)
      const defaultH = Math.min(850, window.innerHeight * 0.85)
      const defaultX = Math.max(20, (window.innerWidth - defaultW) / 2) + (this.windows.length * 30)
      const defaultY = Math.max(20, (window.innerHeight - defaultH) / 2) + (this.windows.length * 30)

      const newWin: WindowState = {
        id: win.id || `win_${Date.now()}`,
        title: win.title || 'Window',
        component: win.component || 'div',
        icon: win.icon || '📄',
        width: win.width || defaultW,
        height: win.height || defaultH,
        x: win.x || defaultX,
        y: win.y || defaultY,
        zIndex: this.nextZIndex++,
        isMinimized: false,
        isMaximized: false,
        props: win.props || {}
      }
      this.windows.push(newWin)
    },
    closeWindow(id: string) {
      this.windows = this.windows.filter(w => w.id !== id)
    },
    focusWindow(id: string) {
      const win = this.windows.find(w => w.id === id)
      if (win && win.zIndex < this.nextZIndex - 1) {
        win.zIndex = this.nextZIndex++
      }
    },
    minimizeWindow(id: string) {
      const win = this.windows.find(w => w.id === id)
      if (win) {
        win.isMinimized = true
      }
    },
    toggleMaximize(id: string) {
      const win = this.windows.find(w => w.id === id)
      if (win) {
        win.isMaximized = !win.isMaximized
        this.focusWindow(id)
      }
    },
    updatePosition(id: string, x: number, y: number) {
      const win = this.windows.find(w => w.id === id)
      if (win) {
        win.x = x
        win.y = y
      }
    },
    updateSize(id: string, width: number, height: number) {
      const win = this.windows.find(w => w.id === id)
      if (win) {
        win.width = width
        win.height = height
      }
    }
  }
})
