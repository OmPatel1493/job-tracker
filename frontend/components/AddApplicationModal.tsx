"use client";

import { useState } from "react";
import { createApplication, type Application } from "@/lib/api";
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
  onCreated: (app: Application) => void;
}

export default function AddApplicationModal({ onCreated }: Props) {
  const [open, setOpen] = useState(false);

  async function handleSubmit(data: ApplicationFormData) {
    const created = await createApplication({
      company_name: data.company_name,
      job_title: data.job_title,
      status: data.status,
      location: data.location || null,
      is_remote: data.is_remote,
      job_url: data.job_url || null,
      job_description: null,
      application_date: null,
      salary_min: data.salary_min ? parseInt(data.salary_min) : null,
      salary_max: data.salary_max ? parseInt(data.salary_max) : null,
    });
    onCreated(created);
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">+ Add application</Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add application</DialogTitle>
        </DialogHeader>
        <ApplicationForm onSubmit={handleSubmit} submitLabel="Add application" />
      </DialogContent>
    </Dialog>
  );
}
