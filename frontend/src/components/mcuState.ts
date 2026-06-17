import { reactive, ref } from 'vue';

export const sharedState = reactive({
  mcuFiles: [],
  currentPath: '/',
  activeFile: '',
  openFiles: [],
  fileContent: 'print("Hello NeoThonny!")',
  fileLanguage: 'python',
  loading: false,
  error: '',
  success: '',
  aiExplanation: '',
  sudoPassword: '',
  flashTool: 'esptool',
  flashChip: 'esp32',
  flashOffset: '0x1000',
  autoFirmware: '',
  showFlashMenu: false,
  isWorkspaceMode: false,
  workspaceTemplate: ''
});

export const flashFile = ref(null);

export const serialEvents = new EventTarget();
