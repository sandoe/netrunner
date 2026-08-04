<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import AttackToolLayout from '@/components/AttackToolLayout.vue'
import LogTerminal from '@/components/LogTerminal.vue'

const activeTab = ref('arp')

// Logs
const terminalLogs = ref<string[]>([])

function log(msg: string) {
  const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
  terminalLogs.value.push(`[${timestamp}] ${msg}`)
}

const tabs = [
  { id: 'arp', label: 'ARP SPOOFING' },
  { id: 'stp', label: 'STP TAKEOVER' },
  { id: 'vlan', label: 'VLAN HOPPING' },
  { id: 'flood', label: 'MAC FLOODING' },
  { id: 'cdp', label: 'CDP/LLDP SNIFF' },
  { id: 'dhcp_starve', label: 'DHCP STARVATION' },
  { id: 'rogue_dhcp', label: 'ROGUE DHCP' },
  { id: 'mac_spoof', label: 'MAC SPOOFING' },
  { id: 'vtp_bomb', label: 'VTP BOMBING' },
  { id: 'ndp_spoof', label: 'NDP SPOOFING (IPv6)' },
]

// ARP Spoofing State
const arpTargetIp = ref('192.168.1.100')
const arpGatewayIp = ref('192.168.1.1')
const arpInterface = ref('eth0')

async function runArpSpoof() {
  log(`> Init ARP Poisoning on ${arpInterface.value} (Target: ${arpTargetIp.value}, Gateway: ${arpGatewayIp.value})`)
  try {
    const { data: res } = await api.post('/api/layer2/arp-spoof', {
      target_ip: arpTargetIp.value,
      gateway_ip: arpGatewayIp.value,
      interface: arpInterface.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] ARP spoof failed: ${err.message}`)
  }
}

// STP Takeover State
const stpInterface = ref('eth0')
const stpPriority = ref(0)

async function runStpTakeover() {
  log(`> Transmitting BPDUs on ${stpInterface.value} with priority ${stpPriority.value}`)
  try {
    const { data: res } = await api.post('/api/layer2/stp-takeover', {
      interface: stpInterface.value,
      bridge_priority: stpPriority.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] STP takeover failed: ${err.message}`)
  }
}

// VLAN Hopping State
const vlanHopInterface = ref('eth0')
const vlanHopTarget = ref(10)

async function runVlanHop() {
  log(`> Initializing Double-Tagging attack on ${vlanHopInterface.value} targeting VLAN ${vlanHopTarget.value}`)
  try {
    const { data: res } = await api.post('/api/layer2/vlan-hop', {
      interface: vlanHopInterface.value,
      target_vlan: vlanHopTarget.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] VLAN hop failed: ${err.message}`)
  }
}

// MAC Flooding State
const macFloodInterface = ref('eth0')
const macFloodCount = ref(50000)

async function runMacFlood() {
  log(`> Flooding CAM table via ${macFloodInterface.value} (${macFloodCount.value} packets)`)
  try {
    const { data: res } = await api.post('/api/layer2/mac-flood', {
      interface: macFloodInterface.value,
      packets: macFloodCount.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] MAC flood failed: ${err.message}`)
  }
}

// CDP/LLDP State
const discoveredDevices = ref<any[]>([])

async function runCdpSniff() {
  log('> Listening for CDP/LLDP discovery packets...')
  try {
    const { data: res } = await api.get('/api/layer2/cdp-sniff')
    log(`[SUCCESS] Intercepted discovery packets!`)
    discoveredDevices.value = res.devices
    res.devices.forEach((d: any) => {
      log(`Found: ${d.type} (${d.ip}) on port ${d.port} (VLAN ${d.vlan})`)
    })
  } catch (err: any) {
    log(`[ERROR] Discovery sniff failed: ${err.message}`)
  }
}

// DHCP Starvation State
const dhcpStarveInterface = ref('eth0')
const dhcpStarveCount = ref(254)

async function runDhcpStarve() {
  log(`> Initiating DHCP Starvation on ${dhcpStarveInterface.value}...`)
  try {
    const { data: res } = await api.post('/api/layer2/dhcp-starve', {
      interface: dhcpStarveInterface.value,
      pool_size: dhcpStarveCount.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] DHCP starvation failed: ${err.message}`)
  }
}

// Rogue DHCP State
const rogueDhcpInterface = ref('eth0')
const fakeGateway = ref('192.168.1.200')
const fakeDns = ref('192.168.1.200')
const offerRange = ref('192.168.1.201-250')

async function runRogueDhcp() {
  log(`> Starting Rogue DHCP Server on ${rogueDhcpInterface.value}...`)
  try {
    const { data: res } = await api.post('/api/layer2/rogue-dhcp', {
      interface: rogueDhcpInterface.value,
      fake_gateway: fakeGateway.value,
      fake_dns: fakeDns.value,
      offer_ip_range: offerRange.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] Rogue DHCP failed: ${err.message}`)
  }
}

// MAC Spoofing State
const macSpoofInterface = ref('eth0')
const targetMac = ref('00:11:22:33:44:55')

async function runMacSpoof() {
  log(`> Spoofing MAC address on ${macSpoofInterface.value} to ${targetMac.value}...`)
  try {
    const { data: res } = await api.post('/api/layer2/mac-spoof', {
      interface: macSpoofInterface.value,
      target_mac: targetMac.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] MAC spoofing failed: ${err.message}`)
  }
}

// VTP Bomb State
const vtpBombInterface = ref('eth0')
const vtpDomain = ref('CORP_VLAN')
const vtpPassword = ref('')
const vtpRevision = ref(2147483647)

async function runVtpBomb() {
  log(`> Sending VTP Bomb on ${vtpBombInterface.value} (Domain: ${vtpDomain.value})...`)
  try {
    const { data: res } = await api.post('/api/layer2/vtp-bomb', {
      interface: vtpBombInterface.value,
      vtp_domain: vtpDomain.value,
      vtp_password: vtpPassword.value,
      revision_number: vtpRevision.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] VTP Bomb failed: ${err.message}`)
  }
}

// NDP Spoofing State
const ndpSpoofInterface = ref('eth0')
const ndpTarget = ref('fe80::100')
const ndpGateway = ref('fe80::1')

async function runNdpSpoof() {
  log(`> Init IPv6 NDP Spoofing on ${ndpSpoofInterface.value} (Target: ${ndpTarget.value})...`)
  try {
    const { data: res } = await api.post('/api/layer2/ndp-spoof', {
      interface: ndpSpoofInterface.value,
      target_ipv6: ndpTarget.value,
      gateway_ipv6: ndpGateway.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] NDP Spoofing failed: ${err.message}`)
  }
}
</script>

<template>
  <AttackToolLayout
    title="L2 TACTICAL"
    titleClass="title-l2"
    themeClass="theme-l2"
    :tabs="tabs"
    v-model:activeTab="activeTab"
  >

        <template v-if="activeTab === 'arp'">
          <h3>ARP SPOOFING</h3>
          <p class="description">Poison the ARP cache of the target and gateway to intercept traffic.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="arpInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="arpTargetIp" type="text" />
          </div>
          <div class="form-group">
            <label>Gateway IP</label>
            <input v-model="arpGatewayIp" type="text" />
          </div>
          <button class="btn btn-danger" @click="runArpSpoof">ENGAGE ARP POISONING</button>
        </template>

        <template v-if="activeTab === 'stp'">
          <h3>STP TAKEOVER</h3>
          <p class="description">Broadcast forged BPDU packets with a priority of 0 to become the Root Bridge.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="stpInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Bridge Priority</label>
            <input v-model.number="stpPriority" type="number" />
          </div>
          <button class="btn btn-danger" @click="runStpTakeover">BROADCAST BPDU</button>
        </template>

        <template v-if="activeTab === 'vlan'">
          <h3>VLAN HOPPING</h3>
          <p class="description">Send 802.1Q double-tagged frames or DTP negotiation packets to access unauthorized VLANs.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="vlanHopInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Target VLAN ID</label>
            <input v-model.number="vlanHopTarget" type="number" />
          </div>
          <button class="btn btn-danger" @click="runVlanHop">INITIATE VLAN HOP</button>
        </template>

        <template v-if="activeTab === 'flood'">
          <h3>MAC FLOODING</h3>
          <p class="description">Overflow the switch's CAM table by flooding random MAC addresses, forcing the switch into hub-mode.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="macFloodInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Packet Count</label>
            <input v-model.number="macFloodCount" type="number" />
          </div>
          <button class="btn btn-danger" @click="runMacFlood">FLOOD CAM TABLE</button>
        </template>

        <template v-if="activeTab === 'cdp'">
          <h3>CDP/LLDP DISCOVERY</h3>
          <p class="description">Passively sniff the network for broadcasted Cisco Discovery or Link Layer Discovery packets.</p>
          <button class="btn btn-primary" @click="runCdpSniff">SNIFF DISCOVERY PACKETS</button>

          <div v-if="discoveredDevices.length > 0" class="device-list">
            <h4>DISCOVERED HARDWARE:</h4>
            <div v-for="(dev, idx) in discoveredDevices" :key="idx" class="device-item">
              <div><strong>{{ dev.type }}</strong> ({{ dev.ip }})</div>
              <div class="text-muted">Port: {{ dev.port }} | VLAN: {{ dev.vlan }}</div>
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'dhcp_starve'">
          <h3>DHCP STARVATION</h3>
          <p class="description">Flood the network with DHCP Discover packets to exhaust the DHCP IP pool.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="dhcpStarveInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Pool Size to Exhaust</label>
            <input v-model.number="dhcpStarveCount" type="number" />
          </div>
          <button class="btn btn-danger" @click="runDhcpStarve">STARVE DHCP</button>
        </template>

        <template v-if="activeTab === 'rogue_dhcp'">
          <h3>ROGUE DHCP SERVER</h3>
          <p class="description">Stand up a fake DHCP server to offer malicious gateway and DNS routing to clients.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="rogueDhcpInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Offer IP Range</label>
            <input v-model="offerRange" type="text" />
          </div>
          <div class="form-group">
            <label>Fake Gateway</label>
            <input v-model="fakeGateway" type="text" />
          </div>
          <div class="form-group">
            <label>Fake DNS</label>
            <input v-model="fakeDns" type="text" />
          </div>
          <button class="btn btn-danger" @click="runRogueDhcp">START ROGUE SERVER</button>
        </template>

        <template v-if="activeTab === 'mac_spoof'">
          <h3>MAC SPOOFING / CLONING</h3>
          <p class="description">Change your interface's physical hardware address to bypass port security or impersonate devices.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="macSpoofInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Target MAC Address</label>
            <input v-model="targetMac" type="text" />
          </div>
          <button class="btn btn-danger" @click="runMacSpoof">SPOOF MAC</button>
        </template>

        <template v-if="activeTab === 'vtp_bomb'">
          <h3>VTP BOMBING</h3>
          <p class="description">Inject a VTP frame with a maximum revision number to delete all VLANs across the VTP domain.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="vtpBombInterface" type="text" />
          </div>
          <div class="form-group">
            <label>VTP Domain Name</label>
            <input v-model="vtpDomain" type="text" />
          </div>
          <div class="form-group">
            <label>VTP Password (Optional)</label>
            <input v-model="vtpPassword" type="text" />
          </div>
          <button class="btn btn-danger" @click="runVtpBomb">DEPLOY VTP BOMB</button>
        </template>

        <template v-if="activeTab === 'ndp_spoof'">
          <h3>IPv6 NDP SPOOFING</h3>
          <p class="description">Poison the IPv6 Neighbor Discovery cache (similar to ARP spoofing) to intercept IPv6 traffic.</p>
          <div class="form-group">
            <label>Interface</label>
            <input v-model="ndpSpoofInterface" type="text" />
          </div>
          <div class="form-group">
            <label>Target IPv6</label>
            <input v-model="ndpTarget" type="text" />
          </div>
          <div class="form-group">
            <label>Gateway IPv6</label>
            <input v-model="ndpGateway" type="text" />
          </div>
          <button class="btn btn-danger" @click="runNdpSpoof">ENGAGE NDP SPOOFING</button>
        </template>
    <template #terminal>
      <LogTerminal :logs="terminalLogs" />
    </template>
  </AttackToolLayout>
</template>
