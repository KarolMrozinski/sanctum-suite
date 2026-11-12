"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import {
  dashboardNavigation,
  getDashboardSnapshot,
  type DashboardSectionKey,
  type DashboardSnapshot,
} from "@/lib/dashboard-data";

const sectionTitleMap: Record<DashboardSectionKey, string> = {
  overview: "Operational overview",
  threats: "Threat landscape",
  entities: "Entities & indicators",
  investigations: "Investigations",
  alerts: "Alerts",
};

export function DashboardShell({
  section,
  children,
}: {
  section: DashboardSectionKey;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [liveSnapshot, setLiveSnapshot] = useState<DashboardSnapshot | null>(null);

  const activeSection = useMemo(() => {
    const matched = dashboardNavigation.find((item) => {
      if (pathname === "/") {
        return item.id === "overview";
      }
      return item.href === pathname;
    });

    return matched?.id ?? section;
  }, [pathname, section]);

  useEffect(() => {
    let isMounted = true;

    fetch(`/api/dashboard?section=${activeSection}`)
      .then((response) => response.json())
      .then((data: DashboardSnapshot) => {
        if (isMounted) {
          setLiveSnapshot(data);
        }
      })
      .catch(() => {
        if (isMounted) {
          setLiveSnapshot(getDashboardSnapshot(activeSection));
        }
      });

    return () => {
      isMounted = false;
    };
  }, [activeSection]);

  return (
    <main className="min-h-screen bg-[#071a28] text-slate-100">
      <div className="flex min-h-screen">
        <aside className="w-[280px] border-r border-slate-800/90 bg-[#0b1622] px-5 py-6">
          <div className="flex items-center gap-3 px-2 pb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#36d4ab]/30 bg-[#1de9b6]/10 text-sm font-bold text-[#7ef7d5] shadow-[0_0_24px_rgba(29,233,182,0.25)]">
              S
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-[#7fe7d4]">KarolMrozinski</div>
              <div className="text-lg font-semibold tracking-wide text-white">SANCTUM-SUITE</div>
            </div>
          </div>

          <div className="mb-5 rounded-xl border border-[#1de9b6]/20 bg-[#122233] px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-[#8ae9cf]">
            Sanctum Suite workspace
          </div>

          <nav aria-label="Primary navigation" className="space-y-2">
            {dashboardNavigation.map(({ id, label, href, count }) => {
              const isActive = activeSection === id;

              return (
                <Link
                  key={id}
                  href={href}
                  className={[
                    "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition",
                    isActive
                      ? "border-[#1de9b6]/30 bg-[#132b3a] text-white shadow-[inset_0_0_0_1px_rgba(29,233,182,0.18)]"
                      : "border-transparent bg-transparent text-slate-300 hover:border-slate-700 hover:bg-slate-900/60 hover:text-white",
                  ].join(" ")}
                >
                  <span>{label}</span>
                  <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-0.5 text-[10px] font-medium text-slate-200">
                    {count}
                  </span>
                </Link>
              );
            })}
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
              <h1 className="mt-1 text-2xl font-semibold text-white">{sectionTitleMap[activeSection]}</h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-slate-700 bg-[#0d1d2d] px-3 py-1.5 text-xs text-slate-300">02:42 UTC</div>
              <button type="button" className="rounded-full border border-[#1de9b6]/30 bg-[#113d35] px-4 py-2 text-sm font-medium text-[#8feccc] transition hover:bg-[#174c42]">
                Run sweep
              </button>
            </div>
          </header>

          <div className="space-y-6 p-6">{children}</div>
        </div>
      </div>
    </main>
  );
}
