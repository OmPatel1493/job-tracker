"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Clock,
  Target,
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
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAnalyticsSummary, getApplications } from "@/lib/api";
import type { AnalyticsSummary, Application } from "@/lib/types";
import ApplicationCard from "@/components/ApplicationCard";
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

// ─── Custom tooltip ───────────────────────────────────────────────────────────

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

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Skeleton className="h-64 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
      <Skeleton className="h-[350px] w-full rounded-xl" />
      <div className="space-y-3">
        {[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [recentApps, setRecentApps] = useState<Application[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getAnalyticsSummary().then((r) => setSummary(r.data)),
      getApplications({ limit: 5, sort_by: "newest" }).then((r) =>
        setRecentApps(r.data.items)
      ),
    ])
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <DashboardSkeleton />;

  // ── Derived data ────────────────────────────────────────────────────────────

  const avgScore = summary?.avg_fit_score_pct ?? null;
  const scoreColor =
    avgScore === null ? "text-slate-400"
    : avgScore > 60   ? "text-green-400"
    : avgScore > 40   ? "text-yellow-400"
    : "text-red-400";
  const scoreIconBg =
    avgScore === null ? "bg-slate-500/10"
    : avgScore > 60   ? "bg-green-500/10"
    : avgScore > 40   ? "bg-yellow-500/10"
    : "bg-red-500/10";
  const scoreIconColor =
    avgScore === null ? "text-slate-400"
    : avgScore > 60   ? "text-green-400"
    : avgScore > 40   ? "text-yellow-400"
    : "text-red-400";

  const statCards = [
    {
      icon: <Briefcase className="h-5 w-5 text-blue-400" />,
      iconBg: "bg-blue-500/10",
      value: String(summary?.total_applications ?? 0),
      label: "Total Applications",
      valueColor: "text-white",
    },
    {
      icon: <Target className={`h-5 w-5 ${scoreIconColor}`} />,
      iconBg: scoreIconBg,
      value: avgScore !== null ? `${avgScore}%` : "--",
      label: "Average Fit Score",
      valueColor: scoreColor,
    },
    {
      icon: <Users className="h-5 w-5 text-purple-400" />,
      iconBg: "bg-purple-500/10",
      value: `${summary?.interview_rate ?? 0}%`,
      label: "Interview Rate",
      valueColor: "text-white",
    },
    {
      icon: <Clock className="h-5 w-5 text-orange-400" />,
      iconBg: "bg-orange-500/10",
      value: String(summary?.pending_count ?? 0),
      label: "Pending Analysis",
      valueColor: "text-white",
    },
  ];

  // Weekly applications — strip year, keep W01 etc
  const weeklyData = (summary?.weekly_applications ?? []).map((w) => ({
    week: w.week.replace(/^\d{4}-/, ""),
    count: w.count,
  }));

  // Status donut — filter zero-count entries
  const statusData = Object.entries(summary?.by_status ?? {})
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  // Top 10 missing skills
  const skillGaps = (summary?.top_missing_skills ?? []).slice(0, 10);

  return (
    <div className="space-y-6">

      {/* ── Section 1: Stat cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {statCards.map((c) => (
          <div
            key={c.label}
            className="rounded-xl border border-slate-800 bg-slate-900 p-5"
          >
            <div className={`inline-flex rounded-lg p-2 ${c.iconBg} mb-3`}>
              {c.icon}
            </div>
            <p className={`text-3xl font-bold ${c.valueColor}`}>{c.value}</p>
            <p className="text-sm text-slate-400 mt-1">{c.label}</p>
          </div>
        ))}
      </div>

      {/* ── Section 2: Line + Donut ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Line chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-sm font-semibold text-white mb-4">
            Applications Over Time
          </h2>
          {weeklyData.length === 0 ? (
            <div className="flex items-center justify-center h-[250px]">
              <p className="text-sm text-slate-500">No data yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
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
            Application Status
          </h2>
          {statusData.length === 0 ? (
            <div className="flex items-center justify-center h-[250px]">
              <p className="text-sm text-slate-500">No data yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="45%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {statusData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={STATUS_COLORS[entry.name] ?? "#64748b"}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0];
                    return (
                      <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-lg">
                        <p style={{ color: d.payload.fill }}>{d.name}: <span className="font-semibold text-white">{d.value}</span></p>
                      </div>
                    );
                  }}
                />
                <Legend
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

      {/* ── Section 3: Skill gaps ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-sm font-semibold text-white mb-4">Top Skill Gaps</h2>
        {skillGaps.length === 0 ? (
          <div className="flex items-center justify-center h-24">
            <p className="text-sm text-slate-500">
              Add applications to see your skill gaps
            </p>
          </div>
        ) : (
          <div className="h-[250px] lg:h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={skillGaps}
                layout="vertical"
                margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
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
                <Bar dataKey="count" name="Missing in" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* ── Section 4: Recent applications ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Recent Applications</h2>
          <Link
            href="/applications"
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            View all
          </Link>
        </div>
        {recentApps.length === 0 ? (
          <div className="flex items-center justify-center py-10">
            <p className="text-sm text-slate-500">No applications yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentApps.map((app) => (
              <ApplicationCard key={app.id} application={app} />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
