"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, UploadCloud, Loader2, Zap, Clock } from "lucide-react";
import { toast } from "sonner";
import { uploadResume, getResume, deleteResume } from "@/lib/api";
import type { Resume } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const CATEGORIES = ["languages", "frameworks", "tools", "concepts", "other"] as const;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return `${months} month${months > 1 ? "s" : ""} ago`;
}

// ─── Loading skeleton ────────────────────────────────────────────────────────

function ResumeSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-48 rounded-xl" />
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}

// ─── Upload section ───────────────────────────────────────────────────────────

function UploadSection({ onUploaded }: { onUploaded: (r: Resume) => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [uploading, setUploading] = useState(false);

  async function submit(file?: File) {
    setUploading(true);
    try {
      const fd = new FormData();
      if (file) {
        fd.append("file", file);
      } else {
        fd.append("text", pasteText);
      }
      const res = await uploadResume(fd);
      toast.success("Resume uploaded successfully!");
      onUploaded(res.data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed. Please try again.";
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) submit(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) submit(file);
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Page title */}
      <div className="flex items-center gap-3">
        <FileText className="h-6 w-6 text-blue-400" />
        <h1 className="text-xl font-semibold text-white">My Resume</h1>
      </div>

      {/* Drop zone */}
      <div
        className={`rounded-xl border-2 border-dashed p-12 text-center cursor-pointer transition-colors ${
          dragOver
            ? "border-blue-500 bg-slate-800/80"
            : "border-slate-600 hover:border-blue-500 hover:bg-slate-800/50"
        }`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <UploadCloud className="mx-auto h-12 w-12 text-slate-400 mb-4" />
        <p className="text-white font-medium">Drag & drop your resume PDF here</p>
        <p className="text-slate-400 text-sm mt-1">or click to browse files</p>
        <span className="inline-block mt-3 px-3 py-1 rounded-full text-xs bg-slate-700 text-slate-300">
          PDF only, max 10MB
        </span>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {/* OR divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 border-t border-slate-700" />
        <span className="text-sm text-slate-500">or</span>
        <div className="flex-1 border-t border-slate-700" />
      </div>

      {/* Paste text */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          Or paste your resume text directly
        </label>
        <textarea
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder="Paste your resume content here..."
          className="w-full min-h-[200px] rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-y"
        />
      </div>

      <button
        onClick={() => submit()}
        disabled={uploading || (!pasteText.trim())}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
        {uploading ? "Analyzing..." : "Upload Resume"}
      </button>
    </div>
  );
}

// ─── Resume display ───────────────────────────────────────────────────────────

function ResumeDisplay({
  resume,
  onReplace,
  onDeleted,
  autoScroll,
}: {
  resume: Resume;
  onReplace: () => void;
  onDeleted: () => void;
  autoScroll?: boolean;
}) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const skillsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll) {
      setTimeout(() => skillsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
    }
  }, [autoScroll]);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteResume();
      toast.success("Resume deleted.");
      setDeleteOpen(false);
      onDeleted();
    } catch {
      toast.error("Failed to delete resume.");
    } finally {
      setDeleting(false);
    }
  }

  const totalSkills = resume.skill_count;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-blue-400" />
          <div>
            <h1 className="text-xl font-semibold text-white">My Resume</h1>
            <p className="text-sm text-slate-400">
              Uploaded {formatDate(resume.uploaded_at)}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onReplace}
            className="border-slate-600 text-slate-300 hover:text-white">
            Replace Resume
          </Button>
          <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)}
            className="border-red-800 text-red-400 hover:bg-red-950 hover:text-red-300">
            Delete
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl bg-slate-800 border border-slate-700 p-4 flex items-center gap-3">
          <Zap className="h-5 w-5 text-blue-400 shrink-0" />
          <div>
            <p className="text-2xl font-bold text-white">{totalSkills}</p>
            <p className="text-xs text-slate-400">Total Skills</p>
          </div>
        </div>
        <div className="rounded-xl bg-slate-800 border border-slate-700 p-4 flex items-center gap-3">
          <FileText className="h-5 w-5 text-blue-400 shrink-0" />
          <div>
            <p className="text-2xl font-bold text-white">{resume.word_count}</p>
            <p className="text-xs text-slate-400">Word Count</p>
          </div>
        </div>
        <div className="rounded-xl bg-slate-800 border border-slate-700 p-4 flex items-center gap-3">
          <Clock className="h-5 w-5 text-blue-400 shrink-0" />
          <div>
            <p className="text-lg font-bold text-white">{timeAgo(resume.uploaded_at)}</p>
            <p className="text-xs text-slate-400">Last Updated</p>
          </div>
        </div>
      </div>

      {/* Skills breakdown */}
      <div ref={skillsRef} className="space-y-4">
        {CATEGORIES.map((cat) => {
          const skills: string[] = resume.parsed_skills?.[cat] ?? [];
          return (
            <div key={cat} className="rounded-xl bg-slate-800 border border-slate-700 p-5">
              <h3 className="text-sm font-semibold text-white capitalize mb-3">{cat}</h3>
              {skills.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {skills.map((s) => (
                    <Badge key={s} className="bg-slate-700 text-slate-200 hover:bg-slate-600">
                      {s}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">None detected</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Delete dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle>Delete Resume</DialogTitle>
          </DialogHeader>
          <p className="text-slate-300 text-sm">
            Are you sure you want to delete your resume? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setDeleteOpen(false)}
              className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleDelete} disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white">
              {deleting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ResumePage() {
  const [resume, setResume] = useState<Resume | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [justUploaded, setJustUploaded] = useState(false);

  useEffect(() => {
    getResume()
      .then((res) => setResume(res.data))
      .catch(() => setResume(null))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <ResumeSkeleton />;

  if (!resume || showUpload) {
    return (
      <UploadSection
        onUploaded={(r) => {
          setResume(r);
          setShowUpload(false);
          setJustUploaded(true);
        }}
      />
    );
  }

  return (
    <ResumeDisplay
      resume={resume}
      autoScroll={justUploaded}
      onReplace={() => setShowUpload(true)}
      onDeleted={() => {
        setResume(null);
        setShowUpload(false);
      }}
    />
  );
}
