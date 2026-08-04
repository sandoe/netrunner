<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import AttackToolLayout from '@/components/AttackToolLayout.vue'
import LogTerminal from '@/components/LogTerminal.vue'

const activeTab = ref('syn_flood')

// Logs
const terminalLogs = ref<string[]>([])

function log(msg: string) {
  const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
  terminalLogs.value.push(`[${timestamp}] ${msg}`)
}

const tabs = [
  { id: 'syn_flood', label: 'TCP SYN FLOOD' },
  { id: 'udp_flood', label: 'UDP FLOOD' },
  { id: 'tcp_rst', label: 'TCP RST HIJACK' },
  { id: 'ack_flood', label: 'TCP ACK FLOOD' },
]

// TCP SYN Flood State
const synTarget = ref('192.168.1.100')
const synPort = ref(80)

async function runSynFlood() {
  log(`> Launching TCP SYN Flood against ${synTarget.value}:${synPort.value}...`)
  try {
    const { data: res } = await api.post('/api/layer4/syn-flood', {
      target_ip: synTarget.value,
      target_port: synPort.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] SYN Flood failed: ${err.message}`)
  }
}

// UDP Flood State
const udpTarget = ref('192.168.1.100')
const udpPort = ref(53)

async function runUdpFlood() {
  log(`> Launching UDP Flood against ${udpTarget.value}:${udpPort.value}...`)
  try {
    const { data: res } = await api.post('/api/layer4/udp-flood', {
      target_ip: udpTarget.value,
      target_port: udpPort.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] UDP Flood failed: ${err.message}`)
  }
}

// TCP RST Hijack State
const rstTargetIp = ref('192.168.1.100')
const rstTargetPort = ref(80)
const rstSourceIp = ref('10.0.0.5')
const rstSourcePort = ref(45212)

async function runTcpRst() {
  log(`> Injecting TCP RST into session ${rstSourceIp.value}:${rstSourcePort.value} -> ${rstTargetIp.value}:${rstTargetPort.value}...`)
  try {
    const { data: res } = await api.post('/api/layer4/tcp-rst', {
      target_ip: rstTargetIp.value,
      target_port: rstTargetPort.value,
      source_ip: rstSourceIp.value,
      source_port: rstSourcePort.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] TCP RST Injection failed: ${err.message}`)
  }
}

// TCP ACK Flood State
const ackTarget = ref('192.168.1.100')
const ackPort = ref(443)

async function runAckFlood() {
  log(`> Launching TCP ACK Flood against ${ackTarget.value}:${ackPort.value}...`)
  try {
    const { data: res } = await api.post('/api/layer4/ack-flood', {
      target_ip: ackTarget.value,
      target_port: ackPort.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] ACK Flood failed: ${err.message}`)
  }
}

</script>

<template>
  <AttackToolLayout
    title="L4 TACTICAL"
    titleClass="title-l4"
    themeClass="theme-l4"
    :tabs="tabs"
    v-model:activeTab="activeTab"
  >

        <template v-if="activeTab === 'syn_flood'">
          <h3>TCP SYN FLOOD</h3>
          <p class="description">Overwhelm the target's half-open connection queue by flooding it with SYN packets and ignoring the SYN-ACKs.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="synTarget" type="text" />
          </div>
          <div class="form-group">
            <label>Target Port</label>
            <input v-model="synPort" type="number" />
          </div>
          <button class="btn btn-danger" @click="runSynFlood">LAUNCH SYN FLOOD</button>
        </template>

        <template v-if="activeTab === 'udp_flood'">
          <h3>UDP FLOOD</h3>
          <p class="description">Flood the target with massive amounts of UDP packets, forcing it to consume resources replying with ICMP Destination Unreachable.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="udpTarget" type="text" />
          </div>
          <div class="form-group">
            <label>Target Port</label>
            <input v-model="udpPort" type="number" />
          </div>
          <button class="btn btn-danger" @click="runUdpFlood">LAUNCH UDP FLOOD</button>
        </template>

        <template v-if="activeTab === 'tcp_rst'">
          <h3>TCP RST HIJACKING</h3>
          <p class="description">Inject a forged TCP Reset (RST) packet into an established session to abruptly terminate the connection.</p>
          <div class="form-group">
            <label>Target IP (Server)</label>
            <input v-model="rstTargetIp" type="text" />
          </div>
          <div class="form-group">
            <label>Target Port</label>
            <input v-model="rstTargetPort" type="number" />
          </div>
          <div class="form-group">
            <label>Source IP (Client)</label>
            <input v-model="rstSourceIp" type="text" />
          </div>
          <div class="form-group">
            <label>Source Port</label>
            <input v-model="rstSourcePort" type="number" />
          </div>
          <button class="btn btn-primary" @click="runTcpRst">INJECT TCP RST</button>
        </template>

        <template v-if="activeTab === 'ack_flood'">
          <h3>TCP ACK FLOOD</h3>
          <p class="description">Flood the target with forged ACK packets to exhaust state tables in Firewalls and IPS systems.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="ackTarget" type="text" />
          </div>
          <div class="form-group">
            <label>Target Port</label>
            <input v-model="ackPort" type="number" />
          </div>
          <button class="btn btn-danger" @click="runAckFlood">LAUNCH ACK FLOOD</button>
        </template>
    <template #terminal>
      <LogTerminal :logs="terminalLogs" />
    </template>
  </AttackToolLayout>
</template>
