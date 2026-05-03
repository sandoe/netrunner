<template>
  <div class="config-panel">
    <div class="config-sidebar">
      <div v-for="(cat, key) in CONFIG_CATEGORIES" :key="key" class="cat-group">
        <div class="cat-label">{{ cat.icon }} {{ cat.label }}</div>
        <button
          v-for="item in cat.types"
          :key="item.type"
          class="type-btn"
          :class="{ active: activeType === item.type }"
          @click="selectType(item.type)"
        >{{ item.label }}</button>
      </div>
    </div>

    <div class="config-main">
      <div v-if="!activeType" class="placeholder">Select a configuration generator →</div>
      <div v-else class="config-editor">
        <div class="editor-header">
          <span class="type-name">{{ activeType }}</span>
          <div class="header-actions">
            <button class="btn-preview" @click="getPreview" :disabled="loading">👁 preview</button>
            <button class="btn-apply" @click="applyConfig" :disabled="loading || !previewCommands.length">🚀 apply</button>
          </div>
        </div>

        <div class="editor-body">
          <!-- Specialized IP Form -->
          <div v-if="activeType === 'ip'" class="specialized-form">
            <div class="form-row">
              <label>Interface
                <input v-model="ipForm.interface" placeholder="eth0" />
              </label>
              <label>IP Address / CIDR
                <input v-model="ipForm.address" placeholder="10.0.0.1/24" />
              </label>
              <label>Action
                <select v-model="ipForm.action">
                  <option value="add">Add</option>
                  <option value="del">Delete</option>
                  <option value="flush">Flush & Add</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Specialized Routes Form -->
          <div v-if="activeType === 'routes'" class="specialized-form">
            <div v-for="(route, idx) in routeForm.routes" :key="idx" class="form-row multi-row">
              <label>Destination
                <input v-model="route.dst" placeholder="10.1.0.0/24" />
              </label>
              <label>Gateway (via)
                <input v-model="route.via" placeholder="10.0.0.254" />
              </label>
              <label>Device
                <input v-model="route.dev" placeholder="eth0" />
              </label>
              <label>Metric
                <input v-model.number="route.metric" type="number" placeholder="100" />
              </label>
              <button class="btn-remove" @click="routeForm.routes.splice(idx, 1)">✕</button>
            </div>
            <div class="form-actions">
              <button class="btn-add-sub" @click="routeForm.routes.push({ dst: '', via: '', dev: '', metric: 0 })">+ Add Route</button>
              <label class="check-label">
                <input type="checkbox" v-model="routeForm.isDelete" /> Delete instead of Add
              </label>
            </div>
          </div>

          <!-- DHCP Form -->
          <div v-if="activeType === 'dhcp'" class="specialized-form">
            <div class="form-row">
              <label>Interface <input v-model="dhcpForm.interface" /></label>
              <label>Action
                <select v-model="dhcpForm.action">
                  <option value="renew">Renew / Start</option>
                  <option value="release">Release / Stop</option>
                </select>
              </label>
            </div>
          </div>

          <!-- DNS Form -->
          <div v-if="activeType === 'dns'" class="specialized-form">
            <div class="form-row">
              <label>Nameservers (CSV) <input v-model="dnsForm.nameservers" /></label>
              <label>Search Domains (CSV) <input v-model="dnsForm.search" /></label>
            </div>
            <div class="form-row">
              <label>Hostname <input v-model="dnsForm.hostname" /></label>
              <label>Domain <input v-model="dnsForm.domain" /></label>
            </div>
            <div class="section-label-sub">Static Host Records</div>
            <div v-for="(rec, i) in dnsForm.records" :key="i" class="form-row">
              <input v-model="rec.name" placeholder="name (e.g. router.local)" />
              <input v-model="rec.value" placeholder="IP address" />
              <button class="btn-remove" @click="dnsForm.records.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="dnsForm.records.push({ name: '', value: '' })">+ Add Record</button>
          </div>

          <!-- NAT Form -->
          <div v-if="activeType === 'nat'" class="specialized-form">
            <div class="form-row">
              <label>WAN (Outbound) <input v-model="natForm.outbound_iface" /></label>
              <label>LAN (Inbound) <input v-model="natForm.inbound_iface" /></label>
              <label>Source Subnet <input v-model="natForm.source_subnet" /></label>
            </div>
            <label class="check-label"><input type="checkbox" v-model="natForm.masquerade" /> Enable Masquerade</label>
            <div class="section-label-sub">Port Forwards</div>
            <div v-for="(f, i) in natForm.port_forwards" :key="i" class="form-row multi-row">
              <label>Ext Port <input v-model="f.external_port" /></label>
              <label>Target IP <input v-model="f.target_ip" /></label>
              <label>Int Port <input v-model="f.target_port" /></label>
              <label>Proto
                <select v-model="f.proto">
                  <option value="tcp">TCP</option>
                  <option value="udp">UDP</option>
                </select>
              </label>
              <button class="btn-remove" @click="natForm.port_forwards.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="natForm.port_forwards.push({ proto: 'tcp', external_port: '', target_ip: '', target_port: '' })">+ Add Forward</button>
          </div>

          <!-- VLAN Router Form -->
          <div v-if="activeType === 'vlan-router'" class="specialized-form">
            <div class="form-row">
              <label>Base Interface <input v-model="vlanRouterForm.interface" /></label>
            </div>
            <div class="section-label-sub">VLAN Interfaces</div>
            <div v-for="(v, i) in vlanRouterForm.vlans" :key="i" class="form-row multi-row">
              <label>VLAN ID <input v-model="v.id" /></label>
              <label>Address <input v-model="v.address" /></label>
              <label>Description <input v-model="v.description" /></label>
              <button class="btn-remove" @click="vlanRouterForm.vlans.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="vlanRouterForm.vlans.push({ id: '', address: '', description: '' })">+ Add VLAN</button>
          </div>

          <!-- VLAN Switch Form -->
          <div v-if="activeType === 'vlan-switch'" class="specialized-form">
            <div class="form-row">
              <label>Bridge Name <input v-model="vlanSwitchForm.bridge" /></label>
            </div>
            <div class="section-label-sub">VLAN Definitions</div>
            <div v-for="(v, i) in vlanSwitchForm.vlans" :key="i" class="form-row">
              <input v-model="v.id" placeholder="ID" />
              <input v-model="v.name" placeholder="Name" />
              <button class="btn-remove" @click="vlanSwitchForm.vlans.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="vlanSwitchForm.vlans.push({ id: '', name: '' })">+ Add VLAN</button>
            
            <div class="section-label-sub">Port Assignments</div>
            <div v-for="(p, i) in vlanSwitchForm.ports" :key="i" class="form-row multi-row">
              <label>Iface <input v-model="p.iface" /></label>
              <label>Mode
                <select v-model="p.mode">
                  <option value="access">Access</option>
                  <option value="trunk">Trunk</option>
                </select>
              </label>
              <label v-if="p.mode === 'access'">VLAN <input v-model="p.vlan" /></label>
              <label v-if="p.mode === 'trunk'">Allowed (CSV) <input v-model="p.allowed" /></label>
              <button class="btn-remove" @click="vlanSwitchForm.ports.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="vlanSwitchForm.ports.push({ iface: '', mode: 'access', vlan: '1', allowed: [] })">+ Add Port</button>
          </div>

          <!-- WireGuard Form -->
          <div v-if="activeType === 'wireguard'" class="specialized-form">
            <div class="form-row">
              <label>Interface <input v-model="wireguardForm.interface" /></label>
              <label>Address <input v-model="wireguardForm.address" /></label>
              <label>Listen Port <input v-model.number="wireguardForm.listen_port" type="number" /></label>
            </div>
            <label>Private Key <input v-model="wireguardForm.private_key" type="password" /></label>
            <div class="section-label-sub">Peers</div>
            <div v-for="(peer, i) in wireguardForm.peers" :key="i" class="form-row multi-row">
              <label>Public Key <input v-model="peer.public_key" /></label>
              <label>Endpoint <input v-model="peer.endpoint" /></label>
              <label>Allowed IPs <input v-model="peer.allowed_ips" /></label>
              <button class="btn-remove" @click="wireguardForm.peers.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="wireguardForm.peers.push({ public_key: '', endpoint: '', allowed_ips: '0.0.0.0/0' })">+ Add Peer</button>
          </div>

          <!-- IP Forwarding Form -->
          <div v-if="activeType === 'forwarding'" class="specialized-form">
            <div class="form-row">
              <label class="check-label"><input type="checkbox" v-model="forwardingForm.ipv4" /> IPv4 Forwarding</label>
              <label class="check-label"><input type="checkbox" v-model="forwardingForm.ipv6" /> IPv6 Forwarding</label>
            </div>
          </div>

          <!-- Reset Node Form -->
          <div v-if="activeType === 'reset-node'" class="specialized-form">
            <div class="warning-box">
              ⚠️ This will flush ALL network settings, firewall rules, and WireGuard tunnels.
            </div>
            <button class="btn-sync" @click="inputJson = '{}'">Prepare Reset ↓</button>
          </div>

          <!-- Linux Service Form -->
          <div v-if="activeType === 'service'" class="specialized-form">
            <div class="form-row">
              <label>Service Name <input v-model="serviceForm.name" placeholder="ssh, nginx, etc." /></label>
              <label>Action
                <select v-model="serviceForm.action">
                  <option value="status">Status</option>
                  <option value="start">Start</option>
                  <option value="stop">Stop</option>
                  <option value="restart">Restart</option>
                  <option value="enable">Enable (Boot)</option>
                  <option value="disable">Disable (Boot)</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Linux Package Form -->
          <div v-if="activeType === 'package'" class="specialized-form">
            <div class="form-row">
              <label>Packages (CSV) <input v-model="packageForm.packages" placeholder="curl, vim, htop" /></label>
              <label>Action
                <select v-model="packageForm.action">
                  <option value="install">Install</option>
                  <option value="remove">Remove</option>
                  <option value="update">Update / Upgrade All</option>
                </select>
              </label>
              <label>Manager
                <select v-model="packageForm.manager">
                  <option value="auto">Auto-detect</option>
                  <option value="apt">apt (Debian/Ubuntu)</option>
                  <option value="apk">apk (Alpine)</option>
                  <option value="yum">yum (CentOS/RHEL)</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Linux User Form -->
          <div v-if="activeType === 'user'" class="specialized-form">
            <div class="form-row">
              <label>Username <input v-model="userForm.username" /></label>
              <label>Action
                <select v-model="userForm.action">
                  <option value="create">Create</option>
                  <option value="modify">Modify</option>
                  <option value="passwd">Change Password</option>
                  <option value="delete">Delete</option>
                  <option value="sudo">Grant Sudo/Wheel</option>
                </select>
              </label>
            </div>
            <div class="form-row" v-if="userForm.action !== 'delete' && userForm.action !== 'sudo'">
              <label>Password <input v-model="userForm.password" type="password" /></label>
              <label>Groups (CSV) <input v-model="userForm.groups" /></label>
            </div>
            <div class="form-row" v-if="userForm.action === 'create' || userForm.action === 'modify'">
              <label>Shell <input v-model="userForm.shell" /></label>
              <label>Home Dir <input v-model="userForm.home" /></label>
              <label class="check-label"><input type="checkbox" v-model="userForm.system" /> System User</label>
            </div>
          </div>

          <!-- Hostname Form -->
          <div v-if="activeType === 'hostname'" class="specialized-form">
            <div class="form-row">
              <label>Hostname <input v-model="hostnameForm.hostname" /></label>
              <label>Domain <input v-model="hostnameForm.domain" /></label>
            </div>
          </div>

          <!-- Sysctl Form -->
          <div v-if="activeType === 'sysctl'" class="specialized-form">
            <div v-for="(p, i) in sysctlForm.params" :key="i" class="form-row">
              <input v-model="p.key" placeholder="net.ipv4.ip_forward" />
              <input v-model="p.value" placeholder="1" />
              <button class="btn-remove" @click="sysctlForm.params.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="sysctlForm.params.push({ key: '', value: '' })">+ Add Parameter</button>
            <label class="check-label"><input type="checkbox" v-model="sysctlForm.persist" /> Persist to /etc/sysctl.d/</label>
          </div>

          <!-- File Write Form -->
          <div v-if="activeType === 'file-write'" class="specialized-form">
            <div class="form-row">
              <label>File Path <input v-model="fileWriteForm.path" /></label>
              <label>Mode <input v-model="fileWriteForm.mode" /></label>
              <label>Owner <input v-model="fileWriteForm.owner" /></label>
            </div>
            <div class="input-section">
              <div class="section-label">File Content</div>
              <textarea v-model="fileWriteForm.content" class="json-textarea" style="height: 180px;"></textarea>
            </div>
            <label class="check-label"><input type="checkbox" v-model="fileWriteForm.backup" /> Create .bak before writing</label>
          </div>

          <div class="input-section">
            <div class="section-label">Data (JSON)<span v-if="activeType" class="auto-label"> — auto-generated</span></div>
            <textarea
              v-model="inputJson"
              class="json-textarea"
              spellcheck="false"
              placeholder='{ "interface": "eth0", "addresses": ["192.168.1.1/24"] }'
            ></textarea>
          </div>

          <div class="preview-section" v-if="previewCommands.length || previewError">
            <div class="section-label">Generated Commands</div>
            <div v-if="previewError" class="preview-error">{{ previewError }}</div>
            <pre v-else class="preview-pre">{{ previewCommands.join('\n') }}</pre>
          </div>

          <div class="results-section" v-if="results.length">
            <div class="section-label">Execution Results</div>
            <div v-for="(r, i) in results" :key="i" class="result-block">
              <div class="result-cmd">$ {{ r.command }}</div>
              <pre v-if="r.output" class="result-out">{{ r.output }}</pre>
              <pre v-if="r.error"  class="result-err">{{ r.error }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '@/api/client'
import type { CommandResult } from '@/types'

const props = defineProps<{ nodeId: string }>()

const CONFIG_CATEGORIES = {
  network: {
    icon: '🌐', label: 'Network',
    types: [
      { type: 'ip', label: 'IP Address' },
      { type: 'routes', label: 'Routes' },
      { type: 'dhcp', label: 'DHCP Client' },
      { type: 'dns', label: 'DNS / Resolver' },
      { type: 'nat', label: 'NAT / Forwarding' },
      { type: 'vlan-router', label: 'VLAN Router' },
      { type: 'vlan-switch', label: 'VLAN Switch' },
      { type: 'wireguard', label: 'WireGuard' },
      { type: 'forwarding', label: 'IP Forwarding' },
      { type: 'reset-node', label: 'Reset Node' },
    ]
  },
  linux: {
    icon: '🐧', label: 'Linux',
    types: [
      { type: 'service', label: 'Services' },
      { type: 'package', label: 'Packages' },
      { type: 'user', label: 'Users' },
      { type: 'hostname', label: 'Hostname' },
      { type: 'sysctl', label: 'Sysctl' },
      { type: 'file-write', label: 'Write File' },
    ]
  }
}

const activeType      = ref<string | null>(null)
const inputJson       = ref('{}')
const previewCommands = ref<string[]>([])
const previewError    = ref('')
const results         = ref<CommandResult[]>([])
const loading         = ref(false)

const ipForm = ref({
  interface: 'eth0',
  address: '10.0.0.1/24',
  action: 'add'
})

function syncIpForm() {
  inputJson.value = JSON.stringify({
    interface: ipForm.value.interface,
    addresses: [ipForm.value.address],
    action: ipForm.value.action
  }, null, 2)
}

const routeForm = ref({
  routes: [{ dst: '10.1.0.0/24', via: '10.0.0.254', dev: '', metric: 0 }],
  isDelete: false
})

const dhcpForm = ref({ interface: 'eth0', action: 'renew' })

const dnsForm = ref({
  nameservers: ['8.8.8.8'],
  search: ['local'],
  hostname: '',
  domain: '',
  records: [{ name: '', value: '' }]
})

const natForm = ref({
  outbound_iface: 'eth0',
  inbound_iface: 'eth1',
  source_subnet: '10.0.0.0/24',
  masquerade: true,
  port_forwards: [{ proto: 'tcp', external_port: '80', target_ip: '10.0.0.10', target_port: '80' }]
})

const vlanRouterForm = ref({
  interface: 'eth0',
  vlans: [{ id: '10', address: '10.0.10.1/24', description: 'Management' }]
})

const vlanSwitchForm = ref({
  bridge: 'br0',
  vlans: [{ id: '10', name: 'MGMT' }],
  ports: [{ iface: 'eth1', mode: 'access', vlan: '10', allowed: [] as string[] }]
})

const wireguardForm = ref({
  interface: 'wg0',
  private_key: '',
  address: '10.0.0.1/24',
  listen_port: 51820,
  peers: [{ public_key: '', endpoint: '', allowed_ips: '0.0.0.0/0' }]
})

const forwardingForm = ref({ ipv4: true, ipv6: false })

const serviceForm = ref({ name: '', action: 'status' })

const packageForm = ref({ packages: '', action: 'install', manager: 'auto' })

const userForm = ref({
  username: '', action: 'create', password: '',
  groups: '', shell: '/bin/bash', home: '', system: false
})

const hostnameForm = ref({ hostname: '', domain: '' })

const sysctlForm = ref({
  params: [{ key: 'net.ipv4.ip_forward', value: '1' }],
  persist: true
})

const fileWriteForm = ref({
  path: '/tmp/test.txt',
  content: '',
  mode: '644',
  owner: 'root',
  backup: false
})

function syncRouteForm() {
  inputJson.value = JSON.stringify({
    routes: routeForm.value.routes.filter(r => r.dst),
    action: routeForm.value.isDelete ? 'del' : 'add'
  }, null, 2)
}

function syncDhcpForm() {
  inputJson.value = JSON.stringify(dhcpForm.value, null, 2)
}

function syncDnsForm() {
  inputJson.value = JSON.stringify({
    ...dnsForm.value,
    records: dnsForm.value.records.filter(r => r.name)
  }, null, 2)
}

function syncNatForm() {
  inputJson.value = JSON.stringify({
    ...natForm.value,
    port_forwards: natForm.value.port_forwards.filter(f => f.external_port)
  }, null, 2)
}

function syncVlanRouterForm() {
  inputJson.value = JSON.stringify({
    ...vlanRouterForm.value,
    vlans: vlanRouterForm.value.vlans.filter(v => v.id)
  }, null, 2)
}

function syncVlanSwitchForm() {
  inputJson.value = JSON.stringify({
    ...vlanSwitchForm.value,
    vlans: vlanSwitchForm.value.vlans.filter(v => v.id),
    ports: vlanSwitchForm.value.ports.filter(p => p.iface)
  }, null, 2)
}

function syncWireguardForm() {
  inputJson.value = JSON.stringify({
    ...wireguardForm.value,
    peers: wireguardForm.value.peers.filter(p => p.public_key)
  }, null, 2)
}

function syncForwardingForm() {
  inputJson.value = JSON.stringify(forwardingForm.value, null, 2)
}

function syncServiceForm() {
  inputJson.value = JSON.stringify(serviceForm.value, null, 2)
}

function syncPackageForm() {
  inputJson.value = JSON.stringify({
    ...packageForm.value,
    packages: packageForm.value.packages.split(',').map(p => p.trim()).filter(Boolean)
  }, null, 2)
}

function syncUserForm() {
  inputJson.value = JSON.stringify({
    ...userForm.value,
    groups: userForm.value.groups.split(',').map(g => g.trim()).filter(Boolean)
  }, null, 2)
}

function syncHostnameForm() {
  inputJson.value = JSON.stringify(hostnameForm.value, null, 2)
}

function syncSysctlForm() {
  inputJson.value = JSON.stringify({
    ...sysctlForm.value,
    params: sysctlForm.value.params.filter(p => p.key)
  }, null, 2)
}

function syncFileWriteForm() {
  inputJson.value = JSON.stringify(fileWriteForm.value, null, 2)
}

const syncFnMap: Record<string, () => void> = {}

function selectType(type: string) {
  activeType.value = type
  previewCommands.value = []
  previewError.value = ''
  results.value = []
  if (syncFnMap[type]) syncFnMap[type]()
  else if (type === 'reset-node') inputJson.value = '{}'
  else inputJson.value = '{}'
}

async function getPreview() {
  previewError.value = ''
  previewCommands.value = []
  try {
    const data = JSON.parse(inputJson.value)
    const res = await api.preview(activeType.value!, data)
    previewCommands.value = res.commands
  } catch (e) {
    previewError.value = String(e)
  }
}

async function applyConfig() {
  if (!previewCommands.value.length) return
  loading.value = true
  results.value = []
  try {
    const res = await api.executeNode(props.nodeId, previewCommands.value)
    results.value = res.results
  } catch (e) {
    previewError.value = `Execution failed: ${e}`
  } finally {
    loading.value = false
  }
}

// Register sync functions so selectType can call them by key
syncFnMap.ip           = syncIpForm
syncFnMap.routes       = syncRouteForm
syncFnMap.dhcp         = syncDhcpForm
syncFnMap.dns          = syncDnsForm
syncFnMap.nat          = syncNatForm
syncFnMap['vlan-router']  = syncVlanRouterForm
syncFnMap['vlan-switch']  = syncVlanSwitchForm
syncFnMap.wireguard    = syncWireguardForm
syncFnMap.forwarding   = syncForwardingForm
syncFnMap.service      = syncServiceForm
syncFnMap.package      = syncPackageForm
syncFnMap.user         = syncUserForm
syncFnMap.hostname     = syncHostnameForm
syncFnMap.sysctl       = syncSysctlForm
syncFnMap['file-write'] = syncFileWriteForm

// Auto-update JSON as form fields change
watch(ipForm,          () => { if (activeType.value === 'ip')          syncIpForm() },          { deep: true })
watch(routeForm,       () => { if (activeType.value === 'routes')      syncRouteForm() },       { deep: true })
watch(dhcpForm,        () => { if (activeType.value === 'dhcp')        syncDhcpForm() },        { deep: true })
watch(dnsForm,         () => { if (activeType.value === 'dns')         syncDnsForm() },         { deep: true })
watch(natForm,         () => { if (activeType.value === 'nat')         syncNatForm() },         { deep: true })
watch(vlanRouterForm,  () => { if (activeType.value === 'vlan-router') syncVlanRouterForm() },  { deep: true })
watch(vlanSwitchForm,  () => { if (activeType.value === 'vlan-switch') syncVlanSwitchForm() },  { deep: true })
watch(wireguardForm,   () => { if (activeType.value === 'wireguard')   syncWireguardForm() },   { deep: true })
watch(forwardingForm,  () => { if (activeType.value === 'forwarding')  syncForwardingForm() },  { deep: true })
watch(serviceForm,     () => { if (activeType.value === 'service')     syncServiceForm() },     { deep: true })
watch(packageForm,     () => { if (activeType.value === 'package')     syncPackageForm() },     { deep: true })
watch(userForm,        () => { if (activeType.value === 'user')        syncUserForm() },        { deep: true })
watch(hostnameForm,    () => { if (activeType.value === 'hostname')    syncHostnameForm() },    { deep: true })
watch(sysctlForm,      () => { if (activeType.value === 'sysctl')      syncSysctlForm() },      { deep: true })
watch(fileWriteForm,   () => { if (activeType.value === 'file-write')  syncFileWriteForm() },   { deep: true })

watch(() => props.nodeId, () => {
  activeType.value = null
  previewCommands.value = []
  results.value = []
})
</script>

<style scoped>
.config-panel { display: flex; height: 100%; overflow: hidden; }
.config-sidebar {
  width: 180px; min-width: 180px; overflow-y: auto;
  border-right: 1px solid #30363d; padding: 8px 0;
}
.cat-group { margin-bottom: 8px; }
.cat-label {
  padding: 4px 12px; font-size: 11px; font-weight: 600;
  color: #6e7681; text-transform: uppercase;
}
.type-btn {
  display: block; width: 100%; padding: 5px 14px; text-align: left;
  background: none; border: none; color: #8b949e;
  font-size: 12px; cursor: pointer;
}
.type-btn:hover { background: #161b22; color: #c9d1d9; }
.type-btn.active { background: #1c2128; color: #58a6ff; }

.config-main { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.placeholder { color: #6e7681; font-size: 13px; padding: 24px; }
.config-editor { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.editor-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; border-bottom: 1px solid #30363d;
}
.type-name { font-size: 14px; font-weight: 600; color: #e6edf3; }
.header-actions { display: flex; gap: 8px; }
.btn-preview, .btn-apply {
  padding: 4px 10px; font-size: 12px; border-radius: 4px;
  cursor: pointer; border: 1px solid #30363d;
}
.btn-preview { background: #21262d; color: #c9d1d9; }
.btn-apply { background: #238636; color: #fff; border-color: #2ea043; }
.btn-apply:disabled { opacity: 0.5; cursor: not-allowed; }

.specialized-form {
  background: #1c2128; padding: 12px; border-radius: 6px;
  border: 1px solid #30363d; margin-bottom: 8px;
}
.form-row { display: flex; gap: 12px; margin-bottom: 10px; }
.form-row label { flex: 1; display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: #8b949e; }
.form-row input, .form-row select {
  background: #0d1117; border: 1px solid #30363d; border-radius: 4px;
  color: #e6edf3; padding: 5px 8px; font-size: 12px;
}
.btn-sync {
  width: 100%; padding: 4px; font-size: 11px; background: #21262d;
  border: 1px solid #30363d; border-radius: 4px; color: #8b949e; cursor: pointer;
}
.btn-sync:hover { background: #30363d; color: #c9d1d9; }

.section-label-sub {
  font-size: 10px; font-weight: 600; color: #484f58;
  text-transform: uppercase; margin: 12px 0 6px;
  border-bottom: 1px solid #21262d; padding-bottom: 2px;
}
.warning-box {
  background: #331c00; border: 1px solid #d29922; border-radius: 6px;
  padding: 10px; color: #d29922; font-size: 12px; margin-bottom: 10px;
}

.multi-row { align-items: flex-end; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
.btn-remove {
  background: none; border: none; color: #f85149; cursor: pointer;
  padding: 5px; font-size: 14px; margin-bottom: 3px;
}
.btn-remove:hover { color: #ff7b72; }
.form-actions { display: flex; align-items: center; gap: 16px; margin-top: 10px; }
.btn-add-sub {
  background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
  padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;
}
.btn-add-sub:hover { background: #30363d; }
.check-label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #8b949e; cursor: pointer; flex: 1; }

.editor-body { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 16px; }
.section-label { font-size: 11px; font-weight: 600; color: #6e7681; text-transform: uppercase; margin-bottom: 6px; }
.auto-label { font-weight: 400; text-transform: none; color: #484f58; }
.json-textarea {
  width: 100%; height: 120px; background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #c9d1d9; font-family: monospace; font-size: 12px;
  padding: 8px; resize: vertical;
}
.preview-pre {
  background: #161b22; padding: 10px; border-radius: 6px;
  font-family: monospace; font-size: 12px; color: #d29922;
  white-space: pre-wrap; margin: 0;
}
.preview-error { color: #f85149; font-size: 12px; margin-bottom: 8px; }

.result-block { margin-bottom: 8px; }
.result-cmd { font-family: monospace; font-size: 11px; color: #58a6ff; margin-bottom: 2px; }
.result-out, .result-err {
  padding: 6px 8px; font-family: monospace; font-size: 11px;
  border-radius: 4px; white-space: pre-wrap;
}
.result-out { background: #0d1117; color: #c9d1d9; }
.result-err { background: #1a0a0a; color: #f85149; }
</style>
