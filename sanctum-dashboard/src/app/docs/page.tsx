import Link from "next/link";

export const metadata = {
  title: "Documentation | SANCTUM-SUITE",
  description: "Installation, configuration, and deployment notes for SANCTUM-SUITE.",
};

export default function DocsPage() {
  return (
    <main className="min-h-screen bg-[#020817] px-6 py-16 text-slate-100">
      <article className="prose prose-invert mx-auto max-w-4xl">
        <Link href="/" className="not-prose text-sm text-cyan-300 hover:text-cyan-200">← SANCTUM-SUITE</Link>
        <p className="mt-12 text-xs uppercase tracking-[0.24em] text-cyan-300">Documentation</p>
        <h1 className="mt-4 text-4xl font-black text-white">Install and evaluate</h1>
        <p className="mt-5 leading-7 text-slate-300">
          SANCTUM-SUITE is a source-available project. The repository license restricts execution and commercial use without the copyright holder&apos;s written authorization. Confirm your rights before installing, deploying, or using it.
        </p>

        <h2 className="mt-10 text-2xl font-semibold text-white">Python CLI</h2>
        <p className="text-slate-300">Use Python 3.11 or later and install from a checked-out, authorized source tree:</p>
        <pre className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-cyan-100"><code>{`python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
sanctum --help`}</code></pre>

        <h2 className="mt-10 text-2xl font-semibold text-white">Dashboard</h2>
        <pre className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-cyan-100"><code>{`cd sanctum-dashboard
npm ci
npm run dev
# Open http://localhost:3000`}</code></pre>
        <p className="text-slate-300">
          The dashboard workbench uses the configured API WebSocket. Set <code>NEXT_PUBLIC_SANCTUM_WS_URL</code> to the authorized API endpoint, for example <code>ws://127.0.0.1:8000/ws/incidents</code> for local development. Use <code>wss://</code> behind HTTPS in production.
        </p>

        <h2 className="mt-10 text-2xl font-semibold text-white">Lead form setup</h2>
        <p className="text-slate-300">
          The public inquiry form forwards data server-side to a webhook; it does not store leads in this application. Configure <code>SANCTUM_LEAD_WEBHOOK_URL</code> with an HTTPS endpoint and optionally set <code>SANCTUM_LEAD_WEBHOOK_TOKEN</code>. Keep these values in the hosting provider&apos;s secret manager, never in <code>NEXT_PUBLIC_*</code> variables. Add provider-side rate limiting and retention controls before publishing the form.
        </p>

        <h2 className="mt-10 text-2xl font-semibold text-white">Production deployment</h2>
        <ol className="space-y-3 text-slate-300">
          <li>1. Review the license, threat model, dependencies, and required permissions.</li>
          <li>2. Run the Python tests and build the dashboard in CI.</li>
          <li>3. Configure secrets, HTTPS, firewall rules, backups, and monitoring.</li>
          <li>4. Bind the API only to trusted interfaces; do not expose development defaults to the public internet.</li>
          <li>5. Verify every enabled module against a test environment and retain a rollback plan.</li>
        </ol>

        <h2 className="mt-10 text-2xl font-semibold text-white">Useful project resources</h2>
        <ul className="space-y-2 text-cyan-300">
          <li><a href="https://github.com/KarolMrozinski/sanctum-suite">Source repository</a></li>
          <li><a href="https://github.com/KarolMrozinski/sanctum-suite/blob/main/SECURITY.md">Security policy</a></li>
          <li><a href="https://github.com/KarolMrozinski/sanctum-suite/blob/main/CHANGELOG.md">Changelog</a></li>
          <li><Link href="/privacy">Website privacy notice</Link></li>
        </ul>
      </article>
    </main>
  );
}
