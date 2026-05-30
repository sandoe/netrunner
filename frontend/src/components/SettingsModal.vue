<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content cyber-glass">
      <div class="modal-header">
        <div class="modal-title">
          <span class="icon">⚙️</span>
          <span>SYSTEM SETTINGS</span>
        </div>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body-layout">
        <!-- Sidebar Navigation -->
        <div class="settings-nav">
          <button 
            v-for="tab in tabs" 
            :key="tab.id" 
            class="nav-tab" 
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            <span class="tab-icon">{{ tab.icon }}</span>
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </div>

        <!-- Main Content Area -->
        <div class="settings-content">
          <transition name="fade" mode="out-in">
            <!-- GENERAL / INTEGRATIONS TAB -->
            <div v-if="activeTab === 'general'" class="tab-pane" key="general">
              
              <div class="settings-card">
                <div class="card-header">
                  <div class="card-icon">🧠</div>
                  <div class="card-title">AI Assistant</div>
                </div>
                <div class="card-body">
                  <div class="form-group">
                    <label>OPENAI API KEY</label>
                    <div class="input-with-hint">
                      <input v-model="apiKey" type="password" placeholder="sk-..." class="form-input" />
                      <div class="hint" v-if="currentKeyMasked">
                        <span class="status-dot active"></span> Active Key: <span class="masked-text">{{ currentKeyMasked }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="settings-card">
                <div class="card-header">
                  <div class="card-icon">🛡️</div>
                  <div class="card-title">Cyber Threat Intelligence (CTI)</div>
                </div>
                <div class="card-body">
                  <div class="form-group">
                    <label>ALIENVAULT OTX API KEY</label>
                    <div class="input-with-hint">
                      <input v-model="alienvaultKey" type="password" placeholder="Enter API Key to disable Demo Mode" class="form-input" />
                      <div class="hint" v-if="currentAlienvaultMasked">
                        <span class="status-dot active"></span> Active Key: <span class="masked-text">{{ currentAlienvaultMasked }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="settings-card">
                <div class="card-header">
                  <div class="card-icon">🕸️</div>
                  <div class="card-title">GNS3 Hypervisor</div>
                </div>
                <div class="card-body">
                  <div class="form-group">
                    <label>SERVER ENDPOINT URL</label>
                    <input v-model="gns3Url" placeholder="http://127.0.0.1:3080" class="form-input" />
                  </div>
                </div>
              </div>

            </div>

            <!-- DATABASE TAB -->
            <div v-else-if="activeTab === 'database'" class="tab-pane" key="database">
              
              <div class="settings-card db-status-card">
                <div class="db-status-bar">
                  <div class="db-status-indicator">
                    <div class="db-lamp" :class="dbStatus"></div>
                    <div class="db-status-info">
                      <div class="db-status-label">ENGINE STATUS</div>
                      <div class="db-status-text" :class="dbStatus">{{ dbStatusLabel }}</div>
                    </div>
                  </div>
                  <div class="db-actions">
                    <button v-if="dbConfig.type === 'sqlite'" class="btn-action btn-init" @click="initializeDb" :disabled="initializingDb">
                      <span v-if="initializingDb" class="spinner"></span>
                      <span v-else>✨ INIT NEW</span>
                    </button>
                    <button class="btn-action btn-test" @click="testConnection" :disabled="testingDb">
                      <span v-if="testingDb" class="spinner"></span>
                      <span v-else>📡 TEST CONN</span>
                    </button>
                  </div>
                </div>
                <div v-if="dbError && dbStatus === 'error'" class="db-error-msg">
                  ⚠️ {{ dbError }}
                </div>
              </div>

              <div class="settings-card">
                <div class="card-body">
                  <div class="form-group">
                    <label>ENGINE TYPE</label>
                    <div class="custom-select-wrapper">
                      <select v-model="dbConfig.type" class="form-input custom-select">
                        <option value="sqlite">SQLite (Local File)</option>
                        <option value="postgresql">PostgreSQL</option>
                        <option value="mysql">MySQL / MariaDB</option>
                      </select>
                    </div>
                  </div>

                  <transition name="slide-fade">
                    <div v-if="dbConfig.type === 'sqlite'" class="form-group mt-3">
                      <label>DATABASE FILE PATH</label>
                      <input v-model="dbConfig.path" placeholder="data/netrunner.db" class="form-input" />
                    </div>

                    <div v-else class="db-grid mt-3">
                      <div class="form-group">
                        <label>HOST</label>
                        <input v-model="dbConfig.host" placeholder="localhost" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>PORT</label>
                        <input v-model.number="dbConfig.port" type="number" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>USER</label>
                        <input v-model="dbConfig.user" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>PASSWORD</label>
                        <input v-model="dbConfig.pass" type="password" class="form-input" />
                      </div>
                      <div class="form-group full-width">
                        <label>DATABASE NAME</label>
                        <input v-model="dbConfig.name" class="form-input" />
                      </div>
                    </div>
                  </transition>
                  
                  <div class="form-group raw-url">
                    <label>RAW CONNECTION STRING <span class="read-only-badge">READ-ONLY</span></label>
                    <input :value="computedDbUrl" readonly class="form-input raw-input" />
                  </div>
                </div>
              </div>

            </div>
          </transition>
        </div>
      </div>

      <div class="modal-footer">
        <div class="footer-left">
          <transition name="fade">
            <button class="btn-restart" @click="restart" v-if="hasChanges" :disabled="restarting">
              <span v-if="restarting" class="spinner"></span>
              <span v-else>⚠️ RESTART CORE</span>
            </button>
          </transition>
        </div>
        <div class="footer-right">
          <button class="btn-cancel" @click="$emit('close')">CANCEL</button>
          <button class="btn-save" @click="save" :disabled="saving">
            <span v-if="saving" class="spinner"></span>
            <span v-else>SAVE CHANGES</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api/client'

const emit = defineEmits(['close', 'saved'])

const activeTab = ref('general')
const tabs = [
  { id: 'general', label: 'Integrations', icon: '🔌' },
  { id: 'database', label: 'Database', icon: '🗄️' }
]

const apiKey = ref('')
const gns3Url = ref('http://127.0.0.1:3080')
const currentKeyMasked = ref('')
const alienvaultKey = ref('')
const currentAlienvaultMasked = ref('')
const saving = ref(false)
const restarting = ref(false)
const hasChanges = ref(false)

const dbConfig = ref({
    type: 'sqlite',
    path: 'data/netrunner.db',
    host: 'localhost',
    port: 5432,
    user: 'postgres',
    pass: '',
    name: 'netrunner'
})

const dbStatus = ref<'idle' | 'connecting' | 'connected' | 'error'>('idle')
const dbError = ref('')
const testingDb = ref(false)
const initializingDb = ref(false)

const dbStatusLabel = computed(() => {
    switch (dbStatus.value) {
        case 'connected': return 'ONLINE'
        case 'error': return 'CONNECTION FAILED'
        case 'connecting': return 'CONNECTING...'
        default: return 'STANDBY'
    }
})

const computedDbUrl = computed(() => {
    const c = dbConfig.value
    if (c.type === 'sqlite') {
        return `sqlite+aiosqlite:///${c.path}`
    } else if (c.type === 'postgresql') {
        return `postgresql+asyncpg://${c.user}:${c.pass}@${c.host}:${c.port}/${c.name}`
    } else if (c.type === 'mysql') {
        return `mysql+aiomysql://${c.user}:${c.pass}@${c.host}:${c.port}/${c.name}`
    }
    return ''
})

async function load() {
  try {
    const res = await api.getSettings()
    if (res.openai_api_key_set) currentKeyMasked.value = res.masked_key
    if (res.alienvault_api_key_set) currentAlienvaultMasked.value = res.masked_alienvault_key
    if (res.gns3_server_url) gns3Url.value = res.gns3_server_url
    
    if (res.database_url) {
        const url = res.database_url
        if (url.startsWith('sqlite')) {
            dbConfig.value.type = 'sqlite'
            dbConfig.value.path = url.split(':///')[1] || 'data/netrunner.db'
        } else {
            const match = url.match(/(postgresql|mysql)\+(asyncpg|aiomysql):\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/(.+)/)
            if (match) {
                dbConfig.value.type = match[1]
                dbConfig.value.user = match[3]
                dbConfig.value.pass = match[4]
                dbConfig.value.host = match[5]
                dbConfig.value.port = parseInt(match[6])
                dbConfig.value.name = match[7]
            }
        }
    }
    dbStatus.value = 'connected'
  } catch (e) {
    console.error('Failed to load settings', e)
  }
}

async function testConnection() {
    testingDb.value = true
    dbStatus.value = 'connecting'
    try {
        const res = await api.testDbConnection(computedDbUrl.value)
        if (res.status === 'ok') {
            dbStatus.value = 'connected'
        } else {
            dbStatus.value = 'error'
            dbError.value = res.message || 'Unknown error'
        }
    } catch (e) {
        dbStatus.value = 'error'
        dbError.value = String(e)
    } finally {
        testingDb.value = false
    }
}

async function initializeDb() {
    if (!confirm('This will create a new database file at the specified path. Continue?')) return
    initializingDb.value = true
    try {
        await api.initDb(computedDbUrl.value)
        dbStatus.value = 'connected'
        dbError.value = ''
    } catch (e) {
        dbStatus.value = 'error'
        dbError.value = String(e)
    } finally {
        initializingDb.value = false
    }
}

async function save() {
  saving.value = true
  try {
    const payload: any = { 
        gns3_server_url: gns3Url.value,
        database_url: computedDbUrl.value 
    }
    if (apiKey.value) payload.openai_api_key = apiKey.value
    if (alienvaultKey.value) payload.alienvault_api_key = alienvaultKey.value
    await api.updateSettings(payload)
    hasChanges.value = true
    emit('saved')
  } catch (e) {
    alert(String(e))
  } finally {
    saving.value = false
  }
}

async function restart() {
    if (!confirm('Restart server to apply changes?')) return
    restarting.value = true
    try {
        await api.restartServer()
        setTimeout(() => { location.reload() }, 3000)
    } catch (e) {
        setTimeout(() => { location.reload() }, 3000)
    }
}

onMounted(load)
</script>

<style scoped>
/* Animations */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-fade-enter-active { transition: all 0.3s ease-out; }
.slide-fade-leave-active { transition: all 0.2s ease-in; }
.slide-fade-enter-from, .slide-fade-leave-to { opacity: 0; transform: translateY(-10px); }
@keyframes pulseGlow { 0% { box-shadow: 0 0 5px var(--cyan); } 50% { box-shadow: 0 0 15px var(--cyan); } 100% { box-shadow: 0 0 5px var(--cyan); } }
@keyframes spin { to { transform: rotate(360deg); } }

.spinner {
  display: inline-block;
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Modal Shell */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(3, 5, 10, 0.85);
  backdrop-filter: blur(12px); display: flex; align-items: center; justify-content: center; z-index: 3000;
}
.modal-content.cyber-glass {
  width: 100%; max-width: 750px; background: rgba(10, 14, 25, 0.8); border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 12px; box-shadow: 0 24px 80px rgba(0, 229, 255, 0.1), inset 0 0 30px rgba(0, 229, 255, 0.05);
  overflow: hidden; display: flex; flex-direction: column;
}

/* Header */
.modal-header { 
  padding: 20px 24px; border-bottom: 1px solid rgba(0, 229, 255, 0.1); 
  display: flex; align-items: center; justify-content: space-between; 
  background: linear-gradient(90deg, rgba(0, 229, 255, 0.05), transparent);
}
.modal-title { display: flex; align-items: center; gap: 10px; font-family: var(--font-hd); font-size: 14px; letter-spacing: 2px; color: var(--textwh); }
.modal-title .icon { font-size: 16px; filter: drop-shadow(0 0 5px var(--cyan)); }
.btn-close { background: none; border: none; color: var(--text); font-size: 24px; cursor: pointer; transition: color 0.2s; line-height: 1; }
.btn-close:hover { color: var(--pink); text-shadow: 0 0 10px var(--pink); }

/* Layout */
.modal-body-layout { display: flex; height: 500px; }

/* Sidebar Nav */
.settings-nav {
  width: 200px; background: rgba(5, 8, 15, 0.5); border-right: 1px solid rgba(0, 229, 255, 0.1);
  padding: 16px 0; display: flex; flex-direction: column; gap: 4px;
}
.nav-tab {
  display: flex; align-items: center; gap: 12px; padding: 12px 20px;
  background: transparent; border: none; border-left: 3px solid transparent;
  color: var(--text); font-family: var(--font-hd); font-size: 11px; letter-spacing: 1px;
  cursor: pointer; text-align: left; transition: all 0.2s;
}
.nav-tab:hover { background: rgba(255, 255, 255, 0.03); color: var(--textwh); }
.nav-tab.active {
  background: rgba(0, 229, 255, 0.08); border-left-color: var(--cyan); color: var(--cyan);
  box-shadow: inset 20px 0 20px -20px rgba(0, 229, 255, 0.3);
}
.tab-icon { font-size: 14px; opacity: 0.8; }
.nav-tab.active .tab-icon { filter: drop-shadow(0 0 5px var(--cyan)); opacity: 1; }

/* Main Content */
.settings-content { flex: 1; padding: 24px; overflow-y: auto; background: rgba(10, 14, 25, 0.2); }
.tab-pane { display: flex; flex-direction: column; gap: 20px; }

/* Settings Cards */
.settings-card {
  background: rgba(15, 20, 35, 0.4); border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px; overflow: hidden; transition: border-color 0.3s;
}
.settings-card:hover { border-color: rgba(0, 229, 255, 0.2); }
.card-header {
  padding: 12px 16px; background: rgba(0, 0, 0, 0.2); border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex; align-items: center; gap: 10px;
}
.card-icon { font-size: 14px; }
.card-title { font-family: var(--font-hd); font-size: 10px; color: var(--textwh); letter-spacing: 1px; }
.card-body { padding: 16px; }

/* DB Status Bar */
.db-status-card { padding: 16px; }
.db-status-bar { display: flex; align-items: center; justify-content: space-between; }
.db-status-indicator { display: flex; align-items: center; gap: 16px; }
.db-lamp { width: 14px; height: 14px; border-radius: 50%; background: #444; border: 2px solid rgba(0,0,0,0.5); }
.db-lamp.connected { background: var(--green); box-shadow: 0 0 12px var(--green); }
.db-lamp.error { background: var(--pink); box-shadow: 0 0 12px var(--pink); }
.db-lamp.connecting { background: var(--yellow); box-shadow: 0 0 12px var(--yellow); animation: blink 1s infinite; }
.db-status-info { display: flex; flex-direction: column; gap: 2px; }
.db-status-label { font-family: var(--font-hd); font-size: 8px; color: var(--text); letter-spacing: 1px; }
.db-status-text { font-family: var(--font-hd); font-size: 11px; letter-spacing: 1px; font-weight: bold; }
.db-status-text.connected { color: var(--green); }
.db-status-text.error { color: var(--pink); }
.db-status-text.connecting { color: var(--yellow); }

.db-actions { display: flex; gap: 8px; }
.btn-action { 
  background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); 
  color: var(--textwh); font-family: var(--font-hd); font-size: 9px; padding: 8px 14px; 
  border-radius: 4px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; min-width: 100px;
}
.btn-action:hover:not(:disabled) { background: rgba(255, 255, 255, 0.1); border-color: rgba(255, 255, 255, 0.2); }
.btn-action:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-init { border-color: rgba(0, 229, 255, 0.3); color: var(--cyan); }
.btn-init:hover:not(:disabled) { background: rgba(0, 229, 255, 0.1); border-color: var(--cyan); box-shadow: 0 0 10px rgba(0, 229, 255, 0.2); }

.db-error-msg { margin-top: 12px; padding: 10px; background: rgba(255, 45, 110, 0.1); border-left: 3px solid var(--pink); font-family: var(--font-co); font-size: 11px; color: var(--pink); }

/* Forms */
.mt-3 { margin-top: 16px; }
.form-group { margin-bottom: 16px; position: relative; }
.form-group:last-child { margin-bottom: 0; }
label { display: flex; align-items: center; gap: 8px; font-family: var(--font-hd); font-size: 9px; color: var(--text); margin-bottom: 8px; letter-spacing: 1px; }
.read-only-badge { background: rgba(255, 255, 255, 0.1); padding: 2px 6px; border-radius: 3px; font-size: 7px; color: var(--textwh); }

.form-input { 
  width: 100%; padding: 10px 14px; background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); 
  border-radius: 6px; color: var(--textwh); font-family: var(--font-co); font-size: 12px; outline: none; transition: all 0.2s;
}
.form-input:focus { border-color: var(--cyan); box-shadow: 0 0 12px rgba(0,229,255,0.15); background: rgba(0, 0, 0, 0.5); }
.form-input::placeholder { color: rgba(255, 255, 255, 0.2); }

.custom-select-wrapper { position: relative; }
.custom-select { appearance: none; cursor: pointer; }
.custom-select-wrapper::after { content: '▼'; position: absolute; right: 14px; top: 50%; transform: translateY(-50%); font-size: 8px; color: var(--text); pointer-events: none; }

.db-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.full-width { grid-column: span 2; }

.raw-url { margin-top: 24px; padding-top: 16px; border-top: 1px dashed rgba(255, 255, 255, 0.1); }
.raw-input { font-size: 11px; color: var(--textbr); background: rgba(0, 0, 0, 0.5); border-color: transparent; }
.raw-input:focus { box-shadow: none; border-color: rgba(255, 255, 255, 0.1); }

.hint { margin-top: 8px; font-size: 11px; color: var(--text); font-family: var(--font-co); display: flex; align-items: center; gap: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text); }
.status-dot.active { background: var(--green); box-shadow: 0 0 8px var(--green); }
.masked-text { color: var(--textwh); letter-spacing: 2px; }

/* Footer */
.modal-footer { 
  padding: 16px 24px; border-top: 1px solid rgba(0, 229, 255, 0.1); 
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(5, 8, 15, 0.8);
}
.footer-left, .footer-right { display: flex; gap: 12px; align-items: center; }

.btn-cancel { 
  background: none; border: 1px solid rgba(255, 255, 255, 0.1); color: var(--text); 
  padding: 10px 20px; border-radius: 6px; font-family: var(--font-hd); font-size: 10px; cursor: pointer; transition: all 0.2s; 
}
.btn-cancel:hover { background: rgba(255, 255, 255, 0.05); color: var(--textwh); }

.btn-save { 
  background: rgba(0, 229, 255, 0.15); color: var(--cyan); border: 1px solid var(--cyan); 
  padding: 10px 24px; border-radius: 6px; font-family: var(--font-hd); font-size: 11px; letter-spacing: 1px;
  cursor: pointer; transition: all 0.3s; display: flex; align-items: center; justify-content: center; min-width: 120px;
}
.btn-save:hover:not(:disabled) { background: var(--cyan); color: #000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.4); }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; border-color: rgba(0, 229, 255, 0.3); color: rgba(0, 229, 255, 0.5); background: transparent; }

.btn-restart { 
  background: rgba(255, 45, 110, 0.1); color: var(--pink); border: 1px solid var(--pink); 
  padding: 10px 16px; border-radius: 6px; font-family: var(--font-hd); font-size: 10px; 
  cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.3s;
}
.btn-restart:hover:not(:disabled) { background: var(--pink); color: #fff; box-shadow: 0 0 15px rgba(255, 45, 110, 0.4); }
.btn-restart:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
