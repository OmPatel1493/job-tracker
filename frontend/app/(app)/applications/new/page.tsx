"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeft, Loader2 } from "lucide-react";
import { createApplication } from "@/lib/api";

// ─── Schemas ──────────────────────────────────────────────────────────────────

const STATUSES = [
  "saved",
  "applied",
  "phone_screen",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
] as const;

const step1Schema = z.object({
  company_name: z.string().min(1, "Company name is required"),
  job_title: z.string().min(1, "Job title is required"),
  job_url: z.string().url("Must be a valid URL").or(z.literal("")).optional(),
  applied_date: z.string().optional(),
  status: z.enum(STATUSES),
});

const step2Schema = z.object({
  job_description: z
    .string()
    .min(50, "Job description must be at least 50 characters")
    .max(20000, "Job description must be under 20,000 characters"),
  notes: z.string().max(2000, "Notes must be under 2,000 characters").optional(),
});

type Step1Data = z.infer<typeof step1Schema>;
type Step2Data = z.infer<typeof step2Schema>;

// ─── Step indicator ───────────────────────────────────────────────────────────

function StepIndicator({ current }: { current: 1 | 2 }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      {[1, 2].map((step) => (
        <div key={step} className="flex items-center gap-2">
          <div
            className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
              step === current
                ? "bg-blue-600 text-white"
                : step < current
                ? "bg-blue-600/40 text-blue-300"
                : "bg-slate-700 text-slate-400"
            }`}
          >
            {step}
          </div>
          <span
            className={`text-sm ${
              step === current ? "text-white font-medium" : "text-slate-500"
            }`}
          >
            {step === 1 ? "Job Details" : "Description"}
          </span>
          {step < 2 && <div className="h-px w-8 bg-slate-700 ml-1" />}
        </div>
      ))}
      <span className="ml-auto text-xs text-slate-500">Step {current} of 2</span>
    </div>
  );
}

// ─── Field helpers ────────────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-xs text-red-400 mt-1">{message}</p>;
}

const inputCls =
  "w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewApplicationPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [step1Data, setStep1Data] = useState<Step1Data | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Step 1 form
  const form1 = useForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues: { status: "saved" },
  });

  // Step 2 form
  const form2 = useForm<Step2Data>({
    resolver: zodResolver(step2Schema),
  });

  const jdValue = form2.watch("job_description") ?? "";

  function handleStep1(data: Step1Data) {
    setStep1Data(data);
    setStep(2);
  }

  async function handleStep2(data: Step2Data) {
    if (!step1Data) return;
    setSubmitting(true);
    try {
      const res = await createApplication({
        company_name: step1Data.company_name,
        job_title: step1Data.job_title,
        job_url: step1Data.job_url || undefined,
        applied_date: step1Data.applied_date || undefined,
        status: step1Data.status,
        job_description: data.job_description,
        notes: data.notes || undefined,
      });
      toast.success("Application saved! AI analysis running in background.");
      router.push(`/applications/${res.data.id}`);
    } catch {
      toast.error("Failed to save application. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/applications"
          className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <h1 className="text-xl font-semibold text-white">Add New Application</h1>
      </div>

      {/* Card */}
      <div className="rounded-2xl border border-slate-700 bg-slate-800 p-6">
        <StepIndicator current={step} />

        {/* ── Step 1 ── */}
        {step === 1 && (
          <form onSubmit={form1.handleSubmit(handleStep1)} className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Company Name <span className="text-red-400">*</span>
                </label>
                <input
                  {...form1.register("company_name")}
                  placeholder="Acme Corp"
                  className={inputCls}
                />
                <FieldError message={form1.formState.errors.company_name?.message} />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Job Title <span className="text-red-400">*</span>
                </label>
                <input
                  {...form1.register("job_title")}
                  placeholder="Software Engineer"
                  className={inputCls}
                />
                <FieldError message={form1.formState.errors.job_title?.message} />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Job URL
              </label>
              <input
                {...form1.register("job_url")}
                type="text"
                placeholder="https://..."
                className={inputCls}
              />
              <FieldError message={form1.formState.errors.job_url?.message} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Applied Date
                </label>
                <input
                  {...form1.register("applied_date")}
                  type="date"
                  className={`${inputCls} [color-scheme:dark]`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Status
                </label>
                <select
                  {...form1.register("status")}
                  className={inputCls}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s} className="bg-slate-900">
                      {s.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
              >
                Next
              </button>
            </div>
          </form>
        )}

        {/* ── Step 2 ── */}
        {step === 2 && (
          <form onSubmit={form2.handleSubmit(handleStep2)} className="space-y-5">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-slate-300">
                  Job Description <span className="text-red-400">*</span>
                </label>
                <span className="text-xs text-slate-500">
                  {jdValue.length} / 20000
                </span>
              </div>
              <textarea
                {...form2.register("job_description")}
                placeholder="Paste the full job description here..."
                className={`${inputCls} min-h-[300px] resize-y`}
              />
              <FieldError message={form2.formState.errors.job_description?.message} />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Notes
              </label>
              <textarea
                {...form2.register("notes")}
                placeholder="Personal notes about this application..."
                className={`${inputCls} min-h-[120px] resize-y`}
              />
              <FieldError message={form2.formState.errors.notes?.message} />
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded-lg border border-slate-600 px-5 py-2 text-sm font-semibold text-slate-300 hover:text-white hover:border-slate-500 transition-colors"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                Save Application
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
