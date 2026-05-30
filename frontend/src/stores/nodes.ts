import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import type { NrNode, NrLink } from '@/types'

export const useNodesStore = defineStore('nodes', () => {
  const nodes = ref<Record<string, NrNode>>({})
  const links = ref<NrLink[]>([])
  const connections = ref<Record<string, { connected: boolean }>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)
  const SELECTED_KEY = 'netrunner_selected_node'
  const selectedId = ref<string | null>(localStorage.getItem(SELECTED_KEY))
  const manuallyDisconnected = ref<Set<string>>(new Set())

  const nodeList = computed(() => Object.values(nodes.value).sort((a, b) => a.name.localeCompare(b.name)))
  const selected = computed(() => selectedId.value ? nodes.value[selectedId.value] : null)
  const connectedCount = computed(() => Object.values(connections.value).filter(c => c.connected).length)
  function isConnected(id: string): boolean {
    return !!connections.value[id]?.connected
  }

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      const [n, l] = await Promise.all([
        api.listNodes(),
        api.listLinks()
      ])
      nodes.value = n
      links.value = l
      // Drop a stale persisted selection if that node no longer exists
      if (selectedId.value && !nodes.value[selectedId.value]) {
        select(null)
      }
      await refreshConnections()
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  async function refreshConnections() {
    try {
      connections.value = await api.listConnections()
    } catch {
      // non-fatal: keep stale data, don't crash UI
    }
  }

  async function create(data: Partial<NrNode> & { password?: string }) {
    const node = await api.createNode(data)
    nodes.value[node.id] = node
    return node
  }

  async function update(id: string, data: Partial<NrNode> & { password?: string }) {
    const node = await api.updateNode(id, data)
    nodes.value[id] = node
    return node
  }

  async function remove(id: string) {
    await api.deleteNode(id)
    delete nodes.value[id]
    // Clean up links associated with this node
    links.value = links.value.filter(l => l.source !== id && l.target !== id)
    if (selectedId.value === id) select(null)
  }

  async function createLink(source: string, target: string) {
    const link = await api.createLink(source, target)
    links.value.push(link)
    return link
  }

  async function removeLink(id: string) {
    await api.deleteLink(id)
    links.value = links.value.filter(l => l.id !== id)
  }

  async function discover() {
    const res = await api.discoverLinks()
    await refresh()
    return res
  }

  function select(id: string | null) {
    selectedId.value = id
    if (id) localStorage.setItem(SELECTED_KEY, id)
    else localStorage.removeItem(SELECTED_KEY)
  }

  async function detectType(id: string) {
    const result = await api.detectDevice(id)
    if (nodes.value[id]) {
      nodes.value[id].device_type = result.device_type as NrNode['device_type']
    }
    return result.device_type
  }

  return {
    nodes, nodeList, links, connections, connectedCount, isConnected,
    loading, error, selectedId, selected, manuallyDisconnected,
    refresh, refreshConnections, create, update, remove, select, detectType,
    createLink, removeLink, discover
  }
})
