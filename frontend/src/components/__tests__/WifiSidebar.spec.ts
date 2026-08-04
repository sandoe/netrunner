import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WifiSidebar from '../NetworkController/WifiSidebar.vue'

describe('WifiSidebar', () => {
  it('renders active nodes correctly and emits events', async () => {
    const wrapper = mount(WifiSidebar, {
      props: {
        activeNodes: [{ id: '1', ip: '192.168.1.100' }],
        selectedNodeId: '1',
        isNodeActive: (id: string) => id === '1',
        isRealData: true,
        isSimulation: false,
        csiSource: 'nexmon',
        dataStatus: 'Active',
        selectedTelemetry: { capabilities: { wifi_chip: 'brcmfmac', nexmon: true } },
        motionDetected: false,
        typingActive: false
      }
    })

    expect(wrapper.text()).toContain('WIFI & CSI ANALYSIS')
    expect(wrapper.text()).toContain('192.168.1.100')

    await wrapper.find('.start-btn').trigger('click')
    expect(wrapper.emitted()).toHaveProperty('startNode')
    expect(wrapper.emitted('startNode')![0]).toEqual(['1'])

    await wrapper.find('.node-item').trigger('click')
    expect(wrapper.emitted()).toHaveProperty('update:selectedNodeId')
    expect(wrapper.emitted('update:selectedNodeId')![0]).toEqual(['1'])
  })
})
