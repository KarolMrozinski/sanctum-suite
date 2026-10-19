import Link from "next/link";

const pricingPlans = [
  {
    name: "SANCTUM Core",
    subtitle: "SOC & Security Teams",
    audience: "A focused starting point for smaller security operations teams, MSPs, and technology companies.",
    price: "45,000 PLN",
    priceLabel: "Initial license",
    priceNote: "Annual updates subscription quoted separately.",
    deployment: "Up to 3 licensed deployment nodes",
    responsibility: "Customer-operated deployment. Implementation, training, and support are available by separate agreement.",
    scope: [
      "Core analytics capabilities",
      "Container scanning",
      "Standard audit trail and reporting",
      "Deployment documentation",
    ],
  },
  {
    name: "SANCTUM Enterprise",
    subtitle: "Enterprise Security",
    audience: "For large organizations requiring a broader deployment footprint and tailored security integrations.",
    price: "140,000 PLN",
    priceLabel: "Enterprise license",
    priceNote: "Updates, services, and license term defined in the written quote.",
    deployment: "Air-gapped deployment and unlimited licensed nodes",
    responsibility: "Customer-operated deployment. Integration, implementation, training, and support are scoped to your requirements.",
    scope: [
      "Proposed access to all 7 autonomous core pillars",
      "WORM storage integration (MinIO Compliance mode)",
      "Policy integration with OPA",
      "Autonomous Red-Team tooling",
    ],
  },
  {
    name: "SANCTUM Sovereign",
    subtitle: "Government & Defense",
    audience: "For public-sector and defense organizations with specialized deployment, assurance, and licensing requirements.",
    price: "450,000 PLN+",
    priceLabel: "Starting price",
    priceNote: "Final pricing based on an agreed technical and licensing scope.",
    deployment: "Deployment model and environment defined per engagement",
    responsibility: "Dedicated licensing and delivery terms agreed for each engagement. Perpetual source-available rights may be negotiated.",
    scope: [
      "Optional specialist modules and advanced decoders",
      "Post-quantum cryptography assessment and integration options (ML-KEM / ML-DSA)",
      "HSM integration and ZK-SNARK/MPC work, subject to technical scoping",
      "TEMPEST assessment can be scoped with qualified specialist providers",
    ],
  },
];

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-[#020817] px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <div className="mb-12 text-center">
          <div className="text-xs uppercase tracking-[0.24em] text-cyan-300">Licensing & engagement</div>
          <h1 className="mt-4 text-4xl font-black text-white md:text-5xl">Security capabilities, scoped to your needs</h1>
          <p className="mx-auto mt-5 max-w-2xl text-sm leading-6 text-slate-400">
            Three proposed engagement tiers, from a focused SOC deployment to a tailored sovereign engagement. Pricing is indicative; scope, licensing, delivery, and support are confirmed in a written proposal and signed agreement.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {pricingPlans.map((plan) => (
            <div
              key={plan.name}
              className="flex flex-col rounded-3xl border border-slate-800 bg-slate-900/80 p-6"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">{plan.subtitle}</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">{plan.name}</h2>
              <p className="mt-4 min-h-12 text-sm leading-6 text-slate-300">{plan.audience}</p>
              <p className="mt-6 text-xs font-medium uppercase tracking-[0.14em] text-slate-400">{plan.priceLabel}</p>
              <div className="mt-1 text-3xl font-black text-white">{plan.price}</div>
              <p className="mt-2 min-h-10 text-xs leading-5 text-slate-400">{plan.priceNote}</p>
              <p className="mt-5 rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-sm text-cyan-100">
                {plan.deployment}
              </p>
              <h3 className="mt-6 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Package highlights</h3>
              <ul className="mt-3 flex-1 space-y-3 text-sm text-slate-200">
                {plan.scope.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/15 text-xs text-emerald-300">✓</span>
                    <span className="leading-5">{feature}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-xs leading-5 text-slate-400">{plan.responsibility}</p>
              <Link href="/#contact" className="mt-8 inline-flex w-full justify-center rounded-full border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-semibold text-slate-100 transition hover:border-cyan-500 hover:text-cyan-200">
                Request a proposal
              </Link>
            </div>
          ))}
        </div>

        <section className="mt-10 rounded-3xl border border-slate-800 bg-slate-900/70 p-6 md:p-8" aria-labelledby="package-terms">
          <h2 id="package-terms" className="text-2xl font-bold text-white">Engagement details</h2>
          <div className="mt-6 grid gap-6 text-sm leading-6 text-slate-300 md:grid-cols-2">
            <div>
              <h3 className="font-semibold text-cyan-200">Scope and delivery</h3>
              <p className="mt-2">Each proposal specifies licensed software, deployment environments, deliverables, and acceptance criteria. Implementation, integrations, training, support, and service levels are scoped separately unless expressly included.</p>
            </div>
            <div>
              <h3 className="font-semibold text-cyan-200">Deployment limits</h3>
              <p className="mt-2">The agreement defines a licensed node and how test, standby, disaster-recovery, affiliate, and additional-site environments are counted.</p>
            </div>
            <div>
              <h3 className="font-semibold text-cyan-200">License and intellectual property</h3>
              <p className="mt-2">Package descriptions are not a license grant. Execution and commercial use require prior written authorization under the repository license. Any rights to modify, redistribute, sublicense, or use the software perpetually must be expressly granted in the signed agreement; copyright transfer is not implied.</p>
            </div>
            <div>
              <h3 className="font-semibold text-cyan-200">Security and compliance</h3>
              <p className="mt-2">SANCTUM may support security and compliance workflows; it does not certify compliance with DORA, NIS2, or other regulations, or guarantee security outcomes. Capabilities and integrations are confirmed during technical discovery.</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
