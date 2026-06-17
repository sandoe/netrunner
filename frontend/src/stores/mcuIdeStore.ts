import { defineStore } from 'pinia'

export const useMcuIdeStore = defineStore('mcuIde', {
  state: () => ({
    mcuFiles: [],
    currentPath: '/',
    activeFile: '',
    fileContent: 'print("Hello NeoThonny!")',
    fileLanguage: 'python',
    loading: false,
    error: '',
    success: '',
    aiExplanation: '',
    
    // Flash state
    flashFile: null,
    flashTool: 'esptool',
    flashChip: 'esp32',
    flashOffset: '0x1000',
    autoFirmware: '',
    sudoPassword: '',
    showFlashMenu: false
  }),
  actions: {
    authHeaders() {
      const token = localStorage.getItem('nr_token')
      return { 'Authorization': `Bearer ${token}` }
    },
    getFullPath(filename: string) {
      const p = this.currentPath.replace(/\/+$/, '')
      return p === '' ? '/' + filename : p + '/' + filename
    }
  }
})
