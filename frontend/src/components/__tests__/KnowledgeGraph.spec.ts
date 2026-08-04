import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import KnowledgeGraph from '../KnowledgeGraph.vue'
import { api } from '@/api/client'
import ForceGraph3D from '3d-force-graph'

// Mock 3d-force-graph
const mockGraphInstance = {
  graphData: vi.fn().mockReturnThis(),
  nodeAutoColorBy: vi.fn().mockReturnThis(),
  nodeThreeObject: vi.fn().mockReturnThis(),
  linkDirectionalArrowLength: vi.fn().mockReturnThis(),
  linkDirectionalArrowRelPos: vi.fn().mockReturnThis(),
  linkCurvature: vi.fn().mockReturnThis(),
  linkColor: vi.fn().mockReturnThis(),
  linkWidth: vi.fn().mockReturnThis(),
  linkDirectionalParticles: vi.fn().mockReturnThis(),
  linkDirectionalParticleWidth: vi.fn().mockReturnThis(),
  linkDirectionalParticleColor: vi.fn().mockReturnThis(),
  onNodeClick: vi.fn().mockReturnThis(),
  backgroundColor: vi.fn().mockReturnThis(),
  width: vi.fn().mockReturnThis(),
  height: vi.fn().mockReturnThis(),
  cameraPosition: vi.fn().mockReturnThis(),
};

const mockForceGraph3D = vi.fn(() => vi.fn(() => mockGraphInstance));

vi.mock('3d-force-graph', () => {
  return {
    default: vi.fn(() => vi.fn(() => mockGraphInstance))
  }
})

// Mock api client
vi.mock('@/api/client', () => ({
  api: {
    queryIntelligence: vi.fn()
  }
}))

describe('KnowledgeGraph.vue', () => {
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    document.body.innerHTML = ''; // Clean up body for document.getElementById
    vi.clearAllMocks();
  })

  afterEach(() => {
    global.fetch = originalFetch;
  })

  it('renders graph with API data and initializes 3d-force-graph', async () => {
    global.fetch = vi.fn(async (url) => {
      if (url === '/api/v1/nodes') {
        return {
          ok: true,
          json: async () => [{ id: '1', label: 'Test Node', type: 'Machine' }]
        } as Response
      }
      if (url === '/api/v1/links') {
        return {
          ok: true,
          json: async () => [{ source: '1', target: '2', label: 'connects' }]
        } as Response
      }
      return { ok: false } as Response
    })

    const wrapper = mount(KnowledgeGraph, {
      attachTo: document.body
    })

    // Wait for async fetchGraph
    await new Promise(r => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    // 3d-force-graph should have been instantiated
    expect(mockGraphInstance.graphData).toHaveBeenCalled()

    // Check if graphData was called with expected mapped links
    const graphDataCall = mockGraphInstance.graphData.mock.calls[0][0]
    expect(graphDataCall.nodes).toEqual([{ id: '1', label: 'Test Node', type: 'Machine' }])
    expect(graphDataCall.links).toEqual([{ source: '1', target: '2', label: 'connects' }])
  })

  it('falls back to mock data if API fails', async () => {
    global.fetch = vi.fn(async () => {
      return { ok: false, status: 500 } as Response
    })

    const wrapper = mount(KnowledgeGraph, {
      attachTo: document.body
    })

    // Wait for async fetchGraph
    await new Promise(r => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    // Should fall back to mock data in component
    expect(mockGraphInstance.graphData).toHaveBeenCalled()
    const graphDataCall = mockGraphInstance.graphData.mock.calls[0][0]
    expect(graphDataCall.nodes.length).toBeGreaterThan(0)
    expect(graphDataCall.nodes[0].id).toBe('1')
    expect(graphDataCall.nodes[0].label).toBe('Gateway Node')
  })

  it('submits RAG query and displays answer', async () => {
    global.fetch = vi.fn(async () => ({ ok: false } as Response)) // Fallback to mock graph

    ;(api.queryIntelligence as any).mockResolvedValue({ answer: 'This is an AI response.' })

    const wrapper = mount(KnowledgeGraph, {
      attachTo: document.body
    })

    // Wait for initial render and graph init
    await new Promise(r => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    // Set input value
    const input = wrapper.find('.rag-input')
    await input.setValue('What is going on?')

    // Click submit
    await wrapper.find('button.btn-primary').trigger('click')

    // Wait for API resolution
    await new Promise(r => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    expect(api.queryIntelligence).toHaveBeenCalledWith('What is going on?')
    expect(wrapper.text()).toContain('This is an AI response.')
  })
})
