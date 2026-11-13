"use client";

import { FormEvent, useEffect, useState } from "react";

type SubmissionState = "idle" | "sending" | "sent" | "error";

export default function LeadForm() {
  const [state, setState] = useState<SubmissionState>("idle");
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/leads", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Lead service status unavailable");
        return (await response.json()) as { available: boolean };
      })
      .then(({ available: isAvailable }) => {
        if (active) setAvailable(isAvailable);
      })
      .catch(() => {
        if (active) setAvailable(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("sending");

    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    try {
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        setState("error");
        return;
      }

      form.reset();
      setState("sent");
    } catch {
      setState("error");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block text-sm text-slate-300">
        Work email
        <input
          required
          type="email"
          name="email"
          autoComplete="email"
          maxLength={254}
          className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400"
        />
      </label>
      <label className="block text-sm text-slate-300">
        Organization
        <input
          required
          type="text"
          name="organization"
          autoComplete="organization"
          maxLength={120}
          className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400"
        />
      </label>
      <label className="block text-sm text-slate-300">
        What would you like to discuss?
        <textarea
          required
          name="message"
          rows={4}
          maxLength={2000}
          className="mt-2 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400"
        />
      </label>
      <label className="hidden" aria-hidden="true">
        Leave this field empty
        <input name="website" tabIndex={-1} autoComplete="off" />
      </label>
      <p className="text-xs leading-5 text-slate-500">
        By submitting, you agree that your details will be sent to the site operator&apos;s configured lead-processing service. See the <a href="/privacy" className="text-cyan-300 underline">privacy notice</a>.
      </p>
      <button
        type="submit"
        disabled={state === "sending" || available !== true}
        className="rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-wait disabled:opacity-60"
      >
        {state === "sending" ? "Sending..." : available === null ? "Checking contact service..." : available ? "Send inquiry" : "Contact form unavailable"}
      </button>
      {available === false && <p role="status" className="text-sm text-amber-200">The site operator has not configured the inquiry service yet.</p>}
      {state === "sent" && <p role="status" className="text-sm text-emerald-300">Thanks. Your inquiry was submitted.</p>}
      {state === "error" && <p role="alert" className="text-sm text-rose-300">We could not submit your inquiry. Please try again later or use the repository contact channel.</p>}
    </form>
  );
}
