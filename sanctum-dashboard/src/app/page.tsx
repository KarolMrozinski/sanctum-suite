"use client";

import { useMemo, useState } from "react";

type SectionKey = "overview" | "threats" | "entities" | "investigations" | "alerts";

type Threat = {
  id: string;
  title: string;
  actor: string;
  severity: "Critical" | "High" | "Medium" | "Low";
  source: string;
  status: "Active" | "Monitoring" | "Contained";
  confidence: number;
};

type Entity = {
  id: string;
  type: string;
  value: string;
  risk: "Critical" | "High" | "Medium" | "Low";
  firstSeen: string;
  tags: string[];
};

type Investigation = {
  id: string;
  name: string;
  owner: string;
  progress: number;
  priority: "P1" | "P2" | "P3";
  stage: string;
  updated: string;
};

type Alert = {
  id: string;
  title: string;
  severity: "Critical" | "High" | "Medium" | "Low";
  source: string;
  observed: string;
  status: "Open" | "Dismissed" | "Investigating";
};

const navItems = [
  { id: "overview", label: "Overview", count: "12" },
  { id: "threats", label: "Threats", count: "36" },
  { id: "entities", label: "Entities", count: "64" },
  { id: "investigations", label: "Investigations", count: "08" },
  { id: "alerts", label: "Alerts", count: "19" },
];

const threatData: Threat[] = [
  { id: "THR-421", title: "Credential harvesting campaign", actor: "APT-29", severity: "Critical", source: "Mail gateway", status: "Active", confidence: 96 },
  { id: "THR-612", title: "Malware staging via signed package", actor: "ShadowPad", severity: "High", source: "Software supply chain", status: "Monitoring", confidence: 82 },
  { id: "THR-118", title: "Phishing redirect chain", actor: "Storm-182", severity: "Medium", source: "Web analytics", status: "Contained", confidence: 71 },
  { id: "THR-204", title: "Ransomware exfiltration indicator", actor: "BlackCat", severity: "Critical", source: "Endpoint telemetry", status: "Active", confidence: 94 },
];

const entityData: Entity[] = [
  { id: "ENT-91", type: "IPv4", value: "45.77.124.17", risk: "Critical", firstSeen: "2026-11-11", tags: ["C2", "Proxy", "Malware"] },
  { id: "ENT-125", type: "Domain", value: "secure-ops-update[.]cloud", risk: "High", firstSeen: "2026-11-09", tags: ["Phishing", "Redirect"] },
  { id: "ENT-214", type: "File hash", value: "bfe6ab18f7c1...", risk: "Medium", firstSeen: "2026-11-08", tags: ["Loader", "Signed"] },
  { id: "ENT-302", type: "Email", value: "ops@northbridge.it", risk: "Low", firstSeen: "2026-11-06", tags: ["Compromised", "Target"] },
];

const investigationData: Investigation[] = [
  { id: "INV-03", name: "Credential theft on finance users", owner: "A. Szymczak", progress: 74, priority: "P1", stage: "Containment plan review", updated: "12 mins ago" },
  { id: "INV-11", name: "Suspicious package in release pipeline", owner: "K. Mrozinski", progress: 52, priority: "P1", stage: "Binary validation", updated: "28 mins ago" },
  { id: "INV-22", name: "Abnormal outbound traffic cluster", owner: "L. Nowak", progress: 86, priority: "P2", stage: "Case packaging", updated: "46 mins ago" },
  { id: "INV-47", name: "Executive phishing lures", owner: "J. Kowalski", progress: 31, priority: "P3", stage: "Triage", updated: "1 hour ago" },
];

const alertData: Alert[] = [
  { id: "ALT-180", title: "New beacon pattern observed", severity: "Critical", source: "EDR", observed: "02:41 UTC", status: "Open" },
  { id: "ALT-181", title: "Suspicious PowerShell invoked on workstation", severity: "High", source: "Windows Defender", observed: "02:21 UTC", status: "Investigating" },
  { id: "ALT-182", title: "Lateral movement from finance VLAN", severity: "Medium", source: "Firewall", observed: "01:58 UTC", status: "Open" },
  { id: "ALT-183", title: "Unusual admin password reset", severity: "Low", source: "IAM", observed: "00:48 UTC", status: "Dismissed" },
];

const overviewStats = [
  { label: "Open indicators", value: "2,418", delta: "+18.4%" },
  { label: "Malware families", value: "84", delta: "+6" },
  { label: "Critical cases", value: "19", delta: "+3" },
  { label: "Detection coverage", value: "91%", delta: "+7.2%" },
];

const detectionBars = [
  { label: "Credential theft", value: 82 },
  { label: "Phishing", value: 66 },
  { label: "Supply chain", value: 54 },
  { label: "Ransomware", value: 76 },
  { label: "Malware delivery", value: 49 },
];

const recentEvents = [
  { time: "08:10", title: "IP cluster pivot observed", detail: "Three blocked hosts matched the same TTP profile." },
  { time: "09:35", title: "Mail relay anomaly", detail: "Outbound campaigns shifted to a new domain family." },
  { time: "12:20", title: "New IOC ingested", detail: "Indicators mapped to an active intrusion set in EU-CENTRAL." },
  { time: "15:05", title: "Case synchronized", detail: "Analyst workflow and collector policy were re-linked." },
];

function getSeverityTone(severity: string) {
  const tones: Record<string, string> = {
    Critical: "border-red-500/40 bg-red-500/10 text-red-200",
    High: "border-amber-500/40 bg-amber-500/10 text-amber-200",
    Medium: "border-cyan-500/40 bg-cyan-500/10 text-cyan-200",
    Low: "border-slate-500/40 bg-slate-500/10 text-slate-200",
  };
  return tones[severity] ?? "border-slate-500/30 bg-slate-500/10 text-slate-200";
}

export default function HomePage() {
  const [activeSection, setActiveSection] = useState<SectionKey>("overview");

  const sectionTitle = useMemo(() => {
    switch (activeSection) {
      case "threats":
        return "Threat landscape";
      case "entities":
        return "Entities & indicators";
      case "investigations":
        return "Investigations";
      case "alerts":
        return "Alerts";
      default:
        return "Operational overview";
    }
  }, [activeSection]);

  return (
    <main className="min-h-screen bg-[#071a28] text-slate-100">
      <div className="flex min-h-screen">
        <aside className="w-[280px] border-r border-slate-800/90 bg-[#0b1622] px-5 py-6">
          <div className="flex items-center gap-3 px-2 pb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#36d4ab]/30 bg-[#1de9b6]/10 text-sm font-bold text-[#7ef7d5] shadow-[0_0_24px_rgba(29,233,182,0.25)]">
              S
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-[#7fe7d4]">KarolMrozinski</div>
              <div className="text-lg font-semibold tracking-wide text-white">SANCTUM-SUITE</div>
            </div>
          </div>

          <div className="mb-5 rounded-xl border border-[#1de9b6]/20 bg-[#122233] px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-[#8ae9cf]">
            OpenCTI-inspired workspace
          </div>

          <nav className="space-y-2" aria-label="Main navigation">
            {navItems.map(({ id, label, count }) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveSection(id as SectionKey)}
                className={[
                  "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition",
                  activeSection === id
                    ? "border-[#1de9b6]/30 bg-[#132b3a] text-white shadow-[inset_0_0_0_1px_rgba(29,233,182,0.18)]"
                    : "border-transparent bg-transparent text-slate-300 hover:border-slate-700 hover:bg-slate-900/60 hover:text-white",
                ].join(" ")}
              >
                <span>{label}</span>
                <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-0.5 text-[10px] font-medium text-slate-200">
                  {count}
                </span>
              </button>
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-slate-800 bg-[#0d1a2c] p-4">
            <div className="mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-slate-400">
              <span>Signal</span>
              <span className="text-[#8ae9cf]">Live</span>
            </div>
            <div className="space-y-3">
              <div>
                <div className="mb-1 flex justify-between text-xs text-slate-300">
                  <span>Threat score</span>
                  <span className="text-white">87/100</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full w-[87%] rounded-full bg-gradient-to-r from-[#1de9b6] to-[#6dd7ff]" />
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Analyst queue</span>
                <span className="font-medium text-[#8ae9cf]">06 pending</span>
              </div>
            </div>
          </div>
        </aside>

        <div className="flex-1">
          <header className="flex items-center justify-between border-b border-slate-800 bg-[#091c2b]/80 px-6 py-4 backdrop-blur-sm">
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Threat intelligence workspace</div>
              <h1 className="mt-1 text-2xl font-semibold text-white">{sectionTitle}</h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-slate-700 bg-[#0d1d2d] px-3 py-1.5 text-xs text-slate-300">02:42 UTC</div>
              <button type="button" className="rounded-full border border-[#1de9b6]/30 bg-[#113d35] px-4 py-2 text-sm font-medium text-[#8feccc] transition hover:bg-[#174c42]">
                Run sweep
              </button>
            </div>
          </header>

          <main className="space-y-6 p-6">
            {activeSection === "overview" && (
              <>
                <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  {overviewStats.map((item) => (
                    <div key={item.label} className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-4 shadow-[0_0_0_1px_rgba(148,163,184,0.06)]">
                      <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-slate-400">
                        <span>{item.label}</span>
                        <span className="text-[#8ae9cf]">{item.delta}</span>
                      </div>
                      <div className="mt-5 text-3xl font-semibold text-white">{item.value}</div>
                    </div>
                  ))}
                </section>

                <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                  <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Threat landscape</div>
                        <h2 className="mt-1 text-xl font-semibold text-white">Active detection categories</h2>
                      </div>
                      <button type="button" onClick={() => setActiveSection("threats")} className="text-sm text-[#8feccc] hover:text-[#b7f7e6]">
                        View all →
                      </button>
                    </div>

                    <div className="space-y-4">
                      {detectionBars.map((item) => (
                        <div key={item.label}>
                          <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                            <span>{item.label}</span>
                            <span className="text-white">{item.value}%</span>
                          </div>
                          <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                            <div className="h-full rounded-full bg-gradient-to-r from-[#1de9b6] via-[#7fe7d4] to-[#47c4ff]" style={{ width: `${item.value}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                    <div className="mb-4 text-[10px] uppercase tracking-[0.2em] text-slate-400">Priority entities</div>
                    <div className="space-y-3">
                      {entityData.slice(0, 4).map((entity) => (
                        <div key={entity.id} className="flex items-center justify-between rounded-xl border border-slate-800 bg-[#0f2237] px-3 py-3">
                          <div>
                            <div className="text-sm font-medium text-white">{entity.value}</div>
                            <div className="text-xs text-slate-400">{entity.type}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-semibold text-[#8feccc]">{entity.risk}</div>
                            <div className="text-[10px] uppercase tracking-[0.1em] text-slate-400">{entity.id}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>

                <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                  <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Analyst notes</div>
                        <h2 className="mt-1 text-xl font-semibold text-white">Recent operational events</h2>
                      </div>
                      <div className="rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-slate-300">24h</div>
                    </div>

                    <div className="space-y-4">
                      {recentEvents.map((item) => (
                        <div key={item.time} className="flex gap-4 rounded-xl border border-slate-800 bg-[#0f2237] p-3">
                          <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-full border border-[#1de9b6]/30 bg-[#113d35] text-[10px] font-medium text-[#8feccc]">
                            {item.time.split(":")[0]}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-sm font-medium text-white">{item.title}</div>
                              <div className="text-[10px] uppercase tracking-[0.12em] text-slate-400">{item.time}</div>
                            </div>
                            <p className="mt-2 text-sm leading-6 text-slate-400">{item.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                    <div className="mb-4 text-[10px] uppercase tracking-[0.2em] text-slate-400">System summary</div>
                    <div className="space-y-4">
                      <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
                        <div className="text-sm text-slate-400">Incident readiness</div>
                        <div className="mt-2 text-3xl font-semibold text-[#8feccc]">94%</div>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
                        <div className="text-sm text-slate-400">Pipeline sync</div>
                        <div className="mt-2 text-3xl font-semibold text-white">4.8s</div>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
                        <div className="text-sm text-slate-400">Connected collectors</div>
                        <div className="mt-2 text-3xl font-semibold text-white">27</div>
                      </div>
                    </div>
                  </div>
                </section>
              </>
            )}

            {activeSection === "threats" && (
              <section className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Threat intelligence</div>
                    <h2 className="mt-1 text-xl font-semibold text-white">Current threat tracking</h2>
                  </div>
                  <button type="button" onClick={() => setActiveSection("overview")} className="text-sm text-[#8feccc] hover:text-[#b7f7e6]">
                    Back to overview
                  </button>
                </div>

                <div className="overflow-hidden rounded-xl border border-slate-800">
                  <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                    <thead className="bg-[#0f2237] text-slate-300">
                      <tr>
                        <th className="px-4 py-3 font-medium">ID</th>
                        <th className="px-4 py-3 font-medium">Threat</th>
                        <th className="px-4 py-3 font-medium">Actor</th>
                        <th className="px-4 py-3 font-medium">Source</th>
                        <th className="px-4 py-3 font-medium">Severity</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 bg-[#0d1b2b]">
                      {threatData.map((threat) => (
                        <tr key={threat.id} className="align-middle hover:bg-[#102234]">
                          <td className="px-4 py-3 text-slate-300">{threat.id}</td>
                          <td className="px-4 py-3">
                            <div className="font-medium text-white">{threat.title}</div>
                            <div className="text-xs text-slate-400">Confidence {threat.confidence}%</div>
                          </td>
                          <td className="px-4 py-3 text-slate-300">{threat.actor}</td>
                          <td className="px-4 py-3 text-slate-300">{threat.source}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(threat.severity)}`}>
                              {threat.severity}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-300">{threat.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {activeSection === "entities" && (
              <section className="grid gap-5 md:grid-cols-2">
                {entityData.map((entity) => (
                  <div key={entity.id} className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{entity.type}</div>
                        <div className="mt-1 text-xl font-semibold text-white">{entity.value}</div>
                      </div>
                      <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(entity.risk)}`}>
                        {entity.risk}
                      </span>
                    </div>
                    <div className="space-y-3 text-sm text-slate-300">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Entity ID</span>
                        <span>{entity.id}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">First seen</span>
                        <span>{entity.firstSeen}</span>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {entity.tags.map((tag) => (
                        <span key={tag} className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-300">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </section>
            )}

            {activeSection === "investigations" && (
              <section className="grid gap-5 xl:grid-cols-2">
                {investigationData.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{item.id}</div>
                      <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-300">
                        {item.priority}
                      </span>
                    </div>
                    <h3 className="text-xl font-semibold text-white">{item.name}</h3>
                    <div className="mt-3 flex items-center justify-between text-sm text-slate-300">
                      <span>Owner</span>
                      <span>{item.owner}</span>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-sm text-slate-300">
                      <span>Stage</span>
                      <span>{item.stage}</span>
                    </div>
                    <div className="mt-4">
                      <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.14em] text-slate-400">
                        <span>Progress</span>
                        <span>{item.progress}%</span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                        <div className="h-full rounded-full bg-gradient-to-r from-[#1de9b6] to-[#6dd7ff]" style={{ width: `${item.progress}%` }} />
                      </div>
                    </div>
                    <div className="mt-4 text-xs uppercase tracking-[0.14em] text-slate-400">Updated {item.updated}</div>
                  </div>
                ))}
              </section>
            )}

            {activeSection === "alerts" && (
              <section className="grid gap-5 md:grid-cols-2">
                {alertData.map((alert) => (
                  <div key={alert.id} className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{alert.id}</div>
                      <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(alert.severity)}`}>
                        {alert.severity}
                      </span>
                    </div>
                    <h3 className="text-xl font-semibold text-white">{alert.title}</h3>
                    <div className="mt-4 space-y-2 text-sm text-slate-300">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Source</span>
                        <span>{alert.source}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Observed</span>
                        <span>{alert.observed}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Status</span>
                        <span>{alert.status}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </section>
            )}
          </main>
        </div>
      </div>
    </main>
  );
}
