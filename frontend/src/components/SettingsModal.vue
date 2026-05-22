<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <div class="modal-title">SYSTEM SETTINGS</div>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div class="section-title">AI ASSISTANT</div>
        <div class="form-group">
          <label>OPENAI API KEY</label>
          <div class="input-with-hint">
            <input v-model="apiKey" type="password" placeholder="sk-..." class="form-input" />
            <div class="hint" v-if="currentKeyMasked">
              Current: <span class="masked-text">{{ currentKeyMasked }}</span>
            </div>
          </div>
        </div>

        <div class="section-title">CYBER THREAT INTELLIGENCE (CTI)</div>
        <div class="form-group">
          <label>ALIENVAULT OTX API KEY</label>
          <div class="input-with-hint">
            <input v-model="alienvaultKey" type="password" placeholder="Enter API Key to disable Demo Mode" class="form-input" />
            <div class="hint" v-if="currentAlienvaultMasked">
              Current: <span class="masked-text">{{ currentAlienvaultMasked }}</span>
            </div>
          </div>
        </div>

        <div class="section-title">GNS3 INTEGRATION</div>
        <div class="form-group">
          <label>SERVER URL</label>
          <input v-model="gns3Url" placeholder="http://127.0.0.1:3080" class="form-input" />
        </div>

        <div class="section-title">DATABASE CONFIGURATION</div>
        <div class="db-config-box">
          <div class="db-status-bar">
            <div class="db-lamp" :class="dbStatus"></div>
            <span class="db-status-text">{{ dbStatusLabel }}</span>
            <div class="db-actions">
                <button v-if="dbConfig.type === 'sqlite'" class="btn-init-db" @click="initializeDb" :disabled="initializingDb">
                    {{ initializingDb ? 'CREATING...' : 'INITIALIZE NEW DB' }}
                </button>
                <button class="btn-test-db" @click="testConnection" :disabled="testingDb">
                    {{ testingDb ? 'TESTING...' : 'TEST CONNECTION' }}
                </button>
            </div>
          </div>

          <div class="form-group">
            <label>ENGINE TYPE</label>
            <select v-model="dbConfig.type" class="form-input">
                <option value="sqlite">SQLite (Local File)</option>
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL / MariaDB</option>
            </select>
          </div>

          <div v-if="dbConfig.type === 'sqlite'" class="form-group">
            <label>FILE PATH</label>
            <input v-model="dbConfig.path" placeholder="data/netrunner.db" class="form-input" />
          </div>

          <div v-else class="db-grid">
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
          
          <div class="form-group raw-url">
            <label>RAW CONNECTION STRING</label>
            <input :value="computedDbUrl" readonly class="form-input raw-input" />
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-restart" @click="restart" v-if="hasChanges" :disabled="restarting">
          {{ restarting ? 'RESTARTING...' : 'RESTART SERVER' }}
        </button>
        <button class="btn-cancel" @click="$emit('close')">CANCEL</button>
        <button class="btn-save" @click="save" :disabled="saving">
          {{ saving ? 'SAVING...' : 'SAVE CONFIG' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api/client'

const emit = defineEmits(['close', 'saved'])

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
        case 'connected': return 'DATABASE CONNECTED'
        case 'error': return 'CONNECTION ERROR'
        case 'connecting': return 'CONNECTING...'
        default: return 'NOT TESTED'
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
            alert('Connection failed: ' + dbError.value)
        }
    } catch (e) {
        dbStatus.value = 'error'
        alert(String(e))
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
        alert('Database initialized successfully.')
    } catch (e) {
        alert('Failed to initialize: ' + e)
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
.modal-overlay {
  position: fixed; inset: 0; background: rgba(5, 8, 15, 0.9);
  backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 3000;
}
.modal-content {
  width: 100%; max-width: 500px; background: var(--bg2); border: 1px solid var(--border);
  border-radius: var(--r2); box-shadow: 0 20px 60px rgba(0,0,0,0.6); overflow: hidden;
}
.modal-header { padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.modal-title { font-family: var(--font-hd); font-size: 13px; letter-spacing: 2px; color: var(--cyan); text-shadow: 0 0 8px var(--cyan); }
.btn-close { background: none; border: none; color: var(--text); font-size: 20px; cursor: pointer; }
.modal-body { padding: 24px; max-height: 70vh; overflow-y: auto; }

.section-title { font-family: var(--font-hd); font-size: 10px; color: var(--textwh); margin: 24px 0 12px; letter-spacing: 1px; opacity: 0.8; }
.section-title:first-child { margin-top: 0; }

.db-config-box { background: var(--bg3); border: 1px solid var(--border); border-radius: var(--r); padding: 16px; }

.db-status-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
.db-lamp { width: 10px; height: 10px; border-radius: 50%; background: #444; box-shadow: 0 0 5px #000; }
.db-lamp.connected { background: var(--green); box-shadow: 0 0 10px var(--green); }
.db-lamp.error { background: var(--pink); box-shadow: 0 0 10px var(--pink); }
.db-lamp.connecting { background: var(--yellow); box-shadow: 0 0 10px var(--yellow); animation: blink 1s infinite; }
.db-status-text { font-family: var(--font-hd); font-size: 9px; color: var(--textbr); flex: 1; }
.db-actions { display: flex; gap: 8px; }
.btn-test-db, .btn-init-db { background: #21262d; border: 1px solid var(--border2); color: var(--textwh); font-family: var(--font-hd); font-size: 8px; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
.btn-init-db { border-color: var(--cyan); color: var(--cyan); }
.btn-init-db:hover { background: rgba(0, 229, 255, 0.1); }

@keyframes blink { 0%, 100% { opacity: 1 } 50% { opacity: 0.4 } }

.db-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.full-width { grid-column: span 2; }

.form-group { margin-bottom: 16px; }
label { display: block; font-family: var(--font-hd); font-size: 8px; color: var(--text); margin-bottom: 6px; letter-spacing: 1px; }
.form-input { width: 100%; padding: 10px; background: var(--bg); border: 1px solid var(--border); border-radius: var(--r); color: var(--textwh); font-family: var(--font-co); font-size: 11px; outline: none; }
.form-input:focus { border-color: var(--cyan); box-shadow: 0 0 10px rgba(0,229,255,0.1); }

.raw-url { margin-top: 16px; opacity: 0.6; }
.raw-input { font-size: 9px; background: rgba(0,0,0,0.2); }

.hint { margin-top: 6px; font-size: 9px; color: var(--text); font-family: var(--font-co); }
.masked-text { color: var(--green); }

.modal-footer { padding: 18px 24px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 12px; background: var(--bg3); }
.btn-cancel { background: none; border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: var(--r); font-family: var(--font-hd); font-size: 10px; cursor: pointer; }
.btn-save { background: var(--cyan); color: var(--bg); border: none; padding: 8px 20px; border-radius: var(--r); font-family: var(--font-hd); font-size: 10px; cursor: pointer; transition: all 0.2s; }
.btn-save:hover { box-shadow: var(--shadow-c); }
.btn-restart { background: var(--pink); color: #fff; border: none; padding: 8px 16px; border-radius: var(--r); font-family: var(--font-hd); font-size: 10px; cursor: pointer; margin-right: auto; box-shadow: 0 0 10px rgba(255, 45, 110, 0.3); }
</style>
