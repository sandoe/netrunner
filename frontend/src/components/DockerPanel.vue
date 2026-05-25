<template>
  <div class="docker-panel-container" :class="{ 'fullscreen-mode': isFullscreen }">
    <!-- RJ45 Header & Title -->
    <!-- RJ45 Header & Title -->
    <div class="rj45-panel">
      <div class="rj45-panel-title">🐳 DOCKER SERVICE CONSOLE</div>
      
      <!-- Right-aligned controls and info summary -->
      <div style="display: flex; align-items: center; gap: 16px; margin-left: auto;">
        <!-- Telemetry Summary -->
        <div v-if="daemonStatus && !daemonStatus.includes('not running')" class="rj45-info-summary" style="font-family: var(--font-co); font-size: 10px; color: var(--textbr); text-align: right; line-height: 1.35;">
          <div><span style="color: var(--cyan);">NODE:</span> <span style="color: #fff;">{{ props.nodeId }}</span></div>
          <div><span style="color: var(--green);">RUNNING:</span> <span style="color: #fff;">{{ containers.filter(c => c.status.toLowerCase().includes('up')).length }} / {{ containers.length }}</span></div>
          <div v-if="swarmState"><span style="color: var(--cyan);">SWARM:</span> <span :style="{ color: swarmState === 'active' ? 'var(--green)' : 'var(--pink)' }">{{ swarmState.toUpperCase() }}</span></div>
        </div>

        <div class="rj45-ports-grid">
          <div class="rj45-port active" :title="`Docker Node: ${props.nodeId}\nContainers: ${containers.filter(c => c.status.toLowerCase().includes('up')).length} active`">
            <div class="rj45-led green pulsing"></div>
            <div class="rj45-label">DKR-01</div>
          </div>
        </div>

        <!-- Fullscreen Toggle -->
        <button class="btn-action-sm btn-fullscreen" style="height: 26px; font-size: 8.5px;" @click="toggleFullscreen">
          {{ isFullscreen ? '🖥️ MINIMER' : '🖥️ FULD SKÆRM' }}
        </button>
      </div>
    </div>

    <!-- Daemon Offline Warning -->
    <div v-if="daemonStatus && daemonStatus.includes('not running')" class="daemon-offline-card">
      <div class="warning-header">🛑 DOCKER DAEMON OFFLINE OR NOT INSTALLED</div>
      <p>
        The Docker daemon could not be reached on the target node <code>{{ props.nodeId }}</code>. 
        Ensure Docker is installed and running (e.g. <code>systemctl start docker</code> or <code>rc-service docker start</code>) and the user has correct permissions.
      </p>
      <div style="margin-top: 16px;">
        <button class="btn-action btn-install-docker" :disabled="executing" @click="installDocker" style="background: rgba(0, 229, 255, 0.1); border-color: var(--cyan); color: var(--cyan);">
          {{ executing ? '⏳ INSTALLERER DOCKER...' : '🛠️ INSTALLÉR DOCKER & DOCKER COMPOSE NU' }}
        </button>
      </div>
    </div>

    <!-- Sub-Tabs Selector -->
    <div v-else-if="daemonStatus && !daemonStatus.includes('not running')" class="docker-sub-tabs">
      <button class="sub-tab-btn" :class="{ active: currentTab === 'containers' }" @click="currentTab = 'containers'">
        📦 CONTAINER LIFECYCLE
      </button>
      <button class="sub-tab-btn" :class="{ active: currentTab === 'networks' }" @click="currentTab = 'networks'">
        🌐 NETWORK CONSOLE
      </button>
      <button class="sub-tab-btn" :class="{ active: currentTab === 'swarm' }" @click="currentTab = 'swarm'">
        🐝 SWARM ORCHESTRATOR
      </button>
      <button class="sub-tab-btn" :class="{ active: currentTab === 'compose' }" @click="currentTab = 'compose'">
        🐙 COMPOSE MANAGER
      </button>
      <button class="sub-tab-btn" :class="{ active: currentTab === 'telemetry' }" @click="currentTab = 'telemetry'">
        📈 TELEMETRY DASHBOARD
      </button>
    </div>

    <!-- Error box -->
    <div v-if="error" class="error-box" style="margin-top: 10px;">
      <span class="error-icon">⚠️</span>
      <div class="error-msg">{{ error }}</div>
    </div>

    <!-- TAB 1: CONTAINER LIFECYCLE -->
    <div v-if="daemonStatus && !daemonStatus.includes('not running') && currentTab === 'containers'" class="docker-dashboard-grid">
      <!-- Left Column: Container List -->
      <div class="docker-left-col">
        <!-- Controls & Refresh Banner -->
        <div class="panel-header-controls">
          <span class="active-node-badge">🐳 ACTIVE CONSOLE: {{ props.nodeId }}</span>
          <div class="controls-group">
            <button class="btn-action-sm btn-refresh" :disabled="loading" @click="refreshDocker">
              {{ loading ? '⏳ SYNCING...' : '🔄 REFRESH METRICS' }}
            </button>
            <button class="btn-action-sm btn-danger-outline" @click="runPrune" :disabled="executing">
              🧹 PRUNE UNUSED
            </button>
          </div>
        </div>

        <!-- Container list card -->
        <div class="cyber-card">
          <div class="card-title-bar">
            <span>📦 CONTAINER REGISTRY ({{ containers.length }})</span>
            <span class="pulse-indicator" :class="{ active: loading }"></span>
          </div>

          <div v-if="!containers.length" class="empty-list-text">
            No active or inactive containers found on this node. Use the form on the right to spin one up!
          </div>

          <div v-else class="containers-table-wrapper">
            <table class="cyber-table">
              <thead>
                <tr>
                  <th v-for="(h, idx) in ['CONTAINER ID', 'NAME', 'IMAGE', 'STATUS', 'PORTS', 'RESOURCE STATS', 'ACTIONS']" :key="h" class="resizable-th">
                    {{ h }}
                    <div v-if="idx < 6" class="resize-handle" @mousedown="startResize($event, idx)"></div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in containers" :key="c.id" class="container-row" :class="{ 'stopped': c.status.toLowerCase().includes('exited') }">
                  <td class="mono font-cyan">{{ c.id }}</td>
                  <td class="font-white font-bold">{{ c.name }}</td>
                  <td class="mono font-gray">{{ c.image }}</td>
                  <td>
                    <span class="status-badge" :class="c.status.toLowerCase().includes('up') ? 'active' : 'stopped'">
                      {{ c.status }}
                    </span>
                  </td>
                  <td class="mono font-gray font-small">{{ c.ports }}</td>
                  <td class="mono font-green">
                    <div v-if="stats[c.id]" class="stats-badge-grid">
                      <div class="stats-meter">
                        <span class="meter-label">⚡ CPU: {{ stats[c.id].cpu }}</span>
                        <div class="meter-bar">
                          <div class="meter-fill cpu-fill" :style="{ width: stats[c.id].cpu }"></div>
                        </div>
                      </div>
                      <div class="stats-meter">
                        <span class="meter-label">💾 RAM: {{ stats[c.id].mem }}</span>
                        <div class="meter-bar">
                          <div class="meter-fill ram-fill" :style="{ width: parseRamPercent(stats[c.id].mem) }"></div>
                        </div>
                      </div>
                      <div class="net-io-label">🌐 NET I/O: {{ stats[c.id].net }}</div>
                    </div>
                    <div v-else class="font-gray font-small">No active stats (Stopped)</div>
                  </td>
                  <td>
                    <div class="actions-cell">
                      <button v-if="c.status.toLowerCase().includes('exited')" class="btn-icon-action" title="Start Container" @click="controlContainer(c.name, 'start')">▶</button>
                      <button v-else class="btn-icon-action btn-stop" title="Stop Container" @click="controlContainer(c.name, 'stop')">⏹</button>
                      <button class="btn-icon-action" title="Restart Container" @click="controlContainer(c.name, 'restart')">🔄</button>
                      <button class="btn-icon-action btn-logs" title="View Logs" @click="viewLogs(c.name)">📝</button>
                      <button class="btn-icon-action btn-inspect" title="Inspect Raw Metadata" @click="inspectContainer(c.name)">🔍</button>
                      <button class="btn-icon-action btn-delete-peer" title="Delete Container" @click="controlContainer(c.name, 'delete')">✕</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Images Grid (Minified on container view) -->
        <div class="cyber-card">
          <div class="card-title-bar">💿 ACTIVE DOCKER IMAGES ({{ images.length }})</div>
          <table class="cyber-table">
            <thead>
              <tr>
                <th>REPOSITORY</th>
                <th>TAG</th>
                <th>SIZE</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(img, idx) in images" :key="idx">
                <td class="font-white font-small">{{ img.repository }}</td>
                <td class="mono font-cyan font-small">{{ img.tag }}</td>
                <td class="mono font-green font-small">{{ img.size }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Right Column: Launch Form & CRT terminal logs -->
      <div class="docker-right-col">
        <!-- Run New Container Form -->
        <div class="cyber-card">
          <div class="card-title-bar">🚀 LAUNCH NEW CONTAINER</div>
          
          <div class="specialized-form">
            <div class="form-row">
              <label>Container Navn <input v-model="runForm.name" placeholder="e.g. my-web-app" /></label>
              <label>Docker Image <input v-model="runForm.image" placeholder="e.g. nginx:alpine" /></label>
            </div>
            
            <div class="form-row">
              <label>Port Mappings (CSV) <input v-model="runForm.ports" placeholder="e.g. 8080:80, 8443:443" /></label>
              <label>Volumes Binding (CSV) <input v-model="runForm.volumes" placeholder="e.g. /var/www:/usr/share/nginx/html" /></label>
            </div>

            <div class="form-row">
              <label>Miljøvariabler (Env CSV) <input v-model="runForm.env" placeholder="e.g. DB_HOST=postgres, ENV=prod" /></label>
            </div>

            <div class="form-row">
              <label>Custom Options (Optional) <input v-model="runForm.options" placeholder="e.g. --restart always --net bridge" /></label>
            </div>

            <div class="form-row action-row">
              <button class="btn-action btn-preview-docker" :disabled="executing" @click="previewRun">
                🔍 PREVIEW RUN CMD
              </button>
              <button class="btn-action btn-apply-docker" :disabled="executing || !runForm.name || !runForm.image" @click="applyRun">
                🚀 RUN CONTAINER
              </button>
            </div>
          </div>
        </div>

        <!-- Logs / Inspect Panel -->
        <div v-if="activeLogs || activeInspect" class="cyber-card logs-card">
          <div class="card-title-bar">
            <span>{{ activeLogs ? `📝 LOGS: ${activeTargetContainer}` : `🔍 INSPECT: ${activeTargetContainer}` }}</span>
            <button class="btn-close-logs" @click="closeLogsInspect">✕ CLOSE</button>
          </div>
          <div class="logs-viewport" ref="logsViewport">
            <pre class="logs-pre" v-html="logsOutput"></pre>
          </div>
        </div>

        <!-- Generated preview commands -->
        <div v-if="previewCommands.length" class="cyber-card">
          <div class="card-title-bar">🛠️ GENERATED LAUNCH COMMANDS</div>
          <pre class="preview-pre font-green"><code>{{ previewCommands.join('\n') }}</code></pre>
        </div>

        <!-- Daemon Stats Info -->
        <div v-if="daemonInfo" class="cyber-card">
          <div class="card-title-bar">📊 SYSTEM METRICS (DOCKER INFO)</div>
          <pre class="info-pre font-gray">{{ daemonInfo }}</pre>
        </div>
      </div>
    </div>

    <!-- TAB 2: NETWORK CONSOLE -->
    <div v-if="daemonStatus && !daemonStatus.includes('not running') && currentTab === 'networks'" class="docker-dashboard-grid">
      <!-- Left Column: Networks List & Detailed Inspects -->
      <div class="docker-left-col">
        <div class="cyber-card">
          <div class="card-title-bar">
            <span>🌐 ACTIVE DOCKER NETWORKS ({{ networks.length }})</span>
            <button class="btn-refresh-schema" @click="refreshDocker">🔄</button>
          </div>
          <table class="cyber-table">
            <thead>
              <tr>
                <th>NETWORK ID</th>
                <th>NAME</th>
                <th>DRIVER</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="n in networks" :key="n.id" class="container-row">
                <td class="mono font-cyan font-small">{{ n.id }}</td>
                <td class="font-white font-bold">{{ n.name }}</td>
                <td class="mono font-green font-small">{{ n.driver.toUpperCase() }}</td>
                <td>
                  <div class="actions-cell">
                    <button class="btn-icon-action" title="Inspect Network Topology" @click="inspectNetwork(n.name)">🔍</button>
                    <button class="btn-icon-action btn-delete-peer" :disabled="['bridge', 'host', 'none'].includes(n.name)" title="Remove Network" @click="deleteNetwork(n.name)">✕</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Network Inspector Output Viewport -->
        <div v-if="activeInspect && activeTargetContainer.startsWith('NETWORK:')" class="cyber-card logs-card">
          <div class="card-title-bar">
            <span>🔍 TOPOLOGY DETAILED: {{ activeTargetContainer }}</span>
            <button class="btn-close-logs" @click="closeLogsInspect">✕ CLOSE</button>
          </div>
          <div class="logs-viewport" ref="logsViewport">
            <pre class="logs-pre" v-html="logsOutput"></pre>
          </div>
        </div>
      </div>

      <!-- Right Column: Create Network & Attach/Detach Containers -->
      <div class="docker-right-col">
        <!-- Create Network Card -->
        <div class="cyber-card">
          <div class="card-title-bar">🛠️ CREATE NEW NETWORK</div>
          <div class="specialized-form">
            <div class="form-row">
              <label>Netværk Navn <input v-model="networkForm.name" placeholder="e.g. app-bridge" /></label>
              <label>Driver Type
                <select v-model="networkForm.driver">
                  <option value="bridge">bridge (Local standard)</option>
                  <option value="overlay">overlay (Multi-node swarm)</option>
                  <option value="host">host (Host native)</option>
                  <option value="macvlan">macvlan (Direct NIC hardware)</option>
                  <option value="none">none (Isolated loopback)</option>
                </select>
              </label>
            </div>
            
            <div class="form-row">
              <label>Subnet IP (Optional) <input v-model="networkForm.subnet" placeholder="e.g. 172.20.0.0/16" /></label>
              <label>Gateway IP (Optional) <input v-model="networkForm.gateway" placeholder="e.g. 172.20.0.1" /></label>
            </div>

            <div class="form-row">
              <label>Ekstra Flag (Options) <input v-model="networkForm.options" placeholder="e.g. --internal --attachable" /></label>
            </div>

            <div class="form-row action-row">
              <button class="btn-action btn-apply-docker" :disabled="executing || !networkForm.name" @click="applyCreateNetwork">
                🛠️ CREATE NETWORK
              </button>
            </div>
          </div>
        </div>

        <!-- Attach/Detach Container Card -->
        <div class="cyber-card">
          <div class="card-title-bar">🔗 ATTACH / DETACH CONTAINER</div>
          <div class="specialized-form">
            <div class="form-row">
              <label>Vælg Container
                <select v-model="binderForm.container">
                  <option value="" disabled>-- Vælg en container --</option>
                  <option v-for="c in containers" :key="c.id" :value="c.name">{{ c.name }}</option>
                </select>
              </label>
              
              <label>Vælg Netværk
                <select v-model="binderForm.network">
                  <option value="" disabled>-- Vælg et netværk --</option>
                  <option v-for="n in networks" :key="n.id" :value="n.name">{{ n.name }} ({{ n.driver }})</option>
                </select>
              </label>
            </div>

            <div class="form-row action-row">
              <button class="btn-action btn-preview-docker" :disabled="executing || !binderForm.container || !binderForm.network" @click="controlNetworkBinding('disconnect-network')">
                🔗 DISCONNECT
              </button>
              <button class="btn-action btn-apply-docker" :disabled="executing || !binderForm.container || !binderForm.network" @click="controlNetworkBinding('connect-network')">
                🔗 CONNECT
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: SWARM ORCHESTRATOR -->
    <div v-if="!daemonStatus.includes('not running') && currentTab === 'swarm'" class="docker-dashboard-grid">
      <!-- Left Column: Swarm status HUD & Inactive Setup forms -->
      <div class="docker-left-col">
        <!-- Swarm status -->
        <div class="cyber-card">
          <div class="card-title-bar">
            <span>🐝 SWARM CLUSTER PANEL</span>
            <span class="status-badge" :class="swarmState === 'active' ? 'active' : 'stopped'">
              {{ swarmState ? swarmState : 'INACTIVE' }}
            </span>
          </div>

          <div v-if="swarmState === 'active' && swarmInfo" class="specialized-form" style="padding: 4px;">
            <div class="form-row">
              <label class="font-bold">Swarm Node ID: <span class="mono font-cyan font-small">{{ swarmInfo.NodeID }}</span></label>
            </div>
            <div class="form-row">
              <label class="font-bold">Local Role: <span class="font-white">{{ swarmInfo.ControlPlaneAddr ? 'Manager (Leader)' : 'Worker' }}</span></label>
              <label class="font-bold">Cluster ID: <span class="mono font-cyan font-small">{{ swarmInfo.Cluster?.ID }}</span></label>
            </div>
            <div v-if="swarmInfo.ControlPlaneAddr" class="form-row">
              <label class="font-bold">Control Plane Link: <span class="mono font-green font-small">{{ swarmInfo.ControlPlaneAddr }}</span></label>
            </div>

            <div class="form-row action-row" style="margin-top: 10px;">
              <button class="btn-action btn-danger-outline" :disabled="executing" @click="leaveSwarm">
                🛑 LEAVE SWARM CLUSTER
              </button>
            </div>
          </div>

          <!-- If Inactive state explanation -->
          <div v-else class="empty-list-text" style="padding: 10px 0;">
            Docker Swarm is not enabled on this node. Initialize a new cluster or join an existing swarm below!
          </div>
        </div>

        <!-- Inactive options: Setup swarm -->
        <template v-if="swarmState !== 'active'">
          <!-- Swarm Init Card -->
          <div class="cyber-card">
            <div class="card-title-bar">🐝 INITIALIZE SWARM MANAGER (LEADER)</div>
            <div class="specialized-form">
              <div class="form-row">
                <label>Advertise IP-adresse <input v-model="swarmForm.advertiseAddr" placeholder="e.g. 192.168.1.100" /></label>
                <label>Custom Flags <input v-model="swarmForm.options" placeholder="e.g. --task-history-limit 5" /></label>
              </div>

              <div class="form-row action-row">
                <button class="btn-action btn-apply-docker" :disabled="executing" @click="applySwarmInit">
                  🐝 INITIALIZE SWARM
                </button>
              </div>
            </div>
          </div>

          <!-- Swarm Join Card -->
          <div class="cyber-card">
            <div class="card-title-bar">🐝 JOIN EXISTING SWARM CLUSTER</div>
            <div class="specialized-form">
              <div class="form-row">
                <label>Swarm Join Token <input v-model="swarmForm.token" placeholder="SWMTKN-1-xxxx..." /></label>
              </div>
              <div class="form-row">
                <label>Manager Forbindelsesadresse <input v-model="swarmForm.address" placeholder="e.g. 192.168.1.100:2377" /></label>
              </div>

              <div class="form-row action-row">
                <button class="btn-action btn-apply-docker" :disabled="executing || !swarmForm.token || !swarmForm.address" @click="applySwarmJoin">
                  🐝 JOIN CLUSTER
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Right Column: Swarm nodes list & services (active state only) -->
      <div class="docker-right-col">
        <!-- Swarm Nodes List -->
        <div v-if="swarmState === 'active'" class="cyber-card">
          <div class="card-title-bar">💻 SWARM CLUSTER NODES ({{ swarmNodes.length }})</div>
          
          <div v-if="!swarmNodes.length" class="empty-list-text">
            No node list available. (Ensure this node is a Swarm Manager leader).
          </div>
          <div v-else class="containers-table-wrapper">
            <table class="cyber-table">
              <thead>
                <tr>
                  <th>NODE ID</th>
                  <th>HOSTNAME</th>
                  <th>STATUS</th>
                  <th>AVAILABILITY</th>
                  <th>ROLE</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="node in swarmNodes" :key="node.id" class="container-row">
                  <td class="mono font-cyan font-small">{{ node.id }}</td>
                  <td class="font-white font-bold">{{ node.hostname }}</td>
                  <td>
                    <span class="status-badge" :class="node.status.toLowerCase() === 'ready' ? 'active' : 'stopped'">
                      {{ node.status }}
                    </span>
                  </td>
                  <td class="mono font-gray font-small">{{ node.availability }}</td>
                  <td class="mono font-green font-small">{{ node.managerStatus }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Swarm Services Registry -->
        <div v-if="swarmState === 'active'" class="cyber-card">
          <div class="card-title-bar">📦 ACTIVE SWARM SERVICES ({{ swarmServices.length }})</div>
          
          <div v-if="!swarmServices.length" class="empty-list-text">
            No active Swarm services found. Deploy services via terminal to populate!
          </div>
          <div v-else class="containers-table-wrapper">
            <table class="cyber-table">
              <thead>
                <tr>
                  <th>SERVICE ID</th>
                  <th>NAME</th>
                  <th>MODE</th>
                  <th>REPLICAS</th>
                  <th>IMAGE</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in swarmServices" :key="s.id" class="container-row">
                  <td class="mono font-cyan font-small">{{ s.id }}</td>
                  <td class="font-white font-bold">{{ s.name }}</td>
                  <td class="mono font-gray font-small">{{ s.mode }}</td>
                  <td class="mono font-green font-small">{{ s.replicas }}</td>
                  <td class="mono font-gray font-small">{{ s.image }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    <!-- TAB 4: COMPOSE MANAGER -->
    <div v-if="!daemonStatus.includes('not running') && currentTab === 'compose'" class="docker-dashboard-grid">
      <!-- Left Column: Compose file loader & YAML editor -->
      <div class="docker-left-col">
        <div class="cyber-card">
          <div class="card-title-bar">
            <span>🐙 DOCKER COMPOSE FILE MANAGER</span>
            <span v-if="composeFileContent !== composeOriginalContent" class="status-badge stopped">UNSAVED CHANGES</span>
            <span v-else class="status-badge active">SAVED</span>
          </div>

          <div class="specialized-form">
            <div class="form-row">
              <label style="flex: 2;">Compose Filsti (Node)
                <input v-model="composeFilePath" placeholder="e.g. /home/aso/docker-compose.yml" />
              </label>
              <div style="display: flex; align-items: flex-end;">
                <button class="btn-action btn-apply-docker" :disabled="loadingComposeFile || executing" @click="loadComposeFile" style="height: 33px; font-size: 8.5px; padding: 0 16px;">
                  {{ loadingComposeFile ? '⏳ HENTER...' : '📥 HENT COMPOSE FIL' }}
                </button>
              </div>
            </div>

            <!-- YAML Code Editor Viewport (CRT Monitor phosphor style) -->
            <div class="form-row" style="flex-direction: column; gap: 6px;">
              <label>Compose YAML Indhold</label>
              <textarea 
                v-model="composeFileContent" 
                class="preview-pre font-green mono" 
                placeholder="# Paste your docker-compose.yml file here..." 
                style="width: 100%; height: 350px; resize: vertical; border: 1px solid var(--border); font-size: 11px; outline: none; background: radial-gradient(circle at center, rgba(6, 10, 22, 0.9) 0%, rgba(2, 4, 8, 0.96) 100%); color: var(--green); box-shadow: inset 0 0 10px rgba(0,0,0,0.8);"
              ></textarea>
            </div>

            <div class="form-row action-row" style="gap: 12px;">
              <button class="btn-action btn-danger-outline" :disabled="!composeFilePath || loadingComposeFile || executing" @click="deleteComposeFile">
                🗑️ SLET FIL
              </button>
              <button class="btn-action btn-apply-docker" :disabled="!composeFilePath || loadingComposeFile || executing" @click="saveComposeFile">
                💾 GEM FIL PÅ NODE
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Actions Chassis Panel & CRT Output Viewport -->
      <div class="docker-right-col">
        <div class="cyber-card">
          <div class="card-title-bar">🎛️ COMPOSE LIFECYCLE CONTROLS</div>
          
          <div class="specialized-form" style="padding: 4px; gap: 10px;">
            <div class="form-row" style="flex-wrap: wrap; gap: 8px;">
              <button class="btn-action-sm btn-apply-docker" :disabled="executingCompose || executing || !composeFilePath" @click="runComposeCommand('up')" title="docker compose up -d" style="flex: 1; min-width: 100px;">
                🚀 COMPOSE UP
              </button>
              <button class="btn-action-sm btn-danger-outline" :disabled="executingCompose || executing || !composeFilePath" @click="runComposeCommand('down')" title="docker compose down" style="flex: 1; min-width: 100px;">
                🛑 COMPOSE DOWN
              </button>
            </div>
            
            <div class="form-row" style="flex-wrap: wrap; gap: 8px;">
              <button class="btn-action-sm" :disabled="executingCompose || executing || !composeFilePath" @click="runComposeCommand('restart')" title="docker compose restart" style="flex: 1; min-width: 100px; border-color: var(--orange); color: var(--orange);">
                🔄 RESTART
              </button>
              <button class="btn-action-sm" :disabled="executingCompose || executing || !composeFilePath" @click="runComposeCommand('build')" title="docker compose build" style="flex: 1; min-width: 100px; border-color: var(--cyan); color: var(--cyan);">
                🛠️ BUILD
              </button>
            </div>

            <div class="form-row" style="flex-wrap: wrap; gap: 8px;">
              <button class="btn-action-sm btn-fullscreen" :disabled="executingCompose || executing || !composeFilePath" @click="runComposeCommand('ps')" title="docker compose ps" style="flex: 1; min-width: 100px;">
                📊 COMPOSE PS
              </button>
              <button class="btn-action-sm btn-fullscreen" :disabled="executingCompose || executing || !composeFilePath" @click="runComposeCommand('logs')" title="docker compose logs --tail=100" style="flex: 1; min-width: 100px;">
                📟 VIEW LOGS
              </button>
            </div>
          </div>
        </div>

        <!-- CRT Terminal Viewport for Output Logs -->
        <div class="cyber-card logs-card" style="flex: 1; display: flex; flex-direction: column;">
          <div class="card-title-bar">
            <span>📟 COMPOSE TERMINAL OUTPUT</span>
            <span v-if="executingCompose" class="pulse-indicator active"></span>
          </div>
          <div class="logs-viewport" style="flex: 1; min-height: 220px; max-height: 380px;">
            <pre class="logs-pre"><code class="mono">{{ composeOutput || 'Klar til at modtage kommandooutput...\n\nVælg en Compose-handling ovenfor for at diagnosticere klyngen.' }}</code></pre>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 5: TELEMETRY DASHBOARD -->
    <div v-if="!daemonStatus.includes('not running') && currentTab === 'telemetry'" class="docker-dashboard-grid" style="display: flex; flex-direction: column;">
      <div class="cyber-card" style="flex: 1; min-height: 250px;">
        <div class="card-title-bar">⚡ CPU USAGE (%)</div>
        <DockerChart title="CPU Usage" :datasets="cpuDatasets" />
      </div>
      <div class="cyber-card" style="flex: 1; min-height: 250px;">
        <div class="card-title-bar">💾 RAM USAGE (MB)</div>
        <DockerChart title="RAM Usage" :datasets="ramDatasets" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { api } from '@/api/client'
import DockerChart from './DockerChart.vue'

const props = defineProps<{ nodeId: string }>()

// Sub-Tab Selector State
const currentTab = ref('containers')

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

// Resizable columns
let startX = 0
let startWidth = 0
let activeColIdx = -1

function startResize(e: MouseEvent, index: number) {
  e.preventDefault()
  activeColIdx = index
  startX = e.clientX
  
  const handle = e.currentTarget as HTMLElement
  const th = handle.parentElement as HTMLTableCellElement
  startWidth = th.offsetWidth
  
  window.addEventListener('mousemove', handleResize)
  window.addEventListener('mouseup', stopResize)
}

function handleResize(e: MouseEvent) {
  if (activeColIdx === -1) return
  const diff = e.clientX - startX
  const newWidth = Math.max(60, startWidth + diff)
  
  const ths = document.querySelectorAll('.containers-table-wrapper th') as NodeListOf<HTMLTableCellElement>
  if (ths && ths[activeColIdx]) {
    ths[activeColIdx].style.width = `${newWidth}px`
    ths[activeColIdx].style.minWidth = `${newWidth}px`
  }
}

function stopResize() {
  activeColIdx = -1
  window.removeEventListener('mousemove', handleResize)
  window.removeEventListener('mouseup', stopResize)
}

// Add/Remove Native Fullscreen event listeners
onMounted(() => {
  document.addEventListener('fullscreenchange', handleNativeFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleNativeFullscreenChange)
})

const loading = ref(false)
const executing = ref(false)
const error = ref('')

const daemonStatus = ref('')
const daemonInfo = ref('')
const containers = ref<any[]>([])
const stats = ref<Record<string, any>>({})
const networks = ref<any[]>([])
const images = ref<any[]>([])

// Swarm States
const swarmInfo = ref<any>(null)
const swarmState = ref('')
const swarmNodes = ref<any[]>([])
const swarmServices = ref<any[]>([])

// Compose States
const composeFilePath = ref('/home/aso/docker-compose.yml')
const composeFileContent = ref('')
const composeOriginalContent = ref('')
const loadingComposeFile = ref(false)
const executingCompose = ref(false)
const composeOutput = ref('')

const activeLogs = ref(false)
const activeInspect = ref(false)
const activeTargetContainer = ref('')
const logsOutput = ref('')
const logsViewport = ref<HTMLElement | null>(null)

// Forms Models
const runForm = ref({
  action: 'run',
  name: '',
  image: '',
  ports: '',
  volumes: '',
  env: '',
  options: ''
})

const networkForm = ref({
  action: 'create-network',
  name: '',
  driver: 'bridge',
  subnet: '',
  gateway: '',
  options: ''
})

const binderForm = ref({
  container: '',
  network: '',
  action: 'connect-network'
})

const swarmForm = ref({
  action: 'swarm-init',
  advertiseAddr: '',
  token: '',
  address: '',
  options: ''
})

const previewCommands = ref<string[]>([])

// Telemetry refresh polling timer
let pollTimer: ReturnType<typeof setInterval> | null = null

function parseRamPercent(memStr: string): string {
  if (!memStr) return '0%'
  const parts = memStr.split('/')
  if (parts.length < 2) return '0%'
  
  const parseVal = (s: string) => {
    const num = parseFloat(s.replace(/[^0-9.]/g, ''))
    if (isNaN(num)) return 0
    if (s.toLowerCase().includes('gib') || s.toLowerCase().includes('gb')) return num * 1024
    if (s.toLowerCase().includes('kib') || s.toLowerCase().includes('kb')) return num / 1024
    return num
  }
  
  const used = parseVal(parts[0])
  const limit = parseVal(parts[1])
  if (!limit) return '0%'
  return `${Math.min(100, Math.round((used / limit) * 100))}%`
}

// Parsers
function parseContainers(output: string) {
  if (!output || output.includes('No containers') || output.includes('not running') || output.includes('not installed')) {
    return []
  }
  const lines = output.trim().split('\n').filter(l => l.trim() !== '')
  if (lines.length < 2) return []
  
  const list = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split('\t').map(c => c.trim())
    if (cols.length >= 4) {
      list.push({
        id: cols[0],
        name: cols[1],
        image: cols[2],
        status: cols[3],
        ports: cols[4] || '(None)'
      })
    }
  }
  return list
}

function parseStats(output: string) {
  if (!output || output.includes('Stats unavailable') || output.includes('not running')) {
    return {}
  }
  const lines = output.trim().split('\n').filter(l => l.trim() !== '')
  const statsMap: Record<string, any> = {}
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split('\t').map(c => c.trim())
    if (cols.length >= 5) {
      statsMap[cols[0]] = {
        name: cols[1],
        cpu: cols[2],
        mem: cols[3],
        net: cols[4]
      }
    }
  }
  return statsMap
}

function parseNetworks(output: string) {
  if (!output || output.includes('Networks unavailable')) return []
  const lines = output.trim().split('\n').filter(l => l.trim() !== '')
  const list = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split('\t').map(c => c.trim())
    if (cols.length >= 3) {
      list.push({ id: cols[0], name: cols[1], driver: cols[2] })
    }
  }
  return list
}

function parseImages(output: string) {
  if (!output || output.includes('Images unavailable')) return []
  const lines = output.trim().split('\n').filter(l => l.trim() !== '')
  const list = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split('\t').map(c => c.trim())
    if (cols.length >= 3) {
      list.push({ repository: cols[0], tag: cols[1], size: cols[2] })
    }
  }
  return list
}

function parseSwarmInfo(output: string) {
  if (!output || output.includes('unavailable') || output.includes('not running') || output.includes('Error')) {
    return null
  }
  try {
    const start = output.indexOf('{')
    const end = output.lastIndexOf('}')
    if (start !== -1 && end !== -1) {
      const jsonStr = output.substring(start, end + 1)
      return JSON.parse(jsonStr)
    }
  } catch {
    // silent fallback
  }
  return null
}

function parseSwarmNodes(output: string) {
  if (!output || output.includes('unavailable') || output.includes('not running') || output.includes('Error') || output.includes('not a swarm manager')) {
    return []
  }
  const lines = output.trim().split('\n').filter(l => l.trim() !== '')
  if (lines.length < 2) return []
  const list = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split('\t').map(c => c.trim())
    if (cols.length >= 4) {
      list.push({
        id: cols[0],
        hostname: cols[1],
        status: cols[2],
        availability: cols[3],
        managerStatus: cols[4] || '(Worker)'
      })
    }
  }
  return list
}

function parseSwarmServices(output: string) {
  if (!output || output.includes('unavailable') || output.includes('not running') || output.includes('Error') || output.includes('not a swarm manager')) {
    return []
  }
  const lines = output.trim().split('\n').filter(l => l.trim() !== '')
  if (lines.length < 2) return []
  const list = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split('\t').map(c => c.trim())
    if (cols.length >= 4) {
      list.push({
        id: cols[0],
        name: cols[1],
        mode: cols[2],
        replicas: cols[3],
        image: cols[4] || '(None)'
      })
    }
  }
  return list
}

// Actions
async function refreshDocker() {
  if (!props.nodeId) return
  loading.value = true
  error.value = ''
  try {
    const res = await api.readNode(props.nodeId, 'docker')
    const results = res.results || []
    
    // Command 1: Info & Daemon State
    daemonStatus.value = results[0]?.output || ''
    daemonInfo.value = results[0]?.output || ''
    
    // Command 2: Container List
    containers.value = parseContainers(results[1]?.output || '')
    
    // Command 3: Stats
    stats.value = parseStats(results[2]?.output || '')
    
    // Command 4: Networks
    networks.value = parseNetworks(results[3]?.output || '')
    
    // Command 5: Images
    images.value = parseImages(results[4]?.output || '')

    // Command 6: Swarm Info
    swarmInfo.value = parseSwarmInfo(results[5]?.output || '')
    if (swarmInfo.value && swarmInfo.value.LocalNodeState) {
      swarmState.value = swarmInfo.value.LocalNodeState.toLowerCase()
    } else {
      swarmState.value = 'inactive'
    }

    // Command 7: Swarm Nodes
    swarmNodes.value = parseSwarmNodes(results[6]?.output || '')

    // Command 8: Swarm Services
    swarmServices.value = parseSwarmServices(results[7]?.output || '')
  } catch (err: any) {
    error.value = String(err.message || err)
    daemonStatus.value = 'not running'
  } finally {
    loading.value = false
  }
}

// Telemetry Logic
interface Point { time: number; value: number }
interface TelemetryHistory { cpu: Point[]; ram: Point[] }
const telemetryData = ref<Record<string, TelemetryHistory>>({})
const containerColors = ref<Record<string, string>>({})
const availableColors = ['#00ff9d', '#ff003c', '#00e5ff', '#ff00ff', '#ffb700', '#0055ff', '#b700ff']

function assignColor(id: string) {
  if (!containerColors.value[id]) {
    const color = availableColors[Object.keys(containerColors.value).length % availableColors.length]
    containerColors.value[id] = color
  }
  return containerColors.value[id]
}

function parseNumber(str: string): number {
  if (!str) return 0
  const val = parseFloat(str.replace(/[^0-9.]/g, ''))
  if (isNaN(val)) return 0
  if (str.toLowerCase().includes('gib') || str.toLowerCase().includes('gb')) return val * 1024
  if (str.toLowerCase().includes('kib') || str.toLowerCase().includes('kb')) return val / 1024
  if (str.toLowerCase().includes('mib') || str.toLowerCase().includes('mb')) return val
  return val
}

watch(() => stats.value, (newStats) => {
  if (currentTab.value !== 'telemetry') return
  const now = Math.floor(Date.now() / 1000)
  for (const [id, s] of Object.entries(newStats)) {
    if (!telemetryData.value[id]) telemetryData.value[id] = { cpu: [], ram: [] }
    assignColor(id)
    
    telemetryData.value[id].cpu.push({ time: now, value: parseFloat(s.cpu) || 0 })
    
    const memStr = s.mem.split('/')[0] || ''
    telemetryData.value[id].ram.push({ time: now, value: parseNumber(memStr) })
    
    if (telemetryData.value[id].cpu.length > 30) {
      telemetryData.value[id].cpu.shift()
      telemetryData.value[id].ram.shift()
    }
  }
}, { deep: true })

const cpuDatasets = computed(() => {
  return Object.entries(telemetryData.value).map(([id, hist]) => ({
    label: stats.value[id]?.name || id,
    color: containerColors.value[id],
    dataPoints: hist.cpu
  }))
})

const ramDatasets = computed(() => {
  return Object.entries(telemetryData.value).map(([id, hist]) => ({
    label: stats.value[id]?.name || id,
    color: containerColors.value[id],
    dataPoints: hist.ram
  }))
})

// --- Docker Compose Functions ---
async function loadComposeFile() {
  if (!composeFilePath.value) return
  loadingComposeFile.value = true
  composeOutput.value = ''
  try {
    const res = await api.executeNode(props.nodeId, [`cat ${composeFilePath.value}`])
    const r = res.results?.[0]
    const hasCatError = r?.output && (
      r.output.includes('No such file') ||
      r.output.startsWith('cat:') ||
      r.output.toLowerCase().includes('permission denied') ||
      r.output.toLowerCase().includes('no matches found')
    )
    if (r && !r.error && !hasCatError) {
      composeFileContent.value = r.output || ''
      composeOriginalContent.value = r.output || ''
      composeOutput.value = `[SUCCESS] Fil hentet succesfuldt fra node: ${composeFilePath.value}`
    } else {
      // If file doesn't exist, start with a template
      composeFileContent.value = `services:\n  node-red:\n    image: nodered/node-red:latest\n    ports:\n      - "1880:1880"\n    volumes:\n      - node-red-data:/data\n\nvolumes:\n  node-red-data:\n`
      composeOriginalContent.value = ''
      const errorDetail = r?.output || r?.error || 'Filen eksisterer ikke eller er tom'
      composeOutput.value = `[INFO] Filen blev ikke fundet eller er tom. Initialiseret standardskabelon for ${composeFilePath.value}.\nBesked: ${errorDetail.trim()}`
    }
  } catch (err: any) {
    composeOutput.value = `[ERROR] Kunne ikke hente fil: ${err.message || err}`
  } finally {
    loadingComposeFile.value = false
  }
}

async function saveComposeFile() {
  if (!composeFilePath.value) return
  executing.value = true
  composeOutput.value = 'Gemmer fil...'
  try {
    const data = {
      path: composeFilePath.value,
      content: composeFileContent.value,
      mode: '644',
      owner: 'root',
      backup: true
    }
    const previewRes = await api.preview('file-write', data)
    const cmds = previewRes.commands
    const res = await api.executeNode(props.nodeId, cmds)
    const r = res.results?.[0]
    if (r && !r.error) {
      composeOriginalContent.value = composeFileContent.value
      composeOutput.value = `[SUCCESS] Filen er blevet gemt succesfuldt på noden: ${composeFilePath.value}`
    } else {
      composeOutput.value = `[ERROR] Kunne ikke gemme filen: ${r?.error || 'Ingen output'}`
    }
  } catch (err: any) {
    composeOutput.value = `[ERROR] Kunne ikke gemme: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function deleteComposeFile() {
  if (!composeFilePath.value) return
  if (!confirm(`Er du sikker på, at du vil slette compose-filen på stien "${composeFilePath.value}"?`)) return
  if (!confirm(`SLETNINGSBEKRÆFTELSE: Dette vil permanent fjerne filen fra remote noden. Fortsæt?`)) return
  executing.value = true
  composeOutput.value = 'Sletter fil...'
  try {
    const cmd = `rm -f ${composeFilePath.value}`
    const res = await api.executeNode(props.nodeId, [cmd])
    const r = res.results?.[0]
    if (r && !r.error) {
      composeFileContent.value = ''
      composeOriginalContent.value = ''
      composeOutput.value = `[SUCCESS] Filen blev slettet permanent: ${composeFilePath.value}`
    } else {
      composeOutput.value = `[ERROR] Kunne ikke slette filen: ${r?.error || 'Ingen output'}`
    }
  } catch (err: any) {
    composeOutput.value = `[ERROR] Kunne ikke slette: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function runComposeCommand(action: string) {
  if (!composeFilePath.value) return
  executingCompose.value = true
  composeOutput.value = `Udfører "docker compose ${action}" på noden...\n\n`
  try {
    let cmd = ''
    if (action === 'up') {
      cmd = `docker compose -f ${composeFilePath.value} up -d --remove-orphans 2>&1 || sudo -n docker compose -f ${composeFilePath.value} up -d --remove-orphans 2>&1`
    } else if (action === 'down') {
      cmd = `docker compose -f ${composeFilePath.value} down 2>&1 || sudo -n docker compose -f ${composeFilePath.value} down 2>&1`
    } else if (action === 'restart') {
      cmd = `docker compose -f ${composeFilePath.value} restart 2>&1 || sudo -n docker compose -f ${composeFilePath.value} restart 2>&1`
    } else if (action === 'build') {
      cmd = `docker compose -f ${composeFilePath.value} build 2>&1 || sudo -n docker compose -f ${composeFilePath.value} build 2>&1`
    } else if (action === 'ps') {
      cmd = `docker compose -f ${composeFilePath.value} ps -a 2>&1 || sudo -n docker compose -f ${composeFilePath.value} ps -a 2>&1`
    } else if (action === 'logs') {
      cmd = `docker compose -f ${composeFilePath.value} logs --tail=100 2>&1 || sudo -n docker compose -f ${composeFilePath.value} logs --tail=100 2>&1`
    }
    
    const res = await api.executeNode(props.nodeId, [cmd])
    const r = res.results?.[0]
    
    if (r) {
      composeOutput.value += r.output || '(Intet output modtaget)'
      if (r.error) {
        composeOutput.value += `\n\n[FEJL UNDER UDFØRELSE]\n${r.error}`
      }
    }
    // Auto refresh docker after up/down actions
    if (action === 'up' || action === 'down' || action === 'restart') {
      await refreshDocker()
    }
  } catch (err: any) {
    composeOutput.value += `\n\n[EXECUTION ERROR] ${err.message || err}`
  } finally {
    executingCompose.value = false
  }
}

async function controlContainer(name: string, action: string) {
  if (!confirm(`Vil du udføre handlingen "${action.toUpperCase()}" på containeren "${name}"?`)) return
  executing.value = true
  error.value = ''
  try {
    const previewRes = await api.preview('docker', { name, action })
    const cmds = previewRes.commands
    await api.executeNode(props.nodeId, cmds)
    await refreshDocker()
  } catch (err: any) {
    error.value = `Fejl under ${action}: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function runPrune() {
  if (!confirm("Vil du rydde op i Docker? Dette sletter permanent alle stoppede containere, ubrugte netværk og ubenyttede images!")) return
  executing.value = true
  error.value = ''
  try {
    const previewRes = await api.preview('docker', { action: 'prune' })
    await api.executeNode(props.nodeId, previewRes.commands)
    await refreshDocker()
  } catch (err: any) {
    error.value = `Fejl under Prune: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function viewLogs(name: string) {
  activeLogs.value = true
  activeInspect.value = false
  activeTargetContainer.value = name
  logsOutput.value = 'Henter logs...'
  
  try {
    const res = await api.executeNode(props.nodeId, [`docker logs --tail 150 "${name}" 2>&1`])
    const out = res.results?.[0]?.output || res.results?.[0]?.error || '(Ingen log output fundet)'
    logsOutput.value = out
    nextTick(() => {
      if (logsViewport.value) {
        logsViewport.value.scrollTop = logsViewport.value.scrollHeight
      }
    })
  } catch (err: any) {
    logsOutput.value = `Fejl under hentning af logs: ${err.message || err}`
  }
}

async function inspectContainer(name: string) {
  activeLogs.value = false
  activeInspect.value = true
  activeTargetContainer.value = name
  logsOutput.value = 'Henter inspektion...'
  
  try {
    const res = await api.executeNode(props.nodeId, [`docker inspect "${name}"`])
    const out = res.results?.[0]?.output || '(Ingen data fundet)'
    logsOutput.value = out
  } catch (err: any) {
    logsOutput.value = `Fejl under inspektion: ${err.message || err}`
  }
}

function closeLogsInspect() {
  activeLogs.value = false
  activeInspect.value = false
  activeTargetContainer.value = ''
  logsOutput.value = ''
}

// Network actions
async function inspectNetwork(name: string) {
  activeLogs.value = false
  activeInspect.value = true
  activeTargetContainer.value = `NETWORK: ${name}`
  logsOutput.value = 'Inspektion af netværk indlæses...'
  
  try {
    const res = await api.executeNode(props.nodeId, [`docker network inspect "${name}"`])
    const out = res.results?.[0]?.output || '(Ingen netværksdata fundet)'
    logsOutput.value = out
  } catch (err: any) {
    logsOutput.value = `Fejl under netværksinspektion: ${err.message || err}`
  }
}

async function deleteNetwork(name: string) {
  if (!confirm(`Vil du permanent slette netværket "${name}"? Det kan kun lade sig gøre, hvis ingen containere er tilsluttet.`)) return
  executing.value = true
  error.value = ''
  try {
    const res = await api.preview('docker', { action: 'delete-network', name })
    await api.executeNode(props.nodeId, res.commands)
    await refreshDocker()
  } catch (err: any) {
    error.value = `Fejl under sletning af netværk: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function applyCreateNetwork() {
  executing.value = true
  error.value = ''
  try {
    const res = await api.preview('docker', networkForm.value)
    await api.executeNode(props.nodeId, res.commands)
    
    // reset form
    networkForm.value = {
      action: 'create-network',
      name: '',
      driver: 'bridge',
      subnet: '',
      gateway: '',
      options: ''
    }
    
    await refreshDocker()
  } catch (err: any) {
    error.value = `Kunne ikke oprette netværk: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function controlNetworkBinding(action: 'connect-network' | 'disconnect-network') {
  const container = binderForm.value.container
  const network = binderForm.value.network
  
  executing.value = true
  error.value = ''
  try {
    const res = await api.preview('docker', {
      action,
      name: network,
      container
    })
    await api.executeNode(props.nodeId, res.commands)
    
    // reset binder
    binderForm.value.container = ''
    binderForm.value.network = ''
    
    await refreshDocker()
  } catch (err: any) {
    error.value = `Netværksbinding fejlede: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

// Swarm Actions
async function applySwarmInit() {
  executing.value = true
  error.value = ''
  try {
    const res = await api.preview('docker', {
      action: 'swarm-init',
      advertiseAddr: swarmForm.value.advertiseAddr,
      options: swarmForm.value.options
    })
    await api.executeNode(props.nodeId, res.commands)
    
    // reset init fields
    swarmForm.value.advertiseAddr = ''
    swarmForm.value.options = ''
    
    await refreshDocker()
  } catch (err: any) {
    error.value = `Kunne ikke initialisere Swarm: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function applySwarmJoin() {
  executing.value = true
  error.value = ''
  try {
    const res = await api.preview('docker', {
      action: 'swarm-join',
      token: swarmForm.value.token,
      address: swarmForm.value.address
    })
    await api.executeNode(props.nodeId, res.commands)
    
    // reset join fields
    swarmForm.value.token = ''
    swarmForm.value.address = ''
    
    await refreshDocker()
  } catch (err: any) {
    error.value = `Kunne ikke tilslutte Swarm kluster: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function leaveSwarm() {
  if (!confirm("Er du sikker på, at du vil forlade Swarm klustret på denne node? Det kan forstyrre aktive swarm services.")) return
  executing.value = true
  error.value = ''
  try {
    const res = await api.preview('docker', { action: 'swarm-leave', force: true })
    await api.executeNode(props.nodeId, res.commands)
    await refreshDocker()
  } catch (err: any) {
    error.value = `Fejl under fjernelse af Swarm: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

// Launch forms
async function previewRun() {
  previewCommands.value = []
  error.value = ''
  try {
    const res = await api.preview('docker', runForm.value)
    previewCommands.value = res.commands
  } catch (err: any) {
    error.value = `Preview fejl: ${err.message || err}`
  }
}

async function applyRun() {
  executing.value = true
  error.value = ''
  try {
    const res = await api.preview('docker', runForm.value)
    previewCommands.value = res.commands
    await api.executeNode(props.nodeId, res.commands)
    
    // Clear form
    runForm.value = {
      action: 'run',
      name: '',
      image: '',
      ports: '',
      volumes: '',
      env: '',
      options: ''
    }
    previewCommands.value = []
    
    await refreshDocker()
  } catch (err: any) {
    error.value = `Kunne ikke starte container: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

async function installDocker() {
  executing.value = true
  error.value = ''
  try {
    const cmd = "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    await api.executeNode(props.nodeId, [cmd])
    // Wait a couple of seconds for the daemon to start properly
    await new Promise(r => setTimeout(r, 4000))
    await refreshDocker()
  } catch (err: any) {
    error.value = `Fejl under installation af Docker: ${err.message || err}`
  } finally {
    executing.value = false
  }
}

// Watch nodeId to refresh telemetry and clear logs overlay
watch(() => props.nodeId, () => {
  closeLogsInspect()
  previewCommands.value = []
  currentTab.value = 'containers' // reset tab on node switch
  
  // Clear compose states
  composeFileContent.value = ''
  composeOriginalContent.value = ''
  composeOutput.value = ''
  
  refreshDocker()
}, { immediate: true })

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// Poll container metrics every 8 seconds
pollTimer = setInterval(() => {
  if (!loading.value && !executing.value) {
    refreshDocker()
  }
}, 8000)
</script>

<style scoped>
.docker-panel-container {
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
  background: rgba(8, 16, 32, 0.75);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 16px;
  margin-bottom: 20px;
  box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.05);
  backdrop-filter: blur(8px);
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

/* ═══════════════════════════════════════════════════════════════
   SUB-CONTROLS BANNER
   ═══════════════════════════════════════════════════════════════ */
.panel-header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(13, 20, 38, 0.45);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.02);
}

.active-node-badge {
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 1.5px;
  color: var(--cyan);
  font-weight: 700;
  text-transform: uppercase;
  text-shadow: 0 0 6px rgba(0, 229, 255, 0.35);
}

.controls-group {
  display: flex;
  gap: 12px;
}

.btn-action-sm {
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--border);
  color: var(--textwh);
  padding: 6px 14px;
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.2px;
  border-radius: 4px;
  cursor: pointer;
  text-transform: uppercase;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-action-sm:hover:not(:disabled) {
  border-color: var(--cyan);
  color: #fff;
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3), inset 0 0 5px rgba(0, 229, 255, 0.1);
  transform: translateY(-1px);
}

.btn-danger-outline {
  border-color: rgba(255, 45, 110, 0.3);
  color: var(--pink);
}

.btn-danger-outline:hover:not(:disabled) {
  border-color: var(--pink) !important;
  color: #fff !important;
  background: rgba(255, 45, 110, 0.15) !important;
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.3) !important;
}

.btn-fullscreen {
  border-color: rgba(0, 229, 255, 0.3);
  color: var(--cyan);
}

.btn-fullscreen:hover {
  border-color: var(--cyan) !important;
  color: #fff !important;
  background: rgba(0, 229, 255, 0.15) !important;
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.4) !important;
}

/* ═══════════════════════════════════════════════════════════════
   DASHBOARD GRID LAYOUT
   ═══════════════════════════════════════════════════════════════ */
.docker-dashboard-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
  margin-top: 10px;
}

.docker-left-col, .docker-right-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.docker-sub-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* ═══════════════════════════════════════════════════════════════
   OFFLINE CARD & EMPTY STATES
   ═══════════════════════════════════════════════════════════════ */
.daemon-offline-card {
  padding: 24px;
  background: rgba(255, 45, 110, 0.05);
  border: 1px dashed var(--pink);
  border-radius: 6px;
  font-family: var(--font-ui);
  box-shadow: 0 0 15px rgba(255, 45, 110, 0.08), inset 0 0 10px rgba(255, 45, 110, 0.05);
}

.warning-header {
  font-family: var(--font-hd);
  font-size: 14px;
  font-weight: 700;
  color: var(--pink);
  margin-bottom: 8px;
  letter-spacing: 1px;
  text-shadow: 0 0 8px rgba(255, 45, 110, 0.4);
}

.empty-list-text {
  padding: 30px;
  text-align: center;
  font-family: var(--font-ui);
  color: var(--text);
  font-size: 0.9rem;
  line-height: 1.6;
}

/* ═══════════════════════════════════════════════════════════════
   CYBER CARD SYSTEM WITH BRACKETS
   ═══════════════════════════════════════════════════════════════ */
.cyber-card {
  position: relative;
  background: rgba(8, 14, 26, 0.65) !important;
  backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(0, 229, 255, 0.15) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6) !important;
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
}

.cyber-card:hover {
  border-color: rgba(0, 229, 255, 0.25) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 15px rgba(0, 229, 255, 0.05) !important;
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
   PREMIUM CYBER TABLE
   ═══════════════════════════════════════════════════════════════ */
.containers-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: rgba(4, 7, 14, 0.4);
}

.cyber-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.cyber-table th {
  background: rgba(13, 20, 38, 0.7);
  border-bottom: 2px solid var(--cyan);
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 1px;
  padding: 10px 14px;
  font-weight: 700;
  text-shadow: 0 0 4px rgba(0, 229, 255, 0.3);
  position: relative;
}

.cyber-table td {
  padding: 10px 14px;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
  transition: background 0.2s;
}

.container-row {
  transition: all 0.2s;
}

.container-row:hover {
  background: rgba(0, 229, 255, 0.03) !important;
}

.container-row.stopped {
  background: rgba(255, 45, 110, 0.01);
  opacity: 0.7;
}

/* ═══════════════════════════════════════════════════════════════
   HIGH-TECH MONOSPACE TYPOGRAPHY & BADGES
   ═══════════════════════════════════════════════════════════════ */
.mono {
  font-family: var(--font-co);
}

.font-cyan {
  color: var(--cyan) !important;
}

.font-white {
  color: var(--textwh) !important;
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

.status-badge {
  font-size: 8px;
  font-family: var(--font-hd);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  padding: 3px 8px;
  border-radius: 3px;
  display: inline-block;
  box-shadow: 0 0 6px currentColor;
}

.status-badge.active {
  background: rgba(0, 255, 157, 0.08);
  border: 1px solid var(--green);
  color: var(--green);
}

.status-badge.stopped {
  background: rgba(255, 45, 110, 0.08);
  border: 1px solid var(--pink);
  color: var(--pink);
}

.stats-badge-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0;
}

/* ═══════════════════════════════════════════════════════════════
   HUD METERS & RESOURCE TELEMETRY
   ═══════════════════════════════════════════════════════════════ */
.stats-meter {
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 100%;
  min-width: 110px;
}

.meter-label {
  font-size: 8px;
  font-family: var(--font-co);
  color: var(--textbr);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.meter-bar {
  width: 100%;
  height: 5px;
  background: rgba(26, 37, 64, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 3px;
  overflow: hidden;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.5);
}

.meter-fill {
  height: 100%;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.cpu-fill {
  background: var(--green, #00ff9d) !important;
  box-shadow: 0 0 8px var(--green, #00ff9d);
}

.ram-fill {
  background: var(--cyan, #00e5ff) !important;
  box-shadow: 0 0 8px var(--cyan, #00e5ff);
}

.net-io-label {
  font-size: 8.5px;
  color: var(--textbr);
  font-family: var(--font-co);
  margin-top: 2px;
  opacity: 0.8;
  letter-spacing: 0.5px;
}

/* ═══════════════════════════════════════════════════════════════
   ACTION BUTTONS & CELL LAYOUTS
   ═══════════════════════════════════════════════════════════════ */
.actions-cell {
  display: flex;
  gap: 6px;
}

.btn-icon-action {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--border);
  color: var(--textwh);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-icon-action:hover {
  border-color: var(--cyan);
  color: #fff;
  background: rgba(0, 229, 255, 0.15);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
  transform: translateY(-1px);
}

.btn-stop:hover {
  border-color: var(--orange) !important;
  color: #fff !important;
  background: rgba(255, 107, 53, 0.2) !important;
  box-shadow: 0 0 8px rgba(255, 107, 53, 0.4) !important;
}

.btn-delete-peer:hover {
  border-color: var(--pink) !important;
  color: #fff !important;
  background: rgba(255, 45, 110, 0.2) !important;
  box-shadow: 0 0 8px rgba(255, 45, 110, 0.4) !important;
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

.btn-preview-docker {
  background: rgba(16, 24, 40, 0.6);
  border: 1px solid var(--orange);
  color: var(--orange);
}

.btn-preview-docker:hover:not(:disabled) {
  background: rgba(255, 107, 53, 0.15) !important;
  color: #fff !important;
  box-shadow: 0 0 12px rgba(255, 107, 53, 0.4);
}

.btn-apply-docker {
  background: var(--green) !important;
  border: 1px solid var(--green) !important;
  color: #05080f !important;
  box-shadow: 0 0 8px rgba(0, 255, 157, 0.25);
}

.btn-apply-docker:hover:not(:disabled) {
  background: #fff !important;
  color: #05080f !important;
  box-shadow: 0 0 18px var(--green);
}

.btn-apply-docker:disabled {
  background: rgba(26, 37, 64, 0.3) !important;
  border-color: var(--border) !important;
  color: rgba(255,255,255,0.2) !important;
  box-shadow: none !important;
  cursor: not-allowed;
}

/* ═══════════════════════════════════════════════════════════════
   CRT TERMINAL VIEWPORT FOR LOGS & INSPECTS
   ═══════════════════════════════════════════════════════════════ */
.logs-card {
  border-color: var(--cyan) !important;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.15) !important;
}

.btn-close-logs {
  background: rgba(255, 45, 110, 0.1);
  border: 1px solid var(--pink);
  color: var(--pink);
  padding: 4px 10px;
  font-family: var(--font-hd);
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-close-logs:hover {
  background: var(--pink);
  color: white;
  box-shadow: 0 0 10px var(--pink);
}

.logs-viewport {
  background: radial-gradient(circle at center, rgba(8, 20, 42, 0.95) 0%, rgba(2, 4, 8, 0.98) 100%) !important;
  border: 1px solid rgba(0, 229, 255, 0.35) !important;
  border-radius: 4px;
  padding: 16px;
  height: 320px;
  position: relative;
  overflow-y: auto;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.9), 0 0 10px rgba(0, 229, 255, 0.1);
}

/* Phosphor overlay lines */
.logs-viewport::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%),
              linear-gradient(90deg, rgba(0, 229, 255, 0.02), rgba(0, 255, 157, 0.01), rgba(0, 229, 255, 0.02));
  background-size: 100% 4px, 6px 100%;
  pointer-events: none;
  z-index: 10;
}

.logs-pre {
  margin: 0;
  font-family: var(--font-co);
  font-size: 11px;
  line-height: 1.55;
  color: var(--textwh);
  white-space: pre-wrap;
  position: relative;
  z-index: 2;
}

.preview-pre, .info-pre {
  margin: 0;
  padding: 14px;
  background: radial-gradient(circle at center, rgba(6, 10, 22, 0.9) 0%, rgba(2, 4, 8, 0.96) 100%);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-family: var(--font-co);
  font-size: 11px;
  line-height: 1.45;
  white-space: pre-wrap;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
}

.check-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--textbr);
  font-family: var(--font-ui);
  font-size: 0.9rem;
  cursor: pointer;
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: transparent;
}

.pulse-indicator.active {
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
  animation: rj45-pulse 1.2s infinite;
}

@keyframes rj45-pulse {
  0% { opacity: 1; }
  50% { opacity: 0.3; }
  100% { opacity: 1; }
}

/* ═══════════════════════════════════════════════════════════════
   FULLSCREEN & COLUMN RESIZE STATES
   ═══════════════════════════════════════════════════════════════ */
.docker-panel-container.fullscreen-mode {
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

.resizable-th {
  position: relative;
  user-select: none;
}

.resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 10;
  transition: background 0.15s;
}

.resize-handle:hover {
  background: rgba(0, 229, 255, 0.5);
}

/* ═══════════════════════════════════════════════════════════════
   DOCKER COCKPIT SUB-TABS & ORCHESTRATION STYLING
   ═══════════════════════════════════════════════════════════════ */
.docker-sub-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 4px;
  background: rgba(13, 20, 38, 0.4);
  border: 1px solid var(--border);
  border-radius: 6px;
}

.sub-tab-btn {
  flex: 1;
  background: transparent;
  border: 1px solid transparent;
  color: var(--textbr);
  padding: 8px 16px;
  font-family: var(--font-hd);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  text-transform: uppercase;
}

.sub-tab-btn:hover {
  color: var(--cyan);
  background: rgba(0, 229, 255, 0.05);
}

.sub-tab-btn.active {
  background: rgba(0, 229, 255, 0.12) !important;
  border-color: var(--cyan) !important;
  color: #fff !important;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.25), inset 0 0 5px rgba(0, 229, 255, 0.1);
  text-shadow: 0 0 6px rgba(0, 229, 255, 0.4);
}
</style>
