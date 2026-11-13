import { DashboardFilters } from "@/components/dashboard/dashboard-filters";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { OverviewSection } from "@/components/dashboard/overview-section";
import { AlertFeed } from "@/components/dashboard/widgets/alert-feed";
import { EntityCard } from "@/components/dashboard/widgets/entity-card";
import { InvestigationTimeline } from "@/components/dashboard/widgets/investigation-timeline";
import { ThreatDetail } from "@/components/dashboard/widgets/threat-detail";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function HomePage() {
  const snapshot = getDashboardSnapshot("overview");

  const storyCards = [
    {
      title: "Czym jest Sanctum Suite",
      text: "To nowoczesne centrum cyber threat intelligence, które łączy obserwację zagrożeń, relacje między obiektami i workflow analityka w jednym miejscu.",
    },
    {
      title: "Po co zostało stworzone",
      text: "Aby skrócić czas od wykrycia do reakcji i umożliwić zespołom SOC szybkie rozróżnianie, kontekstualizację i wdrażanie działań naprawczych.",
    },
    {
      title: "Jak działa",
      text: "Środowisko zbiera sygnały, łączy je z entytami, scenariuszami i incydentami, a następnie prowadzi analityka przez priorytetyzację i kontynuację działań.",
    },
  ];

  return (
    <DashboardShell section="overview">
      <section className="panel-surface overflow-hidden rounded-[28px] border border-[#7ef7d3]/10 bg-[radial-gradient(circle_at_top_left,_rgba(126,247,211,0.18),_transparent_32%),linear-gradient(135deg,_rgba(9,14,20,0.96),_rgba(13,20,28,1))] p-6 shadow-[0_0_40px_rgba(27,48,58,0.42)]">
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr] xl:items-end">
          <div>
            <div className="mb-4 inline-flex items-center rounded-full border border-[#7ef7d3]/25 bg-[#0f1d1a] px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-[#9ee7d6]">
              Sanctum Suite release overview
            </div>
            <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white md:text-5xl">
              Cyber threat intelligence workspace built for faster signal-to-action decisions.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
              Sanctum Suite pomaga zespołom bezpieczeństwa monitorować, kojarzyć i rozwiązywać działania zagrażające organizacji — od obserwacji IOCs po pełen workflow analiz i reagowania.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button type="button" className="rounded-full border border-[#7ef7d3]/25 bg-[#102218] px-4 py-2 text-sm font-medium text-[#9ee7d6] transition hover:bg-[#163129]">
                Review live posture
              </button>
              <button type="button" className="rounded-full border border-slate-700 bg-[#0d1419] px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-600 hover:text-white">
                Open investigations
              </button>
            </div>
          </div>

          <div className="grid gap-3">
            {[
              { label: "Critical triage", value: "19" },
              { label: "Analyst action rate", value: "76%" },
              { label: "Threat coverage", value: "91%" },
            ].map((item) => (
              <div key={item.label} className="rounded-2xl border border-slate-800 bg-[#0b1116]/80 p-4">
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{item.label}</div>
                <div className="mt-2 text-3xl font-semibold text-white">{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {storyCards.map((card) => (
          <div key={card.title} className="panel-surface rounded-3xl p-5">
            <div className="mb-3 text-[10px] uppercase tracking-[0.2em] text-slate-400">Mission</div>
            <h2 className="text-lg font-semibold text-white">{card.title}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">{card.text}</p>
          </div>
        ))}
      </section>

      <DashboardFilters />

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
        <div className="panel-surface rounded-3xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Exec summary</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Mission posture</h2>
            </div>
            <div className="rounded-full border border-[#7ef7d3]/30 bg-[#0f1b1a] px-3 py-1 text-[10px] uppercase tracking-[0.18em] text-[#9ee7d6]">
              Live signal
            </div>
          </div>
          <OverviewSection snapshot={snapshot} />
        </div>

        <div className="panel-surface rounded-3xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Operations</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Operator notes</h2>
            </div>
          </div>
          <div className="space-y-4">
            {[
              { label: "Priority queue", value: "06 active cases", tone: "text-[#9ee7d6]" },
              { label: "Threat drift", value: "+18.4% vs last run", tone: "text-[#8ad8ff]" },
              { label: "Containment", value: "4 mitigations deployed", tone: "text-[#c7d2fe]" },
            ].map((item) => (
              <div key={item.label} className="rounded-2xl border border-slate-800 bg-[#0d1419] p-3.5">
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{item.label}</div>
                <div className={`mt-2 text-sm font-medium ${item.tone}`}>{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <ThreatDetail threat={snapshot.threats[0]} />
        <AlertFeed alerts={snapshot.alerts} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
        <div className="grid gap-5 md:grid-cols-2">
          {snapshot.entities.slice(0, 2).map((entity) => (
            <EntityCard key={entity.id} entity={entity} />
          ))}
        </div>
        <InvestigationTimeline investigation={snapshot.investigations[0]} />
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        {[
          { title: "Threat intelligence", value: "356", detail: "Indicators mapped to active adversary clusters" },
          { title: "Entity graph", value: "1.2K", detail: "Linked domains, hashes, identities and IP objects" },
          { title: "Case velocity", value: "09m 41s", detail: "Average time to detect and triage signals" },
        ].map((card) => (
          <div key={card.title} className="panel-surface rounded-3xl p-5">
            <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Performance</div>
            <div className="mt-4 text-3xl font-semibold text-white">{card.value}</div>
            <div className="mt-2 text-sm font-medium text-[#9ee7d6]">{card.title}</div>
            <div className="mt-3 text-sm text-slate-400">{card.detail}</div>
          </div>
        ))}
      </section>
    </DashboardShell>
  );
}
