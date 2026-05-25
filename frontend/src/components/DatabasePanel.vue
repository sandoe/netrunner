<template>
  <div class="db-panel-container" :class="{ 'fullscreen-mode': isFullscreen }">
    <!-- Cyber Header & RJ45 Details -->
    <div class="rj45-panel">
      <div class="rj45-panel-title">🗄️ DATABASE EXPLORER & SQL CONSOLE</div>
      
      <!-- Right-aligned controls and info summary -->
      <div style="display: flex; align-items: center; gap: 16px; margin-left: auto;">
        <!-- Connection Telemetry Summary -->
        <div class="rj45-info-summary" style="font-family: var(--font-co); font-size: 10px; color: var(--textbr); text-align: right; line-height: 1.35;">
          <div><span style="color: var(--cyan);">DB TYPE:</span> <span style="color: #fff;">{{ dbConfig.type.toUpperCase() }}</span></div>
          <div><span style="color: var(--cyan);">STATUS:</span> <span :style="{ color: connected ? 'var(--green)' : 'var(--pink)' }">{{ connected ? 'CONNECTED' : 'DISCONNECTED' }}</span></div>
        </div>

        <div class="rj45-ports-grid">
          <div class="rj45-port" :class="{ 'active': connected }" :title="`Database Type: ${dbConfig.type.toUpperCase()}\nStatus: ${connected ? 'Connected' : 'Disconnected'}`">
            <div class="rj45-led" :class="ledClass"></div>
            <div class="rj45-label">{{ dbConfig.type.toUpperCase() }}</div>
          </div>
        </div>

        <!-- Fullscreen Toggle -->
        <button class="btn-action-sm btn-fullscreen" style="height: 26px; font-size: 8.5px;" @click="toggleFullscreen">
          {{ isFullscreen ? '🖥️ MINIMER' : '🖥️ FULD SKÆRM' }}
        </button>
      </div>
    </div>

    <!-- Cyber Tab Bar -->
    <div class="cyber-tabs-bar" style="display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid rgba(0, 255, 157, 0.2); padding-bottom: 8px;">
      <button 
        class="tab-btn" 
        :class="{ 'active': activeSubTab === 'explorer' }" 
        @click="activeSubTab = 'explorer'"
        :style="activeSubTab === 'explorer' ? {
          background: 'rgba(0, 255, 157, 0.12)',
          border: '1px solid var(--green)',
          color: 'var(--green)',
          textShadow: '0 0 8px var(--green)',
          borderRadius: '3px',
          boxShadow: '0 0 10px rgba(0, 255, 157, 0.15)'
        } : {
          background: 'rgba(8, 16, 32, 0.4)',
          border: '1px solid rgba(0, 255, 157, 0.1)',
          color: 'rgba(255, 255, 255, 0.6)',
          borderRadius: '3px'
        }"
        style="font-family: var(--font-co); font-size: 10px; padding: 6px 14px; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.25s;"
      >
        🗃️ DATABASER (EXPLORER)
      </button>
      <button 
        class="tab-btn" 
        :class="{ 'active': activeSubTab === 'users' }" 
        @click="activeSubTab = 'users'"
        :style="activeSubTab === 'users' ? {
          background: 'rgba(0, 255, 157, 0.12)',
          border: '1px solid var(--green)',
          color: 'var(--green)',
          textShadow: '0 0 8px var(--green)',
          borderRadius: '3px',
          boxShadow: '0 0 10px rgba(0, 255, 157, 0.15)'
        } : {
          background: 'rgba(8, 16, 32, 0.4)',
          border: '1px solid rgba(0, 255, 157, 0.1)',
          color: 'rgba(255, 255, 255, 0.6)',
          borderRadius: '3px'
        }"
        style="font-family: var(--font-co); font-size: 10px; padding: 6px 14px; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.25s;"
      >
        🔐 BRUGERADMINISTRATION
      </button>
      <button 
        class="tab-btn" 
        :class="{ 'active': activeSubTab === 'radar' }" 
        @click="activeSubTab = 'radar'"
        :style="activeSubTab === 'radar' ? {
          background: 'rgba(0, 255, 157, 0.12)',
          border: '1px solid var(--green)',
          color: 'var(--green)',
          textShadow: '0 0 8px var(--green)',
          borderRadius: '3px',
          boxShadow: '0 0 10px rgba(0, 255, 157, 0.15)'
        } : {
          background: 'rgba(8, 16, 32, 0.4)',
          border: '1px solid rgba(0, 255, 157, 0.1)',
          color: 'rgba(255, 255, 255, 0.6)',
          borderRadius: '3px'
        }"
        style="font-family: var(--font-co); font-size: 10px; padding: 6px 14px; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.25s;"
      >
        📡 DATABASE RADAR
      </button>
      <button 
        class="tab-btn" 
        :class="{ 'active': activeSubTab === 'performance' }" 
        @click="activeSubTab = 'performance'"
        :style="activeSubTab === 'performance' ? {
          background: 'rgba(0, 255, 157, 0.12)',
          border: '1px solid var(--green)',
          color: 'var(--green)',
          textShadow: '0 0 8px var(--green)',
          borderRadius: '3px',
          boxShadow: '0 0 10px rgba(0, 255, 157, 0.15)'
        } : {
          background: 'rgba(8, 16, 32, 0.4)',
          border: '1px solid rgba(0, 255, 157, 0.1)',
          color: 'rgba(255, 255, 255, 0.6)',
          borderRadius: '3px'
        }"
        style="font-family: var(--font-co); font-size: 10px; padding: 6px 14px; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.25s;"
      >
        📈 YDEEVNE (PERFORMANCE)
      </button>
      <button 
        class="tab-btn" 
        :class="{ 'active': activeSubTab === 'audit' }" 
        @click="activeSubTab = 'audit'"
        :style="activeSubTab === 'audit' ? {
          background: 'rgba(0, 255, 157, 0.12)',
          border: '1px solid var(--green)',
          color: 'var(--green)',
          textShadow: '0 0 8px var(--green)',
          borderRadius: '3px',
          boxShadow: '0 0 10px rgba(0, 255, 157, 0.15)'
        } : {
          background: 'rgba(8, 16, 32, 0.4)',
          border: '1px solid rgba(0, 255, 157, 0.1)',
          color: 'rgba(255, 255, 255, 0.6)',
          borderRadius: '3px'
        }"
        style="font-family: var(--font-co); font-size: 10px; padding: 6px 14px; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.25s;"
      >
        🛡️ CYBER AUDIT
      </button>
    </div>

    <!-- Main Grid Dashboard -->
    <div v-show="activeSubTab === 'explorer'" class="db-dashboard-grid">
      <!-- Top/Left: Connection Settings & Schema Explorer -->
      <aside class="db-sidebar">
        <!-- Connection Card -->
        <div class="cyber-card">
          <div class="card-title-bar">🔑 NODECONNECTION CONFIG</div>
          
          <div class="specialized-form">
            <div class="form-row">
              <label>Database Type
                <select v-model="dbConfig.type" @change="onTypeChange(nodeId)">
                  <option value="sqlite">SQLite 3</option>
                  <option value="mysql">MySQL / MariaDB</option>
                  <option value="mssql">MS SQL Server (MSSQL)</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="redis">Redis Cache</option>
                  <option value="mongodb">MongoDB Document Store</option>
                  <option value="influxdb">InfluxDB Time Series</option>
                </select>
              </label>
            </div>

            <!-- SQLite Specific Inputs -->
            <template v-if="dbConfig.type === 'sqlite'">
              <div class="form-row">
                <label>Database Filsti (Node)
                  <input v-model="dbConfig.sqlitePath" placeholder="f.eks. data/netrunner.db" />
                </label>
              </div>
            </template>

            <!-- Server-based Inputs -->
            <template v-else>
              <div v-if="dbConfig.type === 'mssql'" class="form-row">
                <label>Godkendelsestype
                  <select v-model="dbConfig.mssqlAuthType">
                    <option value="sql">SQL Server Authentication</option>
                    <option value="windows">Windows Authentication (AD)</option>
                  </select>
                </label>
              </div>
              <div class="form-row">
                <label>Host <input v-model="dbConfig.host" placeholder="127.0.0.1" /></label>
                <label>Port 
                  <input 
                    v-model="dbConfig.port" 
                    type="number" 
                    :placeholder="dbConfig.type === 'mssql' ? '1433' : dbConfig.type === 'postgresql' ? '5432' : dbConfig.type === 'redis' ? '6379' : dbConfig.type === 'mongodb' ? '27017' : dbConfig.type === 'influxdb' ? '8086' : '3306'" 
                  />
                </label>
              </div>
              <div class="form-row" v-if="!(dbConfig.type === 'mssql' && dbConfig.mssqlAuthType === 'windows')">
                <label>Bruger 
                  <input 
                    v-model="dbConfig.user" 
                    :placeholder="dbConfig.type === 'mssql' ? 'sa' : dbConfig.type === 'postgresql' ? 'postgres' : dbConfig.type === 'redis' ? 'default' : dbConfig.type === 'mongodb' ? 'admin' : dbConfig.type === 'influxdb' ? 'admin' : 'root'" 
                  />
                </label>
                <label>Adgangskode <input v-model="dbConfig.password" type="password" placeholder="••••••••" /></label>
              </div>
              <div class="form-row">
                <label>Database/Index Navn 
                  <div style="display: flex; gap: 8px; width: 100%;">
                    <template v-if="availableDatabases.length > 0 && !isManualDbInput">
                      <select v-model="dbConfig.database" style="flex: 1;" @change="handleDbChange">
                        <option value="">-- Vælg database --</option>
                        <option v-for="db in availableDatabases" :key="db" :value="db">{{ db }}</option>
                      </select>
                      <button 
                        type="button"
                        class="btn-action-sm btn-structure" 
                        style="height: 31px; padding: 0 8px; font-size: 8px; display: flex; align-items: center;"
                        @click="isManualDbInput = true"
                        title="Skriv manuelt"
                      >
                        ✍️ MANUEL
                      </button>
                    </template>
                    <template v-else>
                      <input 
                        v-model="dbConfig.database" 
                        :placeholder="dbConfig.type === 'mssql' ? 'f.eks. master' : dbConfig.type === 'postgresql' ? 'f.eks. postgres' : dbConfig.type === 'influxdb' ? 'f.eks. telegraf' : 'f.eks. netrunner'" 
                        style="flex: 1;"
                        @change="handleDbChange"
                      />
                      <button 
                        v-if="availableDatabases.length > 0"
                        type="button"
                        class="btn-action-sm btn-structure" 
                        style="height: 31px; padding: 0 8px; font-size: 8px; display: flex; align-items: center;"
                        @click="isManualDbInput = false"
                        title="Vælg fra liste"
                      >
                        📋 LISTE
                      </button>
                    </template>
                    <button 
                      v-if="['mysql', 'postgresql', 'mssql', 'mongodb', 'influxdb'].includes(dbConfig.type)"
                      type="button"
                      class="btn-action-sm btn-structure" 
                      style="height: 31px; padding: 0 10px; font-size: 8.5px; display: flex; align-items: center; white-space: nowrap;"
                      :disabled="loading"
                      @click="fetchDatabases(nodeId)"
                    >
                      🔍 HENT
                    </button>
                  </div>
                </label>
              </div>
            </template>

            <div class="form-row action-row" style="display: flex; gap: 8px;">
              <button class="btn-action btn-connect" :disabled="loading" @click="testConnection(nodeId)" style="flex: 1;">
                {{ loading ? '⏳ FORBINDER...' : '⚡ TILSLUT & OPDATER' }}
              </button>
              <button v-if="connected" type="button" class="btn-action btn-disconnect-db" @click="disconnect" style="flex: 1; background: rgba(255, 45, 110, 0.1); border: 1px solid var(--pink); color: var(--pink); text-shadow: 0 0 6px rgba(255, 45, 110, 0.4); box-shadow: 0 0 10px rgba(255, 45, 110, 0.1);">
                ❌ DISCONNECT
              </button>
            </div>
          </div>
        </div>

        <!-- Table / Schema Explorer Component -->
        <DatabaseExplorer :nodeId="nodeId" />
      </aside>

      <!-- Main Column: SQL Editor & Data Grid -->
      <section class="db-main-col">
        <!-- Error box -->
        <div v-if="error" class="error-box" style="align-items: flex-start;">
          <span class="error-icon" style="margin-top: 2px;">⚠️</span>
          <div class="error-msg-container" style="flex: 1; display: flex; flex-direction: column; gap: 8px;">
            <div class="error-msg">{{ error }}</div>
            
            <div v-if="error.toLowerCase().includes('sqlite3') && (error.toLowerCase().includes('not found') || error.toLowerCase().includes('ikke fundet') || error.toLowerCase().includes('no such file') || error.toLowerCase().includes('not recognized'))" class="sqlite-install-offer" style="margin-top: 4px; padding-top: 8px; border-top: 1px dashed rgba(255, 45, 110, 0.3);">
              <p class="install-tip" style="font-size: 11px; color: #ffb3c6; margin: 0 0 8px 0; font-family: var(--font-co); line-height: 1.4;">
                [DIAGNOSTIK] SQLite3 CLI-klienten er ikke installeret på denne Linux-node. Netrunner kan forsøge at installere den automatisk for dig via nodens pakkehåndtering.
              </p>
              <button 
                class="btn-action btn-install-sqlite" 
                :disabled="loading" 
                @click="installSqlite(nodeId)"
                style="background: linear-gradient(135deg, rgba(255, 45, 110, 0.4), rgba(255, 45, 110, 0.15)); border: 1px solid var(--pink); color: #fff; padding: 4px 10px; font-size: 10px; font-family: var(--font-co); border-radius: 3px; cursor: pointer; text-shadow: 0 0 5px rgba(255, 45, 110, 0.6); box-shadow: 0 0 8px rgba(255, 45, 110, 0.2); width: fit-content;"
              >
                ⚡ INSTALLÉR SQLITE3 PÅ NODE (SUDO)
              </button>
            </div>

            <div v-if="(error.toLowerCase().includes('mysql') || error.toLowerCase().includes('mariadb')) && (error.toLowerCase().includes('not found') || error.toLowerCase().includes('ikke fundet') || error.toLowerCase().includes('no such file') || error.toLowerCase().includes('not recognized'))" class="mysql-install-offer" style="margin-top: 4px; padding-top: 8px; border-top: 1px dashed rgba(255, 45, 110, 0.3);">
              <p class="install-tip" style="font-size: 11px; color: #ffb3c6; margin: 0 0 8px 0; font-family: var(--font-co); line-height: 1.4;">
                [DIAGNOSTIK] MySQL/MariaDB CLI-klienten er ikke installeret på denne Linux-node. Netrunner kan forsøge at installere den automatisk for dig via nodens pakkehåndtering.
              </p>
              <button 
                class="btn-action btn-install-mysql" 
                :disabled="loading" 
                @click="installMysqlClient(nodeId)"
                style="background: linear-gradient(135deg, rgba(255, 45, 110, 0.4), rgba(255, 45, 110, 0.15)); border: 1px solid var(--pink); color: #fff; padding: 4px 10px; font-size: 10px; font-family: var(--font-co); border-radius: 3px; cursor: pointer; text-shadow: 0 0 5px rgba(255, 45, 110, 0.6); box-shadow: 0 0 8px rgba(255, 45, 110, 0.2); width: fit-content;"
              >
                ⚡ INSTALLÉR MYSQL KLIENT PÅ NODE (SUDO)
              </button>
            </div>

            <div v-if="(error.toLowerCase().includes('sqlcmd') || error.toLowerCase().includes('sqsh')) && (error.toLowerCase().includes('not found') || error.toLowerCase().includes('ikke fundet') || error.toLowerCase().includes('no such file') || error.toLowerCase().includes('not recognized'))" class="mssql-install-offer" style="margin-top: 4px; padding-top: 8px; border-top: 1px dashed rgba(255, 45, 110, 0.3);">
              <p class="install-tip" style="font-size: 11px; color: #ffb3c6; margin: 0 0 8px 0; font-family: var(--font-co); line-height: 1.4;">
                [DIAGNOSTIK] MS SQL Server CLI-klienten (sqlcmd/sqsh) er ikke installeret på denne Linux-node. Netrunner kan forsøge at installere sqsh-klienten automatisk for dig via nodens pakkehåndtering.
              </p>
              <button 
                class="btn-action btn-install-mssql" 
                :disabled="loading" 
                @click="installMssqlClient(nodeId)"
                style="background: linear-gradient(135deg, rgba(255, 45, 110, 0.4), rgba(255, 45, 110, 0.15)); border: 1px solid var(--pink); color: #fff; padding: 4px 10px; font-size: 10px; font-family: var(--font-co); border-radius: 3px; cursor: pointer; text-shadow: 0 0 5px rgba(255, 45, 110, 0.6); box-shadow: 0 0 8px rgba(255, 45, 110, 0.2); width: fit-content;"
              >
                ⚡ INSTALLÉR MS SQL KLIENT (SUDO)
              </button>
            </div>

            <div v-if="error.toLowerCase().includes('psql') && (error.toLowerCase().includes('not found') || error.toLowerCase().includes('ikke fundet') || error.toLowerCase().includes('no such file') || error.toLowerCase().includes('not recognized'))" class="postgres-install-offer" style="margin-top: 4px; padding-top: 8px; border-top: 1px dashed rgba(255, 45, 110, 0.3);">
              <p class="install-tip" style="font-size: 11px; color: #ffb3c6; margin: 0 0 8px 0; font-family: var(--font-co); line-height: 1.4;">
                [DIAGNOSTIK] PostgreSQL CLI-klienten (psql) er ikke installeret på denne Linux-node. Netrunner kan forsøge at installere den automatisk for dig via nodens pakkehåndtering.
              </p>
              <button 
                class="btn-action btn-install-postgres" 
                :disabled="loading" 
                @click="installPostgresClient(nodeId)"
                style="background: linear-gradient(135deg, rgba(255, 45, 110, 0.4), rgba(255, 45, 110, 0.15)); border: 1px solid var(--pink); color: #fff; padding: 4px 10px; font-size: 10px; font-family: var(--font-co); border-radius: 3px; cursor: pointer; text-shadow: 0 0 5px rgba(255, 45, 110, 0.6); box-shadow: 0 0 8px rgba(255, 45, 110, 0.2); width: fit-content;"
              >
                ⚡ INSTALLÉR POSTGRESQL KLIENT (SUDO)
              </button>
            </div>

            <div v-if="error.toLowerCase().includes('redis-cli') && (error.toLowerCase().includes('not found') || error.toLowerCase().includes('ikke fundet') || error.toLowerCase().includes('no such file') || error.toLowerCase().includes('not recognized'))" class="redis-install-offer" style="margin-top: 4px; padding-top: 8px; border-top: 1px dashed rgba(255, 45, 110, 0.3);">
              <p class="install-tip" style="font-size: 11px; color: #ffb3c6; margin: 0 0 8px 0; font-family: var(--font-co); line-height: 1.4;">
                [DIAGNOSTIK] Redis-cli klientværktøjet er ikke installeret på denne Linux-node. Netrunner kan forsøge at installere redis-tools automatisk for dig via nodens pakkehåndtering.
              </p>
              <button 
                class="btn-action btn-install-redis" 
                :disabled="loading" 
                @click="installRedisTools(nodeId)"
                style="background: linear-gradient(135deg, rgba(255, 45, 110, 0.4), rgba(255, 45, 110, 0.15)); border: 1px solid var(--pink); color: #fff; padding: 4px 10px; font-size: 10px; font-family: var(--font-co); border-radius: 3px; cursor: pointer; text-shadow: 0 0 5px rgba(255, 45, 110, 0.6); box-shadow: 0 0 8px rgba(255, 45, 110, 0.2); width: fit-content;"
              >
                ⚡ INSTALLÉR REDIS KLIENT (SUDO)
              </button>
            </div>

            <div v-if="(error.toLowerCase().includes('mongosh') || error.toLowerCase().includes('mongo ')) && (error.toLowerCase().includes('not found') || error.toLowerCase().includes('ikke fundet') || error.toLowerCase().includes('no such file') || error.toLowerCase().includes('not recognized'))" class="mongo-install-offer" style="margin-top: 4px; padding-top: 8px; border-top: 1px dashed rgba(255, 45, 110, 0.3);">
              <p class="install-tip" style="font-size: 11px; color: #ffb3c6; margin: 0 0 8px 0; font-family: var(--font-co); line-height: 1.4;">
                [DIAGNOSTIK] MongoDB-shell klienten (mongosh/mongo) er ikke installeret på denne Linux-node. Netrunner kan forsøge at installere den automatisk for dig via nodens pakkehåndtering.
              </p>
              <button 
                class="btn-action btn-install-mongo" 
                :disabled="loading" 
                @click="installMongosh(nodeId)"
                style="background: linear-gradient(135deg, rgba(255, 45, 110, 0.4), rgba(255, 45, 110, 0.15)); border: 1px solid var(--pink); color: #fff; padding: 4px 10px; font-size: 10px; font-family: var(--font-co); border-radius: 3px; cursor: pointer; text-shadow: 0 0 5px rgba(255, 45, 110, 0.6); box-shadow: 0 0 8px rgba(255, 45, 110, 0.2); width: fit-content;"
              >
                ⚡ INSTALLÉR MONGODB KLIENT (SUDO)
              </button>
            </div>

            <div v-if="error.toLowerCase().includes('influx') && (error.toLowerCase().includes('not found') || error.toLowerCase().includes('ikke fundet') || error.toLowerCase().includes('no such file') || error.toLowerCase().includes('not recognized'))" class="influx-install-offer" style="margin-top: 4px; padding-top: 8px; border-top: 1px dashed rgba(255, 45, 110, 0.3);">
              <p class="install-tip" style="font-size: 11px; color: #ffb3c6; margin: 0 0 8px 0; font-family: var(--font-co); line-height: 1.4;">
                [DIAGNOSTIK] InfluxDB CLI-klienten (influx) er ikke installeret på denne Linux-node. Netrunner kan forsøge at installere den automatisk for dig via nodens pakkehåndtering.
              </p>
              <button 
                class="btn-action btn-install-influx" 
                :disabled="loading" 
                @click="installInfluxClient(nodeId)"
                style="background: linear-gradient(135deg, rgba(255, 45, 110, 0.4), rgba(255, 45, 110, 0.15)); border: 1px solid var(--pink); color: #fff; padding: 4px 10px; font-size: 10px; font-family: var(--font-co); border-radius: 3px; cursor: pointer; text-shadow: 0 0 5px rgba(255, 45, 110, 0.6); box-shadow: 0 0 8px rgba(255, 45, 110, 0.2); width: fit-content;"
              >
                ⚡ INSTALLÉR INFLUXDB KLIENT (SUDO)
              </button>
            </div>
          </div>
        </div>

        <!-- Success notification -->
        <div v-if="successMsg" class="success-box">
          <span class="success-icon">✓</span>
          <div class="success-msg">{{ successMsg }}</div>
        </div>

        <!-- SQL Console Component -->
        <DatabaseConsole :nodeId="nodeId" />

        <!-- Result / Grid Section -->
        <div class="cyber-card results-card">
          <div class="card-title-bar">
            <span>📊 QUERY RESULTATER {{ queryDuration ? `(${queryDuration}ms)` : '' }}</span>
            <span v-if="resultsRows.length && resultsHeaders[0] !== 'nosql'" class="result-count font-green">{{ resultsRows.length }} rækker returneret</span>
          </div>

          <div v-if="loading" class="terminal-loader">
            <div class="spinner"></div>
            <div class="loading-text">AFVIKLER QUERY PÅ NODEN...</div>
          </div>

          <div v-else-if="!resultsHeaders.length && hasRunQuery" class="welcome-box empty-data-box" style="border: 1px dashed var(--pink); background: rgba(255, 45, 110, 0.05); padding: 24px; text-align: center; border-radius: 4px; display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; min-height: 200px;">
            <div class="welcome-icon font-pink" style="font-size: 32px; margin-bottom: 12px; filter: drop-shadow(0 0 6px var(--pink)); color: var(--pink); text-shadow: 0 0 6px var(--pink);">⚠️</div>
            <div style="font-family: var(--font-co); font-size: 11px; font-weight: 600; color: var(--pink); text-shadow: 0 0 4px var(--pink); text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px;">INGEN DATA FUNDET</div>
            <p class="font-small font-gray" style="margin: 0; max-width: 320px; line-height: 1.5; font-size: 10.5px;">
              Forespørgslen blev afviklet succesfuldt, men der blev ikke returneret nogen datapunkter for denne tabel eller måling. Databasen er tom for dette datasæt.
            </p>
          </div>

          <div v-else-if="!resultsHeaders.length" class="welcome-box">
            <div class="welcome-icon font-cyan">🗄️</div>
            <p class="welcome-text font-gray">
              {{ welcomeText }}
            </p>
            <p class="welcome-tip font-small font-cyan">
              {{ welcomeTip }}
            </p>
          </div>

          <!-- Document Viewport for Redis/MongoDB -->
          <div v-else-if="resultsHeaders[0] === 'nosql'" style="flex: 1; display: flex; flex-direction: column;">
            <DatabaseNoSqlViewport />
          </div>

          <!-- Relational tabular grid -->
          <div v-else style="flex: 1; display: flex; flex-direction: column;">
            <DatabaseGrid :nodeId="nodeId" />
          </div>
        </div>
      </section>
    </div>

    <!-- Sub Views -->
    <DatabaseRadar v-show="activeSubTab === 'radar'" :nodeId="nodeId" />
    <DatabaseUsers v-show="activeSubTab === 'users'" :nodeId="nodeId" />
    <DatabasePerformance v-show="activeSubTab === 'performance'" :nodeId="nodeId" />
    <DatabaseAudit v-show="activeSubTab === 'audit'" :nodeId="nodeId" />

    <!-- SQL Preview & Confirmation Overlay Modal -->
    <div v-if="showConfirmModal" class="modal-overlay" @click.self="showConfirmModal = false">
      <div class="cyber-modal-card">
        <div class="cyber-modal-header warning">
          <div class="modal-title">⚠️ BEKRÆFT SQL AFVIKLING</div>
          <button class="btn-close-modal" @click="showConfirmModal = false">×</button>
        </div>
        <div class="cyber-modal-body">
          <p>Følgende genererede SQL vil blive afviklet på databasen:</p>
          <pre class="sql-preview-box font-orange mono"><code>{{ pendingSql }}</code></pre>
          <div class="warning-text-box">
            <span class="warning-icon">⚠️</span>
            <span>Handlingen kan ikke fortrydes. Hvis du foretager ændringer eller sletter en række, modificeres databasen på fjernnoden øjeblikkeligt.</span>
          </div>
        </div>
        <div class="cyber-modal-footer">
          <button class="btn-modal-cancel" @click="showConfirmModal = false">ANNULLER</button>
          <button class="btn-modal-confirm" @click="executePendingSql">BEKRÆFT SQL</button>
        </div>
      </div>
    </div>

    <!-- Add Row Modal -->
    <div v-if="showAddRowModal" class="modal-overlay" @click.self="showAddRowModal = false">
      <div class="cyber-modal-card add-row-card">
        <div class="cyber-modal-header">
          <div class="modal-title">➕ TILFØJ NY RÆKKE I: {{ activeTable }}</div>
          <button class="btn-close-modal" @click="showAddRowModal = false">×</button>
        </div>
        <div class="cyber-modal-body select-body scroll-y">
          <div class="add-row-grid">
            <div v-for="col in activeTableColumns" :key="col.name" class="add-row-field">
              <label class="font-bold">
                {{ col.name }} <span class="font-gray font-small">({{ col.type }})</span>
                <span v-if="col.pk" class="pk-badge">PK</span>
                <input 
                  v-model="newRowData[col.name]" 
                  :placeholder="col.defaultValue || 'Indtast værdi...'"
                  class="add-row-input"
                />
              </label>
            </div>
          </div>
        </div>
        <div class="cyber-modal-footer">
          <button class="btn-modal-cancel" @click="showAddRowModal = false">ANNULLER</button>
          <button class="btn-modal-confirm btn-apply" @click="submitAddRow(nodeId)">OPRET RÆKKE</button>
        </div>
      </div>
    </div>

    <!-- Add InfluxDB Datapoint Modal -->
    <div v-if="showAddInfluxPointModal" class="modal-overlay" @click.self="showAddInfluxPointModal = false">
      <div class="cyber-modal-card add-row-card" style="border-color: var(--cyan); box-shadow: 0 0 30px rgba(0, 229, 255, 0.25);">
        <div class="cyber-modal-header" style="background: rgba(0, 229, 255, 0.1); border-bottom: 1px solid rgba(0, 229, 255, 0.2);">
          <div class="modal-title font-cyan" style="text-shadow: 0 0 6px rgba(0, 229, 255, 0.4);">➕ TILFØJ NYT DATAPUNKT (INFLUXDB Line Protocol)</div>
          <button class="btn-close-modal" style="color: var(--cyan);" @click="showAddInfluxPointModal = false">×</button>
        </div>
        <div class="cyber-modal-body" style="display: flex; flex-direction: column; gap: 14px;">
          <p class="font-small font-gray" style="margin: 0;">Opret målinger og værdier direkte i din tidsserie-database ved hjælp af InfluxDB Line Protocol syntaks.</p>
          
          <div class="form-row" style="display: flex; gap: 16px;">
            <label style="flex: 1; display: flex; flex-direction: column; gap: 6px; font-family: var(--font-hd); font-size: 8.5px; color: var(--textbr); text-transform: uppercase;">
              Måling (Measurement) <span class="font-gray">*</span>
              <input 
                v-model="newInfluxPoint.measurement" 
                placeholder="f.eks. cpu, temperatur, forbrug"
                style="width: 100%; background: rgba(4, 7, 14, 0.6); border: 1px solid var(--border); border-radius: 4px; color: var(--textwh); padding: 8px 12px; font-family: var(--font-co); font-size: 11px; outline: none;"
              />
            </label>
          </div>

          <div class="form-row" style="display: flex; gap: 16px;">
            <label style="flex: 1; display: flex; flex-direction: column; gap: 6px; font-family: var(--font-hd); font-size: 8.5px; color: var(--textbr); text-transform: uppercase;">
              Tags (Dimensioner / Indekseret)
              <input 
                v-model="newInfluxPoint.tags" 
                placeholder="f.eks. host=server01,region=west,env=prod"
                style="width: 100%; background: rgba(4, 7, 14, 0.6); border: 1px solid var(--border); border-radius: 4px; color: var(--textwh); padding: 8px 12px; font-family: var(--font-co); font-size: 11px; outline: none;"
              />
            </label>
          </div>

          <div class="form-row" style="display: flex; gap: 16px;">
            <label style="flex: 1; display: flex; flex-direction: column; gap: 6px; font-family: var(--font-hd); font-size: 8.5px; color: var(--textbr); text-transform: uppercase;">
              Felter (Værdier / Numerisk & Tekst) <span class="font-gray">*</span>
              <input 
                v-model="newInfluxPoint.fields" 
                placeholder="f.eks. value=45.2,usage=0.67,status=&quot;aktiv&quot;"
                style="width: 100%; background: rgba(4, 7, 14, 0.6); border: 1px solid var(--border); border-radius: 4px; color: var(--textwh); padding: 8px 12px; font-family: var(--font-co); font-size: 11px; outline: none;"
              />
            </label>
          </div>

          <div class="form-row" style="display: flex; gap: 16px;">
            <label style="flex: 1; display: flex; flex-direction: column; gap: 6px; font-family: var(--font-hd); font-size: 8.5px; color: var(--textbr); text-transform: uppercase;">
              Valgfrit Tidsstempel (Nanosekunder epoch)
              <input 
                v-model="newInfluxPoint.timestamp" 
                placeholder="Efterlad tom for nuværende server-tid..."
                style="width: 100%; background: rgba(4, 7, 14, 0.6); border: 1px solid var(--border); border-radius: 4px; color: var(--textwh); padding: 8px 12px; font-family: var(--font-co); font-size: 11px; outline: none;"
              />
            </label>
          </div>
          
          <!-- Code Preview of Line Protocol -->
          <div style="margin-top: 6px;">
            <div style="font-family: var(--font-hd); font-size: 8.5px; color: var(--textbr); text-transform: uppercase; margin-bottom: 6px;">PREVIEW (LINE PROTOCOL SYNTAS):</div>
            <pre class="sql-preview-box mono" style="margin: 0; padding: 10px; background: #020408; border: 1px dashed var(--cyan); color: var(--cyan); text-shadow: 0 0 4px rgba(0, 229, 255, 0.3); font-size: 10px; min-height: 36px; max-height: 50px;"><code>INSERT {{ newInfluxPoint.measurement || 'measurement' }}{{ newInfluxPoint.tags ? ',' + newInfluxPoint.tags : '' }} {{ newInfluxPoint.fields || 'fields=value' }}{{ newInfluxPoint.timestamp ? ' ' + newInfluxPoint.timestamp : '' }}</code></pre>
          </div>
        </div>
        <div class="cyber-modal-footer">
          <button class="btn-modal-cancel" @click="showAddInfluxPointModal = false">ANNULLER</button>
          <button class="btn-modal-confirm btn-apply" style="background: var(--cyan); border-color: var(--cyan); color: #05080f; box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);" :disabled="!newInfluxPoint.measurement || !newInfluxPoint.fields" @click="submitAddInfluxPoint(nodeId)">SKRIV DATAPUNKT</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'

// Import Sub-Components
import DatabaseRadar from './database/DatabaseRadar.vue'
import DatabaseExplorer from './database/DatabaseExplorer.vue'
import DatabaseConsole from './database/DatabaseConsole.vue'
import DatabaseGrid from './database/DatabaseGrid.vue'
import DatabaseNoSqlViewport from './database/DatabaseNoSqlViewport.vue'
import DatabaseUsers from './database/DatabaseUsers.vue'
import DatabasePerformance from './database/DatabasePerformance.vue'
import DatabaseAudit from './database/DatabaseAudit.vue'

// Import Composables
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'
import { useDatabaseRadar } from '@/composables/useDatabaseRadar'
import { useDatabaseQuery } from '@/composables/useDatabaseQuery'

const props = defineProps<{ nodeId: string }>()

// Composables setup
const {
  dbConfig,
  connected,
  loading,
  error,
  successMsg,
  isRelational,
  isReadOnly,
  testConnection,
  onTypeChange,
  loadConfig,
  availableDatabases,
  hasRunQuery,
  disconnect,
  fetchDatabases,
  installSqlite,
  installMysqlClient,
  installMssqlClient,
  installPostgresClient,
  installRedisTools,
  installMongosh,
  installInfluxClient
} = useDatabaseConfig()

const isManualDbInput = ref(false)

const welcomeText = computed(() => {
  const type = dbConfig.value.type
  if (type === 'redis') {
    return 'Redis konsol klar. Vælg en nøgle (key) fra sidebaren for at hente dens værdi med det samme, eller afvikl en Redis-kommando (f.eks. GET, KEYS) i terminalen.'
  } else if (type === 'mongodb') {
    return 'MongoDB konsol klar. Vælg en samling (collection) fra sidebaren for at inspicere dokumenter, eller kør et MongoDB eval-script i terminalen.'
  } else if (type === 'influxdb') {
    return 'InfluxDB konsol klar. Forbind til din tidsserie-database, vælg en måling (measurement) fra sidebaren for at hente datapunkter automatisk, eller skriv en InfluxQL forespørgsel.'
  } else {
    return 'SQL Console klar. Forbind til en database, vælg en tabel fra sidebaren for at hente data automatisk, eller skriv en brugerdefineret SQL query ovenfor og klik på "Kør forespørgsel".'
  }
})

const welcomeTip = computed(() => {
  if (isReadOnly.value) {
    return 'Tidsserier og NoSQL-databaser er skrivebeskyttede (read-only) i denne konsol.'
  }
  return 'Dobbeltklik på en celle i tabellen for at redigere værdien inline!'
})

const { activeSubTab } = useDatabaseRadar()

const {
  queryDuration,
  resultsHeaders,
  resultsRows,
  activeTable,
  activeTableColumns,
  showConfirmModal,
  pendingSql,
  executePendingSql,
  showAddRowModal,
  newRowData,
  submitAddRow,
  runQuery,
  showAddInfluxPointModal,
  newInfluxPoint,
  submitAddInfluxPoint
} = useDatabaseQuery()

// Fullscreen mode states
const isFullscreen = ref(false)

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {})
    }
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(() => {})
    }
  }
}

function handleNativeFullscreenChange() {
  if (!document.fullscreenElement) {
    isFullscreen.value = false
  }
}

// LED Status class representation
const ledClass = computed(() => {
  if (error.value) return 'red pulsing'
  if (loading.value) return 'cyan pulsing'
  if (connected.value) return 'green'
  return 'gray'
})

// Keyboard shortcuts (Ctrl+Enter to run query)
function handleKeyDown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') {
    runQuery(props.nodeId)
  }
}

function handleDbChange() {
  saveConfig(props.nodeId)
  if (connected.value) {
    loadSchema(props.nodeId)
  }
}

// Watchers
watch(() => props.nodeId, (newId) => {
  loadConfig(newId)
}, { immediate: true })

// Mount/Unmount hooks
onMounted(() => {
  document.addEventListener('fullscreenchange', handleNativeFullscreenChange)
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleNativeFullscreenChange)
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.db-panel-container {
  padding: 20px;
  overflow-y: auto;
  height: 100%;
}

/* ═══════════════════════════════════════════════════════════════
   PREMIUM RJ45 HARDWARE CHASSIS HEADER
   ═══════════════════════════════════════════════════════════════ */
.rj45-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: radial-gradient(circle at 10% 20%, rgba(13, 25, 48, 0.85) 0%, rgba(5, 10, 20, 0.95) 100%);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 6px;
  padding: 10px 16px;
  margin-bottom: 20px;
  box-shadow: inset 0 0 25px rgba(0, 229, 255, 0.08), 0 8px 32px rgba(0,0,0,0.5);
  backdrop-filter: blur(12px);
  position: relative;
  overflow: hidden;
}

.rj45-panel::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--green), var(--cyan), transparent);
  animation: laser-sweep 5s linear infinite;
}

@keyframes laser-sweep {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.rj45-panel-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--cyan);
  font-family: var(--font-hd);
  letter-spacing: 2px;
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
}

.rj45-ports-grid {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rj45-port {
  position: relative;
  width: 80px;
  height: 52px;
  background: #040812;
  border: 2px solid var(--border2);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding-bottom: 4px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 10px rgba(0,0,0,0.6);
}

.rj45-port::before {
  content: '';
  position: absolute;
  top: 8px;
  width: 52px;
  height: 22px;
  background: #0c1220;
  border: 1px solid #1f2d4d;
  border-radius: 2px;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.9);
}

.rj45-port::after {
  content: '';
  position: absolute;
  top: 17px;
  width: 22px;
  height: 10px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 1px;
  z-index: 2;
}

.rj45-led {
  position: absolute;
  top: 4px;
  right: 6px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #1e293b;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.5);
  transition: all 0.3s ease;
}

.rj45-led.green {
  background: var(--green);
  box-shadow: 0 0 8px var(--green), 0 0 15px rgba(0, 255, 157, 0.6);
}

.rj45-led.cyan {
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan), 0 0 15px rgba(0, 229, 255, 0.6);
}

.rj45-led.red {
  background: var(--pink);
  box-shadow: 0 0 8px var(--pink), 0 0 15px rgba(255, 45, 110, 0.6);
}

.rj45-led.pulsing {
  animation: rj45-led-pulse 1s infinite alternate;
}

@keyframes rj45-led-pulse {
  0% { opacity: 0.4; }
  100% { opacity: 1; filter: brightness(1.2); }
}

.rj45-label {
  font-size: 8px;
  font-weight: 700;
  color: var(--textbr);
  font-family: var(--font-hd);
  letter-spacing: 0.5px;
  z-index: 3;
  margin-top: 10px;
}

.btn-fullscreen {
  border-color: rgba(0, 229, 255, 0.3);
  color: var(--cyan);
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--border);
  padding: 6px 14px;
  font-family: var(--font-hd);
  font-weight: 700;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-fullscreen:hover {
  border-color: var(--cyan) !important;
  color: white !important;
  background: rgba(0, 229, 255, 0.15) !important;
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.4) !important;
  transform: translateY(-1px);
}

/* ═══════════════════════════════════════════════════════════════
   DASHBOARD GRID & SIDEBAR
   ═══════════════════════════════════════════════════════════════ */
.db-dashboard-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  margin-top: 10px;
}

.db-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.db-main-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ═══════════════════════════════════════════════════════════════
   CYBER CARD STYLING & BRACKETS
   ═══════════════════════════════════════════════════════════════ */
.cyber-card {
  position: relative;
  background: radial-gradient(circle at 30% 30%, rgba(10, 20, 38, 0.8) 0%, rgba(3, 5, 10, 0.9) 100%) !important;
  background-image: 
    radial-gradient(circle at 30% 30%, rgba(10, 20, 38, 0.75) 0%, rgba(3, 5, 10, 0.9) 100%),
    linear-gradient(rgba(0, 229, 255, 0.015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 255, 0.015) 1px, transparent 1px) !important;
  background-size: 100% 100%, 24px 24px, 24px 24px !important;
  backdrop-filter: blur(16px) !important;
  border: 1px solid rgba(0, 229, 255, 0.2) !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.75), inset 0 0 20px rgba(0, 229, 255, 0.02) !important;
  border-radius: 6px;
  overflow: hidden;
  padding: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.cyber-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 10px;
  height: 10px;
  border-top: 2px solid var(--cyan);
  border-left: 2px solid var(--cyan);
  z-index: 5;
  pointer-events: none;
  transition: all 0.3s ease;
}

.cyber-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: 0;
  width: 10px;
  height: 10px;
  border-bottom: 2px solid var(--cyan);
  border-right: 2px solid var(--cyan);
  z-index: 5;
  pointer-events: none;
  transition: all 0.3s ease;
}

.cyber-card:hover {
  border-color: rgba(0, 229, 255, 0.35) !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 229, 255, 0.08) !important;
}

.cyber-card:hover::before, .cyber-card:hover::after {
  filter: brightness(1.3);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.6);
}

.card-title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-hd);
  font-size: 10.5px;
  font-weight: 700;
  color: var(--cyan) !important;
  letter-spacing: 1.5px;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
  text-transform: uppercase;
}

/* ═══════════════════════════════════════════════════════════════
   PREMIUM CYBER FORM STYLING
   ═══════════════════════════════════════════════════════════════ */
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

.action-row {
  justify-content: flex-end;
  margin-top: 4px;
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

/* ═══════════════════════════════════════════════════════════════
   PREMIUM CYBER TABLE & GRID RESULTS
   ═══════════════════════════════════════════════════════════════ */
.results-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.result-count {
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 0.5px;
  text-shadow: 0 0 4px rgba(0, 255, 157, 0.3);
}

.welcome-box {
  padding: 40px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.welcome-icon {
  font-size: 32px;
  text-shadow: 0 0 10px var(--cyan);
}

.welcome-text {
  max-width: 480px;
  line-height: 1.6;
}

/* ═══════════════════════════════════════════════════════════════
   NOTIFICATIONS AND UTILITIES
   ═══════════════════════════════════════════════════════════════ */
.error-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 45, 110, 0.08);
  border: 1px solid var(--pink);
  border-radius: 4px;
  padding: 10px 16px;
  margin-bottom: 16px;
  color: #fff;
  font-family: var(--font-ui);
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.1);
}

.error-icon {
  font-size: 14px;
}

.error-msg {
  font-size: 12px;
  line-height: 1.5;
}

.success-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(0, 255, 157, 0.08);
  border: 1px solid var(--green);
  border-radius: 4px;
  padding: 10px 16px;
  margin-bottom: 16px;
  color: #fff;
  font-family: var(--font-ui);
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.1);
}

.success-icon {
  font-weight: 700;
  color: var(--green);
}

.success-msg {
  font-size: 12px;
  line-height: 1.5;
}

.mono {
  font-family: var(--font-co);
}

.font-cyan {
  color: var(--cyan) !important;
}

.font-bold {
  font-weight: 600;
}

.font-gray {
  color: var(--text) !important;
}

.font-green {
  color: var(--green) !important;
}

.font-small {
  font-size: 10.5px;
}

.terminal-loader {
  padding: 40px;
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

.loading-text {
  font-family: var(--font-co);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--cyan);
  animation: rj45-led-pulse 1s infinite alternate;
}

/* ═══════════════════════════════════════════════════════════════
   HIGH-ALERT CONSOLE OVERLAY MODALS
   ═══════════════════════════════════════════════════════════════ */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(4, 7, 13, 0.85);
  backdrop-filter: blur(8px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.cyber-modal-card {
  width: 100%;
  max-width: 580px;
  background: rgba(8, 14, 26, 0.96);
  border: 1px solid var(--orange);
  box-shadow: 0 0 30px rgba(255, 107, 53, 0.25), inset 0 0 15px rgba(255, 107, 53, 0.1);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
}

.cyber-modal-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 12px;
  height: 12px;
  border-top: 3px solid var(--orange);
  border-left: 3px solid var(--orange);
  pointer-events: none;
}

.cyber-modal-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: 0;
  width: 12px;
  height: 12px;
  border-bottom: 3px solid var(--orange);
  border-right: 3px solid var(--orange);
  pointer-events: none;
}

.cyber-modal-header {
  background: rgba(255, 107, 53, 0.1);
  border-bottom: 1px solid rgba(255, 107, 53, 0.2);
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: var(--orange);
  text-shadow: 0 0 6px rgba(255, 107, 53, 0.4);
}

.btn-close-modal {
  background: transparent;
  border: none;
  color: var(--orange);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close-modal:hover {
  color: white;
  text-shadow: 0 0 8px var(--orange);
}

.cyber-modal-body {
  padding: 20px;
  color: var(--textwh);
  font-family: var(--font-ui);
  font-size: 13px;
  line-height: 1.5;
}

.sql-preview-box {
  background: #020408 !important;
  border: 1px dashed var(--orange) !important;
  color: var(--orange) !important;
  text-shadow: 0 0 4px rgba(255, 107, 53, 0.3);
  padding: 14px;
  font-family: var(--font-co);
  font-size: 11.5px;
  line-height: 1.5;
  border-radius: 4px;
  margin: 12px 0;
  max-height: 160px;
  overflow-y: auto;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.9);
}

.warning-text-box {
  display: flex;
  gap: 12px;
  background: rgba(255, 107, 53, 0.05);
  border: 1px solid rgba(255, 107, 53, 0.2);
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--textbr);
}

.warning-icon {
  font-size: 14px;
}

.cyber-modal-footer {
  padding: 14px 20px;
  border-top: 1px solid rgba(255, 107, 53, 0.15);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: rgba(4, 7, 13, 0.5);
}

.btn-modal-cancel {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 16px;
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 700;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
}

.btn-modal-cancel:hover {
  border-color: var(--textbr);
  color: var(--textwh);
}

.btn-modal-confirm {
  background: var(--orange) !important;
  border: 1px solid var(--orange) !important;
  color: #05080f !important;
  padding: 6px 16px;
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 700;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 0 10px rgba(255, 107, 53, 0.3);
  text-transform: uppercase;
}

.btn-modal-confirm:hover {
  background: #fff !important;
  box-shadow: 0 0 15px var(--orange);
}

/* Add Row Form Styling specifics */
.add-row-card {
  max-width: 500px !important;
  border-color: var(--cyan) !important;
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.2), inset 0 0 15px rgba(0, 229, 255, 0.05) !important;
}

.add-row-card::before, .add-row-card::after {
  border-color: var(--cyan) !important;
}

.add-row-card .cyber-modal-header {
  background: rgba(0, 229, 255, 0.08);
  border-bottom-color: rgba(0, 229, 255, 0.2);
}

.add-row-card .modal-title {
  color: var(--cyan) !important;
  text-shadow: 0 0 6px rgba(0, 229, 255, 0.4);
}

.add-row-card .btn-close-modal {
  color: var(--cyan);
}

.add-row-card .btn-close-modal:hover {
  text-shadow: 0 0 8px var(--cyan);
}

.add-row-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 4px;
}

.add-row-field label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--textbr);
}

.add-row-input {
  width: 100%;
  background: rgba(4, 7, 14, 0.6);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--textwh);
  padding: 8px 12px;
  font-family: var(--font-co);
  font-size: 11px;
  outline: none;
  transition: all 0.2s;
}

.add-row-input:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}

.pk-badge {
  display: inline-block;
  background: rgba(255, 170, 0, 0.15);
  border: 1px solid var(--orange);
  color: var(--orange);
  font-size: 7.5px;
  padding: 1px 4px;
  border-radius: 3px;
  margin-left: 6px;
  vertical-align: middle;
  font-family: var(--font-hd);
  font-weight: 700;
}

.add-row-card .cyber-modal-footer {
  border-top-color: rgba(0, 229, 255, 0.15);
}

.btn-apply {
  background: var(--green) !important;
  border-color: var(--green) !important;
  color: #05080f !important;
  font-weight: 700;
}

.btn-apply:hover {
  background: #fff !important;
  box-shadow: 0 0 15px var(--green);
}

/* ═══════════════════════════════════════════════════════════════
   FULLSCREEN & COLUMN RESIZE STATES
   ═══════════════════════════════════════════════════════════════ */
.db-panel-container.fullscreen-mode {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  background: var(--bg1, #0a0e1a) !important;
  padding: 30px;
  overflow-y: auto;
}
</style>
