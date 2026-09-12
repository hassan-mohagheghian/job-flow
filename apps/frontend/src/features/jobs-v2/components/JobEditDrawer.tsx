"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Drawer,
  DrawerHeader,
  DrawerContent,
  DrawerFooter,
} from "@/shared/components/Drawer";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { Button } from "@/shared/ui/button";
import { CircleNotch, Pencil, Warning, X, Plus } from "@phosphor-icons/react";
import { TrackingStatusSelect } from "./TrackingStatusSelect";
import { jobApi } from "@/entities/job/api";
import type {
  JobDetail,
  JobEditInput,
  JobNoteItem,
  JobLinkItem,
} from "@/entities/job/types";

const JOBS_KEY = "jobs-v2-infinite";
const WORK_TYPES = ["On-site", "Remote", "Hybrid"];
const EMPLOYMENT_TYPES = [
  "Full-time",
  "Part-time",
  "Contract",
  "Internship",
  "Temporary",
];

interface JobEditDrawerProps {
  jobId: string | null;
  onOpenChange: (jobId: string | null) => void;
}

function Field({
  label,
  required = false,
  children,
  hint,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-0.5 text-xs text-muted-foreground">
        <span>{label}</span>
        {required && <span className="text-destructive">*</span>}
        {!required && (
          <span className="text-muted-foreground/60">(optional)</span>
        )}
      </label>
      {children}
      {hint && <p className="text-2xs text-destructive">{hint}</p>}
    </div>
  );
}

export function JobEditDrawer({ jobId, onOpenChange }: JobEditDrawerProps) {
  const queryClient = useQueryClient();
  const [detail, setDetail] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [url, setUrl] = useState("");
  const [workTypes, setWorkTypes] = useState<string[]>([]);
  const [employmentTypes, setEmploymentTypes] = useState<string[]>([]);
  const [visa, setVisa] = useState("");
  const [salary, setSalary] = useState("");
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState<JobNoteItem[]>([]);
  const [links, setLinks] = useState<JobLinkItem[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [noteDraft, setNoteDraft] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkTitle, setLinkTitle] = useState("");

  const open = !!jobId;

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    setLoading(true);
    setError(null);
    jobApi
      .getDetail(jobId)
      .then((d) => {
        if (!active) return;
        setDetail(d);
        setTitle(d.title ?? "");
        setRole(d.role ?? "");
        setCompany(d.company_name ?? "");
        setLocation(d.location ?? "");
        setUrl(d.url ?? "");
        setWorkTypes(d.work_types ?? []);
        setEmploymentTypes(d.employment_types ?? []);
        setVisa(d.visa ?? "");
        setSalary(d.salary ?? "");
        setDescription(d.description ?? "");
        setNotes(d.notes ?? []);
        setLinks(d.links ?? []);
        setTags(d.tags ?? []);
      })
      .catch(() => active && setError("Unable to load job details."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [jobId]);

  const urlValid = url.startsWith("http://") || url.startsWith("https://");

  const handleSave = async () => {
    if (!jobId) return;
    if (!urlValid) {
      setError("URL must start with http:// or https://");
      return;
    }
    setSubmitting(true);
    setError(null);
    const payload: JobEditInput = {
      title: title || null,
      role: role.trim() || null,
      company: company.trim() || null,
      location: location.trim() || null,
      url: url.trim(),
      work_types: workTypes.length > 0 ? workTypes : null,
      employment_types: employmentTypes.length > 0 ? employmentTypes : null,
      visa: visa.trim() || null,
      salary: salary.trim() || null,
      description: description.trim() || null,
      notes,
      links,
      tags: tags.length > 0 ? tags : null,
    };
    try {
      await jobApi.updateJob(jobId, payload);
      queryClient.invalidateQueries({ queryKey: [JOBS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["job-detail", jobId] });
      onOpenChange(null);
    } catch {
      setError("Failed to save changes. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Drawer
      open={open}
      onOpenChange={(o) => {
        if (!o) onOpenChange(null);
      }}
    >
      <DrawerHeader
        title={
          <span className="flex items-center gap-1.5">
            <Pencil className="w-3.5 h-3.5" /> Edit Job
          </span>
        }
        onClose={() => onOpenChange(null)}
      />
      <DrawerContent>
        {loading && (
          <div className="flex items-center justify-center h-40">
            <CircleNotch className="w-6 h-6 text-muted-foreground animate-spin" />
          </div>
        )}

        {!loading && error && !detail && (
          <div className="flex items-start gap-1 text-xs text-destructive bg-destructive/10 rounded p-2 m-4">
            <Warning className="w-3.5 h-3.5 shrink-0" />
            {error}
          </div>
        )}

        {!loading && detail && (
          <div className="space-y-3">
            <Field label="Title">
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Staff Software Engineer"
              />
            </Field>
            <Field label="Tracking">
              <div className="pt-1">
                <TrackingStatusSelect jobId={detail.id} />
              </div>
            </Field>
            <Field label="Role">
              <Input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="Backend Engineer"
              />
            </Field>
            <Field label="Company">
              <Input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Acme GmbH"
              />
            </Field>
            <Field label="Location">
              <Input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Berlin"
              />
            </Field>
            <Field
              label="Job Post URL"
              required
              hint={
                !urlValid && url
                  ? "URL must start with http:// or https://"
                  : undefined
              }
            >
              <Input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://..."
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Work Type">
                <Select
                  value={workTypes[0] || undefined}
                  onValueChange={(v) => setWorkTypes([v])}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {WORK_TYPES.map((t) => (
                      <SelectItem key={t} value={t} className="text-xs">
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Employment Type">
                <Select
                  value={employmentTypes[0] || undefined}
                  onValueChange={(v) => setEmploymentTypes([v])}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {EMPLOYMENT_TYPES.map((t) => (
                      <SelectItem key={t} value={t} className="text-xs">
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Visa">
                <Input
                  value={visa}
                  onChange={(e) => setVisa(e.target.value)}
                  placeholder="Strong"
                />
              </Field>
              <Field label="Salary">
                <Input
                  value={salary}
                  onChange={(e) => setSalary(e.target.value)}
                  placeholder="€90k - €110k"
                />
              </Field>
            </div>

            <Field label="Notes">
              <div className="space-y-1.5">
                {notes.map((n, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-1 rounded border bg-muted/50 px-2 py-1 text-2xs"
                  >
                    <div className="flex-1 min-w-0">
                      {n.title && (
                        <div className="text-muted-foreground truncate">
                          {n.title}
                        </div>
                      )}
                      <div className="break-all whitespace-pre-wrap">
                        {n.content}
                      </div>
                    </div>
                    <button
                      onClick={() => setNotes(notes.filter((_, j) => j !== i))}
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                <div className="flex gap-1">
                  <Textarea
                    value={noteDraft}
                    onChange={(e) => setNoteDraft(e.target.value)}
                    placeholder="Add a note..."
                    className="h-8 min-h-0 text-xs resize-none flex-1"
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-8 px-2 shrink-0"
                    disabled={!noteDraft.trim()}
                    aria-label="Add note"
                    onClick={() => {
                      setNotes([...notes, { content: noteDraft.trim() }]);
                      setNoteDraft("");
                    }}
                  >
                    <Plus className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </Field>

            <Field label="Links">
              <div className="space-y-1.5">
                {links.map((l, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-1 rounded border bg-muted/50 px-2 py-1 text-2xs"
                  >
                    <div className="flex-1 min-w-0">
                      <a
                        href={l.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline break-all"
                      >
                        {l.url}
                      </a>
                      {l.title && (
                        <div className="text-muted-foreground truncate">
                          {l.title}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => setLinks(links.filter((_, j) => j !== i))}
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                <div className="space-y-1">
                  <div className="flex gap-1">
                    <Input
                      type="url"
                      value={linkUrl}
                      onChange={(e) => setLinkUrl(e.target.value)}
                      placeholder="Link URL (https://...)"
                      className="h-8 flex-1"
                    />
                    <Input
                      value={linkTitle}
                      onChange={(e) => setLinkTitle(e.target.value)}
                      placeholder="Title (optional)"
                      className="h-8 flex-1"
                    />
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-8 px-2 shrink-0"
                      disabled={
                        !linkUrl.trim() || !linkUrl.trim().startsWith("http")
                      }
                      aria-label="Add link"
                      onClick={() => {
                        setLinks([
                          ...links,
                          {
                            url: linkUrl.trim(),
                            title: linkTitle.trim() || null,
                          },
                        ]);
                        setLinkUrl("");
                        setLinkTitle("");
                      }}
                    >
                      <Plus className="w-3 h-3" />
                    </Button>
                  </div>
                  {linkUrl && !linkUrl.startsWith("http") && (
                    <p className="text-2xs text-destructive">
                      URL must start with http:// or https://
                    </p>
                  )}
                </div>
              </div>
            </Field>

            <Field label="Description">
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Job description..."
                className="min-h-[80px] text-xs resize-none"
              />
            </Field>

            <Field label="Tags">
              <div className="space-y-1.5">
                {tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {tags.map((t, i) => (
                      <span
                        key={`${t}-${i}`}
                        className="inline-flex items-center gap-1 text-2xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border"
                      >
                        {t}
                        <button
                          onClick={() => setTags(tags.filter((_, j) => j !== i))}
                          className="text-muted-foreground hover:text-destructive"
                        >
                          <X className="w-2.5 h-2.5" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex gap-1">
                  <Input
                    value={tagDraft}
                    onChange={(e) => setTagDraft(e.target.value)}
                    placeholder="Add a tag..."
                    className="h-8 text-xs flex-1"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && tagDraft.trim()) {
                        e.preventDefault()
                        if (!tags.includes(tagDraft.trim())) {
                          setTags([...tags, tagDraft.trim()])
                        }
                        setTagDraft("")
                      }
                    }}
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-8 px-2 shrink-0"
                    disabled={!tagDraft.trim() || tags.includes(tagDraft.trim())}
                    aria-label="Add tag"
                    onClick={() => {
                      if (tagDraft.trim() && !tags.includes(tagDraft.trim())) {
                        setTags([...tags, tagDraft.trim()])
                        setTagDraft("")
                      }
                    }}
                  >
                    <Plus className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </Field>

            {error && detail && (
              <div className="flex items-start gap-1 text-xs text-destructive bg-destructive/10 rounded p-2">
                <Warning className="w-3.5 h-3.5 shrink-0" />
                {error}
              </div>
            )}
          </div>
        )}
      </DrawerContent>

      {!loading && detail && (
        <DrawerFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(null)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleSave}
            disabled={submitting}
          >
            {submitting ? "Saving..." : "Save"}
          </Button>
        </DrawerFooter>
      )}
    </Drawer>
  );
}
