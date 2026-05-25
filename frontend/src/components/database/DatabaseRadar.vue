<template>
  <div class="db-radar-workspace" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-family: var(--font-ui); margin-top: 10px; margin-bottom: 20px;">
    <!-- Left Column: Sonar HUD & Scan Settings -->
    <div class="cyber-card" style="display: flex; flex-direction: column;">
      <div class="card-title-bar">📡 DATABASE SONAR CONTROLS</div>
      
      <div class="specialized-form" style="padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 16px; min-height: 480px;">
        <!-- Sonar Visual Animation -->
        <div class="radar-sonar-container">
          <div class="sonar-screen" :class="{ 'scanning': scanning }">
            <div class="sonar-crosshair-h"></div>
            <div class="sonar-crosshair-v"></div>
            <div class="sonar-sweep-line"></div>
            <div class="sonar-wave"></div>
            
            <!-- Blips dynamically rendered based on found databases -->
            <div v-for="(db, idx) in foundDatabases" :key="idx" class="sonar-blip" :style="getBlipStyle(idx)"></div>
          </div>
        </div>
        
        <div class="form-row">
          <label style="flex: 1;">Target Host / Subnet Range
            <input v-model="radarHost" placeholder="f.eks. 127.0.0.1 eller localhost" style="width: 100%;" />
          </label>
        </div>

        <div class="form-row">
          <label style="flex: 1;">Database Radar Prober Type
            <select v-model="radarScanType" style="width: 100%;">
              <option value="all">Fuld Søgning (Netværk + SQLite Filer)</option>
              <option value="network">Kun Netværk (MySQL, Postgres, MSSQL, Redis, etc.)</option>
              <option value="sqlite">Kun SQLite Filfinder (Lokale folders)</option>
            </select>
          </label>
        </div>

        <button 
          class="btn-action btn-connect" 
          :disabled="scanning" 
          @click="runRadarScan(nodeId)"
          style="width: 100%; margin-top: auto; padding: 10px;"
        >
          {{ scanning ? '📡 SCANNER AKTIVT...' : '📡 SYNKRONISÉR RADAR' }}
        </button>
      </div>
    </div>

    <!-- Right Column: Sonar Output Viewport & Active Bindings -->
    <div class="cyber-card" style="display: flex; flex-direction: column;">
      <div class="card-title-bar">📟 SONAR TERMINAL FEED & RESULTS</div>
      
      <div class="radar-right-workspace" style="padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 16px;">
        <!-- CRT Phosphor Output feed -->
        <div class="crt-terminal-container" style="flex: 1; min-height: 220px; background: radial-gradient(circle, #081208 0%, #020502 100%); border: 1px solid var(--green); border-radius: 4px; padding: 12px; font-family: var(--font-co); font-size: 11px; color: var(--green); position: relative; overflow-y: auto; box-shadow: inset 0 0 20px rgba(0,255,157,0.15); max-height: 260px;">
          <!-- scanlines overlay -->
          <div style="position: absolute; top:0; left:0; width:100%; height:100%; background: linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.15) 50%), linear-gradient(90deg, rgba(255,0,0,0.03), rgba(0,255,0,0.01), rgba(0,0,255,0.03)); background-size: 100% 3px, 6px 100%; pointer-events: none;"></div>
          
          <div v-for="(log, idx) in radarLogs" :key="idx" class="crt-log-line" style="margin-bottom: 4px; line-height: 1.4;">
            {{ log }}
          </div>
          <div v-if="scanning" class="blinking-cursor" style="display: inline-block; width: 6px; height: 12px; background: var(--green); margin-left: 2px;"></div>
          
          <div v-if="radarLogs.length === 0" style="color: rgba(0, 255, 157, 0.4); text-align: center; margin-top: 80px;">
            [RADAR SYSTEM INAKTIVT]<br>Tryk på SYNKRONISÉR RADAR for at scanne noden.
          </div>
        </div>

        <!-- Found Databases list -->
        <div class="found-databases-container" style="display: flex; flex-direction: column; gap: 8px;">
          <div style="font-family: var(--font-co); font-size: 10px; color: var(--cyan); text-transform: uppercase; letter-spacing: 0.5px;">
            🎯 Fundne databaser på fjern-node:
          </div>
          
          <div v-if="foundDatabases.length === 0" style="font-size: 11px; color: rgba(255, 255, 255, 0.4); padding: 8px; border: 1px dashed rgba(255, 255, 255, 0.1); border-radius: 4px; text-align: center;">
            Ingen aktive databaser identificeret endnu.
          </div>

          <div 
            v-for="(db, idx) in foundDatabases" 
            :key="idx" 
            class="db-found-card"
            :style="isDbSupported(db.type) 
              ? 'display: flex; align-items: center; justify-content: space-between; background: rgba(8, 16, 32, 0.7); border: 1px solid rgba(0, 255, 157, 0.2); border-radius: 4px; padding: 10px 12px; font-family: var(--font-co); box-shadow: 0 0 10px rgba(0, 255, 157, 0.05);' 
              : 'display: flex; align-items: center; justify-content: space-between; background: rgba(8, 16, 32, 0.7); border: 1px solid rgba(255, 45, 110, 0.15); border-radius: 4px; padding: 10px 12px; font-family: var(--font-co); box-shadow: 0 0 10px rgba(255, 45, 110, 0.03);'"
          >
            <div style="display: flex; flex-direction: column; gap: 2px; overflow: hidden; margin-right: 12px;">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span 
                  style="font-size: 8px; padding: 1px 4px; border-radius: 3px; font-weight: 700; text-transform: uppercase;"
                  :style="isDbSupported(db.type) 
                    ? 'background: rgba(0, 255, 157, 0.15); color: var(--green); border: 1px solid var(--green);' 
                    : 'background: rgba(255, 45, 110, 0.1); color: var(--pink); border: 1px solid var(--pink);'"
                >
                  {{ db.type }}
                </span>
                <span style="font-size: 11px; color: #fff; font-weight: 600;">
                  {{ db.type === 'sqlite' ? getFileName(db.path) : `${db.host}:${db.port}` }}
                </span>
              </div>
              <span style="font-size: 9px; color: rgba(255, 255, 255, 0.5); overflow: hidden; text-overflow: ellipsis; max-width: 280px; white-space: nowrap;" :title="db.path">
                {{ db.type === 'sqlite' ? db.path : 'Aktiv database-port fundet' }}
              </span>
            </div>

            <button 
              v-if="isDbSupported(db.type)"
              class="btn-action-sm btn-connect" 
              @click="bindFoundDb(db)"
              style="height: 24px; font-size: 8.5px; padding: 0 10px; font-family: var(--font-co); background: linear-gradient(135deg, rgba(0, 255, 157, 0.25), rgba(0, 255, 157, 0.08)); border: 1px solid var(--green); color: var(--green); text-shadow: 0 0 5px var(--green);"
            >
              🔌 TILSLUT
            </button>
            <span 
              v-else
              style="font-size: 8.5px; padding: 4px 8px; border: 1px dashed rgba(255, 45, 110, 0.4); color: var(--pink); border-radius: 3px; font-family: var(--font-co); text-shadow: 0 0 5px rgba(255, 45, 110, 0.3); font-weight: 600; text-transform: uppercase; white-space: nowrap;"
            >
              ⚠️ KONSOL UNDERSTØTTES IKKE
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDatabaseRadar } from '@/composables/useDatabaseRadar'
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'

const props = defineProps<{ nodeId: string }>()

const {
  activeSubTab,
  radarHost,
  radarScanType,
  scanning,
  radarLogs,
  foundDatabases,
  runRadarScan
} = useDatabaseRadar()

const {
  dbConfig,
  testConnection,
  isDbSupported
} = useDatabaseConfig()

function bindFoundDb(db: any) {
  if (!isDbSupported(db.type)) return
  if (db.type === 'sqlite') {
    dbConfig.value.type = 'sqlite'
    dbConfig.value.sqlitePath = db.path || ''
  } else {
    dbConfig.value.type = db.type
    dbConfig.value.host = db.host || '127.0.0.1'
    dbConfig.value.port = db.port || (db.type === 'mssql' ? 1433 : db.type === 'postgresql' ? 5432 : db.type === 'redis' ? 6379 : db.type === 'mongodb' ? 27017 : db.type === 'influxdb' ? 8086 : 3306)
    dbConfig.value.user = db.type === 'mssql' ? 'sa' : db.type === 'postgresql' ? 'postgres' : db.type === 'redis' ? 'default' : db.type === 'mongodb' ? 'admin' : db.type === 'influxdb' ? 'admin' : 'root'
    dbConfig.value.database = ''
  }
  
  activeSubTab.value = 'explorer'
  testConnection(props.nodeId)
}

function getFileName(path?: string): string {
  if (!path) return 'sqlite.db'
  return path.substring(path.lastIndexOf('/') + 1)
}

function getBlipStyle(idx: number) {
  const coordinates = [
    { top: '35%', left: '25%' },
    { top: '65%', left: '75%' },
    { top: '20%', left: '60%' },
    { top: '80%', left: '40%' },
    { top: '45%', left: '80%' },
    { top: '75%', left: '20%' },
    { top: '30%', left: '50%' }
  ]
  const coord = coordinates[idx % coordinates.length]
  return {
    top: coord.top,
    left: coord.left,
    animationDelay: `${idx * 0.4}s`
  }
}
</script>

<style scoped>
.radar-sonar-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(4, 7, 13, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.15);
  border-radius: 4px;
  padding: 24px;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.8);
}

.sonar-screen {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 255, 157, 0.05) 0%, rgba(0, 10, 5, 0.6) 80%, rgba(0, 0, 0, 0.95) 100%);
  border: 2px solid var(--green);
  position: relative;
  overflow: hidden;
  box-shadow: 0 0 15px rgba(0, 255, 157, 0.2);
}

.sonar-screen::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 50%;
  background: 
    repeating-radial-gradient(circle, transparent, transparent 18px, rgba(0, 255, 157, 0.06) 19px, rgba(0, 255, 157, 0.06) 20px),
    linear-gradient(rgba(0, 255, 157, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 255, 157, 0.02) 1px, transparent 1px);
  background-size: 100% 100%, 20px 20px, 20px 20px;
  pointer-events: none;
}

.sonar-crosshair-h {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(0, 255, 157, 0.25);
  pointer-events: none;
}

.sonar-crosshair-v {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(0, 255, 157, 0.25);
  pointer-events: none;
}

.sonar-sweep-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: conic-gradient(from 0deg at 50% 50%, rgba(0, 255, 157, 0.2) 0deg, rgba(0, 255, 157, 0.08) 60deg, transparent 240deg);
  border-radius: 50%;
  pointer-events: none;
  transform: rotate(0deg);
}

.sonar-screen.scanning .sonar-sweep-line {
  animation: sonar-sweep 3.5s linear infinite;
}

.sonar-blip {
  position: absolute;
  width: 6px;
  height: 6px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 10px #fff, 0 0 20px var(--green);
  opacity: 0;
  transform: translate(-50%, -50%);
}

.scanning .sonar-blip {
  animation: sonar-fade 3.5s ease-out infinite;
}

@keyframes sonar-sweep {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes sonar-fade {
  0% {
    opacity: 0;
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.4);
  }
  100% {
    opacity: 0.15;
    transform: translate(-50%, -50%) scale(0.9);
  }
}

.blinking-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  from, to { background: transparent }
  50% { background: var(--green) }
}

/* Premium Cyber Form & Button Styles inherited in sub-component */
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

/* Pulsing Sonar Wave & Drifting CRT Scanline styling */
.sonar-wave {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 200px;
  height: 200px;
  border: 1.5px solid rgba(0, 255, 157, 0.25);
  border-radius: 50%;
  transform: translate(-50%, -50%) scale(0.1);
  opacity: 0;
  pointer-events: none;
}

.scanning .sonar-wave {
  animation: sonar-expand 3.5s linear infinite;
}

@keyframes sonar-expand {
  0% { transform: translate(-50%, -50%) scale(0.1); opacity: 0.8; }
  100% { transform: translate(-50%, -50%) scale(1.1); opacity: 0; }
}

.crt-terminal-container {
  position: relative;
  overflow: hidden;
}

.crt-terminal-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 80px;
  background: linear-gradient(to bottom, transparent, rgba(0, 255, 157, 0.04) 50%, rgba(0, 255, 157, 0.08) 95%, transparent);
  animation: crt-scanline 8s linear infinite;
  pointer-events: none;
  z-index: 5;
}

@keyframes crt-scanline {
  0% { transform: translateY(-100px); }
  100% { transform: translateY(260px); }
}
</style>
