import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import ActiveDefensePanel from '../ActiveDefensePanel.vue'

describe('ActiveDefensePanel.vue', () => {
  it('renders locked state when user is not admin', () => {
    const wrapper = mount(ActiveDefensePanel, {
      props: { nodeId: 'node_1' },
      global: {
        plugins: [createTestingPinia({
          createSpy: vi.fn,
          initialState: {
            nodes: { nodes: { node_1: { id: 'node_1', name: 'Test Node' } } }
          }
        })],
        provide: {
          userRole: 'analyst'
        }
      }
    })

    expect(wrapper.text()).toContain('[LOCKED: ADMIN CLEARANCE REQUIRED]')
    expect(wrapper.find('button.btn-danger').exists()).toBe(false)
  })

  it('renders admin buttons when user is admin', () => {
    const wrapper = mount(ActiveDefensePanel, {
      props: { nodeId: 'node_1' },
      global: {
        plugins: [createTestingPinia({
          createSpy: vi.fn,
          initialState: {
            nodes: { nodes: { node_1: { id: 'node_1', name: 'Test Node' } } }
          }
        })],
        provide: {
          userRole: 'admin'
        }
      }
    })

    expect(wrapper.text()).not.toContain('[LOCKED: ADMIN CLEARANCE REQUIRED]')
    expect(wrapper.find('button.btn-danger').exists()).toBe(true)
    expect(wrapper.find('button.btn-danger').text()).toContain('ISOLATE NODE (PANIC)')
  })
})
