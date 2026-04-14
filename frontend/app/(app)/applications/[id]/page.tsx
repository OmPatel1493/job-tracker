"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Building2,
  Calendar,
  ExternalLink,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
  getApplication,
  updateStatus,
  deleteApplication,
  reanalyzeApplication,
} from "@/lib/api";
import type { ApplicationDetail, ApplicationStatus } from "@/lib/types";
import FitScoreGauge from "@/components/FitScoreGauge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUSES: ApplicationStatus[] = [
  "saved",
  "applied",
  "phone_screen",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  phone_screen: "Phone Screen",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  saved: "bg-slate-700 text-slate-300",
  applied: "bg-blue-600/20 text-blue-400",
  phone_screen: "bg-yellow-600/20 text-yellow-400",
  interview: "bg-purple-600/20 text-purple-400",
  offer: "bg-green-600/20 text-green-400",
  rejected: "bg-red-600/20 text-red-400",
  withdrawn: "bg-gray-600/20 text-gray-400",
};

function formatDate(iso: string | null) {
  if (!iso) return "--";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-8 w-64" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-6 flex flex-col items-center gap-4">
          <Skeleton className="h-40 w-40 rounded-full" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-6 space-y-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [app, setApp] = useState<ApplicationDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    getApplication(id)
      .then((res) => setApp(res.data))
      .catch((err) => {
        if (err?.response?.status === 404) setNotFound(true);
        else toast.error("Failed to load application.");
      })
      .finally(() => setIsLoading(false));
  }, [id]);

  async function handleStatusChange(newStatus: string) {
    if (!app) return;
    try {
      const res = await updateStatus(id, newStatus);
      setApp((prev) => prev ? { ...prev, status: res.data.status } : prev);
      toast.success("Status updated.");
    } catch {
      toast.error("Failed to update status.");
    }
  }

  async function handleReanalyze() {
    setReanalyzing(true);
    try {
      await reanalyzeApplication(id);
      toast.success("Reanalysis started. Results will update shortly.");
    } catch {
      toast.error("Failed to start reanalysis.");
    } finally {
      setReanalyzing(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteApplication(id);
      toast.success("Application deleted.");
      router.push("/applications");
    } catch {
      toast.error("Failed to delete application.");
      setDeleting(false);
    }
  }

  if (isLoading) return <DetailSkeleton />;

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-slate-400 text-lg font-medium">Application not found.</p>
        <Link
          href="/applications"
          className="mt-4 text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          Back to Applications
        </Link>
      </div>
    );
  }

  if (!app) return null;

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="space-y-1">
          <Link
            href="/applications"
            className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors text-sm w-fit"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
          <h1 className="text-2xl font-bold text-white">{app.company_name}</h1>
          <p className="text-slate-400">{app.job_title}</p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReanalyze}
            disabled={reanalyzing}
            className="border-slate-600 text-slate-300 hover:text-white gap-1.5"
          >
            <RefreshCw className={`h-4 w-4 ${reanalyzing ? "animate-spin" : ""}`} />
            Reanalyze
          </Button>

          <select
            value={app.status}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-white outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s} className="bg-slate-900">
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setDeleteOpen(true)}
            className="border-red-800 text-red-400 hover:bg-red-950 hover:text-red-300 gap-1.5"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Hero section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left — gauge */}
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-6 flex flex-col items-center justify-center gap-5">
          <FitScoreGauge score={app.fit_score_pct} size="lg" />

          {/* Sub-scores */}
          <div className="flex gap-6 text-center">
            <div>
              <p className="text-lg font-bold text-white">
                {app.semantic_score !== null ? `${app.semantic_score}%` : "--"}
              </p>
              <p className="text-xs text-slate-400">Semantic Match</p>
            </div>
            <div className="w-px bg-slate-700" />
            <div>
              <p className="text-lg font-bold text-white">
                {app.skill_overlap_score !== null
                  ? `${app.skill_overlap_score}%`
                  : "--"}
              </p>
              <p className="text-xs text-slate-400">Skill Match</p>
            </div>
          </div>

          {/* Analysis status badge */}
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
              app.analysis_status === "complete"
                ? "bg-green-600/20 text-green-400"
                : "bg-yellow-600/20 text-yellow-400"
            }`}
          >
            {app.analysis_status === "complete"
              ? "Analysis Complete"
              : "Analysis Pending..."}
          </span>
        </div>

        {/* Right — job info */}
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-6 space-y-3">
          {/* Company */}
          <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3">
            <Building2 className="h-4 w-4 text-slate-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-slate-500 mb-0.5">Company</p>
              <p className="text-sm text-white font-medium truncate">
                {app.company_name}
              </p>
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3">
            <div className="h-4 w-4 shrink-0 flex items-center justify-center">
              <div className="h-2 w-2 rounded-full bg-blue-400" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-slate-500 mb-0.5">Status</p>
              <span
                className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  STATUS_STYLES[app.status]
                }`}
              >
                {STATUS_LABELS[app.status]}
              </span>
            </div>
          </div>

          {/* Applied date */}
          <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3">
            <Calendar className="h-4 w-4 text-slate-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-slate-500 mb-0.5">Applied Date</p>
              <p className="text-sm text-white">{formatDate(app.applied_date)}</p>
            </div>
          </div>

          {/* Job URL */}
          <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3">
            <ExternalLink className="h-4 w-4 text-slate-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-slate-500 mb-0.5">Job URL</p>
              {app.job_url ? (
                <a
                  href={app.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:text-blue-300 truncate block transition-colors"
                >
                  {app.job_url}
                </a>
              ) : (
                <p className="text-sm text-slate-500">--</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle>Delete Application</DialogTitle>
          </DialogHeader>
          <p className="text-slate-300 text-sm">
            Are you sure you want to delete the application for{" "}
            <span className="text-white font-medium">{app.job_title}</span> at{" "}
            <span className="text-white font-medium">{app.company_name}</span>?
            This action cannot be undone.
          </p>
          <div className="flex justify-end gap-2 mt-4">
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              className="border-slate-600 text-slate-300"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
