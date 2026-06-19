<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content cyber-glass" role="dialog" aria-modal="true" aria-labelledby="user-mgmt-title">
      <div class="modal-header">
        <div class="modal-title" id="user-mgmt-title">
          <span class="icon">👤</span>
          <span>USER MANAGEMENT</span>
        </div>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- Create user -->
        <div class="card">
          <div class="card-title">CREATE OPERATOR</div>
          <form class="create-form" @submit.prevent="createUser">
            <div class="row">
              <div class="fg">
                <label>USERNAME</label>
                <input v-model="form.username" type="text" placeholder="operator id" autocomplete="off" spellcheck="false" />
              </div>
              <div class="fg">
                <label>PASSWORD</label>
                <input v-model="form.password" type="password" placeholder="••••••••" autocomplete="new-password" />
              </div>
              <div class="fg fg-role">
                <label>ROLE</label>
                <select v-model="form.role">
                  <option value="analyst">analyst</option>
                  <option value="admin">admin</option>
                </select>
              </div>
              <button type="submit" class="btn-add-user" :disabled="busy || !form.username || !form.password">
                <span v-if="busy" class="spinner"></span>
                <span v-else>+ ADD</span>
              </button>
            </div>
            <div v-if="error" class="msg error">{{ error }}</div>
            <div v-if="notice" class="msg ok">{{ notice }}</div>
          </form>
        </div>

        <!-- Users list -->
        <div class="card">
          <div class="card-title">OPERATORS ({{ users.length }})</div>
          <table class="user-table">
            <thead>
              <tr><th>USERNAME</th><th>ROLE</th><th>CREATED</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.username">
                <td class="u-name">{{ u.username }}<span v-if="u.username === currentUser" class="you">(you)</span></td>
                <td><span class="role-badge" :class="u.role">{{ u.role }}</span></td>
                <td class="u-date">{{ u.created || '—' }}</td>
                <td class="u-action">
                  <button
                    class="btn-del"
                    :disabled="u.username === currentUser"
                    :title="u.username === currentUser ? 'You cannot delete your own account' : 'Delete user'"
                    @click="removeUser(u.username)"
                  >✕</button>
                </td>
              </tr>
              <tr v-if="users.length === 0"><td colspan="4" class="empty">No operators.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'

const emit = defineEmits(['close'])

onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))
function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

const users = ref<{ username: string, role: string, created?: string }[]>([])
const form = ref({ username: '', password: '', role: 'analyst' })
const busy = ref(false)
const error = ref('')
const notice = ref('')
const currentUser = localStorage.getItem('nr_username') || ''

async function load() {
  error.value = ''
  try {
    const res = await api.listUsers()
    users.value = res.users
  } catch (e: any) {
    error.value = String(e.message || e)
  }
}

async function createUser() {
  error.value = ''; notice.value = ''
  busy.value = true
  try {
    await api.createUser({ ...form.value })
    notice.value = `Operator "${form.value.username}" created.`
    form.value = { username: '', password: '', role: 'analyst' }
    await load()
  } catch (e: any) {
    error.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

async function removeUser(username: string) {
  if (!confirm(`Delete operator "${username}"?`)) return
  error.value = ''; notice.value = ''
  try {
    await api.deleteUser(username)
    await load()
  } catch (e: any) {
    error.value = String(e.message || e)
  }
}

onMounted(load)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9000;
  backdrop-filter: blur(4px);
}
.modal-content {
  width: 100%;
  max-width: 640px;
  background: rgba(8, 13, 24, 0.97);
  border: 1px solid var(--border, #1a2540);
  border-radius: var(--r, 8px);
  box-shadow: 0 0 50px rgba(0, 229, 255, 0.12);
  font-family: var(--font-hd, 'Orbitron', monospace);
  overflow: hidden;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border, #1a2540);
}
.modal-title { display: flex; align-items: center; gap: 10px; color: var(--textwh); letter-spacing: 2px; font-size: 14px; }
.btn-close { background: none; border: none; color: var(--text); font-size: 24px; cursor: pointer; line-height: 1; }
.btn-close:hover { color: var(--pink); }
.modal-body { padding: 20px; display: flex; flex-direction: column; gap: 18px; max-height: 70vh; overflow-y: auto; }

.card { border: 1px solid var(--border); border-radius: 6px; padding: 16px; background: rgba(0, 0, 0, 0.25); }
.card-title { color: var(--cyan); font-size: 11px; letter-spacing: 2px; margin-bottom: 14px; }

.create-form .row { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }
.fg { display: flex; flex-direction: column; flex: 1 1 140px; min-width: 0; }
.fg-role { flex: 0 0 110px; }
.fg label { font-size: 10px; color: var(--text); margin-bottom: 5px; letter-spacing: 1px; }
.fg input, .fg select {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border2);
  color: var(--textwh);
  padding: 9px 10px;
  font-family: var(--font-co, 'JetBrains Mono', monospace);
  font-size: 13px;
  border-radius: 4px;
  outline: none;
}
.fg input:focus, .fg select:focus { border-color: var(--cyan); box-shadow: 0 0 10px rgba(0, 229, 255, 0.2); }
.btn-add-user {
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid var(--cyan-d);
  color: var(--cyan);
  padding: 9px 16px;
  font-family: var(--font-hd, 'Orbitron', monospace);
  font-size: 12px;
  letter-spacing: 1px;
  cursor: pointer;
  border-radius: 4px;
  white-space: nowrap;
}
.btn-add-user:hover:not(:disabled) { background: rgba(0, 229, 255, 0.2); }
.btn-add-user:disabled { opacity: 0.4; cursor: not-allowed; }

.msg { margin-top: 12px; font-family: var(--font-co, monospace); font-size: 12px; }
.msg.error { color: var(--pink); }
.msg.ok { color: var(--green); }

.user-table { width: 100%; border-collapse: collapse; font-family: var(--font-co, 'JetBrains Mono', monospace); font-size: 12px; }
.user-table th { text-align: left; color: var(--text); font-size: 10px; letter-spacing: 1px; padding: 6px 8px; border-bottom: 1px solid var(--border); }
.user-table td { padding: 9px 8px; border-bottom: 1px solid rgba(26, 37, 64, 0.5); color: var(--textbr); }
.u-name { color: var(--textwh); }
.you { color: var(--cyan); font-size: 10px; margin-left: 6px; }
.u-date { color: var(--text); }
.u-action { text-align: right; }
.role-badge { padding: 2px 8px; border-radius: 3px; font-size: 10px; letter-spacing: 1px; }
.role-badge.admin { background: rgba(255, 45, 110, 0.15); color: var(--pink); border: 1px solid rgba(255, 45, 110, 0.4); }
.role-badge.analyst { background: rgba(0, 229, 255, 0.1); color: var(--cyan); border: 1px solid rgba(0, 229, 255, 0.3); }
.btn-del { background: none; border: 1px solid var(--border); color: var(--pink); width: 24px; height: 24px; border-radius: 4px; cursor: pointer; }
.btn-del:hover:not(:disabled) { background: rgba(255, 45, 110, 0.15); }
.btn-del:disabled { opacity: 0.25; cursor: not-allowed; }
.empty { color: var(--text); text-align: center; padding: 16px; }
button:focus-visible, .btn-action:focus-visible, .btn-close:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
</style>
