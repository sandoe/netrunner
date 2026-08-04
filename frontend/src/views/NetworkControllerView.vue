<template>
  <div class="network-controller-view">
    <div class="tabs-nav" role="tablist">
      <button role="tab" :aria-selected="activeTab === 'Config'" aria-controls="tab-config" @click="activeTab = 'Config'" :class="{active: activeTab === 'Config'}">Config</button>
      <button role="tab" :aria-selected="activeTab === 'Clients'" aria-controls="tab-clients" @click="activeTab = 'Clients'" :class="{active: activeTab === 'Clients'}">Clients</button>
      <button role="tab" :aria-selected="activeTab === 'Traffic'" aria-controls="tab-traffic" @click="activeTab = 'Traffic'" :class="{active: activeTab === 'Traffic'}">Traffic</button>
      <button role="tab" :aria-selected="activeTab === 'Hotspot'" aria-controls="tab-hotspot" @click="activeTab = 'Hotspot'" :class="{active: activeTab === 'Hotspot'}">Hotspot</button>
      <button role="tab" :aria-selected="activeTab === 'Wifi'" aria-controls="tab-wifi" @click="activeTab = 'Wifi'" :class="{active: activeTab === 'Wifi'}">Wifi</button>
      <button role="tab" :aria-selected="activeTab === 'Bluetooth'" aria-controls="tab-bluetooth" @click="activeTab = 'Bluetooth'" :class="{active: activeTab === 'Bluetooth'}">Bluetooth</button>
      <button role="tab" :aria-selected="activeTab === 'Bgp'" aria-controls="tab-bgp" @click="activeTab = 'Bgp'" :class="{active: activeTab === 'Bgp'}">BGP Routing</button>
      <button role="tab" :aria-selected="activeTab === 'SDN'" aria-controls="tab-sdn" @click="activeTab = 'SDN'" :class="{active: activeTab === 'SDN'}">SDN (NAT/VLAN)</button>
      <button role="tab" :aria-selected="activeTab === 'ProtocolTester'" aria-controls="tab-protocol-tester" @click="activeTab = 'ProtocolTester'" :class="{active: activeTab === 'ProtocolTester'}">Protocol Tester</button>
    </div>
    <div class="tabs-content">
      <div v-show="activeTab === 'Config'" id="tab-config" class="tab-pane" role="tabpanel">
<div class="infrastructure-view">
    <div class="panel-header">
      <h2>🔌 INFRASTRUCTURE & SDN</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel">
        <h3>VLANs & Networks</h3>
        <p>No networks configured yet.</p>
        <button class="btn-cyan">Create Network</button>
      </div>
      <div class="glass-panel" style="margin-top: 15px;">
        <h3>Firmware & Agents</h3>
        <p>All nodes up to date.</p>
      </div>
    </div>
  </div>
      </div>
      <div v-show="activeTab === 'Clients'" id="tab-clients" class="tab-pane" role="tabpanel">
<div class="clients-view">
    <div class="panel-header">
      <h2>💻 CLIENT MANAGEMENT</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel">
        <table class="data-table">
          <thead>
            <tr>
              <th>HOSTNAME</th>
              <th>IP ADDRESS</th>
              <th>MAC ADDRESS</th>
              <th>EXPERIENCE</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colspan="5" style="text-align: center; color: var(--text-muted);">No clients discovered yet.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
      </div>
      <div v-show="activeTab === 'Traffic'" id="tab-traffic" class="tab-pane" role="tabpanel">
<div class="traffic-analytics-view">
    <div class="panel-header">
      <h2>📈 LAYER-7 TRAFFIC ANALYTICS</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel text-center">
        <p style="color: var(--text-muted);">Awaiting deep packet inspection data from nodes...</p>
      </div>
    </div>
  </div>
      </div>
      <div v-show="activeTab === 'Hotspot'" id="tab-hotspot" class="tab-pane" role="tabpanel">
<div class="hotspot-manager-view">
    <div class="panel-header">
      <h2>🎟️ GUEST HOTSPOT MANAGER</h2>
    </div>
    <div class="panel-content">
      <div class="glass-panel">
        <h3>Generate Vouchers</h3>
        <button class="btn-cyan">Create New Voucher</button>
      </div>
      <div class="glass-panel" style="margin-top: 15px;">
        <h3>Active Guest Sessions</h3>
        <p style="color: var(--text-muted);">No active guests.</p>
      </div>
    </div>
  </div>
      </div>
      <div v-show="activeTab === 'Wifi'" id="tab-wifi" class="tab-pane" role="tabpanel">
<div class="wifi-container">
    <WifiSidebar
      :activeNodes="activeNodes"
      :selectedNodeId="selectedNodeId"
      @update:selectedNodeId="selectedNodeId = $event"
      :isNodeActive="isNodeActive"
      @startNode="startNode"
      @stopNode="stopNode"
      @deleteNode="deleteNode"
      :isRealData="isRealData"
      :isSimulation="isSimulation"
      :csiSource="csiSource"
      :dataStatus="dataStatus"
      :selectedTelemetry="selectedTelemetry"
      :motionDetected="motionDetected"
      :typingActive="typingActive"
    />

    <div class="wifi-main">
      <div class="mode-toggle">
        <button :class="{'active': activeMode === 'single'}" @click="activeMode = 'single'">[ SINGLE NODE DECODER ]</button>
        <button :class="{'active': activeMode === 'mesh'}" @click="activeMode = 'mesh'">[ MULTI-NODE MESH ]</button>
        <button :class="{'active': activeMode === '3d-map'}" @click="activeMode = '3d-map'">[ 3D SIGNAL MAPPING ]</button>
        <button :class="{'active': activeMode === 'observatory'}" @click="activeMode = 'observatory'">[ DENSEPOSE OBSERVATORY ]</button>
      </div>

      <!-- DYNAMIC NODE MANAGER -->
      <div class="node-manager">
        <div class="mode-switch">
          <button :class="{'active': isSimulation}" @click="setMode(true)">[ SIMULATION ]</button>
          <button :class="{'danger-active': !isSimulation}" @click="setMode(false)" class="danger-btn">[ REALTIME SENSORS ]</button>
        </div>

        <div class="divider"></div>

        <!-- RECORD CONTROL -->
        <div class="record-control">
          <button v-if="!isRecording" class="rec-btn" @click="startRecording">
             <span class="rec-dot"></span> RECORD
          </button>
          <button v-else class="rec-btn recording" @click="stopRecording">
             <span class="stop-square"></span> STOP {{ formatRecTime }}
          </button>
          <a v-if="lastDownloadLink" :href="lastDownloadLink" target="_blank" class="download-link">[ GET .JSONL ]</a>
        </div>

        <div class="divider"></div>

        <div class="node-input-group" style="text-align: center;">
          <button @click="showDeployModal = true" class="deploy-btn">[ + DEPLOY NEW NODE ]</button>
        </div>

        <div class="divider"></div>

        <button :class="{'active': showAdvancedStream}" class="node-btn" @click="showAdvancedStream = !showAdvancedStream">[ ADVANCED RAW ]</button>

        <div class="active-nodes-list">
          <span v-if="activeNodes.length === 0" class="no-nodes">No external nodes connected. Simulating 3 nodes.</span>
          <div v-for="(node, index) in activeNodes" :key="index" class="node-badge" :class="{'selected-badge': selectedNodeId === node.id}" :style="{ borderColor: isNodeActive(node.id) ? 'var(--cyan)' : 'var(--pink)' }" @click="selectedNodeId = node.id" tabindex="0" @keydown.enter="selectedNodeId = node.id" @keydown.space.prevent="selectedNodeId = node.id" role="button">
            <div class="node-badge-indicator" :style="{ background: isNodeActive(node.id) ? 'var(--cyan)' : 'var(--pink)' }"></div>
            <span class="node-ip">{{ node.ip }}</span>
            <button @click="removeNode(index)" class="node-remove" aria-label="Remove Node">×</button>
          </div>
        </div>
      </div>

      <!-- SINGLE NODE MODE -->
      <div v-show="activeMode === 'single'" class="single-mode">
        <div class="chart-header">
          <div class="glitch-title">CSI SUBCARRIER AMPLITUDE MATRIX</div>
          <div class="live-badge"><span class="pulse"></span> LIVE STREAM</div>
        </div>
      <div class="chart-container">
        <canvas ref="chartCanvas"></canvas>
      </div>

      <div class="decoders-grid">
        <!-- Panel 1: WiKey -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">KEYSTROKE (WiKey)</div>
            <div v-if="!isSimulation && decodersSimulated" class="sim-tag" title="No CSI keystroke model loaded — demo only">SIMULATED</div>
            <div v-else-if="typingActive" class="live-badge alert-badge" aria-live="assertive"><span class="pulse-alert"></span> INTERCEPTING...</div>
          </div>
          <div class="decoder-terminal">
            <div class="terminal-text">{{ decodedText }}<span class="cursor" v-show="cursorVisible">_</span></div>
          </div>
        </div>

        <!-- Panel 2: Vital Signs -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">VITAL SIGNS (CSI)</div>
            <div class="live-badge"><span class="pulse-alert" style="background:var(--pink);"></span> {{ bpm }} BPM</div>
          </div>
          <div class="decoder-content" style="flex-direction:column;display:flex;align-items:center;justify-content:center;gap:14px;">
             <div class="heartbeat-line"></div>
             <div class="vital-readout">
               <span class="vital-resp">{{ breathingRate !== null ? breathingRate.toFixed(0) : '--' }}</span>
               <span class="vital-unit">RPM (RESP)</span>
             </div>
             <div v-if="!isSimulation && breathingRate === null" class="vital-hint">collecting CSI (~10s)…</div>
          </div>
        </div>

        <!-- Panel 3: Radar -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">THROUGH-WALL RADAR</div>
            <div v-if="!isSimulation && decodersSimulated" class="sim-tag" title="Single-node CSI can't localise — demo only">SIMULATED</div>
          </div>
          <div class="decoder-content" style="position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;">
            <div class="radar-scope">
              <div class="radar-sweep"></div>
              <div class="radar-blip" :style="{ left: (radarX * 100) + '%', top: (radarY * 100) + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- Panel 4: Behavior -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">BEHAVIOR & SPEECH</div>
            <div v-if="!isSimulation && decodersSimulated" class="sim-tag" title="No lip-reading/gesture model loaded — demo only">SIMULATED</div>
          </div>
          <div class="decoder-terminal behavior-terminal">
            <div v-for="(log, idx) in behaviorLogs" :key="idx" class="terminal-text" :class="{'speech-log': log.includes('[SPEECH]'), 'gesture-log': log.includes('[GESTURE]')}">
              {{ log }}
            </div>
          </div>
        </div>
        </div>
      </div>

      <!-- MESH NODE MODE -->
      <div v-show="activeMode === 'mesh'" class="mesh-mode">
        <div class="chart-header">
          <div class="glitch-title">MULTI-NODE SENSOR ARRAY (3D SPATIAL TRACKING)</div>
          <div class="live-badge"><span class="pulse"></span> LIVE TRIANGULATION</div>
        </div>

        <div class="mesh-container">
          <!-- Mesh Map -->
          <div class="mesh-map-panel">
            <div class="mesh-canvas-container">
              <canvas ref="meshCanvas"></canvas>
            </div>
          </div>

          <!-- Mesh Side Telemetry -->
          <div class="mesh-telemetry-panel">
            <div class="link-status" v-for="(link, id) in meshLinks" :key="id">
              <div class="link-header">
                <span class="link-name">LINK {{ id }}</span>
                <span class="link-dist" :class="{'high-dist': link.disturbance > 0.5}">
                  {{ (link.disturbance * 100).toFixed(0) }}% DISTURBANCE
                </span>
              </div>
              <div class="link-bar-bg">
                <div class="link-bar-fill" :style="{ width: (link.disturbance * 100) + '%', backgroundColor: link.disturbance > 0.5 ? 'var(--pink)' : 'var(--cyan)' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3D SIGNAL MAPPING MODE -->
      <div v-show="activeMode === '3d-map'" class="map3d-mode">
        <div class="chart-header">
          <div class="glitch-title">3D SIGNAL STRENGTH VISUALIZATION (CSI SPATIAL MATRIX)</div>
          <div class="live-badge"><span class="pulse"></span> LIVE RENDER</div>
        </div>

        <div class="map3d-grid">
          <div class="map3d-panel">
            <div ref="map3dSurface" class="plotly-container"></div>
          </div>
          <div class="map3d-panel">
            <div ref="mapTopView" class="plotly-container"></div>
          </div>
          <div class="map3d-panel">
            <div ref="mapSideX" class="plotly-container"></div>
          </div>
          <div class="map3d-panel">
            <div ref="mapSideY" class="plotly-container"></div>
          </div>
        </div>
      </div>

      <!-- DENSEPOSE OBSERVATORY MODE -->
      <div v-show="activeMode === 'observatory' && !isRebuildingObservatory" class="observatory-mode">
        <div class="obs-container" ref="obsContainer">
          <canvas ref="obsCanvas" class="obs-canvas"></canvas>

          <!-- Top UI Overlay -->
          <div class="obs-top">
            <h2>π RuView</h2>
            <div class="obs-sub">WIFI DENSEPOSE SENSING OBSERVATORY</div>
          </div>

          <!-- UI Overlay Left -->
          <div class="obs-ui obs-ui-left">
            <div class="obs-panel">
              <div class="obs-panel-title">VITAL SIGNS</div>
              <div class="obs-stat">
                <span class="obs-icon" style="color:var(--pink);">❤️</span>
                <div class="obs-val">
                  <span class="obs-num">85</span><span class="obs-unit">BPM</span>
                </div>
                <div class="obs-label">HEART RATE</div>
              </div>
              <div class="obs-divider"></div>
              <div class="obs-stat">
                <span class="obs-icon" style="color:var(--cyan);">☀️</span>
                <div class="obs-val">
                  <span class="obs-num">18</span><span class="obs-unit">RPM</span>
                </div>
                <div class="obs-label">RESPIRATION</div>
              </div>
              <div class="obs-divider"></div>
              <div class="obs-stat">
                <span class="obs-icon" style="color:#ffb800;">⚖️</span>
                <div class="obs-val">
                  <span class="obs-num">81</span><span class="obs-unit">%</span>
                </div>
                <div class="obs-label">CONFIDENCE</div>
                <div class="obs-bar"><div class="obs-bar-fill" style="width:81%; background:var(--cyan);"></div></div>
              </div>
            </div>
          </div>

          <!-- UI Overlay Right -->
          <div class="obs-ui obs-ui-right">
            <div class="obs-panel">
              <div class="obs-panel-title">WIFI SIGNAL</div>
              <div class="obs-row"><span>RSSI</span><span style="color:#0088ff;">-36 dBm</span></div>
              <div class="obs-row"><span>Variance</span><span style="color:#0088ff;">2.43</span></div>
              <div class="obs-row"><span>Motion</span><span style="color:#0088ff;">0.394</span></div>
              <div class="obs-row"><span>Persons</span><span style="color:#0088ff;">2 🟢🟢⚫⚫⚫</span></div>
              <div class="obs-wave"></div>
              <div class="obs-panel-title" style="margin-top:20px;">PRESENCE</div>
              <div class="obs-btn-active">ACTIVE</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ADVANCED RAW STREAM PANEL -->
      <div v-if="showAdvancedStream" class="advanced-stream-panel">
        <div class="advanced-header">
           <span>RAW CSI DATA STREAM [JSON]</span>
           <button @click="showAdvancedStream = false" class="close-btn" aria-label="Close stream">×</button>
        </div>
        <div class="advanced-content" ref="advancedContent">
           <div v-for="(log, idx) in rawLogs" :key="idx" class="log-line">
              {{ log }}
           </div>
        </div>
      </div>

      <!-- NODE CONFIGURATION MODAL -->
      <div v-if="showDeployModal" class="modal-overlay" @click.self="showDeployModal = false">
        <div class="modal-content glitch-box">
          <div class="modal-header">
            <h2>NODE CONFIGURATION PAYLOAD</h2>
            <button @click="showDeployModal = false" class="close-btn">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label for="deploy-ip">TARGET IP (SSH)</label>
              <input id="deploy-ip" v-model="deployForm.ip" type="text" placeholder="e.g. 192.168.1.100" class="hack-input"/>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="deploy-username">USERNAME</label>
                <input id="deploy-username" v-model="deployForm.username" type="text" placeholder="pi" class="hack-input"/>
              </div>
              <div class="form-group">
                <label for="deploy-password">PASSWORD</label>
                <input id="deploy-password" v-model="deployForm.password" type="password" placeholder="***" class="hack-input"/>
              </div>
            </div>

            <div class="form-group">
              <label for="deploy-csi">CSI EXTRACTION MODE</label>
              <select id="deploy-csi" v-model="deployForm.csi_mode" class="hack-select">
                <option value="AUTO">AUTO (Nexmon -> Synthetic)</option>
                <option value="RAW_NEXMON">RAW_NEXMON (Force hardware)</option>
                <option value="SYNTHETIC">SYNTHETIC (Simulation)</option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="deploy-sample">SAMPLE RATE (Hz)</label>
                <input id="deploy-sample" v-model="deployForm.sample_rate" type="number" class="hack-input"/>
              </div>
              <div class="form-group">
                <label for="deploy-udp">UDP TARGET PORT</label>
                <input id="deploy-udp" v-model="deployForm.udp_port" type="number" class="hack-input"/>
              </div>
            </div>

            <div class="form-group">
              <label for="deploy-server">TARGET SERVER IP (This computer's IP, e.g. 192.168.1.X)</label>
              <input id="deploy-server" v-model="deployForm.target_server_ip" type="text" class="hack-input"/>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="saveAndDeployNode" class="hack-btn primary" :disabled="isDeploying">
              <span v-if="isDeploying" class="spinner"></span> [ INJECT BEACON ]
            </button>
            <button @click="showDeployModal = false" class="hack-btn secondary">[ ABORT ]</button>
          </div>
        </div>
      </div>

    </div>
  </div>
      </div>
      <div v-show="activeTab === 'Bluetooth'" id="tab-bluetooth" class="tab-pane" role="tabpanel">
<div class="bt-view">
    <div class="bt-header">
      <div class="header-title">
        <span class="icon">📡</span> BLUETOOTH CONTROL ROOM
        <span class="pulse" :class="{ active: connected }"></span>
        <span v-if="selectedTelemetry?.capabilities?.bluetooth" class="badge" :style="{ marginLeft: '10px', background: selectedTelemetry.capabilities.bluetooth_state === 'UP' ? 'var(--green)' : 'var(--pink)', color: '#000', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' }">
          {{ selectedTelemetry.capabilities.bluetooth_state === 'UP' ? 'HW: UP' : 'HW: DOWN' }}
        </span>
        <span v-else class="badge" style="margin-left: 10px; background: var(--text-muted); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;">
          NO HW DETECTED
        </span>
      </div>
      <div class="header-stats">
        <span>{{ sortedDevices.length }} DEVICES DETECTED</span>
        <button v-if="store.selectedId" class="btn btn-outline" style="margin-left: 10px; border-color: var(--green); color: var(--green); padding: 2px 8px; font-size: 10px;" @click="toggleNodeBluetooth(true)">
          TURN ON NODE BT
        </button>
        <button v-if="store.selectedId" class="btn btn-outline" style="margin-left: 10px; border-color: var(--pink); color: var(--pink); padding: 2px 8px; font-size: 10px;" @click="toggleNodeBluetooth(false)">
          TURN OFF NODE BT
        </button>
        <button v-if="store.selectedId" class="btn btn-outline" style="margin-left: 10px; border-color: var(--cyan); color: var(--cyan); padding: 2px 8px; font-size: 10px;" @click="store.select(null)">
          CLEAR NODE FILTER
        </button>

      </div>
    </div>

    <div class="bt-content">
      <div class="radar-container aliens-theme">
        <div class="radar-crt-overlay"></div>
        <div class="radar">
          <div class="sweep"></div>
          <div class="ring r1"></div>
          <div class="ring r2"></div>
          <div class="ring r3"></div>
          <div class="ring r4"></div>
          <div class="crosshair-v"></div>
          <div class="crosshair-h"></div>

          <template v-if="!triangulationMode">
            <div
              v-for="dev in sortedDevices"
              :key="dev.mac"
              class="blip"
              :class="{
                'true-aoa': dev.azimuth !== undefined,
                'jamming-target': jammedTargets[dev.mac]
              }"
              :style="getBlipStyle(dev)"
              :title="dev.name + ' (' + dev.mac + ')'"
              @click="selectedDevice = dev; triangulationMode = false"
            >
              <div class="blip-ripple"></div>
              <div class="jamming-lightning" v-if="jammedTargets[dev.mac]"></div>
              <div class="blip-label">{{ dev.name !== 'Unknown Device' ? dev.name : dev.mac.substring(0,8) }}</div>
            </div>
          </template>

          <template v-else-if="selectedDevice && selectedDevice.nodes">
            <!-- Triangulation Mode: Render Nodes -->
            <div
              v-for="(pos, nid) in triangulationData.nodes"
              :key="nid"
              class="blip node-blip"
              :style="{ left: pos.x + '%', top: pos.y + '%' }"
            >
              <div class="node-label" style="top: -30px">{{ nid }}<br>{{ selectedDevice.nodes[nid]?.rssi ? rssiToDistance(selectedDevice.nodes[nid].rssi) : '?' }}m</div>
            </div>

            <!-- Triangulation Mode: Render Target (Weighted Center) -->
            <div class="blip target-blip" :style="{ left: triangulationData.target.x + '%', top: triangulationData.target.y + '%', background: '#ff3333', boxShadow: '0 0 15px #ff3333, 0 0 30px #ff0000', width: '16px', height: '16px' }">
              <div class="blip-ripple" style="border-color: #ff3333;"></div>
              <div class="blip-label text-pink" style="top: -25px; color: #ff3333 !important; font-size: 12px; background: rgba(0,0,0,0.8); border-color: #ff3333;">TARGET</div>
            </div>
          </template>
        </div>
        <div class="closest-range" v-if="sortedDevices.length">
          <span class="range-label">PROXIMITY</span>
          <span class="range-val">{{ Math.abs(sortedDevices[0].rssi) }} <small>m</small></span>
        </div>
      </div>

      <div class="device-list">
        <h3>DISCOVERED DEVICES</h3>
        <div v-if="devices.length === 0" class="empty-list">No devices found. Scanning...</div>
        <div
          v-for="dev in sortedDevices"
          :key="dev.mac"
          class="device-card"
          :class="{ selected: selectedDevice && selectedDevice.mac === dev.mac }"
          @click="selectedDevice = dev"
          tabindex="0"
          @keydown.enter="selectedDevice = dev"
          @keydown.space.prevent="selectedDevice = dev"
          role="button"
        >
          <div class="card-header">
            <span class="dev-name">{{ dev.name }}</span>
            <span class="dev-rssi" :class="getRssiClass(dev.rssi)">{{ dev.rssi }} dBm</span>
          </div>
          <div class="card-body">
            <div class="dev-mac">{{ dev.mac }}</div>
            <div class="dev-seen">Last seen: {{ Math.round((Date.now() - dev.last_seen * 1000) / 1000) }}s ago</div>
          </div>
        </div>
      </div>

      <div class="device-details" v-if="selectedDevice">
        <h3>DEVICE DETAILS</h3>
        <div class="detail-row">
          <span class="lbl">NAME:</span>
          <span class="val">{{ selectedDevice.name }}</span>
        </div>
        <div class="detail-row">
          <span class="lbl">MAC:</span>
          <span class="val">{{ selectedDevice.mac }}</span>
        </div>
        <div class="detail-row" v-if="selectedDevice.azimuth !== undefined">
          <span class="lbl">AOA AZIMUTH:</span>
          <span class="val text-pink">{{ selectedDevice.azimuth }}° (True)</span>
        </div>
        <div class="detail-row">
          <span class="lbl">SIGNAL:</span>
          <span class="val" :class="getRssiClass(selectedDevice.rssi)">{{ selectedDevice.rssi }} dBm</span>
        </div>
        <div class="detail-row" v-if="selectedDevice.tx_power !== undefined && selectedDevice.tx_power !== null">
          <span class="lbl">TX POWER:</span>
          <span class="val">{{ selectedDevice.tx_power }} dBm</span>
        </div>
        <div class="detail-row" v-if="selectedDevice.manufacturer_data && Object.keys(selectedDevice.manufacturer_data).length > 0">
          <span class="lbl">MANUFACTURER:</span>
          <div class="val-box">
            <div v-for="(hex, id) in selectedDevice.manufacturer_data" :key="id">
              [0x{{ Number(id).toString(16).toUpperCase() }}] {{ hex }}
            </div>
          </div>
        </div>
        <div class="detail-row" v-if="selectedDevice.service_uuids && selectedDevice.service_uuids.length > 0">
          <span class="lbl">SERVICES:</span>
          <div class="val-box">
            <div v-for="uuid in selectedDevice.service_uuids" :key="uuid">
              {{ uuid }}
            </div>
          </div>
        </div>


        <div class="detail-row" v-if="selectedDevice.nodes && Object.keys(selectedDevice.nodes).length > 0">
          <button class="btn btn-outline" style="width: 100%; border-color: var(--cyan); color: var(--cyan);" @click="triangulationMode = !triangulationMode">
            {{ triangulationMode ? 'DEACTIVATE TRIANGULATION' : 'ACTIVATE TRIANGULATION' }}
          </button>
        </div>

        <div class="detail-row" v-if="selectedDevice.nodes && Object.keys(selectedDevice.nodes).length > 0">
          <span class="lbl">SEEN BY:</span>
          <div class="val-box">
            <div v-for="(ndata, nid) in selectedDevice.nodes" :key="nid" :class="{ 'text-cyan': store.selectedId === nid }">
              {{ nid }}: <span :class="getRssiClass(ndata.rssi)">{{ ndata.rssi }} dBm</span>
              <span class="text-cyan">(Est. {{ rssiToDistance(ndata.rssi) }}m)</span>
            </div>
          </div>
        </div>

        <!-- Active Enumeration Data -->
        <div class="detail-row" v-if="selectedDevice.enum_data">
          <span class="lbl text-pink">GATT PROFILE:</span>
          <div class="val-box gatt-box">
            <div v-for="(srv, uuid) in selectedDevice.enum_data" :key="uuid" class="gatt-service">
              <div class="gatt-title">{{ srv.description || uuid }}</div>
              <div v-for="(cval, cname) in srv.characteristics" :key="cname" class="gatt-char">
                <span class="cname">{{ cname }}:</span> <span class="cval">{{ cval }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="actions">
          <button
            class="btn-action"
            @click="enumerateDevice(selectedDevice.mac)"
            :disabled="selectedDevice.enumerating"
          >
            {{ selectedDevice.enumerating ? 'ENUMERATING...' : 'CONNECT / ENUMERATE' }}
          </button>
          <button class="btn-action" @click="pairingModalVisible = true; pairingStatus = ''">
            PAIR DEVICE 🔗
          </button>
          <button
            v-if="!jammedTargets[selectedDevice.mac]"
            class="btn-action btn-danger"
            @click="toggleJam(selectedDevice.mac)"
          >
            ENGAGE JAMMER 💥
          </button>
          <button
            v-else
            class="btn-action btn-danger jamming-active"
            @click="toggleJam(selectedDevice.mac)"
          >
            STOP JAMMING 🛑
          </button>
        </div>
      </div>
    </div>

    <!-- Pairing Modal -->
    <div class="modal-overlay" v-if="pairingModalVisible">
      <div class="modal-box aliens-theme-box">
        <h3>PAIR BLUETOOTH DEVICE</h3>
        <p>Target: <strong class="text-cyan">{{ selectedDevice?.mac }}</strong> ({{ selectedDevice?.name }})</p>
        <div v-if="pairingStatus" class="pairing-status" :class="{'text-pink': pairingStatus.includes('failed') || pairingStatus.includes('error'), 'text-green': pairingStatus.includes('success')}" aria-live="assertive">
          {{ pairingStatus }}
        </div>
        <div class="actions" style="margin-top: 20px; flex-direction: row; justify-content: center; padding: 0;">
          <button class="btn-action" style="flex: 1" @click="confirmPairing" :disabled="isPairing">
            <span v-if="isPairing" class="spinner"></span> {{ isPairing ? 'PAIRING...' : 'CONFIRM PAIRING' }}
          </button>
          <button class="btn-action btn-outline text-pink" style="border-color: var(--pink)" @click="pairingModalVisible = false; pairingStatus = ''">CANCEL</button>
        </div>
      </div>
    </div>

    <!-- Recon Modal -->
    <div class="modal-overlay" v-if="reconModalVisible">
      <div class="modal-box aliens-theme-box" style="width: 800px; max-width: 90vw;">
        <h3 class="text-green">ADVANCED RECONNAISSANCE DATA</h3>
        <p>Target Node: <strong class="text-cyan">{{ store.selectedId }}</strong></p>
        <div class="recon-data-container" style="max-height: 60vh; overflow-y: auto; text-align: left; background: rgba(0,0,0,0.8); padding: 15px; font-family: monospace; font-size: 11px; white-space: pre-wrap; color: var(--green); border: 1px solid var(--green); border-radius: 4px; box-shadow: inset 0 0 10px rgba(0,255,0,0.2);">
          {{ reconData || 'Loading OSINT payload...' }}
        </div>
        <div class="actions" style="margin-top: 20px; flex-direction: row; justify-content: center; padding: 0;">
          <button class="btn-action btn-cancel text-cyan" style="border-color: var(--cyan)" @click="reconModalVisible = false">CLOSE RECON</button>
        </div>
      </div>
    </div>

  </div>
      </div>
      <div v-show="activeTab === 'Bgp'" id="tab-bgp" class="tab-pane" role="tabpanel">
        <div class="bgp-routing-view">
          <div class="panel-header">
            <h2>🌍 BGP ROUTING</h2>
          </div>
          <div class="panel-content">
            <div class="glass-panel">
              <h3>BGP Route Management</h3>
              <div class="form-group" style="margin-top: 15px;">
                <label for="bgp-route" style="display: block; margin-bottom: 5px; color: var(--cyan);">BGP Route</label>
                <input id="bgp-route" v-model="bgpRoute" type="text" placeholder="e.g. 10.0.0.0/24" class="hack-input" style="width: 100%; max-width: 400px;"/>
              </div>
              <div class="form-group" style="margin-top: 15px;">
                <label for="bgp-nexthop" style="display: block; margin-bottom: 5px; color: var(--cyan);">Next Hop</label>
                <input id="bgp-nexthop" v-model="bgpNextHop" type="text" placeholder="e.g. 192.168.1.1" class="hack-input" style="width: 100%; max-width: 400px;"/>
              </div>
              <div class="form-row" style="margin-top: 20px; display: flex; gap: 15px;">
                <button class="btn-cyan" @click="announceRoute">Announce Route</button>
                <button class="btn-cyan" @click="withdrawRoute" style="background: transparent; color: var(--pink); border: 1px solid var(--pink);">Withdraw Route</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'SDN'" id="tab-sdn" class="tab-pane" role="tabpanel">
        <SdnConfigPanel />
      </div>

      <div v-show="activeTab === 'ProtocolTester'" id="tab-protocol-tester" class="tab-pane" role="tabpanel">
        <ProtocolTesterPanel />
      </div>
    </div>
    <!-- Toast Notifications -->
    <div class="toast-container" v-if="toasts.length > 0">
      <div v-for="toast in toasts" :key="toast.id" class="toast-msg" :class="toast.type">
        {{ toast.message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { api, wsBase, wsTokenParam } from '@/api/client'
import Chart from 'chart.js/auto'
import Plotly from 'plotly.js-dist-min'
import * as THREE from 'three'
import { useNodesStore } from '@/stores/nodes'
import SdnConfigPanel from '@/components/SdnConfigPanel.vue'
import ProtocolTesterPanel from '@/components/ProtocolTesterPanel.vue'
import WifiSidebar from '@/components/NetworkController/WifiSidebar.vue'

const activeTab = ref('Config')

const toasts = ref<{id: number, message: string, type: string}[]>([])
let toastId = 0
function showToast(message: string, type: 'error' | 'success' | 'info' = 'info') {
  const id = toastId++
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 4000)
}

const isDeploying = ref(false)

// Dummy logic for now
// --- End Config Script ---


interface NetworkNode {
  ip: string;
  color: number;
}

const activeMode = ref(localStorage.getItem('netrunner_wifi_mode') || 'single')

const selectedNodeId = ref<string>(localStorage.getItem('netrunner_wifi_selected') || "")
const nodeLastSeen = ref<Record<string, number>>({})

// fetch wrapper that attaches the JWT (backend now requires auth on wifi endpoints)
const authFetch = (url: string, opts: RequestInit = {}) => {
  const token = localStorage.getItem('nr_token')
  const headers: Record<string, string> = { ...(opts.headers as Record<string, string> || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return fetch(url, { ...opts, headers })
}

const bgpRoute = ref('')
const bgpNextHop = ref('')

const announceRoute = async () => {
  if (!bgpRoute.value || !bgpNextHop.value) {
    showToast('Please provide both BGP Route and Next Hop.', 'error')
    return
  }
  try {
    const res = await authFetch('/api/bgp/announce', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ route: bgpRoute.value, nextHop: bgpNextHop.value })
    })
    if (!res.ok) throw new Error('API Error')
    showToast('BGP Route announced successfully.', 'success')
  } catch (e: any) {
    showToast('Failed to announce BGP Route.', 'error')
  }
}

const withdrawRoute = async () => {
  if (!bgpRoute.value || !bgpNextHop.value) {
    showToast('Please provide both BGP Route and Next Hop.', 'error')
    return
  }
  try {
    const res = await authFetch('/api/bgp/withdraw', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ route: bgpRoute.value, nextHop: bgpNextHop.value })
    })
    if (!res.ok) throw new Error('API Error')
    showToast('BGP Route withdrawn successfully.', 'success')
  } catch (e: any) {
    showToast('Failed to withdraw BGP Route.', 'error')
  }
}

watch(selectedNodeId, (v) => {
  if (v) localStorage.setItem('netrunner_wifi_selected', v)
  else localStorage.removeItem('netrunner_wifi_selected')
})
watch(activeMode, (v) => localStorage.setItem('netrunner_wifi_mode', v))

const isNodeActive = (id: string) => {
  if (isSimulation.value) return true;
  return (Date.now() - (nodeLastSeen.value[id] || 0)) < 5000;
}

const newNodeIp = ref('')
const activeNodes = ref<NetworkNode[]>([])
const isSimulation = ref(true)

// Modal & Deploy State
const showDeployModal = ref(false)
const deployForm = ref({
  id: '',
  ip: '',
  username: '',
  password: '',
  csi_mode: 'AUTO',
  sample_rate: 30,
  udp_port: 8001,
  target_server_ip: window.location.hostname !== 'localhost' ? window.location.hostname : '127.0.0.1'
})

const fetchSavedNodes = async () => {
  try {
    const res = await authFetch('/api/wifi/beacons')
    const data = await res.json()
    if (data.beacons) {
      activeNodes.value = data.beacons.map((b: any) => ({
        ip: b.ip,
        color: availableColors[Math.floor(Math.random() * availableColors.length)],
        id: b.id
      }))
    }
  } catch(e) {
    console.error("Failed to fetch beacons", e)
  }
}

// Persist state
onMounted(() => {
  fetchSavedNodes()

  const savedMode = localStorage.getItem('netrunner_sim_mode')
  if (savedMode !== null) {
    isSimulation.value = savedMode === 'true'
  }

  // Sync with backend on load
  authFetch('/api/wifi/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      simulation: isSimulation.value,
      nodes: activeNodes.value.map(n => n.ip)
    })
  }).catch(e => console.error("Initial sync failed", e))

  // Poll per-node hardware capabilities / CSI source
  fetchTelemetry()
  telemetryInterval = setInterval(fetchTelemetry, 2000)
})

watch(activeNodes, (newVal) => {
  localStorage.setItem('netrunner_nodes', JSON.stringify(newVal))
}, { deep: true })

watch(isSimulation, (newVal) => {
  localStorage.setItem('netrunner_sim_mode', String(newVal))
})

const showAdvancedStream = ref(false)
const rawLogs = ref<string[]>([])
const advancedContent = ref<HTMLElement | null>(null)

// Recorder state
const isRecording = ref(false)
const recordingSeconds = ref(0)
const lastDownloadLink = ref('')
let recInterval: any = null

const formatRecTime = computed(() => {
  const m = Math.floor(recordingSeconds.value / 60).toString().padStart(2, '0')
  const s = (recordingSeconds.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

const startRecording = async () => {
  try {
    await authFetch('/api/wifi/record/start', { method: 'POST' })
    isRecording.value = true
    recordingSeconds.value = 0
    lastDownloadLink.value = ''
    recInterval = setInterval(() => { recordingSeconds.value++ }, 1000)
  } catch(e) {
    console.error("Start recording failed", e)
  }
}

const stopRecording = async () => {
  try {
    const res = await authFetch('/api/wifi/record/stop', { method: 'POST' })
    const data = await res.json()
    isRecording.value = false
    if (recInterval) clearInterval(recInterval)
    if (data.filename) {
      lastDownloadLink.value = `/api/wifi/record/download/${data.filename}`
    }
  } catch(e) {
    console.error("Stop recording failed", e)
  }
}

const availableColors = [0x0055ff, 0xff2d6e, 0x00ff9d, 0xffb800, 0x9d00ff, 0x00ffff]

const setMode = async (sim: boolean) => {
  isSimulation.value = sim
  await pushModeToBackend()
}

const pushModeToBackend = async () => {
  try {
    await authFetch('/api/wifi/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulation: isSimulation.value,
        nodes: activeNodes.value.map(n => n.ip)
      })
    })
  } catch(e) {
    console.error("Failed to set mode", e)
  }
}

const getHexColorStr = (hex: number) => {
  return '#' + hex.toString(16).padStart(6, '0')
}

const saveAndDeployNode = async () => {
  if (!deployForm.value.ip) return

  // Generate ID if new
  const nodeId = deployForm.value.id || 'node_' + Date.now()
  deployForm.value.id = nodeId

  isDeploying.value = true
  try {
    // 1. Save to DB
    await authFetch('/api/wifi/beacons', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(deployForm.value)
    })

    // 2. Trigger Deploy regardless of mode
    const res = await authFetch('/api/wifi/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: nodeId })
    })
    const deployData = await res.json()
    if (deployData.error) {
        showToast("DEPLOYMENT FAILED: " + deployData.error, 'error')
        return
    }

    // Auto switch to realtime mode
    if (isSimulation.value) {
        setMode(false)
    }

    showDeployModal.value = false
    await fetchSavedNodes()
    pushModeToBackend()

    if (activeMode.value === 'observatory') {
      rebuildObservatory()
    }
    showToast("Node Deployed Successfully.", 'success')

    // reset form but keep target_server_ip
    const currentTargetIp = deployForm.value.target_server_ip
    deployForm.value = {
      id: '', ip: '', username: '', password: '', csi_mode: 'AUTO', sample_rate: 30, udp_port: 8001, target_server_ip: currentTargetIp
    }
  } catch (e: any) {
    showToast("DEPLOYMENT FAILED: " + e.message, 'error')
  } finally {
    isDeploying.value = false
  }
}

const startNode = async (nodeId: string) => {
  try {
    const res = await authFetch('/api/wifi/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: nodeId })
    })
    const data = await res.json()
    if (data.error) {
      showToast("START FAILED: " + data.error, 'error')
    } else {
      showToast("Beacon Started Successfully.", 'success')
      pushModeToBackend()
    }
  } catch (e: any) {
    console.error(e)
    showToast("START FAILED: " + e.message, 'error')
  }
}

const stopNode = async (nodeId: string) => {
  try {
    const res = await authFetch(`/api/wifi/beacons/${nodeId}/stop`, {
      method: 'POST'
    })
    const data = await res.json()
    if (data.error) {
      showToast("STOP FAILED: " + data.error, 'error')
    } else {
      showToast("Beacon Stopped Successfully.", 'success')
    }
  } catch (e: any) {
    console.error(e)
    showToast("STOP FAILED: " + e.message, 'error')
  }
}

const deleteNode = async (nodeId: string) => {
  if (!confirm("Are you sure you want to remove this node configuration?")) return
  try {
    await authFetch(`/api/wifi/beacons/${nodeId}`, {
      method: 'DELETE'
    })
    await fetchSavedNodes()
  } catch(e) {
    console.error("Delete failed", e)
  }
}

const removeNode = async (index: number) => {
  const node = activeNodes.value[index]
  if ((node as any).id) {
    try {
      await authFetch(`/api/wifi/beacons/${(node as any).id}`, {
        method: 'DELETE'
      })
    } catch(e) {}
  }
  activeNodes.value.splice(index, 1)
  pushModeToBackend()
  if (activeMode.value === 'observatory') {
    rebuildObservatory()
  }
}

const isRebuildingObservatory = ref(false)

const rebuildObservatory = () => {
  if (obsReqFrame) cancelAnimationFrame(obsReqFrame)
  isRebuildingObservatory.value = true
  setTimeout(() => {
    isRebuildingObservatory.value = false
    setTimeout(() => {
      initObservatory()
    }, 50)
  }, 50)
}
const chartCanvas = ref<HTMLCanvasElement | null>(null)
const meshCanvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null
let wifiWs: WebSocket | null = null

const motionDetected = ref(false)
const typingActive = ref(false)
const decodedText = ref("")
const cursorVisible = ref(true)

const bpm = ref(72)
const breathingRate = ref<number | null>(null)
const radarX = ref(0.5)
const radarY = ref(0.5)
const behaviorLogs = ref<string[]>([])

// --- live data provenance (REAL hardware CSI vs SIMULATED) ---
const csiSource = ref<string>('')          // 'nexmon' | 'synthetic' | ''
const dataStatus = ref<string>('')         // honest status string from beacon
const decodersSimulated = ref<boolean>(true)
const motionLevel = ref<number>(0)
// per-node hardware telemetry from /api/wifi/telemetry
const nodeTelemetry = ref<Record<string, any>>({})
let telemetryInterval: any = null

const isRealData = computed(() => !isSimulation.value && csiSource.value === 'nexmon')

const selectedTelemetry = computed(() => {
  if (selectedNodeId.value && nodeTelemetry.value[selectedNodeId.value]) {
    return nodeTelemetry.value[selectedNodeId.value]
  }
  const vals = Object.values(nodeTelemetry.value)
  return vals.length ? vals[0] : null
})

const fetchTelemetry = async () => {
  try {
    const res = await authFetch('/api/wifi/telemetry')
    const data = await res.json()
    const map: Record<string, any> = {}
    for (const n of (data.nodes || [])) map[n.node_id] = n
    nodeTelemetry.value = map
  } catch (e) { /* non-fatal */ }
}

// Mesh state
const meshNodes = ref<any>({})
const meshTarget = ref<any>({x: 50, y: 50})
const meshLinks = ref<any>({
  "AB": { disturbance: 0 },
  "BC": { disturbance: 0 },
  "CA": { disturbance: 0 }
})
let meshAnimFrame: number | null = null

// Mesh rendering is driven by the always-on renderMesh() rAF loop (set up in onMounted),
// which only draws while activeMode === 'mesh'. This is a no-op hook kept for the
// activeMode watcher / restore-on-mount call sites.
const startMeshAnimation = () => {}

// 3D map references
const map3dSurface = ref<HTMLElement | null>(null)
const mapTopView = ref<HTMLElement | null>(null)
const mapSideX = ref<HTMLElement | null>(null)
const mapSideY = ref<HTMLElement | null>(null)
let mapAnimFrame: number | null = null
let mapAnimTimer: number | null = null

// Observatory state
const obsContainer = ref<HTMLElement | null>(null)
const obsCanvas = ref<HTMLCanvasElement | null>(null)
let obsReqFrame: number | null = null

setInterval(() => {
  cursorVisible.value = !cursorVisible.value
}, 500)

onMounted(() => {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  // Initialize chart
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array.from({ length: 64 }, (_, i) => i - 32),
      datasets: [{
        label: 'Amplitude',
        data: Array(64).fill(0),
        borderColor: 'var(--cyan)',
        backgroundColor: 'rgba(0, 255, 157, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 0 // turn off animation for high FPS updates
      },
      scales: {
        y: {
          min: 0,
          max: 60,
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: '#aaa' }
        },
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#aaa' }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  })

  // Setup WebSocket
  wifiWs = new WebSocket(`${wsBase()}/wifiWs/csi${wsTokenParam()}`)

  wifiWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      let resolvedNodeId = data.node_id ? data.node_id.replace('beacon_', '') : '';
      if (!resolvedNodeId && data.node_ip) {
        const matchingNode = activeNodes.value.find(n => n.ip === data.node_ip);
        if (matchingNode) {
          resolvedNodeId = matchingNode.id;
        }
      }

      if (resolvedNodeId) {
         nodeLastSeen.value[resolvedNodeId] = Date.now()
         // Also set with the raw node_ip just in case
         if (data.node_ip) {
           nodeLastSeen.value[data.node_ip] = Date.now()
         }
      }


      if (data.type === 'mesh') {
        // Process mesh telemetry
        meshNodes.value = data.nodes
        meshTarget.value = data.target
        meshLinks.value = data.links

        if (showAdvancedStream.value) {
          rawLogs.value.push(`[MESH] ${JSON.stringify(data.links)}`)
          if (rawLogs.value.length > 20) rawLogs.value.shift()
          nextTick(() => {
            if (advancedContent.value) advancedContent.value.scrollTop = advancedContent.value.scrollHeight
          })
        }

      } else {
        // Single Node CSI Amplitude Matrix logic
        if (selectedNodeId.value && resolvedNodeId !== selectedNodeId.value) { return; }

        // Provenance of this stream (REAL hardware CSI vs synthetic fallback)
        if (data.csi_source) csiSource.value = data.csi_source
        if (data.status) dataStatus.value = data.status
        if (data.decoders_simulated !== undefined) decodersSimulated.value = data.decoders_simulated
        if (data.motion_level !== undefined) motionLevel.value = data.motion_level
        if (data.breathing_rate !== undefined) breathingRate.value = data.breathing_rate

        if (showAdvancedStream.value) {
          rawLogs.value.push(`[CSI] ${JSON.stringify({ts: data.timestamp, amps: data.amplitudes.slice(0, 5) + '...'})}`)
          if (rawLogs.value.length > 20) rawLogs.value.shift()
          nextTick(() => {
            if (advancedContent.value) advancedContent.value.scrollTop = advancedContent.value.scrollHeight
          })
        }

        if (chart && data.amplitudes) {
          chart.data.datasets[0].data = data.amplitudes
          chart.update()
        }
      }

      motionDetected.value = data.motion_detected || false
      typingActive.value = data.typing_active !== undefined ? data.typing_active : (data.keystroke ? true : false)

      const parsedBpm = data.bpm || data.heart_rate;
      if (parsedBpm) bpm.value = Math.round(parsedBpm);

      if (data.radar) {
        radarX.value = data.radar.x
        radarY.value = data.radar.y
      } else if (data.radar_x !== undefined && data.radar_y !== undefined) {
        radarX.value = data.radar_x
        radarY.value = data.radar_y
      }
      if (data.behavior) {
        behaviorLogs.value.push(`[${new Date().toISOString().split('T')[1].slice(0,8)}] ${data.behavior}`)
        if (behaviorLogs.value.length > 8) behaviorLogs.value.shift()
      }

      if (data.keystroke) {
        decodedText.value += data.keystroke
        if (decodedText.value.length > 300) {
          decodedText.value = decodedText.value.substring(decodedText.value.length - 300)
        }
      }

      if (chart) {
        if (data.amplitudes) {
           chart.data.datasets[0].data = data.amplitudes
        }
        if (data.motion_detected) {
          chart.data.datasets[0].borderColor = 'var(--pink)'
          chart.data.datasets[0].backgroundColor = 'rgba(255, 45, 110, 0.2)'
        } else if (data.typing_active) {
          chart.data.datasets[0].borderColor = '#ffc000'
          chart.data.datasets[0].backgroundColor = 'rgba(255, 192, 0, 0.2)'
        } else {
          chart.data.datasets[0].borderColor = 'var(--cyan)'
          chart.data.datasets[0].backgroundColor = 'rgba(0, 255, 157, 0.1)'
        }
        chart.update()
      }
    } catch (e) {}
  }

  // Render loop for Mesh Canvas
  const renderMesh = () => {
    if (activeMode.value === 'mesh' && meshCanvas.value) {
      const canvas = meshCanvas.value
      const ctx = canvas.getContext('2d')
      if (ctx) {
        // Adjust canvas size to match container
        const parent = canvas.parentElement
        if (parent && (canvas.width !== parent.clientWidth || canvas.height !== parent.clientHeight)) {
          canvas.width = parent.clientWidth
          canvas.height = parent.clientHeight
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height)

        // Draw grid
        ctx.strokeStyle = 'rgba(0, 255, 157, 0.05)'
        ctx.lineWidth = 1
        for(let i=0; i<canvas.width; i+=40) {
          ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
        }
        for(let i=0; i<canvas.height; i+=40) {
          ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke();
        }

        const nodes = meshNodes.value
        const w = canvas.width
        const h = canvas.height

        const getCoord = (p: {x:number, y:number}) => ({ x: (p.x/100)*w, y: (p.y/100)*h })

        if (nodes.A && nodes.B && nodes.C) {
          const a = getCoord(nodes.A)
          const b = getCoord(nodes.B)
          const c = getCoord(nodes.C)

          // Draw Links
          const drawLink = (p1: any, p2: any, dist: number) => {
            ctx.beginPath()
            ctx.moveTo(p1.x, p1.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.lineWidth = 2 + (dist * 5)
            const r = dist > 0.5 ? 255 : 0
            const g = dist > 0.5 ? 45 : 255
            const b_c = dist > 0.5 ? 110 : 157
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b_c}, ${0.3 + (dist * 0.7)})`
            ctx.stroke()

            // Draw disturbance waves
            if (dist > 0.2) {
              const midX = (p1.x + p2.x) / 2
              const midY = (p1.y + p2.y) / 2
              ctx.beginPath()
              ctx.arc(midX, midY, 10 + (Math.random() * 20 * dist), 0, Math.PI * 2)
              ctx.strokeStyle = `rgba(${r}, ${g}, ${b_c}, ${0.5})`
              ctx.lineWidth = 1
              ctx.stroke()
            }
          }

          drawLink(a, b, meshLinks.value.AB?.disturbance || 0)
          drawLink(b, c, meshLinks.value.BC?.disturbance || 0)
          drawLink(c, a, meshLinks.value.CA?.disturbance || 0)

          // Draw Nodes
          const drawNode = (p: any, label: string) => {
            ctx.beginPath()
            ctx.arc(p.x, p.y, 8, 0, Math.PI * 2)
            ctx.fillStyle = 'var(--cyan)'
            ctx.fill()
            ctx.shadowBlur = 10
            ctx.shadowColor = 'var(--cyan)'
            ctx.fillStyle = '#fff'
            ctx.font = '12px JetBrains Mono'
            ctx.fillText(`RPI-${label}`, p.x + 15, p.y + 4)
            ctx.shadowBlur = 0
          }
          drawNode(a, "A")
          drawNode(b, "B")
          drawNode(c, "C")
        }

        // Draw Target
        const t = getCoord(meshTarget.value)
        ctx.beginPath()
        ctx.arc(t.x, t.y, 6, 0, Math.PI * 2)
        ctx.fillStyle = 'var(--pink)'
        ctx.fill()
        ctx.shadowBlur = 15
        ctx.shadowColor = 'var(--pink)'
        ctx.stroke()
        ctx.shadowBlur = 0

        // Target pulse
        ctx.beginPath()
        ctx.arc(t.x, t.y, 10 + (Math.random()*5), 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(255, 45, 110, 0.5)'
        ctx.lineWidth = 2
        ctx.stroke()
      }
    }
    meshAnimFrame = requestAnimationFrame(renderMesh)
  }
  meshAnimFrame = requestAnimationFrame(renderMesh)
})

// Generate simulated CSI 2D array
const generateZ = (t: number) => {
  const z: number[][] = []
  for (let y = 0; y < 50; y++) {
    const row: number[] = []
    for (let x = 0; x < 50; x++) {
      // Base noise
      let val = -100 + Math.random() * 5
      // Target 1
      const distTarget1 = Math.sqrt(Math.pow(x - 25 + Math.cos(t)*10, 2) + Math.pow(y - 25 + Math.sin(t)*10, 2))
      if (distTarget1 < 10) val += 40 * (1 - distTarget1/10)

      // Target 2
      const distTarget2 = Math.sqrt(Math.pow(x - 10 + Math.sin(t*0.5)*5, 2) + Math.pow(y - 10 + Math.cos(t*0.5)*5, 2))
      if (distTarget2 < 6) val += 20 * (1 - distTarget2/6)

      // Walls / Interference shadow
      if (x > 30 && x < 40 && y > 10 && y < 20) val = -140
      if (x > 15 && x < 20 && y > 35 && y < 45) val = -135

      row.push(val)
    }
    z.push(row)
  }
  return z
}

const render3DMap = () => {
  if (activeMode.value !== '3d-map') return

  let t = 0
  const update = () => {
    if (activeMode.value !== '3d-map') return
    t += 0.2
    const zData = generateZ(t)

    const paperBg = 'rgba(0,0,0,0)'
    const plotBg = 'rgba(0,0,0,0)'
    const fontColor = 'var(--cyan)'

    // update Surface
    if (map3dSurface.value) {
      Plotly.react(map3dSurface.value, [{
        z: zData,
        type: 'surface',
        colorscale: 'Jet',
        cmin: -150,
        cmax: -20,
        showscale: true,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: '3D Signal Strength (45° view)', font: { color: fontColor } },
        margin: {l:0, r:0, b:0, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        scene: {
          zaxis: { range: [-150, 0], title: { text: 'RSSI (dBm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          xaxis: { title: { text: 'X (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          yaxis: { title: { text: 'Y (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
        }
      })
    }

    const getFloorPlanShapes = () => {
      const shapes: any[] = [];
      const lines = [
        // Outer boundaries
        [2, 2, 48, 2], [48, 2, 48, 48], [48, 48, 2, 48], [2, 48, 2, 2],
        // Rooms
        [15, 48, 15, 30], [15, 30, 2, 30], // Top left room
        [15, 48, 30, 48], [30, 48, 30, 35], [30, 35, 15, 35], // Top middle room
        [30, 48, 48, 48], [48, 35, 30, 35], // Top right room
        [15, 30, 25, 30], [25, 30, 25, 15], [25, 15, 48, 15], // Middle sections
        [35, 30, 35, 15], [2, 15, 15, 15], [15, 15, 15, 2]
      ];

      for (const [x0, y0, x1, y1] of lines) {
        shapes.push({
          type: 'line',
          x0: x0, y0: y0, x1: x1, y1: y1,
          line: { color: 'rgba(0, 255, 157, 0.6)', width: 2 }
        });
      }
      return shapes;
    }

    // update Heatmap
    if (mapTopView.value) {
      Plotly.react(mapTopView.value, [{
        z: zData,
        type: 'heatmap',
        colorscale: 'Jet',
        zmin: -150,
        zmax: -20,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: 'Top View (Floor Plan Overlay)', font: { color: fontColor } },
        margin: {l:40, r:10, b:40, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        xaxis: { title: { text: 'X (m)', font: {color: fontColor} }, tickfont: {color: fontColor} },
        yaxis: { title: { text: 'Y (m)', font: {color: fontColor} }, tickfont: {color: fontColor} },
        shapes: getFloorPlanShapes()
      })
    }

    // X-Z Plane
    if (mapSideX.value) {
      Plotly.react(mapSideX.value, [{
        z: zData,
        type: 'surface',
        colorscale: 'Jet',
        cmin: -150, cmax: -20, showscale: true,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: 'Side View (X-Z plane)', font: { color: fontColor } },
        margin: {l:0, r:0, b:0, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        scene: {
          camera: { eye: {x: 0, y: -2, z: 0} }, // look from Y
          zaxis: { range: [-150, 0], title: { text: 'RSSI (dBm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          xaxis: { title: { text: 'X (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          yaxis: { title: { text: 'Y (cm)', font: {color: fontColor} }, tickfont: {color: fontColor}, showticklabels: false }
        }
      })
    }

    // Y-Z Plane
    if (mapSideY.value) {
      Plotly.react(mapSideY.value, [{
        z: zData,
        type: 'surface',
        colorscale: 'Jet',
        cmin: -150, cmax: -20, showscale: true,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: 'Side View (Y-Z plane)', font: { color: fontColor } },
        margin: {l:0, r:0, b:0, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        scene: {
          camera: { eye: {x: -2, y: 0, z: 0} }, // look from X
          zaxis: { range: [-150, 0], title: { text: 'RSSI (dBm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          xaxis: { title: { text: 'X (cm)', font: {color: fontColor} }, tickfont: {color: fontColor}, showticklabels: false },
          yaxis: { title: { text: 'Y (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} }
        }
      })
    }

    mapAnimTimer = window.setTimeout(() => {
      mapAnimFrame = requestAnimationFrame(update)
    }, 500) // 2 FPS to not overload browser with 4 plotlys
  }
  update()
}

watch(activeMode, async (newVal) => {
    if (newVal === 'mesh') {
      await nextTick()
      startMeshAnimation()
    } else {
      if (meshAnimFrame) cancelAnimationFrame(meshAnimFrame)
    }

    if (newVal === '3d-map') {
      await nextTick()
      render3DMap()
    } else {
      if (mapAnimFrame) cancelAnimationFrame(mapAnimFrame)
      if (mapAnimTimer) clearTimeout(mapAnimTimer)
    }

    if (newVal === 'observatory') {
      await nextTick()
      initObservatory()
    } else {
      if (obsReqFrame) cancelAnimationFrame(obsReqFrame)
    }
  })

// Initialise the restored view mode after refresh (the watch above only fires on change)
onMounted(async () => {
  await nextTick()
  if (activeMode.value === 'mesh') startMeshAnimation()
  else if (activeMode.value === '3d-map') render3DMap()
  else if (activeMode.value === 'observatory') initObservatory()
})

const initObservatory = () => {
  if (!obsCanvas.value || !obsContainer.value) return;
  const canvas = obsCanvas.value;
  const container = obsContainer.value;

  const width = container.clientWidth;
  const height = container.clientHeight;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x050505);
  scene.fog = new THREE.Fog(0x050505, 10, 50);

  const camera = new THREE.PerspectiveCamera(45, width/height, 0.1, 100);
  camera.position.set(0, 10, 25);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);

  // Floor Grid Points
  const pointsGeo = new THREE.BufferGeometry();
  const pointsPos = [];
  for(let x=-20; x<=20; x+=1.5) {
    for(let z=-20; z<=20; z+=1.5) {
      pointsPos.push(x, 0.01, z);
    }
  }
  pointsGeo.setAttribute('position', new THREE.Float32BufferAttribute(pointsPos, 3));
  const pointsMat = new THREE.PointsMaterial({ color: 0x00ff9d, size: 0.15, transparent: true, opacity: 0.4 });
  const gridPoints = new THREE.Points(pointsGeo, pointsMat);
  scene.add(gridPoints);

  // Floor transparent plane
  const floorGeo = new THREE.PlaneGeometry(50, 50);
  const floorMat = new THREE.MeshBasicMaterial({ color: 0x00ff9d, transparent: true, opacity: 0.02 });
  const floorPlane = new THREE.Mesh(floorGeo, floorMat);
  floorPlane.rotation.x = -Math.PI / 2;
  scene.add(floorPlane);

  // 3 Nodes (Raspberry Pi's) with Concentric spheres
  let nodesToRender = [];
  if (activeNodes.value.length === 0) {
    // Fallback to simulated 3 nodes if none connected
    nodesToRender = [
      { position: new THREE.Vector3(-15, 2, -10), color: 0x0055ff, spheres: [] as THREE.Mesh[] },
      { position: new THREE.Vector3(15, 2, -5), color: 0xff2d6e, spheres: [] as THREE.Mesh[] },
      { position: new THREE.Vector3(0, 2, 15), color: 0x00ff9d, spheres: [] as THREE.Mesh[] },
    ];
  } else {
    // Distribute nodes dynamically in a circle
    const radius = 15;
    activeNodes.value.forEach((an, idx) => {
      const angle = (idx / activeNodes.value.length) * Math.PI * 2;
      nodesToRender.push({
        position: new THREE.Vector3(Math.cos(angle)*radius, 2, Math.sin(angle)*radius),
        color: an.color,
        spheres: [] as THREE.Mesh[]
      });
    });
  }

  nodesToRender.forEach((node, index) => {
    // Visual representation of the RPi Node
    const boxGeo = new THREE.BoxGeometry(0.8, 0.8, 0.8);
    const boxMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true });
    const box = new THREE.Mesh(boxGeo, boxMat);
    box.position.copy(node.position);
    scene.add(box);

    // Creating spheres for the waves
    for(let i=0; i<3; i++) {
      const sGeo = new THREE.SphereGeometry(1, 32, 16);
      const sMat = new THREE.MeshBasicMaterial({ color: node.color, wireframe: true, transparent: true, opacity: 0.1 });
      const sphere = new THREE.Mesh(sGeo, sMat);
      sphere.position.copy(node.position);
      // stagger the initial scale so they look asynchronous between nodes
      const startScale = (i * 10 + 1) + (index * 3);
      sphere.scale.set(startScale, startScale, startScale);
      scene.add(sphere);
      node.spheres.push(sphere);
    }
  });

  // DensePose targets
  const createSkeleton = () => {
    const group = new THREE.Group();
    // Glowing capsule
    const cGeo = new THREE.CapsuleGeometry(0.7, 2.0, 4, 16);
    const cMat = new THREE.MeshBasicMaterial({ color: 0x00ff9d, transparent: true, opacity: 0.3 });
    const capsule = new THREE.Mesh(cGeo, cMat);
    capsule.position.y = 1.7;
    group.add(capsule);

    // Add skeleton lines inside
    const lineMat = new THREE.LineBasicMaterial({ color: 0xff0000 });
    const points = [];
    points.push(new THREE.Vector3(0,3,0)); // head
    points.push(new THREE.Vector3(0,2,0)); // neck
    points.push(new THREE.Vector3(-0.8,2,0)); // left shoulder
    points.push(new THREE.Vector3(-0.8,0.5,0)); // left hand
    points.push(new THREE.Vector3(0,2,0)); // neck
    points.push(new THREE.Vector3(0.8,2,0)); // right shoulder
    points.push(new THREE.Vector3(0.8,0.5,0)); // right hand
    points.push(new THREE.Vector3(0,2,0)); // neck
    points.push(new THREE.Vector3(0,0.5,0)); // pelvis
    points.push(new THREE.Vector3(-0.4,-1.5,0)); // left foot
    points.push(new THREE.Vector3(0,0.5,0)); // pelvis
    points.push(new THREE.Vector3(0.4,-1.5,0)); // right foot
    const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
    const skeleton = new THREE.Line(lineGeo, lineMat);
    skeleton.position.y = 1.7;
    group.add(skeleton);

    // Red joint dots
    const jointGeo = new THREE.SphereGeometry(0.1, 8, 8);
    const jointMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
    points.forEach(p => {
      const j = new THREE.Mesh(jointGeo, jointMat);
      j.position.copy(p);
      j.position.y += 1.7;
      group.add(j);
    });

    return group;
  }

  const target1 = createSkeleton();
  target1.position.set(-3, 0, 0);
  scene.add(target1);

  const target2 = createSkeleton();
  target2.position.set(4, 0, 2);
  scene.add(target2);

  let time = 0;

  const renderLoop = () => {
    if (activeMode.value !== 'observatory') return;

    time += 0.01;

    // Animate spheres for all nodes
    nodesToRender.forEach(node => {
      node.spheres.forEach((s) => {
        let scale = s.scale.x + 0.05;
        if (scale > 35) scale = 0.1;
        s.scale.set(scale, scale, scale);
        // Fade out as it expands
        s.material.opacity = Math.max(0, 0.15 - (scale / 233));
      });
    });

    // Animate targets
    target1.position.x = -3 + Math.sin(time) * 3;
    target1.position.z = Math.cos(time * 0.5) * 2;

    target2.position.x = 4 + Math.cos(time * 0.8) * 4;
    target2.position.z = 2 + Math.sin(time * 1.2) * 3;

    // Slowly rotate camera
    camera.position.x = Math.sin(time * 0.1) * 25;
    camera.position.z = Math.cos(time * 0.1) * 25;
    camera.lookAt(0, 2, 0);

    renderer.render(scene, camera);
    obsReqFrame = requestAnimationFrame(renderLoop);
  }

  renderLoop();
}

onUnmounted(() => {
  if (wifiWs) wifiWs.close()
  if (chart) chart.destroy()
  if (meshAnimFrame) cancelAnimationFrame(meshAnimFrame)
  if (mapAnimFrame) cancelAnimationFrame(mapAnimFrame)
  if (mapAnimTimer) clearTimeout(mapAnimTimer)
  if (obsReqFrame) cancelAnimationFrame(obsReqFrame)
  if (telemetryInterval) clearInterval(telemetryInterval)
})
// --- End Wifi Script ---


const store = useNodesStore()

interface BluetoothDevice {
  mac: string
  name: string
  rssi: number
  last_seen: number
  azimuth?: number
  manufacturer_data?: Record<string, string>
  service_uuids?: string[]
  tx_power?: number
  enum_data?: any
  enumerating?: boolean
  nodes?: Record<string, { rssi: number, last_seen: number }>
}

const devices = ref<BluetoothDevice[]>([])
const selectedDevice = ref<BluetoothDevice | null>(null)
const connected = ref(false)
const triangulationMode = ref(false)
const jammedTargets = ref<Record<string, boolean>>({})
let btWs: WebSocket | null = null

const pairingModalVisible = ref(false)
const isPairing = ref(false)
const pairingStatus = ref('')

const reconModalVisible = ref(false)
const reconData = ref('')

async function injectRecon(nid: string) {
  reconModalVisible.value = true
  reconData.value = "Initiating Advanced Recon Agent deployment to " + nid + "..."
  try {
    const res = await fetch(`/api/nodes/${nid}/recon/inject`, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    reconData.value = data.detail || data.message || "Unknown error"
  } catch (err) {
    reconData.value = "Deploy Error: " + err
  }
}

async function stopRecon(nid: string) {
  reconModalVisible.value = true
  reconData.value = "Sending kill signal to Recon Agent..."
  try {
    const res = await fetch(`/api/nodes/${nid}/recon/stop`, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    reconData.value = data.detail || data.message || "Unknown error"
  } catch (err) {
    reconData.value = "Stop Error: " + err
  }
}

async function fetchRecon(nid: string) {
  reconData.value = 'Intercepting reconnaissance data stream from ' + nid + '...'
  reconModalVisible.value = true
  try {
    const res = await fetch(`/api/nodes/${nid}/recon/fetch`, {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    if (!data.data) {
      reconData.value = "No recon data intercepted. Verify if agent is actively running."
    } else {
      reconData.value = data.data
    }
  } catch (err) {
    reconData.value = "Fetch Error: " + err
  }
}

const sortedDevices = computed(() => {
  let list = devices.value

  // If a specific node is selected, only show devices seen by that node
  // and use that node's specific RSSI.
  if (store.selectedId) {
    list = list.filter(d => d.nodes && d.nodes[store.selectedId])
    list = list.map(d => ({
      ...d,
      rssi: d.nodes[store.selectedId].rssi
    }))
  }

  return [...list].sort((a, b) => b.rssi - a.rssi)
})

async function toggleJam(mac: string) {
  const query = store.selectedId ? `?node_id=${store.selectedId}` : ''
  const isJamming = jammedTargets.value[mac]
  const endpoint = isJamming ? `/api/bluetooth/unjam/${mac}${query}` : `/api/bluetooth/jam/${mac}${query}`

  try {
    const res = await fetch(endpoint, { method: 'POST' })
    const data = await res.json()
    if (data.status.includes('engaged') || data.status.includes('already')) {
      jammedTargets.value[mac] = true
    } else {
      delete jammedTargets.value[mac]
    }
  } catch (e) {
    console.error("Jam API failed", e)
  }
}

async function confirmPairing() {
  if (!selectedDevice.value) return
  isPairing.value = true
  pairingStatus.value = 'Initiating pairing sequence...'
  try {
    const res = await fetch(`/api/bluetooth/pair/${selectedDevice.value.mac}`, { method: 'POST' })
    const data = await res.json()
    pairingStatus.value = `[${data.status.toUpperCase()}] ${data.message}`
  } catch (e: any) {
    pairingStatus.value = `[ERROR] ${e.message}`
  } finally {
    isPairing.value = false
  }
}

async function toggleNodeBluetooth(enable: boolean) {
  if (!store.selectedId) return
  const cmds = enable ?
    ["bluetoothctl power on || sudo rfkill unblock bluetooth"] :
    ["bluetoothctl power off || sudo rfkill block bluetooth"]

  try {
    const res = await fetch(`/api/nodes/${store.selectedId}/execute`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ commands: cmds })
    })
    const data = await res.json()
    console.log("Toggle BT output:", data)

    const outStr = JSON.stringify(data).toLowerCase()
    if (outStr.includes("fail") || outStr.includes("not found")) {
      showToast(`Command failed on node ${store.selectedId}`, 'error')
    } else {
      showToast(`Bluetooth command sent to node ${store.selectedId}`, 'success')
    }
  } catch (err) {
    console.error(err)
    showToast("Failed to change Bluetooth state", 'error')
  }
}

async function enumerateDevice(mac: string) {
  const idx = devices.value.findIndex(d => d.mac === mac)
  if (idx === -1) return

  devices.value[idx].enumerating = true
  if (selectedDevice.value && selectedDevice.value.mac === mac) {
    selectedDevice.value.enumerating = true
  }

  try {
    const res = await fetch(`/api/bluetooth/enumerate/${mac}`, { method: 'POST' })
    const data = await res.json()
    if (data.status === 'success') {
      devices.value[idx].enum_data = data.services
      if (selectedDevice.value && selectedDevice.value.mac === mac) {
        selectedDevice.value.enum_data = data.services
      }
    } else {
      console.error("Enumeration failed", data.error)
      showToast("Enumeration failed: " + data.error, 'error')
    }
  } catch (e) {
    console.error("Enumerate API failed", e)
  } finally {
    devices.value[idx].enumerating = false
    if (selectedDevice.value && selectedDevice.value.mac === mac) {
      selectedDevice.value.enumerating = false
    }
  }
}

function getRssiClass(rssi: number) {
  if (rssi > -60) return 'signal-strong'
  if (rssi > -80) return 'signal-med'
  return 'signal-weak'
}

function rssiToDistance(rssi: number): string {
  // Distance = 10 ^ ((TxPower - RSSI) / (10 * N))
  const txPower = -59
  const n = 2.0
  if (!rssi) return "?"
  const dist = Math.pow(10, (txPower - rssi) / (10 * n))
  return dist.toFixed(1)
}

function getBlipStyle(dev: BluetoothDevice) {
  // Map RSSI (-100 to -40) to distance from center (100% to 0%)
  // -40 is very close (radius ~ 10%), -100 is far (radius ~ 90%)
  let distance = (Math.abs(dev.rssi) - 30) / 70
  distance = Math.max(0.1, Math.min(0.95, distance))

  let angle = 0;

  if (dev.azimuth !== undefined) {
    // True hardware AoA angle
    angle = dev.azimuth
  } else {
    // Fallback: Use MAC address to generate a stable pseudo-random angle
    let hash = 0
    for (let i = 0; i < dev.mac.length; i++) {
      hash = dev.mac.charCodeAt(i) + ((hash << 5) - hash)
    }
    angle = Math.abs(hash % 360)
  }

  // subtract 90 so 0 is "North" (top)
  const rad = (angle - 90) * (Math.PI / 180)
  const cx = 50 + distance * 50 * Math.cos(rad)
  const cy = 50 + distance * 50 * Math.sin(rad)

  return {
    left: `${cx}%`,
    top: `${cy}%`,
    /* Let CSS classes handle the color for Aliens theme */
  }
}

const triangulationData = computed(() => {
  const result = {
    nodes: {} as Record<string, { x: number, y: number }>,
    target: { x: 50, y: 50 }
  };

  if (!selectedDevice.value || !selectedDevice.value.nodes) return result;

  const nodeKeys = Object.keys(selectedDevice.value.nodes);
  if (nodeKeys.length === 0) return result;

  // Faste positioner til noderne (i en ring på 40% afstand fra midten)
  nodeKeys.forEach((nid, index) => {
    if (nodeKeys.length === 1) {
      result.nodes[nid] = { x: 50, y: 50 }; // Placer i midten, hvis der kun er 1 node
    } else {
      const angle = (360 / nodeKeys.length) * index;
      const rad = (angle - 90) * (Math.PI / 180);
      result.nodes[nid] = {
        x: 50 + 40 * Math.cos(rad),
        y: 50 + 40 * Math.sin(rad)
      };
    }
  });

  if (nodeKeys.length === 1) {
    // Falsk sonar-visning hvis der kun er 1 node (som før)
    const nid = nodeKeys[0];
    const ndata = selectedDevice.value.nodes[nid];
    let distance = (Math.abs(ndata.rssi) - 30) / 70;
    distance = Math.max(0.15, Math.min(0.95, distance));

    let hash = 0;
    for (let i = 0; i < selectedDevice.value.mac.length; i++) {
      hash = selectedDevice.value.mac.charCodeAt(i) + ((hash << 5) - hash);
    }
    const angle = Math.abs(hash % 360);
    const rad = (angle - 90) * (Math.PI / 180);

    result.target = {
      x: 50 + distance * 50 * Math.cos(rad),
      y: 50 + distance * 50 * Math.sin(rad)
    };
  } else {
    // Ægte Trilateration (Weighted Average / Center of Mass)
    let totalWeight = 0;
    let sumX = 0;
    let sumY = 0;

    nodeKeys.forEach(nid => {
      const ndata = selectedDevice.value!.nodes![nid];
      const dist = Math.pow(10, (-59 - ndata.rssi) / 20); // Simpel path loss model
      const weight = 1 / (dist + 0.1); // Undgå division by zero

      sumX += result.nodes[nid].x * weight;
      sumY += result.nodes[nid].y * weight;
      totalWeight += weight;
    });

    result.target = {
      x: sumX / totalWeight,
      y: sumY / totalWeight
    };
  }

  return result;
});

onMounted(() => {
  const btWsUrl = `${wsBase()}/api/bluetooth/btWs${wsTokenParam()}`
  btWs = new WebSocket(btWsUrl)

  btWs.onopen = () => {
    connected.value = true
  }

  btWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'init') {
        devices.value = data.devices
      } else if (data.type === 'device_update') {
        const idx = devices.value.findIndex(d => d.mac === data.device.mac)
        if (idx !== -1) {
          devices.value[idx] = data.device
        } else {
          devices.value.push(data.device)
        }
        if (selectedDevice.value && selectedDevice.value.mac === data.device.mac) {
          selectedDevice.value = data.device
        }
      } else if (data.type === 'device_removed') {
        devices.value = devices.value.filter(d => d.mac !== data.mac)
        if (selectedDevice.value && selectedDevice.value.mac === data.mac) {
          selectedDevice.value = null
        }
      }
    } catch (e) {
      console.error("Failed to parse BT WS message", e)
    }
  }

  btWs.onclose = () => {
    connected.value = false
  }
})

onUnmounted(() => {
  if (btWs) {
    btWs.close()
  }
})
// --- End Bluetooth Script ---

</script>

<style scoped>

.network-controller-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.tabs-nav {
  display: flex;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
}
.tabs-nav button {
  padding: 10px 20px;
  background: transparent;
  border: none;
  color: var(--text);
  cursor: pointer;
  font-family: var(--font-hd);
  font-size: 14px;
}
.tabs-nav button.active {
  color: #00e5ff;
  border-bottom: 2px solid #00e5ff;
}
.tabs-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}
.tab-pane {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  overflow: auto;
}

/* --- Config Styles --- */
.infrastructure-view {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  color: var(--textbr);
}
.panel-header {
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  padding-bottom: 10px;
}
.glass-panel {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(0, 229, 255, 0.2);
  padding: 20px;
  border-radius: 4px;
}
.btn-cyan {
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 8px 16px;
  cursor: pointer;
  margin-top: 10px;
}
.btn-cyan:hover {
  background: var(--cyan);
  color: #000;
}
/* --- Clients Styles --- */
.clients-view { padding: 20px; height: 100%; color: var(--textbr); }
.panel-header { margin-bottom: 20px; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 10px; }
.glass-panel { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 229, 255, 0.2); padding: 20px; border-radius: 4px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(0, 229, 255, 0.1); }
/* --- Traffic Styles --- */
.traffic-analytics-view { padding: 20px; height: 100%; color: var(--textbr); }
.panel-header { margin-bottom: 20px; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 10px; }
.glass-panel { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 229, 255, 0.2); padding: 20px; border-radius: 4px; }
.text-center { text-align: center; }
/* --- Hotspot Styles --- */
.hotspot-manager-view { padding: 20px; height: 100%; color: var(--textbr); }
.panel-header { margin-bottom: 20px; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 10px; }
.glass-panel { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 229, 255, 0.2); padding: 20px; border-radius: 4px; }
.btn-cyan { background: rgba(0, 229, 255, 0.1); border: 1px solid var(--cyan); color: var(--cyan); padding: 8px 16px; cursor: pointer; margin-top: 10px; }
.btn-cyan:hover { background: var(--cyan); color: #000; }
/* --- Wifi Styles --- */
.wifi-container {
  display: flex;
  width: 100%;
  height: 100%;
  background: #020408;
  color: #fff;
  font-family: 'JetBrains Mono', monospace;
}

.wifi-sidebar {
  width: 300px;
  background: rgba(10, 20, 40, 0.6);
  border-right: 1px solid rgba(0, 255, 157, 0.3);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.wifi-sidebar h2 {
  color: var(--cyan);
  font-size: 1.2rem;
  letter-spacing: 2px;
  margin: 0;
  text-shadow: 0 0 10px rgba(0, 255, 157, 0.5);
}

.wifi-sidebar h3 {
  color: #888;
  font-size: 0.9rem;
  margin-top: 0;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 5px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
  background: rgba(0, 255, 157, 0.05);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 4px;
}

.node-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #444;
}

.node-dot.active {
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
}

.node-name {
  font-weight: bold;
}

.node-controls {
  display: flex;
  gap: 5px;
  margin-top: 5px;
}

.ctrl-btn {
  background: transparent;
  border: 1px solid #555;
  color: #888;
  padding: 2px 6px;
  font-size: 10px;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.2s;
}

.ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-color: #888;
}

.start-btn:hover {
  color: var(--cyan);
  border-color: var(--cyan);
  background: rgba(0, 255, 157, 0.1);
}

.stop-btn:hover {
  color: #ffb800;
  border-color: #ffb800;
  background: rgba(255, 184, 0, 0.1);
}

.delete-btn:hover {
  color: var(--pink);
  border-color: var(--pink);
  background: rgba(255, 45, 110, 0.1);
}

.node-interface {
  font-size: 0.8rem;
  color: #aaa;
}

.stats-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.highlight {
  color: var(--cyan);
}

.highlight-alert {
  color: var(--pink);
  font-weight: bold;
  animation: flash 1s infinite alternate;
}

@keyframes flash {
  from { text-shadow: 0 0 5px var(--pink); }
  to { text-shadow: 0 0 20px var(--pink), 0 0 30px var(--pink); }
}

.wifi-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 30px;
  gap: 20px;
  position: relative;
}

.mode-toggle {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.mode-toggle button {
  background: rgba(0, 255, 157, 0.05);
  border: 1px solid rgba(0, 255, 157, 0.3);
  color: #aaa;
  padding: 8px 16px;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.mode-toggle button:hover {
  background: rgba(0, 255, 157, 0.1);
  color: var(--cyan);
}

.mode-toggle button.active {
  background: rgba(0, 255, 157, 0.2);
  border-color: var(--cyan);
  color: #fff;
  text-shadow: 0 0 5px var(--cyan);
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.2);
}

.single-mode, .mesh-mode, .map3d-mode {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.glitch-title {
  color: var(--cyan);
  font-size: 1.5rem;
  letter-spacing: 2px;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--cyan);
  font-size: 0.9rem;
  border: 1px solid var(--cyan);
  padding: 4px 10px;
  border-radius: 4px;
  background: rgba(0, 255, 157, 0.1);
}

.pulse {
  width: 8px;
  height: 8px;
  background: var(--cyan);
  border-radius: 50%;
  animation: heartbeat 1s infinite;
}

@keyframes heartbeat {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.chart-container {
  flex: 2;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  padding: 20px;
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.5);
  min-height: 200px;
}

.decoders-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  flex: 3;
}

.decoder-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  padding: 20px;
}

.decoder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.glitch-title-sm {
  color: var(--cyan);
  font-size: 1.1rem;
  letter-spacing: 1px;
}

.alert-badge {
  color: #ffc000;
  border-color: #ffc000;
  background: rgba(255, 192, 0, 0.1);
}

.sim-tag {
  font-size: 0.65rem;
  letter-spacing: 1px;
  color: #ffb800;
  border: 1px solid #ffb800;
  background: rgba(255, 184, 0, 0.08);
  padding: 2px 6px;
  border-radius: 3px;
  cursor: help;
}

.vital-readout {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1;
}
.vital-resp {
  color: var(--cyan);
  font-size: 1.6rem;
  font-weight: bold;
  text-shadow: 0 0 8px rgba(0, 255, 157, 0.5);
}
.vital-unit {
  color: #888;
  font-size: 0.65rem;
  letter-spacing: 1px;
}
.vital-hint {
  color: #666;
  font-size: 0.7rem;
  font-style: italic;
}

.pulse-alert {
  width: 8px;
  height: 8px;
  background: #ffc000;
  border-radius: 50%;
  animation: heartbeat 0.5s infinite;
}

.decoder-terminal {
  flex: 1;
  background: #000;
  border: 1px solid #333;
  padding: 15px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  overflow-y: auto;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
  white-space: pre-wrap;
  word-wrap: break-word;
  display: flex;
  flex-direction: column;
}

.behavior-terminal {
  justify-content: flex-end;
}

.decoder-content {
  flex: 1;
  background: #000;
  border: 1px solid #333;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
}

.terminal-text {
  color: var(--cyan);
  text-shadow: 0 0 5px var(--cyan);
}

.speech-log { color: #00d2ff; text-shadow: 0 0 5px #00d2ff; }
.gesture-log { color: #ffc000; text-shadow: 0 0 5px #ffc000; }

.cursor {
  color: var(--cyan);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* ECG Line */
.heartbeat-line {
  width: 100%;
  height: 2px;
  background: var(--pink);
  box-shadow: 0 0 10px var(--pink);
  position: relative;
}
.heartbeat-line::after {
  content: '';
  position: absolute;
  top: -20px;
  left: 50%;
  width: 20px;
  height: 40px;
  border-left: 2px solid var(--pink);
  border-right: 2px solid var(--pink);
  transform: skewX(-30deg);
  box-shadow: 0 0 10px var(--pink);
  animation: beat 1s infinite;
}
@keyframes beat {
  0%, 100% { transform: skewX(-30deg) scaleY(1); }
  50% { transform: skewX(-30deg) scaleY(1.5); }
}

/* Radar Scope */
.radar-scope {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  border: 2px solid var(--cyan);
  position: relative;
  background: radial-gradient(circle, rgba(0,255,157,0.1) 0%, rgba(0,0,0,1) 70%);
  box-shadow: 0 0 20px rgba(0,255,157,0.2);
}
.radar-scope::before {
  content: '';
  position: absolute;
  top: 50%; left: 0; right: 0; height: 1px;
  background: rgba(0,255,157,0.3);
}
.radar-scope::after {
  content: '';
  position: absolute;
  left: 50%; top: 0; bottom: 0; width: 1px;
  background: rgba(0,255,157,0.3);
}
.radar-sweep {
  position: absolute;
  top: 0; left: 50%;
  width: 50%; height: 50%;
  background: linear-gradient(90deg, rgba(0,255,157,0) 0%, rgba(0,255,157,0.8) 100%);
  transform-origin: bottom left;
  animation: sweep 2s linear infinite;
}
@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.radar-blip {
  position: absolute;
  width: 8px;
  height: 8px;
  background: var(--pink);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 10px var(--pink);
  animation: blipfade 2s infinite;
}
@keyframes blipfade {
  0% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(2); }
}

/* Mesh Mode Styles */
.mesh-container {
  display: flex;
  flex: 1;
  gap: 20px;
  height: 100%;
}

.mesh-map-panel {
  flex: 3;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.5);
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.mesh-canvas-container {
  flex: 1;
  position: relative;
  background: #000;
  border: 1px solid #333;
}

.mesh-telemetry-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  padding: 20px;
}

.link-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(0, 0, 0, 0.5);
  padding: 15px;
  border: 1px solid #333;
  border-radius: 4px;
}

.link-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.link-name {
  color: #fff;
  font-weight: bold;
}

.link-dist {
  color: var(--cyan);
}

.link-dist.high-dist {
  color: var(--pink);
  animation: flash 1s infinite alternate;
}

.link-bar-bg {
  height: 8px;
  background: #222;
  border-radius: 4px;
  overflow: hidden;
}

.link-bar-fill {
  height: 100%;
  transition: width 0.1s linear, background-color 0.2s;
}

/* 3D Map Mode Styles */
.map3d-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  flex: 1;
  height: 100%;
}

.map3d-panel {
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.5);
  display: flex;
  padding: 10px;
}

.plotly-container {
  width: 100%;
  height: 100%;
  border-radius: 4px;
}

/* Observatory Mode Styles */
.observatory-mode {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
}

.obs-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #050505;
}

.obs-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.obs-top {
  position: absolute;
  top: 20px;
  left: 20px;
  pointer-events: none;
  z-index: 10;
}

.obs-top h2 {
  color: var(--cyan);
  font-size: 24px;
  margin: 0;
  font-weight: bold;
}

.obs-sub {
  color: #888;
  font-size: 10px;
  letter-spacing: 2px;
}

.obs-ui {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 10;
}

.obs-ui-left {
  left: 20px;
}

.obs-ui-right {
  right: 20px;
}

.obs-panel {
  background: rgba(10, 15, 25, 0.7);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 12px;
  padding: 20px;
  width: 220px;
  backdrop-filter: blur(5px);
  box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

.obs-panel-title {
  color: #888;
  font-size: 10px;
  letter-spacing: 2px;
  margin-bottom: 20px;
}

.obs-stat {
  margin-bottom: 10px;
  position: relative;
  padding-left: 30px;
}

.obs-icon {
  position: absolute;
  left: 0;
  top: 5px;
  font-size: 16px;
}

.obs-val {
  display: flex;
  align-items: baseline;
  gap: 5px;
}

.obs-num {
  font-size: 24px;
  color: var(--cyan);
  font-weight: bold;
}

.obs-unit {
  font-size: 12px;
  color: #888;
}

.obs-label {
  font-size: 10px;
  color: #666;
  letter-spacing: 1px;
}

.obs-divider {
  height: 1px;
  background: rgba(255,255,255,0.05);
  margin: 15px 0;
}

.obs-bar {
  height: 4px;
  background: rgba(255,255,255,0.1);
  margin-top: 5px;
  border-radius: 2px;
  overflow: hidden;
}

.obs-bar-fill {
  height: 100%;
}

.obs-row {
  display: flex;
  justify-content: space-between;
  color: #888;
  font-size: 12px;
  margin-bottom: 10px;
}

.obs-wave {
  height: 20px;
  border-bottom: 2px solid #0088ff;
  border-radius: 50%;
  margin: 20px 0;
  box-shadow: 0 10px 20px -10px #0088ff;
}

.obs-btn-active {
  background: rgba(255, 184, 0, 0.1);
  border: 1px solid #ffb800;
  color: #ffb800;
  text-align: center;
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  letter-spacing: 2px;
}

/* Node Manager Styles */
.node-manager {
  margin-top: 15px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 255, 157, 0.2);
  padding: 15px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.mode-switch {
  display: flex;
  gap: 10px;
}

.mode-switch button {
  background: transparent;
  border: 1px solid #555;
  color: #888;
  padding: 8px 12px;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-size: 11px;
}

.mode-switch button.active {
  background: rgba(0, 255, 157, 0.1);
  border-color: var(--cyan);
  color: var(--cyan);
}

.mode-switch button.danger-active {
  background: rgba(255, 45, 110, 0.1);
  border-color: var(--pink);
  color: var(--pink);
}

.mode-switch button.danger-btn:hover {
  border-color: var(--pink);
  color: var(--pink);
}

.divider {
  width: 1px;
  height: 30px;
  background: #333;
}

.record-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rec-btn {
  background: transparent;
  border: 1px solid var(--pink);
  color: var(--pink);
  padding: 8px 15px;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rec-btn:hover {
  background: rgba(255, 45, 110, 0.1);
}

.rec-btn.recording {
  background: rgba(255, 45, 110, 0.2);
  animation: pulse-red 1s infinite;
}

.rec-dot {
  width: 10px;
  height: 10px;
  background: var(--pink);
  border-radius: 50%;
  display: inline-block;
}

.stop-square {
  width: 10px;
  height: 10px;
  background: var(--pink);
  display: inline-block;
}

.download-link {
  color: var(--cyan);
  font-family: 'Orbitron', sans-serif;
  font-size: 11px;
  text-decoration: none;
  cursor: pointer;
}

.download-link:hover {
  text-decoration: underline;
}

@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(255, 45, 110, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(255, 45, 110, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 45, 110, 0); }
}

.advanced-stream-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 450px;
  height: 300px;
  background: rgba(10, 15, 20, 0.95);
  border: 1px solid #ffb800;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  z-index: 1000;
  box-shadow: 0 0 20px rgba(255, 184, 0, 0.2);
}

.advanced-header {
  background: #ffb800;
  color: #000;
  font-family: 'Orbitron', sans-serif;
  font-weight: bold;
  font-size: 12px;
  padding: 8px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  background: transparent;
  border: none;
  color: #000;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
}

.advanced-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  font-family: 'JetBrains Mono', monospace;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  backdrop-filter: blur(5px);
}

.modal-content.glitch-box {
  background: rgba(10, 15, 20, 0.95);
  border: 1px solid var(--cyan);
  border-radius: 4px;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 0 20px rgba(0, 255, 157, 0.2);
}

.modal-header {
  background: rgba(0, 255, 157, 0.1);
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 255, 157, 0.3);
}

.modal-header h2 {
  color: var(--cyan);
  margin: 0;
  font-family: 'Orbitron', sans-serif;
  font-size: 14px;
  letter-spacing: 1px;
}

.modal-header .close-btn {
  color: var(--cyan);
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
}

.form-row {
  display: flex;
  gap: 15px;
}

.form-group label {
  color: #888;
  font-size: 11px;
  letter-spacing: 1px;
}

.hack-input, .hack-select {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #333;
  color: var(--cyan);
  padding: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
}

.hack-input:focus, .hack-select:focus {
  outline: none;
  border-color: var(--cyan);
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.2);
}

.modal-footer {
  padding: 15px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid rgba(0, 255, 157, 0.2);
}

.hack-btn {
  padding: 10px 20px;
  font-family: 'Orbitron', sans-serif;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid;
  background: transparent;
  transition: all 0.2s;
}

.hack-btn.primary {
  color: var(--cyan);
  border-color: var(--cyan);
  background: rgba(0, 255, 157, 0.1);
}

.hack-btn.primary:hover {
  background: rgba(0, 255, 157, 0.3);
  box-shadow: 0 0 15px rgba(0, 255, 157, 0.4);
}

.hack-btn.secondary {
  color: #aaa;
  border-color: #555;
}

.hack-btn.secondary:hover {
  color: #fff;
  border-color: #888;
}

.deploy-btn {
  background: rgba(0, 255, 157, 0.1);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 10px 20px;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-weight: bold;
  letter-spacing: 1px;
  transition: all 0.2s;
}

.deploy-btn:hover {
  background: rgba(0, 255, 157, 0.3);
  box-shadow: 0 0 15px rgba(0, 255, 157, 0.4);
}

.log-line {
  border-bottom: 1px solid rgba(0, 255, 157, 0.1);
  padding: 4px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.node-input-group {
  display: flex;
  gap: 10px;
}

.node-input {
  background: #000;
  border: 1px solid #333;
  color: var(--cyan);
  padding: 8px 15px;
  font-family: monospace;
  outline: none;
  width: 250px;
}

.node-input:focus {
  border-color: var(--cyan);
}

.node-btn {
  background: rgba(0, 255, 157, 0.1);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 8px 15px;
  cursor: pointer;
  font-weight: bold;
}

.node-btn:hover {
  background: rgba(0, 255, 157, 0.3);
}

.active-nodes-list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.no-nodes {
  color: #888;
  font-size: 12px;
  font-style: italic;
}

.node-badge {
  display: flex;
  align-items: center;
  background: rgba(10, 20, 30, 0.8);
  border: 1px solid;
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 12px;
  color: #fff;
}

.node-badge-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  box-shadow: 0 0 5px currentColor;
}

.node-ip {
  font-family: monospace;
  margin-right: 10px;
}

.node-remove {
  background: transparent;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

.node-remove:hover {
  color: var(--pink);
}
/* --- Bluetooth Styles --- */
.bt-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  color: var(--textwh);
  font-family: var(--font-ui);
}

.bt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
}

.header-title {
  font-family: var(--font-hd);
  font-size: 18px;
  letter-spacing: 2px;
  color: #00e5ff;
  display: flex;
  align-items: center;
  gap: 12px;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pink);
  box-shadow: 0 0 8px var(--pink);
}
.pulse.active {
  background: #00e5ff;
  box-shadow: 0 0 10px #00e5ff;
  animation: pulse-anim 2s infinite alternate;
}
@keyframes pulse-anim {
  from { opacity: 0.5; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1.2); }
}

.header-stats {
  font-family: var(--font-hd);
  font-size: 12px;
  color: var(--text);
  letter-spacing: 1px;
}

.bt-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.aliens-theme {
  --alien-green: #4ade80;
  --alien-dark: #064e3b;
  --alien-bg: #022c22;
  --alien-text: #bbf7d0;
  background: radial-gradient(circle at center, var(--alien-bg) 0%, #000 100%) !important;
}

.radar-container {
  flex: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at center, var(--bg2) 0%, var(--bg) 100%);
  position: relative;
  overflow: hidden;
}

.radar-crt-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(0,0,0,0.15),
    rgba(0,0,0,0.15) 1px,
    transparent 1px,
    transparent 2px
  );
  pointer-events: none;
  z-index: 10;
}

.closest-range {
  position: absolute;
  bottom: 32px;
  left: 32px;
  display: flex;
  flex-direction: column;
  background: rgba(2, 44, 34, 0.8);
  border: 2px solid var(--alien-green);
  padding: 12px 24px;
  border-radius: 4px;
  box-shadow: 0 0 15px rgba(74, 222, 128, 0.2);
  z-index: 5;
}
.range-label {
  color: var(--alien-green);
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 2px;
  opacity: 0.8;
}
.range-val {
  color: #fff;
  font-family: var(--font-co);
  font-size: 32px;
  font-weight: bold;
  text-shadow: 0 0 10px var(--alien-green);
}

.radar {
  width: 500px;
  height: 500px;
  border-radius: 50%;
  position: relative;
  background: rgba(74, 222, 128, 0.05);
  box-shadow: 0 0 40px rgba(74, 222, 128, 0.1), inset 0 0 50px rgba(74, 222, 128, 0.1);
  overflow: hidden;
  border: 2px solid var(--alien-green);
}

.radar::after {
  content: "N";
  position: absolute;
  top: 5px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--alien-green);
  font-family: var(--font-hd);
  font-size: 14px;
  opacity: 0.8;
}

.ring {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px dashed rgba(74, 222, 128, 0.3);
}
.r1 { width: 25%; height: 25%; }
.r2 { width: 50%; height: 50%; }
.r3 { width: 75%; height: 75%; border-style: solid; border-width: 2px; border-color: rgba(74, 222, 128, 0.4); }
.r4 { width: 100%; height: 100%; }

.crosshair-v, .crosshair-h {
  position: absolute;
  background: rgba(74, 222, 128, 0.2);
}
.crosshair-v { top: 0; bottom: 0; left: 50%; width: 1px; transform: translateX(-50%); }
.crosshair-h { left: 0; right: 0; top: 50%; height: 1px; transform: translateY(-50%); }

.sweep {
  position: absolute;
  top: 50%; left: 50%;
  width: 50%; height: 50%;
  transform-origin: 0% 0%;
  background: conic-gradient(from 0deg, transparent 70%, rgba(74, 222, 128, 0.6) 100%);
  animation: sweep 3s linear infinite;
  pointer-events: none;
}

@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.blip {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 15px #fff, 0 0 30px var(--alien-green);
  cursor: pointer;
  transition: all 0.3s;
  z-index: 2;
}
.blip.true-aoa {
  background: #ff3333;
  box-shadow: 0 0 15px #ff3333, 0 0 30px #ff0000;
}
.blip:hover {
  transform: translate(-50%, -50%) scale(1.5);
  background: #fff;
}

.blip-ripple {
  position: absolute;
  top: 50%; left: 50%;
  width: 100%; height: 100%;
  border-radius: 50%;
  border: 2px solid #fff;
  transform: translate(-50%, -50%);
  animation: blip-ping 1.5s ease-out infinite;
}
@keyframes blip-ping {
  0% { width: 100%; height: 100%; opacity: 1; }
  100% { width: 400%; height: 400%; opacity: 0; }
}

.blip-label {
  position: absolute;
  top: 16px; left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  font-family: var(--font-co);
  font-weight: bold;
  white-space: nowrap;
  color: var(--alien-text);
  pointer-events: none;
  background: rgba(2, 44, 34, 0.8);
  padding: 2px 6px;
  border: 1px solid rgba(74, 222, 128, 0.4);
  border-radius: 2px;
}

.device-list {
  flex: 1;
  min-width: 300px;
  max-width: 400px;
  border-left: 1px solid var(--border);
  background: var(--bg2);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.device-list h3, .device-details h3 {
  padding: 16px;
  margin: 0;
  font-family: var(--font-hd);
  font-size: 13px;
  letter-spacing: 2px;
  color: var(--cyan);
  border-bottom: 1px solid var(--border);
  background: rgba(0,0,0,0.2);
}

.empty-list {
  padding: 24px;
  text-align: center;
  color: var(--text);
  font-size: 12px;
  letter-spacing: 1px;
}

.device-card {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.2s;
}
.device-card:hover {
  background: rgba(0, 229, 255, 0.05);
}
.device-card.selected {
  background: rgba(0, 229, 255, 0.1);
  border-left: 3px solid var(--cyan);
}

.card-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.dev-name {
  font-weight: 600;
  font-size: 13px;
}
.dev-rssi {
  font-family: var(--font-co);
  font-size: 11px;
}

.card-body {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text);
  font-family: var(--font-co);
}

.device-details {
  flex: 1;
  min-width: 300px;
  max-width: 350px;
  border-left: 1px solid var(--border);
  background: var(--bg);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.detail-row .lbl {
  color: var(--text);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 1px;
}
.detail-row .val {
  font-family: var(--font-co);
}

.detail-row .val-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-family: var(--font-co);
  text-align: right;
  font-size: 11px;
}
.gatt-box {
  text-align: left !important;
  margin-top: 8px;
  background: rgba(0,0,0,0.2);
  padding: 8px;
  border-radius: 4px;
  width: 100%;
}
.gatt-service {
  margin-bottom: 8px;
}
.gatt-service:last-child {
  margin-bottom: 0;
}
.gatt-title {
  color: var(--pink);
  font-size: 10px;
  margin-bottom: 4px;
  border-bottom: 1px solid rgba(255,51,102,0.2);
  padding-bottom: 2px;
}
.gatt-char {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2px;
}
.gatt-char .cname { color: var(--text); }
.gatt-char .cval { color: var(--cyan); text-align: right; word-break: break-all; max-width: 60%; }

.actions {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.btn-action {
  padding: 12px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 1px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-action:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.1);
}
.btn-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  color: var(--text);
}

.btn-danger {
  color: #ff3333 !important;
  border-color: rgba(255, 51, 51, 0.4) !important;
  cursor: pointer !important;
  opacity: 1 !important;
}
.btn-danger:hover {
  background: rgba(255, 51, 51, 0.1) !important;
}
.jamming-active {
  animation: bg-pulse-red 1s infinite alternate;
  color: #fff !important;
}

@keyframes bg-pulse-red {
  from { background: rgba(255, 51, 51, 0.2); }
  to { background: rgba(255, 51, 51, 0.6); }
}

.jamming-target .blip-ripple {
  border-color: #ff0000;
  animation-duration: 0.5s; /* Faster ripples */
}

.jamming-lightning {
  position: absolute;
  top: -20px; left: -20px; right: -20px; bottom: -20px;
  background: radial-gradient(circle, transparent 20%, rgba(255,0,0,0.5) 80%);
  border-radius: 50%;
  animation: spin-zap 0.5s infinite linear;
  pointer-events: none;
}

@keyframes spin-zap {
  0% { transform: rotate(0deg) scale(1); opacity: 0.8; }
  50% { transform: rotate(180deg) scale(1.2); opacity: 1; }
  100% { transform: rotate(360deg) scale(1); opacity: 0.8; }
}

.signal-strong { color: var(--green); }
.signal-med { color: var(--yellow); }
.signal-weak { color: var(--pink); }

.node-blip {
  background: var(--cyan);
  box-shadow: 0 0 10px var(--cyan);
  z-index: 100;
}
.node-label {
  position: absolute;
  top: -20px;
  left: -20px;
  width: 60px;
  text-align: center;
  color: var(--cyan);
  font-size: 10px;
  font-family: monospace;
  text-shadow: 0 0 5px rgba(0,0,0,0.8);
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}
.modal-box {
  background: var(--bg-card);
  border: 1px solid var(--cyan);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
  padding: 24px;
  width: 400px;
  max-width: 90vw;
  border-radius: 4px;
}
.modal-box h3 {
  margin-top: 0;
  color: var(--cyan);
  border-bottom: 1px solid rgba(0,229,255,0.3);
  padding-bottom: 8px;
}
.pairing-status {
  margin-top: 16px;
  padding: 12px;
  background: rgba(0,0,0,0.5);
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
}
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 10000;
}
.toast-msg {
  padding: 12px 20px;
  background: rgba(10, 15, 20, 0.95);
  border-left: 4px solid var(--cyan);
  color: #fff;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  font-family: monospace;
  animation: slideIn 0.3s ease-out;
}
.toast-msg.error {
  border-color: var(--pink);
  color: var(--pink);
}
.toast-msg.success {
  border-color: var(--green);
  color: var(--green);
}
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.btn-action:disabled, .hack-btn:disabled {
  opacity: 0.8 !important;
  color: #a0a0a0 !important;
  border-color: #555 !important;
  cursor: not-allowed;
}
</style>
