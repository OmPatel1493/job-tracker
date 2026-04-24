"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  ExternalLink,
  FileText,
  Lightbulb,
  Loader2,
  RefreshCw,
  Sparkles,
  StickyNote,
  Trash2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import {
  getApplication,
  updateStatus,
  deleteApplication,
  reanalyzeApplication,
  generateSuggestions,
  getSuggestions,
  updateNotes,
} from "@/lib/api";
import type { ApplicationDetail, ApplicationStatus, SuggestionItem } from "@/lib/types";
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

  // Suggestions
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [generatingSuggestions, setGeneratingSuggestions] = useState(false);

  // Job description collapse
  const [jdExpanded, setJdExpanded] = useState(false);

  // Notes inline edit
  const [notesEditing, setNotesEditing] = useState(false);
  const [notesDraft, setNotesDraft] = useState("");
  const [notesSaving, setNotesSaving] = useState(false);

  useEffect(() => {
    getApplication(id)
      .then((res) => {
        setApp(res.data);
        setNotesDraft(res.data.notes ?? "");
      })
      .catch((err) => {
        if (err?.response?.status === 404) setNotFound(true);
        else toast.error("Failed to load application.");
      })
      .finally(() => setIsLoading(false));
  }, [id]);

  useEffect(() => {
    getSuggestions(id)
      .then((res) => setSuggestions(res.data.suggestions ?? []))
      .catch(() => {}); // no suggestions yet is fine
  }, [id]);

  // Poll every 5s while analysis is pending
  useEffect(() => {
    if (!app || app.analysis_status === "complete") return;
    const timer = setInterval(async () => {
      try {
        const res = await getApplication(id);
        setApp(res.data);
      } catch {
        // silently ignore transient poll errors
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [id, app?.analysis_status]);

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

  async function handleGenerateSuggestions() {
    setGeneratingSuggestions(true);
    try {
      const res = await generateSuggestions(id);
      setSuggestions(res.data.suggestions ?? []);
      toast.success("Suggestions generated!");
    } catch {
      toast.error("Failed to generate suggestions.");
    } finally {
      setGeneratingSuggestions(false);
    }
  }

  async function handleSaveNotes() {
    setNotesSaving(true);
    try {
      const res = await updateNotes(id, notesDraft);
      setApp((prev) => prev ? { ...prev, notes: res.data.notes } : prev);
      setNotesEditing(false);
      toast.success("Notes saved.");
    } catch {
      toast.error("Failed to save notes.");
    } finally {
      setNotesSaving(false);
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
      {/* Analysis pending banner */}
      {app.analysis_status !== "complete" && (
        <div className="flex items-center gap-3 rounded-lg border border-yellow-700/50 bg-yellow-900/20 px-4 py-3">
          <Loader2 className="h-4 w-4 animate-spin text-yellow-400 shrink-0" />
          <p className="text-sm text-yellow-300">
            AI analysis in progress… This usually takes 10–20 seconds.
          </p>
        </div>
      )}

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

      {/* ── Section 1: Skills Analysis ── */}
      {app.analysis_status === "complete" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Matched skills */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="h-5 w-5 text-green-400 shrink-0" />
              <h2 className="text-sm font-semibold text-white">Matched Skills</h2>
              <span className="ml-auto rounded-full bg-green-900/30 px-2 py-0.5 text-xs font-medium text-green-400">
                {app.matched_skills?.length ?? 0}
              </span>
            </div>
            {app.matched_skills && app.matched_skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {app.matched_skills.map((s) => (
                  <span
                    key={s}
                    className="rounded-full border border-green-800/30 bg-green-900/20 px-2.5 py-0.5 text-xs font-medium text-green-300"
                  >
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No matched skills found</p>
            )}
          </div>

          {/* Missing skills */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <div className="flex items-center gap-2 mb-4">
              <XCircle className="h-5 w-5 text-red-400 shrink-0" />
              <h2 className="text-sm font-semibold text-white">Missing Skills</h2>
              <span className="ml-auto rounded-full bg-red-900/30 px-2 py-0.5 text-xs font-medium text-red-400">
                {app.missing_skills?.length ?? 0}
              </span>
            </div>
            {app.missing_skills && app.missing_skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {app.missing_skills.map((s) => (
                  <span
                    key={s}
                    className="rounded-full border border-red-800/30 bg-red-900/20 px-2.5 py-0.5 text-xs font-medium text-red-300"
                  >
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No missing skills — great match!</p>
            )}
          </div>
        </div>
      )}

      {/* ── Section 2: AI Suggestions ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="h-5 w-5 text-yellow-400 shrink-0" />
          <h2 className="text-sm font-semibold text-white">AI Resume Suggestions</h2>
        </div>

        {suggestions.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <p className="text-sm text-slate-400">
              Get personalized suggestions to improve your resume
            </p>
            <button
              onClick={handleGenerateSuggestions}
              disabled={generatingSuggestions}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {generatingSuggestions ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {generatingSuggestions ? "Generating..." : "Generate Suggestions"}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {suggestions.map((s, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-2"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      s.priority === "high"
                        ? "bg-red-900/30 text-red-400"
                        : s.priority === "medium"
                        ? "bg-yellow-900/30 text-yellow-400"
                        : "bg-slate-700 text-slate-400"
                    }`}
                  >
                    {s.priority}
                  </span>
                  <span className="rounded-full bg-blue-900/30 px-2.5 py-0.5 text-xs font-medium text-blue-400">
                    {s.category}
                  </span>
                </div>
                <p className="text-sm text-white">{s.suggestion}</p>
                {s.example && (
                  <p className="text-xs text-slate-400 italic">{s.example}</p>
                )}
              </div>
            ))}
            <div className="flex justify-end pt-1">
              <button
                onClick={handleGenerateSuggestions}
                disabled={generatingSuggestions}
                className="flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white hover:border-slate-500 disabled:opacity-50 transition-colors"
              >
                {generatingSuggestions && <Loader2 className="h-3 w-3 animate-spin" />}
                Regenerate
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Section 3: Job Description ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="h-5 w-5 text-slate-400 shrink-0" />
          <h2 className="text-sm font-semibold text-white">Job Description</h2>
        </div>
        {app.job_description ? (
          <>
            <div
              className={`whitespace-pre-wrap text-sm text-slate-300 leading-relaxed overflow-y-auto ${
                jdExpanded ? "max-h-[600px]" : ""
              }`}
            >
              {jdExpanded
                ? app.job_description
                : app.job_description.slice(0, 500) +
                  (app.job_description.length > 500 ? "..." : "")}
            </div>
            {app.job_description.length > 500 && (
              <button
                onClick={() => setJdExpanded((p) => !p)}
                className="mt-3 text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                {jdExpanded ? "Show less" : "Show more"}
              </button>
            )}
          </>
        ) : (
          <p className="text-sm text-slate-500">No job description available.</p>
        )}
      </div>

      {/* ── Section 4: Notes ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-2 mb-4">
          <StickyNote className="h-5 w-5 text-slate-400 shrink-0" />
          <h2 className="text-sm font-semibold text-white">Notes</h2>
        </div>

        {notesEditing ? (
          <div className="space-y-3">
            <textarea
              value={notesDraft}
              onChange={(e) => setNotesDraft(e.target.value)}
              rows={5}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-y"
              placeholder="Add your notes here..."
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setNotesEditing(false);
                  setNotesDraft(app.notes ?? "");
                }}
                className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveNotes}
                disabled={notesSaving}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {notesSaving && <Loader2 className="h-3 w-3 animate-spin" />}
                Save
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={() => setNotesEditing(true)}
            className="min-h-[80px] cursor-text rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 hover:border-slate-500 transition-colors"
          >
            {app.notes ? (
              <p className="whitespace-pre-wrap text-sm text-slate-300">{app.notes}</p>
            ) : (
              <p className="text-sm text-slate-500">Click to add notes...</p>
            )}
          </div>
        )}
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
