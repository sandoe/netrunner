<template>
  <div class="boot" @click="finish" @keydown="finish" tabindex="0">
    <div class="boot-scan"></div>
    <div class="boot-inner">
      <div class="boot-logo glitch" data-text="NETRUNNER">NETRUNNER</div>
      <div class="boot-lines">
        <div v-for="(l, i) in shown" :key="i" class="boot-line">
          <span class="boot-ok">[ OK ]</span> {{ l }}
        </div>
      </div>
      <div class="boot-bar"><div class="boot-bar-fill" :style="{ width: pct + '%' }"></div></div>
      <div class="boot-pct">{{ pct }}%  ·  NEURAL LINK {{ pct >= 100 ? 'ESTABLISHED' : 'INITIALIZING' }}</div>
      <div class="boot-skip">click / any key to skip</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const emit = defineEmits<{ done: [] }>()
const LINES = [
  'Initializing neural link…',
  'Decrypting credential vault…',
  'Authenticating operator session…',
  'Spinning up telemetry probes…',
  'Mapping network topology…',
  'Arming threat detection grid…',
  'ACCESS GRANTED',
]
const shown = ref<string[]>([])
const pct = ref(0)
let timers: any[] = []
let done = false

function finish() {
  if (done) return
  done = true
  timers.forEach(clearTimeout)
  emit('done')
}

onMounted(() => {
  const step = 320
  LINES.forEach((l, i) => {
    timers.push(setTimeout(() => {
      shown.value.push(l)
      pct.value = Math.round(((i + 1) / LINES.length) * 100)
    }, i * step))
  })
  timers.push(setTimeout(finish, LINES.length * step + 600))
  // focus for keydown-to-skip
  timers.push(setTimeout(() => (document.querySelector('.boot') as HTMLElement)?.focus(), 0))
})
onUnmounted(() => timers.forEach(clearTimeout))
</script>

<style scoped>
.boot {
  position: fixed; inset: 0; z-index: 20000; outline: none;
  background: radial-gradient(circle at 50% 40%, #05140d 0%, #000 80%);
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; cursor: pointer;
  animation: bootfade 0.3s ease;
}
.boot-scan { position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(0deg, rgba(0,255,157,0.05) 0 2px, transparent 2px 4px); }
.boot-inner { width: 520px; max-width: 90vw; }
.boot-logo {
  font-family: 'Orbitron', monospace; font-size: 52px; font-weight: 900; letter-spacing: 10px;
  color: #00ff9d; text-align: center; text-shadow: 0 0 24px rgba(0,255,157,0.6); margin-bottom: 28px;
}
.glitch { position: relative; }
.glitch::before, .glitch::after {
  content: attr(data-text); position: absolute; left: 0; top: 0; width: 100%;
}
.glitch::before { color: #ff2d6e; animation: glitch1 2s infinite linear alternate; clip-path: inset(0 0 60% 0); }
.glitch::after  { color: #00e5ff; animation: glitch2 1.6s infinite linear alternate; clip-path: inset(55% 0 0 0); }
@keyframes glitch1 { 0%{transform:translate(0)} 20%{transform:translate(-3px,1px)} 40%{transform:translate(2px,-1px)} 100%{transform:translate(0)} }
@keyframes glitch2 { 0%{transform:translate(0)} 30%{transform:translate(3px,-1px)} 60%{transform:translate(-2px,1px)} 100%{transform:translate(0)} }
.boot-lines { min-height: 160px; font-size: 13px; color: #cdd6e4; }
.boot-line { margin: 5px 0; animation: linein 0.2s ease; }
.boot-ok { color: #00ff9d; }
.boot-line:last-child { color: #00ff9d; font-weight: bold; letter-spacing: 2px; }
@keyframes linein { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; } }
.boot-bar { height: 4px; background: rgba(0,255,157,0.12); border-radius: 2px; margin-top: 18px; overflow: hidden; }
.boot-bar-fill { height: 100%; background: #00ff9d; box-shadow: 0 0 10px #00ff9d; transition: width 0.3s; }
.boot-pct { font-size: 11px; color: #00ff9d; letter-spacing: 2px; margin-top: 10px; }
.boot-skip { font-size: 10px; color: #4a5a72; margin-top: 18px; text-align: center; }
@keyframes bootfade { from { opacity: 0; } to { opacity: 1; } }
</style>
