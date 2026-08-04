<template>
  <div class="start-menu glass-panel" v-if="isOpen">
    <div class="start-menu-left">
      <!-- Fast Actions (formerly Topbar right) -->
      <div class="fast-actions">
        <button class="btn-icon" :class="{ 'holo-on': holoMode }" @click="$emit('toggle-holo')" title="HOLO mode">🛸</button>
        <button class="btn-icon" @click="$emit('toggle-audio')" title="Audio">{{ audioEnabled ? '🔊' : '🔇' }}</button>
        <button class="btn-icon" @click="$emit('open-settings')" title="Settings">⚙️</button>
      </div>

      <!-- User Profile -->
      <div class="user-profile">
        <div class="avatar">👨‍💻</div>
        <div class="user-info">
          <div class="user-id">{{ currentUsername || 'operator' }}</div>
          <div class="user-role" :class="userRole">{{ userRole }}</div>
        </div>
      </div>

      <button class="btn-logout" @click="$emit('logout')">LOGOUT ⏻</button>
    </div>

    <div class="start-menu-right">
      <div class="app-grid">
        <div class="app-category">
          <h3>CORE SYSTEMS</h3>
          <div class="app-list">
            <button class="app-btn" @click="emit('show-desktop'); emit('close')">🖥️ Vis Skrivebord</button>
            <button class="app-btn" @click="launch('dashboard', 'Dashboard', '⎈')">⎈ Dashboard</button>
            <button class="app-btn" @click="launch('alerts', 'Alert Inbox', '🚨')">🚨 Alert Inbox</button>
            <button class="app-btn" @click="launch('reports', 'Reports', '📑')">📑 Reports</button>
            <button v-if="userRole !== 'student'" class="app-btn" @click="launch('ai', 'AI Playbooks', '🧠')">🧠 AI Playbooks</button>
          </div>
        </div>

        <div class="app-category">
          <h3>NETWORK & INFRA</h3>
          <div class="app-list">
            <button class="app-btn" @click="launch('topology', 'Topology', '🕸️')">🕸️ Topology & Maps</button>
            <button class="app-btn" @click="launch('network', 'Target Nodes', '🔌')">🔌 Network Controller</button>
            <button class="app-btn" @click="launch('osi', 'OSI Inspector', '📡')">📡 OSI Inspector</button>
            <button class="app-btn" @click="launch('host', 'Local Host', '💻')">💻 Local Host</button>
            <button v-if="userRole !== 'student'" class="app-btn" @click="launch('database', 'Database', '🗄️')">🗄️ Database Control</button>
          </div>
        </div>

        <div class="app-category">
          <h3>OPERATIONS & INTEL</h3>
          <div class="app-list">
            <button class="app-btn" @click="launch('codex', 'Cyberdeck Codex', '📖')">📖 Cyberdeck Codex</button>
            <button v-if="userRole !== 'student'" class="app-btn" @click="launch('hunting', 'Threat Hunting', '🔍')">🔍 Threat Hunting</button>
            <button v-if="userRole !== 'student'" class="app-btn" @click="launch('recon', 'Subnet Scan', '📡')">📡 Subnet Scan</button>
            <button v-if="userRole !== 'student'" class="app-btn" @click="launch('analytics', 'Analytics Center', '📊')">📊 Analytics Center</button>
            <button v-if="userRole !== 'student'" class="app-btn" @click="launch('kismet', 'Wireless IDS', '📶')">📶 Wireless IDS</button>
            <button v-if="userRole !== 'student'" class="app-btn" @click="launch('intelligence', 'Intelligence', '🧠')">🧠 Intelligence & TTP</button>
          </div>
        </div>

        <div v-if="userRole !== 'student'" class="app-category">
          <h3>RED TEAM</h3>
          <div class="app-list">
            <button class="app-btn btn-attack" @click="launch('attack', 'Attack Matrix', '☠️')">☠️ Attack Matrix</button>
            <button class="app-btn btn-attack" @click="launch('layer2', 'L2 Tactical', '🔌')">🔌 L2 Tactical</button>
            <button class="app-btn btn-attack" @click="launch('layer3', 'L3 Tactical', '🌐')">🌐 L3 Tactical</button>
            <button class="app-btn btn-attack" @click="launch('layer4', 'L4 Tactical', '⚡')">⚡ L4 Tactical</button>
            <button class="app-btn btn-attack" @click="launch('layer5', 'L5 Tactical', '🎭')">🎭 L5 Tactical</button>
            <button class="app-btn btn-attack" @click="launch('layer6', 'L6 Tactical', '📦')">📦 L6 Tactical</button>
            <button class="app-btn btn-attack" @click="launch('layer7', 'L7 Tactical', '🕸️')">🕸️ L7 Tactical</button>
            <button class="app-btn btn-attack" @click="launch('wifi-attack', 'WiFi Attacks', '📶')">📶 WiFi Attacks</button>
            <button class="app-btn btn-attack" @click="launch('bruteforce', 'Bruteforce Ops', '🎯')">🎯 Bruteforce Ops</button>
            <button class="app-btn btn-attack" @click="launch('privesc', 'Privesc Scan', '⬆️')">⬆️ Privesc Scan</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  isOpen: boolean
  holoMode: boolean
  audioEnabled: boolean
  currentUsername: string
  userRole: string
}>()

const emit = defineEmits(['launch-app', 'toggle-holo', 'toggle-audio', 'open-settings', 'logout', 'close', 'show-desktop'])

const launch = (component: string, title: string, icon: string) => {
  emit('launch-app', { id: `app_${component}`, component, title, icon, width: 900, height: 600 })
  emit('close')
}
</script>

<style scoped>
.start-menu {
  position: absolute;
  bottom: 54px; /* Taskbar height + margin */
  left: 10px;
  width: 700px;
  height: 500px;
  display: flex;
  background: rgba(12, 18, 32, 0.9);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 12px;
  box-shadow: 0 15px 50px rgba(0, 0, 0, 0.7);
  z-index: 1100;
  overflow: hidden;
}

.start-menu-left {
  width: 200px;
  background: rgba(0, 0, 0, 0.4);
  border-right: 1px solid rgba(0, 229, 255, 0.1);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 20px;
}

.fast-actions {
  display: flex;
  gap: 12px;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: white;
}
.btn-icon:hover {
  background: rgba(0, 229, 255, 0.2);
  border-color: var(--cyan);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.avatar {
  font-size: 24px;
  background: rgba(0, 229, 255, 0.1);
  border-radius: 50%;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 229, 255, 0.3);
}
.user-id {
  font-family: var(--font-co);
  font-size: 14px;
  color: white;
}
.user-role {
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--cyan);
  background: rgba(0, 229, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  margin-top: 4px;
}
.user-role.admin {
  color: var(--pink);
  background: rgba(255, 45, 110, 0.15);
}

.btn-logout {
  width: 100%;
  background: rgba(255, 45, 110, 0.1);
  border: 1px solid rgba(255, 45, 110, 0.3);
  color: var(--pink);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 1px;
  padding: 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-logout:hover {
  background: var(--pink);
  color: white;
}

.start-menu-right {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.app-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.app-category h3 {
  font-family: var(--font-hd);
  font-size: 10px;
  color: var(--text);
  letter-spacing: 2px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 6px;
  margin-bottom: 12px;
}

.app-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.app-btn {
  background: transparent;
  border: none;
  color: var(--textwh);
  font-family: var(--font-co);
  font-size: 13px;
  text-align: left;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.app-btn:hover {
  background: rgba(0, 229, 255, 0.15);
  color: white;
}
.btn-attack:hover {
  background: rgba(255, 45, 110, 0.15);
}
</style>
