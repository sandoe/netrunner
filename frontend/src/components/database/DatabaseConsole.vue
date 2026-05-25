<template>
  <div class="cyber-card">
    <div class="card-title-bar">💻 {{ consoleTitle }}</div>
    <div class="sql-editor-container">
      <textarea 
        v-model="sqlQuery" 
        :placeholder="placeholderText"
        class="sql-textarea mono"
      ></textarea>

      <div class="editor-boilerplates">
        <button 
          v-for="bp in boilerplates" 
          :key="bp.label" 
          class="btn-boilerplate" 
          @click="appendQuery(bp.template)"
        >
          {{ bp.label }}
        </button>
      </div>

      <div class="editor-actions">
        <div class="actions-left">
          <button class="btn-action-sm btn-clear" @click="sqlQuery = ''">🧹 RYD</button>
          <button v-if="activeTable && isRelational" class="btn-action-sm btn-insert" @click="openAddRowModal">➕ NY RÆKKE</button>
          <button v-if="dbConfig.type === 'influxdb'" class="btn-action-sm btn-insert" style="border-color: rgba(0, 229, 255, 0.3); color: var(--cyan);" @click="openAddInfluxPointModal">➕ NYT DATAPUNKT</button>
          <button v-if="activeTable" class="btn-action-sm btn-structure" @click="showTableStructure">🔍 {{ structureBtnLabel }}</button>
        </div>
        <button class="btn-action btn-execute" :disabled="loading || !sqlQuery.trim()" @click="runQuery(nodeId)">
          ⚡ KØR FORESPØRGSEL (Ctrl+Enter)
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'
import { useDatabaseQuery } from '@/composables/useDatabaseQuery'

const props = defineProps<{ nodeId: string }>()

const { 
  dbConfig, 
  activeTable, 
  loading,
  isRelational
} = useDatabaseConfig()

const {
  sqlQuery,
  runQuery,
  appendQuery,
  openAddRowModal,
  openAddInfluxPointModal
} = useDatabaseQuery()

const consoleTitle = computed(() => {
  const type = dbConfig.value.type
  if (type === 'redis') return 'REDIS CLI TERMINAL'
  if (type === 'mongodb') return 'MONGODB SHELL CONSOLE'
  if (type === 'influxdb') return 'INFLUXDB TIME SERIES WORKSPACE'
  return 'SQL QUERY TERMINAL'
})

const placeholderText = computed(() => {
  const type = dbConfig.value.type
  if (type === 'redis') {
    return 'Skriv din Redis kommando her... f.eks. GET min_nøgle'
  } else if (type === 'mongodb') {
    return 'Skriv din MongoDB eval script her... f.eks. db.min_samling.find()'
  } else if (type === 'influxdb') {
    return 'Skriv din InfluxQL forespørgsel her... f.eks. SELECT * FROM cpu'
  } else {
    return 'Skriv din SQL forespørgsel her... f.eks. SELECT * FROM nodes;'
  }
})

const structureBtnLabel = computed(() => {
  const type = dbConfig.value.type
  if (type === 'redis') return 'VIS KEY INFO'
  if (type === 'mongodb') return 'VIS INDEKSER'
  if (type === 'influxdb') return 'VIS STRUKTUR (FIELDS)'
  return 'VIS STRUKTUR'
})

const boilerplates = computed(() => {
  const type = dbConfig.value.type
  if (type === 'redis') {
    return [
      { label: 'GET', template: 'GET "<table>"' },
      { label: 'SET', template: 'SET "<table>" "værdi"' },
      { label: 'DEL', template: 'DEL "<table>"' },
      { label: 'KEYS', template: 'KEYS *' },
      { label: 'TTL', template: 'TTL "<table>"' }
    ]
  } else if (type === 'mongodb') {
    return [
      { label: 'FIND', template: 'db.<table>.find().limit(50)' },
      { label: 'INSERT ONE', template: 'db.<table>.insertOne({ felt: "værdi" })' },
      { label: 'UPDATE ONE', template: 'db.<table>.updateOne({ _id: ObjectId("...") }, { $set: { felt: "ny_værdi" } })' },
      { label: 'DELETE ONE', template: 'db.<table>.deleteOne({ _id: ObjectId("...") })' },
      { label: 'GET INDEXES', template: 'db.<table>.getIndexes()' }
    ]
  } else if (type === 'influxdb') {
    return [
      { label: 'SELECT', template: 'SELECT * FROM "<table>" LIMIT 50;' },
      { label: 'FIELD KEYS', template: 'SHOW FIELD KEYS FROM "<table>";' },
      { label: 'TAG KEYS', template: 'SHOW TAG KEYS FROM "<table>";' },
      { label: 'SERIES', template: 'SHOW SERIES FROM "<table>";' },
      { label: 'DROP SERIES', template: 'DROP SERIES FROM "<table>";' }
    ]
  } else {
    // Relational SQL (sqlite, mysql, mssql, postgresql)
    const list = [
      { label: 'SELECT', template: 'SELECT * FROM <table> LIMIT 50;' },
      { label: 'INSERT', template: 'INSERT INTO <table> (<cols>) VALUES (<vals>);' },
      { label: 'UPDATE', template: 'UPDATE <table> SET <col> = <val> WHERE <cond>;' },
      { label: 'DELETE', template: 'DELETE FROM <table> WHERE <cond>;' }
    ]
    if (type === 'sqlite') {
      list.push({ label: 'SQLITE SCHEMA', template: 'PRAGMA table_info(<table>);' })
    } else if (type === 'postgresql') {
      list.push({ label: 'POSTGRES SCHEMA', template: "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '<table>';" })
    } else if (type === 'mssql') {
      list.push({ label: 'MSSQL SCHEMA', template: "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '<table>';" })
    } else {
      list.push({ label: 'MYSQL SCHEMA', template: 'DESCRIBE <table>;' })
    }
    return list
  }
})

async function showTableStructure() {
  if (!activeTable.value) return
  let query = ''
  const type = dbConfig.value.type
  
  if (type === 'sqlite') {
    query = `PRAGMA table_info("${activeTable.value}");`
  } else if (type === 'mssql' || type === 'postgresql') {
    query = `SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '${activeTable.value}';`
  } else if (type === 'influxdb') {
    query = `SHOW FIELD KEYS FROM "${activeTable.value}";`
  } else if (type === 'redis') {
    query = `TYPE "${activeTable.value}"`
  } else if (type === 'mongodb') {
    query = `db.${activeTable.value}.getIndexes()`
  } else {
    query = `DESCRIBE \`${activeTable.value}\`;`
  }
  sqlQuery.value = query
  await runQuery(props.nodeId)
}
</script>

<style scoped>
.sql-editor-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sql-textarea {
  width: 100%;
  height: 140px;
  background: radial-gradient(circle at center, rgba(13, 20, 38, 0.95) 0%, rgba(2, 4, 8, 0.98) 100%) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px;
  color: var(--green) !important;
  text-shadow: 0 0 4px rgba(0, 255, 157, 0.4);
  padding: 14px;
  font-family: var(--font-co);
  font-size: 12px;
  line-height: 1.5;
  resize: vertical;
  outline: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: inset 0 0 15px rgba(0,0,0,0.9), 0 0 5px rgba(0, 255, 157, 0.05);
}

.sql-textarea:focus {
  border-color: var(--green) !important;
  box-shadow: inset 0 0 15px rgba(0,0,0,0.9), 0 0 15px rgba(0, 255, 157, 0.3) !important;
}

.editor-boilerplates {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn-boilerplate {
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--border);
  color: var(--textbr);
  padding: 5px 10px;
  font-family: var(--font-hd);
  font-size: 8px;
  letter-spacing: 0.5px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
}

.btn-boilerplate:hover {
  border-color: var(--cyan);
  color: var(--cyan);
  background: rgba(0, 229, 255, 0.05);
  box-shadow: 0 0 6px rgba(0, 229, 255, 0.2);
}

.editor-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.actions-left {
  display: flex;
  gap: 8px;
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
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  text-transform: uppercase;
}

.btn-action-sm:hover:not(:disabled) {
  border-color: var(--cyan);
  color: #fff;
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.btn-clear {
  border-color: rgba(255, 45, 110, 0.3);
  color: var(--pink);
}

.btn-clear:hover {
  border-color: var(--pink) !important;
  color: white !important;
  background: rgba(255, 45, 110, 0.15) !important;
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.3) !important;
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

.btn-structure {
  border-color: rgba(0, 229, 255, 0.3);
  color: var(--cyan);
}

.btn-structure:hover {
  border-color: var(--cyan) !important;
  color: white !important;
  background: rgba(0, 229, 255, 0.15) !important;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3) !important;
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

.btn-execute {
  background: var(--green) !important;
  border: 1px solid var(--green) !important;
  color: #05080f !important;
  font-weight: 700;
}

.btn-execute:hover:not(:disabled) {
  background: white !important;
  color: #05080f !important;
  box-shadow: 0 0 18px var(--green);
}

.btn-execute:disabled {
  background: rgba(26, 37, 64, 0.3) !important;
  border-color: var(--border) !important;
  color: rgba(255,255,255,0.2) !important;
  box-shadow: none !important;
  cursor: not-allowed;
}

.mono {
  font-family: var(--font-co);
}
</style>
