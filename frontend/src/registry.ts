import { defineAsyncComponent } from 'vue'

const NetworkControllerView = defineAsyncComponent(() => import('@/views/NetworkControllerView.vue'))
const AttackMatrix = defineAsyncComponent(() => import('@/components/AttackMatrix.vue'))
const TopologyView = defineAsyncComponent(() => import('@/components/TopologyView.vue'))
const ReconView = defineAsyncComponent(() => import('@/components/ReconView.vue'))
const HostControlView = defineAsyncComponent(() => import('@/views/HostControlView.vue'))
const ThreatTimeline = defineAsyncComponent(() => import('@/components/ThreatTimeline.vue'))
const BruteforceControlRoom = defineAsyncComponent(() => import('@/components/BruteforceControlRoom.vue'))
const DatabaseControlView = defineAsyncComponent(() => import('@/views/DatabaseControlView.vue'))
const KnowledgeGraph = defineAsyncComponent(() => import('@/components/KnowledgeGraph.vue'))
const AlertInboxView = defineAsyncComponent(() => import('@/views/AlertInboxView.vue'))
const ReportGeneratorView = defineAsyncComponent(() => import('@/views/ReportGeneratorView.vue'))
const PlaybooksView = defineAsyncComponent(() => import('@/views/PlaybooksView.vue'))
const Layer2AttacksView = defineAsyncComponent(() => import('@/views/Layer2AttacksView.vue'))
const Layer3AttacksView = defineAsyncComponent(() => import('@/views/Layer3AttacksView.vue'))
const Layer4AttacksView = defineAsyncComponent(() => import('@/views/Layer4AttacksView.vue'))
const Layer5AttacksView = defineAsyncComponent(() => import('@/views/Layer5AttacksView.vue'))
const Layer6AttacksView = defineAsyncComponent(() => import('@/views/Layer6AttacksView.vue'))
const Layer7AttacksView = defineAsyncComponent(() => import('@/views/Layer7AttacksView.vue'))
const DashboardView = defineAsyncComponent(() => import('@/views/DashboardView.vue'))
const IntegrationsView = defineAsyncComponent(() => import('@/views/IntegrationsView.vue'))
const ThreatHuntingView = defineAsyncComponent(() => import('@/views/ThreatHuntingView.vue'))
const KismetView = defineAsyncComponent(() => import('@/views/KismetView.vue'))
const ForensicsView = defineAsyncComponent(() => import('@/views/ForensicsView.vue'))
const ComplianceView = defineAsyncComponent(() => import('@/views/ComplianceView.vue'))
const LateralMovementView = defineAsyncComponent(() => import('@/views/LateralMovementView.vue'))
const LogAggregationView = defineAsyncComponent(() => import('@/views/LogAggregationView.vue'))
const SocialEngineeringView = defineAsyncComponent(() => import('@/views/SocialEngineeringView.vue'))
const PrivescView = defineAsyncComponent(() => import('@/views/PrivescView.vue'))
const IncidentResponseView = defineAsyncComponent(() => import('@/views/IncidentResponseView.vue'))
const ExfiltrationView = defineAsyncComponent(() => import('@/views/ExfiltrationView.vue'))
const WifiAttackView = defineAsyncComponent(() => import('@/views/WifiAttackView.vue'))
const OsiInspector = defineAsyncComponent(() => import('@/components/OsiInspector.vue'))
const AnalyticsCenterView = defineAsyncComponent(() => import('@/views/AnalyticsCenterView.vue'))
const CyberdeckCodex = defineAsyncComponent(() => import('@/components/CyberdeckCodex.vue'))
const AiOrchestratorView = defineAsyncComponent(() => import('@/views/AiOrchestratorView.vue'))
export const AppRegistry: Record<string, any> = {
  network: NetworkControllerView,
  attack: AttackMatrix,
  topology: TopologyView,
  recon: ReconView,
  host: HostControlView,
  history: ThreatTimeline,
  bruteforce: BruteforceControlRoom,
  database: DatabaseControlView,
  intelligence: KnowledgeGraph,
  alerts: AlertInboxView,
  reports: ReportGeneratorView,
  playbooks: PlaybooksView,
  dashboard: DashboardView,
  integrations: IntegrationsView,
  hunting: ThreatHuntingView,
  kismet: KismetView,
  forensics: ForensicsView,
  compliance: ComplianceView,
  lateral: LateralMovementView,
  logs: LogAggregationView,
  'social-engineering': SocialEngineeringView,
  privesc: PrivescView,
  ir: IncidentResponseView,
  exfil: ExfiltrationView,
  'wifi-attack': WifiAttackView,
  osi: OsiInspector,
  analytics: AnalyticsCenterView,
  codex: CyberdeckCodex,
  layer2: Layer2AttacksView,
  layer3: Layer3AttacksView,
  layer4: Layer4AttacksView,
  layer5: Layer5AttacksView,
  layer6: Layer6AttacksView,
  layer7: Layer7AttacksView,
  ai: AiOrchestratorView
}
