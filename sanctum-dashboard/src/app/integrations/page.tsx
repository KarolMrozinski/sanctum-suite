import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function IntegrationsPage() {
  const snapshot = getDashboardSnapshot("integrations");

  return (
    <DashboardShell section="integrations">
      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel-surface rounded-3xl p-5">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Production integrations</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Connected operational fabric</h2>
            </div>
            <div className="rounded-full border border-[#7ef7d3]/30 bg-[#101d1a] px-3 py-1.5 text-[10px] uppercase tracking-[0.18em] text-[#9ee7d6]">
              6 active
            </div>
          </div>

          <div className="grid gap-4">
            {snapshot.integrations.map((integration) => (
              <div key={integration.id} className="rounded-2xl border border-slate-800 bg-[#0d1419] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{integration.id}</div>
                    <div className="mt-1 text-lg font-semibold text-white">{integration.name}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-slate-700 bg-[#111922] px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
                      {integration.type}
                    </span>
                    <span className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${
                      integration.status === "Connected" || integration.status === "Healthy"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                        : integration.status === "Pending"
                          ? "border-amber-500/30 bg-amber-500/10 text-amber-200"
                          : "border-rose-500/30 bg-rose-500/10 text-rose-200"
                    }`}>
                      {integration.status}
                    </span>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-slate-800 bg-[#0c1217] p-3">
                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Latency</div>
                    <div className="mt-2 text-base font-medium text-white">{integration.latency}</div>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-[#0c1217] p-3">
                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Owner</div>
                    <div className="mt-2 text-base font-medium text-white">{integration.owner}</div>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-[#0c1217] p-3">
                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Last sync</div>
                    <div className="mt-2 text-base font-medium text-white">{integration.lastSync}</div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {integration.metadata.map((item) => (
                    <span key={item} className="rounded-full border border-slate-700 bg-[#111a21] px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
                      {item}
                    </span>
                  ))}
                </div>

                <div className="mt-4 text-sm text-slate-400">Endpoint: {integration.endpoint}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <div className="panel-surface rounded-3xl p-5">
            <div className="mb-4 text-[10px] uppercase tracking-[0.2em] text-slate-400">Integration roadmap</div>
            <div className="space-y-4">
              {[
                { label: "AI orchestration", detail: "Agent-to-agent workflows and context sync" },
                { label: "External CTI feeds", detail: "MISP, OTX and custom intel sources" },
                { label: "Case management", detail: "Bi-directional sync with ticketing ecosystems" },
                { label: "Cloud posture data", detail: "Kubernetes and cloud-native telemetry" },
              ].map((item) => (
                <div key={item.label} className="rounded-2xl border border-slate-800 bg-[#0d1419] p-3.5">
                  <div className="text-sm font-medium text-white">{item.label}</div>
                  <div className="mt-1 text-sm text-slate-400">{item.detail}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel-surface rounded-3xl p-5">
            <div className="mb-4 text-[10px] uppercase tracking-[0.2em] text-slate-400">Deployment status</div>
            <div className="space-y-3 text-sm text-slate-300">
              <div className="flex items-center justify-between">
                <span>API readiness</span>
                <span className="text-[#9ee7d6]">Production-ready adapter</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Auth model</span>
                <span className="text-[#9ee7d6]">Token + mTLS</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Sync mode</span>
                <span className="text-[#9ee7d6]">Near real-time</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </DashboardShell>
  );
}
