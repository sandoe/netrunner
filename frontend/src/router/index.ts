import { createRouter, createWebHistory } from 'vue-router'
const NetworkControllerView = () => import('@/views/NetworkControllerView.vue')
const AttackMatrix = () => import('@/components/AttackMatrix.vue')
const TopologyView = () => import('@/components/TopologyView.vue')
const ReconView = () => import('@/components/ReconView.vue')
const HostControlView = () => import('@/views/HostControlView.vue')
const ThreatTimeline = () => import('@/components/ThreatTimeline.vue')
const BruteforceControlRoom = () => import('@/components/BruteforceControlRoom.vue')
const DatabaseControlView = () => import('@/views/DatabaseControlView.vue')
const KnowledgeGraph = () => import('@/components/KnowledgeGraph.vue')
const AlertInboxView = () => import('@/views/AlertInboxView.vue')
const ReportGeneratorView = () => import('@/views/ReportGeneratorView.vue')
const PlaybooksView = () => import('@/views/PlaybooksView.vue')
const DashboardView = () => import('@/views/DashboardView.vue')
const IntegrationsView = () => import('@/views/IntegrationsView.vue')
const ThreatHuntingView = () => import('@/views/ThreatHuntingView.vue')
const KismetView = () => import('@/views/KismetView.vue')
const ForensicsView = () => import('@/views/ForensicsView.vue')
const ComplianceView = () => import('@/views/ComplianceView.vue')
const Layer2AttacksView = () => import('@/views/Layer2AttacksView.vue')
const Layer3AttacksView = () => import('@/views/Layer3AttacksView.vue')
const Layer4AttacksView = () => import('@/views/Layer4AttacksView.vue')
const Layer5AttacksView = () => import('@/views/Layer5AttacksView.vue')
const Layer6AttacksView = () => import('@/views/Layer6AttacksView.vue')
const Layer7AttacksView = () => import('@/views/Layer7AttacksView.vue')
const LateralMovementView = () => import('@/views/LateralMovementView.vue')
const LogAggregationView = () => import('@/views/LogAggregationView.vue')
const SocialEngineeringView = () => import('@/views/SocialEngineeringView.vue')
const PrivescView = () => import('@/views/PrivescView.vue')
const IncidentResponseView = () => import('@/views/IncidentResponseView.vue')
const ExfiltrationView = () => import('@/views/ExfiltrationView.vue')
const WifiAttackView = () => import('@/views/WifiAttackView.vue')
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
  { path: '/layer2', name: 'layer2', component: Layer2AttacksView },
  { path: '/layer3', name: 'layer3', component: Layer3AttacksView },
  { path: '/layer4', name: 'layer4', component: Layer4AttacksView },
  { path: '/layer5', name: 'layer5', component: Layer5AttacksView },
  { path: '/layer6', name: 'layer6', component: Layer6AttacksView },
  { path: '/layer7', name: 'layer7', component: Layer7AttacksView },
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

router.beforeEach((to, from, next) => {
  const role = localStorage.getItem('nr_role')
  if (role === 'student') {
    const allowed = ['dashboard', 'reports', 'topology', 'alerts', 'home', 'network', 'node']
    const name = to.name as string
    if (!name || !allowed.includes(name)) {
      next({ name: 'dashboard' })
      return
    }
  }
  next()
})

router.afterEach((to, from) => {
  if (to.path !== from.path) {
    sendUiEvent('navigate', to.path, undefined, { from: from.path, name: to.name as string })
  }
})

export default router
