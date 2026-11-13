import { getSeverityTone, type DashboardSnapshot } from "@/lib/dashboard-data";

export function OverviewSection({ snapshot }: { snapshot: DashboardSnapshot }) {
  return (
    <>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {snapshot.stats.map((item) => (
          <div key={item.label} className="metric-card rounded-2xl p-4">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.14em] text-slate-400">
              <span>{item.label}</span>
              <span className="text-[#9ee7d6]">{item.delta}</span>
            </div>
            <div className="mt-5 text-3xl font-semibold tracking-tight text-white">{item.value}</div>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="panel-surface rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="section-kicker">Threat landscape</div>
              <h2 className="mt-1 text-xl font-semibold text-white">Active detection categories</h2>
            </div>
            <a href="/threats" className="text-sm text-[#9ee7d6] hover:text-[#c9f8eb]">
              View all →
            </a>
          </div>

          <div className="space-y-4">
            {snapshot.detection.map((item) => (
              <div key={item.label}>
                <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                  <span>{item.label}</span>
                  <span className="text-white">{item.value}%</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#1de9b6] via-[#7fe7d4] to-[#47c4ff]"
                    style={{ width: `${item.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel-surface rounded-2xl p-5">
          <div className="mb-4 section-kicker">Priority entities</div>
          <div className="space-y-3">
            {snapshot.entities.slice(0, 4).map((entity) => (
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
        <div className="panel-surface rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="section-kicker">Analyst notes</div>
              <h2 className="mt-1 text-xl font-semibold text-white">Recent operational events</h2>
            </div>
            <div className="rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-slate-300">24h</div>
          </div>

          <div className="space-y-4">
            {snapshot.events.map((item) => (
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

        <div className="panel-surface rounded-2xl p-5">
          <div className="mb-4 section-kicker">System summary</div>
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
  );
}

export function ThreatsSection({ snapshot }: { snapshot: DashboardSnapshot }) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Threat intelligence</div>
          <h2 className="mt-1 text-xl font-semibold text-white">Current threat tracking</h2>
        </div>
        <a href="/" className="text-sm text-[#8feccc] hover:text-[#b7f7e6]">
          Back to overview
        </a>
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
            {snapshot.threats.map((threat) => (
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
  );
}

export function EntitiesSection({ snapshot }: { snapshot: DashboardSnapshot }) {
  return (
    <section className="grid gap-5 md:grid-cols-2">
      {snapshot.entities.map((entity) => (
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
  );
}

export function InvestigationsSection({ snapshot }: { snapshot: DashboardSnapshot }) {
  return (
    <section className="grid gap-5 xl:grid-cols-2">
      {snapshot.investigations.map((item) => (
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
  );
}

export function AlertsSection({ snapshot }: { snapshot: DashboardSnapshot }) {
  return (
    <section className="grid gap-5 md:grid-cols-2">
      {snapshot.alerts.map((alert) => (
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
  );
}
