import Link from "next/link";

export const metadata = {
  title: "About | SANCTUM-SUITE",
  description: "About the SANCTUM-SUITE security engineering toolkit and its current scope.",
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-[#020817] px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-4xl">
        <Link href="/" className="text-sm text-cyan-300 hover:text-cyan-200">← SANCTUM-SUITE</Link>
        <p className="mt-12 text-xs uppercase tracking-[0.24em] text-cyan-300">About</p>
        <h1 className="mt-4 text-4xl font-black text-white md:text-5xl">A modular toolkit for security engineering.</h1>
        <p className="mt-6 text-lg leading-8 text-slate-300">
          SANCTUM-SUITE brings together Python modules for audit workflows, threat analysis, AI safety experiments, compliance support, reporting, and operations. It is intended to be evaluated and configured by experienced security teams—not treated as a substitute for security review or qualified professional judgment.
        </p>

        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {[
            ["Composable", "Use modules independently and integrate them into existing workflows."],
            ["Operator-controlled", "Run and validate components in environments where you have authorization."],
            ["Evaluation-first", "Verify the behavior, prerequisites, and limitations of each capability before production use."],
            ["Source available", "Access and use are subject to the restrictions in the repository license."],
          ].map(([heading, body]) => (
            <section key={heading} className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <h2 className="text-lg font-semibold text-white">{heading}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">{body}</p>
            </section>
          ))}
        </div>

        <aside className="mt-8 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5 text-sm leading-6 text-amber-100">
          Product capabilities are not independent certifications, guarantees of security outcomes, or evidence of compliance. Review the implementation and obtain any required legal or regulatory advice before relying on them.
        </aside>
        <div className="mt-8 flex gap-5 text-sm">
          <Link href="/features" className="text-cyan-300 hover:text-cyan-200">Explore features</Link>
          <Link href="/docs" className="text-cyan-300 hover:text-cyan-200">Read docs</Link>
        </div>
      </div>
    </main>
  );
}
