<template>
  <div class="war-room">
    <div class="wr-header">
      <div class="title">⚔️ CYBER COMMAND // RED VS BLUE</div>
      <div class="subtitle">LIVE SYSTEM OPERATIONS DASHBOARD</div>
    </div>

    <div class="split-view">
      <!-- RED TEAM (Chaos) -->
      <div class="team-panel red-team">
        <div class="team-header">
          <h2>RED TEAM</h2>
          <span class="sub">THREAT EMULATION / CHAOS MONKEY</span>
        </div>
        <!-- SUB-TABS FOR RED TEAM -->
        <div class="sub-tab-bar">
          <button 
            class="sub-tab" 
            :class="{ active: redSubTab === 'chaos' }"
            @click="redSubTab = 'chaos'"
          >
            🤖 AUTOMATED CHAOS
          </button>
          <button 
            class="sub-tab" 
            :class="{ active: redSubTab === 'manual' }"
            @click="redSubTab = 'manual'"
          >
            🎯 MANUAL STRIKE
          </button>
        </div>

        <div class="control-area" :class="{ 'manual-mode': redSubTab === 'manual' }">
          <!-- CHAOS PANEL -->
          <div v-if="redSubTab === 'chaos'" class="chaos-panel" style="width: 100%; display: flex; flex-direction: column; align-items: center; gap: 20px;">
            <p class="desc text-pink">
              Slip Chaos Monkey løs på netværket. 
              Dette simulerer interne og eksterne trusler ved at igangsætte Nmap-scans, 
              brute-force forsøg og anomali-skabelse for at teste Blue Teams reaktionsevne.
            </p>
            <button 
              v-if="isAdmin"
              class="btn-engage btn-red" 
              :class="{ active: chaosActive }" 
              @click="$emit('toggle-chaos')"
            >
              {{ chaosActive ? '🔥 CHAOS MODE: ENGAGED' : 'ENGAGE CHAOS MODE' }}
            </button>
            <div v-else class="locked text-pink">[LOCKED: ADMIN REQUIRED]</div>
          </div>

          <!-- MANUAL PANEL -->
          <div v-else class="manual-panel" style="width: 100%; display: flex; flex-direction: column; align-items: center;">
            <div class="strike-form" style="width: 100%;">
              <div v-if="isAdmin" style="width: 100%; display: flex; flex-direction: column; gap: 12px;">
                <!-- Node selection -->
                <div class="form-row">
                  <label>TARGET NODE:</label>
                  <select v-model="selectedNodeId" class="cyber-select">
                    <option value="" disabled>Vælg målnode...</option>
                    <option v-for="node in nodeList" :key="node.id" :value="node.id">
                      {{ node.name }} ({{ node.host || 'Ingen IP' }})
                    </option>
                  </select>
                </div>

                <!-- Attack type selection -->
                <div class="form-row">
                  <label>ATTACK VECTOR:</label>
                  <select v-model="selectedAttackType" @change="onAttackTypeChange" class="cyber-select">
                    <option value="ssh">SSH Brute Force</option>
                    <option value="sqli">Web Exploit: SQL Injection (SQLi)</option>
                    <option value="xss">Web Exploit: Cross-Site Scripting (XSS)</option>
                    <option value="lfi">Web Exploit: Path Traversal (LFI)</option>
                    <option value="ufw">Firewall: UFW Blocked Port Scan</option>
                  </select>
                </div>

                <!-- Attacker IP -->
                <div class="form-row">
                  <label>ATTACKER IP:</label>
                  <input v-model="attackerIp" type="text" class="cyber-input" placeholder="F.eks. 203.0.113.5" />
                </div>

                <!-- SSH username conditional field -->
                <div v-if="selectedAttackType === 'ssh'" class="form-row">
                  <label>TARGET USERNAME:</label>
                  <input v-model="sshUsername" type="text" class="cyber-input" placeholder="F.eks. root" />
                </div>

                <!-- Web Path Query conditional field -->
                <div v-if="['sqli', 'xss', 'lfi'].includes(selectedAttackType)" class="form-row">
                  <label>URL QUERY / PATH:</label>
                  <input v-model="webPathQuery" type="text" class="cyber-input" placeholder="F.eks. /?id=1%20UNION%20SELECT%201" />
                </div>

                <!-- Firewall port conditional field -->
                <div v-if="selectedAttackType === 'ufw'" class="form-row">
                  <label>TARGET PORT:</label>
                  <input v-model="fwPort" type="number" class="cyber-input" placeholder="F.eks. 8080" />
                </div>

                <!-- Action button -->
                <button 
                  class="btn-engage btn-red btn-strike" 
                  @click="launchAttack"
                  :disabled="launchingAttack || !selectedNodeId"
                >
                  {{ launchingAttack ? '🚀 UDRULLER ANGREB...' : '⚡ AFFYR MANUELT ANGREB' }}
                </button>

                <!-- Feedback message -->
                <div v-if="attackResult" class="strike-result text-pink animate-flash">
                  {{ attackResult }}
                </div>
              </div>
              <div v-else class="locked text-pink">[LOCKED: ADMIN REQUIRED]</div>
            </div>
          </div>
        </div>
        
        <div class="log-area">
          <div class="log-title text-pink">RED TEAM ACTIVITY FEED</div>
          <div class="log-window" ref="redLogsRef">
            <div v-for="(log, idx) in redLogs" :key="idx" class="log-entry text-pink">
              <span class="ts">[{{ log.ts }}]</span> {{ log.msg }}
            </div>
            <div v-if="redLogs.length === 0" class="log-empty">No recent activity.</div>
          </div>
        </div>
      </div>

      <!-- BLUE TEAM (Autopilot) -->
      <div class="team-panel blue-team">
        <div class="team-header">
          <h2>BLUE TEAM</h2>
          <span class="sub">AUTONOMOUS SOAR / ACTIVE DEFENSE</span>
        </div>
        <div class="control-area">
          <p class="desc text-cyan">
            Aktiver AI Autopilot. 
            Maskinlæringsmodellen vil analysere trusler i realtid, isolere inficerede noder 
            og håndhæve Zero Trust arkitektur automatisk uden menneskelig indgriben.
          </p>
          <button 
            v-if="isAdmin"
            class="btn-engage btn-blue" 
            :class="{ active: autopilotActive }" 
            @click="$emit('toggle-autopilot')"
          >
            {{ autopilotActive ? '🤖 AI AUTOPILOT: ONLINE' : 'ACTIVATE AI AUTOPILOT' }}
          </button>
          <div v-else class="locked text-cyan">[LOCKED: ADMIN REQUIRED]</div>
        </div>

        <div class="log-area">
          <div class="log-title text-cyan">BLUE TEAM ACTIVITY FEED</div>
          <div class="log-window" ref="blueLogsRef">
            <div v-for="(log, idx) in blueLogs" :key="idx" class="log-entry text-cyan">
              <span class="ts">[{{ log.ts }}]</span> {{ log.msg }}
            </div>
            <div v-if="blueLogs.length === 0" class="log-empty">No recent activity.</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, inject, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { api } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'

const props = defineProps<{
  autopilotActive: boolean
  chaosActive: boolean
}>()

defineEmits(['toggle-autopilot', 'toggle-chaos'])

const userRole = inject<any>('userRole')
const isAdmin = computed(() => {
  if (!userRole) return false
  const val = typeof userRole === 'object' && 'value' in userRole ? userRole.value : userRole
  return val === 'admin'
})

const nodesStore = useNodesStore()
const nodeList = computed(() => Object.values(nodesStore.nodes))

// Red Team sub-tabs
const redSubTab = ref<'chaos' | 'manual'>('chaos')

// Form variables for manual strike
const selectedNodeId = ref('')
const selectedAttackType = ref('ssh')
const attackerIp = ref('203.0.113.5')
const sshUsername = ref('root')
const webPathQuery = ref('/?id=1%20UNION%20SELECT%201')
const fwPort = ref(8080)

const launchingAttack = ref(false)
const attackResult = ref('')

// Set default values when selectedNodeId is empty on mount
onMounted(() => {
  if (nodeList.value.length > 0) {
    selectedNodeId.value = nodeList.value[0].id
  }
})

// Automatically set target fields based on selected attack type
function onAttackTypeChange() {
  if (selectedAttackType.value === 'ssh') {
    sshUsername.value = 'root'
  } else if (selectedAttackType.value === 'sqli') {
    webPathQuery.value = '/?id=1%20UNION%20SELECT%201'
  } else if (selectedAttackType.value === 'xss') {
    webPathQuery.value = '/?q=%3Cscript%3Ealert(1)%3C/script%3E'
  } else if (selectedAttackType.value === 'lfi') {
    webPathQuery.value = '/../../etc/passwd'
  } else if (selectedAttackType.value === 'ufw') {
    fwPort.value = 8080
  }
}

async function launchAttack() {
  if (!selectedNodeId.value) return
  launchingAttack.value = true
  attackResult.value = ''
  try {
    const payload = {
      node_id: selectedNodeId.value,
      attack_type: selectedAttackType.value,
      attacker_ip: attackerIp.value,
      username: selectedAttackType.value === 'ssh' ? sshUsername.value : undefined,
      port: selectedAttackType.value === 'ufw' ? Number(fwPort.value) : undefined,
      path_query: ['sqli', 'xss', 'lfi'].includes(selectedAttackType.value) ? webPathQuery.value : undefined
    }
    const res = await api.triggerAttack(payload)
    const writeDetail = res.real_file_write ? ' (Skrevet til serverlogfiler!)' : ' (Simuleret fallback)'
    attackResult.value = `Angreb udrullet: ${res.message}${writeDetail}`
  } catch (e: any) {
    attackResult.value = 'FEJL: ' + e.message
  } finally {
    launchingAttack.value = false
  }
}

const rawLogs = ref<any[]>([])

const redLogsRef = ref<HTMLElement | null>(null)
const blueLogsRef = ref<HTMLElement | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null

// Simple heuristic: If log contains "Chaos" or "Red", it's red team. 
// If it contains "Autopilot", "SOAR", "Defense", "Zero Trust", "Isolation", "Blue", it's blue team.
// Everything else goes to a general category or we just guess based on keywords.
const redLogs = computed(() => {
  return rawLogs.value.filter(l => {
    const msg = l.msg.toLowerCase()
    return msg.includes('chaos') || msg.includes('red team') || msg.includes('scan') || msg.includes('attack') || msg.includes('nmap') || msg.includes('strike')
  })
})

const blueLogs = computed(() => {
  return rawLogs.value.filter(l => {
    const msg = l.msg.toLowerCase()
    return msg.includes('autopilot') || msg.includes('blue team') || msg.includes('soar') || msg.includes('defense') || msg.includes('isolation') || msg.includes('zero trust') || msg.includes('block') || msg.includes('ai response')
  })
})

async function fetchLogs() {
  try {
    const res = await api.systemLogs()
    // Sort oldest to newest (or newest first, usually append bottom)
    // Assume res.logs is already chronological
    if (res.logs.length !== rawLogs.value.length) {
      rawLogs.value = res.logs
      scrollToBottom()
    }
  } catch (e) {
    // Ignore fetch errors during polling
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (redLogsRef.value) redLogsRef.value.scrollTop = redLogsRef.value.scrollHeight
    if (blueLogsRef.value) blueLogsRef.value.scrollTop = blueLogsRef.value.scrollHeight
  })
}

onMounted(() => {
  fetchLogs()
  pollTimer = setInterval(fetchLogs, 2000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.war-room {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 30px;
  background: radial-gradient(circle at center, #0a0e17 0%, #020305 100%);
  color: var(--text);
  overflow: hidden;
}

.wr-header {
  text-align: center;
  margin-bottom: 30px;
}

.wr-header .title {
  font-family: var(--font-hd);
  font-size: 28px;
  color: #fff;
  letter-spacing: 4px;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
}

.wr-header .subtitle {
  font-family: var(--font-hd);
  font-size: 12px;
  color: var(--text);
  letter-spacing: 2px;
  margin-top: 5px;
}

.split-view {
  flex: 1;
  display: flex;
  gap: 30px;
  min-height: 0;
}

.team-panel {
  flex: 1;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.red-team {
  border-top: 3px solid var(--pink);
}

.blue-team {
  border-top: 3px solid var(--cyan);
}

.team-header {
  padding: 20px;
  text-align: center;
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid var(--border);
}

.team-header h2 {
  margin: 0;
  font-family: var(--font-hd);
  font-size: 24px;
  letter-spacing: 3px;
}

.red-team h2 { color: var(--pink); text-shadow: 0 0 15px rgba(255, 45, 110, 0.5); }
.blue-team h2 { color: var(--cyan); text-shadow: 0 0 15px rgba(0, 229, 255, 0.5); }

.team-header .sub {
  font-family: var(--font-hd);
  font-size: 10px;
  color: var(--text);
  letter-spacing: 1px;
}

.control-area {
  padding: 30px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid var(--border);
}

.desc {
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.5;
  max-width: 400px;
}

.text-pink { color: var(--pink); }
.text-cyan { color: var(--cyan); }

.btn-engage {
  font-family: var(--font-hd);
  font-size: 16px;
  padding: 15px 40px;
  border-radius: 4px;
  cursor: pointer;
  letter-spacing: 2px;
  transition: all 0.3s;
  background: transparent;
  font-weight: bold;
}

.btn-red {
  border: 2px solid var(--pink);
  color: var(--pink);
}

.btn-red:hover {
  background: rgba(255, 45, 110, 0.1);
  box-shadow: 0 0 20px rgba(255, 45, 110, 0.3);
}

.btn-red.active {
  background: var(--pink);
  color: #fff;
  box-shadow: 0 0 30px rgba(255, 45, 110, 0.6);
  animation: pulse-red 2s infinite;
}

.btn-blue {
  border: 2px solid var(--cyan);
  color: var(--cyan);
}

.btn-blue:hover {
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}

.btn-blue.active {
  background: var(--cyan);
  color: #fff;
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.6);
  animation: pulse-blue 2s infinite;
}

.locked {
  font-family: var(--font-hd);
  font-size: 14px;
  font-weight: bold;
  padding: 15px;
}

.log-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  min-height: 0;
  background: #020305;
}

.log-title {
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 2px;
  margin-bottom: 10px;
}

.log-window {
  flex: 1;
  overflow-y: auto;
  font-family: var(--font-co);
  font-size: 12px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: rgba(0,0,0,0.5);
}

.log-entry {
  margin-bottom: 8px;
  line-height: 1.4;
  word-break: break-word;
}

.log-entry .ts {
  opacity: 0.6;
  margin-right: 8px;
}

.log-empty {
  color: var(--text);
  font-style: italic;
  opacity: 0.5;
  text-align: center;
  margin-top: 20px;
}

@keyframes pulse-red {
  0% { box-shadow: 0 0 20px rgba(255, 45, 110, 0.4); }
  50% { box-shadow: 0 0 40px rgba(255, 45, 110, 0.8); }
  100% { box-shadow: 0 0 20px rgba(255, 45, 110, 0.4); }
}

@keyframes pulse-blue {
  0% { box-shadow: 0 0 20px rgba(0, 229, 255, 0.4); }
  50% { box-shadow: 0 0 40px rgba(0, 229, 255, 0.8); }
  100% { box-shadow: 0 0 20px rgba(0, 229, 255, 0.4); }
}

.sub-tab-bar {
  display: flex;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid var(--border);
  width: 100%;
}

.sub-tab {
  flex: 1;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 2px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  opacity: 0.7;
}

.sub-tab:hover {
  opacity: 1;
  color: var(--pink);
  text-shadow: 0 0 8px rgba(255, 45, 110, 0.4);
}

.sub-tab.active {
  opacity: 1;
  color: var(--pink);
  border-bottom: 2px solid var(--pink);
  text-shadow: 0 0 10px rgba(255, 45, 110, 0.6);
  background: rgba(255, 45, 110, 0.03);
}

.control-area.manual-mode {
  padding: 20px 30px;
}

.strike-form {
  width: 100%;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row label {
  font-family: var(--font-hd);
  font-size: 10px;
  color: var(--textwh);
  letter-spacing: 1.5px;
}

.cyber-select,
.cyber-input {
  background: rgba(1, 2, 4, 0.8) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px;
  color: #fff !important;
  font-family: var(--font-ui);
  font-size: 13px;
  padding: 8px 12px;
  width: 100%;
  transition: all 0.2s ease;
  outline: none;
}

.cyber-select:focus,
.cyber-input:focus {
  border-color: var(--pink) !important;
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.2);
}

.cyber-select option {
  background: #0d121f;
  color: #fff;
}

.btn-strike {
  width: 100%;
  margin-top: 8px;
}

.strike-result {
  font-family: var(--font-co);
  font-size: 11px;
  padding: 10px;
  background: rgba(255, 45, 110, 0.05);
  border: 1px dashed rgba(255, 45, 110, 0.3);
  border-radius: 4px;
  text-align: center;
  text-shadow: 0 0 5px var(--pink);
}

.animate-flash {
  animation: log-flash 0.5s ease-out;
}

@keyframes log-flash {
  0% { opacity: 0; background: rgba(255, 45, 110, 0.2); }
  100% { opacity: 1; background: rgba(255, 45, 110, 0.05); }
}
</style>
