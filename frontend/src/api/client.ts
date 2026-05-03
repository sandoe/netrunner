import type { NrNode, CommandResult, SavedConfig } from '@/types'

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
  detectDevice: (id: string) => req<{ device_type: string }>('POST', `/nodes/${id}/detect`),

  readNode: (id: string, type: string) => req<{ results: CommandResult[] }>('GET', `/nodes/${id}/read/${type}`),
  executeNode: (id: string, commands: string[]) => req<{ results: CommandResult[] }>('POST', `/nodes/${id}/execute`, { commands }),

  // Backup
  backupNode: (id: string) => req<{ ok: boolean }>('POST', `/nodes/${id}/backup`),
  rollbackNode: (id: string) => req<{ ok: boolean; results: CommandResult[] }>('POST', `/nodes/${id}/rollback`),

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
