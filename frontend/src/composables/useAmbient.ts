import { ref } from 'vue'

/**
 * Ambient cyberpunk drone (Web Audio, no assets). A bed of detuned oscillators
 * through a slowly-sweeping lowpass; intensity (0..1) opens the filter and
 * raises the volume so the room "tenses up" as network alerts pile in.
 */
const active = ref(false)
let ctx: AudioContext | null = null
let master: GainNode | null = null
let filter: BiquadFilterNode | null = null

function build() {
  ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
  master = ctx.createGain(); master.gain.value = 0; master.connect(ctx.destination)
  filter = ctx.createBiquadFilter(); filter.type = 'lowpass'; filter.frequency.value = 380; filter.Q.value = 6
  filter.connect(master)

  const mk = (type: OscillatorType, freq: number, detune = 0, gain = 0.5) => {
    const o = ctx!.createOscillator(); o.type = type; o.frequency.value = freq; o.detune.value = detune
    const g = ctx!.createGain(); g.gain.value = gain
    o.connect(g); g.connect(filter!); o.start()
  }
  mk('sawtooth', 55)            // A1 root
  mk('sawtooth', 55, 7, 0.4)    // detuned beat
  mk('sine', 82.4, 0, 0.3)      // E2 fifth
  mk('triangle', 110, -4, 0.18) // A2 shimmer

  // Slow filter sweep for movement
  const lfo = ctx.createOscillator(); lfo.frequency.value = 0.06
  const lfoGain = ctx.createGain(); lfoGain.gain.value = 110
  lfo.connect(lfoGain); lfoGain.connect(filter.frequency); lfo.start()
}

export function useAmbient() {
  function start() {
    if (active.value) return
    if (!ctx) build()
    ctx!.resume().catch(() => {})
    master!.gain.cancelScheduledValues(ctx!.currentTime)
    master!.gain.linearRampToValueAtTime(0.05, ctx!.currentTime + 2.5)
    active.value = true
  }
  function stop() {
    if (!ctx || !master) { active.value = false; return }
    master.gain.cancelScheduledValues(ctx.currentTime)
    master.gain.linearRampToValueAtTime(0, ctx.currentTime + 1.2)
    active.value = false
  }
  function setIntensity(t: number) {
    if (!ctx || !filter || !master) return
    const k = Math.max(0, Math.min(1, t))
    filter.frequency.linearRampToValueAtTime(380 + k * 2200, ctx.currentTime + 0.6)
    if (active.value) master.gain.linearRampToValueAtTime(0.045 + k * 0.06, ctx.currentTime + 0.6)
  }
  return { active, start, stop, setIntensity }
}
