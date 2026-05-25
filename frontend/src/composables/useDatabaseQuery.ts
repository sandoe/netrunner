import { ref, nextTick } from 'vue'
import { api } from '@/api/client'
import { 
  useDatabaseConfig, 
  parseCSV, 
  parseTSV 
} from './useDatabaseConfig'

export const sqlQuery = ref('')
export const queryDuration = ref(0)
export const resultsHeaders = ref<string[]>([])
export const resultsRows = ref<Record<string, any>[]>([])
export const rawNosqlOutput = ref('')

export const inlineEditRow = ref<number | null>(null)
export const inlineEditCol = ref<string | null>(null)
export const inlineEditValue = ref('')
export const inlineInputRef = ref<HTMLInputElement | null>(null)

export const showConfirmModal = ref(false)
export const pendingSql = ref('')
export const onConfirmCallback = ref<(() => Promise<void>) | null>(null)

export const showAddRowModal = ref(false)
export const newRowData = ref<Record<string, string>>({})

export const showAddInfluxPointModal = ref(false)
export const newInfluxPoint = ref({
  measurement: '',
  tags: '',
  fields: '',
  timestamp: ''
})

export async function runQuery(nodeId: string) {
  if (!sqlQuery.value.trim()) return
  
  const { 
    dbConfig, 
    loading, 
    activeTable, 
    showFlashMsg, 
    buildDbCommand, 
    loadSchema,
    hasRunQuery
  } = useDatabaseConfig()
  
  loading.value = true
  resultsHeaders.value = []
  resultsRows.value = []
  rawNosqlOutput.value = ''
  hasRunQuery.value = true
  
  const startTime = Date.now()
  try {
    const cmd = buildDbCommand(sqlQuery.value, true)
    const res = await api.executeNode(nodeId, [cmd])
    const out = res.results?.[0]?.output || ''
    const err = res.results?.[0]?.error || ''
    
    queryDuration.value = Date.now() - startTime
    
    const isCommandNotFound = out.toLowerCase().includes('not found') || 
                              out.toLowerCase().includes('ikke fundet') || 
                              out.toLowerCase().includes('kommando') ||
                              out.toLowerCase().includes('no such file') ||
                              out.toLowerCase().includes('command not found') ||
                              out.toLowerCase().includes('nicht gefunden') ||
                              out.toLowerCase().includes('introuvable')
    
    if (err || out.toLowerCase().includes('error') || out.toLowerCase().includes('incorrect') || out.toLowerCase().includes('syntax error') || isCommandNotFound) {
      throw new Error(out || err || 'Forespørgsel fejlede.')
    }
    
    if (dbConfig.value.type === 'redis' || dbConfig.value.type === 'mongodb') {
      rawNosqlOutput.value = out
      resultsHeaders.value = ['nosql'] // Flag to render NoSQL view
      return
    }
    
    const parsed = (dbConfig.value.type === 'sqlite' || dbConfig.value.type === 'influxdb') ? parseCSV(out) : parseTSV(out)
    if (parsed.length > 0) {
      resultsHeaders.value = parsed[0]
      const rows = parsed.slice(1)
      
      resultsRows.value = rows.map(row => {
        const obj: Record<string, any> = {}
        resultsHeaders.value.forEach((h, idx) => {
          obj[h] = row[idx] === undefined ? null : row[idx]
        })
        return obj
      })
    } else {
      showFlashMsg('Kommando afviklet succesfuldt. Ingen rækker returneret.')
      if (activeTable.value) {
        setTimeout(() => loadSchema(nodeId), 500)
      }
    }
  } catch (err: any) {
    showFlashMsg(`SQL afviklingsfejl: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export function appendQuery(tpl: string) {
  const { activeTable, activeTableColumns } = useDatabaseConfig()
  const table = activeTable.value || 'min_tabel'
  let query = tpl.replace(/<table>/g, table)
  
  if (activeTableColumns.value.length > 0) {
    const colNames = activeTableColumns.value.map(c => c.name).join(', ')
    const valPlaceholders = activeTableColumns.value.map(() => '?').join(', ')
    query = query
      .replace(/<cols>/g, colNames)
      .replace(/<vals>/g, valPlaceholders)
  } else {
    query = query
      .replace(/<cols>/g, 'felt1, felt2')
      .replace(/<vals>/g, "'værdi1', 'værdi2'")
  }
  sqlQuery.value = query
}

export function formatCellValue(val: any): string {
  if (val === null || val === undefined) return 'NULL'
  if (val === '') return '"" (Tom)'
  return String(val)
}

export function getCellClass(val: any): string {
  if (val === null || val === undefined) return 'font-gray font-small italic'
  if (val === '') return 'font-gray font-small italic'
  if (!isNaN(val)) return 'font-green'
  return ''
}

export function startInlineEdit(rowIdx: number, colName: string, curVal: any) {
  inlineEditRow.value = rowIdx
  inlineEditCol.value = colName
  inlineEditValue.value = curVal === null || curVal === undefined ? '' : String(curVal)
  
  nextTick(() => {
    if (inlineInputRef.value) {
      inlineInputRef.value.focus()
      inlineInputRef.value.select()
    }
  })
}

export function cancelInlineEdit() {
  inlineEditRow.value = null
  inlineEditCol.value = null
  inlineEditValue.value = ''
}

export function buildRowCondition(row: Record<string, any>): string {
  const { activeTableColumns } = useDatabaseConfig()
  const pks = activeTableColumns.value.filter(c => c.pk)
  if (pks.length > 0) {
    return pks.map(pk => {
      const val = row[pk.name]
      return `${pk.name} = '${String(val).replace(/'/g, "''")}'`
    }).join(' AND ')
  }
  
  return Object.keys(row).map(key => {
    const val = row[key]
    if (val === null || val === undefined) {
      return `${key} IS NULL`
    }
    return `${key} = '${String(val).replace(/'/g, "''")}'`
  }).join(' AND ')
}

export function confirmInlineEdit(row: Record<string, any>, nodeId: string) {
  if (inlineEditRow.value === null || !inlineEditCol.value) return
  
  const newVal = inlineEditValue.value
  const col = inlineEditCol.value
  
  if (String(row[col]) === newVal) {
    cancelInlineEdit()
    return
  }
  
  const { activeTable, loading, showFlashMsg, buildDbCommand } = useDatabaseConfig()
  
  if (!activeTable.value) {
    cancelInlineEdit()
    return
  }
  
  const conds = buildRowCondition(row)
  const escapedNewVal = newVal.replace(/'/g, "''")
  const updateSql = `UPDATE ${activeTable.value} SET ${col} = '${escapedNewVal}' WHERE ${conds};`
  
  pendingSql.value = updateSql
  onConfirmCallback.value = async () => {
    loading.value = true
    try {
      const cmd = buildDbCommand(updateSql, false)
      const res = await api.executeNode(nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      const err = res.results?.[0]?.error || ''
      
      if (err || out.toLowerCase().includes('error')) {
        throw new Error(out || err || 'Opdatering mislykkedes.')
      }
      
      showFlashMsg('Række opdateret successfully!')
      await runQuery(nodeId)
    } catch (err: any) {
      showFlashMsg(`Kunne ikke opdatere celle: ${err.message || err}`, true)
    } finally {
      loading.value = false
    }
  }
  
  showConfirmModal.value = true
  cancelInlineEdit()
}

export async function executePendingSql() {
  showConfirmModal.value = false
  if (onConfirmCallback.value) {
    await onConfirmCallback.value()
    onConfirmCallback.value = null
  }
}

export function deleteRow(row: Record<string, any>, nodeId: string) {
  const { activeTable, loading, showFlashMsg, buildDbCommand } = useDatabaseConfig()
  if (!activeTable.value) return
  
  const conds = buildRowCondition(row)
  const deleteSql = `DELETE FROM ${activeTable.value} WHERE ${conds};`
  
  pendingSql.value = deleteSql
  onConfirmCallback.value = async () => {
    loading.value = true
    try {
      const cmd = buildDbCommand(deleteSql, false)
      const res = await api.executeNode(nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      const err = res.results?.[0]?.error || ''
      
      if (err || out.toLowerCase().includes('error')) {
        throw new Error(out || err || 'Sletning mislykkedes.')
      }
      
      showFlashMsg('Række slettet fra tabellen!')
      await runQuery(nodeId)
    } catch (err: any) {
      showFlashMsg(`Kunne ikke slette række: ${err.message || err}`, true)
    } finally {
      loading.value = false
    }
  }
  
  showConfirmModal.value = true
}

export function openAddRowModal() {
  const { activeTable, activeTableColumns } = useDatabaseConfig()
  if (!activeTable.value || activeTableColumns.value.length === 0) return
  newRowData.value = {}
  activeTableColumns.value.forEach(c => {
    newRowData.value[c.name] = ''
  })
  showAddRowModal.value = true
}

export function submitAddRow(nodeId: string) {
  showAddRowModal.value = false
  const { activeTable, loading, showFlashMsg, buildDbCommand } = useDatabaseConfig()
  if (!activeTable.value) return
  
  const cols: string[] = []
  const vals: string[] = []
  
  Object.keys(newRowData.value).forEach(key => {
    const val = newRowData.value[key]
    if (val !== undefined && val !== null && val.trim() !== '') {
      cols.push(key)
      vals.push(`'${val.replace(/'/g, "''")}'`)
    }
  })
  
  if (cols.length === 0) {
    showFlashMsg('Du skal udfylde mindst ét felt for at tilføje en række!', true)
    return
  }
  
  const insertSql = `INSERT INTO ${activeTable.value} (${cols.join(', ')}) VALUES (${vals.join(', ')});`
  
  pendingSql.value = insertSql
  onConfirmCallback.value = async () => {
    loading.value = true
    try {
      const cmd = buildDbCommand(insertSql, false)
      const res = await api.executeNode(nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      const err = res.results?.[0]?.error || ''
      
      if (err || out.toLowerCase().includes('error')) {
        throw new Error(out || err || 'Indsættelse mislykkedes.')
      }
      
      showFlashMsg('Ny række tilføjet successfully!')
      await runQuery(nodeId)
    } catch (err: any) {
      showFlashMsg(`Kunne ikke tilføje række: ${err.message || err}`, true)
    } finally {
      loading.value = false
    }
  }
  
  showConfirmModal.value = true
}

export function openAddInfluxPointModal() {
  newInfluxPoint.value = {
    measurement: '',
    tags: '',
    fields: '',
    timestamp: ''
  }
  showAddInfluxPointModal.value = true
}

export async function submitAddInfluxPoint(nodeId: string) {
  showAddInfluxPointModal.value = false
  const { dbConfig, loading, showFlashMsg, buildDbCommand, loadSchema } = useDatabaseConfig()
  
  const m = newInfluxPoint.value.measurement.trim()
  const f = newInfluxPoint.value.fields.trim()
  const t = newInfluxPoint.value.tags.trim()
  const ts = newInfluxPoint.value.timestamp.trim()
  
  if (!m || !f) {
    showFlashMsg('Måling og felter er påkrævede!', true)
    return
  }
  
  // Format the Influx Line Protocol INSERT command
  const lineProtocol = `INSERT ${m}${t ? ',' + t : ''} ${f}${ts ? ' ' + ts : ''}`
  
  pendingSql.value = lineProtocol
  onConfirmCallback.value = async () => {
    loading.value = true
    try {
      const cmd = buildDbCommand(lineProtocol, false)
      const res = await api.executeNode(nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      const err = res.results?.[0]?.error || ''
      
      if (err || out.toLowerCase().includes('error') || out.toLowerCase().includes('database name required')) {
        throw new Error(out || err || 'Indsættelse mislykkedes.')
      }
      
      showFlashMsg('Nyt datapunkt tilføjet succesfuldt til InfluxDB!')
      // Refresh the measurements list
      await loadSchema(nodeId)
      
      // If we are currently inspecting this measurement, refresh the query!
      const { activeTable } = useDatabaseConfig()
      if (activeTable.value === m) {
        await runQuery(nodeId)
      }
    } catch (err: any) {
      showFlashMsg(`Kunne ikke tilføje datapunkt til InfluxDB: ${err.message || err}`, true)
    } finally {
      loading.value = false
    }
  }
  
  showConfirmModal.value = true
}

export function useDatabaseQuery() {
  return {
    sqlQuery,
    queryDuration,
    resultsHeaders,
    resultsRows,
    rawNosqlOutput,
    inlineEditRow,
    inlineEditCol,
    inlineEditValue,
    inlineInputRef,
    showConfirmModal,
    pendingSql,
    onConfirmCallback,
    showAddRowModal,
    newRowData,
    showAddInfluxPointModal,
    newInfluxPoint,
    runQuery,
    appendQuery,
    formatCellValue,
    getCellClass,
    startInlineEdit,
    cancelInlineEdit,
    confirmInlineEdit,
    buildRowCondition,
    executePendingSql,
    deleteRow,
    openAddRowModal,
    submitAddRow,
    openAddInfluxPointModal,
    submitAddInfluxPoint
  }
}
