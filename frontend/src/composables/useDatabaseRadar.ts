import { ref } from 'vue'
import { api } from '@/api/client'

// Global states so both Chassis and Radar tabs read the same data
export const activeSubTab = ref('explorer')
export const radarHost = ref('127.0.0.1')
export const radarScanType = ref('all')
export const scanning = ref(false)
export const radarLogs = ref<string[]>([])
export const foundDatabases = ref<Array<{ type: string; path?: string; host?: string; port?: number }>>([])

export async function runRadarScan(nodeId: string) {
  scanning.value = true
  radarLogs.value = []
  foundDatabases.value = []
  
  const addLog = (msg: string) => {
    const time = new Date().toLocaleTimeString('da-DK', { hour12: false })
    radarLogs.value.push(`[${time}] ${msg}`)
  }
  
  addLog('📡 Initialiserer Database Sonar-antenne array på node...')
  addLog(`📡 Scanning startet mod host: ${radarHost.value}`)
  
  try {
    // 1. Scan network database ports
    if (radarScanType.value === 'all' || radarScanType.value === 'network') {
      addLog('⚡ Prober netværksporte for kendte database-daemons...')
      const ports = [3306, 5432, 1433, 1521, 6379, 27017, 9042, 8086]
      const dbNames: Record<number, string> = {
        3306: 'MySQL/MariaDB',
        5432: 'PostgreSQL',
        1433: 'MS SQL Server (MSSQL)',
        1521: 'Oracle DB',
        6379: 'Redis Cache',
        27017: 'MongoDB',
        9042: 'Cassandra',
        8086: 'InfluxDB'
      }
      
      const pythonScanner = `python3 -c "import socket; host='${radarHost.value}'; ports=[3306, 5432, 1433, 1521, 6379, 27017, 9042, 8086]; [print(f'OPEN:{p}') for p in ports if (s:=socket.socket(socket.AF_INET, socket.SOCK_STREAM)).settimeout(0.35) or s.connect_ex((host, p)) == 0]"`
      
      const res = await api.executeNode(nodeId, [pythonScanner])
      const out = res.results?.[0]?.output || ''
      const lines = out.split(/\r?\n/)
      
      let foundNet = 0
      for (const line of lines) {
        if (line.startsWith('OPEN:')) {
          const portStr = line.split(':')[1]
          const portNum = parseInt(portStr, 10)
          const name = dbNames[portNum] || 'Ukendt'
          addLog(`[TARGET DETECTED] Port ${portNum} er ÅBEN! Aktiv ${name} database identificeret!`)
          
          const portToType: Record<number, string> = {
            3306: 'mysql',
            1433: 'mssql',
            5432: 'postgresql',
            1521: 'oracle',
            6379: 'redis',
            27017: 'mongodb',
            9042: 'cassandra',
            8086: 'influxdb'
          }
          const dbTypeMap = portToType[portNum] || 'unknown'
          
          foundDatabases.value.push({
            type: dbTypeMap,
            host: radarHost.value,
            port: portNum
          })
          foundNet++
        }
      }
      if (foundNet === 0) {
        addLog('ℹ️ Ingen åbne netværksporte fundet på de gængse databasetyper.')
      }
    }
    
    // 2. Scan filesystem for SQLite database files
    if (radarScanType.value === 'all' || radarScanType.value === 'sqlite') {
      addLog('📁 Gennemsøger lokale directories efter SQLite-databasefiler...')
      
      const findCmd = `find /home /var/www /opt /srv /etc -maxdepth 5 \\( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.db3" \\) -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/cache/*" -type f 2>/dev/null | head -n 15`
      
      const res = await api.executeNode(nodeId, [findCmd])
      const out = res.results?.[0]?.output || ''
      const lines = out.split(/\r?\n/).map(l => l.trim()).filter(l => l !== '')
      
      let foundFiles = 0
      for (const file of lines) {
        addLog(`[FILE LOCATED] SQLite-database identificeret: ${file}`)
        foundDatabases.value.push({
          type: 'sqlite',
          path: file
        })
        foundFiles++
      }
      if (foundFiles === 0) {
        addLog('ℹ️ Ingen lokale SQLite-filer (.db/.sqlite) fundet i de gængse mapper.')
      }
    }
    
    addLog(`🏁 Sonar-scanning afsluttet succesfuldt! Fandt ${foundDatabases.value.length} database(r).`)
  } catch (err: any) {
    addLog(`❌ Scanning fejlede: ${err.message || err}`)
  } finally {
    scanning.value = false
  }
}

export function useDatabaseRadar() {
  return {
    activeSubTab,
    radarHost,
    radarScanType,
    scanning,
    radarLogs,
    foundDatabases,
    runRadarScan
  }
}
