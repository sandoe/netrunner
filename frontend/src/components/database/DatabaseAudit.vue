<template>
  <div class="db-audit-workspace">
    <div class="cyber-card audit-card">
      <div class="card-title-bar warning" style="border-bottom-color: var(--orange);">
        <span>🛡️ CYBERSHIELD AUDIT SCANNER</span>
        <button class="btn-action-sm btn-scan" :class="{ scanning: loading }" :disabled="loading" @click="runAuditScan">
          {{ loading ? '⏳ KØRER PEN-TEST...' : '🎯 INITIÉR CYBER-SCAN' }}
        </button>
      </div>

      <div class="audit-results" v-if="hasScanned">
        <div class="audit-summary" :class="riskLevelClass">
          <div class="score-display">
            <span class="score-label">RISIKOVURDERING:</span>
            <span class="score-value">{{ riskLevelText }}</span>
          </div>
          <div class="score-stats">
            <span class="stat critical">🔴 {{ criticalCount }} KRITISKE</span>
            <span class="stat warning">🟡 {{ warningCount }} ADVARSLER</span>
            <span class="stat info">🔵 {{ infoCount }} INFO</span>
          </div>
        </div>

        <div class="audit-findings">
          <div v-for="(finding, i) in findings" :key="i" class="finding-item" :class="finding.severity">
            <div class="finding-header">
              <span class="finding-icon">{{ getSeverityIcon(finding.severity) }}</span>
              <span class="finding-title">{{ finding.title }}</span>
            </div>
            <div class="finding-desc">{{ finding.description }}</div>
            <div v-if="finding.remediationSql" class="finding-remediation">
              <div class="remediation-label">AFHJÆLPNING (REMEDIATION SQL):</div>
              <pre class="mono"><code>{{ finding.remediationSql }}</code></pre>
              <button class="btn-action-sm" style="border-color: var(--green); color: var(--green);" @click="applyRemediation(finding.remediationSql)">KØR SCRIPT</button>
            </div>
          </div>
          
          <div v-if="findings.length === 0" class="no-findings" style="text-align: center; padding: 32px; color: var(--green); font-weight: bold; border: 1px dashed var(--green); border-radius: 4px; background: rgba(0, 255, 157, 0.05);">
            ✅ INGEN SÅRBARHEDER FUNDET. DATABASEN ER SIKKER!
          </div>
        </div>
      </div>
      
      <div v-else class="welcome-box">
        <div class="welcome-icon font-orange">🛡️</div>
        <p class="welcome-text font-gray">
          Cybershield Audit er klar til at scanne.
        </p>
        <p class="welcome-tip font-small font-orange">
          Klik på 'KØR SÅRBARHEDSSCAN' for at inspicere den aktive database for miskonfigurationer, overdreven rettighedstildeling og åbne sikkerhedshuller.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import { useDatabaseConfig } from '@/composables/useDatabaseConfig'
import { useDatabaseQuery } from '@/composables/useDatabaseQuery'

const props = defineProps<{ nodeId: string }>()

const { dbConfig, connected, buildDbCommand, showFlashMsg } = useDatabaseConfig()
const { pendingSql, showConfirmModal, onConfirmCallback } = useDatabaseQuery()

interface AuditFinding {
  severity: 'critical' | 'warning' | 'info'
  title: string
  description: string
  remediationSql?: string
}

const loading = ref(false)
const hasScanned = ref(false)
const findings = ref<AuditFinding[]>([])

const criticalCount = computed(() => findings.value.filter(f => f.severity === 'critical').length)
const warningCount = computed(() => findings.value.filter(f => f.severity === 'warning').length)
const infoCount = computed(() => findings.value.filter(f => f.severity === 'info').length)

const riskLevelClass = computed(() => {
  if (criticalCount.value > 0) return 'risk-high'
  if (warningCount.value > 0) return 'risk-medium'
  return 'risk-low'
})

const riskLevelText = computed(() => {
  if (criticalCount.value > 0) return 'HØJ RISIKO'
  if (warningCount.value > 0) return 'MODERAT'
  return 'LAV RISIKO (SIKKER)'
})

function getSeverityIcon(sev: string) {
  if (sev === 'critical') return '🔴'
  if (sev === 'warning') return '🟡'
  return '🔵'
}

async function runAuditScan() {
  if (!connected.value) {
    showFlashMsg('Du skal være forbundet til en database for at scanne.', true)
    return
  }
  
  loading.value = true
  findings.value = []
  
  try {
    const type = dbConfig.value.type
    
    if (type === 'postgresql') {
      // Postgres scan: check superusers
      const cmd = buildDbCommand(`SELECT usename FROM pg_user WHERE usesuper = true;`, true)
      const res = await api.executeNode(props.nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      const rows = out.split('\n').filter(Boolean).slice(1) // skip header
      
      for (const row of rows) {
        const user = row.trim()
        if (user === 'postgres') {
          findings.value.push({
            severity: 'warning',
            title: 'Standard administratorkonto aktiv',
            description: `Kontoen '${user}' er en standard superbruger. Sikkerhedspraksis foreskriver at ændre standardnavnet eller deaktivere direkte login.`,
            remediationSql: `ALTER USER postgres RENAME TO custom_admin;`
          })
        } else {
          findings.value.push({
            severity: 'info',
            title: 'Superbruger fundet',
            description: `Brugeren '${user}' har super-rettigheder. Sørg for at dette er tilsigtet (Least Privilege Principle).`
          })
        }
      }
    } else if (type === 'mssql') {
      // MSSQL scan: check sysadmins
      const cmd = buildDbCommand(`SELECT name FROM sys.server_principals WHERE IS_SRVROLEMEMBER('sysadmin', name) = 1;`, false)
      const res = await api.executeNode(props.nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      
      const rows = out.split('\n').map(r => r.trim()).filter(Boolean)
      
      let saFound = false
      for (const user of rows) {
        if (user === 'sa') saFound = true;
        if (user !== 'sa' && user !== 'NT SERVICE\\MSSQLSERVER' && user !== 'NT AUTHORITY\\SYSTEM' && user !== 'sa') {
          findings.value.push({
            severity: 'info',
            title: 'Sysadmin rolle tildelt',
            description: `Kontoen '${user}' har adgang til sysadmin rollen. Bør overvåges nøje.`
          })
        }
      }
      
      if (saFound) {
        findings.value.push({
          severity: 'critical',
          title: 'Standard "sa" konto er aktiv',
          description: `Den indbyggede 'sa' konto er aktiveret, hvilket er et almindeligt mål for brute-force angreb. Den bør deaktiveres, og i stedet bør Windows Authentication bruges.`,
          remediationSql: `ALTER LOGIN sa DISABLE;`
        })
      }
      
      if (dbConfig.value.mssqlAuthType === 'sql') {
        findings.value.push({
          severity: 'warning',
          title: 'Brug af SQL Authentication',
          description: `Du er logget ind via SQL Authentication. Sikkerheds-best-practice er at bruge Windows Authentication (Active Directory) for MSSQL.`,
        })
      }
      
    } else if (type === 'mysql') {
      // MySQL scan: check empty passwords or root user
      const cmd = buildDbCommand(`SELECT user, host, plugin FROM mysql.user;`, true)
      const res = await api.executeNode(props.nodeId, [cmd])
      const out = res.results?.[0]?.output || ''
      
      if (out.includes('root') && out.includes('%')) {
        findings.value.push({
          severity: 'critical',
          title: 'Root login fra alle netværk',
          description: `Kontoen 'root'@'%' tillader fuld administratoradgang fra ethvert IP-netværk. Dette er en enorm sikkerhedsrisiko.`,
          remediationSql: `DELETE FROM mysql.user WHERE User='root' AND Host='%'; FLUSH PRIVILEGES;`
        })
      }
      
      findings.value.push({
        severity: 'info',
        title: 'Netværkseksponering',
        description: `Databasen lytter på port ${dbConfig.value.port}. Sikr at der er en firewall (f.eks. iptables eller AWS Security Group), der blokerer offentlig adgang.`
      })
      
    } else if (type === 'sqlite') {
       findings.value.push({
          severity: 'info',
          title: 'Filrettigheder (SQLite)',
          description: `Da dette er SQLite, findes der ingen brugere. Sørg for at filen '${dbConfig.value.sqlitePath}' har de korrekte chown/chmod rettigheder på Linux-noden, så uvedkommende ikke kan downloade den (f.eks. 'chmod 600').`
       })
    } else {
      findings.value.push({
        severity: 'warning',
        title: 'Scanner ikke understøttet fuldt ud',
        description: `Der er endnu ikke tilføjet en fuld penetrationstest-suite for ${type}. Auditer logfiler og tjek for standardpasswords manuelt.`
      })
    }
    
    // Add common check
    if (dbConfig.value.user === 'root' || dbConfig.value.user === 'sa' || dbConfig.value.user === 'admin' || dbConfig.value.user === 'postgres') {
       findings.value.push({
         severity: 'warning',
         title: 'Brug af defaultkonto til forbindelsen',
         description: `Du er logget ind som standard-kontoen '${dbConfig.value.user}'. Det anbefales stærkt at oprette specifikke service-konti med Least Privilege.`
       })
    }
    
  } catch (err: any) {
    showFlashMsg(`Scannerfejl: ${err.message}`, true)
  } finally {
    loading.value = false
    hasScanned.value = true
  }
}

function applyRemediation(sql: string) {
  pendingSql.value = sql
  if (onConfirmCallback) {
    onConfirmCallback.value = async () => {
      loading.value = true
      try {
        const cmd = buildDbCommand(sql, false)
        const res = await api.executeNode(props.nodeId, [cmd])
        const out = res.results?.[0]?.output || ''
        const err = res.results?.[0]?.error || ''
        
        if (err || out.toLowerCase().includes('error')) {
          throw new Error(out || err || 'Remediation mislykkedes.')
        }
        
        showFlashMsg('Sikkerhedsopdatering blev anvendt!')
        await runAuditScan() // rescan
      } catch (err: any) {
        showFlashMsg(`Fejl under patching: ${err.message}`, true)
      } finally {
        loading.value = false
      }
    }
    if (showConfirmModal) showConfirmModal.value = true
  }
}
</script>

<style scoped>
.db-audit-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}
.audit-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
}
.audit-results {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}
.audit-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(10, 15, 25, 0.6);
  border: 1px solid var(--border);
  border-radius: 6px;
}
.audit-summary.risk-high {
  border-color: var(--pink);
  box-shadow: 0 0 12px rgba(255, 45, 110, 0.2);
}
.audit-summary.risk-medium {
  border-color: var(--orange);
}
.audit-summary.risk-low {
  border-color: var(--green);
}
.score-display {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.score-label {
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--textbr);
}
.score-value {
  font-size: 20px;
  font-weight: 700;
  text-shadow: 0 0 8px currentColor;
}
.risk-high .score-value { color: var(--pink); }
.risk-medium .score-value { color: var(--orange); }
.risk-low .score-value { color: var(--green); }

.score-stats {
  display: flex;
  gap: 16px;
  font-family: var(--font-co);
  font-size: 11px;
}

.audit-findings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.finding-item {
  padding: 16px;
  border-radius: 6px;
  background: rgba(10, 15, 25, 0.4);
  border-left: 4px solid var(--border);
}
.finding-item.critical {
  border-left-color: var(--pink);
  background: rgba(255, 45, 110, 0.05);
}
.finding-item.warning {
  border-left-color: var(--orange);
  background: rgba(255, 171, 0, 0.05);
}
.finding-item.info {
  border-left-color: var(--cyan);
}
.finding-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.finding-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--textwh);
}
.finding-desc {
  font-size: 12px;
  color: var(--textbr);
  line-height: 1.5;
  margin-bottom: 12px;
}
.finding-remediation {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 4px;
  border: 1px dashed rgba(255, 255, 255, 0.1);
}
.remediation-label {
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--green);
  margin-bottom: 6px;
}
.finding-remediation pre {
  margin: 0 0 12px 0;
  padding: 8px;
  background: #000;
  border: 1px solid rgba(0, 255, 157, 0.3);
  color: var(--green);
  font-size: 11px;
  border-radius: 4px;
}
.btn-scan {
  border-color: var(--pink);
  color: var(--pink);
  background: rgba(255, 45, 110, 0.05);
  box-shadow: 0 0 8px rgba(255, 45, 110, 0.2);
  font-weight: bold;
  letter-spacing: 1px;
  transition: all 0.3s ease;
}
.btn-scan:hover:not(:disabled) {
  background: var(--pink);
  color: #000;
  box-shadow: 0 0 15px var(--pink);
  transform: scale(1.02);
}
.btn-scan.scanning {
  border-color: var(--orange);
  color: var(--orange);
  animation: pulse-scan 1s infinite alternate;
}

@keyframes pulse-scan {
  from { box-shadow: 0 0 5px var(--orange); }
  to { box-shadow: 0 0 20px var(--orange); text-shadow: 0 0 5px var(--orange); }
}
</style>
