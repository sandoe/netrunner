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
          <!-- Specialized Interface Form -->
          <div v-if="activeType === 'interface'" class="specialized-form">
            <div class="form-row">
              <label>Interface
                <input v-model="interfaceForm.interface" placeholder="eth0" />
              </label>
              <label class="check-label">
                <input type="checkbox" v-model="interfaceForm.dhcp" /> Enable DHCP
              </label>
            </div>
            <div class="section-label-sub">Static Addresses</div>
            <div v-for="(addr, idx) in interfaceForm.addresses" :key="idx" class="form-row">
              <input v-model="interfaceForm.addresses[idx]" placeholder="10.0.0.1/24" />
              <button class="btn-remove" @click="interfaceForm.addresses.splice(idx, 1)">✕</button>
            </div>
            <div class="form-actions">
              <button class="btn-add-sub" @click="interfaceForm.addresses.push('')">+ Add Static IP</button>
              <label v-if="interfaceForm.addresses.length > 0">Action
                <select v-model="interfaceForm.action">
                  <option value="add">Add Only</option>
                  <option value="flush">Flush & Add</option>
                </select>
              </label>
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
                <input v-model="route.dev" placeholder="eth0" />
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
              <label>WAN (Outbound) <input v-model="natForm.outbound_iface" /></label>
              <label>LAN (Inbound) <input v-model="natForm.inbound_iface" /></label>
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
              <label>Base Interface <input v-model="vlanRouterForm.interface" /></label>
            </div>
            <div class="section-label-sub">VLAN Interfaces</div>
            <div v-for="(v, i) in vlanRouterForm.vlans" :key="i" class="form-row multi-row">
              <label>VLAN ID <input v-model="v.id" /></label>
              <label>Address <input v-model="v.address" /></label>
              <label>Description <input v-model="v.description" /></label>
              <button class="btn-remove" @click="vlanRouterForm.vlans.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="vlanRouterForm.vlans.push({ id: '', address: '', description: '' })">+ Add VLAN</button>
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
              <label>Iface <input v-model="p.iface" /></label>
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
            <button class="btn-add-sub" @click="vlanSwitchForm.ports.push({ iface: '', mode: 'access', vlan: '1', allowed: [] })">+ Add Port</button>
          </div>

          <!-- WireGuard Form -->
          <div v-if="activeType === 'wireguard'" class="specialized-form">
            <div class="form-row">
              <label>Interface <input v-model="wireguardForm.interface" /></label>
              <label>Address <input v-model="wireguardForm.address" /></label>
              <label>Listen Port <input v-model.number="wireguardForm.listen_port" type="number" /></label>
            </div>
            <label>Private Key <input v-model="wireguardForm.private_key" type="password" /></label>
            <div class="section-label-sub">Peers</div>
            <div v-for="(peer, i) in wireguardForm.peers" :key="i" class="form-row multi-row">
              <label>Public Key <input v-model="peer.public_key" /></label>
              <label>Endpoint <input v-model="peer.endpoint" /></label>
              <label>Allowed IPs <input v-model="peer.allowed_ips" /></label>
              <button class="btn-remove" @click="wireguardForm.peers.splice(i, 1)">✕</button>
            </div>
            <button class="btn-add-sub" @click="wireguardForm.peers.push({ public_key: '', endpoint: '', allowed_ips: '0.0.0.0/0' })">+ Add Peer</button>
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
              <label>Iface <input v-model="wolForm.interface" placeholder="(optional)" /></label>
            </div>
          </div>

          <!-- Arp-scan Form -->
          <div v-if="activeType === 'arp-scan'" class="specialized-form">
            <div class="form-row">
              <label>Target <input v-model="arpScanForm.target" placeholder="localnet | 192.168.1.0/24" /></label>
              <label>Iface <input v-model="arpScanForm.interface" placeholder="eth0 (optional)" /></label>
            </div>
          </div>

          <div class="input-section">
            <div class="section-label">Data (JSON)<span v-if="activeType" class="auto-label"> — auto-generated</span></div>
            <textarea
              v-model="inputJson"
              class="json-textarea"
              spellcheck="false"
              placeholder='{ "interface": "eth0", "addresses": ["192.168.1.1/24"] }'
            ></textarea>
          </div>

          <div class="preview-section" v-if="previewCommands.length || previewError">
            <div class="section-label">Generated Commands</div>
            <div v-if="previewError" class="preview-error">{{ previewError }}</div>
            <pre v-else class="preview-pre">{{ previewCommands.join('\n') }}</pre>
          </div>

          <div class="results-section" v-if="results.length">
            <div class="section-label">
              Execution Results
              <button class="btn-clear-results" @click="results = []">clear</button>
            </div>
            <div v-for="(r, i) in results" :key="i" class="result-block">
              <div class="result-cmd">$ {{ r.command }}</div>
              <pre v-if="r.output" class="result-out">{{ r.output }}</pre>
              <pre v-if="r.error" class="result-err">{{ r.error }}</pre>
              <!-- Fix button if command not found -->
              <div v-if="(r.output + r.error).toLowerCase().includes('not found') || (r.output + r.error).toLowerCase().includes('not installed')" class="result-fix">
                <button class="btn-fix-inline" @click="installMissing(r.command)" :disabled="installingTool">
                    {{ installingTool ? 'INSTALLING...' : 'INSTALL MISSING TOOL' }}
                </button>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
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
  }
}

const activeType      = ref<string | null>(null)
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

const defaultInterfaceForm    = () => ({ interface: 'eth0', addresses: [] as string[], dhcp: false, action: 'add' })
const defaultRouteForm        = () => ({ routes: [{ dst: '10.1.0.0/24', via: '10.0.0.254', dev: '', metric: 0 }], isDelete: false })
const defaultDnsForm          = () => ({ nameservers: ['8.8.8.8'], search: ['local'], hostname: '', domain: '', records: [{ name: '', value: '' }] })
const defaultNatForm          = () => ({ outbound_iface: 'eth0', inbound_iface: 'eth1', source_subnet: '10.0.0.0/24', masquerade: true, port_forwards: [{ proto: 'tcp', external_port: '80', target_ip: '10.0.0.10', target_port: '80' }] })
const defaultVlanRouterForm   = () => ({ interface: 'eth0', vlans: [{ id: '10', address: '10.0.10.1/24', description: 'Management' }] })
const defaultVlanSwitchForm   = () => ({ bridge: 'br0', vlans: [{ id: '10', name: 'MGMT' }], ports: [{ iface: 'eth1', mode: 'access', vlan: '10', allowed: [] as string[] }] })
const defaultWireguardForm    = () => ({ interface: 'wg0', private_key: '', address: '10.0.0.1/24', listen_port: 51820, peers: [{ public_key: '', endpoint: '', allowed_ips: '0.0.0.0/0' }] })
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
  inputJson.value = JSON.stringify({
    interface: interfaceForm.value.interface,
    addresses: interfaceForm.value.addresses.filter(a => a.trim()),
    dhcp: interfaceForm.value.dhcp,
    action: interfaceForm.value.action
  }, null, 2)
}

const routeForm       = ref(defaultRouteForm())
const dnsForm         = ref(defaultDnsForm())
const natForm         = ref(defaultNatForm())
const vlanRouterForm  = ref(defaultVlanRouterForm())
const vlanSwitchForm  = ref(defaultVlanSwitchForm())
const wireguardForm   = ref(defaultWireguardForm())
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
    vlans: vlanRouterForm.value.vlans.filter(v => v.id)
  }, null, 2)
}

function syncVlanSwitchForm() {
  inputJson.value = JSON.stringify({
    ...vlanSwitchForm.value,
    vlans: vlanSwitchForm.value.vlans.filter(v => v.id),
    ports: vlanSwitchForm.value.ports.filter(p => p.iface)
  }, null, 2)
}

function syncWireguardForm() {
  inputJson.value = JSON.stringify({
    ...wireguardForm.value,
    peers: wireguardForm.value.peers.filter(p => p.public_key)
  }, null, 2)
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
    const res = await api.preview(activeType.value!, data)
    let cmds = res.commands
    if (persistMode.value && cmds.length) {
      const wrapped = await api.preview('persist', { name: activeType.value, commands: cmds })
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
  try {
    const res = await api.executeNode(props.nodeId, previewCommands.value)
    results.value = res.results
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

// Auto-update JSON as form fields change
watch(interfaceForm,   () => { if (activeType.value === 'interface')   syncInterfaceForm() },   { deep: true })
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
})
</script>

<style scoped>
.config-panel { display: flex; height: 100%; overflow: hidden; }
.config-sidebar {
  width: 180px; min-width: 180px; overflow-y: auto;
  border-right: 1px solid #30363d; padding: 8px 0;
}
.cat-group { margin-bottom: 8px; }
.cat-label {
  padding: 6px 12px; font-size: 11px; font-weight: 600;
  color: #6e7681; text-transform: uppercase;
  cursor: pointer; display: flex; justify-content: space-between; align-items: center;
  user-select: none; transition: color .2s;
}
.cat-label:hover { color: #c9d1d9; }
.cat-chevron { font-size: 10px; transition: transform .3s; }
.cat-chevron.collapsed { transform: rotate(180deg); }
.type-btn {
  display: block; width: 100%; padding: 5px 14px; text-align: left;
  background: none; border: none; color: #8b949e;
  font-size: 12px; cursor: pointer;
}
.type-btn:hover { background: #161b22; color: #c9d1d9; }
.type-btn.active { background: #1c2128; color: #58a6ff; }

.config-main { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.placeholder { color: #6e7681; font-size: 13px; padding: 24px; }
.config-editor { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.editor-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; border-bottom: 1px solid #30363d;
}
.type-name { font-size: 14px; font-weight: 600; color: #e6edf3; }
.header-actions { display: flex; gap: 8px; }
.btn-preview, .btn-apply, .btn-clear-form {
  padding: 4px 10px; font-size: 12px; border-radius: 4px;
  cursor: pointer; border: 1px solid #30363d;
}
.btn-preview { background: #21262d; color: #c9d1d9; }
.btn-clear-form { background: #21262d; color: #8b949e; }
.btn-clear-form:hover { color: #f85149; border-color: rgba(248, 81, 73, 0.4); }
.btn-apply { background: #238636; color: #fff; border-color: #2ea043; }
.btn-apply:disabled { opacity: 0.5; cursor: not-allowed; }
.persist-toggle {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: #8b949e; cursor: pointer;
  padding: 4px 8px; border: 1px solid #30363d; border-radius: 4px;
  background: #0d1117; user-select: none;
}
.persist-toggle:has(input:checked) { color: #d29922; border-color: #4a3818; background: #1f1500; }
.persist-toggle input { margin: 0; cursor: pointer; }

.specialized-form {
  background: #1c2128; padding: 12px; border-radius: 6px;
  border: 1px solid #30363d; margin-bottom: 8px;
}
.form-row { display: flex; gap: 12px; margin-bottom: 10px; }
.form-row label { flex: 1; display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: #8b949e; }
.form-row input, .form-row select {
  background: #0d1117; border: 1px solid #30363d; border-radius: 4px;
  color: #e6edf3; padding: 5px 8px; font-size: 12px;
}
.btn-sync {
  width: 100%; padding: 4px; font-size: 11px; background: #21262d;
  border: 1px solid #30363d; border-radius: 4px; color: #8b949e; cursor: pointer;
}
.btn-sync:hover { background: #30363d; color: #c9d1d9; }

.section-label-sub {
  font-size: 10px; font-weight: 600; color: #484f58;
  text-transform: uppercase; margin: 12px 0 6px;
  border-bottom: 1px solid #21262d; padding-bottom: 2px;
}
.warning-box {
  background: #331c00; border: 1px solid #d29922; border-radius: 6px;
  padding: 10px; color: #d29922; font-size: 12px; margin-bottom: 10px;
}

.multi-row { align-items: flex-end; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
.btn-remove {
  background: none; border: none; color: #f85149; cursor: pointer;
  padding: 5px; font-size: 14px; margin-bottom: 3px;
}
.btn-remove:hover { color: #ff7b72; }
.form-actions { display: flex; align-items: center; gap: 16px; margin-top: 10px; }
.btn-add-sub {
  background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
  padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;
}
.btn-add-sub:hover { background: #30363d; }
.check-label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #8b949e; cursor: pointer; flex: 1; }
.fw-rule {
  background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
  padding: 8px 10px; margin-bottom: 8px;
}
.fw-rule .form-row { margin-bottom: 6px; }
.fw-rule .form-row:last-child { margin-bottom: 0; }
.hint { font-size: 11px; color: #6e7681; margin-top: 6px; font-style: italic; }

.editor-body { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 16px; }
.section-label { 
  font-size: 11px; font-weight: 600; color: #6e7681; 
  text-transform: uppercase; margin-bottom: 6px; 
  display: flex; justify-content: space-between; align-items: center;
}
.btn-clear-results {
  background: none; border: 1px solid #30363d; color: #6e7681;
  font-size: 10px; padding: 1px 6px; border-radius: 3px; cursor: pointer;
}
.btn-clear-results:hover { color: #f85149; border-color: #f85149; }
.auto-label { font-weight: 400; text-transform: none; color: #484f58; }
.json-textarea {
  width: 100%; height: 120px; background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #c9d1d9; font-family: monospace; font-size: 12px;
  padding: 8px; resize: vertical;
}
.preview-pre {
  background: #161b22; padding: 10px; border-radius: 6px;
  font-family: monospace; font-size: 12px; color: #d29922;
  white-space: pre-wrap; margin: 0;
}
.preview-error { color: #f85149; font-size: 12px; margin-bottom: 8px; }

.result-block { margin-bottom: 8px; }
.result-cmd { font-family: monospace; font-size: 11px; color: #58a6ff; margin-bottom: 2px; }
.result-out, .result-err {
  padding: 6px 8px; font-family: monospace; font-size: 11px;
  border-radius: 4px; white-space: pre-wrap;
}
.result-out { background: #0d1117; color: #c9d1d9; }
.result-err { background: #1a0a0a; color: #f85149; }

.result-fix { margin-top: 6px; }
.btn-fix-inline {
    padding: 4px 12px; background: none; border: 1px solid var(--green);
    color: var(--green); border-radius: 4px; font-size: 10px;
    font-family: var(--font-hd); cursor: pointer; transition: all 0.2s;
}
.btn-fix-inline:hover:not(:disabled) { background: var(--green); color: var(--bg); box-shadow: var(--shadow-g); }
.btn-fix-inline:disabled { opacity: 0.5; cursor: wait; }
</style>
