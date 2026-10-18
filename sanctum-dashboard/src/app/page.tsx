import Link from "next/link";
import LeadForm from "@/components/LeadForm";

const highlights = [
  ["Security operations", "Audit orchestration, telemetry correlation, detection rules, and report generation."],
  ["AI safety", "Prompt inspection, policy guardrails, and anomaly analysis for AI workflows."],
  ["Resilience tooling", "Compliance helpers, remediation playbooks, and infrastructure security modules."],
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#0f172a_0%,_#020817_52%,_#01050d_100%)] text-slate-100">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10">
        <Link href="/" className="flex items-center gap-3" aria-label="SANCTUM-SUITE home">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-500/10 text-lg">S</span>
          <span>
            <span className="block text-lg font-semibold tracking-wide text-cyan-300">SANCTUM-SUITE</span>
            <span className="block text-[10px] uppercase tracking-[0.24em] text-slate-400">Security operations toolkit</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm text-slate-300 md:flex" aria-label="Main navigation">
          <Link href="/features" className="hover:text-cyan-300">Features</Link>
          <Link href="/about" className="hover:text-cyan-300">About</Link>
          <Link href="/docs" className="hover:text-cyan-300">Documentation</Link>
          <Link href="/pricing" className="hover:text-cyan-300">Pricing</Link>
          <Link href="/workbench" className="hover:text-cyan-300">Workbench</Link>
        </nav>
        <a href="#contact" className="rounded-full border border-cyan-500/50 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20">
          Contact sales
        </a>
      </header>

      <section className="mx-auto grid max-w-7xl gap-10 px-6 pb-20 pt-10 lg:grid-cols-[1.2fr_0.8fr] lg:px-10 lg:pt-20">
        <div>
          <div className="mb-6 inline-flex rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-cyan-200">
            Security engineering and resilience
          </div>
          <h1 className="max-w-2xl text-4xl font-black tracking-tight text-white md:text-6xl">
            Bring security workflows together with <span className="text-cyan-400">SANCTUM-SUITE</span>.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
            An extensible security toolkit for audit orchestration, AI safety experiments, compliance support, and operational reporting. Review capabilities and validate each module in your own environment.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <a href="#contact" className="rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300">Request a conversation</a>
            <Link href="/docs" className="rounded-full border border-slate-700 bg-slate-900/70 px-6 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white">Read the documentation</Link>
          </div>
          <p className="mt-5 max-w-xl text-xs leading-5 text-slate-500">
            Capabilities and deployment requirements vary by module. This site does not represent independent certification, guaranteed security outcomes, or an active service-level commitment.
          </p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5 shadow-2xl shadow-cyan-950/40">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">Toolkit overview</div>
            <h2 className="mt-3 text-2xl font-bold text-white">A modular view of security work</h2>
            <div className="mt-6 space-y-3">
              {highlights.map(([title, description]) => (
                <div key={title} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <h3 className="text-sm font-semibold text-cyan-200">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
                </div>
              ))}
            </div>
            <p className="mt-5 text-xs text-slate-500">Illustrative summary; not a live telemetry feed.</p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-16 lg:px-10">
        <div className="grid gap-6 md:grid-cols-3">
          {[
            ["/features", "Explore features", "See the capabilities described by the current codebase."],
            ["/workbench", "Open the workbench", "View the dashboard UI and its connection status."],
            ["/pricing", "Review commercial options", "Discuss evaluation and deployment requirements."],
          ].map(([href, title, description]) => (
            <Link key={href} href={href} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 transition hover:border-cyan-700">
              <h2 className="text-lg font-semibold text-white">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-400">{description}</p>
              <span className="mt-5 inline-block text-sm font-medium text-cyan-300">Learn more →</span>
            </Link>
          ))}
        </div>
      </section>

      <section id="contact" className="mx-auto max-w-7xl px-6 py-16 lg:px-10">
        <div className="grid gap-10 rounded-3xl border border-slate-800 bg-slate-900/80 p-7 md:grid-cols-[0.8fr_1.2fr] md:p-10">
          <div>
            <div className="text-xs uppercase tracking-[0.24em] text-cyan-300">Contact</div>
            <h2 className="mt-4 text-3xl font-bold text-white">Discuss an evaluation or deployment.</h2>
            <p className="mt-4 text-sm leading-6 text-slate-300">
              Tell us how you plan to evaluate the toolkit. Do not submit credentials, vulnerability details, or other sensitive security information through this form.
            </p>
          </div>
          <LeadForm />
        </div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-wrap justify-between gap-4 border-t border-slate-800 px-6 py-8 text-xs text-slate-500 lg:px-10">
        <span>© SANCTUM-SUITE. Source-available; usage governed by the repository license.</span>
        <div className="flex gap-5">
          <Link href="/privacy" className="hover:text-slate-300">Privacy</Link>
          <Link href="/docs" className="hover:text-slate-300">Docs</Link>
          <Link href="/pricing" className="hover:text-slate-300">Commercial options</Link>
        </div>
      </footer>
    </main>
  );
}
