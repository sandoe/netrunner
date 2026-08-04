import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NodeStatsPanel from '../NetworkController/NodeStatsPanel.vue'

describe('NodeStatsPanel', () => {
  it('renders simulation mode correctly', () => {
    const wrapper = mount(NodeStatsPanel, {
      props: {
        isRealData: false,
        isSimulation: true,
        csiSource: 'synthetic',
        dataStatus: 'Active',
        selectedTelemetry: { capabilities: { wifi_chip: 'brcmfmac', nexmon: true } },
        motionDetected: false,
        typingActive: false
      }
    })

    expect(wrapper.text()).toContain('SIMULATION')
  })

  it('renders real data mode correctly', () => {
    const wrapper = mount(NodeStatsPanel, {
      props: {
        isRealData: true,
        isSimulation: false,
        csiSource: 'nexmon',
        dataStatus: 'Active',
        selectedTelemetry: { capabilities: { wifi_chip: 'brcmfmac', nexmon: true } },
        motionDetected: true,
        typingActive: true
      }
    })

    expect(wrapper.text()).toContain('REAL CSI')
    expect(wrapper.text()).toContain('ALERT')
    expect(wrapper.text()).toContain('INTERCEPTING')
  })
})
