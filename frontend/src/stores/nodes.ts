import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import type { NrNode } from '@/types'

export const useNodesStore = defineStore('nodes', () => {
  const nodes = ref<Record<string, NrNode>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedId = ref<string | null>(null)

  const nodeList = computed(() => Object.values(nodes.value).sort((a, b) => a.name.localeCompare(b.name)))
  const selected = computed(() => selectedId.value ? nodes.value[selectedId.value] : null)

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      nodes.value = await api.listNodes()
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
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
    if (selectedId.value === id) selectedId.value = null
  }

  function select(id: string | null) {
    selectedId.value = id
  }

  async function detectType(id: string) {
    const result = await api.detectDevice(id)
    if (nodes.value[id]) {
      nodes.value[id].device_type = result.device_type as NrNode['device_type']
    }
    return result.device_type
  }

  return { nodes, nodeList, loading, error, selectedId, selected, refresh, create, update, remove, select, detectType }
})
