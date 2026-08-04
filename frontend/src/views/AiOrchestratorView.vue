<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { api } from '@/api/client';

const messages = ref([
  { role: 'assistant', content: 'Netrunner AI Orchestrator online. Awaiting instructions...' }
]);
const inputMsg = ref('');
const isProcessing = ref(false);
const messagesContainer = ref(null);

const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const sendMsg = async () => {
  if (!inputMsg.value.trim() || isProcessing.value) return;

  messages.value.push({ role: 'user', content: inputMsg.value });
  const reqMsg = inputMsg.value;
  inputMsg.value = '';
  isProcessing.value = true;
  await scrollToBottom();

  try {
    const { data } = await api.post('/v1/ai/chat', {
      messages: messages.value.map(m => ({ role: m.role, content: m.content }))
    });

    // Add the response
    messages.value.push({ role: 'assistant', content: data.content });
  } catch (err) {
    messages.value.push({ role: 'assistant', content: `[ERROR] ${err.response?.data?.detail || err.message}` });
  } finally {
    isProcessing.value = false;
    await scrollToBottom();
  }
};

</script>

<template>
  <div class="ai-orchestrator-container">
    <div class="page-header cyber-panel">
      <h2>AI ORCHESTRATOR</h2>
      <p>Automate workflows, deploy agents, and manage the Netrunner ecosystem via natural language.</p>
    </div>

    <div class="cyber-panel chat-panel">
      <div class="messages" ref="messagesContainer">
        <div v-for="(msg, idx) in messages" :key="idx" class="message-row" :class="msg.role">
          <div class="message-bubble">
            <div class="message-role">{{ msg.role === 'user' ? 'OPERATOR' : 'AI ENGINE' }}</div>
            <div class="message-content">{{ msg.content }}</div>
          </div>
        </div>
        <div v-if="isProcessing" class="message-row assistant">
          <div class="message-bubble processing">
            <span class="blinking">PROCESSING...</span>
          </div>
        </div>
      </div>

      <div class="input-area">
        <input
          v-model="inputMsg"
          @keyup.enter="sendMsg"
          placeholder="Enter command (e.g., 'Scan the network', 'Deploy a honeypot', 'Generate PDF report')..."
          class="cyber-input"
          :disabled="isProcessing"
        />
        <button class="btn-engage" @click="sendMsg" :disabled="isProcessing || !inputMsg.trim()">
          SEND
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-orchestrator-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.page-header {
  padding: 20px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  flex-shrink: 0;
}
.page-header h2 {
  color: var(--cyan);
  margin: 0 0 8px 0;
  font-family: var(--font-hd);
  letter-spacing: 2px;
}
.page-header p {
  margin: 0;
  color: var(--textbr);
  font-size: 14px;
}

.chat-panel {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.messages {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message-row {
  display: flex;
  width: 100%;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.message-row.user .message-bubble {
  border-color: var(--cyan);
  border-right: 4px solid var(--cyan);
}

.message-row.assistant .message-bubble {
  border-color: var(--pink);
  border-left: 4px solid var(--pink);
  background: rgba(255, 0, 128, 0.05);
}

.message-role {
  font-size: 11px;
  opacity: 0.6;
  margin-bottom: 6px;
  letter-spacing: 1px;
}

.message-row.user .message-role {
  color: var(--cyan);
  text-align: right;
}

.message-row.assistant .message-role {
  color: var(--pink);
}

.processing .blinking {
  animation: blink 1s infinite;
  color: var(--pink);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.input-area {
  display: flex;
  padding: 15px;
  background: var(--bg);
  border-top: 1px solid var(--border);
  gap: 10px;
}

.input-area .cyber-input {
  flex-grow: 1;
  font-size: 14px;
}
</style>
