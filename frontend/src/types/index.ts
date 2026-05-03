export interface NrNode {
  id: string
  name: string
  host: string
  port: number
  username: string
  transport: 'ssh' | 'telnet'
  device_type: 'gns3' | 'linux' | 'rpi' | 'unknown'
  has_password: boolean
  created: string
  tags: string[]
}

export interface CommandResult {
  command: string
  output: string
  error: string | null
}

export interface SavedConfig {
  name: string
  size: number
  modified: string
}

export type ReadType =
  | 'ip' | 'routes' | 'interfaces' | 'neighbors' | 'sockets' | 'resolver'
  | 'nftables' | 'iptables' | 'ufw' | 'wireguard' | 'forwarding'
  | 'vlan-router' | 'vlan-switch' | 'dns-service' | 'dhcp-server' | 'nat'
  | 'services' | 'packages' | 'users' | 'groups' | 'cron' | 'logs'
  | 'disk' | 'cpu' | 'memory' | 'processes' | 'os-info' | 'environment' | 'mounts'
  | 'rpi-config' | 'rpi-gpio' | 'rpi-temp' | 'rpi-i2c' | 'rpi-camera'
  | 'rpi-clocks' | 'rpi-voltage' | 'rpi-info'

export interface ReadCategory {
  label: string
  icon: string
  types: { type: ReadType; label: string }[]
}

export const READ_CATEGORIES: Record<string, ReadCategory> = {
  network: {
    label: 'Network',
    icon: '🌐',
    types: [
      { type: 'ip',          label: 'IP Addresses' },
      { type: 'routes',      label: 'Routes' },
      { type: 'interfaces',  label: 'Interfaces' },
      { type: 'neighbors',   label: 'ARP/Neighbors' },
      { type: 'sockets',     label: 'Sockets' },
      { type: 'resolver',    label: 'DNS Resolver' },
      { type: 'forwarding',  label: 'IP Forwarding' },
      { type: 'nat',         label: 'NAT' },
      { type: 'nftables',    label: 'nftables' },
      { type: 'iptables',    label: 'iptables' },
      { type: 'ufw',         label: 'UFW' },
      { type: 'wireguard',   label: 'WireGuard' },
      { type: 'vlan-router', label: 'VLAN Router' },
      { type: 'vlan-switch', label: 'VLAN Switch' },
      { type: 'dns-service', label: 'DNS Service' },
      { type: 'dhcp-server', label: 'DHCP Server' },
    ],
  },
  linux: {
    label: 'Linux',
    icon: '🐧',
    types: [
      { type: 'os-info',     label: 'OS Info' },
      { type: 'services',    label: 'Services' },
      { type: 'packages',    label: 'Packages' },
      { type: 'processes',   label: 'Processes' },
      { type: 'users',       label: 'Users' },
      { type: 'groups',      label: 'Groups' },
      { type: 'cron',        label: 'Cron Jobs' },
      { type: 'logs',        label: 'Logs' },
      { type: 'disk',        label: 'Disk' },
      { type: 'cpu',         label: 'CPU' },
      { type: 'memory',      label: 'Memory' },
      { type: 'mounts',      label: 'Mounts' },
      { type: 'environment', label: 'Environment' },
    ],
  },
  rpi: {
    label: 'Raspberry Pi',
    icon: '🍓',
    types: [
      { type: 'rpi-info',    label: 'RPi Info' },
      { type: 'rpi-config',  label: 'config.txt' },
      { type: 'rpi-gpio',    label: 'GPIO' },
      { type: 'rpi-temp',    label: 'Temperature' },
      { type: 'rpi-i2c',     label: 'I2C' },
      { type: 'rpi-camera',  label: 'Camera' },
      { type: 'rpi-clocks',  label: 'Clocks' },
      { type: 'rpi-voltage', label: 'Voltage' },
    ],
  },
}
