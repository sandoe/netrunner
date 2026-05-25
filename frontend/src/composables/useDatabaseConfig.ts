import { ref, computed } from 'vue'
import { api } from '@/api/client'

// Global state variables for unified database panel state
export const dbConfig = ref({
  type: 'sqlite',
  sqlitePath: 'data/netrunner.db',
  host: '127.0.0.1',
  port: 3306,
  user: 'root',
  password: '',
  database: '',
  mssqlAuthType: 'sql' // 'sql' or 'windows'
})

export const connected = ref(false)
export const tables = ref<string[]>([])
export const activeTable = ref('')
export const activeTableColumns = ref<{ name: string; type: string; pk: boolean; defaultValue: any }[]>([])
export const availableDatabases = ref<string[]>([])
export const hasRunQuery = ref(false)

export const loading = ref(false)
export const error = ref('')
export const successMsg = ref('')

export const isRelational = computed(() => {
  return ['sqlite', 'mysql', 'mssql', 'postgresql'].includes(dbConfig.value.type)
})

export const isReadOnly = computed(() => {
  return ['redis', 'mongodb', 'influxdb'].includes(dbConfig.value.type)
})

export function showFlashMsg(text: string, isErr = false) {
  if (isErr) {
    error.value = text
    successMsg.value = ''
  } else {
    successMsg.value = text
    error.value = ''
    setTimeout(() => {
      if (successMsg.value === text) successMsg.value = ''
    }, 4500)
  }
}

// RFC 4180-compliant CSV parser for sqlite3
export function parseCSV(text: string): string[][] {
  const result: string[][] = []
  let row: string[] = []
  let inQuotes = false
  let curVal = ''
  
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    const next = text[i+1]
    
    if (inQuotes) {
      if (c === '"') {
        if (next === '"') {
          curVal += '"'
          i++ // skip next quote
        } else {
          inQuotes = false
        }
      } else {
        curVal += c
      }
    } else {
      if (c === '"') {
        inQuotes = true
      } else if (c === ',') {
        row.push(curVal)
        curVal = ''
      } else if (c === '\n' || c === '\r') {
        row.push(curVal)
        curVal = ''
        if (row.length > 0 && !(row.length === 1 && row[0] === '')) {
          result.push(row)
        }
        row = []
        if (c === '\r' && next === '\n') {
          i++ // skip double newline chars
        }
      } else {
        curVal += c
      }
    }
  }
  if (curVal || row.length > 0) {
    row.push(curVal)
    if (row.length > 0 && !(row.length === 1 && row[0] === '')) {
      result.push(row)
    }
  }
  return result
}

// MySQL Batch parser (tab-separated values)
export function parseTSV(text: string): string[][] {
  const lines = text.split(/\r?\n/)
  const result: string[][] = []
  for (const line of lines) {
    if (!line.trim()) continue
    const row = line.split('\t').map(col => {
      // Unescape MySQL batch strings
      return col
        .replace(/\\n/g, '\n')
        .replace(/\\t/g, '\t')
        .replace(/\\r/g, '\r')
        .replace(/\\\\/g, '\\')
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"')
    })
    result.push(row)
  }
  return result
}

// Build remote shell terminal command based on selected DB engine
export function buildDbCommand(sql: string, includeHeaders = true): string {
  const cfg = dbConfig.value
  const cleanSql = sql.trim().replace(/"/g, '\\"').replace(/`/g, '\\`').replace(/\$/g, '\\$')
  
  const type = cfg.type
  const sqlitePath = (cfg.sqlitePath || '').trim()
  const host = (cfg.host || '').trim()
  const port = String(cfg.port || '').trim()
  const user = (cfg.user || '').trim()
  const password = (cfg.password || '').trim()
  const database = (cfg.database || '').trim()
  
  if (type === 'sqlite') {
    const headerOption = includeHeaders ? '-header' : ''
    return `sqlite3 ${headerOption} -csv "${sqlitePath}" "${cleanSql}" 2>&1`
  } else if (type === 'mssql') {
    const dbArg = database ? ` -d "${database}"` : ''
    if (cfg.mssqlAuthType === 'windows') {
      return `sqlcmd -S "${host},${port}" -E${dbArg} -s $'\\t' -W -Q "${cleanSql}" 2>&1 || sqsh -S "${host}:${port}" -E${dbArg} -m bcp -C "${cleanSql}" 2>&1`
    } else {
      const passArg = password ? ` -P "${password}"` : ''
      return `sqlcmd -S "${host},${port}" -U "${user}"${passArg}${dbArg} -s $'\\t' -W -Q "${cleanSql}" 2>&1 || sqsh -S "${host}:${port}" -U "${user}"${passArg}${dbArg} -m bcp -C "${cleanSql}" 2>&1`
    }
  } else if (type === 'postgresql') {
    const passArg = password ? `PGPASSWORD="${password}" ` : ''
    const dbArg = database ? ` -d "${database}"` : ''
    const headerOption = includeHeaders ? '' : '-t'
    // Uses psql, output formatted as TSV (-A -F $'\t')
    return `${passArg}psql -h "${host}" -p ${port} -U "${user}"${dbArg} -A -F $'\\t' ${headerOption} -c "${cleanSql}" 2>&1`
  } else if (type === 'redis') {
    const passArg = password ? ` -a "${password}"` : ''
    // Redis-cli accepts standard commands
    return `redis-cli -h "${host}" -p ${port}${passArg} ${cleanSql} 2>&1`
  } else if (type === 'mongodb') {
    const passArg = password ? ` -p "${password}"` : ''
    const userArg = user ? ` -u "${user}"` : ''
    // mongosh/mongo Javascript evaluation
    return `mongosh --host "${host}" --port ${port}${userArg}${passArg} --quiet --eval "${cleanSql}" 2>&1 || mongo --host "${host}" --port ${port}${userArg}${passArg} --quiet --eval "${cleanSql}" 2>&1`
  } else if (type === 'influxdb') {
    const passArg = password ? ` -password "${password}"` : ''
    const userArg = user ? ` -username "${user}"` : ''
    // Use '_internal' as a fallback system database if no database is specified, preventing the CLI from throwing "database name required" on global queries
    const dbName = database || '_internal'
    const dbArg = ` -database "${dbName}"`
    const formatOption = '-format csv'
    return `influx -host "${host}" -port ${port}${userArg}${passArg}${dbArg} ${formatOption} -execute "${cleanSql}" 2>&1`
  } else {
    const headerOption = includeHeaders ? '' : '-N'
    const dbArg = database ? ` "${database}"` : ''
    const passArg = password ? ` -p'${password}'` : ''
    return `mysql -h "${host}" -P ${port} -u "${user}"${passArg}${dbArg} ${headerOption} -B -e "${cleanSql}" 2>&1`
  }
}

export function saveConfig(nodeId: string) {
  const key = `nr_db_config_${nodeId}`
  localStorage.setItem(key, JSON.stringify(dbConfig.value))
}

export function loadConfig(nodeId: string) {
  connected.value = false
  tables.value = []
  activeTable.value = ''
  availableDatabases.value = []
  hasRunQuery.value = false
  error.value = ''
  successMsg.value = ''
  
  const key = `nr_db_config_${nodeId}`
  const saved = localStorage.getItem(key)
  if (saved) {
    try {
      dbConfig.value = JSON.parse(saved)
    } catch {
      // fallback
    }
  } else {
    dbConfig.value = {
      type: 'sqlite',
      sqlitePath: 'data/netrunner.db',
      host: '127.0.0.1',
      port: 3306,
      user: 'root',
      password: '',
      database: ''
    }
  }
}

export function onTypeChange(nodeId: string) {
  connected.value = false
  tables.value = []
  activeTable.value = ''
  if (dbConfig.value.type === 'mssql') {
    dbConfig.value.port = 1433
    dbConfig.value.user = 'sa'
  } else if (dbConfig.value.type === 'mysql') {
    dbConfig.value.port = 3306
    dbConfig.value.user = 'root'
  } else if (dbConfig.value.type === 'postgresql') {
    dbConfig.value.port = 5432
    dbConfig.value.user = 'postgres'
  } else if (dbConfig.value.type === 'redis') {
    dbConfig.value.port = 6379
    dbConfig.value.user = 'default'
  } else if (dbConfig.value.type === 'mongodb') {
    dbConfig.value.port = 27017
    dbConfig.value.user = 'admin'
  } else if (dbConfig.value.type === 'influxdb') {
    dbConfig.value.port = 8086
    dbConfig.value.user = 'admin'
  }
  saveConfig(nodeId)
}

export async function testConnection(nodeId: string) {
  loading.value = true
  error.value = ''
  connected.value = false
  saveConfig(nodeId)
  
  try {
    let testCmd = ''
    const type = dbConfig.value.type
    const sqlitePath = (dbConfig.value.sqlitePath || '').trim()
    const host = (dbConfig.value.host || '').trim()
    const port = String(dbConfig.value.port || '').trim()
    const user = (dbConfig.value.user || '').trim()
    const password = (dbConfig.value.password || '').trim()
    const database = (dbConfig.value.database || '').trim()

    if (type === 'sqlite') {
      testCmd = `sqlite3 "${sqlitePath}" "SELECT 1;"`
    } else if (type === 'mssql') {
      if (dbConfig.value.mssqlAuthType === 'windows') {
        const dbArg = database ? ` -d "${database}"` : ''
        // For Windows Authentication use -E for trusted connection. Sqsh doesn't natively do pure Windows Auth the same way, but we will skip -U to avoid interactive prompts.
        testCmd = `sqlcmd -S "${host},${port}" -E${dbArg} -Q "SELECT 1;" 2>&1 || sqsh -S "${host}:${port}"${dbArg} -C "SELECT 1;" 2>&1`
      } else {
        const passArg = password ? ` -P "${password}"` : ''
        const dbArg = database ? ` -d "${database}"` : ''
        testCmd = `sqlcmd -S "${host},${port}" -U "${user}"${passArg}${dbArg} -Q "SELECT 1;" 2>&1 || sqsh -S "${host}:${port}" -U "${user}"${passArg}${dbArg} -C "SELECT 1;" 2>&1`
      }
    } else if (type === 'postgresql') {
      const passArg = password ? `PGPASSWORD="${password}" ` : ''
      const dbArg = database ? ` -d "${database}"` : ''
      testCmd = `${passArg}psql -h "${host}" -p ${port} -U "${user}"${dbArg} -c "SELECT 1;" 2>&1`
    } else if (type === 'redis') {
      const passArg = password ? ` -a "${password}"` : ''
      testCmd = `redis-cli -h "${host}" -p ${port}${passArg} ping 2>&1`
    } else if (type === 'mongodb') {
      const passArg = password ? ` -p "${password}"` : ''
      const userArg = user ? ` -u "${user}"` : ''
      testCmd = `mongosh --host "${host}" --port ${port}${userArg}${passArg} --quiet --eval "db.adminCommand({ping: 1})" 2>&1 || mongo --host "${host}" --port ${port}${userArg}${passArg} --quiet --eval "db.adminCommand({ping: 1})" 2>&1`
    } else if (type === 'influxdb') {
      const passArg = password ? ` -password "${password}"` : ''
      const userArg = user ? ` -username "${user}"` : ''
      testCmd = `influx -host "${host}" -port ${port}${userArg}${passArg} -execute "SHOW DATABASES" 2>&1`
    } else {
      const passArg = password ? ` -p'${password}'` : ''
      testCmd = `mysql -h "${host}" -P ${port} -u "${user}"${passArg} -e "SELECT 1;"`
    }
    
    const res = await api.executeNode(nodeId, [testCmd])
    const out = res.results?.[0]?.output || ''
    const err = res.results?.[0]?.error || ''
    
    const isCommandNotFound = out.toLowerCase().includes('not found') || 
                              out.toLowerCase().includes('ikke fundet') || 
                              out.toLowerCase().includes('kommando') ||
                              out.toLowerCase().includes('no such file') ||
                              out.toLowerCase().includes('command not found') ||
                              out.toLowerCase().includes('nicht gefunden') ||
                              out.toLowerCase().includes('introuvable')
    
    if (err || out.toLowerCase().includes('error') || out.toLowerCase().includes('denied') || isCommandNotFound) {
      throw new Error(out || err || 'Kunne ikke forbinde til databasen. Sørg for at stien eller login-data er korrekte, samt at klienten er installeret på noden.')
    }
    
    connected.value = true
    await loadSchema(nodeId)
    showFlashMsg('Forbindelse oprettet og skema opdateret successfully!')
  } catch (err: any) {
    showFlashMsg(err.message || String(err), true)
  } finally {
    loading.value = false
  }
}

export async function loadSchema(nodeId: string) {
  if (!connected.value) return
  error.value = ''
  
  try {
    let schemaCmd = ''
    if (dbConfig.value.type === 'sqlite') {
      schemaCmd = buildDbCommand(`SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';`, false)
    } else if (dbConfig.value.type === 'mssql') {
      schemaCmd = buildDbCommand(`SELECT name FROM sys.tables;`, false)
    } else if (dbConfig.value.type === 'postgresql') {
      schemaCmd = buildDbCommand(`SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';`, false)
    } else if (dbConfig.value.type === 'redis') {
      schemaCmd = buildDbCommand(`KEYS *`, false)
    } else if (dbConfig.value.type === 'mongodb') {
      schemaCmd = buildDbCommand(`db.getCollectionNames().join('\\n')`, false)
    } else if (dbConfig.value.type === 'influxdb') {
      schemaCmd = buildDbCommand(`SHOW MEASUREMENTS;`, false)
    } else {
      schemaCmd = buildDbCommand(`SHOW TABLES;`, false)
    }
    
    const res = await api.executeNode(nodeId, [schemaCmd])
    const out = res.results?.[0]?.output || ''
    const err = res.results?.[0]?.error || ''
    
    const isCommandNotFound = out.toLowerCase().includes('not found') || 
                              out.toLowerCase().includes('ikke fundet') || 
                              out.toLowerCase().includes('kommando') ||
                              out.toLowerCase().includes('no such file') ||
                              out.toLowerCase().includes('command not found') ||
                              out.toLowerCase().includes('nicht gefunden') ||
                              out.toLowerCase().includes('introuvable')
    
    const isError = err || 
                    out.toLowerCase().includes('error') || 
                    out.toLowerCase().includes('denied') || 
                    out.toLowerCase().includes('flag provided but not defined') ||
                    out.toLowerCase().includes('usage of influx') ||
                    isCommandNotFound;
    
    if (isError) {
      throw new Error(out || err || 'Fejl under indlæsning af tabelskema.')
    }
    
    if (dbConfig.value.type === 'influxdb') {
      const parsed = parseCSV(out)
      tables.value = parsed
        .map(row => row[1] ? row[1].trim() : '')
        .filter(t => t && t.trim() !== '' && t !== 'measurement' && t !== 'name')
    } else {
      const parsed = dbConfig.value.type === 'sqlite' ? parseCSV(out) : parseTSV(out)
      tables.value = parsed
        .map(row => row[0] ? row[0].trim() : '')
        .filter(t => t && t.trim() !== '')
    }
  } catch (err: any) {
    showFlashMsg(`Fejl under indlæsning af tabelskema: ${err.message || err}`, true)
  }
}

export async function fetchTableColumns(nodeId: string, tableName: string) {
  activeTableColumns.value = []
  try {
    let colCmd = ''
    if (dbConfig.value.type === 'sqlite') {
      colCmd = buildDbCommand(`PRAGMA table_info("${tableName}");`, true)
    } else if (dbConfig.value.type === 'mssql' || dbConfig.value.type === 'postgresql') {
      colCmd = buildDbCommand(`SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '${tableName}';`, true)
    } else if (dbConfig.value.type === 'mysql') {
      colCmd = buildDbCommand(`DESCRIBE \`${tableName}\`;`, true)
    } else {
      return
    }
    
    const res = await api.executeNode(nodeId, [colCmd])
    const out = res.results?.[0]?.output || ''
    const err = res.results?.[0]?.error || ''
    
    const isCommandNotFound = out.toLowerCase().includes('not found') || 
                              out.toLowerCase().includes('ikke fundet') || 
                              out.toLowerCase().includes('kommando') ||
                              out.toLowerCase().includes('no such file') ||
                              out.toLowerCase().includes('command not found') ||
                              out.toLowerCase().includes('nicht gefunden') ||
                              out.toLowerCase().includes('introuvable')
    
    if (err || out.toLowerCase().includes('error') || out.toLowerCase().includes('denied') || isCommandNotFound) {
      throw new Error(out || err || 'Fejl under hentning af tabelkolonner.')
    }
    
    const parsed = dbConfig.value.type === 'sqlite' ? parseCSV(out) : parseTSV(out)
    if (parsed.length > 1) {
      const headers = parsed[0]
      const rows = parsed.slice(1)
      
      if (dbConfig.value.type === 'sqlite') {
        const nameIdx = headers.indexOf('name')
        const typeIdx = headers.indexOf('type')
        const pkIdx = headers.indexOf('pk')
        const dfltIdx = headers.indexOf('dflt_value')
        
        activeTableColumns.value = rows.map(r => ({
          name: r[nameIdx] || '',
          type: r[typeIdx] || 'TEXT',
          pk: r[pkIdx] === '1',
          defaultValue: r[dfltIdx] || null
        }))
      } else if (dbConfig.value.type === 'mssql' || dbConfig.value.type === 'postgresql') {
        const nameIdx = headers.indexOf('COLUMN_NAME')
        const typeIdx = headers.indexOf('DATA_TYPE')
        const defaultIdx = headers.indexOf('COLUMN_DEFAULT')
        
        activeTableColumns.value = rows.map(r => ({
          name: r[nameIdx] || '',
          type: r[typeIdx] || 'varchar',
          pk: false,
          defaultValue: r[defaultIdx] || null
        }))
      } else if (dbConfig.value.type === 'mysql') {
        const nameIdx = headers.indexOf('Field')
        const typeIdx = headers.indexOf('Type')
        const keyIdx = headers.indexOf('Key')
        const dfltIdx = headers.indexOf('Default')
        
        activeTableColumns.value = rows.map(r => ({
          name: r[nameIdx] || '',
          type: r[typeIdx] || 'varchar',
          pk: r[keyIdx] === 'PRI',
          defaultValue: r[dfltIdx] || null
        }))
      }
    }
  } catch {
    // silent
  }
}

export async function installSqlite(nodeId: string) {
  loading.value = true
  error.value = ''
  showFlashMsg('Installerer sqlite3 på noden...')
  try {
    const cmd = 'sudo -n apt-get update && sudo -n apt-get install -y sqlite3 || sudo -n apk add sqlite3 || sudo -n yum install -y sqlite3 || apt-get install -y sqlite3 || apk add sqlite3'
    const res = await api.executeNode(nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      showFlashMsg('SQLite3 blev installeret succesfuldt! Forbinder nu...')
      await testConnection(nodeId)
    } else {
      throw new Error(r?.output || r?.error || 'Kunne ikke afvikle installationskommando.')
    }
  } catch (err: any) {
    showFlashMsg(`Installation fejlede: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export async function installMysqlClient(nodeId: string) {
  loading.value = true
  error.value = ''
  showFlashMsg('Installerer mysql-client på noden...')
  try {
    const cmd = 'sudo -n apt-get update && sudo -n apt-get install -y mysql-client mariadb-client || sudo -n apk add mysql-client mariadb-client || sudo -n yum install -y mariadb || apt-get install -y mysql-client mariadb-client || apk add mysql-client'
    const res = await api.executeNode(nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      showFlashMsg('MySQL/MariaDB klient blev installeret succesfuldt! Forbinder nu...')
      await testConnection(nodeId)
    } else {
      throw new Error(r?.output || r?.error || 'Kunne ikke afvikle installationskommando.')
    }
  } catch (err: any) {
    showFlashMsg(`Installation fejlede: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export async function installMssqlClient(nodeId: string) {
  loading.value = true
  error.value = ''
  showFlashMsg('Installerer MS SQL-klient (sqsh) på noden...')
  try {
    const cmd = 'sudo -n apt-get update && sudo -n apt-get install -y sqsh || sudo -n apk add sqsh || sudo -n yum install -y sqsh || apt-get install -y sqsh || apk add sqsh'
    const res = await api.executeNode(nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      showFlashMsg('sqsh (MSSQL-klient) blev installeret succesfuldt! Forbinder nu...')
      await testConnection(nodeId)
    } else {
      throw new Error(r?.output || r?.error || 'Kunne ikke afvikle installationskommando.')
    }
  } catch (err: any) {
    showFlashMsg(`Installation fejlede: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export async function installPostgresClient(nodeId: string) {
  loading.value = true
  error.value = ''
  showFlashMsg('Installerer PostgreSQL-klient på noden...')
  try {
    const cmd = 'sudo -n apt-get update && sudo -n apt-get install -y postgresql-client || sudo -n apk add postgresql-client || sudo -n yum install -y postgresql || apt-get install -y postgresql-client || apk add postgresql-client'
    const res = await api.executeNode(nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      showFlashMsg('PostgreSQL-klient blev installeret succesfuldt! Forbinder nu...')
      await testConnection(nodeId)
    } else {
      throw new Error(r?.output || r?.error || 'Kunne ikke afvikle installationskommando.')
    }
  } catch (err: any) {
    showFlashMsg(`Installation fejlede: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export async function installRedisTools(nodeId: string) {
  loading.value = true
  error.value = ''
  showFlashMsg('Installerer Redis-cli på noden...')
  try {
    const cmd = 'sudo -n apt-get update && sudo -n apt-get install -y redis-tools || sudo -n apk add redis || sudo -n yum install -y redis || apt-get install -y redis-tools || apk add redis'
    const res = await api.executeNode(nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      showFlashMsg('Redis-cli blev installeret succesfuldt! Forbinder nu...')
      await testConnection(nodeId)
    } else {
      throw new Error(r?.output || r?.error || 'Kunne ikke afvikle installationskommando.')
    }
  } catch (err: any) {
    showFlashMsg(`Installation fejlede: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export async function installMongosh(nodeId: string) {
  loading.value = true
  error.value = ''
  showFlashMsg('Installerer MongoDB-klient (mongosh) på noden...')
  try {
    const cmd = 'sudo -n apt-get update && sudo -n apt-get install -y mongodb-mongosh || sudo -n apk add mongodb-tools || apt-get install -y mongodb-mongosh'
    const res = await api.executeNode(nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      showFlashMsg('mongosh blev installeret succesfuldt! Forbinder nu...')
      await testConnection(nodeId)
    } else {
      throw new Error(r?.output || r?.error || 'Kunne ikke afvikle installationskommando.')
    }
  } catch (err: any) {
    showFlashMsg(`Installation fejlede: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export async function installInfluxClient(nodeId: string) {
  loading.value = true
  error.value = ''
  showFlashMsg('Installerer InfluxDB-klient på noden...')
  try {
    const cmd = 'sudo -n apt-get update && sudo -n apt-get install -y influxdb-client || sudo -n apk add influxdb || apt-get install -y influxdb-client || apk add influxdb'
    const res = await api.executeNode(nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      showFlashMsg('InfluxDB-klient blev installeret succesfuldt! Forbinder nu...')
      await testConnection(nodeId)
    } else {
      throw new Error(r?.output || r?.error || 'Kunne ikke afvikle installationskommando.')
    }
  } catch (err: any) {
    showFlashMsg(`Installation fejlede: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export async function fetchDatabases(nodeId: string) {
  availableDatabases.value = []
  error.value = ''
  
  // Save credentials before running discovery
  saveConfig(nodeId)
  
  try {
    let dbCmd = ''
    const cfg = dbConfig.value
    
    // Build connection query using default DBs if the target is blank
    if (cfg.type === 'mysql') {
      const passArg = cfg.password ? ` -p'${cfg.password}'` : ''
      dbCmd = `mysql -h "${cfg.host}" -P ${cfg.port} -u "${cfg.user}"${passArg} -B -N -e "SHOW DATABASES;" 2>&1`
    } else if (cfg.type === 'influxdb') {
      const passArg = cfg.password ? ` -password "${cfg.password}"` : ''
      const userArg = cfg.user ? ` -username "${cfg.user}"` : ''
      dbCmd = `influx -host "${cfg.host}" -port ${cfg.port}${userArg}${passArg} -format csv -execute "SHOW DATABASES" 2>&1`
    } else if (cfg.type === 'postgresql') {
      const passArg = cfg.password ? `PGPASSWORD="${cfg.password}" ` : ''
      const dbArg = cfg.database ? cfg.database : 'postgres' // Connect to postgres by default to fetch databases list
      dbCmd = `${passArg}psql -h "${cfg.host}" -p ${cfg.port} -U "${cfg.user}" -d "${dbArg}" -A -F $'\\t' -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;" 2>&1`
    } else if (cfg.type === 'mssql') {
      const dbArg = cfg.database ? cfg.database : 'master' // Connect to master by default to fetch databases
      if (cfg.mssqlAuthType === 'windows') {
        dbCmd = `sqlcmd -S "${cfg.host},${cfg.port}" -E -d "${dbArg}" -s $'\\t' -W -Q "SELECT name FROM sys.databases;" 2>&1 || sqsh -S "${cfg.host}:${cfg.port}" -d "${dbArg}" -m bcp -C "SELECT name FROM sys.databases;" 2>&1`
      } else {
        const passArg = cfg.password ? ` -P "${cfg.password}"` : ''
        dbCmd = `sqlcmd -S "${cfg.host},${cfg.port}" -U "${cfg.user}"${passArg} -d "${dbArg}" -s $'\\t' -W -Q "SELECT name FROM sys.databases;" 2>&1 || sqsh -S "${cfg.host}:${cfg.port}" -U "${cfg.user}"${passArg} -d "${dbArg}" -m bcp -C "SELECT name FROM sys.databases;" 2>&1`
      }
    } else if (cfg.type === 'mongodb') {
      const passArg = cfg.password ? ` -p "${cfg.password}"` : ''
      const userArg = cfg.user ? ` -u "${cfg.user}"` : ''
      dbCmd = `mongosh --host "${cfg.host}" --port ${cfg.port}${userArg}${passArg} --quiet --eval "db.getMongo().getDBNames().join('\\n')" 2>&1 || mongo --host "${cfg.host}" --port ${cfg.port}${userArg}${passArg} --quiet --eval "db.getMongo().getDBNames().join('\\n')" 2>&1`
    } else {
      // sqlite or redis do not support multi-database listings in this manner
      return
    }
    
    loading.value = true
    const res = await api.executeNode(nodeId, [dbCmd])
    const out = res.results?.[0]?.output || ''
    const err = res.results?.[0]?.error || ''
    
    const isCommandNotFound = out.toLowerCase().includes('not found') || 
                              out.toLowerCase().includes('ikke fundet') || 
                              out.toLowerCase().includes('kommando') ||
                              out.toLowerCase().includes('no such file') ||
                              out.toLowerCase().includes('command not found') ||
                              out.toLowerCase().includes('nicht gefunden') ||
                              out.toLowerCase().includes('introuvable')
                              
    if (err || out.toLowerCase().includes('error') || out.toLowerCase().includes('denied') || isCommandNotFound) {
      throw new Error(out || err || 'Kunne ikke hente liste over databaser fra serveren. Tjek dine loginoplysninger.')
    }
    
    let dbList: string[] = []
    if (cfg.type === 'influxdb') {
      const parsed = parseCSV(out)
      // InfluxDB csv output parses first field as database names
      dbList = parsed.map(row => row[1]).filter(name => name && name.trim() !== '' && name !== 'name' && name !== 'database')
    } else if (cfg.type === 'mongodb') {
      dbList = out.split(/\r?\n/).map(line => line.trim()).filter(line => line !== '')
    } else {
      const parsed = parseTSV(out)
      dbList = parsed.map(row => row[0]).filter(name => name && name.trim() !== '')
    }
    
    // Clean list (remove SQL Server / MySQL default system DBs to keep it friendly)
    const systemDbs = ['information_schema', 'performance_schema', 'mysql', 'sys', 'master', 'tempdb', 'model', 'msdb', 'local', 'config', 'admin']
    availableDatabases.value = dbList.filter(name => !systemDbs.includes(name.toLowerCase()))
    
    if (availableDatabases.value.length === 0) {
      // If no custom user databases exist, just show what we found
      availableDatabases.value = dbList
    }
    
    showFlashMsg(`Fandt ${availableDatabases.value.length} database(r) på serveren!`)
  } catch (err: any) {
    showFlashMsg(`Fejl ved hentning af databaser: ${err.message || err}`, true)
  } finally {
    loading.value = false
  }
}

export function disconnect() {
  connected.value = false
  tables.value = []
  activeTable.value = ''
  activeTableColumns.value = []
  availableDatabases.value = []
  hasRunQuery.value = false
  error.value = ''
  successMsg.value = ''
  showFlashMsg('Forbindelse afbrudt.')
}

// Composition API hook wrapper
export function useDatabaseConfig() {
  return {
    dbConfig,
    connected,
    tables,
    activeTable,
    activeTableColumns,
    hasRunQuery,
    disconnect,
    availableDatabases,
    loading,
    error,
    successMsg,
    isRelational,
    isReadOnly,
    showFlashMsg,
    buildDbCommand,
    saveConfig,
    loadConfig,
    onTypeChange,
    testConnection,
    loadSchema,
    fetchTableColumns,
    fetchDatabases,
    installSqlite,
    installMysqlClient,
    installMssqlClient,
    installPostgresClient,
    installRedisTools,
    installMongosh,
    installInfluxClient,
    isDbSupported: (type: string) => ['sqlite', 'mysql', 'mssql', 'postgresql', 'redis', 'mongodb', 'influxdb'].includes(type)
  }
}
