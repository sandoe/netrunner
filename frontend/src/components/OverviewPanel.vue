<template>
  <div class="overview-panel">
    <div class="ov-toolbar">
      <button class="btn-secondary" @click="refreshAll" :disabled="anyLoading || !connected">RE-SCAN</button>
      <button class="btn-secondary btn-clear" @click="clearAll" :disabled="anyLoading">CLEAR ALL</button>
      <label class="auto-toggle">
        <input type="checkbox" v-model="autoRefresh" :disabled="!connected" />
        <span>AUTO-UPDATE</span>
      </label>
      <span class="last-update" v-if="lastUpdate">LAST SYNC: {{ lastUpdate }}</span>
    </div>

    <div v-if="!connected" class="ov-disconnected">
      <div class="dc-card">
        <div class="dc-icon">⚡</div>
        <div class="dc-title">LINK DISRUPTED</div>
        <div class="dc-msg">NEURAL CONNECTION REQUIRED FOR LIVE TELEMETRY.</div>
        <button class="btn-primary" @click="connectNow" :disabled="connecting">
          {{ connecting ? 'ESTABLISHING...' : 'ESTABLISH LINK' }}
        </button>
        <div v-if="connectError" class="dc-error">{{ connectError }}</div>
      </div>
    </div>

    <div v-else class="ov-content">
      <div v-for="(group, catId) in groupedTiles" :key="catId" class="ov-section">
        <div class="ov-section-head" @click="toggleCat(catId as string)">
          <span class="ov-section-title">{{ getCatLabel(catId as string) }}</span>
          <span class="ov-section-chevron" :class="{ collapsed: collapsedCats.has(catId as string) }">⌃</span>
        </div>
        
        <div v-if="!collapsedCats.has(catId as string)" class="tile-grid">
          <div
            v-for="tile in group"
            :key="tile.key"
            class="tile"
            :class="{ loading: tile.loading, expanded: tile.expanded }"
            @click="toggleExpand(tile, $event)"
          >
            <div class="tile-head">
              <span class="tile-icon">{{ tile.icon }}</span>
              <span class="tile-title">{{ tile.title }}</span>
              <span v-if="tile.loading" class="pulse-dot"></span>
              <span class="tile-chevron" :class="{ open: tile.expanded }">⌃</span>
              <button class="tile-refresh" @click.stop="loadTile(tile)" :disabled="tile.loading" title="Refresh">↻</button>
            </div>

            <div v-if="tile.error" class="tile-error">
              {{ tile.error }}
              <div v-if="tile.error.toLowerCase().includes('not installed') || tile.error.toLowerCase().includes('not found')" class="tile-fix">
                <button class="btn-fix" @click.stop="installTool(tile)" :disabled="tile.loading">
                  {{ tile.loading ? 'INSTALLING...' : 'INSTALL ' + tile.type.toUpperCase() }}
                </button>
              </div>
            </div>
            <div v-else class="tile-body">
              <div v-if="tile.summary" class="tile-summary">
                <div v-for="(v, k) in tile.summary" :key="k" class="kv">
                  <span class="k">{{ k }}</span>
                  <span class="v">{{ v }}</span>
                </div>
              </div>
              <pre v-if="tile.expanded && tile.raw" class="tile-pre full">{{ tile.raw }}</pre>
              <pre v-else-if="tile.preview" class="tile-pre">{{ tile.preview }}</pre>
              <div v-if="!tile.summary && !tile.preview && !tile.loading && !tile.raw" class="tile-empty">— NO DATA DETECTED —</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { api } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'
import type { ReadType } from '@/types'

interface Tile {
  key: string
  title: string
  icon: string
  category: 'network' | 'linux' | 'rpi' | 'firewall'
  type: ReadType
  parse: (raw: string) => { summary?: Record<string, string>; preview?: string }
  loading: boolean
  error: string
  summary: Record<string, string> | null
  preview: string
  raw: string
  expanded: boolean
}

const props = defineProps<{ nodeId: string }>()
const store = useNodesStore()

const connected = computed(() => store.isConnected(props.nodeId))
const connecting = ref(false)
const connectError = ref('')
const collapsedCats = ref<Set<string>>(new Set())

const groupedTiles = computed(() => {
  const groups: Record<string, Tile[]> = {}
  for (const t of tiles.value) {
    if (!groups[t.category]) groups[t.category] = []
    groups[t.category].push(t)
  }
  return groups
})

function getCatLabel(id: string) {
  const labels: Record<string, string> = {
    network: 'NETWORK LIVE TELEMETRY',
    linux: 'LINUX SYSTEM STATUS',
    rpi: 'RASPBERRY PI HARDWARE',
    firewall: 'FIREWALL & SECURITY'
  }
  return labels[id] || id.toUpperCase()
}

function toggleCat(id: string) {
  if (collapsedCats.value.has(id)) collapsedCats.value.delete(id)
  else collapsedCats.value.add(id)
}

async function connectNow() {
  connecting.value = true
  connectError.value = ''
  try {
    await api.connectNode(props.nodeId)
    await store.refreshConnections()
  } catch (e) {
    connectError.value = String(e)
  } finally {
    connecting.value = false
  }
}

function makeTiles(deviceType?: string): Tile[] {
  const all: Tile[] = [
    {
      key: 'ip', title: 'IP ADDRESSES', icon: '🌐', type: 'ip', category: 'network',
      parse: parseIp,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'routes', title: 'ROUTING TABLE', icon: '🛤️', type: 'routes', category: 'network',
      parse: parseRoutes,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'interfaces', title: 'INTERFACES', icon: '🔌', type: 'interfaces', category: 'network',
      parse: parseInterfaces,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'if-stats', title: 'INTERFACE METRICS', icon: '📊', type: 'if-stats', category: 'network',
      parse: parseIfStats,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'wifi-scan', title: 'WIFI SCANNER', icon: '📡', type: 'wifi-scan', category: 'network',
      parse: parseWifiScan,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'nmap-scan', title: 'SECURITY AUDIT', icon: '🕵️', type: 'nmap-scan', category: 'network',
      parse: parseNmap,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'forwarding', title: 'IP FORWARDING', icon: '↪️', type: 'forwarding', category: 'network',
      parse: parseForwarding,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'firewall-nft', title: 'NFTABLES', icon: '🛡️', type: 'nftables', category: 'firewall',
      parse: parseFirewall,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'firewall-ipt', title: 'IPTABLES', icon: '🛡️', type: 'iptables', category: 'firewall',
      parse: parseFirewall,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'wireguard', title: 'WIREGUARD', icon: '🔐', type: 'wireguard', category: 'network',
      parse: parseWireguard,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'dhcp-server', title: 'DHCP SERVER', icon: '📨', type: 'dhcp-server', category: 'network',
      parse: parseDhcp,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'rpi-spi', title: 'SPI STATUS', icon: '📟', type: 'rpi-spi', category: 'rpi',
      parse: parseSpi,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'sockets', title: 'LISTENING SOCKETS', icon: '📡', type: 'sockets', category: 'linux',
      parse: parseSockets,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
    {
      key: 'os-info', title: 'OS METRICS', icon: '💻', type: 'os-info', category: 'linux',
      parse: parseOs,
      loading: false, error: '', summary: null, preview: '', raw: '', expanded: false,
    },
  ]

  return all.filter(t => {
    if (t.key.startsWith('rpi-') && deviceType !== 'rpi') return false
    return true
  })
}

const tiles = ref<Tile[]>(makeTiles(store.selected?.device_type))
const lastUpdate  = ref('')
const autoRefresh = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const anyLoading = computed(() => tiles.value.some(t => t.loading))

// ── Parsers ───────────────────────────────────────────────────────

function parseIp(raw: string): ReturnType<Tile['parse']> {
  if (!raw) return { preview: '' }
  const ifaces  = (raw.match(/^\d+:\s+\S+/gm) || []).length
  const v4addrs = (raw.match(/inet\s+\d+\.\d+\.\d+\.\d+\/\d+/g) || [])
  const v6addrs = (raw.match(/inet6\s+[0-9a-f:]+/g) || [])
  return {
    summary: {
      'INTERFACES': String(ifaces),
      'IPV4 ADDRS': String(v4addrs.length),
      'IPV6 ADDRS': String(v6addrs.length),
    },
    preview: v4addrs.slice(0, 5).map(s => s.replace(/\s+/g, ' ')).join('\n'),
  }
}

function parseRoutes(raw: string): ReturnType<Tile['parse']> {
  if (!raw) return { preview: '' }
  const lines    = raw.split('\n').filter(l => l.trim())
  const def      = lines.find(l => l.startsWith('default '))
  const gw       = def?.match(/via\s+(\S+)/)?.[1] || '—'
  const dev      = def?.match(/dev\s+(\S+)/)?.[1] || '—'
  return {
    summary: {
      'ROUTES': String(lines.length),
      'GATEWAY': gw,
      'INTERFACE': dev,
    },
    preview: lines.slice(0, 4).join('\n'),
  }
}

function parseInterfaces(raw: string): ReturnType<Tile['parse']> {
  if (!raw) return { preview: '' }
  const lines = raw.split('\n').filter(l => /^\d+:/.test(l))
  const up    = lines.filter(l => /state UP/.test(l)).length
  const down  = lines.length - up
  return {
    summary: { 'TOTAL': String(lines.length), 'UP': String(up), 'DOWN': String(down) },
    preview: lines.slice(0, 5).map(l => l.replace(/^\s*/, '').replace(/<[^>]+>/, '').trim()).join('\n'),
  }
}

function parseIfStats(raw: string): ReturnType<Tile['parse']> {
  if (!raw) return {}
  const rxPkts = raw.match(/RX:\s+bytes\s+packets\s+errors\s+dropped\s+missed\s+mcast\s*\n\s*\d+\s+(\d+)\s+(\d+)\s+(\d+)/)
  const txPkts = raw.match(/TX:\s+bytes\s+packets\s+errors\s+dropped\s+carrier\s+collsns\s*\n\s*\d+\s+(\d+)\s+(\d+)\s+(\d+)/)
  
  // Alternative ip -s format parsing
  const rx_p = raw.match(/RX:\s+bytes\s+packets\s+errors\s+dropped\s+overrun\s+mcast\s*\n\s*\d+\s+(\d+)\s+(\d+)\s+(\d+)/)
  const tx_p = raw.match(/TX:\s+bytes\s+packets\s+errors\s+dropped\s+carrier\s+collsns\s*\n\s*\d+\s+(\d+)\s+(\d+)\s+(\d+)/)

  const rx = rxPkts || rx_p
  const tx = txPkts || tx_p

  return {
    summary: {
      'RX PKTS': rx ? rx[1] : '?',
      'RX DROP': rx ? rx[3] : '?',
      'TX PKTS': tx ? tx[1] : '?',
      'TX DROP': tx ? tx[3] : '?',
    },
    preview: raw.split('\n').slice(0, 10).join('\n')
  }
}

function parseWifiScan(raw: string): ReturnType<Tile['parse']> {
  if (!raw || /tools not available/.test(raw)) return { summary: { 'STATUS': 'UNAVAILABLE' } }
  const ssids = (raw.match(/ESSID:"([^"]+)"|SSID: ([^\n]+)/g) || []).length
  return {
    summary: { 'NETWORKS': String(ssids) },
    preview: raw.split('\n').slice(0, 8).join('\n')
  }
}

function parseNmap(raw: string): ReturnType<Tile['parse']> {
  if (!raw || /not installed/.test(raw)) return { summary: { 'STATUS': 'UNINSTALLED' } }
  const ports = (raw.match(/\d+\/tcp\s+open/g) || []).length
  const services = raw.split('\n')
    .filter(l => /open/i.test(l))
    .map(l => l.replace(/\s+/g, ' ').trim())
    .slice(0, 3)
    .join('\n')
    
  return {
    summary: { 'OPEN PORTS': String(ports) },
    preview: services || 'No open ports found'
  }
}

function parseSpi(raw: string): ReturnType<Tile['parse']> {
  if (!raw || /not enabled/.test(raw)) return { summary: { 'STATUS': 'DISABLED' } }
  const devices = (raw.match(/\/dev\/spidev\d+\.\d+/g) || []).length
  return {
    summary: { 'DEVICES': String(devices), 'MODULES': raw.includes('spi') ? 'LOADED' : 'NONE' },
    preview: raw
  }
}

function parseForwarding(raw: string): ReturnType<Tile['parse']> {
  const m4 = raw.match(/net\.ipv4\.ip_forward\s*=\s*(\d)/)
  const m6 = raw.match(/net\.ipv6\.conf\.all\.forwarding\s*=\s*(\d)/)
  return {
    summary: {
      'IPV4 FORWARD': m4 ? (m4[1] === '1' ? 'ACTIVE' : 'DISABLED') : '?',
      'IPV6 FORWARD': m6 ? (m6[1] === '1' ? 'ACTIVE' : 'DISABLED') : '?',
    },
  }
}

function parseFirewall(raw: string): ReturnType<Tile['parse']> {
  if (!raw || /not available|empty or not/.test(raw)) {
    return { summary: { 'STATUS': 'INACTIVE' } }
  }
  const lines = raw.split('\n').filter(l => l.trim())
  const ruleCount = lines.filter(l => /\b(accept|drop|reject|jump|return|dnat|snat|masquerade|-A)\b/i.test(l)).length
  return {
    summary: {
      'STATUS':     'ACTIVE',
      'RULES':     String(ruleCount),
      'LINES':     String(lines.length),
    },
    preview: lines.slice(0, 5).join('\n'),
  }
}

function parseWireguard(raw: string): ReturnType<Tile['parse']> {
  if (!raw || /not running/.test(raw)) {
    return { summary: { 'STATUS': 'INACTIVE' } }
  }
  const ifaces = (raw.match(/^interface:\s*(\S+)/gm) || []).map(l => l.split(/\s+/)[1])
  const peers  = (raw.match(/^peer:/gm) || []).length
  return {
    summary: {
      'INTERFACES': ifaces.join(', ') || '—',
      'PEERS':      String(peers),
    },
  }
}

function parseDhcp(raw: string): ReturnType<Tile['parse']> {
  if (!raw || /not found/.test(raw)) return { summary: { 'STATUS': 'UNCONFIGURED' } }
  const ranges = (raw.match(/dhcp-range=\S+/g) || [])
  const leases = raw.split('\n').filter(l => /^\d+\s+/.test(l)).length
  return {
    summary: {
      'RANGES': String(ranges.length),
      'LEASES': String(leases),
    },
    preview: ranges.slice(0, 3).join('\n'),
  }
}

function parseSockets(raw: string): ReturnType<Tile['parse']> {
  if (!raw) return {}
  const lines = raw.split('\n').filter(l => /LISTEN|UNCONN/.test(l))
  const tcp   = lines.filter(l => /^tcp/i.test(l) || /\btcp\b/i.test(l)).length
  const udp   = lines.filter(l => /^udp/i.test(l) || /\budp\b/i.test(l)).length
  return {
    summary: { 'TCP LISTEN': String(tcp), 'UDP LISTEN': String(udp) },
    preview: lines.slice(0, 5).join('\n'),
  }
}

function parseOs(raw: string): ReturnType<Tile['parse']> {
  if (!raw) return {}
  const pretty = raw.match(/PRETTY_NAME="?([^"\n]+)/)?.[1]
  const kernel = raw.match(/Linux\s+(\S+)\s+(\S+)/)?.slice(1, 3).join(' ')
  const host   = raw.match(/Linux\s+(\S+)/)?.[1]
  const summary: Record<string, string> = {}
  if (pretty) summary['OS'] = pretty
  if (kernel) summary['KERNEL'] = kernel
  if (host)   summary['HOST'] = host
  return { summary, preview: raw.split('\n').slice(0, 4).join('\n') }
}

// ── Loading ───────────────────────────────────────────────────────

async function loadTile(tile: Tile) {
  tile.loading = true
  tile.error   = ''
  try {
    const data = await api.readNode(props.nodeId, tile.type)
    
    // Check if there was any error in results
    const errResult = data.results?.find(r => r.error)
    if (errResult) {
      tile.error = errResult.error || 'Connection or command error.'
      tile.summary = null
      tile.preview = ''
      tile.raw = ''
      return
    }
    if (!data.results || data.results.length === 0) {
      tile.error = 'No telemetry data returned.'
      tile.summary = null
      tile.preview = ''
      tile.raw = ''
      return
    }

    const raw  = data.results.map(r => r.output || '').join('\n').trim()
    
    // Auto-detect "not installed" messages from shell or typical error messages
    const missingIndicators = ['not found', 'no such file', 'not installed', 'unable to locate', 'command not found']
    if (missingIndicators.some(ind => raw.toLowerCase().includes(ind))) {
        tile.error = `Tool '${tile.type}' not installed on node.`
        tile.summary = null
        tile.preview = ''
        tile.raw = raw // Keep raw for debugging in expanded mode
        return
    }

    const parsed = tile.parse(raw)
    tile.raw     = raw
    tile.summary = parsed.summary || null
    tile.preview = parsed.preview || ''
    store.refreshConnections()
  } catch (e) {
    tile.error   = String(e)
    tile.summary = null
    tile.preview = ''
    tile.raw     = ''
  } finally {
    tile.loading = false
  }
}

async function installTool(tile: Tile) {
    tile.loading = true
    try {
        await api.installTool(props.nodeId, tile.type)
        await loadTile(tile)
    } catch (e) {
        tile.error = `Installation failed: ${e}`
    } finally {
        tile.loading = false
    }
}

function toggleExpand(tile: Tile, ev: MouseEvent) {
  if ((ev.target as HTMLElement).closest('.tile-refresh')) return
  tile.expanded = !tile.expanded
}

async function refreshAll() {
  if (!connected.value) return
  for (const tile of tiles.value) {
    await loadTile(tile)
  }
  lastUpdate.value = new Date().toLocaleTimeString()
  store.refreshConnections()
}

function clearAll() {
  for (const tile of tiles.value) {
    tile.raw = ''
    tile.summary = null
    tile.preview = ''
    tile.error = ''
    tile.expanded = false
  }
  lastUpdate.value = ''
}

watch(autoRefresh, (on) => {
  if (timer) { clearInterval(timer); timer = null }
  if (on) timer = setInterval(refreshAll, 10000)
})

watch(() => props.nodeId, () => {
  tiles.value = makeTiles(store.selected?.device_type)
  lastUpdate.value = ''
  if (connected.value) refreshAll()
})

onMounted(() => {
  if (connected.value) refreshAll()
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.overview-panel { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: var(--bg); }

.ov-toolbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 16px; border-bottom: 1px solid var(--border);
  background: var(--bg2);
}
.btn-secondary {
  padding: 6px 14px; background: var(--bg3); border: 1px solid var(--border);
  border-radius: var(--r); color: var(--textwh); font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; cursor: pointer; transition: all .2s;
}
.btn-secondary:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); box-shadow: var(--shadow-c); }
.btn-secondary:disabled { opacity: .4; cursor: not-allowed; }
.btn-clear:hover:not(:disabled) { border-color: var(--pink); color: var(--pink); box-shadow: var(--shadow-p); }

.auto-toggle {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-hd); font-size: 8px; color: var(--text); letter-spacing: 1px; cursor: pointer;
}
.last-update { font-family: var(--font-co); font-size: 9px; color: var(--text); margin-left: auto; }

.ov-disconnected { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px; }

.ov-content { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 32px; }
.ov-section { display: flex; flex-direction: column; gap: 16px; }
.ov-section-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 4px 8px; border-bottom: 1px solid var(--border);
  cursor: pointer; user-select: none;
}
.ov-section-head:hover .ov-section-title { color: var(--cyan); }
.ov-section-title { font-family: var(--font-hd); font-size: 11px; font-weight: 800; color: var(--text); letter-spacing: 2px; transition: color .2s; }
.ov-section-chevron { font-size: 12px; color: var(--text); transition: transform .3s; }
.ov-section-chevron.collapsed { transform: rotate(180deg); }

.dc-card {
  max-width: 400px; width: 100%; text-align: center;
  background: var(--bg2); border: 1px solid var(--border); border-radius: var(--r2); padding: 32px;
  box-shadow: 0 0 40px rgba(0,0,0,.3);
}
.dc-icon { font-size: 40px; margin-bottom: 16px; color: var(--yellow); text-shadow: 0 0 15px var(--yellow); }
.dc-title { font-family: var(--font-hd); font-size: 18px; color: var(--textwh); letter-spacing: 2px; margin-bottom: 12px; }
.dc-msg { font-size: 12px; color: var(--text); margin-bottom: 24px; line-height: 1.6; }
.btn-primary {
  width: 100%; padding: 12px; background: var(--bg3); border: 1px solid var(--cyan); border-radius: var(--r);
  color: var(--cyan); font-family: var(--font-hd); font-size: 11px; letter-spacing: 2px; cursor: pointer; transition: all .3s;
}
.btn-primary:hover:not(:disabled) { background: var(--cyan); color: var(--bg); box-shadow: var(--shadow-c); }
.dc-error { margin-top: 16px; padding: 8px; background: rgba(255,45,110,.1); border: 1px solid var(--pink); border-radius: var(--r); color: var(--pink); font-size: 11px; font-family: var(--font-co); }

.tile-grid {
  flex: 1; overflow-y: auto; padding: 20px;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px; align-content: start;
}

.tile {
  background: var(--bg2); border: 1px solid var(--border); border-radius: var(--r);
  padding: 16px; transition: all .2s;
  cursor: pointer; user-select: none; position: relative;
  overflow: hidden;
}
.tile:hover { border-color: var(--cyan-d); background: var(--bg3); }
.tile.loading { border-color: var(--cyan); }
.tile.expanded {
  grid-column: 1 / -1;
  border-color: var(--cyan);
  background: var(--bg3);
  box-shadow: inset 0 0 20px rgba(0,229,255,.05);
}

.tile-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.tile-icon { font-size: 16px; }
.tile-title { font-family: var(--font-hd); font-size: 10px; font-weight: 700; color: var(--textwh); flex: 1; letter-spacing: 1.5px; }
.tile-refresh {
  background: none; border: none; color: var(--text);
  cursor: pointer; font-size: 14px; transition: color .2s;
}
.tile-refresh:hover:not(:disabled) { color: var(--cyan); }
.tile-chevron { font-size: 12px; color: var(--text); transform: rotate(180deg); transition: transform .3s; }
.tile-chevron.open { transform: rotate(0deg); color: var(--cyan); }

.pulse-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--cyan); box-shadow: 0 0 8px var(--cyan);
  animation: pulse 1s infinite;
}
@keyframes pulse { 0% { opacity: 1 } 50% { opacity: .3 } 100% { opacity: 1 } }

.tile-summary { display: flex; flex-direction: column; gap: 6px; }
.kv { display: flex; justify-content: space-between; font-size: 11px; }
.kv .k { font-family: var(--font-hd); color: var(--text); font-size: 8px; letter-spacing: 1px; }
.kv .v { font-family: var(--font-co); color: var(--green); text-shadow: 0 0 4px rgba(0,255,157,.2); }

.tile-pre {
  margin: 12px 0 0; padding: 10px;
  background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
  font-family: var(--font-co);
  font-size: 10px; line-height: 1.5; color: var(--textbr);
  white-space: pre-wrap; word-break: break-all;
  max-height: 120px; overflow-y: auto;
}
.tile-pre.full {
  max-height: 500px; font-size: 11px; color: var(--textwh);
  padding: 16px; border-color: var(--border2);
}
.tile-error {
  margin-top: 10px; padding: 8px; background: rgba(255,45,110,.1); border: 1px solid var(--pink); border-radius: var(--r);
  color: var(--pink); font-size: 10px; font-family: var(--font-co);
}
.tile-fix { margin-top: 8px; }
.btn-fix {
  width: 100%; padding: 6px; background: var(--bg3); border: 1px solid var(--green);
  border-radius: 4px; color: var(--green); font-family: var(--font-hd); font-size: 8px;
  letter-spacing: 1px; cursor: pointer; transition: all .2s;
}
.btn-fix:hover:not(:disabled) { background: var(--green); color: var(--bg); box-shadow: var(--shadow-g); }
.tile-empty { color: var(--text); font-family: var(--font-hd); font-size: 8px; letter-spacing: 1px; padding: 12px 0; text-align: center; }
</style>
