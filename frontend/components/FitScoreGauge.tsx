"use client";

import { useEffect, useState } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Size = "sm" | "md" | "lg";

interface Props {
  score: number | null;
  size?: Size;
  showLabel?: boolean;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const SIZE_CONFIG: Record<Size, { diameter: number; strokeWidth: number; fontSize: string; pctSize: string }> = {
  sm: { diameter: 80,  strokeWidth: 6,  fontSize: "text-xl",  pctSize: "text-xs" },
  md: { diameter: 120, strokeWidth: 8,  fontSize: "text-3xl", pctSize: "text-sm" },
  lg: { diameter: 160, strokeWidth: 10, fontSize: "text-4xl", pctSize: "text-base" },
};

function scoreColor(score: number | null): { stroke: string; text: string } {
  if (score === null || score === 0) return { stroke: "#475569", text: "text-slate-500" }; // slate-600 / slate-500
  if (score <= 40)  return { stroke: "#ef4444", text: "text-red-400" };    // red-500 / red-400
  if (score <= 70)  return { stroke: "#eab308", text: "text-yellow-400" }; // yellow-500 / yellow-400
  return               { stroke: "#22c55e", text: "text-green-400" };      // green-500 / green-400
}

function deriveLabel(score: number | null): string {
  if (score === null) return "Not Analyzed";
  if (score <= 40)    return "Poor Fit";
  if (score <= 70)    return "Moderate Fit";
  return "Strong Fit";
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function FitScoreGauge({
  score,
  size = "md",
  showLabel = true,
}: Props) {
  const [animated, setAnimated] = useState(0);
  const cfg = SIZE_CONFIG[size];
  const { stroke, text } = scoreColor(score);

  const radius = (cfg.diameter - cfg.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const target = score ?? 0;

  // Animate from 0 → target on mount
  useEffect(() => {
    if (target === 0) return;
    let start: number | null = null;
    const duration = 900; // ms

    function step(ts: number) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimated(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }, [target]);

  const offset = circumference - (animated / 100) * circumference;
  const cx = cfg.diameter / 2;
  const cy = cfg.diameter / 2;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg
        width={cfg.diameter}
        height={cfg.diameter}
        style={{ transform: "rotate(-90deg)" }}
      >
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke="#1e293b"
          strokeWidth={cfg.strokeWidth}
        />
        {/* Progress */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={stroke}
          strokeWidth={cfg.strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.05s linear" }}
        />
        {/* Center text — counter-rotate so it reads upright */}
        <g style={{ transform: `rotate(90deg)`, transformOrigin: `${cx}px ${cy}px` }}>
          {score !== null ? (
            <>
              <text
                x={cx}
                y={cy - 4}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="white"
                className={`font-bold ${cfg.fontSize}`}
                style={{ fontSize: size === "lg" ? 36 : size === "md" ? 28 : 20, fontWeight: 700 }}
              >
                {animated}
              </text>
              <text
                x={cx}
                y={cy + (size === "lg" ? 22 : size === "md" ? 18 : 14)}
                textAnchor="middle"
                fill="#94a3b8"
                style={{ fontSize: size === "lg" ? 14 : 12 }}
              >
                %
              </text>
            </>
          ) : (
            <text
              x={cx}
              y={cy}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#64748b"
              style={{ fontSize: size === "lg" ? 32 : size === "md" ? 24 : 18, fontWeight: 700 }}
            >
              --
            </text>
          )}
        </g>
      </svg>

      {showLabel && (
        <span className={`text-sm font-medium ${text}`}>
          {deriveLabel(score)}
        </span>
      )}
    </div>
  );
}
