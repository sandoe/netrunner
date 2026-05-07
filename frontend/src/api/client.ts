import type { NrNode, NrLink, CommandResult, SavedConfig, CaptureMeta } from '@/types'

const BASE = '/api'

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = { method, headers: { 'Content-Type': 'application/json' } }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(BASE + path, opts)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || data.error || `HTTP ${res.status}`)
  return data as T
}

export const api = {
  // Nodes
  listNodes: () => req<Record<string, NrNode>>('GET', '/nodes'),
  createNode: (n: Partial<NrNode> & { password?: string }) => req<NrNode>('POST', '/nodes', n),
  updateNode: (id: string, n: Partial<NrNode> & { password?: string }) => req<NrNode>('PUT', `/nodes/${id}`, n),
  deleteNode: (id: string) => req<{ ok: boolean }>('DELETE', `/nodes/${id}`),
  connectNode: (id: string) => req<{ status: string }>('POST', `/nodes/${id}/connect`),
  disconnectNode: (id: string) => req<{ ok: boolean }>('POST', `/nodes/${id}/disconnect`),
  listConnections: () => req<Record<string, { connected: boolean }>>('GET', '/nodes/connections'),
  detectDevice: (id: string) => req<{ device_type: string }>('POST', `/nodes/${id}/detect`),

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
  getSettings: () => req<{ openai_api_key_set: boolean; masked_key: string; gns3_server_url: string }>('GET', '/settings'),
  updateSettings: (body: { openai_api_key?: string; gns3_server_url?: string }) => req<{ status: string }>('POST', '/settings', body),

  // GNS3
  listGns3Projects: () => req<{ name: string; project_id: string }[]>('GET', '/gns3/projects'),
  syncGns3Project: (projectId: string) => req<{ status: string; nodes: number; links: number }>('POST', `/gns3/sync/${projectId}`),
  listLocalGns3Projects: () => req<{ name: string; path: string; id: string }[]>('GET', '/gns3/local-projects'),
  syncLocalGns3Project: (path: string) => req<{ status: string; nodes: number; links: number }>('POST', '/gns3/local-sync', { path }),

  readNode: (id: string, type: string) => req<{ results: CommandResult[] }>('GET', `/nodes/${id}/read/${type}`),
  executeNode: (id: string, commands: string[]) => req<{ results: CommandResult[] }>('POST', `/nodes/${id}/execute`, { commands }),

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

  // Preview
  preview: (type: string, data: unknown) => req<{ commands: string[] }>('POST', '/preview', { type, data }),

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
