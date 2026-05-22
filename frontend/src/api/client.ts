import type { NrNode, NrLink, CommandResult, SavedConfig, CaptureMeta } from '@/types'

const BASE = '/api'

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
  if (!res.ok) throw new Error(data.detail || data.error || `HTTP ${res.status}`)
  return data as T
}

export const api = {
  // Auth
  login: (creds: any) => req<any>('POST', '/auth/login', creds),

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

  // Links
  listLinks: () => req<NrLink[]>('GET', '/links'),
  createLink: (source: string, target: string) => req<NrLink>('POST', '/links', { source, target }),
  deleteLink: (id: string) => req<{ status: string }>('DELETE', `/links/${id}`),
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
    openai_api_key_set: boolean; 
    masked_key: string; 
    alienvault_api_key_set: boolean;
    masked_alienvault_key: string;
    gns3_server_url: string;
    database_url: string;
  }>('GET', '/settings'),
  updateSettings: (body: { 
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

  readNode: (id: string, type: string) => req<{ results: CommandResult[] }>('GET', `/nodes/${id}/read/${type}`),
  executeNode: (id: string, commands: string[]) => req<{ results: CommandResult[] }>('POST', `/nodes/${id}/execute`, { commands }),
  installTool: (id: string, tool: string) => req<{ status: string; results: CommandResult[] }>('POST', `/nodes/${id}/install`, { tool }),

  // Backup
  backupNode: (id: string) => req<{ ok: boolean }>('POST', `/nodes/${id}/backup`),
  rollbackNode: (id: string) => req<{ ok: boolean; results: CommandResult[] }>('POST', `/nodes/${id}/rollback`),

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

  // System
  systemState: () => req<{ autopilot: boolean, chaos: boolean }>('GET', '/system/state'),
  updateSystemState: (body: { autopilot?: boolean, chaos?: boolean }) => req<{ autopilot: boolean, chaos: boolean }>('POST', '/system/state', body),
  systemLogs: () => req<{ logs: any[] }>('GET', '/system/logs'),
  triggerAttack: (body: {
    node_id: string
    attack_type: string
    attacker_ip: string
    username?: string
    port?: number
    path_query?: string
  }) => req<{ status: string; message: string; real_file_write: boolean }>('POST', '/chaos/attack', body),

  // Preview
  preview: (type: string, data: unknown) => req<{ commands: string[] }>('POST', '/preview', { type, data }),
  generateWireguardKeys: () => req<{ private_key: string; public_key: string }>('GET', '/wireguard/generate-keys'),

  // Configs
  listConfigs: () => req<SavedConfig[]>('GET', '/configs'),
  getConfig: (name: string) => req<{ name: string; content: string }>('GET', `/configs/${name}`),
  saveConfig: (name: string, content: string, type = 'misc') => req<{ name: string }>('POST', '/configs', { name, content, type }),
  deleteConfig: (name: string) => req<{ ok: boolean }>('DELETE', `/configs/${name}`),
}

export function wsTerminalUrl(nodeId: string): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws/terminal/${nodeId}`
}
