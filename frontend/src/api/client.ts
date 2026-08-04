import type { NrNode, NrLink, CommandResult, SavedConfig, CaptureMeta } from '@/types'

const BASE = '/api'

export function isUiContextEnabled() {
  return localStorage.getItem('ai_context_enabled') === 'true'
}

export function setUiContextEnabled(val: boolean) {
  localStorage.setItem('ai_context_enabled', val ? 'true' : 'false')
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('nr_token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  })
  if (res.status === 401 || res.status === 403) {
    localStorage.removeItem('nr_token')
    localStorage.removeItem('nr_role')
    window.dispatchEvent(new Event('auth-expired'))
    throw new Error('Unauthorized')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = data.detail || data.error
    const msg = typeof detail === 'string' ? detail : typeof detail === 'object' ? JSON.stringify(detail) : `HTTP ${res.status}`
    throw new Error(msg)
  }
  return data as T
}

export const api = {
  get: async <T = any>(path: string, config?: { params?: Record<string, any> }) => {
    let url = path
    if (config?.params) {
      const qs = new URLSearchParams()
      for (const [k, v] of Object.entries(config.params)) {
        if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
      }
      const s = qs.toString()
      if (s) url += '?' + s
    }
    return { data: await req<T>('GET', url) }
  },
  post: async <T = any>(path: string, body?: unknown) => ({ data: await req<T>('POST', path, body) }),
  delete: async <T = any>(path: string) => ({ data: await req<T>('DELETE', path) }),

  // Auth
  login: (creds: any) => req<any>('POST', '/auth/login', creds),

  // User management (admin only)
  listUsers: () => req<{ users: { username: string, role: string, created?: string }[] }>('GET', '/auth/users'),
  createUser: (u: { username: string, password: string, role: string }) => req<any>('POST', '/auth/users', u),
  deleteUser: (username: string) => req<{ status: string }>('DELETE', `/auth/users/${encodeURIComponent(username)}`),

  // Nodes
  listNodes: () => req<Record<string, NrNode>>('GET', '/nodes'),
  createNode: (n: Partial<NrNode> & { password?: string }) => req<NrNode>('POST', '/nodes', n),
  updateNode: (id: string, n: Partial<NrNode> & { password?: string }) => req<NrNode>('PUT', `/nodes/${id}`, n),
  deleteNode: (id: string) => req<{ ok: boolean }>('DELETE', `/nodes/${id}`),
  connectNode: (id: string) => req<{ status: string }>('POST', `/nodes/${id}/connect`),
  disconnectNode: (id: string) => req<{ ok: boolean }>('POST', `/nodes/${id}/disconnect`),
  rebootNode: (id: string, method?: 'command' | 'gns3') => 
    req<{ status: string, message: string, api_call?: string, details?: any }>('POST', `/nodes/${id}/reboot`, { method }),
  gns3ApiCall: (id: string, method: string, path: string, body?: any) => 
    req<{ status: string; url: string; response: any }>('POST', `/nodes/${id}/gns3-api`, { method, path, body }),
  listConnections: () => req<Record<string, { connected: boolean }>>('GET', '/nodes/connections'),
  nodeReachability: () => req<Record<string, { reachable: boolean, latency_ms: number | null, ts: number }>>('GET', '/nodes/reachability'),
  nodeVitals: () => req<Record<string, { cpu: number | null, ram: number | null, net_tx: number, net_rx: number, timestamp: number }>>('GET', '/nodes/vitals'),
  events: () => req<{ events: { id: number, ts: number, severity: string, node_id: string, node_name: string, kind: string, message: string }[] }>('GET', '/events'),
  demoStorm: () => req<{ status: string }>('POST', '/demo/storm'),
  clearEvents: () => req<{ status: string, removed: number }>('DELETE', '/events'),
  detectDevice: (id: string) => req<{ device_type: string }>('POST', `/nodes/${id}/detect`),
  defenseScan: (id: string) => req<{ output: string }>('POST', `/nodes/${id}/defense/scan`),
  isolateNode: (id: string, action: 'isolate' | 'restore') => 
    req<{ status: string }>('POST', `/nodes/${id}/defense/isolate`, { action }),
  enforceZeroTrust: (id: string) => 
    req<{ status: string, message: string }>('POST', `/nodes/${id}/defense/zero-trust`),
  installMonitoring: (id: string) =>
    req<{ status: string, message: string }>('POST', `/nodes/${id}/monitoring/install`),
  removeMonitoring: (id: string) =>
    req<{ status: string, message: string }>('POST', `/nodes/${id}/monitoring/remove`),

  generateReconReport: (nid: string, modules: string[]) => req<{ status: string; report: string }>('POST', `/recon/${nid}/report`, { modules }),

  // Links
  listLinks: () => req<NrLink[]>('GET', '/links'),
  createLink: (source: string, target: string) => req<NrLink>('POST', '/links', { source, target }),
  deleteLink: (id: string) => req<{ status: string }>('DELETE', `/links/${id}`),
  autoDiscoverLinks: () => req<{ status: string; new_links: number }>('GET', '/links/auto-discover'),
  discoverLinks: () => req<{ 
    status: string; 
    discovered: number; 
    message?: string;
    unknown_neighbors: { name?: string; ip?: string; source_node: string; method: string }[] 
  }>('POST', '/links/discover'),

  // AI
  aiChat: (messages: { role: string; content: string }[]) => 
    req<{ role: string; content: string }>('POST', '/ai/chat', { messages }),

  // Settings
  getSettings: () => req<{ 
    ai_execution_mode: string,
    ai_cli_type: string,
    ai_cli_path: string,
    ai_provider: string,
    ai_model: string,
    ai_base_url: string,
    ai_api_key_set: boolean,
    ai_masked_key: string,
    openai_api_key_set: boolean,
    masked_key: string,
    alienvault_api_key_set: boolean,
    masked_alienvault_key: string,
    gns3_server_url: string,
    database_url: string
  }>('GET', '/settings'),
  getNetworkInterfaces: () => req<any[]>('GET', '/network/interfaces'),
  getNetworkRoutes: () => req<any[]>('GET', '/network/routes'),
  addNetworkRoute: (body: any) => req<any>('POST', '/network/routes', body),
  deleteNetworkRoute: (body: any) => req<any>('DELETE', '/network/routes', body),
  addVlan: (body: any) => req<any>('POST', '/network/vlans', body),
  deleteVlan: (ifaceName: string) => req<any>('DELETE', `/network/vlans/${ifaceName}`),
  updateSettings: (body: { 
    ai_provider?: string;
    ai_api_key?: string;
    ai_base_url?: string;
    ai_model?: string;
    openai_api_key?: string; 
    gns3_server_url?: string;
    database_url?: string;
  }) => req<{ status: string }>('POST', '/settings', body),
  testDbConnection: (url: string) => req<{ status: string; message?: string }>('POST', '/settings/test-db', { url }),
  initDb: (url: string) => req<{ status: string }>('POST', '/settings/init-db', { url }),
  restartServer: () => req<{ status: string }>('POST', '/settings/restart'),

  // GNS3
  listGns3Projects: () => req<{ name: string; project_id: string }[]>('GET', '/gns3/projects'),
  syncGns3Project: (projectId: string) => req<{ status: string; nodes: number; links: number }>('POST', `/gns3/sync/${projectId}`),
  listLocalGns3Projects: () => req<{ name: string; path: string; id: string }[]>('GET', '/gns3/local-projects'),
  syncLocalGns3Project: (path: string) => req<{ status: string; nodes: number; links: number }>('POST', '/gns3/local-sync', { path }),

  getPhysicalInterfaces: (nid: string) => req<{ interfaces: any[] }>('GET', `/nodes/${nid}/interfaces/physical`),

  readNode: (id: string, type: string) => req<{ results: CommandResult[] }>('GET', `/nodes/${id}/read/${type}`),
  executeNode: (id: string, commands: string[]) => req<{ results: CommandResult[] }>('POST', `/nodes/${id}/execute`, { commands }),
  installTool: (id: string, tool: string, sudo_pass?: string) => req<{ status: string; results: CommandResult[] }>('POST', `/nodes/${id}/install`, { tool, sudo_pass }),

  // Backup
  backupNode: (id: string) => req<{ ok: boolean }>('POST', `/nodes/${id}/backup`),
  rollbackNode: (id: string) => req<{ ok: boolean; results: CommandResult[] }>('POST', `/nodes/${id}/rollback`),

  // Persistent Configs
  persistList: (id: string) => req<{ persists: { name: string; path: string }[] }>('GET', `/nodes/${id}/persist`),
  persistDelete: (id: string, name: string) => req<{ ok: boolean }>('DELETE', `/nodes/${id}/persist/${name}`),

  // Recon
  runRecon: (id: string, target: string, profile: string, sudo_pass?: string) => req<any>('POST', `/recon/${id}/scan`, { target, profile, sudo_pass }),
  importRecon: (id: string, hosts: any[]) => req<{ status: string; imported: number }>('POST', `/recon/${id}/import`, { hosts }),

  // Export
  exportNode: (id: string, body: { live_diagnostics?: string[]; include_captures?: boolean } = {}) =>
    req<{ name: string; diagnostic_types: string[]; diagnostic_errors: Record<string, string> }>('POST', `/nodes/${id}/export`, body),
  exportDownloadUrl: (name: string) => `${BASE}/exports/${encodeURIComponent(name)}`,

  // Captures
  captureList: (id: string) =>
    req<{ captures: CaptureMeta[] }>('GET', `/nodes/${id}/capture`),
  captureStart: (id: string, body: { id?: string; interface: string; filter?: string; packet_limit?: number }) =>
    req<{ ok: boolean; capture: CaptureMeta }>('POST', `/nodes/${id}/capture/start`, body),
  captureStatus: (id: string, capId: string) =>
    req<{ capture: CaptureMeta & { state: 'running' | 'stopped'; size: number } }>('GET', `/nodes/${id}/capture/${capId}/status`),
  captureStop: (id: string, capId: string) =>
    req<{ ok: boolean; size: number }>('POST', `/nodes/${id}/capture/${capId}/stop`),
  captureDelete: (id: string, capId: string) =>
    req<{ ok: boolean }>('DELETE', `/nodes/${id}/capture/${capId}`),
  captureDownloadUrl: (id: string, capId: string) =>
    `${BASE}/nodes/${id}/capture/${capId}/download`,
  captureAnalyze: async (id: string, capId: string) => {
    const r = await fetch(`${BASE}/nodes/${id}/capture/${capId}/analyze`)
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err.detail || 'Analyze failed')
    }
    return r.json()
  },
  captureInject: (id: string, body: { target_ip: string; port: number; protocol: string; payload: string; count?: number }) =>
    req<{ status: string; output: string }>('POST', `/nodes/${id}/capture/inject`, body),
  captureReplay: (id: string, capId: string, body: { interface: string }) =>
    req<{ ok: boolean; output: string }>('POST', `/nodes/${id}/capture/${capId}/replay`, body),

  // System
  systemState: () => req<{ autopilot: boolean, chaos: boolean }>('GET', '/system/state'),
  updateSystemState: (body: { autopilot?: boolean, chaos?: boolean }) => req<{ autopilot: boolean, chaos: boolean }>('POST', '/system/state', body),
  systemLogs: () => req<{ logs: any[] }>('GET', '/system/logs'),
  nukeTestDockers: () => req<{ ok: boolean, error?: string }>('POST', '/nodes/nuke-all'),
  triggerAttack: (body: {
    node_id: string
    attack_type: string
    attacker_ip: string
    username?: string
    port?: number
    path_query?: string
  }) => req<{ status: string; message: string; real_file_write: boolean }>('POST', '/chaos/attack', body),
  deployRedTeamPayload: (body: {
    node_id: string
    tool_name: string
    target_ip?: string
    target_path?: string
    port?: number
  }) => req<{ status: string; message: string; real_file_write: boolean }>('POST', '/redteam/deploy', body),

  // Deception
  deployMirageHoneypot: (nid: string, body: { persona: string; port: number; aggressiveness: string }) => 
    req<{ status: string; message: string }>('POST', `/nodes/${nid}/deception/deploy`, body),

  // Files
  listFiles: (nid: string, path: string) => req<{ path: string, entries: { name: string, is_dir: boolean, size: number, permissions: string, mtime: number }[] }>('GET', `/nodes/${nid}/fs/list?path=${encodeURIComponent(path)}`),
  readFile: (nid: string, path: string) => req<{ path: string, content: string }>('GET', `/nodes/${nid}/fs/read?path=${encodeURIComponent(path)}`),

  // Metrics
  nodeMetricsHistory: (nid: string) => req<{ status: string; history: { time: number; cpu: number; ram: number; net_tx: number; net_rx: number }[] }>('GET', `/nodes/${nid}/metrics/history`),
  nodeSystemSnapshot: (nid: string) => req<any>('GET', `/nodes/${nid}/system/snapshot`),
  nodeKill: (nid: string, pid: number, signal = 'TERM') => req<any>('POST', `/nodes/${nid}/system/kill`, { pid, signal }),
  nodeLogs: (nid: string, lines = 120) => req<{ lines: string[], error: string | null }>('GET', `/nodes/${nid}/system/logs?lines=${lines}`),
  nodeServices: (nid: string) => req<{ services: any[], error: string | null }>('GET', `/nodes/${nid}/system/services`),
  nodeServiceAction: (nid: string, name: string, action: string) => req<any>('POST', `/nodes/${nid}/system/service`, { name, action }),


  // Preview
  preview: (type: string, data: unknown) => req<{ commands: string[] }>('POST', '/preview', { type, data }),
  generateWireguardKeys: () => req<{ private_key: string; public_key: string }>('GET', `/wireguard/generate-keys?_=${Date.now()}`),

  // Configs
  listConfigs: () => req<SavedConfig[]>('GET', '/configs'),
  getConfig: (name: string) => req<{ name: string; content: string }>('GET', `/configs/${name}`),
  saveConfig: (name: string, content: string, type = 'misc') => req<{ name: string }>('POST', '/configs', { name, content, type }),
  deleteConfig: (name: string) => req<{ ok: boolean }>('DELETE', `/configs/${name}`),

  // Bruteforce
  uploadWordlist: async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    const headers: Record<string, string> = {}
    const token = localStorage.getItem('nr_token')
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${BASE}/bruteforce/wordlists`, { method: 'POST', headers, body: fd })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },
  listWordlists: () => req<string[]>('GET', '/bruteforce/wordlists'),
  launchAttack: (payload: any) => req<{ status: string; message: string }>('POST', '/bruteforce/attack', payload),
  getAttackStatus: () => req<Record<string, any>>('GET', '/bruteforce/status'),
  stopAttack: (nid: string) => req<{ status: string }>('POST', '/bruteforce/stop', { node_id: nid }),
  pauseAttack: (nid: string) => req<{ status: string }>('POST', '/bruteforce/pause', { node_id: nid }),
  resumeAttack: (nid: string) => req<{ status: string }>('POST', '/bruteforce/resume', { node_id: nid }),

  // Intelligence
  getIntelligenceGraph: () => req<any>('GET', '/intelligence/graph'),
  queryIntelligence: (query: string) => req<any>('POST', '/intelligence/query', { query }),

  // Kismet (Wireless IDS)
  kismetStatus: () => req<{ running: boolean; api_reachable: boolean; pid: number | null; interface: string; host: string; port: number }>('GET', '/kismet/status'),
  kismetStart: (body: { interface?: string; http_port?: number; log_dir?: string }) => req<{ status: string; pid?: number; interface?: string }>('POST', '/kismet/start', body),
  kismetStop: () => req<{ status: string }>('POST', '/kismet/stop'),
  kismetNetworks: () => req<{ networks: any[] }>('GET', '/kismet/networks'),
  kismetClients: () => req<{ clients: any[] }>('GET', '/kismet/clients'),
  kismetAlerts: (since = 0) => req<{ alerts: any[] }>('GET', `/kismet/alerts?since=${since}`),
  kismetChannels: () => req<{ channels: Record<string, any> }>('GET', '/kismet/channels'),
  kismetDatasources: () => req<{ datasources: any[] }>('GET', '/kismet/datasources'),
  kismetInterfaces: () => req<{ interfaces: { name: string; driver: string; monitor_mode: boolean }[] }>('GET', '/kismet/interfaces'),
  kismetSetChannel: (source_uuid: string, channel?: number) => req<{ status: string }>('POST', '/kismet/channel', { source_uuid, channel }),

  // AI Storylines & Log Parsing
  getStorylines: () => req<any[]>('GET', '/ai/storylines'),
  parseLog: (log_entry: string, selection: string) => req<{ pattern: string; extracted_fields: any; explanation: string }>('POST', '/ai/parse-log', { log_entry, selection }),
}

/** Query-param suffix carrying the JWT for WebSocket handshakes (browsers
 *  can't set Authorization headers on WS). Returns e.g. "?token=..." or "". */
export function wsTokenParam(): string {
  const t = localStorage.getItem('nr_token')
  return t ? `?token=${encodeURIComponent(t)}` : ''
}

/** Same-origin WebSocket base (e.g. "ws://host:port" / "wss://host").
 *  In dev the Vite proxy forwards /ws → backend; in prod FastAPI serves it.
 *  Use relative paths everywhere so the app works on any host, not just localhost. */
export function wsBase(): string {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}`
}

export function wsTerminalUrl(nodeId: string): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const hostname = location.hostname
  const token = localStorage.getItem('nr_token') || ''
  return `${proto}://${hostname}:8081/ws/terminal?nodeId=${encodeURIComponent(nodeId)}&token=${encodeURIComponent(token)}`
}

export async function sendUiEvent(type: string, path: string, element?: string, data?: any) {
  if (!isUiContextEnabled()) return
  const token = localStorage.getItem('nr_token') || ''
  try {
    await fetch('/api/telemetry/ui', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        type,
        timestamp: new Date().toISOString(),
        path,
        element,
        data
      })
    })
  } catch (e) {
    console.error('Failed to send UI telemetry', e)
  }
}
