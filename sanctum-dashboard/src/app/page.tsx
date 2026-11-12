import Link from "next/link";

const navigation = [
  { label: "Overview", count: "12", active: true },
  { label: "Threats", count: "36" },
  { label: "Entities", count: "64" },
  { label: "Cases", count: "08" },
  { label: "Observations", count: "19" },
  { label: "Settings", count: null },
];

const kpis = [
  { label: "Open indicators", value: "2,418", delta: "+18.4%" },
  { label: "Malware families", value: "84", delta: "+6" },
  { label: "Critical cases", value: "19", delta: "+3" },
  { label: "Detection coverage", value: "91%", delta: "+7.2%" },
];

const detections = [
  { name: "Credential theft", value: 82 },
  { name: "Phishing", value: 66 },
  { name: "Supply chain", value: 54 },
  { name: "Ransomware", value: 76 },
  { name: "Malware delivery", value: 49 },
];

const entities = [
  { name: "MCAP-417", score: "98", status: "High" },
  { name: "PKG-01/b", score: "94", status: "High" },
  { name: "CIR-2.7", score: "89", status: "Medium" },
  { name: "OPS-77", score: "76", status: "Low" },
];

const timeline = [
  { time: "08:10", title: "IP cluster pivot observed", detail: "3 blocked hosts matched the same TTP profile." },
  { time: "09:35", title: "Mail relay anomaly", detail: "Two outbound campaigns shifted to a new domain family." },
  { time: "12:20", title: "New IOC ingested", detail: "Indicators mapped to an active intrusion set in region EU-CENTRAL." },
  { time: "15:05", title: "Case update synchronized", detail: "Analyst workflow and collector policy were re-linked successfully." },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#071a28] text-slate-100">
      <div className="flex min-h-screen">
        <aside className="w-[280px] border-r border-slate-800/90 bg-[#0b1622] px-5 py-6">
          <div className="flex items-center gap-3 px-2 pb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#36d4ab]/30 bg-[#1de9b6]/10 text-sm font-bold text-[#7ef7d5] shadow-[0_0_24px_rgba(29,233,182,0.25)]">
              S
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-[#7fe7d4]">
                KarolMrozinski
              </div>
              <div className="text-lg font-semibold tracking-wide text-white">SANCTUM-SUITE</div>
            </div>
          </div>

          <div className="mb-5 rounded-xl border border-[#1de9b6]/20 bg-[#122233] px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-[#8ae9cf]">
            OpenCTI-inspired workspace
          </div>

          <nav className="space-y-2">
            {navigation.map(({ label, count, active }) => (
              <Link
                key={label}
                href="#"
                className={[
                  "flex items-center justify-between rounded-xl border px-3 py-2.5 text-sm transition",
                  active
                    ? "border-[#1de9b6]/30 bg-[#132b3a] text-white shadow-[inset_0_0_0_1px_rgba(29,233,182,0.18)]"
                    : "border-transparent bg-transparent text-slate-300 hover:border-slate-700 hover:bg-slate-900/60 hover:text-white",
                ].join(" ")}
              >
                <span>{label}</span>
                {count ? (
                  <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-0.5 text-[10px] font-medium text-slate-200">
                    {count}
                  </span>
                ) : null}
              </Link>
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
              <h1 className="mt-1 text-2xl font-semibold text-white">Operational overview</h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-slate-700 bg-[#0d1d2d] px-3 py-1.5 text-xs text-slate-300">
                02:42 UTC
              </div>
              <button className="rounded-full border border-[#1de9b6]/30 bg-[#113d35] px-4 py-2 text-sm font-medium text-[#8feccc] transition hover:bg-[#174c42]">
                Run sweep
              </button>
            </div>
          </header>

          <main className="space-y-6 p-6">
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {kpis.map((item) => (
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
                  <Link href="#" className="text-sm text-[#8feccc] hover:text-[#b7f7e6]">
                    View all →
                  </Link>
                </div>

                <div className="space-y-4">
                  {detections.map((item) => (
                    <div key={item.name}>
                      <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                        <span>{item.name}</span>
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

              <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
                <div className="mb-4 text-[10px] uppercase tracking-[0.2em] text-slate-400">Priority entities</div>
                <div className="space-y-3">
                  {entities.map((entity) => (
                    <div key={entity.name} className="flex items-center justify-between rounded-xl border border-slate-800 bg-[#0f2237] px-3 py-3">
                      <div>
                        <div className="text-sm font-medium text-white">{entity.name}</div>
                        <div className="text-xs text-slate-400">Confidence index</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-[#8feccc]">{entity.score}</div>
                        <div className="text-[10px] uppercase tracking-[0.1em] text-slate-400">{entity.status}</div>
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
                  <div className="rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-slate-300">
                    24h
                  </div>
                </div>

                <div className="space-y-4">
                  {timeline.map((item) => (
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
          </main>
        </div>
      </div>
    </main>
  );
}
