"use client";

import { useState } from "react";
import { updateApplication, type Application } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import ApplicationForm, { type ApplicationFormData } from "@/components/ApplicationForm";

interface Props {
  application: Application;
  onUpdated: (app: Application) => void;
}

export default function EditApplicationModal({ application, onUpdated }: Props) {
  const [open, setOpen] = useState(false);

  async function handleSubmit(data: ApplicationFormData) {
    const updated = await updateApplication(application.id, {
      company_name: data.company_name,
      job_title: data.job_title,
      status: data.status,
      location: data.location || null,
      is_remote: data.is_remote,
      job_url: data.job_url || null,
      salary_min: data.salary_min ? parseInt(data.salary_min) : null,
      salary_max: data.salary_max ? parseInt(data.salary_max) : null,
    });
    onUpdated(updated);
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {/* Small text button so it fits inline in the application row */}
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs">
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit application</DialogTitle>
        </DialogHeader>
        <ApplicationForm
          initial={application}
          onSubmit={handleSubmit}
          submitLabel="Save changes"
        />
      </DialogContent>
    </Dialog>
  );
}
