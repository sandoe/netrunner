import { createRouter, createWebHistory } from 'vue-router'
import NetworkPulse from '@/components/NetworkPulse.vue'
import AgentMapView from '@/views/AgentMapView.vue'
import AttackMatrix from '@/components/AttackMatrix.vue'
import TopologyView from '@/components/TopologyView.vue'
import ReconView from '@/components/ReconView.vue'
import ThreatMap from '@/components/ThreatMap.vue'
import WifiView from '@/components/WifiView.vue'
import BluetoothView from '@/components/BluetoothView.vue'
import InfrastructureView from '@/components/InfrastructureView.vue'
import ClientsView from '@/components/ClientsView.vue'
import TrafficAnalyticsView from '@/components/TrafficAnalyticsView.vue'
import HotspotManagerView from '@/components/HotspotManagerView.vue'
import HostControlView from '@/views/HostControlView.vue'
import ThreatTimeline from '@/components/ThreatTimeline.vue'
import BruteforceControlRoom from '@/components/BruteforceControlRoom.vue'
import DatabaseControlView from '@/views/DatabaseControlView.vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import WarRoomDashboard from '@/components/WarRoomDashboard.vue'
import WelcomeView from '@/views/WelcomeView.vue'
import AlertInboxView from '@/views/AlertInboxView.vue'
import ReportGeneratorView from '@/views/ReportGeneratorView.vue'
import PlaybooksView from '@/views/PlaybooksView.vue'

const routes = [
  { path: '/', name: 'home', redirect: '/node' },
  { path: '/node', name: 'node', component: WelcomeView },
  { path: '/alerts', name: 'alerts', component: AlertInboxView },
  { path: '/reports', name: 'reports', component: ReportGeneratorView },
  { path: '/playbooks', name: 'playbooks', component: PlaybooksView },
  { path: '/pulse', name: 'pulse', component: NetworkPulse },
  { path: '/agent-map', name: 'agent-map', component: AgentMapView },
  { path: '/attack', name: 'attack', component: AttackMatrix },
  { path: '/topology', name: 'topology', component: TopologyView },
  { path: '/recon', name: 'recon', component: ReconView },
  { path: '/threat', name: 'threat', component: ThreatMap },
  { path: '/wifi', name: 'wifi', component: WifiView },
  { path: '/bluetooth', name: 'bluetooth', component: BluetoothView },
  { path: '/sdn-config', name: 'sdn-config', component: InfrastructureView },
  { path: '/sdn-clients', name: 'sdn-clients', component: ClientsView },
  { path: '/sdn-traffic', name: 'sdn-traffic', component: TrafficAnalyticsView },
  { path: '/sdn-hotspot', name: 'sdn-hotspot', component: HotspotManagerView },
  { path: '/host', name: 'host', component: HostControlView },
  { path: '/history', name: 'history', component: ThreatTimeline },
  { path: '/bruteforce', name: 'bruteforce', component: BruteforceControlRoom },
  { path: '/database', name: 'database', component: DatabaseControlView },
  { path: '/intelligence', name: 'intelligence', component: KnowledgeGraph },
  { path: '/warroom', name: 'warroom', component: WarRoomDashboard }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
