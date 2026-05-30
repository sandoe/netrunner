<template>
  <div class="shell-panel">
    <div class="shell-mode">
      <button class="mode-btn" :class="{ active: mode === 'interactive' }" @click="mode = 'interactive'">
        ⌨ INTERACTIVE
      </button>
      <button class="mode-btn" :class="{ active: mode === 'script' }" @click="mode = 'script'">
        📜 SCRIPT
      </button>
      <span class="mode-hint">
        {{ mode === 'interactive' ? 'Live PTY shell' : 'Batch commands — structured output' }}
      </span>
    </div>
    <div class="shell-body">
      <!-- v-show keeps the live shell connection + script text alive across toggles -->
      <Terminal v-show="mode === 'interactive'" :node="node" />
      <ExecPanel v-show="mode === 'script'" v-if="node" :node-id="node.id" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Terminal from './Terminal.vue'
import ExecPanel from './ExecPanel.vue'
import type { NrNode } from '@/types'

defineProps<{ node: NrNode | null }>()

const mode = ref<'interactive' | 'script'>(
  (localStorage.getItem('netrunner_shell_mode') as any) || 'interactive')
watch(mode, m => localStorage.setItem('netrunner_shell_mode', m))
</script>

<style scoped>
.shell-panel { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

.shell-mode {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg2);
}
.mode-btn {
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 1px;
  padding: 5px 12px;
  border-radius: 4px;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--textbr);
  cursor: pointer;
  transition: all .2s;
}
.mode-btn:hover { color: var(--textwh); border-color: var(--border2); }
.mode-btn.active {
  background: var(--bg4);
  color: var(--cyan);
  border-color: var(--cyan-d);
  box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.1);
}
.mode-hint {
  margin-left: auto;
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--text);
  opacity: 0.6;
}
.shell-body { flex: 1; min-height: 0; position: relative; }
.shell-body > * { height: 100%; }
</style>
