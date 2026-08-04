<script setup>
import { ref, onMounted } from 'vue';
import { api } from '@/api/client';

const activeTab = ref('overview');
const stats = ref({});

// Query state
const queryTarget = ref('postgres');
const rawQuery = ref('');
const querying = ref(false);
const queryResults = ref(null);
const queryError = ref('');

// Exfil state
const exfil = ref({
  dsn: '',
  source_table: '',
  target_table: ''
});
const exfiltrating = ref(false);
const exfilError = ref('');
const exfilSuccess = ref('');

// Explorer state
const explorerTables = ref([]);
const explorerError = ref('');

const fetchTables = async () => {
  try {
    const { data } = await api.get('/v1/database/tables');
    explorerTables.value = data.tables;
  } catch (err) {
    explorerError.value = err.message;
  }
};

const viewTable = async (table) => {
  rawQuery.value = `SELECT * FROM ${table} LIMIT 100`;
  queryTarget.value = 'postgres';
  activeTab.value = 'query';
  await runQuery();
};


const fetchStats = async () => {
  try {
    const { data } = await api.get('/v1/database/stats');
    stats.value = data;
  } catch (err) {
    console.error(err);
  }
};

const runQuery = async () => {
  if (!rawQuery.value) return;
  querying.value = true;
  queryError.value = '';
  queryResults.value = null;

  try {
    const { data } = await api.post('/v1/database/query', {
      target: queryTarget.value,
      query: rawQuery.value
    });
    queryResults.value = data;
  } catch (err) {
    queryError.value = err.message;
  } finally {
    querying.value = false;
  }
};

const savingLimits = ref(false);
const limitMessage = ref('');
const saveLimits = async () => {
  if (!stats.value?.storage) return;
  savingLimits.value = true;
  limitMessage.value = '';
  try {
    await api.post('/settings', {
      max_postgres_mb: stats.value.storage.postgres.limit_mb,
      max_influxdb_mb: stats.value.storage.influxdb.limit_mb,
      max_logs_mb: stats.value.storage.logs.limit_mb
    });
    limitMessage.value = 'Limits updated';
    setTimeout(() => limitMessage.value = '', 3000);
  } catch (err) {
    limitMessage.value = err.message;
  } finally {
    savingLimits.value = false;
  }
};


const runExfil = async () => {
  if (!exfil.value.dsn || !exfil.value.source_table || !exfil.value.target_table) return;
  exfiltrating.value = true;
  exfilError.value = '';
  exfilSuccess.value = '';

  try {
    const { data } = await api.post('/v1/database/exfiltrate', {
      source_dsn: exfil.value.dsn,
      source_table: exfil.value.source_table,
      target_table: exfil.value.target_table
    });
    exfilSuccess.value = data.message;
    
    // Refresh overview
    await fetchStats();
  } catch (err) {
    exfilError.value = err.message;
  } finally {
    exfiltrating.value = false;
  }
};

onMounted(() => {
  fetchStats();
});
</script>

<template>
  <div class="db-control-container">
    <div class="page-header cyber-panel">
      <h2>DATABASE CONTROL ROOM</h2>
      <p>Manage Postgres, InfluxDB, and perform data exfiltration</p>

      <div class="tabs">
        <button :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">OVERVIEW</button>
        <button :class="{ active: activeTab === 'explorer' }" @click="activeTab = 'explorer'; fetchTables()">TABLE EXPLORER</button>
        <button :class="{ active: activeTab === 'query' }" @click="activeTab = 'query'">QUERY BUILDER</button>
        <button :class="{ active: activeTab === 'exfil' }" @click="activeTab = 'exfil'">DATA EXFILTRATION</button>
      </div>
    </div>

    <!-- Overview Tab -->
    <div v-if="activeTab === 'overview'" class="tab-content overview-grid">
      <div class="cyber-panel">
        <div class="card-header">
          <h3 class="panel-title">{{ stats.postgres?.engine === 'sqlite' ? 'SQLITE METADATA' : 'POSTGRESQL METADATA' }}</h3>
          <span class="status-badge" :class="stats.postgres?.status">{{ stats.postgres?.status?.toUpperCase() || 'UNKNOWN' }}</span>
        </div>
        <div class="card-body" v-if="stats.postgres">
          <div class="stat-row">
            <span class="lbl">TABLES</span>
            <span class="val">{{ stats.postgres.tables }}</span>
          </div>
          <div class="stat-row">
            <span class="lbl">SIZE</span>
            <span class="val">{{ stats.postgres.size }}</span>
          </div>
          <div class="stat-row" v-if="stats.postgres.error">
            <span class="lbl error-lbl">ERROR</span>
            <span class="val error-val">{{ stats.postgres.error }}</span>
          </div>
        </div>
      </div>

      <div class="cyber-panel">
        <div class="card-header">
          <h3 class="panel-title">INFLUXDB ANALYTICS</h3>
          <span class="status-badge" :class="stats.influxdb?.status">{{ stats.influxdb?.status?.toUpperCase() || 'UNKNOWN' }}</span>
        </div>
        <div class="card-body" v-if="stats.influxdb">
          <div class="stat-row">
            <span class="lbl">ACTIVE BUCKETS</span>
            <span class="val">{{ stats.influxdb.buckets }}</span>
          </div>
          <div class="stat-row" v-if="stats.influxdb.error">
            <span class="lbl error-lbl">ERROR</span>
            <span class="val error-val">{{ stats.influxdb.error }}</span>
          </div>
        </div>
      </div>
      <div class="cyber-panel" style="grid-column: 1 / -1;">
        <div class="card-header">
          <h3 class="panel-title">STORAGE LIMITS & USAGE</h3>
          <span class="status-badge online" v-if="limitMessage">{{ limitMessage }}</span>
        </div>
        <div class="card-body" v-if="stats.storage">
          <!-- Postgres -->
          <div class="storage-row">
            <div class="storage-header">
              <span class="lbl">POSTGRESQL</span>
              <span class="val">{{ stats.storage.postgres.used_mb.toFixed(2) }} MB / <input type="number" v-model.number="stats.storage.postgres.limit_mb" class="cyber-input inline-input" /> MB</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: Math.min(100, (stats.storage.postgres.used_mb / stats.storage.postgres.limit_mb) * 100) + '%' }" :class="{ 'warning': (stats.storage.postgres.used_mb / stats.storage.postgres.limit_mb) > 0.8, 'critical': (stats.storage.postgres.used_mb / stats.storage.postgres.limit_mb) > 0.95 }"></div>
            </div>
          </div>
          
          <!-- InfluxDB -->
          <div class="storage-row">
            <div class="storage-header">
              <span class="lbl">INFLUXDB</span>
              <span class="val">{{ stats.storage.influxdb.used_mb.toFixed(2) }} MB / <input type="number" v-model.number="stats.storage.influxdb.limit_mb" class="cyber-input inline-input" /> MB</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: Math.min(100, (stats.storage.influxdb.used_mb / stats.storage.influxdb.limit_mb) * 100) + '%' }" :class="{ 'warning': (stats.storage.influxdb.used_mb / stats.storage.influxdb.limit_mb) > 0.8, 'critical': (stats.storage.influxdb.used_mb / stats.storage.influxdb.limit_mb) > 0.95 }"></div>
            </div>
          </div>
          
          <!-- Logs -->
          <div class="storage-row">
            <div class="storage-header">
              <span class="lbl">LOG FILES</span>
              <span class="val">{{ stats.storage.logs.used_mb.toFixed(2) }} MB / <input type="number" v-model.number="stats.storage.logs.limit_mb" class="cyber-input inline-input" /> MB</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: Math.min(100, (stats.storage.logs.used_mb / stats.storage.logs.limit_mb) * 100) + '%' }" :class="{ 'warning': (stats.storage.logs.used_mb / stats.storage.logs.limit_mb) > 0.8, 'critical': (stats.storage.logs.used_mb / stats.storage.logs.limit_mb) > 0.95 }"></div>
            </div>
          </div>
          
          <div style="margin-top: 1rem; text-align: right;">
            <button class="btn-engage" @click="saveLimits" :disabled="savingLimits">{{ savingLimits ? 'SAVING...' : 'UPDATE LIMITS' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Table Explorer Tab -->
    <div v-if="activeTab === 'explorer'" class="tab-content table-explorer">
      <div class="cyber-panel">
        <div class="card-header">
          <h3 class="panel-title">DATABASE TABLES</h3>
          <button class="btn-engage" @click="fetchTables" style="padding: 4px 10px; margin-top: 0; font-size: 10px;">REFRESH</button>
        </div>
        <div v-if="explorerError" class="scan-error">{{ explorerError }}</div>
        <div class="card-body" v-else-if="explorerTables.length > 0">
          <div class="table-grid">
            <button v-for="table in explorerTables" :key="table" class="btn-table" @click="viewTable(table)">
              <span class="table-icon">📄</span>
              <span class="table-name">{{ table }}</span>
            </button>
          </div>
        </div>
        <div v-else class="empty-state">
          No tables found in the database.
        </div>
      </div>
    </div>

    <!-- Query Builder Tab -->
    <div v-if="activeTab === 'query'" class="tab-content query-builder">
      <div class="cyber-panel query-panel">
        <h3 class="panel-title">SQL / FLUX TERMINAL</h3>
        <div class="form-group">
          <label>Target Database</label>
          <select v-model="queryTarget" class="cyber-input">
            <option value="postgres">SQLite / PostgreSQL</option>
            <option value="influxdb">InfluxDB</option>
          </select>
        </div>
        <div class="form-group">
          <label>Query String</label>
          <textarea v-model="rawQuery" rows="5" class="cyber-input" placeholder="SELECT * FROM nodes..."></textarea>
        </div>
        <button class="btn-engage" @click="runQuery" :disabled="querying || !rawQuery">
          {{ querying ? 'EXECUTING...' : 'RUN QUERY' }}
        </button>
        <div v-if="queryError" class="scan-error">{{ queryError }}</div>
      </div>

      <div class="cyber-panel results-panel" v-if="queryResults">
        <div class="results-header">
          <h3 class="panel-title">RESULTS ({{ queryResults.count }} ROWS)</h3>
          <p>{{ queryResults.message }}</p>
        </div>
        <div class="table-container" v-if="queryResults.rows && queryResults.rows.length > 0">
          <table>
            <thead>
              <tr>
                <th v-for="key in Object.keys(queryResults.rows[0] || {})" :key="key">{{ key }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in queryResults.rows" :key="idx">
                <td v-for="val in Object.values(row)" :key="val">{{ val }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Data Exfiltration Tab -->
    <div v-if="activeTab === 'exfil'" class="tab-content exfil-builder">
      <div class="cyber-panel warning-card">
        <h3 class="panel-title warning-title">⚠️ TARGET ACQUISITION</h3>
        <p>Connect to a foreign database on the network and dump its tables into Netrunner's PostgreSQL for analysis.</p>
      </div>

      <div class="cyber-panel query-panel">
        <div class="form-group">
          <label>Source Database DSN</label>
          <input type="text" v-model="exfil.dsn" class="cyber-input" placeholder="postgresql+asyncpg://user:pass@192.168.1.10:5432/db" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Source Table</label>
            <input type="text" v-model="exfil.source_table" class="cyber-input" placeholder="users" />
          </div>
          <div class="form-group">
            <label>Save As (Local Table Name)</label>
            <input type="text" v-model="exfil.target_table" class="cyber-input" placeholder="dump_users" />
          </div>
        </div>
        
        <button class="btn-engage" @click="runExfil" :disabled="exfiltrating || !exfil.dsn || !exfil.source_table || !exfil.target_table">
          {{ exfiltrating ? 'EXFILTRATING DATA...' : 'START EXFILTRATION' }}
        </button>
        <div v-if="exfilError" class="scan-error">{{ exfilError }}</div>
        <div v-if="exfilSuccess" class="success-msg">{{ exfilSuccess }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.db-control-container {
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
}
.page-header h2 {
  color: var(--cyan);
  margin: 0 0 8px 0;
  font-family: var(--font-hd);
  letter-spacing: 2px;
}
.page-header p {
  margin: 0 0 20px 0;
  color: var(--textbr);
  font-size: 14px;
}

.tabs {
  display: flex;
  gap: 1rem;
  border-bottom: 1px solid var(--border);
}

.tabs button {
  background: none;
  border: none;
  color: var(--text);
  font-family: var(--font-hd);
  font-size: 14px;
  letter-spacing: 1px;
  padding: 10px 15px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

.tabs button:hover {
  color: var(--textbr);
}

.tabs button.active {
  color: var(--cyan);
  border-bottom-color: var(--cyan);
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.cyber-panel {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
}

.panel-title {
  color: var(--cyan);
  margin: 0;
  font-size: 14px;
  font-family: var(--font-hd);
  letter-spacing: 1px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(255,255,255,0.1);
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 10px;
  font-family: var(--font-hd);
  letter-spacing: 1px;
  background: var(--bg);
  border: 1px solid var(--border);
}

.status-badge.online {
  color: var(--green);
  border-color: rgba(106, 190, 48, 0.5);
  background: rgba(106, 190, 48, 0.1);
}

.status-badge.offline, .status-badge.unknown {
  color: var(--pink);
  border-color: rgba(255, 0, 85, 0.5);
  background: rgba(255, 0, 85, 0.1);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
}

.lbl {
  color: var(--text);
  font-family: var(--font-hd);
  font-size: 12px;
}

.val {
  color: var(--textbr);
  font-family: var(--font-co);
  font-size: 14px;
}

.error-lbl {
  color: var(--pink);
}

.error-val {
  color: var(--pink);
  word-break: break-all;
  max-width: 70%;
  text-align: right;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 15px;
}

.form-group label {
  color: var(--textbr);
  font-size: 12px;
  text-transform: uppercase;
  font-family: var(--font-hd);
}

.form-row {
  display: flex;
  gap: 15px;
}

.form-row .form-group {
  flex: 1;
}

.cyber-input {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--textwh);
  padding: 10px;
  border-radius: 4px;
  font-family: var(--font-co);
  outline: none;
}

.cyber-input:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}

textarea.cyber-input {
  resize: vertical;
}

.btn-engage {
  margin-top: 10px;
  background: rgba(0, 229, 255, 0.1);
  color: var(--cyan);
  border: 1px solid var(--cyan);
  padding: 12px;
  border-radius: 4px;
  font-family: var(--font-hd);
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.btn-engage:not(:disabled):hover {
  background: var(--cyan);
  color: var(--bg);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
}

.btn-engage:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: transparent;
  border-color: var(--border);
  color: var(--text);
}

.scan-error {
  margin-top: 15px;
  padding: 12px;
  background: rgba(255, 0, 85, 0.1);
  border: 1px solid var(--pink);
  color: var(--pink);
  border-radius: 4px;
  font-family: var(--font-co);
  font-size: 13px;
}

.success-msg {
  margin-top: 15px;
  padding: 12px;
  background: rgba(106, 190, 48, 0.1);
  border: 1px solid var(--green);
  color: var(--green);
  border-radius: 4px;
  font-family: var(--font-co);
  font-size: 13px;
}

.warning-card {
  border-left: 4px solid #f39c12;
}

.warning-title {
  color: #f39c12;
  margin-bottom: 8px;
}

.warning-card p {
  color: var(--textbr);
  margin: 0;
  font-size: 14px;
}

.results-panel {
  display: flex;
  flex-direction: column;
}

.results-header {
  margin-bottom: 15px;
}

.results-header p {
  color: var(--text);
  margin: 5px 0 0 0;
  font-size: 12px;
  font-family: var(--font-co);
}

.table-container {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 4px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-co);
  font-size: 13px;
}

th, td {
  padding: 10px 15px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  color: var(--textbr);
}

th {
  background: var(--bg);
  color: var(--cyan);
  font-family: var(--font-hd);
  position: sticky;
  top: 0;
  z-index: 10;
}

tbody tr:hover td {
  background: rgba(0, 229, 255, 0.05);
}

.storage-row {
  margin-bottom: 20px;
}

.storage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.storage-header .lbl {
  color: var(--text);
  font-family: var(--font-hd);
  font-weight: bold;
  letter-spacing: 1px;
}

.storage-header .val {
  color: var(--textbr);
  font-family: var(--font-co);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.inline-input {
  width: 80px;
  padding: 4px 8px;
  text-align: right;
  height: 24px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: var(--cyan);
  transition: width 0.3s ease, background-color 0.3s ease;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

.progress-fill.warning {
  background: #f39c12;
  box-shadow: 0 0 10px rgba(243, 156, 18, 0.5);
}

.progress-fill.critical {
  background: var(--pink);
  box-shadow: 0 0 10px rgba(255, 0, 85, 0.5);
}

.table-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.btn-table {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--textbr);
}

.btn-table:hover {
  background: rgba(0, 229, 255, 0.1);
  border-color: var(--cyan);
  color: var(--cyan);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.table-icon {
  font-size: 18px;
}

.table-name {
  font-family: var(--font-co);
  font-size: 14px;
  font-weight: bold;
}

.empty-state {
  padding: 30px;
  text-align: center;
  color: var(--text);
  font-family: var(--font-hd);
  border: 1px dashed var(--border);
  border-radius: 4px;
}
</style>
