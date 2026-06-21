import { createRouter, createWebHistory } from 'vue-router'
import NetworkControllerView from '@/views/NetworkControllerView.vue'
import AttackMatrix from '@/components/AttackMatrix.vue'
import TopologyView from '@/components/TopologyView.vue'
import ReconView from '@/components/ReconView.vue'
import HostControlView from '@/views/HostControlView.vue'
import ThreatTimeline from '@/components/ThreatTimeline.vue'
import BruteforceControlRoom from '@/components/BruteforceControlRoom.vue'
import DatabaseControlView from '@/views/DatabaseControlView.vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import AlertInboxView from '@/views/AlertInboxView.vue'
import ReportGeneratorView from '@/views/ReportGeneratorView.vue'
import PlaybooksView from '@/views/PlaybooksView.vue'
import DashboardView from '@/views/DashboardView.vue'
import IntegrationsView from '@/views/IntegrationsView.vue'
import ThreatHuntingView from '@/views/ThreatHuntingView.vue'
import KismetView from '@/views/KismetView.vue'
import ForensicsView from '@/views/ForensicsView.vue'
import ComplianceView from '@/views/ComplianceView.vue'
import LateralMovementView from '@/views/LateralMovementView.vue'
import LogAggregationView from '@/views/LogAggregationView.vue'
import SocialEngineeringView from '@/views/SocialEngineeringView.vue'
import PrivescView from '@/views/PrivescView.vue'
import IncidentResponseView from '@/views/IncidentResponseView.vue'
import ExfiltrationView from '@/views/ExfiltrationView.vue'
import WifiAttackView from '@/views/WifiAttackView.vue'
import { sendUiEvent } from '@/api/client'

const routes = [
  { path: '/', name: 'home', redirect: '/dashboard' },
  { path: '/alerts', name: 'alerts', component: AlertInboxView },
  { path: '/reports', name: 'reports', component: ReportGeneratorView },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/integrations', name: 'integrations', component: IntegrationsView },
  { path: '/hunting', name: 'hunting', component: ThreatHuntingView },
  { path: '/playbooks', name: 'playbooks', component: PlaybooksView },
  { path: '/network', name: 'network', component: NetworkControllerView },
  { path: '/attack', name: 'attack', component: AttackMatrix },
  { path: '/topology', name: 'topology', component: TopologyView },
  { path: '/recon', name: 'recon', component: ReconView },
  { path: '/host', name: 'host', component: HostControlView },
  { path: '/history', name: 'history', component: ThreatTimeline },
  { path: '/bruteforce', name: 'bruteforce', component: BruteforceControlRoom },
  { path: '/database', name: 'database', component: DatabaseControlView },
  { path: '/intelligence', name: 'intelligence', component: KnowledgeGraph },
  { path: '/kismet', name: 'kismet', component: KismetView },
  { path: '/forensics', name: 'forensics', component: ForensicsView },
  { path: '/compliance', name: 'compliance', component: ComplianceView },
  { path: '/lateral', name: 'lateral', component: LateralMovementView },
  { path: '/logs', name: 'logs', component: LogAggregationView },
  { path: '/social-engineering', name: 'social-engineering', component: SocialEngineeringView },
  { path: '/privesc', name: 'privesc', component: PrivescView },
  { path: '/ir', name: 'ir', component: IncidentResponseView },
  { path: '/exfil', name: 'exfil', component: ExfiltrationView },
  { path: '/wifi-attack', name: 'wifi-attack', component: WifiAttackView },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to, from) => {
  if (to.path !== from.path) {
    sendUiEvent('navigate', to.path, undefined, { from: from.path, name: to.name as string })
  }
})

export default router
