<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import AttackToolLayout from '@/components/AttackToolLayout.vue'
import LogTerminal from '@/components/LogTerminal.vue'

const activeTab = ref('icmp_redirect')

// Logs
const terminalLogs = ref<string[]>([])

function log(msg: string) {
  const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
  terminalLogs.value.push(`[${timestamp}] ${msg}`)
}

const tabs = [
  { id: 'icmp_redirect', label: 'ICMP REDIRECT' },
  { id: 'ping_of_death', label: 'PING OF DEATH' },
  { id: 'icmp_tunnel', label: 'ICMP TUNNEL' },
  { id: 'ip_frag', label: 'IP FRAGMENTATION' },
  { id: 'ospf_inject', label: 'OSPF INJECTION' },
]

// ICMP Redirect State
const icmpRedirectTarget = ref('192.168.1.100')
const icmpRedirectGateway = ref('192.168.1.1')
const icmpRedirectNewGateway = ref('192.168.1.200')

async function runIcmpRedirect() {
  log(`> Sending ICMP Redirect to ${icmpRedirectTarget.value}...`)
  try {
    const { data: res } = await api.post('/api/layer3/icmp-redirect', {
      target_ip: icmpRedirectTarget.value,
      gateway_ip: icmpRedirectGateway.value,
      new_gateway_ip: icmpRedirectNewGateway.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] ICMP Redirect failed: ${err.message}`)
  }
}

// Ping of Death State
const podTarget = ref('192.168.1.100')

async function runPingOfDeath() {
  log(`> Launching Ping of Death against ${podTarget.value}...`)
  try {
    const { data: res } = await api.post('/api/layer3/ping-of-death', {
      target_ip: podTarget.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] Ping of Death failed: ${err.message}`)
  }
}

// ICMP Tunnel State
const tunnelServer = ref('203.0.113.50')

async function runIcmpTunnel() {
  log(`> Establishing ICMP Tunnel to ${tunnelServer.value}...`)
  try {
    const { data: res } = await api.post('/api/layer3/icmp-tunnel', {
      server_ip: tunnelServer.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] ICMP Tunnel failed: ${err.message}`)
  }
}

// IP Fragmentation State
const ipFragTarget = ref('192.168.1.100')

async function runIpFragmentation() {
  log(`> Starting IP Fragmentation attack against ${ipFragTarget.value}...`)
  try {
    const { data: res } = await api.post('/api/layer3/ip-fragmentation', {
      target_ip: ipFragTarget.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] IP Fragmentation failed: ${err.message}`)
  }
}

// OSPF Route Inject State
const ospfInterface = ref('eth0')
const ospfFakeNetwork = ref('10.0.99.0/24')

async function runOspfInject() {
  log(`> Injecting fake OSPF route ${ospfFakeNetwork.value} on ${ospfInterface.value}...`)
  try {
    const { data: res } = await api.post('/api/layer3/ospf-route-inject', {
      interface: ospfInterface.value,
      fake_network: ospfFakeNetwork.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] OSPF Route Injection failed: ${err.message}`)
  }
}
</script>

<template>
  <AttackToolLayout
    title="L3 TACTICAL"
    titleClass="title-l3"
    themeClass="theme-l3"
    :tabs="tabs"
    v-model:activeTab="activeTab"
  >

        <template v-if="activeTab === 'icmp_redirect'">
          <h3>ICMP REDIRECT</h3>
          <p class="description">Send fake ICMP Redirect messages to trick a host into altering its routing table.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="icmpRedirectTarget" type="text" />
          </div>
          <div class="form-group">
            <label>Current Gateway IP</label>
            <input v-model="icmpRedirectGateway" type="text" />
          </div>
          <div class="form-group">
            <label>New (Fake) Gateway IP</label>
            <input v-model="icmpRedirectNewGateway" type="text" />
          </div>
          <button class="btn btn-danger" @click="runIcmpRedirect">SEND ICMP REDIRECT</button>
        </template>

        <template v-if="activeTab === 'ping_of_death'">
          <h3>PING OF DEATH</h3>
          <p class="description">Send malformed or oversized ICMP packets to crash the target machine.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="podTarget" type="text" />
          </div>
          <button class="btn btn-danger" @click="runPingOfDeath">LAUNCH PING OF DEATH</button>
        </template>

        <template v-if="activeTab === 'icmp_tunnel'">
          <h3>ICMP TUNNELING</h3>
          <p class="description">Establish a covert channel by encapsulating data within ICMP Echo packets.</p>
          <div class="form-group">
            <label>Command & Control Server IP</label>
            <input v-model="tunnelServer" type="text" />
          </div>
          <button class="btn btn-primary" @click="runIcmpTunnel">ESTABLISH TUNNEL</button>
        </template>

        <template v-if="activeTab === 'ip_frag'">
          <h3>IP FRAGMENTATION</h3>
          <p class="description">Evade IDS/IPS and Firewalls by sending fragmented IP packets that are reassembled at the target.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="ipFragTarget" type="text" />
          </div>
          <button class="btn btn-danger" @click="runIpFragmentation">SEND FRAGMENTED PACKETS</button>
        </template>

        <template v-if="activeTab === 'ospf_inject'">
          <h3>OSPF ROUTE INJECTION</h3>
          <p class="description">Broadcast fake OSPF routing updates to hijack traffic intended for other networks.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="ospfInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Fake Network (CIDR)</label>
            <input v-model="ospfFakeNetwork" type="text" />
          </div>
          <button class="btn btn-danger" @click="runOspfInject">INJECT OSPF ROUTE</button>
        </template>
    <template #terminal>
      <LogTerminal :logs="terminalLogs" />
    </template>
  </AttackToolLayout>
</template>
