import Link from "next/link";

export const metadata = {
  title: "Privacy notice | SANCTUM-SUITE",
  description: "Privacy information for inquiries submitted through the SANCTUM-SUITE website.",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#020817] px-6 py-16 text-slate-100">
      <article className="mx-auto max-w-3xl">
        <Link href="/" className="text-sm text-cyan-300 hover:text-cyan-200">← SANCTUM-SUITE</Link>
        <p className="mt-12 text-xs uppercase tracking-[0.24em] text-cyan-300">Privacy notice</p>
        <h1 className="mt-4 text-4xl font-black text-white">Website inquiry data</h1>
        <p className="mt-6 leading-7 text-slate-300">
          The contact form requests your work email address, organization, and message to respond to an inquiry. Do not include passwords, security incident details, personal sensitive information, or confidential system data.
        </p>
        <h2 className="mt-8 text-xl font-semibold text-white">Processing and retention</h2>
        <p className="mt-3 leading-7 text-slate-300">
          Submitted details are forwarded to the webhook configured by the site operator. This application does not persist submissions. The operator and webhook provider may process and retain the information under their own policies. Before enabling the form, the operator must identify the data controller, lawful basis, recipients, retention period, and a privacy contact, and publish the final notice appropriate to their jurisdiction.
        </p>
        <h2 className="mt-8 text-xl font-semibold text-white">Configuration</h2>
        <p className="mt-3 leading-7 text-slate-300">
          If the lead webhook is not configured, the form is unavailable and submissions are not accepted. The hosting operator should secure the webhook credentials and apply provider-side access, rate limits, and retention controls.
        </p>
        <p className="mt-8 text-xs text-slate-500">This template is operational disclosure, not legal advice. Replace it with a reviewed, organization-specific privacy notice before launch.</p>
      </article>
    </main>
  );
}
