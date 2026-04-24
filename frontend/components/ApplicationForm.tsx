"use client";

// Shared form used by both AddApplicationModal and EditApplicationModal.
// WHY shared: both forms have identical fields — only the submit action differs
// (POST vs PATCH). Extracting it avoids duplicating JSX.

import { useState } from "react";
import { type Application, type ApplicationStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STATUSES: ApplicationStatus[] = [
  "applied",
  "screening",
  "interviewing",
  "offer",
  "rejected",
  "withdrawn",
];

export type ApplicationFormData = {
  company_name: string;
  job_title: string;
  status: ApplicationStatus;
  location: string;
  is_remote: boolean;
  job_url: string;
  salary_min: string;
  salary_max: string;
};

interface Props {
  initial?: Partial<Application>;
  onSubmit: (data: ApplicationFormData) => Promise<void>;
  submitLabel: string;
}

export default function ApplicationForm({ initial, onSubmit, submitLabel }: Props) {
  const [companyName, setCompanyName] = useState(initial?.company_name ?? "");
  const [jobTitle, setJobTitle] = useState(initial?.job_title ?? "");
  const [status, setStatus] = useState<ApplicationStatus>(initial?.status ?? "applied");
  const [location, setLocation] = useState(initial?.location ?? "");
  const [isRemote, setIsRemote] = useState(initial?.is_remote ?? false);
  const [jobUrl, setJobUrl] = useState(initial?.job_url ?? "");
  const [salaryMin, setSalaryMin] = useState(initial?.salary_min?.toString() ?? "");
  const [salaryMax, setSalaryMax] = useState(initial?.salary_max?.toString() ?? "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onSubmit({
        company_name: companyName,
        job_title: jobTitle,
        status,
        location,
        is_remote: isRemote,
        job_url: jobUrl,
        salary_min: salaryMin,
        salary_max: salaryMax,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-sm text-destructive font-medium">{error}</p>}

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="company">Company *</Label>
          <Input
            id="company"
            required
            placeholder="Acme Corp"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="title">Job Title *</Label>
          <Input
            id="title"
            required
            placeholder="Software Engineer"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label>Status</Label>
          <Select value={status} onValueChange={(v) => setStatus(v as ApplicationStatus)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s} className="capitalize">
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            placeholder="New York, NY"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="salaryMin">Salary Min ($)</Label>
          <Input
            id="salaryMin"
            type="number"
            placeholder="80000"
            value={salaryMin}
            onChange={(e) => setSalaryMin(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="salaryMax">Salary Max ($)</Label>
          <Input
            id="salaryMax"
            type="number"
            placeholder="120000"
            value={salaryMax}
            onChange={(e) => setSalaryMax(e.target.value)}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="jobUrl">Job URL</Label>
        <Input
          id="jobUrl"
          type="url"
          placeholder="https://..."
          value={jobUrl}
          onChange={(e) => setJobUrl(e.target.value)}
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="remote"
          type="checkbox"
          checked={isRemote}
          onChange={(e) => setIsRemote(e.target.checked)}
          className="h-4 w-4 rounded border-input"
        />
        <Label htmlFor="remote">Remote position</Label>
      </div>

      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? "Saving…" : submitLabel}
      </Button>
    </form>
  );
}
