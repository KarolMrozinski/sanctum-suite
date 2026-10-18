import Link from "next/link";

export const metadata = {
  title: "Features | SANCTUM-SUITE",
  description: "Explore the security, AI safety, analytics, and reporting modules in SANCTUM-SUITE.",
};

const groups = [
  {
    title: "Security operations",
    features: ["Endpoint and TCP port scanning", "Threat correlation and attack graph utilities", "Detection rule generation", "SIEM export and event processing"],
  },
  {
    title: "AI safety and analysis",
    features: ["Prompt inspection API", "LLM guardrail and anomaly modules", "Single- and multi-modal fuzzing utilities", "Resource-exhaustion probes"],
  },
  {
    title: "Governance and reporting",
    features: ["Compliance mapping modules", "Audit analytics storage", "HTML and PDF report generation", "Report signing utilities"],
  },
  {
    title: "Infrastructure and resilience",
    features: ["Container and Kubernetes-related analyzers", "Zero-trust and remediation helpers", "Threat intelligence and XDR integration modules", "Optional platform-specific components"],
  },
];

export default function FeaturesPage() {
  return (
    <main className="min-h-screen bg-[#020817] px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <Link href="/" className="text-sm text-cyan-300 hover:text-cyan-200">← SANCTUM-SUITE</Link>
        <div className="mb-10 mt-12">
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">Features</p>
          <h1 className="mt-4 text-4xl font-black text-white md:text-5xl">A broad set of security modules, with deployment-specific requirements.</h1>
          <p className="mt-5 max-w-3xl leading-7 text-slate-300">
            The repository contains the following categories of modules. Availability and runtime behavior depend on configuration, operating system, dependencies, permissions, and integration credentials. Treat this list as a product overview, not a certification or promise that every module is production validated.
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {groups.map((group) => (
            <section key={group.title} className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <h2 className="text-xl font-semibold text-white">{group.title}</h2>
              <ul className="mt-5 space-y-3 text-sm leading-6 text-slate-300">
                {group.features.map((feature) => <li key={feature} className="flex gap-3"><span className="text-cyan-300">•</span>{feature}</li>)}
              </ul>
            </section>
          ))}
        </div>
        <p className="mt-8 text-sm text-slate-500">
          Use scanning, testing, fuzzing, and red-team functions only on systems for which you have explicit authorization.
        </p>
      </div>
    </main>
  );
}
