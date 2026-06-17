<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="cyber-modal-card scanner-modal">
      <div class="cyber-modal-header">
        <div class="modal-title">🕸️ SUBNET SCANNER: {{ networkBase }}</div>
        <button class="btn-close-modal" @click="$emit('close')">×</button>
      </div>
      <div class="cyber-modal-body">
        
        <div class="topology-grid">
          <div v-for="dev in devices" :key="dev.ip" class="topo-node">
            <div class="topo-icon">💻</div>
            <div class="topo-ip">{{ dev.ip }}</div>
            <div class="topo-mac">{{ dev.mac }}</div>
            <div class="topo-actions">
              <button class="btn-action btn-danger btn-attack" @click="openAttackModal(dev.ip)">[ ATTACK ]</button>
            </div>
          </div>
        </div>

        <div v-if="devices.length === 0" class="empty-state">NO DEVICES FOUND ON LOCAL NETWORK...</div>
      </div>
      <div class="cyber-modal-footer">
        <div class="scan-status" v-if="lastScan">
          <span class="text-cyan">LAST SCAN:</span> {{ lastScan }}
        </div>
        <button class="btn-action" @click="$emit('close')">CLOSE</button>
      </div>
    </div>

    <!-- Sub Modal for Brute Force Attack -->
    <div v-if="attackTarget" class="modal-overlay" style="z-index: 1000" @click.self="attackTarget = null">
      <div class="cyber-modal-card" style="width: 400px">
        <div class="cyber-modal-header">
          <div class="modal-title" style="color: var(--pink)">💥 LAUNCH BRUTE FORCE</div>
          <button class="btn-close-modal" @click="attackTarget = null">×</button>
        </div>
        <div class="cyber-modal-body" style="text-align: center">
          <p style="color: #a0a0a0; margin-bottom: 20px;">TARGET NODE: <strong style="color: #00e5ff">{{ attackTarget }}</strong></p>
          <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button class="btn-action btn-danger" @click="launchAttack('ssh')">[ CRACK SSH ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('ftp')">[ CRACK FTP ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('mysql')">[ CRACK MYSQL ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('postgres')">[ CRACK POSTGRES ]</button>
            <button class="btn-action btn-warning" @click="launchRecon('vmware')">[ VMWare RECON ]</button>
            <button class="btn-action btn-warning" @click="launchRecon('docker')">[ Docker RECON ]</button>
          </div>
          <div v-if="attackStatus" style="margin-top: 15px; color: var(--pink); font-family: monospace; text-shadow: 0 0 8px var(--pink); font-weight: bold;">{{ attackStatus }}</div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

const props = defineProps<{
  dataRaw: string
  nodeId: string
}>()

const emit = defineEmits(['close'])

const devices = ref<any[]>([])
const networkBase = ref('UNKNOWN LAN')
const lastScan = ref('')

const attackTarget = ref<string | null>(null)
const attackStatus = ref('')

function openAttackModal(ip: string) {
  attackTarget.value = ip
  attackStatus.value = ''
}

async function launchAttack(service: string) {
  if (!attackTarget.value || !props.nodeId) return
  
  attackStatus.value = 'Deploying payload...'
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/agents/attack/bruteforce`, {
      method: 'POST',
      headers: { 
        'Authorization': 'Bearer ' + localStorage.getItem('nr_token'),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: attackTarget.value,
        service: service
      })
    })
    
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || data.message || 'Attack failed')
    
    if (data.credentials) {
      attackStatus.value = `CRACKED! User: ${data.credentials.username} | Pass: ${data.credentials.password}`
    } else {
      attackStatus.value = data.message || 'Attack launched!'
    }
    
    setTimeout(() => {
      attackTarget.value = null
    }, 5000)
  } catch(err: any) {
    attackStatus.value = 'ERROR: ' + err.message
  }
}

async function launchRecon(type: string) {
  if (!attackTarget.value || !props.nodeId) return
  
  attackStatus.value = `Deploying ${type.toUpperCase()} recon payload...`
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/agents/attack/${type}`, {
      method: 'POST',
      headers: { 
        'Authorization': 'Bearer ' + localStorage.getItem('nr_token'),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: attackTarget.value
      })
    })
    
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || data.message || 'Recon failed')
    
    attackStatus.value = data.message || 'Recon launched!'
    setTimeout(() => {
      attackTarget.value = null
    }, 2000)
  } catch(err: any) {
    attackStatus.value = 'ERROR: ' + err.message
  }
}

function parseData(raw: string) {
  try {
    const data = JSON.parse(raw)
    devices.value = data.devices || []
    networkBase.value = data.network || 'UNKNOWN LAN'
    if (data.timestamp) {
      lastScan.value = new Date(data.timestamp * 1000).toLocaleTimeString()
    }
  } catch (e) {
    // If it's a JSONL or malformed
    devices.value = []
  }
}

watch(() => props.dataRaw, (newVal) => {
  parseData(newVal)
}, { immediate: true })

</script>

<style scoped>
.scanner-modal {
  width: 700px;
  max-width: 95vw;
}

.topology-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  padding: 10px;
  max-height: 50vh;
  overflow-y: auto;
}

.topo-node {
  background: rgba(10, 15, 20, 0.8);
  border: 1px solid var(--cyan-d);
  padding: 15px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 120px;
  transition: all 0.2s;
}

.topo-node:hover {
  background: rgba(0, 229, 255, 0.1);
  border-color: var(--cyan);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 229, 255, 0.15);
}

.topo-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.topo-ip {
  color: var(--textwh);
  font-family: var(--font-co);
  font-size: 11px;
  font-weight: bold;
}

.topo-mac {
  color: #888;
  font-family: var(--font-co);
  font-size: 9px;
  margin-top: 4px;
}

.empty-state {
  padding: 20px;
  text-align: center;
  color: #666;
  font-family: var(--font-hd);
  letter-spacing: 2px;
}

.scan-status {
  font-family: var(--font-co);
  font-size: 10px;
  flex-grow: 1;
}
.text-cyan { color: var(--cyan); }

.btn-attack {
  width: 100%;
  padding: 6px;
  font-family: var(--font-hd);
  letter-spacing: 1px;
  font-size: 9px;
  border-radius: 4px;
}
.topo-actions {
  margin-top: 15px;
  width: 100%;
}
.btn-danger { border-color: rgba(255, 45, 110, 0.4); color: var(--pink); background: rgba(255, 45, 110, 0.05); transition: all 0.2s;}
.btn-danger:hover:not(:disabled) {
  background: rgba(255, 45, 110, 0.15);
  border-color: #ff0055;
  color: #fff;
  box-shadow: 0 0 15px #ff0055, inset 0 0 10px rgba(255, 0, 85, 0.2);
  text-shadow: 0 0 5px #ff0055;
}
</style>
