<template>
  <div class="ai-sidebar" :class="{ open: isOpen }">
    <div class="ai-toggle" @click="isOpen = !isOpen">
      <span class="ai-toggle-icon">🤖</span>
      <span class="ai-toggle-text">AI ASSISTANT</span>
    </div>

    <div class="ai-content">
      <div class="ai-header">
        <div class="ai-title">NEURAL LINK v1.0</div>
        <button class="btn-close" @click="isOpen = false">×</button>
      </div>

      <div class="ai-messages" ref="msgRef">
        <div v-for="(msg, i) in messages" :key="i" class="message" :class="msg.role">
          <div class="msg-header">
            <span class="msg-role">{{ msg.role.toUpperCase() }}</span>
          </div>
          <div class="msg-text">{{ msg.content }}</div>
        </div>
        <div v-if="loading" class="message assistant loading">
          <div class="msg-text">THINKING...</div>
        </div>
      </div>

      <div class="ai-input-area">
        <textarea 
          v-model="input" 
          placeholder="ASK ANYTHING... (E.G. 'WHAT IS THE IP OF NODE 1?')" 
          @keydown.enter.prevent="sendMessage"
          :disabled="loading"
        ></textarea>
        <button class="btn-send" @click="sendMessage" :disabled="loading || !input.trim()">SEND</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { api } from '@/api/client'

const isOpen = ref(false)
const input = ref('')
const loading = ref(false)
const msgRef = ref<HTMLElement | null>(null)

interface Msg { role: 'user' | 'assistant' | 'system'; content: string }
const messages = ref<Msg[]>([
  { role: 'assistant', content: 'SYSTEM READY. I HAVE DIRECT ACCESS TO NODES AND TOPOLOGY. HOW CAN I HELP?' }
])

async function sendMessage() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  
  await nextTick()
  scrollToBottom()

  try {
    const res = await api.aiChat(messages.value)
    messages.value.push(res as Msg)
  } catch (e) {
    messages.value.push({ role: 'assistant', content: `ERROR: ${String(e)}` })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (msgRef.value) {
    msgRef.value.scrollTop = msgRef.value.scrollHeight
  }
}

watch(isOpen, (val) => {
  if (val) {
    nextTick(scrollToBottom)
  }
})
</script>

<style scoped>
.ai-sidebar {
  position: fixed;
  right: -340px;
  top: 0;
  width: 340px;
  height: 100vh;
  background: var(--bg2);
  border-left: 1px solid var(--border);
  z-index: 2000;
  transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 30px rgba(0,0,0,0.5);
}

.ai-sidebar.open {
  right: 0;
}

.ai-toggle {
  position: absolute;
  left: -40px;
  top: 50%;
  transform: translateY(-50%);
  background: var(--bg2);
  border: 1px solid var(--border);
  border-right: none;
  padding: 15px 10px;
  cursor: pointer;
  writing-mode: vertical-rl;
  border-radius: var(--r) 0 0 var(--r);
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 2px;
}

.ai-toggle:hover {
  background: var(--bg3);
  color: var(--green);
}

.ai-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ai-header {
  padding: 15px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-title {
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--cyan);
  text-shadow: 0 0 8px var(--cyan);
}

.btn-close {
  background: none;
  border: none;
  color: var(--text);
  font-size: 20px;
  cursor: pointer;
}

.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  font-family: var(--font-co);
  font-size: 12px;
  line-height: 1.6;
}

.msg-header {
  margin-bottom: 4px;
}

.msg-role {
  font-family: var(--font-hd);
  font-size: 8px;
  letter-spacing: 1px;
}

.user .msg-role { color: var(--purple); }
.assistant .msg-role { color: var(--green); }

.msg-text {
  background: var(--bg3);
  padding: 12px;
  border-radius: var(--r);
  border: 1px solid var(--border);
  color: var(--textwh);
  white-space: pre-wrap;
}

.assistant .msg-text {
  border-left: 2px solid var(--green);
}

.user .msg-text {
  border-left: 2px solid var(--purple);
}

.loading .msg-text {
  color: var(--text);
  font-style: italic;
  animation: blink 1.5s infinite;
}

@keyframes blink {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}

.ai-input-area {
  padding: 20px;
  border-top: 1px solid var(--border);
  background: var(--bg3);
}

textarea {
  width: 100%;
  height: 80px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--r);
  color: var(--textwh);
  padding: 10px;
  font-family: var(--font-co);
  font-size: 12px;
  outline: none;
  resize: none;
  margin-bottom: 10px;
}

textarea:focus {
  border-color: var(--cyan);
}

.btn-send {
  width: 100%;
  background: var(--cyan);
  color: var(--bg);
  border: none;
  padding: 10px;
  border-radius: var(--r);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-send:hover:not(:disabled) {
  box-shadow: var(--shadow-c);
  transform: translateY(-1px);
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
