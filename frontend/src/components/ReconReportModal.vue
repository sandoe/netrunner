<template>
  <div class="modal-overlay" v-if="show" @click.self="close">
    <div class="modal-content recon-modal">
      <div class="modal-header">
        <h2>🌐 NETWORK RECON REPORT</h2>
        <button class="btn-close" @click="close">X</button>
      </div>
      <div class="modal-body">

        <!-- Module Selection State -->
        <div v-if="!loading && !report && !error" class="config-state">
          <div class="cyber-guide" style="margin-bottom: 16px; font-size: 13px; border-left: 3px solid var(--purple); padding-left: 10px; background: rgba(187, 134, 252, 0.05);">
            <strong style="color: var(--purple);">🎓 Cyber Guide: Reconnaissance (OSINT & Active)</strong><br/>
            <span style="color: #ccc;">Recon (Rekognoscering) er første fase i ethvert hacker-angreb eller penetrationstest (Kill Chain). Angriberen forsøger at samle så meget information om målet som muligt: Hvilke operativsystemer kører de? Hvilke netværksporte er åbne? Hvilke versioner af software er installeret? Målet er at finde en svaghed, før man angriber.</span>
          </div>
          <p class="config-title">Select modules to include in the intelligence report:</p>
          <div class="module-options">
            <label class="module-label">
              <input type="checkbox" value="network" v-model="selectedModules">
              <span>Network Topology (Interfaces, ARP, Routing)</span>
            </label>
            <label class="module-label">
              <input type="checkbox" value="docker" v-model="selectedModules">
              <span>Docker & Containers</span>
            </label>
            <label class="module-label">
              <input type="checkbox" value="services" v-model="selectedModules">
              <span>Running Services (systemd/rc)</span>
            </label>
            <label class="module-label">
              <input type="checkbox" value="system" v-model="selectedModules">
              <span>System & Performance (CPU, RAM, Disk)</span>
            </label>
            <label class="module-label">
              <input type="checkbox" value="vulnerabilities" v-model="selectedModules">
              <span>Vulnerability Indicators (sudoers, passwd, cron)</span>
            </label>
          </div>
        </div>

        <!-- Loading State -->
        <div v-else-if="loading" class="loading-state">
          <span class="pulse-dot"></span> Generating Recon Report (this may take up to 20 seconds for traceroutes)...
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="error-state">
          {{ error }}
        </div>

        <!-- Report State -->
        <div v-else class="report-content parsed-report">
          <div v-for="sec in parsedReport" :key="sec.title" class="report-section glass-panel">
            <h3>{{ sec.title }}</h3>
            <pre class="terminal-output"><code>{{ sec.content.trim() || 'No data available' }}</code></pre>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button v-if="!loading && !report && !error" class="btn-primary" @click="generate" :disabled="selectedModules.length === 0">
          GENERATE REPORT
        </button>
        <template v-if="report">
          <div class="footer-actions">
            <span v-if="saveSuccess" class="success-text">Saved to DB!</span>
            <span v-else-if="saving" class="saving-text">Saving...</span>
            <button class="btn-secondary" @click="saveToDatabase" :disabled="saving || saveSuccess">
              💾 SAVE TO DATABASE
            </button>
            <button class="btn-secondary" @click="downloadReport('txt')">TXT</button>
            <button class="btn-secondary" @click="downloadReport('pdf')">PDF</button>
            <button class="btn-secondary" @click="downloadReport('doc')">WORD</button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = defineProps<{
  show: boolean
  loading: boolean
  error: string
  report: string
}>()

const emit = defineEmits(['close', 'generate'])

const selectedModules = ref<string[]>(['network', 'system'])
const saving = ref(false)
const saveSuccess = ref(false)

const parsedReport = computed(() => {
  if (!props.report) return []
  const lines = props.report.split('\n')
  const sections: { title: string, content: string }[] = []
  let currentSection: { title: string, content: string } | null = null

  for (let line of lines) {
    if (line === '=== RECON_REPORT_START ===' || line === '=== RECON_REPORT_END ===') continue
    if (line.startsWith('--- ') && line.endsWith(' ---')) {
       if (currentSection) sections.push(currentSection)
       currentSection = { title: line.replace(/---/g, '').trim(), content: '' }
    } else if (currentSection) {
       currentSection.content += line + '\n'
    }
  }
  if (currentSection) sections.push(currentSection)
  return sections
})

watch(() => props.show, (newVal) => {
  if (!newVal) {
    // Reset selection when modal closes (optional)
  }
})

function close() {
  emit('close')
}

function generate() {
  emit('generate', selectedModules.value)
}

const saveToDatabase = async () => {
  saving.value = true
  saveSuccess.value = false
  try {
    const res = await fetch('/api/recon/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        report: props.report,
        modules: selectedModules.value,
        timestamp: new Date().toISOString()
      })
    })
    if (res.ok) {
      saveSuccess.value = true
      setTimeout(() => { saveSuccess.value = false }, 3000)
    } else {
      console.error('Failed to save to database')
    }
  } catch (err) {
    console.error('Error saving to DB:', err)
  } finally {
    saving.value = false
  }
}

const downloadReport = async (format: string = 'txt') => {
  let content = props.report;
  let extension = format;
  let mimeType = 'text/plain';

  if (format === 'pdf') {
    // Basic mock for PDF structure
    mimeType = 'application/pdf';
    content = `%PDF-1.4\n%Mock PDF\n\n${props.report}`;
  } else if (format === 'doc') {
    // Basic mock for DOC
    mimeType = 'application/msword';
  }

  const filename = `recon_report_${new Date().toISOString().slice(0,10)}.${extension}`;

  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [{
          description: `${format.toUpperCase()} Document`,
          accept: { [mimeType]: [`.${extension}`] },
        }],
      });
      const writable = await handle.createWritable();
      await writable.write(content);
      await writable.close();
      return;
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error(err);
      }
      return;
    }
  }

  // Fallback for browsers that don't support showSaveFilePicker
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}
.recon-modal {
  width: 900px;
  max-width: 95vw;
  background: rgba(15, 20, 30, 0.95);
  border: 1px solid #00ff9d;
  box-shadow: 0 0 30px rgba(0, 255, 157, 0.2);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}
.modal-header {
  padding: 15px 20px;
  background: rgba(0, 255, 157, 0.1);
  border-bottom: 1px solid rgba(0, 255, 157, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #00ff9d;
  letter-spacing: 2px;
}
.btn-close {
  background: transparent;
  color: #ff3366;
  border: 1px solid #ff3366;
  padding: 5px 10px;
  cursor: pointer;
  font-weight: bold;
}
.btn-close:hover {
  background: #ff3366;
  color: #fff;
}
.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}
.loading-state, .error-state {
  text-align: center;
  padding: 40px;
  font-size: 1.1rem;
}
.error-state {
  color: #ff3366;
}
.pulse-dot {
  display: inline-block;
  width: 10px; height: 10px;
  background: #00ff9d;
  border-radius: 50%;
  animation: pulse 1s infinite alternate;
  margin-right: 10px;
}
@keyframes pulse {
  0% { opacity: 0.2; }
  100% { opacity: 1; }
}
.terminal-output {
  background: #000;
  color: #00ff9d;
  padding: 20px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'Courier New', Courier, monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.4;
  margin: 0;
}
.parsed-report {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.report-section {
  padding: 15px;
}
.report-section h3 {
  margin: 0 0 10px 0;
  color: #00ff9d;
  font-size: 1.1rem;
  border-bottom: 1px solid rgba(0, 255, 157, 0.2);
  padding-bottom: 5px;
}
.report-section .terminal-output {
  padding: 10px;
  background: rgba(0, 0, 0, 0.4);
}
.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: flex-end;
}
.btn-primary {
  background: rgba(0, 255, 157, 0.2);
  color: #00ff9d;
  border: 1px solid #00ff9d;
  padding: 8px 16px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}
.btn-primary:hover:not(:disabled) {
  background: #00ff9d;
  color: #000;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: #666;
  color: #666;
}
.footer-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.success-text {
  color: #00ff9d;
  font-size: 0.9rem;
  margin-right: 10px;
}
.saving-text {
  color: #ffcc00;
  font-size: 0.9rem;
  margin-right: 10px;
}
.btn-secondary {
  background: transparent;
  color: #00ff9d;
  border: 1px solid rgba(0, 255, 157, 0.5);
  padding: 8px 16px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}
.btn-secondary:hover:not(:disabled) {
  background: rgba(0, 255, 157, 0.1);
  border-color: #00ff9d;
}
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.config-state {
  padding: 10px;
}
.config-title {
  color: #00ff9d;
  font-size: 1.1rem;
  margin-bottom: 20px;
  letter-spacing: 1px;
}
.module-options {
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.module-label {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  color: #ccc;
  font-family: 'JetBrains Mono', monospace;
  transition: color 0.2s;
}
.module-label:hover {
  color: #fff;
}
.module-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: #ff3366;
  cursor: pointer;
}
</style>
