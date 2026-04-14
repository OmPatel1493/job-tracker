"use client";

import { useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
import type { Application, ApplicationStatus } from "@/lib/types";

// ─── Status badge config ──────────────────────────────────────────────────────

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  saved: "bg-slate-700 text-slate-300",
  applied: "bg-blue-600/20 text-blue-400",
  phone_screen: "bg-yellow-600/20 text-yellow-400",
  interview: "bg-purple-600/20 text-purple-400",
  offer: "bg-green-600/20 text-green-400",
  rejected: "bg-red-600/20 text-red-400",
  withdrawn: "bg-gray-600/20 text-gray-400",
};

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  phone_screen: "Phone Screen",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

// ─── Fit score color ──────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score <= 40) return "text-red-400";
  if (score <= 70) return "text-yellow-400";
  return "text-green-400";
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ApplicationCard({
  application,
}: {
  application: Application;
}) {
  const router = useRouter();
  const initial = application.company_name.charAt(0).toUpperCase();

  return (
    <div
      onClick={() => router.push(`/applications/${application.id}`)}
      className="flex items-center gap-4 rounded-xl border border-slate-700 bg-slate-800 px-5 py-4 cursor-pointer hover:bg-slate-800/80 transition-colors"
    >
      {/* Company avatar */}
      <div className="h-10 w-10 shrink-0 rounded-full bg-blue-600/20 flex items-center justify-center text-blue-400 font-semibold text-sm">
        {initial}
      </div>

      {/* Company + title */}
      <div className="flex-1 min-w-0">
        <p className="text-white font-medium truncate">{application.company_name}</p>
        <p className="text-slate-400 text-sm truncate">{application.job_title}</p>
      </div>

      {/* Status + date */}
      <div className="hidden sm:flex flex-col items-end gap-1 shrink-0">
        <span
          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
            STATUS_STYLES[application.status]
          }`}
        >
          {STATUS_LABELS[application.status]}
        </span>
        {application.applied_date && (
          <span className="text-xs text-slate-500">
            {formatDate(application.applied_date)}
          </span>
        )}
      </div>

      {/* Fit score */}
      <div className="flex flex-col items-center shrink-0 w-12">
        {application.fit_score_pct !== null ? (
          <>
            <span
              className={`text-lg font-bold ${scoreColor(application.fit_score_pct)}`}
            >
              {application.fit_score_pct}
            </span>
            <span className="text-xs text-slate-500 leading-tight text-center">
              {application.fit_label ?? "%"}
            </span>
          </>
        ) : (
          <span className="text-slate-500 text-sm font-medium">--</span>
        )}
      </div>

      <ChevronRight className="h-4 w-4 text-slate-500 shrink-0" />
    </div>
  );
}
