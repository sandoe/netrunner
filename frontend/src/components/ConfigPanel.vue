<template>
  <div class="config-panel">
    <div class="config-sidebar">
      <div v-for="(cat, key) in CONFIG_CATEGORIES" :key="key" class="cat-group">
        <div class="cat-label" @click="toggleCat(key as string)">
          <span>{{ cat.icon }} {{ cat.label }}</span>
          <span class="cat-chevron" :class="{ collapsed: collapsedCats.has(key as string) }">⌃</span>
        </div>
        <div v-if="!collapsedCats.has(key as string)" class="cat-items">
          <button
            v-for="item in cat.types"
            :key="item.type"
            class="type-btn"
            :class="{ active: activeType === item.type }"
            @click="selectType(item.type)"
          >{{ item.label }}</button>
        </div>
      </div>
    </div>

    <div class="config-main">
      <div v-if="!activeType" class="placeholder">Select a configuration generator →</div>
      <div v-else class="config-editor">
        <div class="editor-header">
          <span class="type-name">{{ activeType }}</span>
          <div class="header-actions">
            <label class="persist-toggle" :title="'Wrap commands in /etc/local.d/<name>.start so they run on every boot'">
              <input type="checkbox" v-model="persistMode" />
              <span>persist on boot</span>
            </label>
            <button class="btn-clear-form" @click="resetForm" title="Reset form to defaults">🗑 clear form</button>
            <button class="btn-preview" @click="getPreview" :disabled="loading">👁 preview</button>
            <button class="btn-apply" @click="applyConfig" :disabled="loading || !previewCommands.length">
              {{ persistMode ? '💾 install' : '🚀 apply' }}
            </button>
          </div>
        </div>

        <div class="editor-body">
          <!-- Live Telemetry Reference Panel -->
          <div class="live-ref-panel">
            <div class="live-ref-header" @click="liveRefExpanded = !liveRefExpanded">
              <div class="live-ref-title">
                <span class="live-ref-icon" :class="{ 'spinning': detectingState === 'loading' }">📡</span>
                <span class="live-ref-text">LIVE TELEMETRY: {{ props.nodeId }}</span>
                <span v-if="detectingState === 'loading'" class="live-ref-status-badge scanning">SCANNING</span>
                <span v-else-if="detectingState === 'success'" class="live-ref-status-badge connected">ONLINE</span>
                <span v-else-if="detectingState === 'error'" class="live-ref-status-badge offline">OFFLINE</span>
              </div>
              <div class="live-ref-actions" @click.stop>
                <button class="btn-ref-refresh" @click="fetchLiveInterfaces" title="Refresh Live Telemetry">
                  <span>🔄</span>
                </button>
                <span class="guide-chevron">{{ liveRefExpanded ? '▲' : '▼' }}</span>
              </div>
            </div>

            <div v-if="liveRefExpanded" class="live-ref-content">
              <div v-if="detectingState === 'loading'" class="live-ref-loading">
                <div class="cyber-pulse-loader"></div>
                <span>Fetching live network telemetry from target node...</span>
              </div>
              
              <div v-else-if="detectingState === 'error'" class="live-ref-error">
                <span class="err-icon">⚠️</span>
                <div class="err-details">
                  <div class="err-title">Failed to contact node telemetry agent</div>
                  <div class="err-msg">{{ detectingError }}</div>
                </div>
                <button class="btn-ref-retry" @click="fetchLiveInterfaces">Retry Connection</button>
              </div>

              <div v-else-if="detectedInterfaces.length === 0" class="live-ref-empty">
                No active network interfaces detected on this node.
              </div>

              <div v-else class="live-ref-wrapper">
                <!-- RJ45 Port Panel -->
                <div v-if="physicalInterfaces.length > 0" class="rj45-panel">
                  <div class="rj45-panel-title">PHYSICAL PORTS FRONT PANEL</div>
                  <div class="rj45-ports-container">
                    <div
                      v-for="iface in physicalInterfaces"
                      :key="iface.name"
                      class="rj45-port"
                      :class="{ 'port-up': iface.status === 'UP', 'port-down': iface.status === 'DOWN' }"
                      @click="selectPort(iface.name)"
                      :title="`Interface: ${iface.name}\nStatus: ${iface.status}\nClick to configure`"
                    >
                      <div class="rj45-led-indicator"></div>
                      <div class="rj45-clip"></div>
                      <div class="rj45-pins">
                        <span v-for="n in 8" :key="n" class="rj45-pin"></span>
                      </div>
                      <div class="rj45-label">{{ iface.name }}</div>
                    </div>
                  </div>
                </div>

                <!-- VLAN & Interfaces Tree Hierarchy -->
                <div class="live-ref-tree">
                  <div class="tree-header">
                    <span>INTERFACES & VLAN HIERARCHY</span>
                    <button 
                      class="btn-live-monitor"
                      :class="{ 'monitor-active': liveMonitorActive }"
                      @click.stop="toggleLiveMonitor"
                      title="Toggle Real-time Traffic Graph & Metrics (Interval: 3s)"
                    >
                      <span class="monitor-dot"></span>
                      <span class="monitor-text">LIVE MONITOR: {{ liveMonitorActive ? 'ACTIVE' : 'OFF' }}</span>
                    </button>
                  </div>
                  <div v-for="node in interfaceTree" :key="node.parent.name" class="tree-node">
                    <!-- Parent Interface Row -->
                    <div 
                      class="tree-parent-row"
                      :class="{ 'iface-up': node.parent.status === 'UP', 'iface-down': node.parent.status === 'DOWN' }"
                    >
                      <div class="tree-toggle" @click="toggleTreeParent(node.parent.name)">
                        <span v-if="node.children.length > 0">
                          {{ collapsedTreeParents.has(node.parent.name) ? '▶' : '▼' }}
                        </span>
                        <span v-else class="tree-bullet">•</span>
                      </div>
                      
                      <div class="tree-info">
                        <span 
                          class="ref-iface-name" 
                          title="Click to copy interface name / Select in form"
                          @click="selectPort(node.parent.name)"
                        >
                          {{ node.parent.name }}
                        </span>
                        <span class="ref-iface-status" :class="node.parent.status.toLowerCase()">
                          {{ node.parent.status }}
                        </span>
                      </div>
                      
                      <!-- Live Traffic Monitor Column -->
                      <div v-if="liveMonitorActive && interfaceTrafficData[node.parent.name]" class="tree-traffic">
                        <div class="traffic-rates">
                          <span class="rate-down">↓ {{ formatRate(interfaceTrafficData[node.parent.name].rxRate) }}</span>
                          <span class="rate-up">↑ {{ formatRate(interfaceTrafficData[node.parent.name].txRate) }}</span>
                        </div>
                        <svg class="traffic-sparkline" width="60" height="16">
                          <path 
                            :d="getSparklinePath(interfaceTrafficData[node.parent.name].rxHistory)" 
                            class="sparkpath-rx" 
                          />
                          <path 
                            :d="getSparklinePath(interfaceTrafficData[node.parent.name].txHistory)" 
                            class="sparkpath-tx" 
                          />
                        </svg>
                      </div>
                      <div v-else-if="liveMonitorActive" class="tree-traffic-loading">
                        <span class="traffic-dot-pulse"></span>
                        <span class="traffic-loading-lbl">MONITORING...</span>
                      </div>
                      
                      <div class="tree-ips">
                        <div v-if="node.parent.ips.length === 0" class="ref-no-ips">No IP address assigned</div>
                        <div 
                          v-for="ip in node.parent.ips" 
                          :key="ip" 
                          class="ref-ip-badge-container"
                        >
                          <span 
                            class="ref-ip-badge" 
                            title="Click to copy IP address"
                            @click="copyToClipboard(ip)"
                          >
                            {{ ip }}
                          </span>
                          
                          <!-- Inline Quick Ping Button -->
                          <button 
                            class="btn-quick-ping"
                            :disabled="pingLoading[`${node.parent.name}-${ip}`]"
                            @click.stop="triggerInlinePing(node.parent.name, ip)"
                            title="Trigger Inline Quick Ping Diagnostics to 8.8.8.8"
                          >
                            <span v-if="pingLoading[`${node.parent.name}-${ip}`]" class="ping-spinner"></span>
                            <span v-else>⚡</span>
                          </button>
                          
                          <!-- Inline Quick Ping Badge -->
                          <span 
                            v-if="pingResults[`${node.parent.name}-${ip}`]" 
                            class="ping-latency-badge"
                            :class="{ 
                              'ping-success': pingResults[`${node.parent.name}-${ip}`].success,
                              'ping-fail': !pingResults[`${node.parent.name}-${ip}`].success
                            }"
                          >
                            {{ pingResults[`${node.parent.name}-${ip}`].success ? pingResults[`${node.parent.name}-${ip}`].latency : 'FAIL' }}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Children VLAN interfaces -->
                    <div 
                      v-if="node.children.length > 0 && !collapsedTreeParents.has(node.parent.name)" 
                      class="tree-children"
                    >
                      <div 
                        v-for="(child, childIdx) in node.children" 
                        :key="child.name"
                        class="tree-child-row"
                        :class="{ 'iface-up': child.status === 'UP', 'iface-down': child.status === 'DOWN' }"
                      >
                        <span class="tree-branch">
                          {{ childIdx === node.children.length - 1 ? '└──' : '├──' }}
                        </span>
                        
                        <div class="tree-info">
                          <span 
                            class="ref-iface-name" 
                            title="Click to copy interface name / Select in form"
                            @click="selectPort(child.name)"
                          >
                            {{ child.name }}
                          </span>
                          <span class="ref-iface-status" :class="child.status.toLowerCase()">
                            {{ child.status }}
                          </span>
                        </div>
                        
                        <!-- Live Traffic Monitor Column -->
                        <div v-if="liveMonitorActive && interfaceTrafficData[child.name]" class="tree-traffic">
                          <div class="traffic-rates">
                            <span class="rate-down">↓ {{ formatRate(interfaceTrafficData[child.name].rxRate) }}</span>
                            <span class="rate-up">↑ {{ formatRate(interfaceTrafficData[child.name].txRate) }}</span>
                          </div>
                          <svg class="traffic-sparkline" width="60" height="16">
                            <path 
                              :d="getSparklinePath(interfaceTrafficData[child.name].rxHistory)" 
                              class="sparkpath-rx" 
                            />
                            <path 
                              :d="getSparklinePath(interfaceTrafficData[child.name].txHistory)" 
                              class="sparkpath-tx" 
                            />
                          </svg>
                        </div>
                        <div v-else-if="liveMonitorActive" class="tree-traffic-loading">
                          <span class="traffic-dot-pulse"></span>
                          <span class="traffic-loading-lbl">MONITORING...</span>
                        </div>
                        
                        <div class="tree-ips">
                          <div v-if="child.ips.length === 0" class="ref-no-ips">No IP address assigned</div>
                          <div 
                            v-for="ip in child.ips" 
                            :key="ip" 
                            class="ref-ip-badge-container"
                          >
                            <span 
                              class="ref-ip-badge" 
                              title="Click to copy IP address"
                              @click="copyToClipboard(ip)"
                            >
                              {{ ip }}
                            </span>
                            
                            <!-- Inline Quick Ping Button -->
                            <button 
                              class="btn-quick-ping"
                              :disabled="pingLoading[`${child.name}-${ip}`]"
                              @click.stop="triggerInlinePing(child.name, ip)"
                              title="Trigger Inline Quick Ping Diagnostics to 8.8.8.8"
                            >
                              <span v-if="pingLoading[`${child.name}-${ip}`]" class="ping-spinner"></span>
                              <span v-else>⚡</span>
                            </button>
                            
                            <!-- Inline Quick Ping Badge -->
                            <span 
                              v-if="pingResults[`${child.name}-${ip}`]" 
                              class="ping-latency-badge"
                              :class="{ 
                                'ping-success': pingResults[`${child.name}-${ip}`].success,
                                'ping-fail': !pingResults[`${child.name}-${ip}`].success
                              }"
                            >
                              {{ pingResults[`${child.name}-${ip}`].success ? pingResults[`${child.name}-${ip}`].latency : 'FAIL' }}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="live-ref-footer">
                💡 <span class="tip-highlight">Click</span> any interface name or IP badge to copy it directly to your clipboard.
              </div>
            </div>
          </div>

          <!-- Cyber-Guide Help Panel -->
          <div v-if="activeGuide" class="cyber-guide">
            <div class="guide-header" @click="guideExpanded = !guideExpanded">
              <div class="guide-title">
                <span class="guide-icon">⚡</span>
                <span class="guide-text">CYBER-GUIDE: {{ activeGuide.title }}</span>
              </div>
              <span class="guide-chevron">{{ guideExpanded ? '▲' : '▼' }}</span>
            </div>
            <div v-if="guideExpanded" class="guide-content">
              <p class="guide-desc">{{ activeGuide.description }}</p>
              <div class="guide-grid">
                <div class="guide-column">
                  <div class="column-title">💾 Affected Files</div>
                  <ul>
                    <li v-for="file in activeGuide.files" :key="file"><code>{{ file }}</code></li>
                  </ul>
                </div>
                <div class="guide-column">
                  <div class="column-title">💡 Operational Tips</div>
                  <ul>
                    <li v-for="tip in activeGuide.tips" :key="tip">{{ tip }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- Specialized Interface Form -->
          <div v-if="activeType === 'interface'" class="specialized-form">
            <div class="form-row">
              <label>Interface
                <input v-model="interfaceForm.interface" placeholder="eth0" list="detected-interfaces" />
              </label>
              <label>Link State
                <select v-model="interfaceForm.state" class="cyber-select">
                  <option value="none">Auto (default)</option>
                  <option value="up">Link UP</option>
                  <option value="down">Link DOWN</option>
                </select>
              </label>
              <label class="check-label" style="margin-top: 18px;">
                <input type="checkbox" v-model="interfaceForm.dhcp" /> Enable DHCP
              </label>
            </div>

            <div class="section-label-sub">Static Addresses</div>
            <div v-for="(addr, idx) in interfaceForm.addresses" :key="idx" class="static-addr-row">
              <div class="form-row">
                <input v-model="interfaceForm.addresses[idx]" placeholder="10.0.0.1/24" />
                <button class="btn-remove" @click="interfaceForm.addresses.splice(idx, 1)">✕</button>
              </div>
              <div v-if="calculateSubnet(addr)" class="subnet-assistant-card">
                <div class="subnet-stat">
                  <span class="label">Netmask:</span>
                  <span class="value cyan-glow">{{ calculateSubnet(addr)?.netmask }}</span>
                </div>
                <div class="subnet-stat">
                  <span class="label">Network:</span>
                  <span class="value yellow-glow">{{ calculateSubnet(addr)?.network }}</span>
                </div>
                <div class="subnet-stat">
                  <span class="label">Broadcast:</span>
                  <span class="value pink-glow">{{ calculateSubnet(addr)?.broadcast }}</span>
                </div>
              </div>
            </div>
            <div class="form-actions">
              <button class="btn-add-sub" @click="interfaceForm.addresses.push('')">+ Add Static IP</button>
              <label v-if="interfaceForm.addresses.length > 0 || interfaceForm.interface.includes('.')">Action
                <select v-model="interfaceForm.action" class="cyber-select">
                  <option v-if="interfaceForm.addresses.length > 0" value="add">Add Only</option>
                  <option v-if="interfaceForm.addresses.length > 0" value="del">Remove Addresses</option>
                  <option v-if="interfaceForm.addresses.length > 0" value="flush">Flush & Add</option>
                  <option v-if="interfaceForm.interface.includes('.')" value="delete_interface">Delete VLAN Interface</option>
                </select>
              </label>
            </div>
            <div v-if="interfaceForm.addresses.length > 0" class="form-actions-tip">
              💡 <span class="cyan-glow">Tip:</span> To remove an address from the router, select <strong>"Remove Addresses"</strong> action before deleting it from the form, or use <strong>"Flush & Add"</strong> to make the router match this list exactly.
            </div>

            <!-- VLAN Sub-interface Helper -->
            <div class="vlan-helper-box">
              <div class="helper-title">VLAN Sub-interface Helper</div>
              <div class="helper-desc">Select a parent interface and VLAN ID to automatically set the sub-interface name (e.g. eth0.100).</div>
              <div class="form-row" style="margin-bottom: 0;">
                <label>Parent Interface
                  <select v-model="interfaceForm.vlanParent" class="cyber-select">
                    <option value="">-- Select Parent --</option>
                    <option v-for="iface in detectedInterfaces" :key="iface.name" :value="iface.name">
                      {{ iface.name }} ({{ iface.status }})
                    </option>
                  </select>
                </label>
                <label>VLAN ID (1-4094)
                  <input v-model.number="interfaceForm.vlanId" type="number" min="1" max="4094" placeholder="100" />
                </label>
              </div>
            </div>
          </div>

          <!-- Specialized Routes Form -->
          <div v-if="activeType === 'routes'" class="specialized-form">
            <div v-for="(route, idx) in routeForm.routes" :key="idx" class="form-row multi-row">
              <label>Destination
                <input v-model="route.dst" placeholder="10.1.0.0/24" />
              </label>
              <label>Gateway (via)
                <input v-model="route.via" placeholder="10.0.0.254" />
              </label>
              <label>Device
                <input v-model="route.dev" placeholder="eth0" list="detected-interfaces" />
              </label>
              <label>Metric
                <input v-model.number="route.metric" type="number" placeholder="100" />
              </label>
              <button class="btn-remove" @click="routeForm.routes.splice(idx, 1)">✕</button>
            </div>
            <div class="form-actions">
              <button class="btn-add-sub" @click="routeForm.routes.push({ dst: '', via: '', dev: '', metric: 0 })">+ Add Route</button>
              <label class="check-label">
                <input type="checkbox" v-model="routeForm.isDelete" /> Delete instead of Add
              </label>
            </div>
          </div>

          <!-- DNS Form -->
          <div v-if="activeType === 'dns'" class="specialized-form">
            <div class="form-row">
              <label>Nameservers (CSV) <input v-model="dnsForm.nameservers" /></label>
              <label>Search Domains (CSV) <input v-model="dnsForm.search" /></label>
            </div>
            <div class="form-row">
              <label>Hostname <input v-model="dnsForm.hostname" /></label>
              <label>Domain <input v-model="dnsForm.domain" /></label>
            </div>
            <div class="section-label-sub">Static Host Records</div>
            <div v-for="(rec, i) in dnsForm.records" :key="i" class="form-row">
              <input v-model="rec.name" placeholder="name (e.g. router.local)" />
              <input v-model="rec.value" placeholder="IP address" />
              <button class="btn-remove" @click="dnsForm.records.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="dnsForm.records.push({ name: '', value: '' })">+ Add Record</button>
          </div>

          <!-- NAT Form -->
          <div v-if="activeType === 'nat'" class="specialized-form">
            <div class="form-row">
              <label>WAN (Outbound) <input v-model="natForm.outbound_iface" list="detected-interfaces" /></label>
              <label>LAN (Inbound) <input v-model="natForm.inbound_iface" list="detected-interfaces" /></label>
              <label>Source Subnet <input v-model="natForm.source_subnet" /></label>
            </div>
            <label class="check-label"><input type="checkbox" v-model="natForm.masquerade" /> Enable Masquerade</label>
            <div class="section-label-sub">Port Forwards</div>
            <div v-for="(f, i) in natForm.port_forwards" :key="i" class="form-row multi-row">
              <label>Ext Port <input v-model="f.external_port" /></label>
              <label>Target IP <input v-model="f.target_ip" /></label>
              <label>Int Port <input v-model="f.target_port" /></label>
              <label>Proto
                <select v-model="f.proto">
                  <option value="tcp">TCP</option>
                  <option value="udp">UDP</option>
                </select>
              </label>
              <button class="btn-remove" @click="natForm.port_forwards.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="natForm.port_forwards.push({ proto: 'tcp', external_port: '', target_ip: '', target_port: '' })">+ Add Forward</button>
          </div>

          <!-- VLAN Router Form -->
          <div v-if="activeType === 'vlan-router'" class="specialized-form">
            <div class="form-row">
              <label>Base Interface <input v-model="vlanRouterForm.interface" list="detected-interfaces" /></label>
            </div>
            <div class="section-label-sub">VLAN Interfaces</div>
            <div v-for="(v, i) in vlanRouterForm.vlans" :key="i" class="form-row multi-row" :class="{ 'vlan-to-delete': v.action === 'del' }">
              <label>VLAN ID <input v-model="v.id" :disabled="v.action === 'del'" /></label>
              <label>Address <input v-model="v.address" :disabled="v.action === 'del'" /></label>
              <label>Description <input v-model="v.description" :disabled="v.action === 'del'" /></label>
              <label>Action
                <select v-model="v.action" class="cyber-select">
                  <option value="add">Create / Update</option>
                  <option value="del">Delete</option>
                </select>
              </label>
              <button class="btn-remove" @click="vlanRouterForm.vlans.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="vlanRouterForm.vlans.push({ id: '', address: '', description: '', action: 'add' })">+ Add VLAN</button>
          </div>

          <!-- VLAN Switch Form -->
          <div v-if="activeType === 'vlan-switch'" class="specialized-form">
            <div class="form-row">
              <label>Bridge Name <input v-model="vlanSwitchForm.bridge" /></label>
            </div>
            <div class="section-label-sub">VLAN Definitions</div>
            <div v-for="(v, i) in vlanSwitchForm.vlans" :key="i" class="form-row">
              <input v-model="v.id" placeholder="ID" />
              <input v-model="v.name" placeholder="Name" />
              <button class="btn-remove" @click="vlanSwitchForm.vlans.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="vlanSwitchForm.vlans.push({ id: '', name: '' })">+ Add VLAN</button>
            
            <div class="section-label-sub">Port Assignments</div>
            <div v-for="(p, i) in vlanSwitchForm.ports" :key="i" class="form-row multi-row">
              <label>Iface <input v-model="p.iface" list="detected-interfaces" /></label>
              <label>Mode
                <select v-model="p.mode">
                  <option value="access">Access</option>
                  <option value="trunk">Trunk</option>
                </select>
              </label>
              <label v-if="p.mode === 'access'">VLAN <input v-model="p.vlan" /></label>
              <label v-if="p.mode === 'trunk'">Allowed (CSV) <input v-model="p.allowed" /></label>
              <button class="btn-remove" @click="vlanSwitchForm.ports.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="vlanSwitchForm.ports.push({ iface: '', mode: 'access', vlan: '1', allowed: '' })">+ Add Port</button>
          </div>

          <!-- WireGuard Form -->
          <div v-if="activeType === 'wireguard'" class="specialized-form wireguard-form-container" :class="{ 'wg-deletion-mode': wireguardForm.action === 'delete' }">
            <!-- Action Selector -->
            <div class="form-row action-selector-row">
              <label>Configuration Action
                <select v-model="wireguardForm.action" class="action-select">
                  <option value="add">🚀 Create / Update Interface & Keys</option>
                  <option value="delete">🔥 Delete Interface & Purge Keys</option>
                </select>
              </label>
            </div>

            <!-- Standard creation/update inputs -->
            <div v-if="wireguardForm.action !== 'delete'" class="wg-form-body">
              <div class="wg-profile-panel">
                <div class="wg-profile-header">
                  <div>
                    <div class="wg-profile-title">Saved WireGuard Profile</div>
                    <div class="wg-profile-subtitle">Save the editable form, load it later, or hydrate it from the node's live config.</div>
                  </div>
                  <button
                    type="button"
                    class="btn-wg-node-load"
                    :disabled="wgLoadingFromNode"
                    @click="loadWireguardFromNode"
                  >
                    {{ wgLoadingFromNode ? 'Loading...' : 'Load from node' }}
                  </button>
                </div>
                <div class="wg-profile-grid">
                  <label>Profile Name <input v-model="wgProfileName" placeholder="e.g. edge-router wg0" /></label>
                  <label>Load Saved Profile
                    <select v-model="wgSelectedProfileId" class="action-select">
                      <option value="">Select saved profile...</option>
                      <option v-for="profile in currentWgProfiles" :key="profile.id" :value="profile.id">
                        {{ profile.name }} — {{ profile.interface }}
                      </option>
                    </select>
                  </label>
                  <div class="wg-profile-actions">
                    <button type="button" class="btn-wg-profile-save" @click="saveWireguardProfile">Save profile</button>
                    <button type="button" class="btn-wg-profile-load" :disabled="!wgSelectedProfileId" @click="loadWireguardProfile">Load selected</button>
                    <button type="button" class="btn-wg-profile-delete" :disabled="!wgSelectedProfileId" @click="deleteWireguardProfile">Delete</button>
                  </div>
                </div>
              </div>

              <div class="form-row">
                <label>Interface <input v-model="wireguardForm.interface" placeholder="wg0" /></label>
                <label>Address <input v-model="wireguardForm.address" placeholder="10.0.0.1/24" /></label>
                <label>Listen Port <input v-model.number="wireguardForm.listen_port" type="number" placeholder="51820" /></label>
              </div>
              
              <!-- Key Generation Row -->
              <div class="form-row key-gen-row">
                <div class="input-with-actions-container">
                  <label class="private-key-label">
                    <span>Private Key</span>
                    <div class="input-actions-wrapper">
                      <input 
                        v-model="wireguardForm.private_key" 
                        :type="hidePrivateKey ? 'password' : 'text'" 
                        placeholder="Local private key..."
                        class="private-key-input"
                      />
                      <button 
                        type="button" 
                        class="btn-input-action" 
                        @click="hidePrivateKey = !hidePrivateKey"
                        :title="hidePrivateKey ? 'Reveal Private Key' : 'Hide Private Key'"
                      >
                        {{ hidePrivateKey ? '👁️' : '🔒' }}
                      </button>
                      <button 
                        type="button" 
                        class="btn-input-action" 
                        @click="copyToClipboard(wireguardForm.private_key)"
                        :disabled="!wireguardForm.private_key"
                        title="Copy Private Key to clipboard"
                      >
                        📋
                      </button>
                    </div>
                  </label>
                </div>
                <div class="gen-keys-button-wrapper">
                  <button 
                    type="button" 
                    class="btn-wg-generate" 
                    @click="generateWireguardKeys" 
                    :disabled="generatingKeys"
                  >
                    <span v-if="generatingKeys">⏳ Generating...</span>
                    <span v-else>🔑 Generate Keypair</span>
                  </button>
                </div>
              </div>

              <!-- Derived Public Key Panel -->
              <div v-if="generatedPublicKey" class="derived-pubkey-panel">
                <div class="derived-pubkey-header">
                  <span class="pubkey-title-glow">📡 LOCAL PUBLIC KEY (Share with Peer)</span>
                  <button 
                    type="button" 
                    class="btn-pubkey-copy" 
                    @click="copyToClipboard(generatedPublicKey)"
                  >
                    📋 Copy Key
                  </button>
                </div>
                <div class="derived-pubkey-value">{{ generatedPublicKey }}</div>
              </div>

              <!-- Key History Collapsible Toggle -->
              <div class="wg-advanced-toggle wg-history-toggle" @click="wgHistoryExpanded = !wgHistoryExpanded">
                <span class="advanced-toggle-title">🔑 Key History / Nøglering ({{ keyHistory.length }})</span>
                <span class="guide-chevron">{{ wgHistoryExpanded ? '▲' : '▼' }}</span>
              </div>

              <!-- Key History List -->
              <div v-if="wgHistoryExpanded" class="wg-history-fields">
                <div v-if="!keyHistory.length" class="no-keys-message">Ingen genererede nøgler i historikken.</div>
                <div v-else class="wg-history-list">
                  <div v-for="item in keyHistory" :key="item.id" class="history-item-card">
                    <div class="history-item-header">
                      <span class="history-item-label">{{ item.label }}</span>
                      <span class="history-item-date">{{ item.timestamp }}</span>
                    </div>
                    <div class="history-keys-row">
                      <div class="history-key-wrapper">
                        <span class="key-type">Priv:</span>
                        <span class="key-value monospace">{{ item.hidePrivate ? '••••••••••••••••••••••••••••••••' : item.privateKey }}</span>
                        <button type="button" class="btn-history-action" @click="item.hidePrivate = !item.hidePrivate" :title="item.hidePrivate ? 'Vis privat nøgle' : 'Skjul privat nøgle'">
                          {{ item.hidePrivate ? '👁️' : '🔒' }}
                        </button>
                        <button type="button" class="btn-history-action" @click="copyToClipboard(item.privateKey)" title="Kopiér privat nøgle">📋</button>
                      </div>
                      <div class="history-key-wrapper">
                        <span class="key-type">Pub:</span>
                        <span class="key-value monospace">{{ item.publicKey }}</span>
                        <button type="button" class="btn-history-action" @click="copyToClipboard(item.publicKey)" title="Kopiér offentlig nøgle">📋</button>
                      </div>
                    </div>
                    <div class="history-card-actions">
                      <button type="button" class="btn-history-load" @click="loadKeyIntoForm(item)">⚡ Indlæs i formular</button>
                      <button type="button" class="btn-history-remove" @click="deleteKeyFromHistory(item.id)">✕ Fjern</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Advanced Configuration Collapsible Toggle -->
              <div class="wg-advanced-toggle" @click="wgAdvancedExpanded = !wgAdvancedExpanded">
                <span class="advanced-toggle-title">⚙️ Advanced Interface Options</span>
                <span class="guide-chevron">{{ wgAdvancedExpanded ? '▲' : '▼' }}</span>
              </div>
              
              <!-- Advanced Fields -->
              <div v-if="wgAdvancedExpanded" class="wg-advanced-fields">
                <div class="form-row">
                  <label>DNS <input v-model="wireguardForm.dns" placeholder="e.g. 1.1.1.1, 8.8.8.8" /></label>
                  <label>MTU <input v-model="wireguardForm.mtu" placeholder="e.g. 1420" /></label>
                </div>
                <div class="form-row">
                  <label>PostUp <input v-model="wireguardForm.post_up" placeholder="iptables -A FORWARD -i wg0 -j ACCEPT; ..." /></label>
                  <label>PostDown <input v-model="wireguardForm.post_down" placeholder="iptables -D FORWARD -i wg0 -j ACCEPT; ..." /></label>
                </div>
              </div>

              <!-- Peers Section -->
              <div class="section-label-sub">Peers</div>
              <div v-for="(peer, i) in wireguardForm.peers" :key="i" class="form-row multi-row peer-row-container">
                <div class="peer-grid">
                  <label class="peer-full-width">Public Key <input v-model="peer.public_key" placeholder="Remote peer public key..." /></label>
                  <label>Endpoint <input v-model="peer.endpoint" placeholder="e.g. 192.168.1.100:51820" /></label>
                  <label>Allowed IPs <input v-model="peer.allowed_ips" placeholder="e.g. 10.0.0.2/32, 192.168.20.0/24" /></label>
                  <label>Preshared Key <input v-model="peer.preshared_key" placeholder="Optional peer preshared key..." /></label>
                  <label>Keepalive <input v-model.number="peer.persistent_keepalive" type="number" placeholder="e.g. 25" /></label>
                </div>
                <button class="btn-remove btn-remove-peer" @click="wireguardForm.peers.splice(i, 1)">✕</button>
              </div>
              <button class="btn-add-sub" @click="wireguardForm.peers.push({ public_key: '', preshared_key: '', endpoint: '', allowed_ips: '0.0.0.0/0', persistent_keepalive: '' })">+ Add Peer</button>
            </div>

            <!-- Deletion Mode Layout -->
            <div v-else class="wg-delete-body">
              <div class="form-row">
                <label>Interface to Delete <input v-model="wireguardForm.interface" placeholder="wg0" /></label>
              </div>
              <div class="wg-delete-warning-box">
                <div class="warning-header">⚠️ WARNING: IRREVERSIBLE OPERATION</div>
                <p>This action will permanently tear down the WireGuard interface <strong class="highlight-wg">{{ wireguardForm.interface }}</strong>, disable its persistence, and completely delete its config and key files on the device.</p>
              </div>
            </div>
          </div>

          <!-- IP Forwarding Form -->
          <div v-if="activeType === 'forwarding'" class="specialized-form">
            <div class="form-row">
              <label class="check-label"><input type="checkbox" v-model="forwardingForm.ipv4" /> IPv4 Forwarding</label>
              <label class="check-label"><input type="checkbox" v-model="forwardingForm.ipv6" /> IPv6 Forwarding</label>
            </div>
          </div>

          <!-- Reset Node Form -->
          <div v-if="activeType === 'reset-node'" class="specialized-form">
            <div class="warning-box">
              ⚠️ This will flush ALL network settings, firewall rules, and WireGuard tunnels.
            </div>
            <button class="btn-sync" @click="inputJson = '{}'">Prepare Reset ↓</button>
          </div>

          <!-- Linux Service Form -->
          <div v-if="activeType === 'service'" class="specialized-form">
            <div class="form-row">
              <label>Service Name <input v-model="serviceForm.name" placeholder="ssh, nginx, etc." /></label>
              <label>Action
                <select v-model="serviceForm.action">
                  <option value="status">Status</option>
                  <option value="start">Start</option>
                  <option value="stop">Stop</option>
                  <option value="restart">Restart</option>
                  <option value="enable">Enable (Boot)</option>
                  <option value="disable">Disable (Boot)</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Linux Package Form -->
          <div v-if="activeType === 'package'" class="specialized-form">
            <div class="form-row">
              <label>Packages (CSV) <input v-model="packageForm.packages" placeholder="curl, vim, htop" /></label>
              <label>Action
                <select v-model="packageForm.action">
                  <option value="install">Install</option>
                  <option value="remove">Remove</option>
                  <option value="update">Update / Upgrade All</option>
                </select>
              </label>
              <label>Manager
                <select v-model="packageForm.manager">
                  <option value="auto">Auto-detect</option>
                  <option value="apt">apt (Debian/Ubuntu)</option>
                  <option value="apk">apk (Alpine)</option>
                  <option value="yum">yum (CentOS/RHEL)</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Linux User Form -->
          <div v-if="activeType === 'user'" class="specialized-form">
            <div class="form-row">
              <label>Username <input v-model="userForm.username" /></label>
              <label>Action
                <select v-model="userForm.action">
                  <option value="create">Create</option>
                  <option value="modify">Modify</option>
                  <option value="passwd">Change Password</option>
                  <option value="delete">Delete</option>
                  <option value="sudo">Grant Sudo/Wheel</option>
                </select>
              </label>
            </div>
            <div class="form-row" v-if="userForm.action !== 'delete' && userForm.action !== 'sudo'">
              <label>Password <input v-model="userForm.password" type="password" /></label>
              <label>Groups (CSV) <input v-model="userForm.groups" /></label>
            </div>
            <div class="form-row" v-if="userForm.action === 'create' || userForm.action === 'modify'">
              <label>Shell <input v-model="userForm.shell" /></label>
              <label>Home Dir <input v-model="userForm.home" /></label>
              <label class="check-label"><input type="checkbox" v-model="userForm.system" /> System User</label>
            </div>
          </div>

          <!-- Hostname Form -->
          <div v-if="activeType === 'hostname'" class="specialized-form">
            <div class="form-row">
              <label>Hostname <input v-model="hostnameForm.hostname" /></label>
              <label>Domain <input v-model="hostnameForm.domain" /></label>
            </div>
          </div>

          <!-- Sysctl Form -->
          <div v-if="activeType === 'sysctl'" class="specialized-form">
            <div v-for="(p, i) in sysctlForm.params" :key="i" class="form-row">
              <input v-model="p.key" placeholder="net.ipv4.ip_forward" />
              <input v-model="p.value" placeholder="1" />
              <button class="btn-remove" @click="sysctlForm.params.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="sysctlForm.params.push({ key: '', value: '' })">+ Add Parameter</button>
            <label class="check-label"><input type="checkbox" v-model="sysctlForm.persist" /> Persist to /etc/sysctl.d/</label>
          </div>

          <!-- File Write Form -->
          <div v-if="activeType === 'file-write'" class="specialized-form">
            <div class="form-row">
              <label>File Path <input v-model="fileWriteForm.path" /></label>
              <label>Mode <input v-model="fileWriteForm.mode" /></label>
              <label>Owner <input v-model="fileWriteForm.owner" /></label>
            </div>
            <div class="input-section">
              <div class="section-label">File Content</div>
              <textarea v-model="fileWriteForm.content" class="json-textarea" style="height: 180px;"></textarea>
            </div>
            <label class="check-label"><input type="checkbox" v-model="fileWriteForm.backup" /> Create .bak before writing</label>
          </div>

          <!-- Direct File Editor Form -->
          <div v-if="activeType === 'direct-file'" class="specialized-form">
            <div class="form-row">
              <label>Target File Path <input v-model="directFilePath" placeholder="/etc/wireguard/wg0.conf" /></label>
              <label>Permissions Mode <input v-model="directFileMode" placeholder="600" /></label>
              <label style="display: flex; align-items: flex-end; margin-bottom: 4px;">
                <button class="btn-ref-retry" :disabled="loadingFile" @click="loadDirectFile" style="margin: 0; padding: 10px 16px; background: var(--bg4); border: 1px solid var(--border); border-radius: 4px; color: var(--textbr); font-family: var(--font-ui); cursor: pointer; transition: all 0.2s;">
                  {{ loadingFile ? '📥 LOADING...' : '📥 LOAD FILE FROM NODE' }}
                </button>
              </label>
            </div>
            <div class="input-section">
              <div class="section-label">File Content (Direct Editor)</div>
              <textarea 
                v-model="directFileContent" 
                class="json-textarea" 
                style="height: 350px; font-family: var(--font-co); font-size: 12px; line-height: 1.5;" 
                placeholder="# Paste or type your file contents directly here..."
              ></textarea>
            </div>
            <label class="check-label"><input type="checkbox" v-model="directFileBackup" /> Create backup copy (.bak) on remote node before overwriting</label>
          </div>

          <!-- Direct JSON Config Form -->
          <div v-if="activeType === 'direct-json'" class="specialized-form">
            <div class="form-row">
              <label>Generator Target Type
                <select v-model="directJsonGeneratorType">
                  <option value="interface">interface (Interface Setup)</option>
                  <option value="routes">routes (Routes)</option>
                  <option value="dns">dns (DNS / Resolver)</option>
                  <option value="nat">nat (NAT / Forwarding)</option>
                  <option value="wireguard">wireguard (WireGuard)</option>
                  <option value="forwarding">forwarding (IP Forwarding)</option>
                  <option value="iptables">iptables (iptables)</option>
                  <option value="nftables">nftables (nftables)</option>
                  <option value="ufw">ufw (UFW)</option>
                  <option value="service">service (Services)</option>
                  <option value="package">package (Packages)</option>
                  <option value="file-write">file-write (Write File)</option>
                </select>
              </label>
            </div>
            <div class="section-label-sub">Directly paste or edit generator JSON below:</div>
          </div>

          <!-- iptables Form -->
          <div v-if="activeType === 'iptables'" class="specialized-form">
            <div class="section-label-sub">Default Policies</div>
            <div class="form-row">
              <label>INPUT
                <select v-model="iptablesForm.defaults.INPUT">
                  <option value="ACCEPT">ACCEPT</option>
                  <option value="DROP">DROP</option>
                </select>
              </label>
              <label>FORWARD
                <select v-model="iptablesForm.defaults.FORWARD">
                  <option value="ACCEPT">ACCEPT</option>
                  <option value="DROP">DROP</option>
                </select>
              </label>
              <label>OUTPUT
                <select v-model="iptablesForm.defaults.OUTPUT">
                  <option value="ACCEPT">ACCEPT</option>
                  <option value="DROP">DROP</option>
                </select>
              </label>
            </div>
            <div class="section-label-sub">Rules</div>
            <div v-for="(r, i) in iptablesForm.rules" :key="i" class="fw-rule">
              <div class="form-row">
                <label>Table
                  <select v-model="r.table">
                    <option value="filter">filter</option>
                    <option value="nat">nat</option>
                    <option value="mangle">mangle</option>
                  </select>
                </label>
                <label>Chain <input v-model="r.chain" placeholder="INPUT" /></label>
                <label>Action
                  <select v-model="r.action">
                    <option value="ACCEPT">ACCEPT</option>
                    <option value="DROP">DROP</option>
                    <option value="REJECT">REJECT</option>
                    <option value="LOG">LOG</option>
                    <option value="DNAT">DNAT</option>
                    <option value="SNAT">SNAT</option>
                    <option value="MASQUERADE">MASQUERADE</option>
                  </select>
                </label>
                <button class="btn-remove" @click="iptablesForm.rules.splice(i, 1)">✕</button>
              </div>
              <div class="form-row">
                <label>Proto
                  <select v-model="r.protocol">
                    <option value="">(any)</option>
                    <option value="tcp">tcp</option>
                    <option value="udp">udp</option>
                    <option value="icmp">icmp</option>
                  </select>
                </label>
                <label>In iface <input v-model="r.iif" placeholder="eth0" /></label>
                <label>Out iface <input v-model="r.oif" placeholder="eth1" /></label>
                <label>Source <input v-model="r.saddr" placeholder="10.0.0.0/24" /></label>
                <label>Dest <input v-model="r.daddr" /></label>
              </div>
              <div class="form-row">
                <label>Sport <input v-model="r.sport" /></label>
                <label>Dport <input v-model="r.dport" placeholder="22" /></label>
                <label>ct_state <input v-model="r.ct_state" placeholder="ESTABLISHED,RELATED" /></label>
                <label v-if="r.action === 'DNAT' || r.action === 'SNAT'">NAT addr <input v-model="r.nat_addr" placeholder="10.0.0.10:80" /></label>
                <label v-if="r.action === 'LOG'">Log prefix <input v-model="r.log_prefix" /></label>
              </div>
            </div>
            <button class="btn-add-sub" @click="iptablesForm.rules.push({ table: 'filter', chain: 'INPUT', protocol: '', iif: '', oif: '', saddr: '', daddr: '', sport: '', dport: '', ct_state: '', action: 'ACCEPT', nat_addr: '', log_prefix: '' })">+ Add Rule</button>
          </div>

          <!-- nftables Form -->
          <div v-if="activeType === 'nftables'" class="specialized-form">
            <div class="form-row">
              <label>Family
                <select v-model="nftablesForm.family">
                  <option value="ip">ip</option>
                  <option value="ip6">ip6</option>
                  <option value="inet">inet</option>
                  <option value="arp">arp</option>
                  <option value="bridge">bridge</option>
                </select>
              </label>
              <label>Table name <input v-model="nftablesForm.table_name" /></label>
              <label>Chain name <input v-model="nftablesForm.chain_name" /></label>
            </div>
            <div class="form-row">
              <label>Chain type
                <select v-model="nftablesForm.chain_type">
                  <option value="filter">filter</option>
                  <option value="nat">nat</option>
                  <option value="route">route</option>
                </select>
              </label>
              <label>Hook
                <select v-model="nftablesForm.hook">
                  <option value="input">input</option>
                  <option value="output">output</option>
                  <option value="forward">forward</option>
                  <option value="prerouting">prerouting</option>
                  <option value="postrouting">postrouting</option>
                </select>
              </label>
              <label>Priority <input v-model="nftablesForm.priority" /></label>
              <label>Policy
                <select v-model="nftablesForm.policy">
                  <option value="accept">accept</option>
                  <option value="drop">drop</option>
                </select>
              </label>
            </div>
            <div class="section-label-sub">Rules</div>
            <div v-for="(r, i) in nftablesForm.rules" :key="i" class="fw-rule">
              <div class="form-row">
                <label>Action
                  <select v-model="r.action">
                    <option value="accept">accept</option>
                    <option value="drop">drop</option>
                    <option value="reject">reject</option>
                    <option value="log">log</option>
                    <option value="dnat">dnat</option>
                    <option value="snat">snat</option>
                    <option value="masquerade">masquerade</option>
                  </select>
                </label>
                <label>Proto
                  <select v-model="r.protocol">
                    <option value="">(any)</option>
                    <option value="tcp">tcp</option>
                    <option value="udp">udp</option>
                    <option value="icmp">icmp</option>
                  </select>
                </label>
                <label>In iface <input v-model="r.iif" /></label>
                <label>Out iface <input v-model="r.oif" /></label>
                <button class="btn-remove" @click="nftablesForm.rules.splice(i, 1)">✕</button>
              </div>
              <div class="form-row">
                <label>Source <input v-model="r.saddr" /></label>
                <label>Dest <input v-model="r.daddr" /></label>
                <label>Sport <input v-model="r.sport" /></label>
                <label>Dport <input v-model="r.dport" /></label>
                <label>ct state <input v-model="r.ct_state" placeholder="established,related" /></label>
              </div>
              <div class="form-row">
                <label v-if="r.action === 'dnat' || r.action === 'snat'">NAT addr <input v-model="r.nat_addr" /></label>
                <label v-if="r.action === 'log'">Log prefix <input v-model="r.log_prefix" /></label>
                <label>Comment <input v-model="r.comment" /></label>
              </div>
            </div>
            <button class="btn-add-sub" @click="nftablesForm.rules.push({ iif: '', oif: '', saddr: '', daddr: '', protocol: '', sport: '', dport: '', ct_state: '', action: 'accept', nat_addr: '', log_prefix: '', comment: '' })">+ Add Rule</button>
            <div class="hint">Multi-table setups: edit JSON below directly.</div>
          </div>

          <!-- UFW Form -->
          <div v-if="activeType === 'ufw'" class="specialized-form">
            <div class="section-label-sub">Defaults</div>
            <div class="form-row">
              <label>Incoming
                <select v-model="ufwForm.defaults.incoming">
                  <option value="allow">allow</option>
                  <option value="deny">deny</option>
                  <option value="reject">reject</option>
                </select>
              </label>
              <label>Outgoing
                <select v-model="ufwForm.defaults.outgoing">
                  <option value="allow">allow</option>
                  <option value="deny">deny</option>
                  <option value="reject">reject</option>
                </select>
              </label>
              <label>Routed
                <select v-model="ufwForm.defaults.routed">
                  <option value="allow">allow</option>
                  <option value="deny">deny</option>
                  <option value="reject">reject</option>
                </select>
              </label>
              <label class="check-label"><input type="checkbox" v-model="ufwForm.enabled" /> Enable UFW</label>
            </div>
            <div class="section-label-sub">Rules</div>
            <div v-for="(r, i) in ufwForm.rules" :key="i" class="fw-rule">
              <div class="form-row">
                <label>Direction
                  <select v-model="r.direction">
                    <option value="">(any)</option>
                    <option value="in">in</option>
                    <option value="out">out</option>
                  </select>
                </label>
                <label>Action
                  <select v-model="r.action">
                    <option value="allow">allow</option>
                    <option value="deny">deny</option>
                    <option value="reject">reject</option>
                    <option value="limit">limit</option>
                  </select>
                </label>
                <label>Proto
                  <select v-model="r.protocol">
                    <option value="">(any)</option>
                    <option value="tcp">tcp</option>
                    <option value="udp">udp</option>
                  </select>
                </label>
                <label>Port <input v-model="r.port" placeholder="22" /></label>
                <button class="btn-remove" @click="ufwForm.rules.splice(i, 1)">✕</button>
              </div>
              <div class="form-row">
                <label>Iface <input v-model="r.iif" /></label>
                <label>From <input v-model="r.saddr" placeholder="any | 10.0.0.0/24" /></label>
                <label>To <input v-model="r.daddr" /></label>
                <label>Comment <input v-model="r.comment" /></label>
              </div>
            </div>
            <button class="btn-add-sub" @click="ufwForm.rules.push({ direction: 'in', action: 'allow', iif: '', protocol: 'tcp', port: '', saddr: '', daddr: '', comment: '' })">+ Add Rule</button>
          </div>

          <!-- RPi WiFi Form -->
          <div v-if="activeType === 'rpi-wifi'" class="specialized-form">
            <div class="form-row">
              <label>SSID <input v-model="rpiWifiForm.ssid" /></label>
              <label>Password <input v-model="rpiWifiForm.password" type="password" /></label>
              <label>Country <input v-model="rpiWifiForm.country" placeholder="DK" /></label>
              <label class="check-label"><input type="checkbox" v-model="rpiWifiForm.hidden" /> Hidden SSID</label>
            </div>
          </div>

          <!-- RPi SPI Form -->
          <div v-if="activeType === 'rpi-spi'" class="specialized-form">
            <div class="form-row">
              <label class="check-label"><input type="checkbox" v-model="rpiSpiForm.enable" /> Enable SPI Bus</label>
            </div>
          </div>

          <!-- RPi I2C Form -->
          <div v-if="activeType === 'rpi-i2c-enable'" class="specialized-form">
            <div class="form-row">
              <label>Bus <input v-model.number="rpiI2cForm.bus" type="number" /></label>
              <label class="check-label"><input type="checkbox" v-model="rpiI2cForm.enable" /> Enable I2C Bus</label>
            </div>
          </div>

          <!-- RPi Camera Form -->
          <div v-if="activeType === 'rpi-camera'" class="specialized-form">
            <div class="form-row">
              <label class="check-label"><input type="checkbox" v-model="rpiCameraForm.enable" /> Enable Camera</label>
              <label class="check-label"><input type="checkbox" v-model="rpiCameraForm.legacy" /> Use Legacy Stack</label>
            </div>
          </div>

          <!-- RPi Watchdog Form -->
          <div v-if="activeType === 'rpi-watchdog'" class="specialized-form">
            <div class="form-row">
              <label>Timeout (s) <input v-model.number="rpiWatchdogForm.timeout" type="number" /></label>
              <label>Action
                <select v-model="rpiWatchdogForm.action">
                  <option value="enable">Enable</option>
                  <option value="disable">Disable</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Nmap Form -->
          <div v-if="activeType === 'nmap'" class="specialized-form">
            <div class="form-row">
              <label>Target IP / Subnet <input v-model="nmapForm.target" placeholder="127.0.0.1 | 10.0.0.0/24" /></label>
              <label>Scan Type
                <select v-model="nmapForm.scan_type">
                  <option value="quick">Quick (Fast, common ports)</option>
                  <option value="service">Service Detection (-sV)</option>
                  <option value="os">OS & Service Detection (-O -sV)</option>
                  <option value="stealth">Stealth Scan (-sS)</option>
                  <option value="ping">Ping Sweep (-sn)</option>
                  <option value="full">Full Port Scan (-p-)</option>
                </select>
              </label>
            </div>
            <div class="form-row">
              <label>Iface <input v-model="nmapForm.interface" placeholder="(optional)" /></label>
              <label class="check-label"><input type="checkbox" v-model="nmapForm.dns_resolve" /> Resolve DNS</label>
            </div>
          </div>

          <!-- iperf3 Form -->
          <div v-if="activeType === 'iperf3'" class="specialized-form">
            <div class="form-row">
              <label>Mode
                <select v-model="iperf3Form.mode">
                  <option value="client">Client (Test against server)</option>
                  <option value="server">Server (Wait for client)</option>
                </select>
              </label>
              <label v-if="iperf3Form.mode === 'client'">Server IP <input v-model="iperf3Form.server" placeholder="10.0.0.1" /></label>
              <label v-if="iperf3Form.mode === 'client'">Duration (s) <input v-model.number="iperf3Form.duration" type="number" /></label>
            </div>
            <div v-if="iperf3Form.mode === 'client'" class="form-row">
              <label>Bitrate (e.g. 100M) <input v-model="iperf3Form.bitrate" placeholder="(optional)" /></label>
              <label class="check-label"><input type="checkbox" v-model="iperf3Form.udp" /> UDP Mode</label>
              <label class="check-label"><input type="checkbox" v-model="iperf3Form.reverse" /> Reverse (Server to Client)</label>
            </div>
            <p v-if="iperf3Form.mode === 'server'" class="form-help">NODE WILL START SERVER AND WAIT FOR ONE INCOMING CONNECTION.</p>
          </div>

          <!-- MTR Form -->
          <div v-if="activeType === 'mtr'" class="specialized-form">
            <div class="form-row">
              <label>Target <input v-model="mtrForm.target" placeholder="google.com" /></label>
              <label>Cycles <input v-model.number="mtrForm.count" type="number" /></label>
            </div>
          </div>

          <!-- Speedtest Form -->
          <div v-if="activeType === 'speedtest'" class="specialized-form">
            <p class="form-help">RUNS speedtest-cli AGAINST A PUBLIC SERVER. THIS MAY TAKE 30-60 SECONDS.</p>
          </div>

          <!-- DNS Lookup Form -->
          <div v-if="activeType === 'dns-lookup'" class="specialized-form">
            <div class="form-row">
              <label>Domain/Host <input v-model="dnsLookupForm.target" placeholder="example.com" /></label>
              <label>Type
                <select v-model="dnsLookupForm.query_type">
                  <option value="A">A (IPv4)</option>
                  <option value="AAAA">AAAA (IPv6)</option>
                  <option value="MX">MX (Mail)</option>
                  <option value="TXT">TXT</option>
                  <option value="NS">NS</option>
                  <option value="CNAME">CNAME</option>
                </select>
              </label>
              <label>Server <input v-model="dnsLookupForm.server" placeholder="8.8.8.8 (optional)" /></label>
            </div>
          </div>

          <!-- WOL Form -->
          <div v-if="activeType === 'wol'" class="specialized-form">
            <div class="form-row">
              <label>MAC Address <input v-model="wolForm.mac" placeholder="00:11:22:33:44:55" /></label>
              <label>Iface <input v-model="wolForm.interface" placeholder="(optional)" list="detected-interfaces" /></label>
            </div>
          </div>

          <!-- Arp-scan Form -->
          <div v-if="activeType === 'arp-scan'" class="specialized-form">
            <div class="form-row">
              <label>Target <input v-model="arpScanForm.target" placeholder="localnet | 192.168.1.0/24" /></label>
              <label>Iface <input v-model="arpScanForm.interface" placeholder="eth0 (optional)" list="detected-interfaces" /></label>
            </div>
          </div>

          <div class="input-section" v-if="activeType !== 'direct-file'">
            <div class="section-label">
              Data (JSON)
              <span v-if="activeType === 'direct-json'" class="auto-label" style="color: var(--accent-light, #00f0ff); font-weight: bold;"> — DIRECT EDIT MODE</span>
              <span v-else-if="activeType" class="auto-label"> — auto-generated</span>
            </div>
            <textarea
              v-model="inputJson"
              class="json-textarea"
              :style="{ height: activeType === 'direct-json' ? '350px' : '180px' }"
              spellcheck="false"
              placeholder='{ "interface": "eth0", "addresses": ["192.168.1.1/24"] }'
            ></textarea>
          </div>

          <div class="preview-section" v-if="previewCommands.length || previewError">
            <div class="section-label">Generated Commands</div>
            <div v-if="previewError" class="preview-error">{{ previewError }}</div>
            <pre v-else class="preview-pre" v-html="highlightedPreview"></pre>
          </div>

          <div class="results-section" v-if="results.length">
            <div class="section-label">
              <span>⚡ Telemetry Output & Execution Logs</span>
              <button class="btn-clear-results" @click="results = []">🗑️ Clear Logs</button>
            </div>
            
            <div v-for="(r, i) in results" :key="i" class="result-card" :class="{ 'card-err': r.error, 'card-ok': !r.error }">
              <div class="result-card-header" @click="toggleResult(i)">
                <div class="result-status-indicator">
                  <span class="status-dot"></span>
                  <span class="status-label">{{ r.error ? 'CRITICAL ERROR' : 'EXECUTION SUCCESS' }}</span>
                </div>
                <div class="result-cmd-preview"><code>$ {{ r.command }}</code></div>
                <span class="card-chevron">{{ collapsedResults[i] ? '▼' : '▲' }}</span>
              </div>
              
              <div v-if="!collapsedResults[i]" class="result-card-body">
                <pre v-if="r.output" class="result-out">{{ r.output }}</pre>
                <pre v-if="r.error" class="result-err">{{ r.error }}</pre>
                
                <!-- Fix button if command not found -->
                <div v-if="(r.output + r.error).toLowerCase().includes('not found') || (r.output + r.error).toLowerCase().includes('not installed')" class="result-fix">
                  <div class="fix-alert">⚡ Missing dependency detected on the target node.</div>
                  <button class="btn-fix-inline" @click="installMissing(r.command)" :disabled="installingTool">
                      {{ installingTool ? 'INSTALLING DEPENDENCY...' : '🛠️ INSTALL MISSING TOOL' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Interface suggestions datalist -->
    <datalist id="detected-interfaces">
      <option v-for="iface in detectedInterfaces" :key="iface.name" :value="iface.name">
        {{ iface.status }} — {{ iface.ips.join(', ') || 'no IP' }}
      </option>
    </datalist>

    <!-- Glowing Cyber Toast Notification -->
    <Transition name="toast">
      <div v-if="showToast" class="cyber-toast">
        <div class="toast-glow"></div>
        <span class="toast-icon">⚡</span>
        <div class="toast-text">
          <span class="toast-label">COPIED TO SYSTEM CLIPBOARD</span>
          <span class="toast-val">{{ lastCopied }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import { api } from '@/api/client'
import type { CommandResult } from '@/types'

const props = defineProps<{ nodeId: string }>()

const CONFIG_CATEGORIES = {
  network: {
    icon: '🌐', label: 'Network',
    types: [
      { type: 'interface', label: 'Interface Setup' },
      { type: 'routes', label: 'Routes' },
      { type: 'dns', label: 'DNS / Resolver' },
      { type: 'nat', label: 'NAT / Forwarding' },
      { type: 'vlan-router', label: 'VLAN Router' },
      { type: 'vlan-switch', label: 'VLAN Switch' },
      { type: 'wireguard', label: 'WireGuard' },
      { type: 'forwarding', label: 'IP Forwarding' },
      { type: 'reset-node', label: 'Reset Node' },
    ]
  },
  firewall: {
    icon: '🛡️', label: 'Firewall',
    types: [
      { type: 'iptables', label: 'iptables' },
      { type: 'nftables', label: 'nftables' },
      { type: 'ufw', label: 'UFW' },
    ]
  },
  linux: {
    icon: '🐧', label: 'Linux',
    types: [
      { type: 'service', label: 'Services' },
      { type: 'package', label: 'Packages' },
      { type: 'user', label: 'Users' },
      { type: 'hostname', label: 'Hostname' },
      { type: 'sysctl', label: 'Sysctl' },
      { type: 'file-write', label: 'Write File' },
    ]
  },
  rpi: {
    icon: '🍓', label: 'Raspberry PI',
    types: [
      { type: 'rpi-info', label: 'System Info' },
      { type: 'rpi-temperature', label: 'Temp & Throttle' },
      { type: 'rpi-gpio-read-all', label: 'GPIO Status' },
      { type: 'rpi-wifi', label: 'WiFi Setup' },
      { type: 'rpi-spi', label: 'SPI Bus' },
      { type: 'rpi-i2c-enable', label: 'I2C Bus' },
      { type: 'rpi-camera', label: 'Camera' },
      { type: 'rpi-watchdog', label: 'Watchdog' },
    ]
  },
  tools: {
    icon: '🔧', label: 'Network Tools',
    types: [
        { type: 'nmap', label: 'Nmap Scanner' },
        { type: 'iperf3', label: 'iperf3 Bandwidth' },
        { type: 'mtr', label: 'MTR Traceroute' },
        { type: 'speedtest', label: 'Speedtest CLI' },
        { type: 'dns-lookup', label: 'DNS Lookup (dig)' },
        { type: 'wol', label: 'Wake-on-LAN' },
        { type: 'arp-scan', label: 'Arp-scan' },
    ]
  },
  advanced: {
    icon: '⚙️', label: 'Advanced',
    types: [
      { type: 'direct-file', label: '📝 Direct File Editor' },
      { type: 'direct-json', label: '⚡ Direct JSON Config' },
    ]
  }
}

const activeType      = ref<string | null>(null)

interface GuideData {
  title: string
  description: string
  files: string[]
  tips: string[]
}

const CYBER_GUIDES: Record<string, GuideData> = {
  interface: {
    title: 'Network Interfaces',
    description: 'Configure network interface IP addresses, subnets, and state.',
    files: ['/etc/network/interfaces', '/etc/dhcpcd.conf'],
    tips: ['Double-check CIDR notation (e.g. /24).', 'Applying this might temporarily disrupt SSH connections if configured on the active interface.']
  },
  routes: {
    title: 'Static Routing',
    description: 'Add static route configurations to target remote subnets through a specific gateway.',
    files: ['Active routing table', '/etc/network/interfaces'],
    tips: ['Ensure the gateway IP is reachable in your local subnet.', 'Use 0.0.0.0/0 to change the default gateway.']
  },
  dns: {
    title: 'DNS Resolution',
    description: 'Set DNS servers and domain search paths for name resolution.',
    files: ['/etc/resolv.conf'],
    tips: ['Set primary DNS to 1.1.1.1 or 8.8.8.8 for public internet access.', 'Add a search domain if you are using a local DNS zone.']
  },
  nat: {
    title: 'NAT & Port Forwarding',
    description: 'Establish IP masquerading (NAT) and port forward ingress traffic to private hosts.',
    files: ['iptables rules', '/etc/sysctl.conf'],
    tips: ['Masquerading requires IP forwarding to be enabled in sysctl.', 'Port forwarding is perfect for making internal services public.']
  },
  'vlan-router': {
    title: 'VLAN Router',
    description: 'Configure VLAN tagged sub-interfaces on routers for 802.1Q routing.',
    files: ['/etc/network/interfaces', 'kernel 8021q module'],
    tips: ['Ensure your physical interfaces support VLAN tag encapsulation.', 'Always specify both a parent interface (e.g., eth0) and a VLAN ID.']
  },
  'vlan-switch': {
    title: 'VLAN Switch (Bridge)',
    description: 'Configure bridge and switch ports for vlan filtering and member ports.',
    files: ['/etc/network/interfaces', 'bridge-utils'],
    tips: ['Define trunk ports to carry multiple VLAN tags.', 'Assign access ports for individual tag untagging.']
  },
  wireguard: {
    title: 'WireGuard VPN',
    description: 'Deploy peer-to-peer secure VPN tunnels utilizing private/public key cryptography.',
    files: ['/etc/wireguard/wg0.conf'],
    tips: ['Ensure UDP port 51820 (or your configured port) is open in the firewall.', 'Generate new private/public keys for security.']
  },
  forwarding: {
    title: 'IP Forwarding',
    description: 'Allow network packets to traverse between different interfaces on this node.',
    files: ['/etc/sysctl.conf', '/proc/sys/net/ipv4/ip_forward'],
    tips: ['Essential for routers, NAT boxes, and WireGuard gateways.', 'Changes will take effect instantly and persist across reboots.']
  },
  service: {
    title: 'System Services',
    description: 'Manage initialization and state (start/stop/enable) of system daemons.',
    files: ['systemd system init', 'sysvinit / openrc'],
    tips: ['Enable services so they start automatically on boot.', 'Restarting a service like sshd can drop existing active sessions.']
  },
  package: {
    title: 'Package Manager',
    description: 'Install or update binary applications on the remote node.',
    files: ['apk, apt, or pacman configurations'],
    tips: ['Verify package names match exactly.', 'Use diagnostic console to verify if the binary is installed.']
  },
  ufw: {
    title: 'UFW Firewall',
    description: 'Manage uncomplicated firewall rules, policies, and ports.',
    files: ['/etc/ufw/before.rules', '/lib/ufw/user.rules'],
    tips: ['Ensure port 22/SSH is allowed BEFORE enabling UFW to prevent lockout!', 'Always default-deny incoming and default-allow outgoing.']
  },
  sysctl: {
    title: 'Sysctl Parameters',
    description: 'Fine-tune Linux kernel parameters dynamically or persistently.',
    files: ['/etc/sysctl.conf'],
    tips: ['Changing sysctl values can alter system security and network behavior instantly.', 'Run sysctl -p to reload.']
  }
}

const guideExpanded = ref(true)
const activeGuide = computed(() => {
  if (!activeType.value) return null
  return CYBER_GUIDES[activeType.value] || null
})

const collapsedResults = ref<Record<number, boolean>>({})
function toggleResult(index: number) {
  collapsedResults.value[index] = !collapsedResults.value[index]
}

function escapeHtml(unsafe: string) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
}

function highlightPreviewCommands(text: string): string {
  let highlighted = escapeHtml(text)
  
  const sysCmds = /\b(ip|rc-update|sysctl|systemctl|cat|chmod|wg-quick|wg|apk|apt|ufw|iptables|mkdir|echo|tee|touch)\b/g
  const heredoc = /(&lt;&lt;\s*&#039;?EOF&#039;?|EOF|__NETRUNNER_EOF__)/g
  const ipAddr = /\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:\/\d{1,2})?)\b/g
  const strings = /(&quot;[^&]*&quot;|&#039;[^&]*&#039;)/g
  
  highlighted = highlighted.replace(strings, '<span class="shell-str">$1</span>')
  highlighted = highlighted.replace(heredoc, '<span class="shell-heredoc">$1</span>')
  highlighted = highlighted.replace(sysCmds, '<span class="shell-cmd">$1</span>')
  highlighted = highlighted.replace(ipAddr, '<span class="shell-ip">$1</span>')
  highlighted = highlighted.replace(/(#[^\n&]*)/g, '<span class="shell-comment">$1</span>')
  
  return highlighted
}

const highlightedPreview = computed(() => {
  if (!previewCommands.value.length) return ''
  return highlightPreviewCommands(previewCommands.value.join('\n'))
})
const collapsedCats   = ref<Set<string>>(new Set())

function toggleCat(key: string) {
  if (collapsedCats.value.has(key)) {
    collapsedCats.value.delete(key)
  } else {
    collapsedCats.value.add(key)
  }
}
const inputJson       = ref('{}')
const previewCommands = ref<string[]>([])
const previewError    = ref('')
const results         = ref<CommandResult[]>([])
const loading         = ref(false)
const installingTool  = ref(false)
const persistMode     = ref(false)

const defaultInterfaceForm    = () => ({ interface: 'eth0', addresses: [''] as string[], dhcp: false, action: 'add', state: 'none', vlanParent: '', vlanId: undefined })
const defaultRouteForm        = () => ({ routes: [{ dst: '10.1.0.0/24', via: '10.0.0.254', dev: '', metric: 0 }], isDelete: false })
const defaultDnsForm          = () => ({ nameservers: ['8.8.8.8'], search: ['local'], hostname: '', domain: '', records: [{ name: '', value: '' }] })
const defaultNatForm          = () => ({ outbound_iface: 'eth0', inbound_iface: 'eth1', source_subnet: '10.0.0.0/24', masquerade: true, port_forwards: [{ proto: 'tcp', external_port: '80', target_ip: '10.0.0.10', target_port: '80' }] })
const defaultVlanRouterForm   = () => ({ interface: 'eth0', vlans: [{ id: '10', address: '10.0.10.1/24', description: 'Management', action: 'add' }] })
const defaultVlanSwitchForm   = () => ({ bridge: 'br0', vlans: [{ id: '10', name: 'MGMT' }], ports: [{ iface: 'eth1', mode: 'access', vlan: '10', allowed: '' }] })
const defaultWireguardForm    = () => ({ action: 'add', interface: 'wg0', private_key: '', address: '10.0.0.1/24', listen_port: 51820, dns: '', mtu: '', post_up: '', post_down: '', peers: [{ public_key: '', preshared_key: '', endpoint: '', allowed_ips: '0.0.0.0/0', persistent_keepalive: '' }] })
const defaultForwardingForm   = () => ({ ipv4: true, ipv6: false })
const defaultServiceForm      = () => ({ name: '', action: 'status' })
const defaultPackageForm      = () => ({ packages: '', action: 'install', manager: 'auto' })
const defaultUserForm         = () => ({ username: '', action: 'create', password: '', groups: '', shell: '/bin/bash', home: '', system: false })
const defaultHostnameForm     = () => ({ hostname: '', domain: '' })
const defaultSysctlForm       = () => ({ params: [{ key: 'net.ipv4.ip_forward', value: '1' }], persist: true })
const defaultFileWriteForm    = () => ({ path: '/tmp/test.txt', content: '', mode: '644', owner: 'root', backup: false })
const defaultIptablesForm     = () => ({
  defaults: { INPUT: 'DROP', FORWARD: 'DROP', OUTPUT: 'ACCEPT' },
  rules: [
    { table: 'filter', chain: 'INPUT', protocol: '', iif: 'lo',  oif: '', saddr: '', daddr: '', sport: '', dport: '', ct_state: '',                      action: 'ACCEPT', nat_addr: '', log_prefix: '' },
    { table: 'filter', chain: 'INPUT', protocol: '', iif: '',    oif: '', saddr: '', daddr: '', sport: '', dport: '', ct_state: 'ESTABLISHED,RELATED', action: 'ACCEPT', nat_addr: '', log_prefix: '' },
  ],
})
const defaultUfwForm          = () => ({
  defaults: { incoming: 'deny', outgoing: 'allow', routed: 'deny' },
  enabled: true,
  rules: [
    { direction: 'in', action: 'allow', iif: '', protocol: 'tcp', port: '22', saddr: '', daddr: '', comment: 'SSH' },
  ],
})
const defaultNftablesForm     = () => ({
  family: 'inet',
  table_name: 'filter',
  chain_name: 'input',
  chain_type: 'filter',
  hook: 'input',
  priority: '0',
  policy: 'drop',
  rules: [
    { iif: 'lo', oif: '', saddr: '', daddr: '', protocol: '', sport: '', dport: '', ct_state: '',                      action: 'accept', nat_addr: '', log_prefix: '', comment: 'loopback' },
    { iif: '',   oif: '', saddr: '', daddr: '', protocol: '', sport: '', dport: '', ct_state: 'established,related', action: 'accept', nat_addr: '', log_prefix: '', comment: '' },
  ],
})
const defaultRpiWifiForm      = () => ({ ssid: '', password: '', country: 'DK', hidden: false })
const defaultRpiSpiForm       = () => ({ enable: true })
const defaultRpiI2cForm       = () => ({ bus: 1, enable: true })
const defaultRpiCameraForm    = () => ({ enable: true, legacy: false })
const defaultRpiWatchdogForm  = () => ({ timeout: 14, action: 'enable' })
const defaultNmapForm         = () => ({ target: '127.0.0.1', scan_type: 'quick', interface: '', dns_resolve: false })
const defaultIperf3Form       = () => ({ mode: 'client', server: '', duration: 10, udp: false, reverse: false, bitrate: '' })
const defaultMtrForm          = () => ({ target: '', count: 5 })
const defaultDnsLookupForm    = () => ({ target: '', query_type: 'A', server: '' })
const defaultWolForm          = () => ({ mac: '', interface: '' })
const defaultArpScanForm      = () => ({ target: 'localnet', interface: '' })

function resetForm() {
  if (!activeType.value) return
  if (!confirm(`Clear current ${activeType.value} configuration form?`)) return
  
  if (activeType.value === 'direct-file') {
    directFileContent.value = ''
    directFilePath.value = '/etc/wireguard/wg0.conf'
    directFileMode.value = '600'
    directFileBackup.value = false
    previewCommands.value = []
    previewError.value = ''
    return
  }
  
  if (activeType.value === 'direct-json') {
    inputJson.value = JSON_BOILERPLATES[directJsonGeneratorType.value] || '{}'
    previewCommands.value = []
    previewError.value = ''
    return
  }
  
  const defaults: Record<string, any> = {
    interface: defaultInterfaceForm, routes: defaultRouteForm, dns: defaultDnsForm,
    nat: defaultNatForm, 'vlan-router': defaultVlanRouterForm, 'vlan-switch': defaultVlanSwitchForm,
    wireguard: defaultWireguardForm, forwarding: defaultForwardingForm, service: defaultServiceForm,
    package: defaultPackageForm, user: defaultUserForm, hostname: defaultHostnameForm,
    sysctl: defaultSysctlForm, 'file-write': defaultFileWriteForm, iptables: defaultIptablesForm,
    ufw: defaultUfwForm, nftables: defaultNftablesForm,
    'rpi-wifi': defaultRpiWifiForm, 'rpi-spi': defaultRpiSpiForm, 'rpi-i2c-enable': defaultRpiI2cForm,
    'rpi-camera': defaultRpiCameraForm, 'rpi-watchdog': defaultRpiWatchdogForm,
    nmap: defaultNmapForm, iperf3: defaultIperf3Form, mtr: defaultMtrForm,
    speedtest: () => ({}), 'dns-lookup': defaultDnsLookupForm, wol: defaultWolForm,
    'arp-scan': defaultArpScanForm
  }

  const formRefs: Record<string, any> = {
    interface: interfaceForm, routes: routeForm, dns: dnsForm,
    nat: natForm, 'vlan-router': vlanRouterForm, 'vlan-switch': vlanSwitchForm,
    wireguard: wireguardForm, forwarding: forwardingForm, service: serviceForm,
    package: packageForm, user: userForm, hostname: hostnameForm,
    sysctl: sysctlForm, 'file-write': fileWriteForm, iptables: iptablesForm,
    ufw: ufwForm, nftables: nftablesForm,
    'rpi-wifi': rpiWifiForm, 'rpi-spi': rpiSpiForm, 'rpi-i2c-enable': rpiI2cForm,
    'rpi-camera': rpiCameraForm, 'rpi-watchdog': rpiWatchdogForm,
    nmap: nmapForm, iperf3: iperf3Form, mtr: mtrForm,
    'dns-lookup': dnsLookupForm, wol: wolForm, 'arp-scan': arpScanForm
  }

  if (defaults[activeType.value] && formRefs[activeType.value]) {
    formRefs[activeType.value].value = defaults[activeType.value]()
    previewCommands.value = []
    previewError.value = ''
  }
}

const interfaceForm = ref(defaultInterfaceForm())

function syncInterfaceForm() {
  // Auto-append /24 hint for addresses missing CIDR (we keep it for the warning check)
  const validated = interfaceForm.value.addresses.filter(a => a.trim()).map(a => {
    const trimmed = a.trim()
    return trimmed
  })
  inputJson.value = JSON.stringify({
    interface: interfaceForm.value.interface,
    addresses: validated,
    dhcp: interfaceForm.value.dhcp,
    action: interfaceForm.value.action,
    state: interfaceForm.value.state
  }, null, 2)
}

const routeForm       = ref(defaultRouteForm())
const dnsForm         = ref(defaultDnsForm())
const natForm         = ref(defaultNatForm())
const vlanRouterForm  = ref(defaultVlanRouterForm())
const vlanSwitchForm  = ref(defaultVlanSwitchForm())
const wireguardForm   = ref(defaultWireguardForm())
const generatedPublicKey = ref('')
const hidePrivateKey = ref(true)
const wgAdvancedExpanded = ref(false)
const generatingKeys = ref(false)
const wgLoadingFromNode = ref(false)
const wgProfileName = ref('')
const wgSelectedProfileId = ref('')

interface WireguardKeyItem {
  id: string
  timestamp: string
  privateKey: string
  publicKey: string
  label?: string
  hidePrivate?: boolean
}

interface WireguardProfile {
  id: string
  nodeId: string
  name: string
  interface: string
  updatedAt: string
  data: ReturnType<typeof defaultWireguardForm>
  publicKey?: string
}

const keyHistory = ref<WireguardKeyItem[]>([])
const wgHistoryExpanded = ref(false)
const wgProfiles = ref<WireguardProfile[]>([])
const currentWgProfiles = computed(() => wgProfiles.value.filter(p => p.nodeId === props.nodeId))

function cloneWireguardForm(): ReturnType<typeof defaultWireguardForm> {
  return JSON.parse(JSON.stringify(wireguardForm.value))
}

function normalizeWireguardForm(data: any): ReturnType<typeof defaultWireguardForm> {
  const defaults = defaultWireguardForm()
  const peers = Array.isArray(data?.peers) && data.peers.length
    ? data.peers.map((peer: any) => ({
        public_key: peer.public_key || peer.PublicKey || '',
        preshared_key: peer.preshared_key || peer.PresharedKey || '',
        endpoint: peer.endpoint || peer.Endpoint || '',
        allowed_ips: Array.isArray(peer.allowed_ips) ? peer.allowed_ips.join(', ') : (peer.allowed_ips || peer.AllowedIPs || ''),
        persistent_keepalive: peer.persistent_keepalive || peer.PersistentKeepalive || ''
      }))
    : defaults.peers

  return {
    ...defaults,
    ...data,
    address: data?.address || (Array.isArray(data?.addresses) ? data.addresses[0] : defaults.address),
    listen_port: Number(data?.listen_port || data?.ListenPort || defaults.listen_port),
    peers
  }
}

function loadWgProfiles() {
  try {
    const raw = localStorage.getItem('nr_wg_profiles_v1')
    wgProfiles.value = raw ? JSON.parse(raw) : []
  } catch (e) {
    console.error('Failed to load WireGuard profiles:', e)
    wgProfiles.value = []
  }
}

function saveWgProfiles() {
  try {
    localStorage.setItem('nr_wg_profiles_v1', JSON.stringify(wgProfiles.value))
  } catch (e) {
    console.error('Failed to save WireGuard profiles:', e)
  }
}

function saveWireguardProfile() {
  const now = new Date().toISOString()
  const iface = wireguardForm.value.interface || 'wg0'
  const name = (wgProfileName.value || `${props.nodeId} ${iface}`).trim()
  const data = cloneWireguardForm()
  const existing = wgProfiles.value.find(p => p.id === wgSelectedProfileId.value)

  if (existing) {
    existing.name = name
    existing.interface = iface
    existing.updatedAt = now
    existing.data = data
    existing.publicKey = generatedPublicKey.value
  } else {
    const profile: WireguardProfile = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      nodeId: props.nodeId,
      name,
      interface: iface,
      updatedAt: now,
      data,
      publicKey: generatedPublicKey.value
    }
    wgProfiles.value.unshift(profile)
    wgSelectedProfileId.value = profile.id
  }

  wgProfileName.value = name
  saveWgProfiles()
}

function loadWireguardProfile() {
  const profile = wgProfiles.value.find(p => p.id === wgSelectedProfileId.value)
  if (!profile) return
  wireguardForm.value = normalizeWireguardForm(profile.data)
  generatedPublicKey.value = profile.publicKey || ''
  wgProfileName.value = profile.name
  syncWireguardForm()
}

function deleteWireguardProfile() {
  const profile = wgProfiles.value.find(p => p.id === wgSelectedProfileId.value)
  if (!profile) return
  if (!confirm(`Delete saved WireGuard profile "${profile.name}"?`)) return
  wgProfiles.value = wgProfiles.value.filter(p => p.id !== profile.id)
  wgSelectedProfileId.value = ''
  wgProfileName.value = ''
  saveWgProfiles()
}

function parseWireguardConfig(conf: string, iface: string): ReturnType<typeof defaultWireguardForm> {
  const parsed = defaultWireguardForm()
  parsed.interface = iface
  parsed.peers = []

  let section = ''
  let currentPeer: any = null

  for (const rawLine of conf.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue

    if (/^\[interface\]$/i.test(line)) {
      section = 'interface'
      currentPeer = null
      continue
    }
    if (/^\[peer\]$/i.test(line)) {
      section = 'peer'
      currentPeer = { public_key: '', preshared_key: '', endpoint: '', allowed_ips: '', persistent_keepalive: '' }
      parsed.peers.push(currentPeer)
      continue
    }

    const idx = line.indexOf('=')
    if (idx === -1) continue
    const key = line.slice(0, idx).trim().toLowerCase()
    const value = line.slice(idx + 1).trim()

    if (section === 'interface') {
      if (key === 'privatekey') parsed.private_key = value
      else if (key === 'address') parsed.address = value
      else if (key === 'listenport') parsed.listen_port = Number(value) || parsed.listen_port
      else if (key === 'dns') parsed.dns = value
      else if (key === 'mtu') parsed.mtu = value
      else if (key === 'postup') parsed.post_up = value
      else if (key === 'postdown') parsed.post_down = value
    } else if (section === 'peer' && currentPeer) {
      if (key === 'publickey') currentPeer.public_key = value
      else if (key === 'presharedkey') currentPeer.preshared_key = value
      else if (key === 'endpoint') currentPeer.endpoint = value
      else if (key === 'allowedips') currentPeer.allowed_ips = value
      else if (key === 'persistentkeepalive') currentPeer.persistent_keepalive = Number(value) || value
    }
  }

  if (!parsed.peers.length) parsed.peers = defaultWireguardForm().peers
  return parsed
}

function safeWireguardInterfaceName(value: string): string {
  const iface = (value || 'wg0').trim()
  if (!/^wg[a-zA-Z0-9_.-]*$/.test(iface)) {
    throw new Error('WireGuard interface must start with "wg" and contain only letters, numbers, underscore, dot, or dash.')
  }
  return iface
}

async function loadWireguardFromNode() {
  wgLoadingFromNode.value = true
  try {
    const iface = safeWireguardInterfaceName(wireguardForm.value.interface)
    const res = await api.executeNode(props.nodeId, [
      `cat /etc/wireguard/${iface}.conf 2>/dev/null || echo "__NR_WG_CONF_NOT_FOUND__"`,
      `cat /etc/wireguard/publickey 2>/dev/null || true`
    ])
    const conf = res.results?.[0]?.output || ''
    if (!conf.trim() || conf.includes('__NR_WG_CONF_NOT_FOUND__')) {
      alert(`No WireGuard config found at /etc/wireguard/${iface}.conf`)
      return
    }

    wireguardForm.value = parseWireguardConfig(conf, iface)
    generatedPublicKey.value = (res.results?.[1]?.output || '').trim()
    wgProfileName.value = `${props.nodeId} ${iface}`
    syncWireguardForm()
  } catch (e: any) {
    alert(`Failed to load WireGuard config from node: ${e.message || e}`)
  } finally {
    wgLoadingFromNode.value = false
  }
}

function loadKeyHistory() {
  try {
    const raw = localStorage.getItem('nr_wg_key_history')
    if (raw) {
      keyHistory.value = JSON.parse(raw).map((item: any) => ({
        ...item,
        hidePrivate: item.hidePrivate !== false
      }))
    }
  } catch (e) {
    console.error('Failed to load WireGuard key history:', e)
  }
}

function saveKeyHistory() {
  try {
    localStorage.setItem('nr_wg_key_history', JSON.stringify(keyHistory.value))
  } catch (e) {
    console.error('Failed to save WireGuard key history:', e)
  }
}

function addKeyToHistory(privateKey: string, publicKey: string) {
  const now = new Date()
  const timestamp = now.toLocaleString('da-DK', { hour12: false })
  
  const newItem: WireguardKeyItem = {
    id: Math.random().toString(36).substring(2, 9),
    timestamp,
    privateKey,
    publicKey,
    label: `Key for ${wireguardForm.value.interface || 'wg0'}`,
    hidePrivate: true
  }
  
  keyHistory.value.unshift(newItem)
  saveKeyHistory()
}

function deleteKeyFromHistory(id: string) {
  if (confirm('Vil du fjerne denne nøgle fra din historik?')) {
    keyHistory.value = keyHistory.value.filter(k => k.id !== id)
    saveKeyHistory()
  }
}

function loadKeyIntoForm(item: WireguardKeyItem) {
  wireguardForm.value.private_key = item.privateKey
  generatedPublicKey.value = item.publicKey
  syncWireguardForm()
}

// Initial load
loadKeyHistory()
loadWgProfiles()
const forwardingForm  = ref(defaultForwardingForm())
const serviceForm     = ref(defaultServiceForm())
const packageForm     = ref(defaultPackageForm())
const userForm        = ref(defaultUserForm())
const hostnameForm    = ref(defaultHostnameForm())
const sysctlForm      = ref(defaultSysctlForm())
const fileWriteForm   = ref(defaultFileWriteForm())
const iptablesForm    = ref(defaultIptablesForm())
const ufwForm         = ref(defaultUfwForm())
const nftablesForm    = ref(defaultNftablesForm())

const rpiWifiForm     = ref(defaultRpiWifiForm())
const rpiSpiForm      = ref(defaultRpiSpiForm())
const rpiI2cForm      = ref(defaultRpiI2cForm())
const rpiCameraForm   = ref(defaultRpiCameraForm())
const rpiWatchdogForm = ref(defaultRpiWatchdogForm())
const nmapForm        = ref(defaultNmapForm())
const iperf3Form      = ref(defaultIperf3Form())
const mtrForm         = ref(defaultMtrForm())
const dnsLookupForm   = ref(defaultDnsLookupForm())
const wolForm         = ref(defaultWolForm())
const arpScanForm     = ref(defaultArpScanForm())

// Advanced direct editing refs
const directFilePath = ref('/etc/wireguard/wg0.conf')
const directFileContent = ref('')
const directFileMode = ref('600')
const directFileBackup = ref(false)
const loadingFile = ref(false)
const directJsonGeneratorType = ref('wireguard')

const JSON_BOILERPLATES: Record<string, string> = {
  interface: JSON.stringify({ interface: "eth1", addresses: ["192.168.10.1/24"], gateway: "192.168.10.254", up: true }, null, 2),
  routes: JSON.stringify({ routes: [{ destination: "10.0.0.0/8", gateway: "192.168.10.254" }] }, null, 2),
  dns: JSON.stringify({ nameservers: ["8.8.8.8", "1.1.1.1"] }, null, 2),
  nat: JSON.stringify({ action: "setup", out_interface: "eth0", inside_subnets: ["192.168.110.0/24"] }, null, 2),
  wireguard: JSON.stringify({ interface: "wg0", action: "add", addresses: ["10.110.0.1/24"], listen_port: 51820, private_key: "wPOIlmY3PXlwkJ4NP2PzHaetquG+kNHzgv+R/fcMgnw=", peers: [{ public_key: "ZG/F+OQdWRxBHlqkJPsQFlMtlq1URE4WT7sI8g8TlAc=", allowed_ips: ["10.110.0.2/32"], endpoint: "192.168.110.2:51820", persistent_keepalive: 25 }] }, null, 2),
  forwarding: JSON.stringify({ enabled: true }, null, 2),
  iptables: JSON.stringify({ defaults: { INPUT: "ACCEPT", FORWARD: "DROP", OUTPUT: "ACCEPT" }, rules: [] }, null, 2),
  nftables: JSON.stringify({ ruleset: "table inet filter {\n  chain input {\n    type filter hook input priority 0; policy accept;\n  }\n}" }, null, 2),
  ufw: JSON.stringify({ enabled: true, defaults: { incoming: "deny", outgoing: "allow" }, rules: [] }, null, 2),
  service: JSON.stringify({ name: "wireguard", action: "start", enabled: true }, null, 2),
  package: JSON.stringify({ name: "wireguard-tools", action: "install" }, null, 2),
  "file-write": JSON.stringify({ path: "/etc/wireguard/wg0.conf", content: "[Interface]\nAddress = 10.110.0.1/24\n", mode: "600", owner: "root", backup: true }, null, 2)
}

function syncRouteForm() {
  inputJson.value = JSON.stringify({
    routes: routeForm.value.routes.filter(r => r.dst),
    action: routeForm.value.isDelete ? 'del' : 'add'
  }, null, 2)
}

function syncDnsForm() {
  inputJson.value = JSON.stringify({
    ...dnsForm.value,
    records: dnsForm.value.records.filter(r => r.name)
  }, null, 2)
}

function syncNatForm() {
  inputJson.value = JSON.stringify({
    ...natForm.value,
    port_forwards: natForm.value.port_forwards.filter(f => f.external_port)
  }, null, 2)
}

function syncVlanRouterForm() {
  inputJson.value = JSON.stringify({
    ...vlanRouterForm.value,
    vlans: vlanRouterForm.value.vlans
  }, null, 2)
}

function syncVlanSwitchForm() {
  inputJson.value = JSON.stringify({
    ...vlanSwitchForm.value,
    vlans: vlanSwitchForm.value.vlans,
    ports: vlanSwitchForm.value.ports.filter(p => p.iface)
  }, null, 2)
}

function syncWireguardForm() {
  inputJson.value = JSON.stringify({
    ...wireguardForm.value,
    peers: wireguardForm.value.peers.filter(p => p.public_key)
  }, null, 2)
}

async function generateWireguardKeys() {
  generatingKeys.value = true
  try {
    const res = await api.generateWireguardKeys()
    wireguardForm.value.private_key = res.private_key
    generatedPublicKey.value = res.public_key
    syncWireguardForm()
    addKeyToHistory(res.private_key, res.public_key)
  } catch (err: any) {
    console.error(err)
  } finally {
    generatingKeys.value = false
  }
}

function syncForwardingForm() {
  inputJson.value = JSON.stringify(forwardingForm.value, null, 2)
}

function syncServiceForm() {
  inputJson.value = JSON.stringify(serviceForm.value, null, 2)
}

function syncPackageForm() {
  inputJson.value = JSON.stringify({
    ...packageForm.value,
    packages: packageForm.value.packages.split(',').map(p => p.trim()).filter(Boolean)
  }, null, 2)
}

function syncUserForm() {
  inputJson.value = JSON.stringify({
    ...userForm.value,
    groups: userForm.value.groups.split(',').map(g => g.trim()).filter(Boolean)
  }, null, 2)
}

function syncHostnameForm() {
  inputJson.value = JSON.stringify(hostnameForm.value, null, 2)
}

function syncSysctlForm() {
  inputJson.value = JSON.stringify({
    ...sysctlForm.value,
    params: sysctlForm.value.params.filter(p => p.key)
  }, null, 2)
}

function syncFileWriteForm() {
  inputJson.value = JSON.stringify(fileWriteForm.value, null, 2)
}

function syncNmapForm() {
  inputJson.value = JSON.stringify(nmapForm.value, null, 2)
}

function syncIperf3Form() { inputJson.value = JSON.stringify(iperf3Form.value, null, 2) }
function syncMtrForm() { inputJson.value = JSON.stringify(mtrForm.value, null, 2) }
function syncDnsLookupForm() { inputJson.value = JSON.stringify(dnsLookupForm.value, null, 2) }
function syncWolForm() { inputJson.value = JSON.stringify(wolForm.value, null, 2) }
function syncArpScanForm() { inputJson.value = JSON.stringify(arpScanForm.value, null, 2) }

function _stripEmpty<T extends Record<string, unknown>>(obj: T): Partial<T> {
  const out: Partial<T> = {}
  for (const k in obj) {
    const v = obj[k]
    if (v !== '' && v !== null && v !== undefined) out[k] = v
  }
  return out
}

function syncIptablesForm() {
  inputJson.value = JSON.stringify({
    defaults: iptablesForm.value.defaults,
    rules: iptablesForm.value.rules.map(r => _stripEmpty(r)),
  }, null, 2)
}

function syncUfwForm() {
  inputJson.value = JSON.stringify({
    defaults: ufwForm.value.defaults,
    enabled: ufwForm.value.enabled,
    rules: ufwForm.value.rules.map(r => _stripEmpty(r)),
  }, null, 2)
}

function syncNftablesForm() {
  const f = nftablesForm.value
  inputJson.value = JSON.stringify({
    tables: [{
      family: f.family,
      name: f.table_name,
      chains: [{
        name: f.chain_name,
        type: f.chain_type,
        hook: f.hook,
        priority: f.priority,
        policy: f.policy,
        rules: f.rules.map(r => _stripEmpty(r)),
      }],
    }],
  }, null, 2)
}

function syncRpiWifiForm() { inputJson.value = JSON.stringify(rpiWifiForm.value, null, 2) }
function syncRpiSpiForm() { inputJson.value = JSON.stringify(rpiSpiForm.value, null, 2) }
function syncRpiI2cForm() { inputJson.value = JSON.stringify(rpiI2cForm.value, null, 2) }
function syncRpiCameraForm() { inputJson.value = JSON.stringify(rpiCameraForm.value, null, 2) }
function syncRpiWatchdogForm() { inputJson.value = JSON.stringify(rpiWatchdogForm.value, null, 2) }

async function loadDirectFile() {
  if (!directFilePath.value) return
  loadingFile.value = true
  try {
    const res = await api.executeNode(props.nodeId, [`cat ${directFilePath.value}`])
    const r = res.results?.[0]
    if (r && !r.error) {
      directFileContent.value = r.output || ''
    } else {
      alert(`Failed to load file: ${r?.error || 'File empty or not found.'}`)
    }
  } catch (e: any) {
    alert(`Error: ${e.message || e}`)
  } finally {
    loadingFile.value = false
  }
}

function syncDirectFileForm() {
  inputJson.value = JSON.stringify({
    path: directFilePath.value,
    content: directFileContent.value,
    mode: directFileMode.value,
    owner: 'root',
    backup: directFileBackup.value
  }, null, 2)
}

const syncFnMap: Record<string, () => void> = {}

function selectType(type: string) {
  activeType.value = type
  previewCommands.value = []
  previewError.value = ''
  results.value = []
  if (syncFnMap[type]) syncFnMap[type]()
  else if (type === 'reset-node') inputJson.value = '{}'
  else inputJson.value = '{}'
}

async function getPreview() {
  previewError.value = ''
  previewCommands.value = []
  try {
    const data = JSON.parse(inputJson.value)
    let previewType = activeType.value!
    if (previewType === 'direct-json') {
      previewType = directJsonGeneratorType.value
    } else if (previewType === 'direct-file') {
      previewType = 'file-write'
    }
    const res = await api.preview(previewType, data)
    let cmds = res.commands
    if (persistMode.value && cmds.length) {
      const wrapped = await api.preview('persist', { name: previewType, commands: cmds })
      cmds = wrapped.commands
    }
    previewCommands.value = cmds
  } catch (e) {
    previewError.value = String(e)
  }
}

async function applyConfig() {
  if (!previewCommands.value.length) return
  loading.value = true
  results.value = []
  previewError.value = ''
  try {
    const cmds = persistMode.value
      ? [previewCommands.value.join('\n')]
      : previewCommands.value
    const res = await api.executeNode(props.nodeId, cmds)
    results.value = res.results
    
    // Automatically trigger a refresh of live telemetry if no execution errors occurred
    const hasError = res.results?.some(r => r.error)
    if (!hasError) {
      await fetchLiveInterfaces()
      if (activeType.value === 'wireguard' && wireguardForm.value.action === 'delete') {
        const deletedIface = wireguardForm.value.interface
        wireguardForm.value.private_key = ''
        generatedPublicKey.value = ''
        wireguardForm.value.action = 'add'
        syncWireguardForm()
        alert(`WireGuard keys and configuration for interface "${deletedIface}" were successfully deleted from the device.`)
      }
    }
  } catch (e) {
    previewError.value = `Execution failed: ${e}`
  } finally {
    loading.value = false
  }
}

async function installMissing(cmd: string) {
    // Extract tool name (first word, e.g. "arp-scan" from "arp-scan localnet")
    const tool = cmd.replace(/^#.*\n/, '').trim().split(' ')[0]
    installingTool.value = true
    try {
        await api.installTool(props.nodeId, tool)
        alert(`${tool} installed successfully. You can now retry the command.`)
    } catch (e) {
        alert('Installation failed: ' + e)
    } finally {
        installingTool.value = false
    }
}

// Register sync functions so selectType can call them by key
syncFnMap.interface    = syncInterfaceForm
syncFnMap.routes       = syncRouteForm
syncFnMap.dns          = syncDnsForm
syncFnMap.nat          = syncNatForm
syncFnMap['vlan-router']  = syncVlanRouterForm
syncFnMap['vlan-switch']  = syncVlanSwitchForm
syncFnMap.wireguard    = syncWireguardForm
syncFnMap.forwarding   = syncForwardingForm
syncFnMap.service      = syncServiceForm
syncFnMap.package      = syncPackageForm
syncFnMap.user         = syncUserForm
syncFnMap.hostname     = syncHostnameForm
syncFnMap.sysctl       = syncSysctlForm
syncFnMap['file-write'] = syncFileWriteForm
syncFnMap.iptables     = syncIptablesForm
syncFnMap.ufw          = syncUfwForm
syncFnMap.nftables     = syncNftablesForm
syncFnMap['rpi-wifi']       = syncRpiWifiForm
syncFnMap['rpi-spi']        = syncRpiSpiForm
syncFnMap['rpi-i2c-enable'] = syncRpiI2cForm
syncFnMap['rpi-camera']     = syncRpiCameraForm
syncFnMap['rpi-watchdog']   = syncRpiWatchdogForm
syncFnMap.nmap              = syncNmapForm
syncFnMap.iperf3            = syncIperf3Form
syncFnMap.mtr               = syncMtrForm
syncFnMap.speedtest         = () => { inputJson.value = '{}' }
syncFnMap['dns-lookup']     = syncDnsLookupForm
syncFnMap.wol               = syncWolForm
syncFnMap['arp-scan']       = syncArpScanForm
syncFnMap['rpi-info']       = () => { inputJson.value = '{}' }
syncFnMap['rpi-temperature'] = () => { inputJson.value = '{}' }
syncFnMap['rpi-gpio-read-all'] = () => { inputJson.value = '{}' }
syncFnMap['direct-file'] = syncDirectFileForm
syncFnMap['direct-json'] = () => {
  inputJson.value = JSON_BOILERPLATES[directJsonGeneratorType.value] || '{}'
}

// Auto-update JSON as form fields change
watch(interfaceForm,   () => { if (activeType.value === 'interface')   syncInterfaceForm() },   { deep: true })
watch(() => [interfaceForm.value.vlanParent, interfaceForm.value.vlanId], ([parent, id]) => {
  if (parent && id !== undefined && id !== null && String(id).trim() !== '') {
    interfaceForm.value.interface = `${parent}.${id}`
  }
})

// Auto-populate interface IP addresses from live telemetry
watch(
  () => [interfaceForm.value.interface, detectedInterfaces.value],
  ([newVal, interfaces]) => {
    if (!newVal || !interfaces || !interfaces.length) return
    const cleanVal = String(newVal).trim()
    const found = (interfaces as DetectedInterface[]).find(i => i.name.toLowerCase() === cleanVal.toLowerCase())
    if (found) {
      const isAddressesUntouched = 
        interfaceForm.value.addresses.length === 0 || 
        (interfaceForm.value.addresses.length === 1 && !interfaceForm.value.addresses[0].trim())
      
      if (isAddressesUntouched) {
        if (found.ips && found.ips.length > 0) {
          interfaceForm.value.addresses = [...found.ips]
        } else {
          interfaceForm.value.addresses = ['']
        }
      }
    }
  },
  { deep: true }
)
watch(routeForm,       () => { if (activeType.value === 'routes')      syncRouteForm() },       { deep: true })
watch(dnsForm,         () => { if (activeType.value === 'dns')         syncDnsForm() },         { deep: true })
watch(natForm,         () => { if (activeType.value === 'nat')         syncNatForm() },         { deep: true })
watch(vlanRouterForm,  () => { if (activeType.value === 'vlan-router') syncVlanRouterForm() },  { deep: true })
watch(vlanSwitchForm,  () => { if (activeType.value === 'vlan-switch') syncVlanSwitchForm() },  { deep: true })
watch(wireguardForm,   () => { if (activeType.value === 'wireguard')   syncWireguardForm() },   { deep: true })
watch(forwardingForm,  () => { if (activeType.value === 'forwarding')  syncForwardingForm() },  { deep: true })
watch(serviceForm,     () => { if (activeType.value === 'service')     syncServiceForm() },     { deep: true })
watch(packageForm,     () => { if (activeType.value === 'package')     syncPackageForm() },     { deep: true })
watch(userForm,        () => { if (activeType.value === 'user')        syncUserForm() },        { deep: true })
watch(hostnameForm,    () => { if (activeType.value === 'hostname')    syncHostnameForm() },    { deep: true })
watch(sysctlForm,      () => { if (activeType.value === 'sysctl')      syncSysctlForm() },      { deep: true })
watch(fileWriteForm,   () => { if (activeType.value === 'file-write')  syncFileWriteForm() },   { deep: true })
watch(iptablesForm,    () => { if (activeType.value === 'iptables')    syncIptablesForm() },    { deep: true })
watch(ufwForm,         () => { if (activeType.value === 'ufw')         syncUfwForm() },         { deep: true })
watch(nftablesForm,    () => { if (activeType.value === 'nftables')    syncNftablesForm() },    { deep: true })
watch(rpiWifiForm,     () => { if (activeType.value === 'rpi-wifi')    syncRpiWifiForm() },     { deep: true })
watch(rpiSpiForm,      () => { if (activeType.value === 'rpi-spi')     syncRpiSpiForm() },      { deep: true })
watch(rpiI2cForm,      () => { if (activeType.value === 'rpi-i2c-enable') syncRpiI2cForm() },   { deep: true })
watch(rpiCameraForm,   () => { if (activeType.value === 'rpi-camera')  syncRpiCameraForm() },   { deep: true })
watch(rpiWatchdogForm, () => { if (activeType.value === 'rpi-watchdog')syncRpiWatchdogForm() }, { deep: true })
watch(nmapForm,        () => { if (activeType.value === 'nmap')        syncNmapForm() },        { deep: true })
watch(iperf3Form,      () => { if (activeType.value === 'iperf3')      syncIperf3Form() },      { deep: true })
watch(mtrForm,         () => { if (activeType.value === 'mtr')         syncMtrForm() },         { deep: true })
watch(dnsLookupForm,   () => { if (activeType.value === 'dns-lookup')  syncDnsLookupForm() },   { deep: true })
watch(wolForm,         () => { if (activeType.value === 'wol')         syncWolForm() },         { deep: true })
watch(arpScanForm,     () => { if (activeType.value === 'arp-scan')    syncArpScanForm() },     { deep: true })

watch([directFilePath, directFileContent, directFileMode, directFileBackup], () => {
  if (activeType.value === 'direct-file') syncDirectFileForm()
}, { deep: true })

watch(directJsonGeneratorType, (newType) => {
  if (activeType.value === 'direct-json') {
    inputJson.value = JSON_BOILERPLATES[newType] || '{}'
  }
})

watch(persistMode, () => { if (activeType.value && previewCommands.value.length) getPreview() })

watch(() => props.nodeId, () => {
  activeType.value      = null
  previewCommands.value = []
  previewError.value    = ''
  results.value         = []
  inputJson.value       = '{}'
  interfaceForm.value   = defaultInterfaceForm()
  routeForm.value       = defaultRouteForm()
  dnsForm.value         = defaultDnsForm()
  natForm.value         = defaultNatForm()
  vlanRouterForm.value  = defaultVlanRouterForm()
  vlanSwitchForm.value  = defaultVlanSwitchForm()
  wireguardForm.value   = defaultWireguardForm()
  forwardingForm.value  = defaultForwardingForm()
  serviceForm.value     = defaultServiceForm()
  packageForm.value     = defaultPackageForm()
  userForm.value        = defaultUserForm()
  hostnameForm.value    = defaultHostnameForm()
  sysctlForm.value      = defaultSysctlForm()
  fileWriteForm.value   = defaultFileWriteForm()
  iptablesForm.value    = defaultIptablesForm()
  ufwForm.value         = defaultUfwForm()
  nftablesForm.value    = defaultNftablesForm()
  persistMode.value     = false
  directFileContent.value = ''
  directFileBackup.value  = false
  
  // Refresh live interfaces telemetry when active node changes
  fetchLiveInterfaces()
})

// Telemetry structures
interface DetectedInterface {
  name: string
  status: 'UP' | 'DOWN' | 'UNKNOWN'
  ips: string[]
}

const detectedInterfaces = ref<DetectedInterface[]>([])
const detectingState = ref<'idle' | 'loading' | 'success' | 'error'>('idle')
const detectingError = ref('')
const liveRefExpanded = ref(true)

// --- Premium UI/UX Network Interface Features ---

// 1. Interactive Port Panel and VLAN Tree state
const collapsedTreeParents = ref<Set<string>>(new Set())

const physicalInterfaces = computed(() => {
  return detectedInterfaces.value.filter(iface => {
    const name = iface.name.toLowerCase()
    return !name.startsWith('lo') &&
           !name.startsWith('br') &&
           !name.startsWith('docker') &&
           !name.startsWith('veth') &&
           !name.startsWith('wg') &&
           !name.includes('.')
  })
})

const interfaceTree = computed(() => {
  const list = detectedInterfaces.value
  const tree: { parent: DetectedInterface; children: DetectedInterface[] }[] = []
  
  const parents = list.filter(i => !i.name.includes('.'))
  const vlans = list.filter(i => i.name.includes('.'))
  const groupedVlans = new Set<string>()
  
  for (const parent of parents) {
    const children = vlans.filter(v => {
      const parts = v.name.split('.')
      return parts[0] === parent.name
    })
    children.forEach(v => groupedVlans.add(v.name))
    tree.push({ parent, children })
  }
  
  const orphanVlans = vlans.filter(v => !groupedVlans.has(v.name))
  for (const orphan of orphanVlans) {
    tree.push({ parent: orphan, children: [] })
  }
  
  return tree
})

function selectPort(ifaceName: string) {
  if (activeType.value !== 'interface') {
    activeType.value = 'interface'
  }
  interfaceForm.value.interface = ifaceName
  syncInterfaceForm()
}

function toggleTreeParent(name: string) {
  if (collapsedTreeParents.value.has(name)) {
    collapsedTreeParents.value.delete(name)
  } else {
    collapsedTreeParents.value.add(name)
  }
}

// 2. Inline Quick-Ping Diagnostics state & methods
const pingLoading = ref<Record<string, boolean>>({})
const pingResults = ref<Record<string, { success: boolean; latency?: string; error?: string }>>({})

async function triggerInlinePing(ifaceName: string, ip: string) {
  const key = `${ifaceName}-${ip}`
  pingLoading.value[key] = true
  delete pingResults.value[key]
  
  const cleanIp = ip.split('/')[0]
  const cmd = `ping -c 2 -W 2 -I ${cleanIp} 8.8.8.8`
  
  try {
    const res = await api.executeNode(props.nodeId, [cmd])
    const result = res.results[0]
    const stdout = result.output || ''
    const stderr = result.error || ''
    
    if (result.error || stderr.toLowerCase().includes('fail') || stderr.toLowerCase().includes('error')) {
      pingResults.value[key] = { success: false, error: 'FAIL' }
    } else {
      const match = stdout.match(/(?:rtt|round-trip)\s+min\/avg\/max(?:\/mdev)?\s+=\s+[\d\.]+\/([\d\.]+)\//i)
      if (match && match[1]) {
        pingResults.value[key] = { success: true, latency: `${parseFloat(match[1]).toFixed(1)}ms` }
      } else {
        const avgMatch = stdout.match(/avg\s+=\s+([\d\.]+)/i)
        if (avgMatch && avgMatch[1]) {
          pingResults.value[key] = { success: true, latency: `${parseFloat(avgMatch[1]).toFixed(1)}ms` }
        } else {
          pingResults.value[key] = { success: false, error: 'FAIL' }
        }
      }
    }
  } catch (err) {
    pingResults.value[key] = { success: false, error: 'FAIL' }
  } finally {
    pingLoading.value[key] = false
  }
}

// 3. Real-time CIDR Subnet Assistant calculations
interface SubnetInfo {
  ip: string
  cidr: number
  netmask: string
  network: string
  broadcast: string
}

function longToIp(long: number): string {
  return [
    (long >>> 24) & 255,
    (long >>> 16) & 255,
    (long >>> 8) & 255,
    long & 255
  ].join('.')
}

function calculateSubnet(ipWithCidr: string): SubnetInfo | null {
  if (!ipWithCidr || !ipWithCidr.includes('/')) return null
  const [ipPart, cidrPart] = ipWithCidr.split('/')
  const cidr = parseInt(cidrPart, 10)
  if (isNaN(cidr) || cidr < 0 || cidr > 32) return null
  
  const ipReg = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/
  const match = ipPart.match(ipReg)
  if (!match) return null
  
  const octets = match.slice(1, 5).map(Number)
  if (octets.some(o => o > 255)) return null
  
  const ipLong = ((octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]) >>> 0
  const maskLong = cidr === 0 ? 0 : (0xFFFFFFFF << (32 - cidr)) >>> 0
  const netmask = longToIp(maskLong)
  
  const netLong = (ipLong & maskLong) >>> 0
  const network = longToIp(netLong)
  
  const broadLong = (netLong | ~maskLong) >>> 0
  const broadcast = longToIp(broadLong)
  
  return {
    ip: ipPart,
    cidr,
    netmask,
    network,
    broadcast
  }
}

// --- End of Premium UI/UX Network Interface Features ---

// Toast notifications for premium clipboard interaction
const showToast = ref(false)
const lastCopied = ref('')
let toastTimeout: any = null

function triggerToast(text: string) {
  lastCopied.value = text
  showToast.value = true
  if (toastTimeout) clearTimeout(toastTimeout)
  toastTimeout = setTimeout(() => {
    showToast.value = false
  }, 2000)
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    triggerToast(text)
  }).catch(err => {
    console.error('Failed to copy text: ', err)
  })
}

async function fetchLiveInterfaces() {
  if (!props.nodeId) return
  detectingState.value = 'loading'
  detectingError.value = ''
  try {
    const data = await api.readNode(props.nodeId, 'ip')
    
    // Check if there was any error in results
    const errResult = data.results?.find(r => r.error)
    if (errResult) {
      detectingError.value = errResult.error || 'Connection or command error.'
      detectingState.value = 'error'
      return
    }
    if (!data.results || data.results.length === 0) {
      detectingError.value = 'No telemetry data returned from node.'
      detectingState.value = 'error'
      return
    }

    const rawStdout = data.results.map(r => r.output || '').join('\n\n').trim()
    detectedInterfaces.value = parseIpAddr(rawStdout)
    detectingState.value = 'success'
  } catch (err: any) {
    detectingError.value = String(err.message || err)
    detectingState.value = 'error'
  }
}


function parseIpAddr(stdout: string): DetectedInterface[] {
  const interfaces: DetectedInterface[] = []
  let currentIface: DetectedInterface | null = null

  const lines = stdout.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    
    // Match interface start line: e.g. "2: eth0: <BROADCAST,..." or "3: eth0.100@eth0: <..."
    const ifaceMatch = trimmed.match(/^\d+:\s+([^:@]+)(?:@[^\s:]+)?:\s+<([^>]+)>/)
    if (ifaceMatch) {
      if (currentIface) {
        interfaces.push(currentIface)
      }
      const name = ifaceMatch[1]
      const flags = ifaceMatch[2]
      let status: 'UP' | 'DOWN' | 'UNKNOWN' = 'UNKNOWN'
      const stateMatch = trimmed.match(/state\s+(UP|DOWN|UNKNOWN)/i)
      if (stateMatch) {
        status = stateMatch[1].toUpperCase() as any
      }
      if (status === 'UNKNOWN' && (flags.includes('UP') || flags.includes('LOWER_UP'))) {
        status = 'UP'
      }

      currentIface = {
        name,
        status,
        ips: []
      }
      continue
    }

    if (currentIface) {
      const ipMatch = trimmed.match(/^inet\s+([0-9a-fA-F\.\/:]+)/)
      if (ipMatch) {
        currentIface.ips.push(ipMatch[1])
      } else {
        const ip6Match = trimmed.match(/^inet6\s+([0-9a-fA-F\.\/:]+)/)
        if (ip6Match) {
          currentIface.ips.push(ip6Match[1])
        }
      }
    }
  }

  if (currentIface) {
    interfaces.push(currentIface)
  }

  return interfaces
}

// 4. Real-time Cyberpunk Network Traffic Monitor & Animated Sparklines
interface InterfaceTraffic {
  rxRate: number      // Current RX rate in Bytes/sec
  txRate: number      // Current TX rate in Bytes/sec
  rxHistory: number[] // Last 10 data points for RX rate
  txHistory: number[] // Last 10 data points for TX rate
  lastRxBytes: number
  lastTxBytes: number
  lastTime: number
}

const liveMonitorActive = ref(false)
const interfaceTrafficData = ref<Record<string, InterfaceTraffic>>({})
let monitorInterval: any = null

function parseIpLinkStats(stdout: string): Record<string, { rxBytes: number; txBytes: number }> {
  const stats: Record<string, { rxBytes: number; txBytes: number }> = {}
  const lines = stdout.split('\n')
  
  let currentIface = ''
  let expectingRx = false
  let expectingTx = false
  
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    
    // Match interface start line, e.g. "2: eth0: <BROADCAST..." or "3: eth0.100@eth0: <..."
    const ifaceMatch = trimmed.match(/^\d+:\s+([^:@]+)(?:@[^\s:]+)?:\s+<([^>]+)>/)
    if (ifaceMatch) {
      currentIface = ifaceMatch[1]
      expectingRx = false
      expectingTx = false
      continue
    }
    
    if (!currentIface) continue
    
    if (trimmed.startsWith('RX:')) {
      expectingRx = true
      expectingTx = false
      continue
    }
    
    if (trimmed.startsWith('TX:')) {
      expectingTx = true
      expectingRx = false
      continue
    }
    
    if (expectingRx) {
      const tokens = trimmed.split(/\s+/)
      if (tokens.length >= 1) {
        const bytes = parseInt(tokens[0], 10)
        if (!isNaN(bytes)) {
          if (!stats[currentIface]) stats[currentIface] = { rxBytes: 0, txBytes: 0 }
          stats[currentIface].rxBytes = bytes
        }
      }
      expectingRx = false
    } else if (expectingTx) {
      const tokens = trimmed.split(/\s+/)
      if (tokens.length >= 1) {
        const bytes = parseInt(tokens[0], 10)
        if (!isNaN(bytes)) {
          if (!stats[currentIface]) stats[currentIface] = { rxBytes: 0, txBytes: 0 }
          stats[currentIface].txBytes = bytes
        }
      }
      expectingTx = false
    }
  }
  
  return stats
}

async function pollTrafficStats() {
  if (!props.nodeId || !liveMonitorActive.value) return
  
  try {
    const data = await api.readNode(props.nodeId, 'if-stats')
    const stdout = data.results.map(r => r.output || '').join('\n')
    
    const parsedStats = parseIpLinkStats(stdout)
    const now = Date.now()
    
    for (const [ifaceName, stats] of Object.entries(parsedStats)) {
      if (!interfaceTrafficData.value[ifaceName]) {
        interfaceTrafficData.value[ifaceName] = {
          rxRate: 0,
          txRate: 0,
          rxHistory: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          txHistory: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          lastRxBytes: stats.rxBytes,
          lastTxBytes: stats.txBytes,
          lastTime: now
        }
      } else {
        const entry = interfaceTrafficData.value[ifaceName]
        const elapsed = (now - entry.lastTime) / 1000
        
        if (elapsed > 0) {
          const rxDiff = stats.rxBytes - entry.lastRxBytes
          const txDiff = stats.txBytes - entry.lastTxBytes
          
          const rxRate = rxDiff >= 0 ? rxDiff / elapsed : 0
          const txRate = txDiff >= 0 ? txDiff / elapsed : 0
          
          entry.rxRate = rxRate
          entry.txRate = txRate
          
          entry.rxHistory.push(rxRate)
          if (entry.rxHistory.length > 10) entry.rxHistory.shift()
          
          entry.txHistory.push(txRate)
          if (entry.txHistory.length > 10) entry.txHistory.shift()
          
          entry.lastRxBytes = stats.rxBytes
          entry.lastTxBytes = stats.txBytes
          entry.lastTime = now
        }
      }
    }
  } catch (err) {
    console.error('Failed to poll traffic statistics:', err)
  }
}

function startLiveMonitor() {
  stopLiveMonitor()
  pollTrafficStats()
  monitorInterval = setInterval(pollTrafficStats, 3000)
}

function stopLiveMonitor() {
  if (monitorInterval) {
    clearInterval(monitorInterval)
    monitorInterval = null
  }
}

function toggleLiveMonitor() {
  liveMonitorActive.value = !liveMonitorActive.value
  if (liveMonitorActive.value) {
    startLiveMonitor()
  } else {
    stopLiveMonitor()
  }
}

function formatRate(bytesPerSec: number): string {
  if (bytesPerSec === 0) return '0 B/s'
  const k = 1024
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  const i = Math.floor(Math.log(bytesPerSec) / Math.log(k))
  return `${(bytesPerSec / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

function getSparklinePath(history: number[] | undefined): string {
  if (!history || history.length < 2) return 'M 0 14 L 60 14'
  const maxVal = Math.max(...history, 1024) // base scale at 1KB/s
  return history.map((val, idx) => {
    const x = (idx / (history.length - 1)) * 60
    const y = 14 - (Math.min(val, maxVal) / maxVal) * 12
    return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}

// Watch nodeId changes to clean up or restart the monitor
watch(() => props.nodeId, () => {
  interfaceTrafficData.value = {}
  if (liveMonitorActive.value) {
    startLiveMonitor()
  } else {
    stopLiveMonitor()
  }
})

onUnmounted(() => {
  stopLiveMonitor()
})

// Initial fetch on mount
fetchLiveInterfaces()
</script>

<style scoped>
/* --- Premium RJ45 Front Panel Styles --- */
.rj45-panel {
  background: rgba(13, 20, 38, 0.9);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px;
  margin-bottom: 16px;
  box-shadow: inset 0 0 15px rgba(0, 229, 255, 0.05);
}
.rj45-panel-title {
  font-size: 10px;
  font-weight: 700;
  color: var(--text);
  font-family: var(--font-hd);
  letter-spacing: 0.12em;
  margin-bottom: 12px;
  opacity: 0.75;
}
.rj45-ports-container {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.rj45-port {
  position: relative;
  width: 72px;
  height: 60px;
  background: #060913;
  border: 2px solid #202b46;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding-bottom: 4px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}
.rj45-port::before {
  content: '';
  position: absolute;
  top: 10px;
  width: 48px;
  height: 26px;
  background: #111827;
  border: 1px solid #273556;
  border-radius: 2px;
  box-shadow: inset 0 2px 5px rgba(0,0,0,0.8);
}
.rj45-clip {
  position: absolute;
  top: 22px;
  width: 20px;
  height: 12px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 1px;
  z-index: 2;
}
.rj45-pins {
  position: absolute;
  top: 12px;
  display: flex;
  gap: 2px;
  z-index: 1;
}
.rj45-pin {
  width: 2px;
  height: 8px;
  background: #fbbf24; /* Golden pins */
  opacity: 0.85;
}
.rj45-led-indicator {
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
.rj45-port.port-up {
  border-color: rgba(16, 185, 129, 0.4);
}
.rj45-port.port-up .rj45-led-indicator {
  background: #10b981;
  box-shadow: 0 0 8px #10b981, 0 0 15px rgba(16, 185, 129, 0.6);
  animation: led-blink 1.5s infinite alternate;
}
.rj45-port.port-down {
  border-color: rgba(249, 115, 22, 0.4);
}
.rj45-port.port-down .rj45-led-indicator {
  background: #f97316;
  box-shadow: 0 0 6px #f97316;
}
.rj45-port:hover {
  border-color: var(--cyan);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 229, 255, 0.15);
}
.rj45-port:hover::before {
  border-color: var(--cyan);
}
.rj45-label {
  font-size: 9px;
  font-weight: 600;
  color: var(--textbr);
  font-family: var(--font-hd);
  z-index: 3;
  margin-top: 18px;
}
@keyframes led-blink {
  0% { opacity: 0.6; }
  100% { opacity: 1; }
}

/* --- VLAN/Interfaces Tree Hierarchy Styles --- */
.live-ref-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.live-ref-tree {
  background: rgba(10, 16, 32, 0.4);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px;
}
.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  font-weight: 700;
  color: var(--text);
  font-family: var(--font-hd);
  letter-spacing: 0.12em;
  margin-bottom: 12px;
  opacity: 0.75;
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
  padding-bottom: 6px;
}

/* --- Premium Live Monitor and Traffic Sparklines --- */
.btn-live-monitor {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 9px;
  font-weight: bold;
  color: var(--cyan);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: var(--font-mono, monospace);
  line-height: 1;
}
.btn-live-monitor:hover {
  background: rgba(0, 229, 255, 0.15);
  border-color: var(--cyan);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}
.btn-live-monitor.monitor-active {
  background: rgba(16, 185, 129, 0.12);
  border-color: #10b981;
  color: #10b981;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.2);
}
.monitor-dot {
  width: 6px;
  height: 6px;
  background-color: currentColor;
  border-radius: 50%;
  transition: all 0.2s ease;
}
.btn-live-monitor.monitor-active .monitor-dot {
  animation: monitor-pulse-green 1.5s infinite;
}

@keyframes monitor-pulse-green {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.tree-traffic {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 12px;
  margin-right: 12px;
  animation: fade-in-scale 0.25s ease-out;
}
.traffic-rates {
  display: flex;
  flex-direction: column;
  font-family: var(--font-mono, monospace);
  font-size: 8.5px;
  line-height: 1.2;
  text-align: right;
  min-width: 60px;
}
.rate-down {
  color: #00e5ff;
  text-shadow: 0 0 4px rgba(0, 229, 255, 0.25);
}
.rate-up {
  color: #f43f5e;
  text-shadow: 0 0 4px rgba(244, 63, 94, 0.25);
}
.traffic-sparkline {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: visible;
  padding: 0;
}
.sparkpath-rx {
  fill: none;
  stroke: #00e5ff;
  stroke-width: 1.25;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0px 0px 2px rgba(0, 229, 255, 0.5));
  transition: d 0.3s ease;
}
.sparkpath-tx {
  fill: none;
  stroke: #f43f5e;
  stroke-width: 1.25;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0px 0px 2px rgba(244, 63, 94, 0.5));
  transition: d 0.3s ease;
}

.tree-traffic-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 8.5px;
  font-family: var(--font-mono, monospace);
  color: rgba(0, 229, 255, 0.4);
  margin-left: 12px;
  margin-right: 12px;
  animation: fade-in-scale 0.25s ease-out;
}
.traffic-dot-pulse {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: var(--cyan);
  animation: traffic-pulse 1s infinite alternate;
}
@keyframes traffic-pulse {
  0% { opacity: 0.3; transform: scale(0.8); }
  100% { opacity: 1; transform: scale(1.2); }
}
@keyframes fade-in-scale {
  0% { opacity: 0; transform: scale(0.95); }
  100% { opacity: 1; transform: scale(1); }
}
.tree-node {
  margin-bottom: 8px;
}
.tree-parent-row, .tree-child-row {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255,255,255,0.03);
  border-radius: 4px;
  margin-bottom: 2px;
  transition: all 0.15s ease;
}
.tree-parent-row:hover, .tree-child-row:hover {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(0, 229, 255, 0.15);
}
.tree-toggle {
  width: 20px;
  cursor: pointer;
  color: var(--cyan);
  font-size: 10px;
  display: flex;
  align-items: center;
  user-select: none;
}
.tree-bullet {
  color: var(--text);
  opacity: 0.35;
}
.tree-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
}
.tree-branch {
  font-family: monospace;
  color: rgba(0, 229, 255, 0.35);
  margin-right: 8px;
  font-size: 12px;
  letter-spacing: -1px;
}
.tree-children {
  padding-left: 20px;
  margin-top: 2px;
}
.tree-ips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex-grow: 1;
  justify-content: flex-end;
}
.ref-ip-badge-container {
  display: inline-flex;
  align-items: center;
  background: rgba(0, 229, 255, 0.04);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 4px;
  padding: 2px 2px 2px 6px;
  transition: all 0.2s;
}
.ref-ip-badge-container:hover {
  border-color: rgba(0, 229, 255, 0.3);
  background: rgba(0, 229, 255, 0.08);
}
.ref-ip-badge-container .ref-ip-badge {
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  font-size: 11px;
}
.btn-quick-ping {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--cyan);
  font-size: 10px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.65;
  transition: all 0.2s;
  height: 14px;
  width: 14px;
  margin-left: 4px;
}
.btn-quick-ping:hover {
  opacity: 1;
  transform: scale(1.2);
}
.btn-quick-ping:disabled {
  cursor: not-allowed;
}
.ping-spinner {
  width: 8px;
  height: 8px;
  border: 1px solid var(--cyan);
  border-top-color: transparent;
  border-radius: 50%;
  animation: ping-spin 0.6s linear infinite;
}
@keyframes ping-spin {
  to { transform: rotate(360deg); }
}
.ping-latency-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 2px;
  margin-left: 6px;
  font-family: monospace;
}
.ping-latency-badge.ping-success {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
  text-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
}
.ping-latency-badge.ping-fail {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  text-shadow: 0 0 6px rgba(239, 68, 68, 0.4);
}

/* --- Subnet Assistant Styles --- */
.static-addr-row {
  margin-bottom: 12px;
  background: rgba(13, 20, 38, 0.3);
  border: 1px solid rgba(255,255,255,0.02);
  border-radius: 6px;
  padding: 8px 8px 10px 8px;
}
.static-addr-row .form-row {
  margin-bottom: 0;
}
.subnet-assistant-card {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(0, 229, 255, 0.08);
}
.subnet-stat {
  display: flex;
  flex-direction: column;
  background: rgba(6, 9, 19, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  padding: 4px 8px;
}
.subnet-stat .label {
  font-size: 8px;
  text-transform: uppercase;
  color: var(--text);
  opacity: 0.6;
  font-family: var(--font-hd);
  letter-spacing: 0.08em;
  margin-bottom: 2px;
}
.subnet-stat .value {
  font-size: 11px;
  font-weight: 600;
  font-family: monospace;
}
.cyan-glow {
  color: var(--cyan);
  text-shadow: 0 0 6px rgba(0, 229, 255, 0.3);
}
.yellow-glow {
  color: var(--yellow);
  text-shadow: 0 0 6px rgba(255, 190, 11, 0.3);
}
.pink-glow {
  color: var(--pink);
  text-shadow: 0 0 6px rgba(255, 45, 110, 0.3);
}

.config-panel { display: flex; height: 100%; overflow: hidden; background: var(--bg2); }
.config-sidebar {
  width: 200px; min-width: 200px; overflow-y: auto;
  border-right: 1px solid var(--border); padding: 12px 0;
  background: rgba(8, 13, 24, 0.5);
  backdrop-filter: blur(10px);
}
.cat-group { margin-bottom: 12px; }
.cat-label {
  padding: 8px 16px; font-size: 11px; font-weight: 700;
  color: var(--text); text-transform: uppercase;
  font-family: var(--font-hd); letter-spacing: .08em;
  cursor: pointer; display: flex; justify-content: space-between; align-items: center;
  user-select: none; transition: color .2s;
}
.cat-label:hover { color: var(--cyan); text-shadow: 0 0 8px rgba(0, 229, 255, 0.4); }
.cat-chevron { font-size: 10px; transition: transform .3s; }
.cat-chevron.collapsed { transform: rotate(180deg); }
.cat-items { padding: 4px 8px; }
.type-btn {
  display: block; width: 100%; padding: 6px 16px; text-align: left;
  background: none; border: none; color: var(--textbr);
  font-size: 12px; cursor: pointer; border-radius: 4px;
  margin-bottom: 2px; transition: all .2s;
  font-family: var(--font-ui);
}
.type-btn:hover { background: rgba(0, 229, 255, 0.05); color: var(--cyan); }
.type-btn.active { 
  background: rgba(0, 229, 255, 0.1); 
  color: var(--cyan); 
  border-left: 2px solid var(--cyan);
  box-shadow: inset 2px 0 8px rgba(0, 229, 255, 0.05);
}

.config-main { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.placeholder { 
  color: var(--text); 
  font-size: 14px; 
  padding: 32px; 
  font-family: var(--font-hd);
  letter-spacing: 1px;
}
.config-editor { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.editor-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; border-bottom: 1px solid var(--border);
  background: var(--bg3);
}
.type-name { 
  font-size: 14px; font-weight: 700; color: var(--cyan); 
  font-family: var(--font-hd); letter-spacing: 1px;
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
}
.header-actions { display: flex; gap: 8px; }
.btn-preview, .btn-apply, .btn-clear-form {
  padding: 5px 12px; font-size: 11px; border-radius: 4px;
  cursor: pointer; border: 1px solid var(--border);
  font-family: var(--font-ui); transition: all 0.2s;
}
.btn-preview { 
  background: var(--bg4); color: var(--textbr); 
}
.btn-preview:hover {
  background: var(--border); color: var(--cyan); border-color: var(--cyan);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.1);
}
.btn-clear-form { 
  background: var(--bg4); color: var(--text); 
}
.btn-clear-form:hover { 
  color: var(--pink); border-color: var(--pink); 
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.1);
}
.btn-apply { 
  background: var(--green); color: var(--bg); border-color: var(--green);
  font-family: var(--font-hd); font-weight: 600; letter-spacing: 0.5px;
}
.btn-apply:hover:not(:disabled) { 
  box-shadow: var(--shadow-g); 
}
.btn-apply:disabled { opacity: 0.4; cursor: not-allowed; }
.persist-toggle {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--text); cursor: pointer;
  padding: 4px 10px; border: 1px solid var(--border); border-radius: 4px;
  background: var(--bg); user-select: none; transition: all 0.2s;
  font-family: var(--font-ui);
}
.persist-toggle:has(input:checked) { 
  color: var(--yellow); border-color: var(--yellow); 
  background: rgba(255, 190, 11, 0.05); 
  box-shadow: 0 0 10px rgba(255, 190, 11, 0.1);
}
.persist-toggle input { margin: 0; cursor: pointer; }

/* Cyber-Guide Styling */
.cyber-guide {
  background: rgba(8, 13, 24, 0.6);
  border: 1px dashed var(--cyan);
  border-radius: var(--r);
  padding: 10px 14px;
  margin-bottom: 8px;
  box-shadow: inset 0 0 12px rgba(0, 229, 255, 0.03);
}
.guide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.guide-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.guide-icon {
  color: var(--cyan);
  text-shadow: 0 0 8px var(--cyan);
  animation: pulse-guide 1.5s infinite alternate;
}
@keyframes pulse-guide {
  from { opacity: 0.6; }
  to { opacity: 1; }
}
.guide-text {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  color: var(--textwh);
  letter-spacing: 0.5px;
}
.guide-chevron {
  font-size: 10px;
  color: var(--text);
}
.guide-content {
  margin-top: 10px;
  border-top: 1px solid rgba(0, 229, 255, 0.1);
  padding-top: 10px;
}
.guide-desc {
  font-size: 12px;
  color: var(--textbr);
  margin-bottom: 12px;
  line-height: 1.5;
}
.guide-grid {
  display: flex;
  gap: 20px;
}
.guide-column {
  flex: 1;
}
.column-title {
  font-family: var(--font-hd);
  font-size: 10px;
  color: var(--cyan);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.guide-column ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.guide-column li {
  font-size: 11px;
  color: var(--text);
  margin-bottom: 4px;
  line-height: 1.4;
  position: relative;
  padding-left: 12px;
}
.guide-column li::before {
  content: '▸';
  position: absolute;
  left: 0;
  color: var(--cyan);
}
.guide-column li code {
  background: var(--bg);
  color: var(--yellow);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: var(--font-co);
}

.specialized-form {
  background: var(--bg3); padding: 16px; border-radius: var(--r2);
  border: 1px solid var(--border); margin-bottom: 8px;
}
.form-row { display: flex; gap: 12px; margin-bottom: 12px; }
.form-row label { flex: 1; display: flex; flex-direction: column; gap: 6px; font-size: 11px; color: var(--text); }
.form-row input, .form-row select {
  background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
  color: var(--textwh); padding: 6px 10px; font-size: 12px; outline: none;
  transition: all 0.2s;
}
.form-row input:focus, .form-row select:focus {
  border-color: var(--cyan);
  box-shadow: var(--shadow-c);
}
.btn-sync {
  width: 100%; padding: 6px; font-size: 11px; background: var(--bg4);
  border: 1px solid var(--border); border-radius: 4px; color: var(--textbr); cursor: pointer;
  font-family: var(--font-ui); transition: all 0.2s;
}
.btn-sync:hover { background: var(--border); color: var(--cyan); border-color: var(--cyan); }

.section-label-sub {
  font-size: 10px; font-weight: 700; color: var(--text);
  text-transform: uppercase; margin: 16px 0 8px;
  border-bottom: 1px solid var(--border); padding-bottom: 4px;
  font-family: var(--font-hd); letter-spacing: 0.5px;
}
.warning-box {
  background: rgba(255, 190, 11, 0.05); border: 1px solid var(--yellow); border-radius: 6px;
  padding: 10px 14px; color: var(--yellow); font-size: 12px; margin-bottom: 12px;
  box-shadow: 0 0 10px rgba(255, 190, 11, 0.05);
}

.multi-row { align-items: flex-end; border-bottom: 1px dashed var(--border); padding-bottom: 12px; }
.btn-remove {
  background: none; border: none; color: var(--pink); cursor: pointer;
  padding: 6px; font-size: 14px; margin-bottom: 2px; transition: color 0.15s;
}
.btn-remove:hover { color: #ff5e97; }
.form-actions { display: flex; align-items: center; gap: 16px; margin-top: 12px; }
.btn-add-sub {
  background: var(--bg4); border: 1px solid var(--border); color: var(--textbr);
  padding: 5px 12px; border-radius: 4px; font-size: 11px; cursor: pointer;
  transition: all 0.2s; font-family: var(--font-ui);
}
.btn-add-sub:hover { background: var(--border); color: var(--cyan); border-color: var(--cyan); }
.check-label { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--textbr); cursor: pointer; flex: 1; user-select: none; }
.fw-rule {
  background: var(--bg); border: 1px solid var(--border); border-radius: var(--r);
  padding: 10px 12px; margin-bottom: 10px;
}
.fw-rule .form-row { margin-bottom: 8px; }
.fw-rule .form-row:last-child { margin-bottom: 0; }
.hint { font-size: 11px; color: var(--text); margin-top: 6px; font-style: italic; }

.editor-body { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 20px; }
.section-label { 
  font-size: 11px; font-weight: 700; color: var(--textbr); 
  text-transform: uppercase; margin-bottom: 8px; 
  display: flex; justify-content: space-between; align-items: center;
  font-family: var(--font-hd); letter-spacing: 0.5px;
}
.btn-clear-results {
  background: var(--bg4); border: 1px solid var(--border); color: var(--text);
  font-size: 10px; padding: 2px 8px; border-radius: 3px; cursor: pointer;
  transition: all 0.2s; font-family: var(--font-ui);
}
.btn-clear-results:hover { color: var(--pink); border-color: var(--pink); box-shadow: 0 0 8px rgba(255, 45, 110, 0.1); }
.auto-label { font-weight: 400; text-transform: none; color: var(--text); }
.json-textarea {
  width: 100%; height: 120px; background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; color: var(--textwh); font-family: var(--font-co); font-size: 12px;
  padding: 10px; resize: vertical; outline: none; transition: border-color 0.2s;
}
.json-textarea:focus { border-color: var(--cyan); box-shadow: var(--shadow-c); }

.preview-pre {
  background: var(--bg); padding: 14px; border-radius: var(--r);
  font-family: var(--font-co); font-size: 12px; color: var(--textbr);
  white-space: pre-wrap; margin: 0; border: 1px solid var(--border);
  line-height: 1.5;
  max-height: 250px;
  overflow-y: auto;
  padding-right: 6px;
}

/* Shell highlighter styles */
:deep(.shell-str) { color: var(--yellow); }
:deep(.shell-heredoc) { color: var(--pink); font-weight: 600; text-shadow: 0 0 6px rgba(255, 45, 110, 0.3); }
:deep(.shell-cmd) { color: var(--cyan); font-weight: 600; text-shadow: 0 0 4px rgba(0, 229, 255, 0.3); }
:deep(.shell-ip) { color: var(--green); }
:deep(.shell-comment) { color: var(--text); font-style: italic; }

.preview-error { color: var(--pink); font-size: 12px; margin-bottom: 8px; }

/* Premium Terminal Result Cards */
.result-card {
  border-radius: var(--r);
  border: 1px solid var(--border);
  background: var(--bg);
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  transition: all 0.25s ease;
}
.result-card.card-ok {
  border-left: 3px solid var(--green);
}
.result-card.card-err {
  border-left: 3px solid var(--pink);
}
.result-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--bg3);
  cursor: pointer;
  user-select: none;
  gap: 12px;
}
.result-card-header:hover {
  background: rgba(24, 33, 53, 0.4);
}
.result-status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.card-ok .status-dot {
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
}
.card-err .status-dot {
  background: var(--pink);
  box-shadow: 0 0 8px var(--pink);
}
.status-label {
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.card-ok .status-label { color: var(--green); }
.card-err .status-label { color: var(--pink); }

.result-cmd-preview {
  flex: 1;
  font-family: var(--font-co);
  font-size: 11px;
  color: var(--textwh);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.85;
}
.card-chevron {
  font-size: 10px;
  color: var(--text);
}
.result-card-body {
  padding: 12px;
  border-top: 1px solid var(--border);
  background: var(--bg2);
}
.result-out, .result-err {
  padding: 10px 12px; font-family: var(--font-co); font-size: 11px;
  border-radius: 4px; white-space: pre-wrap; margin: 0; line-height: 1.5;
  max-height: 250px;
  overflow-y: auto;
  padding-right: 6px;
}
.result-out { background: var(--bg); color: var(--textbr); border: 1px solid var(--border); }
.result-err { background: rgba(255, 45, 110, 0.05); color: var(--pink); border: 1px solid rgba(255, 45, 110, 0.15); margin-top: 8px; }

.result-fix { 
  margin-top: 12px; 
  padding: 10px 14px; 
  background: rgba(255, 45, 110, 0.03); 
  border: 1px dashed var(--pink); 
  border-radius: var(--r); 
}
.fix-alert {
  font-size: 11px;
  color: var(--pink);
  margin-bottom: 8px;
  font-family: var(--font-hd);
  letter-spacing: 0.5px;
}
.btn-fix-inline {
    padding: 6px 14px; background: none; border: 1px solid var(--green);
    color: var(--green); border-radius: 4px; font-size: 10px;
    font-family: var(--font-hd); cursor: pointer; transition: all 0.2s;
    letter-spacing: 0.5px;
}
.btn-fix-inline:hover:not(:disabled) { background: var(--green); color: var(--bg); box-shadow: var(--shadow-g); }
.btn-fix-inline:disabled { opacity: 0.5; cursor: wait; }

/* Transitions */
.list-enter-active,
.list-leave-active {
  transition: all 0.25s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-15px);
}

/* Live Telemetry Reference Panel */
.live-ref-panel {
  background: rgba(8, 13, 24, 0.45);
  border: 1px solid var(--border);
  border-radius: var(--r);
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  transition: all 0.25s ease;
}
.live-ref-panel:hover {
  border-color: rgba(0, 229, 255, 0.35);
  box-shadow: 0 4px 24px rgba(0, 229, 255, 0.05);
}
.live-ref-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: rgba(16, 26, 44, 0.6);
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}
.live-ref-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.live-ref-icon {
  font-size: 14px;
  transition: transform 0.3s ease;
}
.live-ref-icon.spinning {
  display: inline-block;
  animation: spin-ref 1.5s linear infinite;
}
@keyframes spin-ref {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.live-ref-text {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  color: var(--textwh);
  letter-spacing: 0.8px;
}
.live-ref-status-badge {
  font-size: 9px;
  font-family: var(--font-hd);
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}
.live-ref-status-badge.scanning {
  background: rgba(255, 190, 11, 0.1);
  color: var(--yellow);
  border: 1px solid rgba(255, 190, 11, 0.25);
  box-shadow: 0 0 8px rgba(255, 190, 11, 0.08);
}
.live-ref-status-badge.connected {
  background: rgba(0, 229, 255, 0.1);
  color: var(--cyan);
  border: 1px solid rgba(0, 229, 255, 0.25);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.08);
}
.live-ref-status-badge.offline {
  background: rgba(255, 45, 110, 0.1);
  color: var(--pink);
  border: 1px solid rgba(255, 45, 110, 0.25);
  box-shadow: 0 0 8px rgba(255, 45, 110, 0.08);
}
.live-ref-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn-ref-refresh {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.btn-ref-refresh:hover {
  background: rgba(255, 255, 255, 0.05);
  transform: rotate(45deg);
}
.live-ref-content {
  padding: 14px;
  background: rgba(8, 13, 24, 0.2);
  max-height: 480px;
  overflow-y: auto;
  padding-right: 6px;
}
.live-ref-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px 0;
  color: var(--textbr);
  font-size: 12px;
  font-family: var(--font-ui);
}
.cyber-pulse-loader {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 10px var(--cyan);
  animation: pulse-loader 1s ease-in-out infinite alternate;
}
@keyframes pulse-loader {
  from { transform: scale(0.6); opacity: 0.4; }
  to { transform: scale(1.1); opacity: 1; }
}
.live-ref-error {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 45, 110, 0.04);
  border: 1px dashed rgba(255, 45, 110, 0.25);
  border-radius: 4px;
}
.err-icon {
  font-size: 20px;
}
.err-details {
  flex: 1;
}
.err-title {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  color: var(--pink);
  margin-bottom: 2px;
}
.err-msg {
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--textbr);
  word-break: break-all;
}
.btn-ref-retry {
  padding: 5px 12px;
  background: rgba(255, 45, 110, 0.1);
  border: 1px solid var(--pink);
  color: var(--pink);
  border-radius: 4px;
  font-size: 10px;
  font-family: var(--font-hd);
  cursor: pointer;
  transition: all 0.2s;
}
.btn-ref-retry:hover {
  background: var(--pink);
  color: var(--bg);
  box-shadow: 0 0 12px rgba(255, 45, 110, 0.3);
}
.live-ref-empty {
  text-align: center;
  padding: 16px 0;
  color: var(--textbr);
  font-size: 12px;
  font-family: var(--font-ui);
}
.live-ref-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}
.live-ref-card {
  background: rgba(16, 26, 44, 0.4);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.2s;
}
.live-ref-card:hover {
  background: rgba(16, 26, 44, 0.7);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
}
.live-ref-card.iface-up {
  border-left: 2px solid var(--green);
}
.live-ref-card.iface-down {
  border-left: 2px solid var(--pink);
}
.ref-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ref-iface-name {
  font-family: var(--font-hd);
  font-size: 12px;
  font-weight: 700;
  color: var(--textwh);
  cursor: pointer;
  transition: color 0.15s;
}
.ref-iface-name:hover {
  color: var(--cyan);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
}
.ref-iface-status {
  font-size: 8px;
  font-family: var(--font-hd);
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 2px;
}
.ref-iface-status.up {
  background: rgba(106, 190, 48, 0.15);
  color: var(--green);
}
.ref-iface-status.down {
  background: rgba(255, 45, 110, 0.15);
  color: var(--pink);
}
.ref-iface-status.unknown {
  background: rgba(255, 255, 255, 0.05);
  color: var(--textbr);
}
.ref-card-ips {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.ref-no-ips {
  font-size: 10px;
  color: var(--text);
  font-style: italic;
}
.ref-ip-badge {
  background: rgba(0, 229, 255, 0.04);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 3px;
  padding: 2px 6px;
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--cyan);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  max-width: 100%;
}
.ref-ip-badge:hover {
  background: rgba(0, 229, 255, 0.15);
  border-color: var(--cyan);
  color: var(--textwh);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}
.live-ref-footer {
  font-size: 10px;
  color: var(--text);
  border-top: 1px solid rgba(255, 255, 255, 0.03);
  padding-top: 8px;
  margin-top: 8px;
}
.tip-highlight {
  color: var(--cyan);
  font-weight: 600;
}

/* Glowing Cyber Toast Notification */
.cyber-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  background: rgba(8, 13, 24, 0.9);
  border: 1px solid var(--green);
  box-shadow: 0 0 20px rgba(106, 190, 48, 0.25), inset 0 0 10px rgba(106, 190, 48, 0.1);
  border-radius: 4px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  backdrop-filter: blur(10px);
  min-width: 260px;
  max-width: 380px;
}
.toast-glow {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  border-radius: 4px;
  box-shadow: 0 0 30px rgba(106, 190, 48, 0.1);
  pointer-events: none;
}
.toast-icon {
  font-size: 16px;
  color: var(--green);
  animation: pulse-toast 1s ease-in-out infinite alternate;
}
@keyframes pulse-toast {
  from { opacity: 0.6; filter: drop-shadow(0 0 1px var(--green)); }
  to { opacity: 1; filter: drop-shadow(0 0 6px var(--green)); }
}
.toast-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.toast-label {
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.8px;
}
.toast-val {
  font-family: var(--font-co);
  font-size: 11px;
  font-weight: 600;
  color: var(--textwh);
  word-break: break-all;
}

/* Toast Transition */
.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-leave-active {
  transition: all 0.25s cubic-bezier(0.7, 0, 0.84, 0);
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}
/* VLAN Helper & Cyber Select Styles */
.vlan-helper-box {
  background: rgba(0, 229, 255, 0.02);
  border: 1px dashed rgba(0, 229, 255, 0.3);
  border-radius: 6px;
  padding: 12px;
  margin-top: 16px;
  box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.02);
}
.vlan-helper-box .helper-title {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  color: var(--cyan);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.vlan-helper-box .helper-desc {
  font-size: 11px;
  color: var(--text);
  margin-bottom: 12px;
  line-height: 1.4;
}
.cyber-select {
  background: var(--bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  color: var(--textwh) !important;
  padding: 6px 10px !important;
  font-size: 12px !important;
  outline: none !important;
  transition: all 0.2s !important;
}
.cyber-select:focus {
  border-color: var(--cyan) !important;
  box-shadow: var(--shadow-c) !important;
}
.vlan-to-delete {
  border: 1px solid var(--pink) !important;
  background: rgba(255, 45, 110, 0.05) !important;
  opacity: 0.85;
}
.vlan-to-delete input, .vlan-to-delete select {
  color: var(--pink) !important;
  border-color: rgba(255, 45, 110, 0.3) !important;
  text-decoration: line-through;
}
.form-actions-tip {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text);
  line-height: 1.4;
  opacity: 0.85;
}
.form-actions-tip .cyan-glow {
  color: var(--cyan);
  text-shadow: 0 0 5px rgba(0, 229, 255, 0.3);
}

/* --- Enhanced WireGuard Form Styles --- */
.wireguard-form-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.wg-profile-panel {
  background: rgba(0, 229, 255, 0.035);
  border: 1px solid rgba(0, 229, 255, 0.16);
  border-left: 3px solid var(--cyan);
  border-radius: 4px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.wg-profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.wg-profile-title {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 800;
  color: var(--cyan);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.wg-profile-subtitle {
  color: var(--text);
  font-size: 11px;
  margin-top: 3px;
  opacity: 0.78;
}
.wg-profile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  align-items: flex-end;
  gap: 10px;
}
.wg-profile-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.btn-wg-node-load,
.btn-wg-profile-save,
.btn-wg-profile-load,
.btn-wg-profile-delete {
  border-radius: 4px;
  font-family: var(--font-hd);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  cursor: pointer;
  padding: 7px 10px;
  text-transform: uppercase;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.btn-wg-node-load,
.btn-wg-profile-load {
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.35);
  color: var(--cyan);
}
.btn-wg-profile-save {
  background: rgba(0, 255, 157, 0.08);
  border: 1px solid rgba(0, 255, 157, 0.35);
  color: var(--green);
}
.btn-wg-profile-delete {
  background: rgba(255, 45, 110, 0.06);
  border: 1px solid rgba(255, 45, 110, 0.28);
  color: var(--pink);
}
.btn-wg-node-load:hover:not(:disabled),
.btn-wg-profile-load:hover:not(:disabled) {
  background: var(--cyan);
  color: var(--bg);
}
.btn-wg-profile-save:hover:not(:disabled) {
  background: var(--green);
  color: var(--bg);
}
.btn-wg-profile-delete:hover:not(:disabled) {
  background: rgba(255, 45, 110, 0.22);
}
.btn-wg-node-load:disabled,
.btn-wg-profile-load:disabled,
.btn-wg-profile-delete:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.key-gen-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: flex-end;
  gap: 12px;
}
.input-with-actions-container {
  display: flex;
  flex-direction: column;
}
.private-key-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.input-actions-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.private-key-input {
  width: 100%;
  padding-right: 70px !important; /* Space for overlay actions */
}
.btn-input-action {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: var(--text);
  cursor: pointer;
  padding: 4px 6px;
  font-size: 14px;
  opacity: 0.6;
  transition: opacity 0.2s, transform 0.1s;
}
.btn-input-action:hover {
  opacity: 1;
}
.btn-input-action:active {
  transform: translateY(-50%) scale(0.9);
}
.btn-input-action:nth-last-child(2) {
  right: 34px; /* Second button positioning */
}
.gen-keys-button-wrapper {
  display: flex;
}
.btn-wg-generate {
  background: rgba(0, 229, 255, 0.1) !important;
  border: 1px solid var(--cyan) !important;
  color: var(--cyan) !important;
  padding: 8px 16px !important;
  border-radius: 4px !important;
  font-family: var(--font-hd) !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em !important;
  cursor: pointer !important;
  text-transform: uppercase !important;
  transition: all 0.25s ease !important;
  height: 32px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.btn-wg-generate:hover:not(:disabled) {
  background: var(--cyan) !important;
  color: var(--bg) !important;
  box-shadow: var(--shadow-c) !important;
}
.btn-wg-generate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Derived Local Public Key Panel */
.derived-pubkey-panel {
  background: rgba(0, 229, 255, 0.03);
  border: 1px solid rgba(0, 229, 255, 0.18);
  border-left: 3px solid var(--cyan);
  border-radius: 4px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
  animation: wg-glow-in 0.4s ease-out;
}
@keyframes wg-glow-in {
  from { opacity: 0; transform: translateY(-4px); box-shadow: 0 0 0 rgba(0, 229, 255, 0); }
  to { opacity: 1; transform: translateY(0); box-shadow: 0 0 10px rgba(0, 229, 255, 0.15); }
}
.derived-pubkey-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pubkey-title-glow {
  font-family: var(--font-hd);
  font-size: 9px;
  font-weight: 800;
  color: var(--cyan);
  letter-spacing: 0.08em;
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.35);
}
.btn-pubkey-copy {
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.4);
  color: var(--cyan);
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 9px;
  font-family: var(--font-hd);
  cursor: pointer;
  transition: all 0.2s;
}
.btn-pubkey-copy:hover {
  background: var(--cyan);
  color: var(--bg);
}
.derived-pubkey-value {
  font-family: var(--font-co);
  font-size: 11px;
  color: var(--green);
  word-break: break-all;
  user-select: all;
  background: rgba(8, 13, 24, 0.35);
  padding: 6px 10px;
  border-radius: 3px;
  border: 1px solid rgba(255, 255, 255, 0.03);
}

/* Collapsible Advanced Toggle */
.wg-advanced-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  cursor: pointer;
  margin: 6px 0;
  transition: all 0.2s ease;
}
.wg-advanced-toggle:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(0, 229, 255, 0.15);
}
.advanced-toggle-title {
  font-family: var(--font-hd);
  font-size: 10px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.05em;
  opacity: 0.85;
}
.wg-advanced-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  margin-bottom: 8px;
}

/* WireGuard Key History Styles */
.wg-history-toggle {
  border-color: rgba(0, 255, 157, 0.1) !important;
}
.wg-history-toggle:hover {
  border-color: rgba(0, 255, 157, 0.3) !important;
  background: rgba(0, 255, 157, 0.03) !important;
}
.wg-history-toggle .advanced-toggle-title {
  color: var(--green) !important;
  text-shadow: 0 0 8px rgba(0, 255, 157, 0.2);
}
.wg-history-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(0, 255, 157, 0.08);
  border-radius: 4px;
  margin-bottom: 8px;
  max-height: 350px;
  overflow-y: auto;
}
.no-keys-message {
  font-size: 11px;
  color: var(--text);
  text-align: center;
  padding: 10px 0;
  font-style: italic;
}
.wg-history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.history-item-card {
  background: rgba(8, 13, 24, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s ease;
}
.history-item-card:hover {
  border-color: rgba(0, 255, 157, 0.2);
  background: rgba(8, 13, 24, 0.8);
}
.history-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  padding-bottom: 4px;
}
.history-item-label {
  font-family: var(--font-hd);
  font-size: 11px;
  font-weight: 700;
  color: var(--textwh);
}
.history-item-date {
  font-size: 10px;
  color: var(--text);
}
.history-keys-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.history-key-wrapper {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.02);
  border-radius: 3px;
  padding: 4px 6px;
  gap: 6px;
}
.key-type {
  font-size: 10px;
  font-weight: 700;
  color: var(--cyan);
  min-width: 32px;
}
.key-value {
  font-size: 11px;
  color: var(--textbr);
  word-break: break-all;
  flex: 1;
}
.btn-history-action {
  background: transparent;
  border: none;
  color: var(--text);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 2px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.btn-history-action:hover {
  color: var(--cyan);
  background: rgba(0, 229, 255, 0.1);
}
.history-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
.btn-history-load {
  background: rgba(0, 255, 157, 0.1);
  border: 1px solid rgba(0, 255, 157, 0.3);
  border-radius: 3px;
  color: var(--green);
  font-family: var(--font-hd);
  font-size: 10px;
  padding: 4px 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}
.btn-history-load:hover {
  background: var(--green);
  color: var(--bg);
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.4);
}
.btn-history-remove {
  background: rgba(255, 45, 110, 0.05);
  border: 1px solid rgba(255, 45, 110, 0.2);
  border-radius: 3px;
  color: var(--pink);
  font-size: 10px;
  padding: 4px 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-history-remove:hover {
  background: rgba(255, 45, 110, 0.2);
  border-color: var(--pink);
}

/* Peer Rows and Responsive Grid */
.peer-row-container {
  position: relative;
  background: rgba(10, 16, 32, 0.25);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 14px 44px 14px 14px !important;
  margin-bottom: 10px;
}
.peer-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px 12px;
  width: 100%;
}
.peer-full-width {
  grid-column: span 2;
}
.btn-remove-peer {
  position: absolute !important;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  margin: 0 !important;
  height: 28px !important;
  width: 28px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

/* WireGuard Deletion Mode Styles */
.wg-deletion-mode {
  border: 1px solid rgba(255, 46, 99, 0.15) !important;
  box-shadow: 0 0 15px rgba(255, 46, 99, 0.03) !important;
}

.action-selector-row {
  margin-bottom: 15px;
}

.action-select {
  background: rgba(10, 16, 32, 0.7) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: var(--text) !important;
  padding: 6px 12px;
  border-radius: 4px;
  font-family: var(--font-co);
  font-size: 11px;
  cursor: pointer;
  width: 100%;
  transition: all 0.25s ease;
}

.action-select:focus {
  border-color: var(--cyan) !important;
  outline: none;
}

.wg-deletion-mode .action-select:focus {
  border-color: #ff2e63 !important;
}

.wg-delete-warning-box {
  background: rgba(255, 46, 99, 0.03);
  border: 1px solid rgba(255, 46, 99, 0.2);
  border-left: 3px solid #ff2e63;
  border-radius: 4px;
  padding: 12px 16px;
  margin-top: 10px;
  animation: wg-pulse-warning 2s infinite alternate;
}

@keyframes wg-pulse-warning {
  0% { box-shadow: 0 0 5px rgba(255, 46, 99, 0.05); }
  100% { box-shadow: 0 0 12px rgba(255, 46, 99, 0.15); }
}

.warning-header {
  font-family: var(--font-hd);
  font-size: 10px;
  font-weight: 800;
  color: #ff2e63;
  letter-spacing: 0.1em;
  margin-bottom: 6px;
  text-shadow: 0 0 8px rgba(255, 46, 99, 0.35);
}

.wg-delete-warning-box p {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.7);
}

.highlight-wg {
  color: #ff2e63;
  text-shadow: 0 0 6px rgba(255, 46, 99, 0.4);
}

@media (max-width: 900px) {
  .wg-profile-header,
  .wg-profile-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .wg-profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
