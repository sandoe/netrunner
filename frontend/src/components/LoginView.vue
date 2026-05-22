<template>
  <div class="login-wrapper">
    <div class="scanline"></div>
    <div class="login-box glass-panel">
      <div class="glitch-title">NETRUNNER</div>
      <div class="subtitle">ENTERPRISE COMMAND CENTER // AUTHENTICATION</div>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="input-group">
          <label>OPERATOR ID</label>
          <input v-model="username" type="text" placeholder="admin or analyst" autofocus required autocomplete="off" spellcheck="false" />
        </div>
        
        <div class="input-group">
          <label>ACCESS CODE</label>
          <input v-model="password" type="password" placeholder="••••••••" required />
        </div>
        
        <div class="error-msg" v-if="error">{{ error }}</div>
        
        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? 'AUTHENTICATING...' : 'INITIALIZE CONNECTION' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'

const emit = defineEmits(['authenticated'])

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const res = await api.login({ username: username.value, password: password.value })
    localStorage.setItem('nr_token', res.access_token)
    localStorage.setItem('nr_role', res.role)
    emit('authenticated', res.role)
  } catch (e: any) {
    error.value = "ACCESS DENIED: Invalid credentials."
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  position: fixed;
  inset: 0;
  background: var(--bg);
  background-image: radial-gradient(circle at center, var(--bg2) 0%, var(--bg) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  font-family: var(--font-hd);
}

.login-box {
  background: rgba(8, 13, 24, 0.85);
  border: 1px solid var(--border);
  box-shadow: 0 0 50px rgba(0, 229, 255, 0.1);
  padding: 40px;
  width: 100%;
  max-width: 450px;
  border-radius: var(--r);
  position: relative;
  overflow: hidden;
}

.login-box::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, transparent, var(--cyan), transparent);
}

.glitch-title {
  font-size: 36px;
  color: var(--textwh);
  text-align: center;
  letter-spacing: 6px;
  margin-bottom: 8px;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

.subtitle {
  font-size: 10px;
  color: var(--cyan);
  text-align: center;
  letter-spacing: 2px;
  margin-bottom: 32px;
}

.input-group {
  margin-bottom: 24px;
}

.input-group label {
  display: block;
  font-size: 11px;
  color: var(--textbr);
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.input-group input {
  width: 100%;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border2);
  color: var(--textwh);
  padding: 12px 16px;
  font-family: var(--font-co);
  font-size: 14px;
  border-radius: 4px;
  transition: all 0.3s ease;
  outline: none;
}

.input-group input:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.2);
}

.btn-login {
  width: 100%;
  padding: 14px;
  background: var(--bg3);
  border: 1px solid var(--cyan-d);
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 13px;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 4px;
  margin-top: 10px;
}

.btn-login:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
  text-shadow: 0 0 5px var(--cyan);
}

.btn-login:disabled {
  opacity: 0.5;
  cursor: wait;
}

.error-msg {
  color: var(--pink);
  font-family: var(--font-co);
  font-size: 12px;
  text-align: center;
  margin-bottom: 16px;
  text-shadow: 0 0 10px rgba(255, 45, 110, 0.5);
}
</style>
