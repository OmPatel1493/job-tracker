"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Briefcase, Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { getApplications, getAnalyticsSummary } from "@/lib/api";
import type { AnalyticsSummary, Application } from "@/lib/types";
import ApplicationCard from "@/components/ApplicationCard";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Constants ────────────────────────────────────────────────────────────────

const LIMIT = 20;

const STATUS_OPTIONS = [
  { value: "", label: "All" },
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "phone_screen", label: "Phone Screen" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest First" },
  { value: "oldest", label: "Oldest First" },
  { value: "score", label: "Highest Score" },
];

const selectCls =
  "rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500";

// ─── Skeleton cards ───────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-700 bg-slate-800 px-5 py-4">
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-3 w-28" />
      </div>
      <Skeleton className="h-6 w-20 rounded-full" />
      <Skeleton className="h-8 w-8 rounded" />
    </div>
  );
}

// ─── Stats bar ────────────────────────────────────────────────────────────────

function StatsBar({ summary }: { summary: AnalyticsSummary | null }) {
  const stats = [
    {
      label: "Total",
      value: summary ? String(summary.total_applications) : "--",
    },
    {
      label: "Analyzed",
      value: summary ? String(summary.analyzed_count) : "--",
    },
    {
      label: "Avg Score",
      value:
        summary && summary.avg_fit_score_pct !== null
          ? `${summary.avg_fit_score_pct}%`
          : "--",
    },
    {
      label: "Interview Rate",
      value: summary ? `${summary.interview_rate}%` : "--",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {stats.map((s) => (
        <div
          key={s.label}
          className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3"
        >
          <p className="text-xl font-bold text-white">{s.value}</p>
          <p className="text-xs text-slate-400 mt-0.5">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("newest");
  const [offset, setOffset] = useState(0);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Map sort value → API param
  function sortParam(s: string) {
    if (s === "oldest") return "oldest";
    if (s === "score") return "score";
    return "newest";
  }

  const fetchApplications = useCallback(
    async (opts: {
      search: string;
      status: string;
      sort: string;
      offset: number;
      append: boolean;
    }) => {
      try {
        const res = await getApplications({
          search: opts.search || undefined,
          status: opts.status || undefined,
          sort_by: sortParam(opts.sort),
          limit: LIMIT,
          offset: opts.offset,
        });
        const { items, total } = res.data;
        setApplications((prev) => (opts.append ? [...prev, ...items] : items));
        setTotal(total);
      } catch {
        toast.error("Failed to load applications.");
      }
    },
    []
  );

  // Initial load + summary
  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      fetchApplications({ search, status, sort, offset: 0, append: false }),
      getAnalyticsSummary()
        .then((r) => setSummary(r.data))
        .catch(() => {}),
    ]).finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refetch when status or sort changes (reset offset)
  useEffect(() => {
    setOffset(0);
    setIsLoading(true);
    fetchApplications({ search, status, sort, offset: 0, append: false }).finally(
      () => setIsLoading(false)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, sort]);

  // Debounced search
  function handleSearchChange(value: string) {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setOffset(0);
      setIsLoading(true);
      fetchApplications({
        search: value,
        status,
        sort,
        offset: 0,
        append: false,
      }).finally(() => setIsLoading(false));
    }, 300);
  }

  async function handleLoadMore() {
    const newOffset = offset + LIMIT;
    setOffset(newOffset);
    setLoadingMore(true);
    await fetchApplications({
      search,
      status,
      sort,
      offset: newOffset,
      append: true,
    });
    setLoadingMore(false);
  }

  const hasFilters = search !== "" || status !== "";
  const showEmpty = !isLoading && applications.length === 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Briefcase className="h-6 w-6 text-blue-400" />
          <h1 className="text-xl font-semibold text-white">Applications</h1>
        </div>
        <Link
          href="/applications/new"
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Application
        </Link>
      </div>

      {/* Stats */}
      <StatsBar summary={summary} />

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
          <input
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search company or role..."
            className="w-full rounded-lg border border-slate-600 bg-slate-800 pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className={selectCls}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value} className="bg-slate-900">
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className={selectCls}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value} className="bg-slate-900">
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* List */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
        ) : showEmpty ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Briefcase className="h-12 w-12 text-slate-600 mb-4" />
            {hasFilters ? (
              <>
                <p className="text-slate-400 font-medium">
                  No applications match your filters
                </p>
                <button
                  onClick={() => {
                    setSearch("");
                    setStatus("");
                  }}
                  className="mt-3 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Clear filters
                </button>
              </>
            ) : (
              <>
                <p className="text-slate-400 font-medium">
                  No applications yet
                </p>
                <Link
                  href="/applications/new"
                  className="mt-3 flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  Add your first application
                </Link>
              </>
            )}
          </div>
        ) : (
          applications.map((app) => (
            <ApplicationCard key={app.id} application={app} />
          ))
        )}
      </div>

      {/* Pagination */}
      {!isLoading && applications.length > 0 && (
        <div className="flex flex-col items-center gap-3 pt-2">
          <p className="text-sm text-slate-500">
            Showing {applications.length} of {total} applications
          </p>
          {applications.length < total && (
            <button
              onClick={handleLoadMore}
              disabled={loadingMore}
              className="rounded-lg border border-slate-600 px-5 py-2 text-sm font-medium text-slate-300 hover:text-white hover:border-slate-500 disabled:opacity-50 transition-colors"
            >
              {loadingMore ? "Loading..." : "Load more"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
