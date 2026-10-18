import Link from "next/link";

const pricingPlans = [
  {
    name: "Evaluation",
    price: "Discuss scope",
    description: "For early validation and local security testing.",
    features: ["Evaluation scope defined together", "License rights agreed in writing", "No self-service checkout"],
  },
  {
    name: "SOC Team",
    price: "Discuss scope",
    description: "For operational monitoring and recurring cyber defense workflows.",
    features: ["Deployment scope agreed in writing", "Integration requirements reviewed", "Support scope to be agreed"],
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    description: "Private deployment and custom security integrations.",
    features: ["Private deployment subject to review", "SLA only under a signed agreement", "Custom integration scope to be assessed"],
  },
];

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-[#020817] px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <div className="mb-12 text-center">
          <div className="text-xs uppercase tracking-[0.24em] text-cyan-300">Pricing</div>
          <h1 className="mt-4 text-4xl font-black text-white md:text-5xl">Commercial options for your defense workflow</h1>
          <p className="mx-auto mt-5 max-w-2xl text-sm leading-6 text-slate-400">
            These are discussion categories only, not active subscriptions, checkout offers, or a published price list. Scope, licensing, support, and pricing require an approved written agreement.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {pricingPlans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-3xl border p-6 ${
                plan.featured ? "border-cyan-500/60 bg-cyan-500/10" : "border-slate-800 bg-slate-900/80"
              }`}
            >
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-semibold text-white">{plan.name}</h2>
                {plan.featured ? (
                  <span className="rounded-full border border-cyan-400/40 bg-cyan-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-cyan-300">
                    Popular
                  </span>
                ) : null}
              </div>

              <div className="mt-6 text-2xl font-black text-white">{plan.price}</div>

              <p className="mt-4 text-sm leading-6 text-slate-300">{plan.description}</p>

              <ul className="mt-6 space-y-3 text-sm text-slate-200">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-3">
                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/15 text-xs text-emerald-300">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <Link href="/#contact" className={`mt-8 inline-flex w-full justify-center rounded-full px-4 py-3 text-sm font-semibold ${plan.featured ? "bg-cyan-400 text-slate-950" : "border border-slate-700 bg-slate-950 text-slate-100"}`}>
                {plan.price === "Custom" ? "Request quote" : "Discuss this option"}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
