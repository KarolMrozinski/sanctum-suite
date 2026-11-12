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

  const liveSignal = liveSnapshot?.stats?.[0]?.value ?? "2,418";

  return (
    <main className="min-h-screen bg-transparent text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-[1800px]">
        <aside className="w-[280px] border-r border-slate-800/90 bg-[#0b0f13]/95 px-5 py-6 backdrop-blur-sm">
          <div className="flex items-center gap-3 px-2 pb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#6ee7b7]/30 bg-[#0f1d1b] text-sm font-bold text-[#a7f3d0] shadow-[0_0_20px_rgba(110,231,183,0.18)]">
              S
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-[#a7f3d0]">KarolMrozinski</div>
              <div className="text-lg font-semibold tracking-[0.12em] text-white">SANCTUM-SUITE</div>
            </div>
          </div>

          <div className="claude-terminal mb-5 rounded-xl px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-[#9ee7d6]">
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
                    "claude-button flex w-full items-center justify-between rounded-lg border px-3 py-2.5 text-left text-sm transition-all duration-200",
                    isActive
                      ? "border-[#6ee7b7]/25 bg-[#101c1b] text-[#effaf5] shadow-[inset_0_0_0_1px_rgba(110,231,183,0.08),0_0_0_1px_rgba(110,231,183,0.05)]"
                      : "border-transparent bg-transparent text-slate-300 hover:border-slate-700 hover:bg-[#10161b] hover:text-white",
                  ].join(" ")}
                >
                  <span>{label}</span>
                  <span className="rounded-full border border-slate-700 bg-[#0b1116] px-2 py-0.5 text-[10px] font-medium text-slate-200">
                    {count}
                  </span>
                </Link>
              );
            })}
          </nav>

          <div className="panel-surface mt-8 rounded-2xl p-4">
            <div className="mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-slate-400">
              <span>Signal</span>
              <span className="text-[#9ee7d6]">Live</span>
            </div>
            <div className="space-y-3">
              <div>
                <div className="mb-1 flex justify-between text-xs text-slate-300">
                  <span>Threat score</span>
                  <span className="text-white">{liveSignal}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[#11181d]">
                  <div className="h-full w-[87%] rounded-full bg-gradient-to-r from-[#6ee7b7] via-[#82d7ff] to-[#bcd3ff]" />
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Analyst queue</span>
                <span className="font-medium text-[#9ee7d6]">06 pending</span>
              </div>
            </div>
          </div>
        </aside>

        <div className="flex-1">
          <header className="flex items-center justify-between border-b border-slate-800 bg-[#0b1116]/80 px-6 py-4 backdrop-blur-sm">
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Threat intelligence workspace</div>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">{sectionTitleMap[activeSection]}</h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-slate-700 bg-[#0c1217] px-3 py-1.5 text-xs text-slate-300 shadow-inner shadow-slate-950/50">
                02:42 UTC
              </div>
              <button
                type="button"
                className="claude-button rounded-full border border-[#6ee7b7]/20 bg-[#111d1d] px-4 py-2 text-sm font-medium text-[#9ee7d6] transition hover:bg-[#162822]"
              >
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
