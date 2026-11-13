export type DashboardSectionKey =
  | "overview"
  | "threats"
  | "entities"
  | "investigations"
  | "alerts"
  | "incidents"
  | "integrations";

export type Severity = "Critical" | "High" | "Medium" | "Low";

export type Threat = {
  id: string;
  title: string;
  actor: string;
  severity: Severity;
  source: string;
  status: "Active" | "Monitoring" | "Contained";
  confidence: number;
  description: string;
  relations: string[];
  indicators: string[];
  timeline: { id: string; time: string; title: string; detail: string }[];
  relatedEntities: string[];
};

export type Entity = {
  id: string;
  type: string;
  value: string;
  risk: Severity;
  firstSeen: string;
  tags: string[];
  status: "Observed" | "Monitored" | "Contained";
  description: string;
  confidence: number;
  relationships: { type: string; value: string }[];
};

export type InvestigationTimelineEvent = {
  id: string;
  type: string;
  time: string;
  description: string;
};

export type Investigation = {
  id: string;
  name: string;
  owner: string;
  progress: number;
  priority: "P1" | "P2" | "P3";
  stage: string;
  updated: string;
  status: "In progress" | "Monitoring" | "Closed";
  description: string;
  timeline: InvestigationTimelineEvent[];
  linkedThreats: string[];
};

export type Alert = {
  id: string;
  title: string;
  severity: Severity;
  source: string;
  observed: string;
  status: "Open" | "Dismissed" | "Investigating";
  category: string;
  description: string;
  timestamp: string;
  relatedEntity: string;
};

export type IncidentWorkflowStep = {
  id: string;
  label: string;
  owner: string;
  status: "Queued" | "Active" | "Resolved";
  eta: string;
  progress: number;
  notes: string;
};

export type Incident = {
  id: string;
  title: string;
  severity: Severity;
  status: "Open" | "Investigating" | "Contained" | "Resolved";
  category: string;
  summary: string;
  createdAt: string;
  updatedAt: string;
  owner: string;
  confidence: number;
  impactedSystems: string[];
  relatedThreats: string[];
  relatedEntities: string[];
  evidence: string[];
  workflow: IncidentWorkflowStep[];
  actions: { id: string; actor: string; time: string; type: string; summary: string }[];
};

export type DashboardNavigationItem = {
  id: DashboardSectionKey;
  label: string;
  href: string;
  count: string;
};

export type IntegrationConnection = {
  id: string;
  name: string;
  type: "SIEM" | "SOAR" | "Threat Intel" | "Identity" | "Cloud" | "Ticketing";
  status: "Connected" | "Healthy" | "Pending" | "Offline";
  latency: string;
  owner: string;
  endpoint: string;
  lastSync: string;
  metadata: string[];
};

export type OverviewStat = {
  label: string;
  value: string;
  delta: string;
};

export type DetectionBar = {
  label: string;
  value: number;
};

export type RecentEvent = {
  time: string;
  title: string;
  detail: string;
};

export type DashboardSnapshot = {
  section: DashboardSectionKey;
  stats: OverviewStat[];
  detection: DetectionBar[];
  events: RecentEvent[];
  threats: Threat[];
  entities: Entity[];
  investigations: Investigation[];
  alerts: Alert[];
  incidents: Incident[];
  integrations: IntegrationConnection[];
};

export const dashboardNavigation: DashboardNavigationItem[] = [
  { id: "overview", label: "Overview", href: "/", count: "12" },
  { id: "threats", label: "Threats", href: "/threats", count: "36" },
  { id: "entities", label: "Entities", href: "/entities", count: "64" },
  { id: "investigations", label: "Investigations", href: "/investigations", count: "08" },
  { id: "incidents", label: "Incidents", href: "/incidents", count: "04" },
  { id: "alerts", label: "Alerts", href: "/alerts", count: "19" },
  { id: "integrations", label: "Integrations", href: "/integrations", count: "06" },
];

export const overviewStats: OverviewStat[] = [
  { label: "Open indicators", value: "2,418", delta: "+18.4%" },
  { label: "Malware families", value: "84", delta: "+6" },
  { label: "Critical cases", value: "19", delta: "+3" },
  { label: "Detection coverage", value: "91%", delta: "+7.2%" },
  { label: "MTTD", value: "09m 41s", delta: "-2m 14s" },
  { label: "Containment SLA", value: "76%", delta: "+11%" },
];

export const detectionBars: DetectionBar[] = [
  { label: "Credential theft", value: 82 },
  { label: "Phishing", value: 66 },
  { label: "Supply chain", value: 54 },
  { label: "Ransomware", value: 76 },
  { label: "Malware delivery", value: 49 },
  { label: "Privilege abuse", value: 63 },
];

export const recentEvents: RecentEvent[] = [
  { time: "08:10", title: "IP cluster pivot observed", detail: "Three blocked hosts matched the same TTP profile and new C2 infrastructure." },
  { time: "09:35", title: "Mail relay anomaly", detail: "Outbound campaigns shifted to a new domain family across the finance segment." },
  { time: "12:20", title: "New IOC ingested", detail: "Indicators mapped to an active intrusion set in EU-CENTRAL and EMEA." },
  { time: "15:05", title: "Case synchronized", detail: "Analyst workflow and collector policy were re-linked to a live incident record." },
  { time: "16:12", title: "Identity anomaly", detail: "Privileged login pattern drifted outside normal operating hours and regional norms." },
];

export const processFlow = [
  { step: "01", title: "Ingest signals", detail: "Collect telemetry from endpoints, identities, mail and cloud assets." },
  { step: "02", title: "Correlate context", detail: "Map suspicious activity to entities, infrastructure and adversary behavior." },
  { step: "03", title: "Investigate and act", detail: "Prioritize response, assign ownership and contain active risk." },
];

export const productHighlights = [
  { title: "Threat intelligence", metric: "356", detail: "Indicators mapped to active adversary clusters" },
  { title: "Entity graph", metric: "1.2K", detail: "Linked domains, hashes, identities and IP objects" },
  { title: "Case velocity", metric: "09m 41s", detail: "Average time to detect and triage signals" },
  { title: "Containment", metric: "76%", detail: "Response coverage across critical workflows" },
];

export const threatData: Threat[] = [
  {
    id: "THR-421",
    title: "Credential harvesting campaign",
    actor: "APT-29",
    severity: "Critical",
    source: "Mail gateway",
    status: "Active",
    confidence: 96,
    description: "Adversary infrastructure is impersonating internal finance notifications to harvest credentials and session tokens.",
    relations: ["APT-29", "Phishing", "Credential theft"],
    indicators: ["mail.finance-secure.io", "9d4f21d7ab83", "45.77.124.17"],
    timeline: [
      { id: "t-1", time: "08:10", title: "Beacon established", detail: "First malicious macro executed after phishing lure clicked." },
      { id: "t-2", time: "09:28", title: "Token theft", detail: "Session cookies were exfiltrated to a rotating infrastructure node." },
      { id: "t-3", time: "10:14", title: "Credential replay", detail: "Attempted sign-in to privileged accounts from a suspicious endpoint." },
    ],
    relatedEntities: ["ENT-91", "ENT-125", "ENT-302"],
  },
  {
    id: "THR-612",
    title: "Malware staging via signed package",
    actor: "ShadowPad",
    severity: "High",
    source: "Software supply chain",
    status: "Monitoring",
    confidence: 82,
    description: "Unsigned execution path is being staged through a signed installation package to bypass endpoint controls.",
    relations: ["ShadowPad", "Supply chain", "Malware"],
    indicators: ["pkg-helm-update.exe", "sha256:8f2c1ef9", "signed-update.local"],
    timeline: [
      { id: "t-4", time: "06:42", title: "Signed package observed", detail: "Package with valid code signing began broadcasting malicious execution path." },
      { id: "t-5", time: "07:18", title: "Execution chain reviewed", detail: "Artifacts were compared against the supply-chain trust matrix." },
    ],
    relatedEntities: ["ENT-214"],
  },
  {
    id: "THR-118",
    title: "Phishing redirect chain",
    actor: "Storm-182",
    severity: "Medium",
    source: "Web analytics",
    status: "Contained",
    confidence: 71,
    description: "A redirect chain designed to impersonate identity verification pages was contained after user alerting.",
    relations: ["Storm-182", "Phishing", "Redirect"],
    indicators: ["redirect-verify.live", "sso-portal-secure.net", "mfa-reset-quick.click"],
    timeline: [
      { id: "t-6", time: "12:30", title: "Redirect activity", detail: "Visitors were routed through a chain of impersonation pages." },
      { id: "t-7", time: "13:10", title: "Containment", detail: "Web-side block rules were applied and malicious routes disabled." },
    ],
    relatedEntities: ["ENT-125"],
  },
  {
    id: "THR-204",
    title: "Ransomware exfiltration indicator",
    actor: "BlackCat",
    severity: "Critical",
    source: "Endpoint telemetry",
    status: "Active",
    confidence: 94,
    description: "A ransomware family with exfiltration behavior is transferring data toward external archive endpoints.",
    relations: ["BlackCat", "Exfiltration", "Ransomware"],
    indicators: ["archive-drive.net", "enc-9a2b", "c:\\temp\\vault.exe"],
    timeline: [
      { id: "t-8", time: "02:12", title: "Encrypted archive upload", detail: "Large archive transfer detected to external cloud storage." },
      { id: "t-9", time: "02:33", title: "Persistence attempt", detail: "Host attempted to register a scheduled task for repeat execution." },
    ],
    relatedEntities: ["ENT-91", "ENT-214"],
  },
];

export const entityData: Entity[] = [
  { id: "ENT-91", type: "IPv4", value: "45.77.124.17", risk: "Critical", firstSeen: "2026-11-11", tags: ["C2", "Proxy", "Malware"], status: "Observed", description: "Known command-and-control endpoint tied to a malicious beaconing cluster.", confidence: 96, relationships: [{ type: "associated-with", value: "THR-421" }, { type: "hosts", value: "APT-29" }] },
  { id: "ENT-125", type: "Domain", value: "secure-ops-update[.]cloud", risk: "High", firstSeen: "2026-11-09", tags: ["Phishing", "Redirect"], status: "Monitored", description: "Lookalike domain impersonating trusted operational communication resources.", confidence: 88, relationships: [{ type: "related-to", value: "THR-118" }, { type: "used-by", value: "Storm-182" }] },
  { id: "ENT-214", type: "File hash", value: "bfe6ab18f7c1...", risk: "Medium", firstSeen: "2026-11-08", tags: ["Loader", "Signed"], status: "Contained", description: "Signed loader sample detected in a restricted software delivery pipeline.", confidence: 74, relationships: [{ type: "linked-to", value: "THR-612" }, { type: "signature-match", value: "ShadowPad" }] },
  { id: "ENT-302", type: "Email", value: "ops@northbridge.it", risk: "Low", firstSeen: "2026-11-06", tags: ["Compromised", "Target"], status: "Observed", description: "Targeted email address mapped to a spear-phishing campaign footprint.", confidence: 61, relationships: [{ type: "targeted-by", value: "THR-421" }] },
];

export const investigationData: Investigation[] = [
  { id: "INV-03", name: "Credential theft on finance users", owner: "A. Szymczak", progress: 74, priority: "P1", stage: "Containment plan review", updated: "12 mins ago", status: "In progress", description: "Response is focused on the theft of finance identities and UBA-based credential compromise.", timeline: [
    { id: "evt-1", type: "Created", time: "08:15", description: "Case opened after suspicious sign-in alerts across finance workloads." },
    { id: "evt-2", type: "Analysis", time: "09:42", description: "Analysts correlated the activity with a known credential phishing theme." },
    { id: "evt-3", type: "Mitigation", time: "11:05", description: "Conditional access rules and MFA enforcement were deployed for affected users." },
  ], linkedThreats: ["THR-421"] },
  { id: "INV-11", name: "Suspicious package in release pipeline", owner: "K. Mrozinski", progress: 52, priority: "P1", stage: "Binary validation", updated: "28 mins ago", status: "Monitoring", description: "A suspicious package in the release pipeline is under validation for malicious insertion or signature abuse.", timeline: [
    { id: "evt-4", type: "Detection", time: "07:48", description: "The package pipeline triggered a hash match for a known malware staging pattern." },
    { id: "evt-5", type: "Review", time: "10:20", description: "Release artifacts are being unpacked and compared against signed provenance checks." },
  ], linkedThreats: ["THR-612"] },
  { id: "INV-22", name: "Abnormal outbound traffic cluster", owner: "L. Nowak", progress: 86, priority: "P2", stage: "Case packaging", updated: "46 mins ago", status: "In progress", description: "Outbound transfer cluster is being investigated as a possible data exfiltration chain.", timeline: [
    { id: "evt-6", type: "Detection", time: "06:30", description: "Anomalous egress from a cluster of endpoints exceeded the detection threshold." },
    { id: "evt-7", type: "Correlation", time: "08:05", description: "Traffic matched a historical data exfiltration signature in the same region." },
  ], linkedThreats: ["THR-204"] },
  { id: "INV-47", name: "Executive phishing lures", owner: "J. Kowalski", progress: 31, priority: "P3", stage: "Triage", updated: "1 hour ago", status: "Monitoring", description: "A phishing lure campaign aimed at executive roles is under triage and validation.", timeline: [
    { id: "evt-8", type: "Intake", time: "05:10", description: "Executive-targeted phishing lure was reported by a user on the help desk." },
    { id: "evt-9", type: "Triage", time: "06:40", description: "The subject lines and attachments are being compared with active impersonation sets." },
  ], linkedThreats: ["THR-118"] },
];

export const alertData: Alert[] = [
  { id: "ALT-180", title: "New beacon pattern observed", severity: "Critical", source: "EDR", observed: "02:41 UTC", status: "Open", category: "Beaconing", description: "Endpoint beaconing behavior is consistent with known C2 communications and a rotated domain cluster.", timestamp: "02:41 UTC", relatedEntity: "ENT-91" },
  { id: "ALT-181", title: "Suspicious PowerShell invoked on workstation", severity: "High", source: "Windows Defender", observed: "02:21 UTC", status: "Investigating", category: "Execution", description: "PowerShell execution used obfuscated flags and a remote script block pattern associated with living-off-the-land activity.", timestamp: "02:21 UTC", relatedEntity: "ENT-214" },
  { id: "ALT-182", title: "Lateral movement from finance VLAN", severity: "Medium", source: "Firewall", observed: "01:58 UTC", status: "Open", category: "Lateral movement", description: "Repeated authentication attempts were observed between workstations in a critical segment during off-hours.", timestamp: "01:58 UTC", relatedEntity: "ENT-302" },
  { id: "ALT-183", title: "Unusual admin password reset", severity: "Low", source: "IAM", observed: "00:48 UTC", status: "Dismissed", category: "Identity", description: "Password reset was reviewed and attributed to a known internal maintenance task.", timestamp: "00:48 UTC", relatedEntity: "ENT-302" },
];

export const incidentData: Incident[] = [
  {
    id: "INC-1001",
    title: "Finance credential theft campaign",
    severity: "Critical",
    status: "Investigating",
    category: "Credential theft",
    summary: "Active phishing and token theft activity targeted finance users and privileged workflows.",
    createdAt: "2026-11-12T08:15:00Z",
    updatedAt: "2026-11-13T01:20:00Z",
    owner: "A. Szymczak",
    confidence: 96,
    impactedSystems: ["Finance identity plane", "Mail gateway", "VPN edge", "Endpoint fleet"],
    relatedThreats: ["THR-421"],
    relatedEntities: ["ENT-91", "ENT-125", "ENT-302"],
    evidence: [
      "Token replay attempt across privileged sign-ins",
      "Malicious invoice-themed lure distribution",
      "Hotmail-style impersonation domain active in outbound mail",
    ],
    workflow: [
      { id: "wf-1", label: "Validate indicators", owner: "M. Kowalczyk", status: "Resolved", eta: "Resolved", progress: 100, notes: "IOC fidelity validated against endpoint and mail telemetry." },
      { id: "wf-2", label: "Contain access paths", owner: "A. Szymczak", status: "Active", eta: "00:45", progress: 74, notes: "Conditional access and MFA enforcement are being applied to affected roles." },
      { id: "wf-3", label: "Remediate identity trust", owner: "R. Okafor", status: "Queued", eta: "01:15", progress: 42, notes: "Reviewing token revocation and password reset scope for finance operators." },
      { id: "wf-4", label: "Executive briefing", owner: "L. Nowak", status: "Queued", eta: "02:00", progress: 16, notes: "Prepare stakeholder update with risk exposure and response status." },
    ],
    actions: [
      { id: "act-1", actor: "A. Szymczak", time: "08:15Z", type: "Case opened", summary: "Open response case after finance-user alerts and suspicious token replay." },
      { id: "act-2", actor: "M. Kowalczyk", time: "09:42Z", type: "Correlation", summary: "Mapped phishing and domain activity to the APT-29 campaign." },
      { id: "act-3", actor: "R. Okafor", time: "11:05Z", type: "Mitigation", summary: "Deployed conditional access and password reset lift for impacted identities." },
    ],
  },
  {
    id: "INC-1002",
    title: "Signed package abuse in release pipeline",
    severity: "High",
    status: "Contained",
    category: "Supply-chain risk",
    summary: "A signed and trusted software package path was flagged as a staging method for malicious execution.",
    createdAt: "2026-11-11T17:40:00Z",
    updatedAt: "2026-11-12T22:32:00Z",
    owner: "K. Mrozinski",
    confidence: 82,
    impactedSystems: ["Build pipeline", "Package verification", "Artifact registry", "Release environment"],
    relatedThreats: ["THR-612"],
    relatedEntities: ["ENT-214"],
    evidence: [
      "Signed artifact chain mismatch during validation",
      "Loader hash matched to malicious staging pattern",
      "Execution flow diverged from approved release lineage",
    ],
    workflow: [
      { id: "wf-5", label: "Artifact analysis", owner: "K. Mrozinski", status: "Resolved", eta: "Resolved", progress: 100, notes: "Package lineage and signed metadata were reviewed for tampering." },
      { id: "wf-6", label: "Registry quarantine", owner: "D. Kwiatkowski", status: "Resolved", eta: "Resolved", progress: 100, notes: "Malicious package was removed from the promotion queue and quarantined." },
      { id: "wf-7", label: "Release rollback", owner: "N. Rybak", status: "Active", eta: "00:30", progress: 68, notes: "Rollback of recent package variant is underway in the staging pipeline." },
    ],
    actions: [
      { id: "act-4", actor: "D. Kwiatkowski", time: "17:40Z", type: "Detection", summary: "Package signature drift triggered a supply-chain review." },
      { id: "act-5", actor: "K. Mrozinski", time: "18:12Z", type: "Escalation", summary: "Escalated to release engineering and endpoint verification for deeper reverse engineering." },
    ],
  },
  {
    id: "INC-1003",
    title: "Data exfiltration via archive transfer",
    severity: "Critical",
    status: "Open",
    category: "Exfiltration",
    summary: "Encrypted outbound data transfer exceeded expected threshold and matched historical exfiltration behavior.",
    createdAt: "2026-11-12T02:12:00Z",
    updatedAt: "2026-11-13T00:55:00Z",
    owner: "L. Nowak",
    confidence: 94,
    impactedSystems: ["Finance storage cluster", "User endpoint network", "Identity gateway", "Archive relay"],
    relatedThreats: ["THR-204"],
    relatedEntities: ["ENT-91", "ENT-214"],
    evidence: [
      "Large encrypted archive upload observed during off-hours",
      "Volume and destination pattern matched prior ransomware exfiltration model",
      "Firewall and EDR outputs aligned on suspicious network activity",
    ],
    workflow: [
      { id: "wf-8", label: "Traffic triage", owner: "L. Nowak", status: "Active", eta: "00:25", progress: 80, notes: "Analyst is narrowing the cluster to the exact destination path and loss window." },
      { id: "wf-9", label: "Contain network egress", owner: "M. Lis", status: "Queued", eta: "00:55", progress: 25, notes: "Block rules and sinkholing options are being reviewed for safe execution." },
      { id: "wf-10", label: "Evidence preservation", owner: "E. Wrona", status: "Queued", eta: "01:10", progress: 33, notes: "Volumetric network logs and endpoint traces are being sealed for forensics." },
    ],
    actions: [
      { id: "act-6", actor: "L. Nowak", time: "02:12Z", type: "Detection", summary: "Triggered alert for abnormal archive upload pattern and egress burst." },
      { id: "act-7", actor: "M. Lis", time: "02:24Z", type: "Blocking", summary: "Network policy review initiated to stop suspicious outbound transfer path." },
    ],
  },
];

export const integrationConnections: IntegrationConnection[] = [
  {
    id: "INT-01",
    name: "Splunk Enterprise",
    type: "SIEM",
    status: "Connected",
    latency: "132ms",
    owner: "SOC Operations",
    endpoint: "https://siem.internal.example",
    lastSync: "02:41 UTC",
    metadata: ["Correlation rules", "Risk score feed", "Indexed telemetry"],
  },
  {
    id: "INT-02",
    name: "Microsoft Entra ID",
    type: "Identity",
    status: "Healthy",
    latency: "94ms",
    owner: "IAM",
    endpoint: "https://login.microsoftonline.com",
    lastSync: "02:38 UTC",
    metadata: ["Identity graph", "Conditional access", "Risk detections"],
  },
  {
    id: "INT-03",
    name: "MISP Community",
    type: "Threat Intel",
    status: "Connected",
    latency: "210ms",
    owner: "Threat Intel",
    endpoint: "https://misp.internal.example",
    lastSync: "02:19 UTC",
    metadata: ["IOC sync", "TLP amber", "Campaign enrichment"],
  },
  {
    id: "INT-04",
    name: "ServiceNow",
    type: "Ticketing",
    status: "Pending",
    latency: "—",
    owner: "ITSM",
    endpoint: "https://servicenow.internal.example",
    lastSync: "Awaiting approval",
    metadata: ["Incident tickets", "Change approvals", "Escalation orchestration"],
  },
  {
    id: "INT-05",
    name: "AWS Security Hub",
    type: "Cloud",
    status: "Healthy",
    latency: "156ms",
    owner: "Cloud Security",
    endpoint: "https://securityhub.us-east-1.amazonaws.com",
    lastSync: "02:36 UTC",
    metadata: ["GuardDuty sync", "Config events", "Cloud posture"],
  },
  {
    id: "INT-06",
    name: "TheHive / Cortex",
    type: "SOAR",
    status: "Offline",
    latency: "—",
    owner: "IR Engineering",
    endpoint: "https://thehive.internal.example",
    lastSync: "17 mins ago",
    metadata: ["Case automation", "Playbook execution", "Triage routing"],
  },
];

export function getGraphQLDashboardPayload(section: string = "overview", id?: string | null) {
  const snapshot = getDashboardSnapshot(section);
  const selectedThreat = id ? snapshot.threats.find((item) => item.id === id) ?? null : null;
  const selectedEntity = id ? snapshot.entities.find((item) => item.id === id) ?? null : null;
  const selectedAlert = id ? snapshot.alerts.find((item) => item.id === id) ?? null : null;
  const selectedIncident = id ? snapshot.incidents.find((item) => item.id === id) ?? null : null;

  return {
    dashboard: {
      section,
      generatedAt: new Date().toISOString(),
      status: "live",
      summary: {
        openIndicators: snapshot.stats[0]?.value ?? "2,418",
        criticalCases: snapshot.stats[2]?.value ?? "19",
        detectionCoverage: snapshot.stats[3]?.value ?? "91%",
        activeCollectors: 27,
      },
      metrics: snapshot.stats,
      detections: snapshot.detection,
      timeline: snapshot.events,
      threats: snapshot.threats,
      entities: snapshot.entities,
      investigations: snapshot.investigations,
      alerts: snapshot.alerts,
      incidents: snapshot.incidents,
      integrations: snapshot.integrations,
      selected: selectedThreat ?? selectedEntity ?? selectedAlert ?? selectedIncident,
      selectedId: id ?? null,
      graph: {
        nodes: [
          ...snapshot.threats.slice(0, 3).map((item, index) => ({
            id: item.id,
            kind: "threat",
            label: item.title,
            severity: item.severity,
            x: 80 + (index % 3) * 180,
            y: 80 + Math.floor(index / 3) * 120,
          })),
          ...snapshot.entities.slice(0, 3).map((item, index) => ({
            id: item.id,
            kind: "entity",
            label: item.value,
            severity: item.risk,
            x: 120 + (index % 3) * 180,
            y: 180 + Math.floor(index / 3) * 120,
          })),
        ],
        edges: [
          ["THR-421", "ENT-91"],
          ["THR-421", "ENT-125"],
          ["THR-612", "ENT-214"],
          ["ALT-180", "ENT-91"],
        ],
      },
    },
  };
}

export function getSeverityTone(severity: string): string {
  const tones: Record<string, string> = {
    Critical: "border-red-500/40 bg-red-500/10 text-red-200",
    High: "border-amber-500/40 bg-amber-500/10 text-amber-200",
    Medium: "border-cyan-500/40 bg-cyan-500/10 text-cyan-200",
    Low: "border-slate-500/40 bg-slate-500/10 text-slate-200",
  };

  return tones[severity] ?? "border-slate-500/30 bg-slate-500/10 text-slate-200";
}

export function getDashboardSnapshot(section: string = "overview"): DashboardSnapshot {
  const normalizedSection = (section || "overview") as DashboardSectionKey;

  return {
    section: normalizedSection,
    stats: overviewStats,
    detection: detectionBars,
    events: recentEvents,
    threats: threatData,
    entities: entityData,
    investigations: investigationData,
    alerts: alertData,
    incidents: incidentData,
    integrations: integrationConnections,
  };
}

function normalizeDashboardPayload(payload: Partial<DashboardSnapshot> | null | undefined, fallbackSection: string): DashboardSnapshot {
  const fallback = getDashboardSnapshot(fallbackSection);

  return {
    ...fallback,
    ...(payload ?? {}),
    section: (payload?.section ?? fallbackSection ?? "overview") as DashboardSectionKey,
    stats: payload?.stats ?? fallback.stats,
    detection: payload?.detection ?? fallback.detection,
    events: payload?.events ?? fallback.events,
    threats: payload?.threats ?? fallback.threats,
    entities: payload?.entities ?? fallback.entities,
    investigations: payload?.investigations ?? fallback.investigations,
    alerts: payload?.alerts ?? fallback.alerts,
    incidents: payload?.incidents ?? fallback.incidents,
    integrations: payload?.integrations ?? fallback.integrations,
  };
}

export async function fetchDashboardSnapshot(section: string = "overview", id?: string | null): Promise<DashboardSnapshot> {
  const normalizedSection = section || "overview";
  const apiBaseUrl = (process.env.SANCTUM_API_BASE_URL ?? process.env.NEXT_PUBLIC_SANCTUM_API_URL ?? "").replace(/\/$/, "");
  const useRealData = process.env.NEXT_PUBLIC_SANCTUM_USE_REAL_DATA !== "false" && Boolean(apiBaseUrl);

  if (!useRealData) {
    return getDashboardSnapshot(normalizedSection);
  }

  const authToken = process.env.SANCTUM_API_TOKEN ?? process.env.SANCTUM_API_KEY ?? "";
  const credentials = process.env.SANCTUM_API_KEY && !process.env.SANCTUM_API_TOKEN ? "X-API-Key" : "Authorization";

  const endpoints = [
    `${apiBaseUrl}/api/v1/dashboard`,
    `${apiBaseUrl}/api/dashboard`,
    `${apiBaseUrl}/api/v1/cti/dashboard`,
  ];

  for (const endpoint of endpoints) {
    try {
      const url = new URL(endpoint);
      url.searchParams.set("section", normalizedSection);
      if (id) {
        url.searchParams.set("id", id);
      }

      const response = await fetch(url.toString(), {
        cache: "no-store",
        headers: {
          Accept: "application/json",
          ...(authToken
            ? credentials === "Authorization"
              ? { Authorization: `Bearer ${authToken}` }
              : { "X-API-Key": authToken }
            : {}),
        },
      });

      if (!response.ok) {
        continue;
      }

      const payload = await response.json();
      const dashboardData = payload?.data?.dashboard ?? payload?.dashboard ?? payload;

      if (dashboardData && Array.isArray(dashboardData.threats)) {
        return normalizeDashboardPayload(dashboardData, normalizedSection);
      }
    } catch {
      continue;
    }
  }

  return getDashboardSnapshot(normalizedSection);
}
