export type DashboardSectionKey = "overview" | "threats" | "entities" | "investigations" | "alerts";

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
  timeline: InvestigationTimelineEvent[];
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
};

export type DashboardNavigationItem = {
  id: DashboardSectionKey;
  label: string;
  href: string;
  count: string;
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
};

export const dashboardNavigation: DashboardNavigationItem[] = [
  { id: "overview", label: "Overview", href: "/", count: "12" },
  { id: "threats", label: "Threats", href: "/threats", count: "36" },
  { id: "entities", label: "Entities", href: "/entities", count: "64" },
  { id: "investigations", label: "Investigations", href: "/investigations", count: "08" },
  { id: "alerts", label: "Alerts", href: "/alerts", count: "19" },
];

export const overviewStats: OverviewStat[] = [
  { label: "Open indicators", value: "2,418", delta: "+18.4%" },
  { label: "Malware families", value: "84", delta: "+6" },
  { label: "Critical cases", value: "19", delta: "+3" },
  { label: "Detection coverage", value: "91%", delta: "+7.2%" },
];

export const detectionBars: DetectionBar[] = [
  { label: "Credential theft", value: 82 },
  { label: "Phishing", value: 66 },
  { label: "Supply chain", value: 54 },
  { label: "Ransomware", value: 76 },
  { label: "Malware delivery", value: 49 },
];

export const recentEvents: RecentEvent[] = [
  { time: "08:10", title: "IP cluster pivot observed", detail: "Three blocked hosts matched the same TTP profile." },
  { time: "09:35", title: "Mail relay anomaly", detail: "Outbound campaigns shifted to a new domain family." },
  { time: "12:20", title: "New IOC ingested", detail: "Indicators mapped to an active intrusion set in EU-CENTRAL." },
  { time: "15:05", title: "Case synchronized", detail: "Analyst workflow and collector policy were re-linked." },
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
  },
];

export const entityData: Entity[] = [
  { id: "ENT-91", type: "IPv4", value: "45.77.124.17", risk: "Critical", firstSeen: "2026-11-11", tags: ["C2", "Proxy", "Malware"], status: "Observed", description: "Known command-and-control endpoint tied to a malicious beaconing cluster." },
  { id: "ENT-125", type: "Domain", value: "secure-ops-update[.]cloud", risk: "High", firstSeen: "2026-11-09", tags: ["Phishing", "Redirect"], status: "Monitored", description: "Lookalike domain impersonating trusted operational communication resources." },
  { id: "ENT-214", type: "File hash", value: "bfe6ab18f7c1...", risk: "Medium", firstSeen: "2026-11-08", tags: ["Loader", "Signed"], status: "Contained", description: "Signed loader sample detected in a restricted software delivery pipeline." },
  { id: "ENT-302", type: "Email", value: "ops@northbridge.it", risk: "Low", firstSeen: "2026-11-06", tags: ["Compromised", "Target"], status: "Observed", description: "Targeted email address mapped to a spear-phishing campaign footprint." },
];

export const investigationData: Investigation[] = [
  { id: "INV-03", name: "Credential theft on finance users", owner: "A. Szymczak", progress: 74, priority: "P1", stage: "Containment plan review", updated: "12 mins ago", status: "In progress", timeline: [
    { id: "evt-1", type: "Created", time: "08:15", description: "Case opened after suspicious sign-in alerts across finance workloads." },
    { id: "evt-2", type: "Analysis", time: "09:42", description: "Analysts correlated the activity with a known credential phishing theme." },
    { id: "evt-3", type: "Mitigation", time: "11:05", description: "Conditional access rules and MFA enforcement were deployed for affected users." },
  ] },
  { id: "INV-11", name: "Suspicious package in release pipeline", owner: "K. Mrozinski", progress: 52, priority: "P1", stage: "Binary validation", updated: "28 mins ago", status: "Monitoring", timeline: [
    { id: "evt-4", type: "Detection", time: "07:48", description: "The package pipeline triggered a hash match for a known malware staging pattern." },
    { id: "evt-5", type: "Review", time: "10:20", description: "Release artifacts are being unpacked and compared against signed provenance checks." },
  ] },
  { id: "INV-22", name: "Abnormal outbound traffic cluster", owner: "L. Nowak", progress: 86, priority: "P2", stage: "Case packaging", updated: "46 mins ago", status: "In progress", timeline: [
    { id: "evt-6", type: "Detection", time: "06:30", description: "Anomalous egress from a cluster of endpoints exceeded the detection threshold." },
    { id: "evt-7", type: "Correlation", time: "08:05", description: "Traffic matched a historical data exfiltration signature in the same region." },
  ] },
  { id: "INV-47", name: "Executive phishing lures", owner: "J. Kowalski", progress: 31, priority: "P3", stage: "Triage", updated: "1 hour ago", status: "Monitoring", timeline: [
    { id: "evt-8", type: "Intake", time: "05:10", description: "Executive-targeted phishing lure was reported by a user on the help desk." },
    { id: "evt-9", type: "Triage", time: "06:40", description: "The subject lines and attachments are being compared with active impersonation sets." },
  ] },
];

export const alertData: Alert[] = [
  { id: "ALT-180", title: "New beacon pattern observed", severity: "Critical", source: "EDR", observed: "02:41 UTC", status: "Open", category: "Beaconing", description: "Endpoint beaconing behavior is consistent with known C2 communications and a rotated domain cluster.", timestamp: "02:41 UTC" },
  { id: "ALT-181", title: "Suspicious PowerShell invoked on workstation", severity: "High", source: "Windows Defender", observed: "02:21 UTC", status: "Investigating", category: "Execution", description: "PowerShell execution used obfuscated flags and a remote script block pattern associated with living-off-the-land activity.", timestamp: "02:21 UTC" },
  { id: "ALT-182", title: "Lateral movement from finance VLAN", severity: "Medium", source: "Firewall", observed: "01:58 UTC", status: "Open", category: "Lateral movement", description: "Repeated authentication attempts were observed between workstations in a critical segment during off-hours.", timestamp: "01:58 UTC" },
  { id: "ALT-183", title: "Unusual admin password reset", severity: "Low", source: "IAM", observed: "00:48 UTC", status: "Dismissed", category: "Identity", description: "Password reset was reviewed and attributed to a known internal maintenance task.", timestamp: "00:48 UTC" },
];

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
  };
}
