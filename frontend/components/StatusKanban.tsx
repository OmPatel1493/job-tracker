"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { Application } from "@/lib/types";

// ─── Column config ────────────────────────────────────────────────────────────

const COLUMNS = [
  { status: "saved",        label: "Saved",        dot: "bg-slate-400",  badge: "bg-slate-700 text-slate-300" },
  { status: "applied",      label: "Applied",       dot: "bg-blue-400",   badge: "bg-blue-900/40 text-blue-300" },
  { status: "phone_screen", label: "Phone Screen",  dot: "bg-yellow-400", badge: "bg-yellow-900/40 text-yellow-300" },
  { status: "interview",    label: "Interview",     dot: "bg-purple-400", badge: "bg-purple-900/40 text-purple-300" },
  { status: "offer",        label: "Offer",         dot: "bg-green-400",  badge: "bg-green-900/40 text-green-300" },
  { status: "rejected",     label: "Rejected",      dot: "bg-red-400",    badge: "bg-red-900/40 text-red-300" },
  { status: "withdrawn",    label: "Withdrawn",     dot: "bg-gray-400",   badge: "bg-gray-700 text-gray-300" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

function scoreColor(score: number | null): string {
  if (score === null) return "bg-slate-700 text-slate-400";
  if (score <= 40)    return "bg-red-900/30 text-red-400";
  if (score <= 70)    return "bg-yellow-900/30 text-yellow-400";
  return "bg-green-900/30 text-green-400";
}

// ─── Kanban card ──────────────────────────────────────────────────────────────

function KanbanCard({
  app,
  isDragging,
  onDragStart,
  onDragEnd,
}: {
  app: Application;
  isDragging: boolean;
  onDragStart: (e: React.DragEvent, id: number) => void;
  onDragEnd: () => void;
}) {
  const router = useRouter();

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, app.id)}
      onDragEnd={onDragEnd}
      onClick={() => router.push(`/applications/${app.id}`)}
      className={`rounded-lg border border-slate-700 bg-slate-800 p-3 mb-2 cursor-grab select-none transition-opacity ${
        isDragging ? "opacity-50 cursor-grabbing" : "hover:border-slate-600"
      }`}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <p className="text-sm font-medium text-white leading-tight truncate">
          {app.company_name}
        </p>
        <span
          className={`shrink-0 rounded-full px-1.5 py-0.5 text-xs font-medium ${scoreColor(
            app.fit_score_pct
          )}`}
        >
          {app.fit_score_pct !== null ? `${app.fit_score_pct}%` : "?"}
        </span>
      </div>

      {/* Job title */}
      <p className="text-xs text-slate-400 truncate mb-2">{app.job_title}</p>

      {/* Bottom row */}
      <p className="text-xs text-slate-500">{timeAgo(app.created_at)}</p>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface Props {
  applications: Application[];
  onStatusChange: (id: number, newStatus: string) => Promise<void>;
}

export default function StatusKanban({ applications, onStatusChange }: Props) {
  const [localApps, setLocalApps] = useState<Application[]>(applications);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<number | null>(null);

  useEffect(() => {
    setLocalApps(applications);
  }, [applications]);

  function handleDragStart(e: React.DragEvent, id: number) {
    e.dataTransfer.setData("applicationId", id.toString());
    e.dataTransfer.effectAllowed = "move";
    setDraggingId(id);
  }

  function handleDragEnd() {
    setDraggingId(null);
    setDragOverColumn(null);
  }

  function handleDragOver(e: React.DragEvent, colStatus: string) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverColumn(colStatus);
  }

  function handleDragLeave() {
    setDragOverColumn(null);
  }

  async function handleDrop(e: React.DragEvent, newStatus: string) {
    e.preventDefault();
    setDragOverColumn(null);

    const appId = parseInt(e.dataTransfer.getData("applicationId"), 10);
    const app = localApps.find((a) => a.id === appId);
    if (!app || app.status === newStatus) return;

    // Optimistic update
    const prev = localApps;
    setLocalApps((apps) =>
      apps.map((a) =>
        a.id === appId ? { ...a, status: newStatus as Application["status"] } : a
      )
    );

    try {
      await onStatusChange(appId, newStatus);
    } catch {
      setLocalApps(prev);
      toast.error("Failed to update status.");
    }
  }

  return (
    <div className="overflow-x-auto pb-4">
      <div className="flex gap-3" style={{ minWidth: "max-content" }}>
        {COLUMNS.map((col) => {
          const colApps = localApps.filter((a) => a.status === col.status);
          const isOver = dragOverColumn === col.status;

          return (
            <div key={col.status} className="min-w-[280px] max-w-[280px] flex flex-col">
              {/* Column header */}
              <div className="flex items-center gap-2 mb-2 px-1">
                <span className={`h-2 w-2 rounded-full shrink-0 ${col.dot}`} />
                <span className="text-sm font-medium text-white flex-1">
                  {col.label}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${col.badge}`}>
                  {colApps.length}
                </span>
              </div>

              {/* Column body */}
              <div
                onDragOver={(e) => handleDragOver(e, col.status)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, col.status)}
                className={`flex-1 min-h-[400px] rounded-xl p-2 transition-colors ${
                  isOver
                    ? "border-2 border-dashed border-blue-500 bg-blue-500/5"
                    : "border border-slate-800 bg-slate-900/50"
                }`}
              >
                {colApps.map((app) => (
                  <KanbanCard
                    key={app.id}
                    app={app}
                    isDragging={draggingId === app.id}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                  />
                ))}
                {colApps.length === 0 && (
                  <div className="flex items-center justify-center h-20">
                    <p className="text-xs text-slate-600">Drop here</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
