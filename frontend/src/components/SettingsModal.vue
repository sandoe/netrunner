<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content cyber-glass" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div class="modal-header">
        <div class="modal-title" id="settings-title">
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
            <!-- AI ENGINE TAB -->
            <div v-if="activeTab === 'ai'" class="tab-pane" key="ai">

              <div class="settings-card">
                <div class="card-header">
                  <div class="card-icon">🧠</div>
                  <div class="card-title">AI Engine Configuration</div>
                </div>
                <div class="card-body">
                  <div class="form-group">
                    <label>EXECUTION MODE</label>
                    <div class="custom-select-wrapper">
                      <select v-model="aiExecutionMode" class="form-input custom-select">
                        <option value="api">Direct API Call (Cloud/Local API)</option>
                        <option value="cli">CLI Agent (Local Process)</option>
                      </select>
                    </div>
                  </div>

                  <!-- API MODE -->
                  <transition name="fade">
                    <div v-if="aiExecutionMode === 'api'">
                      <div class="form-group mt-3">
                        <label>AI PROVIDER</label>
                        <div class="custom-select-wrapper">
                          <select v-model="aiProvider" class="form-input custom-select">
                            <option value="openai">OpenAI</option>
                            <option value="openrouter">OpenRouter / compatible</option>
                            <option value="ollama">Ollama / local compatible</option>
                            <option value="custom">Custom OpenAI-compatible API</option>
                          </select>
                        </div>
                      </div>
                      <div class="form-group">
                        <label>MODEL</label>
                        <input v-model="aiModel" :placeholder="aiModelPlaceholder" class="form-input" />
                      </div>
                      <div class="form-group" v-if="aiProvider !== 'openai'">
                        <label>BASE URL</label>
                        <input v-model="aiBaseUrl" :placeholder="aiBaseUrlPlaceholder" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>{{ aiProvider === 'ollama' ? 'API KEY (OPTIONAL)' : 'API KEY' }}</label>
                        <div class="input-with-hint">
                          <input v-model="apiKey" type="password" :placeholder="aiKeyPlaceholder" class="form-input" />
                          <div class="hint" v-if="currentKeyMasked">
                            <span class="status-dot active"></span> Active Key: <span class="masked-text">{{ currentKeyMasked }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                  <!-- CLI MODE -->
                    <div v-else-if="aiExecutionMode === 'cli'">
                      <div class="form-group mt-3">
                        <label>AGENT TYPE</label>
                        <div class="custom-select-wrapper">
                          <select v-model="aiCliType" class="form-input custom-select">
                            <option value="antigravity">Antigravity / Gemini SDK</option>
                            <option value="claude">Claude CLI</option>
                            <option value="codex">Codex API Tool</option>
                            <option value="opencode">OpenCode Local Agent</option>
                          </select>
                        </div>
                      </div>
                      <div class="form-group">
                        <label>CLI COMMAND PATH</label>
                        <input v-model="aiCliPath" placeholder="/usr/local/bin/antigravity or npx claude" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>MODEL OVERRIDE (OPTIONAL)</label>
                        <input v-model="aiModel" placeholder="e.g. meta/llama-3.1-405b-instruct" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>BASE URL OVERRIDE (OPTIONAL)</label>
                        <input v-model="aiBaseUrl" placeholder="e.g. https://integrate.api.nvidia.com/v1" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>AGENT API KEY</label>
                        <div class="input-with-hint">
                          <input v-model="apiKey" type="password" placeholder="Key used specifically for this agent process" class="form-input" />
                          <div class="hint" v-if="currentKeyMasked">
                            <span class="status-dot active"></span> Active Key: <span class="masked-text">{{ currentKeyMasked }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </transition>
                </div>
              </div>

            </div>

            <!-- INTEGRATIONS TAB -->
            <div v-else-if="activeTab === 'integrations'" class="tab-pane" key="integrations">

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
            <!-- NETWORK TAB -->
            <div v-else-if="activeTab === 'network'" class="tab-pane" key="network">
              <div class="settings-card">
                <div class="card-header">
                  <div class="card-icon">🌐</div>
                  <div class="card-title">Linux Network Interfaces</div>
                </div>
                <div class="card-body">
                  <div class="db-actions" style="margin-bottom: 16px;">
                    <button class="btn-action btn-test" @click="loadNetwork" :disabled="loadingNetwork">
                      <span v-if="loadingNetwork" class="spinner"></span>
                      <span v-else>🔄 REFRESH</span>
                    </button>
                  </div>

                  <div v-if="loadingNetwork && !networkInterfaces.length" style="text-align:center; padding: 20px;">
                    <span class="spinner" style="width:24px; height:24px; border-width: 3px;"></span>
                  </div>
                  <div v-else>
                    <div class="interfaces-list">
                      <div v-for="iface in networkInterfaces" :key="iface.name" class="interface-item">
                        <div class="iface-header">
                          <span class="iface-name">{{ iface.name }}</span>
                          <div class="iface-actions">
                            <span :class="['iface-state', iface.state.toLowerCase()]">{{ iface.state }}</span>
                            <button v-if="iface.name.includes('.')" class="btn-icon text-pink" @click="deleteVlan(iface.name)" style="margin-left: 8px;">×</button>
                          </div>
                        </div>
                        <div class="iface-details">
                          <div class="detail-row"><span>MAC:</span> <span>{{ iface.mac }}</span></div>
                          <div class="detail-row"><span>MTU:</span> <span>{{ iface.mtu }}</span></div>
                          <div class="detail-row">
                             <span>IPv4:</span>
                             <div class="ip-list">
                               <span v-for="ip in iface.ipv4" :key="ip" class="ip-badge ipv4">{{ ip }}</span>
                               <span v-if="!iface.ipv4.length" class="text-muted">None</span>
                             </div>
                          </div>
                          <div class="detail-row">
                             <span>IPv6:</span>
                             <div class="ip-list">
                               <span v-for="ip in iface.ipv6" :key="ip" class="ip-badge ipv6">{{ ip }}</span>
                               <span v-if="!iface.ipv6.length" class="text-muted">None</span>
                             </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- VLAN MANAGEMENT CARD -->
              <div class="settings-card mt-3">
                <div class="card-header">
                  <div class="card-icon">🔌</div>
                  <div class="card-title">VLAN Subinterfaces</div>
                </div>
                <div class="card-body">
                  <div class="vlan-add-form">
                    <input v-model="newVlan.parent" placeholder="Parent (e.g. eth0)" class="form-input form-input-sm" />
                    <input v-model="newVlan.vlan_id" type="number" placeholder="VLAN ID" class="form-input form-input-sm" style="width: 80px;" />
                    <input v-model="newVlan.ip_address" placeholder="IP (Optional, e.g. 10.0.0.1/24)" class="form-input form-input-sm" />
                    <button class="btn-action" @click="addVlan" :disabled="addingVlan">
                      <span v-if="addingVlan" class="spinner"></span>
                      <span v-else>+ CREATE VLAN</span>
                    </button>
                  </div>
                </div>
              </div>

              <!-- ROUTING TABLE CARD -->
              <div class="settings-card mt-3">
                <div class="card-header">
                  <div class="card-icon">🗺️</div>
                  <div class="card-title">Routing Table</div>
                </div>
                <div class="card-body">
                  <div class="route-add-form">
                    <input v-model="newRoute.dest" placeholder="Dest (e.g. 0.0.0.0/0)" class="form-input form-input-sm" />
                    <input v-model="newRoute.gateway" placeholder="Gateway IP" class="form-input form-input-sm" />
                    <input v-model="newRoute.dev" placeholder="Device" class="form-input form-input-sm" />
                    <button class="btn-action" @click="addRoute" :disabled="addingRoute">
                      <span v-if="addingRoute" class="spinner"></span>
                      <span v-else>+ ADD ROUTE</span>
                    </button>
                  </div>

                  <table class="route-table">
                    <thead>
                      <tr>
                        <th>Destination</th>
                        <th>Gateway</th>
                        <th>Dev</th>
                        <th>Metric</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(r, i) in networkRoutes" :key="i">
                        <td>{{ r.dest }}</td>
                        <td>{{ r.gateway || '*' }}</td>
                        <td>{{ r.dev }}</td>
                        <td>{{ r.metric || '-' }}</td>
                        <td>
                          <button class="btn-icon text-pink" @click="deleteRoute(r)">×</button>
                        </td>
                      </tr>
                      <tr v-if="!networkRoutes.length">
                        <td colspan="5" class="text-center text-muted">No routes found</td>
                      </tr>
                    </tbody>
                  </table>
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
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { api } from '@/api/client'

const emit = defineEmits(['close', 'saved'])

onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))
function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

const activeTab = ref('ai')
const tabs = [
  { id: 'ai', label: 'AI Engine', icon: '🧠' },
  { id: 'integrations', label: 'Integrations', icon: '🔌' },
  { id: 'database', label: 'Database', icon: '🗄️' },
  { id: 'network', label: 'Network', icon: '🌐' }
]

const aiExecutionMode = ref('api')
const aiCliType = ref('antigravity')
const aiCliPath = ref('')
const apiKey = ref('')
const aiProvider = ref('openai')
const aiBaseUrl = ref('')
const aiModel = ref('gpt-4o')
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

const networkInterfaces = ref<any[]>([])
const networkRoutes = ref<any[]>([])
const loadingNetwork = ref(false)
const addingRoute = ref(false)
const newRoute = ref({ dest: '', gateway: '', dev: '' })

const addingVlan = ref(false)
const newVlan = ref({ parent: '', vlan_id: null as number | null, ip_address: '' })

const dbStatusLabel = computed(() => {
    switch (dbStatus.value) {
        case 'connected': return 'ONLINE'
        case 'error': return 'CONNECTION FAILED'
        case 'connecting': return 'CONNECTING...'
        default: return 'STANDBY'
    }
})

const aiModelPlaceholder = computed(() => {
    if (aiProvider.value === 'openrouter') return 'openai/gpt-4o-mini, anthropic/claude-3.5-sonnet, ...'
    if (aiProvider.value === 'ollama') return 'llama3.1'
    return 'gpt-4o'
})

const aiBaseUrlPlaceholder = computed(() => {
    if (aiProvider.value === 'openrouter') return 'https://openrouter.ai/api/v1'
    if (aiProvider.value === 'ollama') return 'http://127.0.0.1:11434/v1'
    return 'https://api.example.com/v1'
})

const aiKeyPlaceholder = computed(() => {
    if (aiProvider.value === 'openrouter') return 'OpenRouter API key'
    if (aiProvider.value === 'ollama') return 'optional'
    return 'sk-...'
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
    aiExecutionMode.value = res.ai_execution_mode || 'api'
    aiCliType.value = res.ai_cli_type || 'antigravity'
    aiCliPath.value = res.ai_cli_path || ''
    aiProvider.value = res.ai_provider || 'openai'
    aiBaseUrl.value = res.ai_base_url || ''
    aiModel.value = res.ai_model || (aiProvider.value === 'ollama' ? 'llama3.1' : 'gpt-4o')
    if (res.ai_api_key_set || res.openai_api_key_set) currentKeyMasked.value = res.ai_masked_key || res.masked_key
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
        ai_execution_mode: aiExecutionMode.value,
        ai_cli_type: aiCliType.value,
        ai_cli_path: aiCliPath.value,
        ai_provider: aiProvider.value,
        ai_base_url: aiBaseUrl.value,
        ai_model: aiModel.value,
        gns3_server_url: gns3Url.value,
        database_url: computedDbUrl.value
    }
    if (apiKey.value) payload.ai_api_key = apiKey.value
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

async function loadNetwork() {
  loadingNetwork.value = true
  try {
    const [ifaces, routes] = await Promise.all([
      api.getNetworkInterfaces(),
      api.getNetworkRoutes()
    ])
    networkInterfaces.value = ifaces
    networkRoutes.value = routes
  } catch (e) {
    console.error('Failed to load network details', e)
  } finally {
    loadingNetwork.value = false
  }
}

async function addRoute() {
  if (!newRoute.value.dest) return
  addingRoute.value = true
  try {
    await api.addNetworkRoute(newRoute.value)
    newRoute.value = { dest: '', gateway: '', dev: '' }
    await loadNetwork()
  } catch (e: any) {
    alert('Failed to add route: ' + e.message)
  } finally {
    addingRoute.value = false
  }
}

async function deleteRoute(r: any) {
  try {
    await api.deleteNetworkRoute(r)
    await loadNetwork()
  } catch (e: any) {
    alert('Failed to delete route: ' + e.message)
  }
}

async function addVlan() {
  if (!newVlan.value.parent || !newVlan.value.vlan_id) return
  addingVlan.value = true
  try {
    await api.addVlan({
      parent: newVlan.value.parent,
      vlan_id: newVlan.value.vlan_id,
      ip_address: newVlan.value.ip_address || undefined
    })
    newVlan.value = { parent: '', vlan_id: null, ip_address: '' }
    await loadNetwork()
  } catch (e: any) {
    alert('Failed to add VLAN: ' + e.message)
  } finally {
    addingVlan.value = false
  }
}

async function deleteVlan(ifaceName: string) {
  if (!confirm(`Delete VLAN interface ${ifaceName}?`)) return
  try {
    await api.deleteVlan(ifaceName)
    await loadNetwork()
  } catch (e: any) {
    alert('Failed to delete VLAN: ' + e.message)
  }
}

onMounted(() => {
  load()
  loadNetwork()
})
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
  padding: 16px 0; display: flex; flex-direction: column; gap: 4px; flex-shrink: 0;
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
.form-input::placeholder { color: rgba(255, 255, 255, 0.5); }

.custom-select-wrapper { position: relative; }
.custom-select { appearance: none; cursor: pointer; }
.custom-select-wrapper::after { content: '▼'; position: absolute; right: 14px; top: 50%; transform: translateY(-50%); font-size: 8px; color: var(--text); pointer-events: none; }

.db-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.full-width { grid-column: span 2; }

@media (max-width: 768px) {
  .modal-body-layout { flex-direction: column; height: auto; max-height: 70vh; }
  .settings-nav { width: 100%; border-right: none; border-bottom: 1px solid rgba(0, 229, 255, 0.1); flex-direction: row; padding: 8px; overflow-x: auto; }
  .nav-tab { border-left: none; border-bottom: 3px solid transparent; flex: 1; justify-content: center; padding: 12px 8px; }
  .nav-tab.active { border-left-color: transparent; border-bottom-color: var(--cyan); box-shadow: inset 0 20px 20px -20px rgba(0, 229, 255, 0.3); }
  .db-grid { grid-template-columns: 1fr; }
  .full-width { grid-column: span 1; }
  .tab-label { display: none; }
}

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
.nav-tab:focus-visible, .btn-action:focus-visible, .btn-close:focus-visible, .btn-cancel:focus-visible, .btn-save:focus-visible, .btn-restart:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
button:focus-visible, .btn-action:focus-visible, .btn-close:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

/* Network Tab Specific Styles */
.interfaces-list { display: flex; flex-direction: column; gap: 12px; }
.interface-item {
  background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px; padding: 12px; transition: border-color 0.2s;
}
.interface-item:hover { border-color: rgba(0, 229, 255, 0.2); }
.iface-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(255, 255, 255, 0.1); padding-bottom: 8px; margin-bottom: 8px; }
.iface-name { font-family: var(--font-hd); font-size: 13px; color: var(--textwh); font-weight: bold; }
.iface-state { font-family: var(--font-hd); font-size: 9px; padding: 2px 6px; border-radius: 4px; letter-spacing: 1px; }
.iface-state.up, .iface-state.unknown { background: rgba(0, 255, 170, 0.1); color: var(--green); border: 1px solid rgba(0, 255, 170, 0.3); }
.iface-state.down { background: rgba(255, 45, 110, 0.1); color: var(--pink); border: 1px solid rgba(255, 45, 110, 0.3); }
.iface-details { display: flex; flex-direction: column; gap: 6px; }
.detail-row { display: grid; grid-template-columns: 50px 1fr; align-items: start; font-family: var(--font-co); font-size: 11px; color: var(--textbr); }
.detail-row > span:first-child { color: var(--text); font-family: var(--font-hd); font-size: 9px; margin-top: 2px; }
.ip-list { display: flex; flex-wrap: wrap; gap: 4px; }
.ip-badge { background: rgba(0, 0, 0, 0.4); padding: 2px 6px; border-radius: 4px; font-size: 10px; }
.ip-badge.ipv4 { border-bottom: 1px solid var(--cyan); }
.ip-badge.ipv6 { border-bottom: 1px solid var(--purple); opacity: 0.8; }
.text-muted { color: rgba(255, 255, 255, 0.3); font-style: italic; }

/* Route Table */
.route-add-form { display: flex; gap: 8px; margin-bottom: 16px; align-items: center; }
.form-input-sm { padding: 8px 12px; font-size: 11px; }
.route-table { width: 100%; border-collapse: collapse; font-family: var(--font-co); font-size: 11px; color: var(--textwh); }
.route-table th { text-align: left; padding: 8px; font-family: var(--font-hd); font-size: 9px; color: var(--text); border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.route-table td { padding: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.route-table tr:hover td { background: rgba(0, 229, 255, 0.05); }
.text-pink { color: var(--pink); }
.btn-icon { background: none; border: none; cursor: pointer; font-size: 14px; padding: 0 4px; transition: text-shadow 0.2s; }
.btn-icon:hover { text-shadow: 0 0 8px currentColor; }
.text-center { text-align: center; }

/* VLAN Management */
.vlan-add-form { display: flex; gap: 8px; align-items: center; }
.iface-actions { display: flex; align-items: center; }
</style>
