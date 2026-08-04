<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import AttackToolLayout from '@/components/AttackToolLayout.vue'
import LogTerminal from '@/components/LogTerminal.vue'

const activeTab = ref('smb')

// Logs
const terminalLogs = ref<string[]>([])

function log(msg: string) {
  const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
  terminalLogs.value.push(`[${timestamp}] ${msg}`)
}

const tabs = [
  { id: 'smb', label: 'SMB RELAY' },
  { id: 'nfs', label: 'NFS SPOOFING' },
  { id: 'rpc', label: 'RPC MAPPING' },
  { id: 'hijack', label: 'SESSION HIJACK' },
  { id: 'socks', label: 'SOCKS TUNNEL' },
]

// SMB Relay State
const smbTargetIp = ref('192.168.1.50')
const smbInterface = ref('eth0')

async function runSmbRelay() {
  log(`> Init SMB Relay on ${smbInterface.value} targeting ${smbTargetIp.value}...`)
  try {
    const { data: res } = await api.post('/api/layer5/smb-relay', {
      target_ip: smbTargetIp.value,
      listen_interface: smbInterface.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] SMB Relay failed: ${err.message}`)
  }
}

// NFS Spoofing State
const nfsTargetIp = ref('10.0.0.10')
const nfsShare = ref('/var/nfs/general')
const nfsSpoofIp = ref('10.0.0.5')

async function runNfsSpoof() {
  log(`> Forging NFS Mount Request to ${nfsTargetIp.value}:${nfsShare.value} as ${nfsSpoofIp.value}...`)
  try {
    const { data: res } = await api.post('/api/layer5/nfs-spoof', {
      target_ip: nfsTargetIp.value,
      target_share: nfsShare.value,
      spoofed_ip: nfsSpoofIp.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] NFS Spoofing failed: ${err.message}`)
  }
}

// RPC Enum State
const rpcTargetIp = ref('192.168.1.10')
const discoveredEndpoints = ref<any[]>([])

async function runRpcEnum() {
  log(`> Enumerating RPC Endpoints on ${rpcTargetIp.value}...`)
  try {
    const { data: res } = await api.post('/api/layer5/rpc-enum', {
      target_ip: rpcTargetIp.value
    })
    log(`[SUCCESS] ${res.message}`)
    discoveredEndpoints.value = res.endpoints
    res.endpoints.forEach((e: any) => {
      log(`Found: Port ${e.port} (${e.service}) - ${e.status}`)
    })
  } catch (err: any) {
    log(`[ERROR] RPC Enum failed: ${err.message}`)
  }
}

// Session Hijack State
const hijackTargetIp = ref('192.168.1.100')
const hijackTargetPort = ref(80)
const hijackSessionId = ref('A7B8C9D0')

async function runSessionHijack() {
  log(`> Attempting sequence prediction and hijacking for session ${hijackSessionId.value}...`)
  try {
    const { data: res } = await api.post('/api/layer5/session-hijack', {
      target_ip: hijackTargetIp.value,
      target_port: hijackTargetPort.value,
      session_id: hijackSessionId.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] Session Hijack failed: ${err.message}`)
  }
}

// SOCKS Tunnel State
const socksListenPort = ref(1080)
const socksForwardIp = ref('10.0.0.20')

async function runSocksTunnel() {
  log(`> Opening SOCKS proxy on port ${socksListenPort.value} routing to ${socksForwardIp.value}...`)
  try {
    const { data: res } = await api.post('/api/layer5/socks-tunnel', {
      listen_port: socksListenPort.value,
      forward_ip: socksForwardIp.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] SOCKS Tunnel failed: ${err.message}`)
  }
}
</script>

<template>
  <AttackToolLayout
    title="L5 TACTICAL"
    titleClass="title-l5"
    themeClass="theme-l5"
    :tabs="tabs"
    v-model:activeTab="activeTab"
  >

        <template v-if="activeTab === 'smb'">
          <h3>SMB RELAY</h3>
          <p class="description">Intercept NTLM authentication requests and relay them to a target machine to gain unauthorized access.</p>
          <div class="form-group">
            <label>Listen Interface</label>
            <input v-model="smbInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="smbTargetIp" type="text" />
          </div>
          <button class="btn btn-danger" @click="runSmbRelay">START SMB RELAY</button>
        </template>

        <template v-if="activeTab === 'nfs'">
          <h3>NFS SPOOFING</h3>
          <p class="description">Spoof an authorized client IP address to mount unsecured Network File System (NFS) exports.</p>
          <div class="form-group">
            <label>Target Server IP</label>
            <input v-model="nfsTargetIp" type="text" />
          </div>
          <div class="form-group">
            <label>Target Share Path</label>
            <input v-model="nfsShare" type="text" />
          </div>
          <div class="form-group">
            <label>Spoofed Source IP</label>
            <input v-model="nfsSpoofIp" type="text" />
          </div>
          <button class="btn btn-danger" @click="runNfsSpoof">FORGE MOUNT REQUEST</button>
        </template>

        <template v-if="activeTab === 'rpc'">
          <h3>RPC ENDPOINT ENUMERATION</h3>
          <p class="description">Query the RPC endpoint mapper (port 135) to list exposed services and dynamic ports.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="rpcTargetIp" type="text" />
          </div>
          <button class="btn btn-primary" @click="runRpcEnum">ENUMERATE RPC</button>

          <div v-if="discoveredEndpoints.length > 0" class="device-list">
            <h4>DISCOVERED SERVICES:</h4>
            <div v-for="(ep, idx) in discoveredEndpoints" :key="idx" class="device-item">
              <div><strong>Port: {{ ep.port }}</strong> ({{ ep.service }})</div>
              <div class="text-muted">Status: {{ ep.status }}</div>
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'hijack'">
          <h3>SESSION HIJACKING</h3>
          <p class="description">Predict TCP sequences or steal tokens to hijack an active session between two hosts.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="hijackTargetIp" type="text" />
          </div>
          <div class="form-group">
            <label>Target Port</label>
            <input v-model.number="hijackTargetPort" type="number" />
          </div>
          <div class="form-group">
            <label>Session ID / Token (Optional)</label>
            <input v-model="hijackSessionId" type="text" />
          </div>
          <button class="btn btn-danger" @click="runSessionHijack">HIJACK SESSION</button>
        </template>

        <template v-if="activeTab === 'socks'">
          <h3>SOCKS PROXY TUNNEL</h3>
          <p class="description">Establish a SOCKS5 proxy tunnel through a compromised session to pivot further into the network.</p>
          <div class="form-group">
            <label>Local Listen Port</label>
            <input v-model.number="socksListenPort" type="number" />
          </div>
          <div class="form-group">
            <label>Forward Target IP</label>
            <input v-model="socksForwardIp" type="text" />
          </div>
          <button class="btn btn-danger" @click="runSocksTunnel">OPEN PROXY TUNNEL</button>
        </template>
    <template #terminal>
      <LogTerminal :logs="terminalLogs" />
    </template>
  </AttackToolLayout>
</template>
