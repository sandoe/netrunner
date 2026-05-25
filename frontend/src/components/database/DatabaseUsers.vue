<template>
  <div class="db-users-workspace" style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; font-family: var(--font-ui); margin-top: 10px; margin-bottom: 20px;">
    <!-- Left Column: Existing Users Directory -->
    <div class="cyber-card" style="display: flex; flex-direction: column;">
      <div class="card-title-bar">
        <span>🔐 BRUGERKONTI & PRIVILEGIER ({{ userList.length }})</span>
        <button class="btn-action-sm btn-insert" style="font-size: 8px; height: 22px; padding: 0 8px;" :disabled="loading || !connected" @click="loadUsers">🔄 OPDATER</button>
      </div>

      <div class="users-content-area" style="padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 16px;">
        <div v-if="!connected" class="empty-warning" style="text-align: center; padding: 40px; border: 1px dashed var(--pink); border-radius: 4px; background: rgba(255,45,110,0.03); color: var(--pink); font-family: var(--font-co); font-size: 11px;">
          ⚠️ KONSOL DISCONNECTED<br>Forbind til en database i EXPLORER fanen for at administrere brugere.
        </div>
        
        <div v-else-if="dbConfig.type === 'sqlite'" class="empty-warning" style="text-align: center; padding: 40px; border: 1px dashed var(--cyan); border-radius: 4px; background: rgba(0,229,255,0.03); color: var(--cyan); font-family: var(--font-co); font-size: 11px;">
          ℹ️ SQLITE ENGINE INFO<br>SQLite er en filbaseret database og understøtter ikke brugerkonti.
        </div>

        <div v-else-if="loading" class="terminal-loader" style="margin: 40px auto;">
          <div class="spinner"></div>
          <div class="loading-text" style="font-family: var(--font-co); font-size: 10px; color: var(--cyan);">HENTER BRUGERLISTE...</div>
        </div>

        <div v-else class="users-tree-list" style="display: flex; flex-direction: column; gap: 8px; overflow-y: auto; max-height: 480px;">
          <div v-if="userList.length === 0" style="text-align: center; font-size: 11px; color: rgba(255,255,255,0.4); padding: 16px; border: 1px dashed rgba(255,255,255,0.1); border-radius: 4px;">
            Ingen brugere indlæst. Klik på OPDATER ovenfor for at scanne.
          </div>

          <div 
            v-for="(u, idx) in userList" 
            :key="idx" 
            class="user-card-item"
            style="display: flex; align-items: center; justify-content: space-between; background: rgba(8, 16, 32, 0.7); border: 1px solid rgba(0, 229, 255, 0.15); border-radius: 4px; padding: 10px 14px; font-family: var(--font-co); transition: all 0.25s;"
          >
            <div style="display: flex; align-items: center; gap: 10px;">
              <span class="user-avatar" style="font-size: 14px;">👤</span>
              <div style="display: flex; flex-direction: column; gap: 2px;">
                <span style="font-size: 12px; color: #fff; font-weight: 600;">{{ u.username }}</span>
                <span style="font-size: 9px; color: rgba(255,255,255,0.4);">Host/Scope: {{ u.host || 'Default' }}</span>
              </div>
            </div>

            <div style="display: flex; align-items: center; gap: 10px;">
              <!-- Admin tag badge -->
              <span 
                v-if="u.isAdmin"
                style="font-size: 8px; padding: 1px 5px; background: rgba(0, 255, 157, 0.15); color: var(--green); border: 1px solid var(--green); border-radius: 3px; font-weight: 700; text-transform: uppercase;"
              >
                ADMIN / DBA
              </span>
              <span 
                v-else
                style="font-size: 8px; padding: 1px 5px; background: rgba(255, 255, 255, 0.05); color: rgba(255,255,255,0.5); border: 1px solid rgba(255,255,255,0.1); border-radius: 3px; font-weight: 700; text-transform: uppercase;"
              >
                STANDARD USER
              </span>

              <button 
                class="btn-icon-action btn-delete-row" 
                title="Slet bruger" 
                :disabled="loading"
                @click="deleteUserConfirm(u.username, u.host)"
                style="width: 22px; height: 22px; border-radius: 4px; background: rgba(255, 45, 110, 0.1); border: 1px solid rgba(255, 45, 110, 0.3); color: var(--pink); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 9px;"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Column: Create User Workspace -->
    <div class="cyber-card" style="display: flex; flex-direction: column;">
      <div class="card-title-bar">🔑 OPRET NY DATABASE BRUGER</div>
      
      <div class="specialized-form" style="padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 16px; min-height: 480px;">
        <div v-if="dbConfig.type === 'sqlite'" class="empty-warning" style="text-align: center; padding: 40px; border: 1px dashed var(--cyan); border-radius: 4px; background: rgba(0,229,255,0.03); color: var(--cyan); font-family: var(--font-co); font-size: 11px;">
          Brugeroprettelse er deaktiveret for SQLite.
        </div>
        
        <template v-else>
          <div class="form-row">
            <label style="flex: 1;">Brugernavn <span class="font-gray">*</span>
              <input v-model="newUser.username" placeholder="f.eks. db_bruger" style="width: 100%;" />
            </label>
          </div>

          <div class="form-row">
            <label style="flex: 1;">Adgangskode <span class="font-gray">*</span>
              <input v-model="newUser.password" type="password" placeholder="••••••••" style="width: 100%;" />
            </label>
          </div>

          <!-- Server specific tags/scopes -->
          <div class="form-row">
            <label v-if="dbConfig.type === 'mysql'" style="flex: 1;">Host Scope
              <input v-model="newUser.mysqlHost" placeholder="f.eks. % eller localhost" style="width: 100%;" />
            </label>
          </div>

          <div class="form-row" style="margin-top: 4px;">
            <label style="flex-direction: row; align-items: center; gap: 10px; cursor: pointer;">
              <input type="checkbox" v-model="newUser.isAdmin" style="width: auto; margin: 0;" />
              <span>Tildel fulde administrator/DBA privilegier</span>
            </label>
          </div>

          <!-- Generated SQL/Line Protocol preview -->
          <div style="margin-top: 10px;">
            <div style="font-family: var(--font-hd); font-size: 8.5px; color: var(--textbr); text-transform: uppercase; margin-bottom: 6px;">GENERERET KOMMANDO PREVIEW:</div>
            <pre class="sql-preview-box mono" style="margin: 0; padding: 10px; background: #020408; border: 1px dashed var(--cyan); color: var(--cyan); text-shadow: 0 0 4px rgba(0, 229, 255, 0.3); font-size: 10px; min-height: 48px; max-height: 80px; overflow-y: auto;"><code>{{ generatedUserQuery }}</code></pre>
          </div>

          <button 
            class="btn-action btn-connect" 
            :disabled="loading || !connected || !newUser.username || !newUser.password" 
            @click="submitCreateUser"
            style="width: 100%; margin-top: auto; padding: 10px;"
          >
            ⚡ OPRET BRUGER
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/api/client'
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'
import { parseCSV, parseTSV } from '@/composables/useDatabaseConfig'
import { useDatabaseQuery } from '@/composables/useDatabaseQuery'

const props = defineProps<{ nodeId: string }>()

const { 
  dbConfig, 
  connected, 
  loading, 
  showFlashMsg,
  buildDbCommand 
} = useDatabaseConfig()

const {
  pendingSql,
  showConfirmModal,
  onConfirmCallback
} = useDatabaseQuery()

const userList = ref<{ username: string; host: string; isAdmin: boolean }[]>([])

const newUser = ref({
  username: '',
  password: '',
  mysqlHost: '%',
  isAdmin: false
})

// Auto-generated command preview depending on database engine
const generatedUserQuery = computed(() => {
  const type = dbConfig.value.type
  const user = newUser.value.username.trim()
  const pass = newUser.value.password.trim()
  const host = newUser.value.mysqlHost.trim() || '%'
  const admin = newUser.value.isAdmin
  
  if (!user || !pass) return '-- Angiv brugernavn og password ovenfor'
  
  if (type === 'mysql') {
    if (admin) {
      return `CREATE USER '${user}'@'${host}' IDENTIFIED BY '${pass}';\nGRANT ALL PRIVILEGES ON *.* TO '${user}'@'${host}' WITH GRANT OPTION;`
    }
    return `CREATE USER '${user}'@'${host}' IDENTIFIED BY '${pass}';`
  } else if (type === 'postgresql') {
    if (admin) {
      return `CREATE USER "${user}" WITH PASSWORD '${pass}' SUPERUSER;`
    }
    return `CREATE USER "${user}" WITH PASSWORD '${pass}';`
  } else if (type === 'mssql') {
    return `CREATE LOGIN "${user}" WITH PASSWORD = '${pass}';`
  } else if (type === 'influxdb') {
    if (admin) {
      return `CREATE USER "${user}" WITH PASSWORD '${pass}' WITH ALL PRIVILEGES;`
    }
    return `CREATE USER "${user}" WITH PASSWORD '${pass}';`
  } else if (type === 'mongodb') {
    const roles = admin ? '["root"]' : '["readWrite", "dbAdmin"]'
    return `db.createUser({ user: "${user}", pwd: "${pass}", roles: ${roles} });`
  }
  return `-- Ingen brugerskema for denne database-type`
})

// Fetch existing user accounts from remote node database server
async function loadUsers() {
  if (!connected.value) return
  const type = dbConfig.value.type
  if (type === 'sqlite') {
    userList.value = []
    return
  }

  loading.value = true
  userList.value = []
  
  try {
    let sql = ''
    if (type === 'mysql') {
      sql = 'SELECT user, host FROM mysql.user;'
    } else if (type === 'postgresql') {
      // usename, usesuper
      sql = 'SELECT usename, usesuper FROM pg_catalog.pg_user;'
    } else if (type === 'mssql') {
      sql = "SELECT name, is_disabled FROM sys.server_principals WHERE type_desc = 'SQL_LOGIN';"
    } else if (type === 'influxdb') {
      sql = 'SHOW USERS;'
    } else if (type === 'mongodb') {
      sql = 'db.getUsers()'
    } else if (type === 'redis') {
      sql = 'ACL LIST'
    } else {
      loading.value = false
      return
    }

    const cmd = buildDbCommand(sql, false)
    const res = await api.executeNode(props.nodeId, [cmd])
    const out = res.results?.[0]?.output || ''
    const err = res.results?.[0]?.error || ''

    if (err || out.toLowerCase().includes('error')) {
      throw new Error(out || err || 'Kunne ikke hente brugere.')
    }

    if (type === 'mysql') {
      const parsed = parseTSV(out)
      userList.value = parsed.map(row => ({
        username: row[0],
        host: row[1],
        isAdmin: row[0] === 'root' || row[0] === 'debian-sys-maint'
      })).filter(u => u.username)
    } else if (type === 'postgresql') {
      const parsed = parseTSV(out)
      userList.value = parsed.map(row => ({
        username: row[0],
        host: 'localhost',
        isAdmin: row[1] === 't' || row[1] === '1'
      })).filter(u => u.username)
    } else if (type === 'mssql') {
      const parsed = parseTSV(out)
      userList.value = parsed.map(row => ({
        username: row[0],
        host: dbConfig.value.host,
        isAdmin: row[0] === 'sa'
      })).filter(u => u.username)
    } else if (type === 'influxdb') {
      const parsed = parseCSV(out)
      // Header: user,admin
      userList.value = parsed.slice(1).map(row => ({
        username: row[0] || '',
        host: dbConfig.value.host,
        isAdmin: row[1] === 'true'
      })).filter(u => u.username && u.username !== 'user' && u.username !== 'admin')
    } else if (type === 'mongodb') {
      // Simple parse mongo users string
      const usernames = [...out.matchAll(/"user"\s*:\s*"([^"]+)"/g)].map(m => m[1])
      userList.value = usernames.map(u => ({
        username: u,
        host: 'localhost',
        isAdmin: u === 'admin' || u === 'root'
      }))
    } else if (type === 'redis') {
      const parsed = out.split('\n').filter(l => l.trim())
      userList.value = parsed.map(line => {
        const match = line.match(/^user\s+([^\s]+)/)
        const name = match ? match[1] : 'default'
        return {
          username: name,
          host: 'localhost',
          isAdmin: line.includes('on') && line.includes('~*') && line.includes('+@all')
        }
      })
    }
  } catch (err: any) {
    showFlashMsg(`Kunne ikke indlæse brugere: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

// Open confirmation modal to drop/delete a database user
function deleteUserConfirm(username: string, host: string) {
  const type = dbConfig.value.type
  let deleteSql = ''
  
  if (type === 'mysql') {
    deleteSql = `DROP USER '${username}'@'${host}';`
  } else if (type === 'postgresql') {
    deleteSql = `DROP USER "${username}";`
  } else if (type === 'mssql') {
    deleteSql = `DROP LOGIN "${username}";`
  } else if (type === 'influxdb') {
    deleteSql = `DROP USER "${username}";`
  } else if (type === 'mongodb') {
    deleteSql = `db.dropUser("${username}");`
  } else if (type === 'redis') {
    deleteSql = `ACL DELUSER "${username}"`
  } else {
    return
  }

  pendingSql.value = deleteSql
  onConfirmCallback.value = async () => {
    loading.value = true
    try {
      const cmd = buildDbCommand(deleteSql, false)
      const res = await api.executeNode(props.nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      const err = res.results?.[0]?.error || ''
      
      if (err || out.toLowerCase().includes('error')) {
        throw new Error(out || err || 'Sletning mislykkedes.')
      }
      
      showFlashMsg(`Bruger '${username}' slettet succesfuldt!`)
      await loadUsers()
    } catch (err: any) {
      showFlashMsg(`Kunne ikke slette bruger: ${err.message || err}`, true)
    } finally {
      loading.value = false
    }
  }
  
  showConfirmModal.value = true
}

// Submit forms to create new users
async function submitCreateUser() {
  const user = newUser.value.username.trim()
  const pass = newUser.value.password.trim()
  
  if (!user || !pass) return
  
  const query = generatedUserQuery.value
  pendingSql.value = query
  
  onConfirmCallback.value = async () => {
    loading.value = true
    try {
      const cmd = buildDbCommand(query, false)
      const res = await api.executeNode(props.nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      const err = res.results?.[0]?.error || ''
      
      if (err || out.toLowerCase().includes('error')) {
        throw new Error(out || err || 'Oprettelse mislykkedes.')
      }
      
      showFlashMsg(`Bruger '${user}' oprettet succesfuldt!`)
      newUser.value.username = ''
      newUser.value.password = ''
      await loadUsers()
    } catch (err: any) {
      showFlashMsg(`Kunne ikke oprette bruger: ${err.message || err}`, true)
    } finally {
      loading.value = false
    }
  }
  
  showConfirmModal.value = true
}

// Watchers
watch(() => props.nodeId, () => {
  if (connected.value) {
    loadUsers()
  }
})

watch(() => connected.value, (newConn) => {
  if (newConn) {
    loadUsers()
  } else {
    userList.value = []
  }
})

onMounted(() => {
  if (connected.value) {
    loadUsers()
  }
})
</script>

<style scoped>
.db-users-workspace {
  box-sizing: border-box;
}

.empty-warning {
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

.user-card-item:hover {
  background: rgba(0, 229, 255, 0.05) !important;
  border-color: rgba(0, 229, 255, 0.3) !important;
  transform: translateX(4px);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.1);
}

.btn-delete-row:hover {
  background: rgba(255, 45, 110, 0.25) !important;
  border-color: var(--pink) !important;
  box-shadow: 0 0 8px rgba(255, 45, 110, 0.4);
}

/* Inherited premium styled forms */
.specialized-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  gap: 16px;
  width: 100%;
}

.form-row label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-family: var(--font-hd);
  font-size: 8.5px;
  letter-spacing: 1px;
  color: var(--textbr);
  text-transform: uppercase;
  flex: 1;
}

.form-row input, .form-row select {
  width: 100%;
  background: rgba(4, 7, 14, 0.6) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px;
  color: var(--textwh) !important;
  padding: 8px 12px;
  font-family: var(--font-co);
  font-size: 11px;
  outline: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.5);
}

.form-row input:focus, .form-row select:focus {
  border-color: var(--cyan) !important;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.5), 0 0 8px rgba(0, 229, 255, 0.25) !important;
  background: rgba(8, 16, 32, 0.8) !important;
}

.btn-action {
  font-family: var(--font-hd);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  text-transform: uppercase;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-connect {
  background: var(--green) !important;
  border: 1px solid var(--green) !important;
  color: #05080f !important;
  box-shadow: 0 0 8px rgba(0, 255, 157, 0.25);
  font-weight: 700;
}

.btn-connect:hover:not(:disabled) {
  background: #fff !important;
  color: #05080f !important;
  box-shadow: 0 0 18px var(--green);
}

.btn-connect:disabled {
  background: rgba(26, 37, 64, 0.3) !important;
  border-color: var(--border) !important;
  color: rgba(255,255,255,0.2) !important;
  box-shadow: none !important;
  cursor: not-allowed;
}

.btn-insert {
  border-color: rgba(0, 255, 157, 0.3);
  color: var(--green);
}

.btn-insert:hover {
  border-color: var(--green) !important;
  color: white !important;
  background: rgba(0, 255, 157, 0.15) !important;
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.3) !important;
}

.btn-action-sm {
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--border);
  color: var(--textbr);
  padding: 6px 12px;
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  text-transform: uppercase;
}

.btn-action-sm:hover:not(:disabled) {
  border-color: var(--cyan);
  color: #fff;
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.terminal-loader {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid rgba(0, 229, 255, 0.1);
  border-top-color: var(--cyan);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sql-preview-box {
  background: #020408 !important;
  border: 1px dashed var(--cyan) !important;
  color: var(--cyan) !important;
  text-shadow: 0 0 4px rgba(0, 229, 255, 0.3);
  padding: 14px;
  font-family: var(--font-co);
  font-size: 11.5px;
  line-height: 1.5;
  border-radius: 4px;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.9);
}
</style>
