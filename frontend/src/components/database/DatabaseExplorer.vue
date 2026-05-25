<template>
  <div v-if="connected" class="cyber-card schema-card">
    <div class="card-title-bar">
      <span>
        {{ dbConfig.type === 'redis' ? '📂 NØGLER (KEYS)' : dbConfig.type === 'mongodb' ? '📂 SAMLINGER' : dbConfig.type === 'influxdb' ? '📂 MÅLINGER' : '📂 TABEL OVERVIEW' }}
        ({{ tables.length }})
      </span>
      <button class="btn-refresh-schema" @click="loadSchema(nodeId)">🔄</button>
    </div>

    <div v-if="!tables.length" class="empty-text">
      {{ dbConfig.type === 'redis' ? 'Ingen nøgler fundet.' : dbConfig.type === 'mongodb' ? 'Ingen samlinger fundet.' : dbConfig.type === 'influxdb' ? 'Ingen målinger fundet.' : 'Ingen tabeller fundet. Prøv at oprette en eller tilslut en anden database.' }}
    </div>

    <div v-else class="tables-tree-list">
      <div 
        v-for="t in tables" 
        :key="t" 
        class="tree-item"
        :class="{ 'active': activeTable === t }"
        @click="selectTable(t)"
      >
        <span class="tree-icon">
          {{ dbConfig.type === 'redis' ? '🔑' : dbConfig.type === 'mongodb' ? '🗂️' : dbConfig.type === 'influxdb' ? '📈' : '📊' }}
        </span>
        <span class="tree-name">{{ t }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'
import { useDatabaseQuery } from '@/composables/useDatabaseQuery'

const props = defineProps<{ nodeId: string }>()

const { 
  dbConfig, 
  connected, 
  tables, 
  activeTable, 
  loadSchema, 
  fetchTableColumns 
} = useDatabaseConfig()

const { 
  sqlQuery, 
  runQuery 
} = useDatabaseQuery()

async function selectTable(tableName: string) {
  activeTable.value = tableName
  
  if (dbConfig.value.type === 'redis') {
    sqlQuery.value = `GET "${tableName}"`
    await runQuery(props.nodeId)
  } else if (dbConfig.value.type === 'mongodb') {
    sqlQuery.value = `db.${tableName}.find().limit(50)`
    await runQuery(props.nodeId)
  } else if (dbConfig.value.type === 'influxdb') {
    sqlQuery.value = `SELECT * FROM "${tableName}" LIMIT 50;`
    await runQuery(props.nodeId)
  } else {
    sqlQuery.value = `SELECT * FROM ${tableName} LIMIT 50;`
    await fetchTableColumns(props.nodeId, tableName)
    await runQuery(props.nodeId)
  }
}
</script>

<style scoped>
.schema-card {
  max-height: 480px;
  display: flex;
  flex-direction: column;
}

.btn-refresh-schema {
  background: transparent;
  border: none;
  color: var(--cyan);
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.btn-refresh-schema:hover {
  color: white;
  text-shadow: 0 0 8px var(--cyan);
  transform: rotate(180deg);
}

.tables-tree-list {
  overflow-y: auto;
  max-height: 400px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-right: 4px;
}

.tree-item {
  padding: 8px 12px;
  border-radius: 4px;
  background: rgba(13, 20, 38, 0.4);
  border: 1px solid var(--border);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.tree-item::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 3px;
  background: var(--cyan);
  transform: scaleY(0);
  transform-origin: bottom;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.tree-item:hover::after {
  transform: scaleY(1);
}

.tree-item:hover {
  background: rgba(0, 229, 255, 0.08);
  border-color: rgba(0, 229, 255, 0.3);
  padding-left: 18px; /* High-tech slide indent */
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.1);
}

.tree-item.active {
  background: rgba(0, 229, 255, 0.15) !important;
  border-color: var(--cyan) !important;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.tree-item.active::after {
  transform: scaleY(1);
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
}

.tree-item.active::before {
  content: '>';
  font-family: var(--font-co);
  color: var(--cyan);
  font-weight: 700;
  margin-right: -4px;
  animation: blink-cursor 1s infinite alternate;
}

@keyframes blink-cursor {
  0% { opacity: 0.2; }
  100% { opacity: 1; }
}

.tree-name {
  color: var(--textwh);
  font-family: var(--font-co);
  font-size: 11px;
}

.empty-text {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  padding: 8px;
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  text-align: center;
  font-family: var(--font-ui);
}
</style>
