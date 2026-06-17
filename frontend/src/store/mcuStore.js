import { reactive, ref } from 'vue';

export const mcuState = reactive({
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
});

export const mcuMethods = {
  authHeaders() {
    const token = localStorage.getItem('nr_token');
    return { 'Authorization': `Bearer ${token}` };
  },
  getFullPath(filename) {
    const p = mcuState.currentPath.replace(/\/+$/, '');
    return p === '' ? '/' + filename : p + '/' + filename;
  }
};
