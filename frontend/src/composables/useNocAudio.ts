import { ref } from 'vue'

/**
 * NOC audio: synthesized alarm tones (Web Audio) + spoken alerts (Web Speech).
 * No assets, no dependencies. Opt-in (persisted); audio context is created on
 * the enabling click (a user gesture, required by browsers).
 */
const enabled = ref(localStorage.getItem('nr_audio') === 'on')
let ctx: AudioContext | null = null
let lastSpoke = 0

function ensureCtx() {
  if (!ctx) {
    try { ctx = new (window.AudioContext || (window as any).webkitAudioContext)() } catch { ctx = null }
  }
  if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {})
  return ctx
}

function tone(freq: number, start: number, dur: number, type: OscillatorType = 'square', gain = 0.06) {
  const c = ensureCtx(); if (!c) return
  const osc = c.createOscillator()
  const g = c.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, c.currentTime + start)
  g.gain.setValueAtTime(0, c.currentTime + start)
  g.gain.linearRampToValueAtTime(gain, c.currentTime + start + 0.01)
  g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + start + dur)
  osc.connect(g); g.connect(c.destination)
  osc.start(c.currentTime + start)
  osc.stop(c.currentTime + start + dur + 0.02)
}

function beep(severity: string) {
  if (!enabled.value) return
  if (severity === 'critical') {        // urgent descending triple
    tone(880, 0, 0.12); tone(660, 0.14, 0.12); tone(440, 0.28, 0.2)
  } else if (severity === 'warning') {   // single mid beep
    tone(620, 0, 0.15, 'triangle')
  } else {                               // soft info blip
    tone(520, 0, 0.08, 'sine', 0.04)
  }
}

function speak(text: string) {
  if (!enabled.value || !('speechSynthesis' in window)) return
  const now = Date.now()
  if (now - lastSpoke < 1200) return  // avoid overlap spam
  lastSpoke = now
  try {
    const u = new SpeechSynthesisUtterance(text)
    u.rate = 1.05; u.pitch = 0.9; u.volume = 0.9
    window.speechSynthesis.speak(u)
  } catch { /* ignore */ }
}

export function useNocAudio() {
  function toggle() {
    enabled.value = !enabled.value
    localStorage.setItem('nr_audio', enabled.value ? 'on' : 'off')
    if (enabled.value) {
      ensureCtx()
      tone(523, 0, 0.1, 'sine'); tone(784, 0.1, 0.15, 'sine')  // power-on chime
      speak('Audio online')
    }
  }

  function announce(ev: { severity: string, message: string }) {
    if (!enabled.value) return
    if (ev.severity !== 'critical' && ev.severity !== 'warning') return
    beep(ev.severity)
    // Speak slightly after the tone so they don't clash
    setTimeout(() => speak(ev.message), 350)
  }

  return { enabled, toggle, announce, beep }
}
