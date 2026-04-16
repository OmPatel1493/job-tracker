"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Brain,
  Briefcase,
  Star,
  Target,
  Trophy,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAnalyticsSummary, getApplications } from "@/lib/api";
import type { AnalyticsSummary, Application } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  saved: "#64748b",
  applied: "#3b82f6",
  phone_screen: "#eab308",
  interview: "#a855f7",
  offer: "#22c55e",
  rejected: "#ef4444",
  withdrawn: "#6b7280",
};

const SCORE_RANGES = ["0–20", "21–40", "41–60", "61–80", "81–100"];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function scoreRangeIndex(score: number): number {
  if (score <= 20) return 0;
  if (score <= 40) return 1;
  if (score <= 60) return 2;
  if (score <= 80) return 3;
  return 4;
}

function avgScoreColor(score: number | null) {
  if (score === null) return { icon: "text-slate-400", bg: "bg-slate-500/10" };
  if (score > 60) return { icon: "text-green-400", bg: "bg-green-500/10" };
  if (score > 40) return { icon: "text-yellow-400", bg: "bg-yellow-500/10" };
  return { icon: "text-red-400", bg: "bg-red-500/10" };
}

function formatTime(date: Date) {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Dark tooltip ─────────────────────────────────────────────────────────────

function DarkTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name: string; value: number; color?: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-lg">
      {label && <p className="text-slate-400 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color ?? "#fff" }}>
          {p.name}: <span className="font-semibold">{p.value}</span>
        </p>
      ))}
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function AnalyticsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {[0,1,2,3,4,5].map((i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
      </div>
      <Skeleton className="h-48 w-full rounded-xl" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Skeleton className="h-[300px] rounded-xl" />
        <Skeleton className="h-[300px] rounded-xl" />
      </div>
      <Skeleton className="h-[400px] w-full rounded-xl" />
      <Skeleton className="h-[200px] w-full rounded-xl" />
    </div>
  );
}

// ─── Pipeline funnel ──────────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { key: "total",        label: "Total",        color: "bg-slate-600" },
  { key: "applied",      label: "Applied",      color: "bg-blue-700" },
  { key: "phone_screen", label: "Phone Screen", color: "bg-yellow-600" },
  { key: "interview",    label: "Interview",    color: "bg-purple-600" },
  { key: "offer",        label: "Offer",        color: "bg-green-600" },
];

function Pipeline({
  total,
  byStatus,
}: {
  total: number;
  byStatus: Record<string, number>;
}) {
  const counts: Record<string, number> = {
    total,
    applied:      (byStatus.applied      ?? 0) + (byStatus.phone_screen ?? 0) + (byStatus.interview ?? 0) + (byStatus.offer ?? 0),
    phone_screen: (byStatus.phone_screen ?? 0) + (byStatus.interview    ?? 0) + (byStatus.offer     ?? 0),
    interview:    (byStatus.interview    ?? 0) + (byStatus.offer        ?? 0),
    offer:         byStatus.offer        ?? 0,
  };

  return (
    <div className="space-y-3">
      {PIPELINE_STAGES.map((stage) => {
        const count = counts[stage.key] ?? 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <div key={stage.key} className="flex items-center gap-3">
            <span className="w-28 shrink-0 text-sm text-slate-400 text-right">
              {stage.label}
            </span>
            <div className="flex-1 h-7 rounded bg-slate-800 overflow-hidden">
              <div
                className={`h-full rounded transition-all duration-700 ${stage.color}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-10 text-right text-sm font-semibold text-white shrink-0">
              {count}
            </span>
            <span className="w-12 text-right text-xs text-slate-500 shrink-0">
              {pct}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Donut center label ───────────────────────────────────────────────────────

function DonutCenterLabel({ total }: { total: number }) {
  return (
    <text x="50%" y="42%" textAnchor="middle" dominantBaseline="middle">
      <tspan x="50%" dy="0" fill="white" fontSize={22} fontWeight={700}>
        {total}
      </tspan>
      <tspan x="50%" dy="18" fill="#94a3b8" fontSize={11}>
        total
      </tspan>
    </text>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [updatedAt] = useState(() => new Date());

  useEffect(() => {
    Promise.all([
      getAnalyticsSummary().then((r) => setSummary(r.data)),
      getApplications({ limit: 100 }).then((r) => setApplications(r.data.items)),
    ])
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <AnalyticsSkeleton />;

  // ── Derived ──────────────────────────────────────────────────────────────────

  const avg = summary?.avg_fit_score_pct ?? null;
  const { icon: avgIconColor, bg: avgIconBg } = avgScoreColor(avg);

  const kpiCards = [
    {
      icon: <Briefcase className="h-5 w-5 text-blue-400" />,
      iconBg: "bg-blue-500/10",
      value: String(summary?.total_applications ?? 0),
      label: "Total Applications",
      sub: null,
    },
    {
      icon: <Brain className="h-5 w-5 text-purple-400" />,
      iconBg: "bg-purple-500/10",
      value: `${summary?.analyzed_count ?? 0} / ${summary?.total_applications ?? 0}`,
      label: "Analyzed",
      sub: `${summary?.pending_count ?? 0} pending`,
    },
    {
      icon: <Target className={`h-5 w-5 ${avgIconColor}`} />,
      iconBg: avgIconBg,
      value: avg !== null ? `${avg}%` : "--",
      label: "Avg Fit Score",
      sub: "across all analyzed apps",
    },
    {
      icon: <Trophy className="h-5 w-5 text-yellow-400" />,
      iconBg: "bg-yellow-500/10",
      value: summary?.highest_fit_score_pct !== null && summary?.highest_fit_score_pct !== undefined
        ? `${summary.highest_fit_score_pct}%`
        : "--",
      label: "Best Score",
      sub: null,
    },
    {
      icon: <Users className="h-5 w-5 text-green-400" />,
      iconBg: "bg-green-500/10",
      value: `${summary?.interview_rate ?? 0}%`,
      label: "Interview Rate",
      sub: "reached interview stage",
    },
    {
      icon: <Star className="h-5 w-5 text-orange-400" />,
      iconBg: "bg-orange-500/10",
      value: `${summary?.offer_rate ?? 0}%`,
      label: "Offer Rate",
      sub: "received offers",
    },
  ];

  // Weekly line chart data
  const weeklyData = (summary?.weekly_applications ?? []).map((w) => ({
    week: w.week.replace(/^\d{4}-/, ""),
    count: w.count,
  }));
  const avgPerWeek =
    weeklyData.length > 0
      ? Math.round(weeklyData.reduce((s, w) => s + w.count, 0) / weeklyData.length)
      : 0;

  // Donut data
  const statusData = Object.entries(summary?.by_status ?? {})
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));
  const statusTotal = statusData.reduce((s, d) => s + d.value, 0);

  // Skill gaps — color by rank
  const skillGaps = (summary?.top_missing_skills ?? []).slice(0, 10);
  function skillBarColor(idx: number) {
    if (idx < 3)  return "#ef4444";
    if (idx < 7)  return "#eab308";
    return "#3b82f6";
  }

  // Score distribution
  const scoreDist = SCORE_RANGES.map((range) => ({ range, count: 0 }));
  applications.forEach((app) => {
    if (app.fit_score_pct !== null) {
      scoreDist[scoreRangeIndex(app.fit_score_pct)].count += 1;
    }
  });
  const hasScoreData = scoreDist.some((d) => d.count > 0);

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-6 w-6 text-blue-400 shrink-0" />
          <div>
            <h1 className="text-xl font-semibold text-white">Analytics</h1>
            <p className="text-sm text-slate-400">
              Track your job search performance over time
            </p>
          </div>
        </div>
        <span className="text-xs text-slate-500 shrink-0 pt-1">
          Updated {formatTime(updatedAt)}
        </span>
      </div>

      {/* ── Section 1: KPI cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {kpiCards.map((c, i) => (
          <div
            key={c.label}
            className="rounded-xl border border-slate-800 bg-slate-900 p-5 animate-fade-in"
            style={{ animationDelay: `${i * 60}ms`, animationFillMode: "both" }}
          >
            <div className={`inline-flex rounded-lg p-2 ${c.iconBg} mb-3`}>
              {c.icon}
            </div>
            <p className="text-3xl font-bold text-white">{c.value}</p>
            <p className="text-sm text-slate-400 mt-1">{c.label}</p>
            {c.sub && (
              <p className="text-xs text-slate-500 mt-0.5">{c.sub}</p>
            )}
          </div>
        ))}
      </div>

      {/* ── Section 2: Pipeline funnel ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-sm font-semibold text-white mb-5">
          Application Pipeline
        </h2>
        {(summary?.total_applications ?? 0) === 0 ? (
          <p className="text-sm text-slate-500 text-center py-6">
            No applications yet
          </p>
        ) : (
          <Pipeline
            total={summary!.total_applications}
            byStatus={summary!.by_status}
          />
        )}
      </div>

      {/* ── Section 3: Line + Donut ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Line chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-sm font-semibold text-white mb-4">
            Weekly Application Volume
          </h2>
          {weeklyData.length === 0 ? (
            <div className="flex items-center justify-center h-[300px]">
              <p className="text-sm text-slate-500">No data yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={weeklyData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                <XAxis
                  dataKey="week"
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<DarkTooltip />} />
                <ReferenceLine
                  y={avgPerWeek}
                  stroke="#64748b"
                  strokeDasharray="3 3"
                  label={{ value: `avg ${avgPerWeek}`, fill: "#64748b", fontSize: 10 }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  name="Applications"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: "#3b82f6", r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Donut chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-sm font-semibold text-white mb-4">
            Status Distribution
          </h2>
          {statusData.length === 0 ? (
            <div className="flex items-center justify-center h-[300px]">
              <p className="text-sm text-slate-500">No data yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="40%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={105}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {statusData.map((entry, i) => (
                    <Cell key={i} fill={STATUS_COLORS[entry.name] ?? "#64748b"} />
                  ))}
                  <DonutCenterLabel total={statusTotal} />
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0];
                    return (
                      <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-lg">
                        <p style={{ color: d.payload.fill }}>
                          {d.name}: <span className="font-semibold text-white">{d.value}</span>
                        </p>
                      </div>
                    );
                  }}
                />
                <Legend
                  layout="vertical"
                  align="right"
                  verticalAlign="middle"
                  formatter={(value) => (
                    <span className="text-xs text-slate-400 capitalize">
                      {value.replace("_", " ")}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ── Section 4: Skill gap analysis ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-sm font-semibold text-white">
          Skills You&apos;re Most Often Missing
        </h2>
        <p className="text-xs text-slate-500 mb-4">
          Based on all analyzed job descriptions
        </p>
        {skillGaps.length === 0 ? (
          <div className="flex items-center justify-center h-24">
            <p className="text-sm text-slate-500">
              Add applications to see your skill gaps
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={skillGaps}
              layout="vertical"
              margin={{ top: 0, right: 40, bottom: 0, left: 0 }}
            >
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="skill"
                width={120}
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="count" name="Missing in" radius={[0, 4, 4, 0]}
                label={{ position: "right", fill: "#94a3b8", fontSize: 11 }}
              >
                {skillGaps.map((_, i) => (
                  <Cell key={i} fill={skillBarColor(i)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Section 5: Score distribution ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-sm font-semibold text-white mb-4">
          Score Distribution
        </h2>
        {!hasScoreData ? (
          <div className="flex items-center justify-center h-24">
            <p className="text-sm text-slate-500">
              No analyzed applications yet
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={scoreDist} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis
                dataKey="range"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="count" name="Applications" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

    </div>
  );
}
