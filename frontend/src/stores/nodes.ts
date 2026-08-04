import { defineStore } from 'pinia'
import { ref, shallowRef, computed } from 'vue'
import { api } from '@/api/client'
import type { NrNode, NrLink } from '@/types'

export const useNodesStore = defineStore('nodes', () => {
  const nodes = shallowRef<Record<string, NrNode>>({})
  const links = shallowRef<NrLink[]>([])
  const connections = shallowRef<Record<string, { connected: boolean }>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)
  const SELECTED_KEY = 'netrunner_selected_node'
  const selectedId = ref<string | null>(localStorage.getItem(SELECTED_KEY))
  const manuallyDisconnected = ref<Set<string>>(new Set())
  const isolatedNodes = shallowRef<Set<string>>(new Set())
  const defconLevel = ref<number>(5)
  const simulationMode = ref<boolean>(localStorage.getItem('nr_simulation') === 'on')

  function setDefcon(level: number) {
    defconLevel.value = level
  }

  function toggleSimulationMode() {
    simulationMode.value = !simulationMode.value
    localStorage.setItem('nr_simulation', simulationMode.value ? 'on' : 'off')
  }

  function isolateNode(id: string) {
    const next = new Set(isolatedNodes.value)
    next.add(id)
    isolatedNodes.value = next
  }

  function unisolateNode(id: string) {
    const next = new Set(isolatedNodes.value)
    next.delete(id)
    isolatedNodes.value = next
  }

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

      // Inject mock layer 1 metadata for demo purposes if missing
      l.forEach((link: any, index: number) => {
        if (!link.metadata) link.metadata = {}
        if (!link.metadata.medium) {
          // Assign random medium: 70% wired, 20% wireless, 10% bluetooth
          const r = Math.random()
          if (r > 0.3) link.metadata.medium = 'wired'
          else if (r > 0.1) link.metadata.medium = 'wireless'
          else link.metadata.medium = 'bluetooth'
        }
        if (!link.metadata.speed) {
          // Assign random speed based on medium
          if (link.metadata.medium === 'wired') link.metadata.speed = Math.random() > 0.5 ? 1000 : 10000
          else if (link.metadata.medium === 'wireless') link.metadata.speed = Math.random() > 0.5 ? 300 : 866
          else link.metadata.speed = 2
        }
        if (!link.metadata.duplex) {
          if (link.metadata.medium === 'wireless' || link.metadata.medium === 'bluetooth') {
            link.metadata.duplex = 'half'
          } else {
            link.metadata.duplex = 'full'
          }
        }
      })

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
    nodes.value = { ...nodes.value, [node.id]: node }
    return node
  }

  async function update(id: string, data: Partial<NrNode> & { password?: string }) {
    const node = await api.updateNode(id, data)
    nodes.value = { ...nodes.value, [id]: node }
    return node
  }

  async function remove(id: string) {
    await api.deleteNode(id)
    const newNodes = { ...nodes.value }
    delete newNodes[id]
    nodes.value = newNodes
    // Clean up links associated with this node
    links.value = links.value.filter(l => l.source !== id && l.target !== id)
    if (selectedId.value === id) select(null)
  }

  async function createLink(source: string, target: string) {
    const link = await api.createLink(source, target)
    links.value = [...links.value, link]
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
      const updatedNode = { ...nodes.value[id], device_type: result.device_type as NrNode['device_type'] }
      nodes.value = { ...nodes.value, [id]: updatedNode }
    }
    return result.device_type
  }

  return {
    nodes, nodeList, links, connections, connectedCount, isConnected,
    loading, error, selectedId, selected, manuallyDisconnected, isolatedNodes,
    refresh, refreshConnections, create, update, remove, select, detectType,
    createLink, removeLink, discover,
    isolateNode,
    unisolateNode,
    defconLevel,
    setDefcon,
    simulationMode,
    toggleSimulationMode
  }
})
