"use client";

import { useState, useEffect, type ReactNode } from "react";
import {
  Drawer,
  DrawerHeader,
  DrawerContent,
  DrawerFooter,
} from "@/shared/components/Drawer";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import {
  Plus,
  X,
  Warning,
  LinkSimple,
  Note,
  CircleNotch,
  Buildings,
  ClipboardText,
} from "@phosphor-icons/react";
import { cn } from "@/shared/lib/utils";
import { readClipboardUrl } from "@/shared/lib/clipboard";
import { gradeForScore, scoreColor } from "@/shared/lib/grade";
import { GradeBadge } from "@/shared/components/GradeBadge";
import { RankBadge } from "@/shared/components/RankBadge";
import type { JobSummary } from "@/entities/job/types";
import { formatCompanyType } from "@/entities/company/lib";
import { TrackingStatusSelect } from "@/features/jobs-v2/components/TrackingStatusSelect";

export type CreateEntityMode = "job" | "company";

export interface CreateEntityLinkItem {
  url: string;
  title: string;
}

export interface CreateEntityNoteItem {
  title?: string;
  content: string;
}

export interface CreateEntityFormData {
  mode: CreateEntityMode;
  job_post_url?: string;
  job_title?: string;
  name?: string;
  primaryLink?: CreateEntityLinkItem;
  links: CreateEntityLinkItem[];
  notes: CreateEntityNoteItem[];
  queue: boolean;
}

interface CreateEntityDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: CreateEntityMode;
  onSubmit: (data: CreateEntityFormData) => void;
  submitting?: boolean;
  error?: string | null;
  errorLink?: { label: string; href: string } | null;
  clipboardUrl?: string | null;
  existingJob?: JobSummary | null;
  onViewJobDetails?: (jobId: string) => void;
}

const LINK_PRESETS = ["LinkedIn", "Website", "Careers", "GitHub"];
const PRIMARY_TITLE_PRESETS = ["Website", "LinkedIn"];
const JOB_NOTE_PRESETS = ["Requirements", "Benefits", "Salary", "Description"];

function normalizeUrl(value: string): string {
  let url = value.trim();
  if (!url.startsWith("http")) url = "https://" + url;
  return url;
}

function SummaryRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 min-w-0">
      <span className="text-2xs text-muted-foreground uppercase tracking-wide shrink-0">
        {label}
      </span>
      <span className="text-xs text-foreground text-right break-words min-w-0">{value ?? "—"}</span>
    </div>
  );
}

function JobScoreCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center">
      <div className={`text-lg font-bold ${scoreColor(value)}`}>{value}</div>
      <div className="text-2xs uppercase tracking-wider text-muted-foreground font-semibold">
        {label}
      </div>
    </div>
  );
}

function JobSummaryCard({
  job,
  onViewDetails,
}: {
  job: JobSummary;
  onViewDetails?: (jobId: string) => void;
}) {
  return (
    <div className="rounded-lg border bg-background/50 p-3 space-y-3">
      <div className="flex justify-between gap-2">
        <div className="flex items-center gap-3 mb-1 flex-wrap">
          <GradeBadge grade={gradeForScore(job.overall_score)} className="w-10 h-8 text-sm" />
          {job.overall_score != null && (
            <JobScoreCard label="Overall" value={job.overall_score} />
          )}
          {job.success_score != null && (
            <JobScoreCard label="Success" value={job.success_score} />
          )}
          {job.fit_score != null && <JobScoreCard label="Fit" value={job.fit_score} />}
          <RankBadge rank={job.rank ?? null} />
        </div>
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline mt-2 shrink-0"
          >
            <LinkSimple className="w-3.5 h-3.5" /> Open job posting
          </a>
        )}
      </div>
      <div>
        <p className="text-base font-semibold text-foreground break-words">
          {job.title || "Untitled"}
        </p>
        <div className="grid grid-cols-2 gap-x-12">
          <div className="min-w-0">
            <SummaryRow label="Company" value={job.company} />
            {job.company_type && (
              <SummaryRow label="Type" value={formatCompanyType(job.company_type)} />
            )}
            <SummaryRow label="Location" value={job.location} />
            <SummaryRow label="Visa" value={job.visa} />
            <SummaryRow
              label="Application"
              value={<TrackingStatusSelect jobId={job.id} />}
            />
          </div>
          <div className="min-w-0">
            <SummaryRow label="Employment" value={job.employment_types?.join(", ")} />
            <SummaryRow label="Salary" value={job.salary} />
            <SummaryRow label="Work Types" value={job.work_types?.join(", ")} />
          </div>
        </div>
      </div>
      {onViewDetails && (
        <button
          type="button"
          onClick={() => onViewDetails(job.id)}
          className="w-full text-xs text-primary font-medium hover:underline text-left"
        >
          View full job details
        </button>
      )}
    </div>
  );
}

export default function CreateEntityDrawer({
  open,
  onOpenChange,
  mode,
  onSubmit,
  submitting = false,
  error = null,
  errorLink = null,
  clipboardUrl = null,
  existingJob = null,
  onViewJobDetails,
}: CreateEntityDrawerProps) {
  const isCompany = mode === "company";

  const [urlInput, setUrlInput] = useState("");
  const [titleInput, setTitleInput] = useState("");

  const [companyName, setCompanyName] = useState("");
  const [primaryUrl, setPrimaryUrl] = useState("");
  const [primaryTitle, setPrimaryTitle] = useState("");

  const [links, setLinks] = useState<CreateEntityLinkItem[]>([]);
  const [showLinkInput, setShowLinkInput] = useState(false);
  const [newLinkTitle, setNewLinkTitle] = useState("");
  const [newLinkUrl, setNewLinkUrl] = useState("");

  const [notes, setNotes] = useState<CreateEntityNoteItem[]>([]);
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [newNoteContent, setNewNoteContent] = useState("");

  useEffect(() => {
    if (!open) return;
    // Clear the link field first so every open starts fresh, then prefill from
    // the gesture-captured clipboardUrl (or, as a fallback, read the clipboard).
    // Replacing (not `prev || url`) also overwrites any stale value left behind
    // by a programmatic close that skipped the reset.
    if (isCompany) {
      setPrimaryUrl("");
    } else {
      setUrlInput("");
    }
    let cancelled = false;
    // Prefer a URL captured inside the user gesture (the open trigger), which
    // satisfies the clipboard-read permission, over an async effect-time read
    // that is outside the gesture and can be rejected on the first open.
    const url = clipboardUrl?.trim() ?? "";
    if (url) {
      if (isCompany) {
        setPrimaryUrl(url);
      } else {
        setUrlInput(url);
      }
    } else {
      readClipboardUrl().then((readUrl) => {
        if (cancelled || !readUrl) return;
        if (isCompany) {
          setPrimaryUrl(readUrl);
        } else {
          setUrlInput(readUrl);
        }
      });
    }
    return () => {
      cancelled = true;
    };
  }, [open, isCompany, clipboardUrl]);

  const urlValid = urlInput.trim().startsWith("http");

  const handleAddLink = () => {
    if (!newLinkUrl.trim()) return;
    setLinks((prev) => [
      ...prev,
      { url: normalizeUrl(newLinkUrl), title: newLinkTitle.trim() },
    ]);
    setNewLinkUrl("");
    setNewLinkTitle("");
    setShowLinkInput(false);
  };

  const handleRemoveLink = (index: number) => {
    setLinks((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAddNote = () => {
    if (!newNoteContent.trim()) return;
    setNotes((prev) => [
      ...prev,
      {
        title: isCompany ? undefined : newNoteTitle.trim(),
        content: newNoteContent.trim(),
      },
    ]);
    setNewNoteContent("");
    setNewNoteTitle("");
    setShowNoteInput(false);
  };

  const handleRemoveNote = (index: number) => {
    setNotes((prev) => prev.filter((_, i) => i !== index));
  };

  const canSubmit = isCompany
    ? primaryUrl.trim().startsWith("http")
    : !!urlInput.trim() && urlValid;

  const buildData = (queue: boolean): CreateEntityFormData => {
    if (isCompany) {
      return {
        mode,
        name: companyName.trim() || undefined,
        primaryLink: { url: primaryUrl.trim(), title: primaryTitle },
        links,
        notes,
        queue,
      };
    }
    return {
      mode,
      job_post_url: urlInput.trim(),
      job_title: titleInput.trim() || undefined,
      links,
      notes,
      queue,
    };
  };

  const handleSubmit = (queue: boolean) => {
    if (!canSubmit || submitting) return;
    onSubmit(buildData(queue));
  };

  const handleJobEnterKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit(true);
    }
  };

  const handleOpenChange = (next: boolean) => {
    onOpenChange(next);
    if (!next) {
      setUrlInput("");
      setTitleInput("");
      setCompanyName("");
      setPrimaryUrl("");
      setPrimaryTitle("");
      setLinks([]);
      setNotes([]);
      setShowLinkInput(false);
      setNewLinkUrl("");
      setNewLinkTitle("");
      setShowNoteInput(false);
      setNewNoteContent("");
      setNewNoteTitle("");
    }
  };

  const presetDisabledInLinks = (label: string) =>
    isCompany &&
    (label === "Website" || label === "LinkedIn") &&
    primaryTitle === label;

  return (
    <Drawer open={open} onOpenChange={handleOpenChange}>
      <DrawerHeader
        title={
          <span className="flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" />{" "}
            {isCompany ? "Add Company" : "Import Job"}
          </span>
        }
        onClose={() => handleOpenChange(false)}
      />
      <DrawerContent>
        <div className="space-y-4">
          {isCompany ? (
            <>
              {/* Primary Link */}
              <div>
                <label className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <LinkSimple className="w-3.5 h-3.5" />
                  <span>Primary Link</span>
                  <span className="text-destructive">*</span>
                </label>
                <Input
                  type="url"
                  value={primaryUrl}
                  onChange={(e) => setPrimaryUrl(e.target.value)}
                  placeholder="https://acme.example"
                  className={cn(
                    "w-full",
                    primaryUrl &&
                      !primaryUrl.trim().startsWith("http") &&
                      "border-destructive",
                  )}
                  autoFocus
                />
                {primaryUrl && !primaryUrl.trim().startsWith("http") && (
                  <p className="text-xs text-destructive mt-1">
                    URL must start with http:// or https://
                  </p>
                )}
                <p className="flex items-center gap-1 text-2xs text-muted-foreground/70 mt-1">
                  <ClipboardText className="w-3 h-3" />
                  Tip: a copied link is auto-filled from your clipboard
                </p>
                <div className="flex items-center gap-1 mt-1.5">
                  {PRIMARY_TITLE_PRESETS.map((label) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() =>
                        setPrimaryTitle(primaryTitle === label ? "" : label)
                      }
                      className={cn(
                        "h-6 px-2 rounded text-xs border transition-colors",
                        primaryTitle === label
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background text-muted-foreground border-border hover:bg-muted",
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Company Name */}
              <div>
                <label className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <span>Company Name</span>
                  <span className="text-muted-foreground/60">(optional)</span>
                </label>
                <Input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Acme GmbH"
                />
              </div>

              <hr className="border-border" />
            </>
          ) : (
            <>
              {/* Job Post URL */}
              <div>
                <label className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <span>Job Post URL</span>
                  <span className="text-destructive">*</span>
                </label>
                <Input
                  type="url"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://linkedin.com/jobs/view/..."
                  className={cn(
                    "w-full",
                    urlInput && !urlValid && "border-destructive",
                  )}
                  onKeyDown={handleJobEnterKey}
                  autoFocus
                />
                {urlInput && !urlValid && (
                  <p className="text-xs text-destructive mt-1">
                    URL must start with http:// or https://
                  </p>
                )}
                <p className="flex items-center gap-1 text-2xs text-muted-foreground/70 mt-1">
                  <ClipboardText className="w-3 h-3" />
                  Tip: a copied link is auto-filled from your clipboard
                </p>
              </div>

              {/* Job Title */}
              <div>
                <label className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <span>Job Title</span>
                  <span className="text-muted-foreground/60">(optional)</span>
                </label>
                <Input
                  type="text"
                  value={titleInput}
                  onChange={(e) => setTitleInput(e.target.value)}
                  placeholder="Senior Backend Engineer"
                  onKeyDown={handleJobEnterKey}
                />
              </div>

              <hr className="border-border" />
            </>
          )}

          {/* Additional Links */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <LinkSimple className="w-3.5 h-3.5" />
                <span>Additional Links</span>
              </div>
              {!showLinkInput && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs gap-1"
                  onClick={() => setShowLinkInput(true)}
                >
                  <Plus className="w-3 h-3" /> Add Link
                </Button>
              )}
            </div>

            {links.length === 0 && !showLinkInput && (
              <p className="text-xs text-muted-foreground/60">
                No additional links
              </p>
            )}

            {links.length > 0 && (
              <div className="space-y-2 mb-3">
                {links.map((link, i) => (
                  <div
                    key={i}
                    className="rounded border bg-muted/50 p-2 space-y-1"
                  >
                    {link.title && (
                      <p className="text-xs font-medium">{link.title}</p>
                    )}
                    <div className="flex items-start gap-1">
                      <LinkSimple className="w-3 h-3 text-primary shrink-0 mt-0.5" />
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary hover:underline break-all flex-1 min-w-0"
                      >
                        {link.url}
                      </a>
                      <button
                        onClick={() => handleRemoveLink(i)}
                        className="shrink-0 text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showLinkInput && (
              <div className="rounded border bg-muted/50 p-3 space-y-2">
                <div>
                  <label className="text-xs text-muted-foreground mb-0.5 block">
                    Title (optional)
                  </label>
                  <div className="flex items-center gap-1">
                    {LINK_PRESETS.map((label) => (
                      <button
                        key={label}
                        type="button"
                        disabled={presetDisabledInLinks(label)}
                        onClick={() =>
                          setNewLinkTitle(newLinkTitle === label ? "" : label)
                        }
                        className={cn(
                          "h-6 px-2 rounded text-xs border transition-colors",
                          newLinkTitle === label
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-background text-muted-foreground border-border hover:bg-muted",
                          presetDisabledInLinks(label) &&
                            "opacity-40 pointer-events-none",
                        )}
                      >
                        {label}
                      </button>
                    ))}
                    <Input
                      type="text"
                      value={newLinkTitle}
                      onChange={(e) => setNewLinkTitle(e.target.value)}
                      placeholder="Custom"
                      className="h-6 text-xs flex-1"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-0.5 block">
                    URL *
                  </label>
                  <Input
                    type="url"
                    value={newLinkUrl}
                    onChange={(e) => setNewLinkUrl(e.target.value)}
                    placeholder="https://..."
                    className="h-7 text-xs"
                    onKeyDown={(e) => e.key === "Enter" && handleAddLink()}
                  />
                </div>
                <div className="flex justify-end gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 text-xs"
                    onClick={() => {
                      setShowLinkInput(false);
                      setNewLinkUrl("");
                      setNewLinkTitle("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    variant="default"
                    className="h-6 text-xs"
                    disabled={!newLinkUrl.trim()}
                    onClick={handleAddLink}
                  >
                    Add
                  </Button>
                </div>
              </div>
            )}
          </div>

          <hr className="border-border" />

          {/* Notes */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Note className="w-3.5 h-3.5" />
                <span>Notes</span>
              </div>
              {!showNoteInput && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs gap-1"
                  onClick={() => setShowNoteInput(true)}
                >
                  <Plus className="w-3 h-3" /> Add Note
                </Button>
              )}
            </div>

            {notes.length === 0 && !showNoteInput && (
              <p className="text-xs text-muted-foreground/60">No notes</p>
            )}

            {notes.length > 0 && (
              <div className="space-y-2 mb-3">
                {notes.map((note, i) => (
                  <div
                    key={i}
                    className="rounded border bg-muted/50 p-2 space-y-1"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <div className="flex-1 min-w-0">
                        {note.title && (
                          <p className="text-xs font-medium">{note.title}</p>
                        )}
                        <p className="text-xs text-muted-foreground whitespace-pre-wrap">
                          {note.content}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRemoveNote(i)}
                        className="shrink-0 text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showNoteInput && (
              <div className="rounded border bg-muted/50 p-3 space-y-2">
                {!isCompany && (
                  <div>
                    <label className="text-xs text-muted-foreground mb-0.5 block">
                      Title (optional)
                    </label>
                    <div className="flex items-center gap-1">
                      {JOB_NOTE_PRESETS.map((label) => (
                        <button
                          key={label}
                          type="button"
                          onClick={() =>
                            setNewNoteTitle(newNoteTitle === label ? "" : label)
                          }
                          className={cn(
                            "h-6 px-2 rounded text-xs border transition-colors",
                            newNoteTitle === label
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-background text-muted-foreground border-border hover:bg-muted",
                          )}
                        >
                          {label}
                        </button>
                      ))}
                      <Input
                        type="text"
                        value={newNoteTitle}
                        onChange={(e) => setNewNoteTitle(e.target.value)}
                        placeholder="Custom"
                        className="h-6 text-xs flex-1"
                      />
                    </div>
                  </div>
                )}
                <div>
                  <label className="text-xs text-muted-foreground mb-0.5 block">
                    Content *
                  </label>
                  <Textarea
                    value={newNoteContent}
                    onChange={(e) => setNewNoteContent(e.target.value)}
                    placeholder="Raw copied text..."
                    className="min-h-[60px] text-xs resize-none"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                        e.preventDefault();
                        handleAddNote();
                      }
                    }}
                  />
                </div>
                <div className="flex justify-end gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 text-xs"
                    onClick={() => {
                      setShowNoteInput(false);
                      setNewNoteContent("");
                      setNewNoteTitle("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    variant="default"
                    className="h-6 text-xs"
                    disabled={!newNoteContent.trim()}
                    onClick={handleAddNote}
                  >
                    Add
                  </Button>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs text-destructive bg-destructive/10 rounded p-2">
                <Warning className="w-3.5 h-3.5 shrink-0" />
                <span className="flex-1 min-w-0">{error}</span>
                {errorLink && (
                  <a
                    href={errorLink.href}
                    className="shrink-0 font-semibold text-destructive underline underline-offset-2"
                  >
                    {errorLink.label}
                  </a>
                )}
              </div>
              {existingJob && (
                <JobSummaryCard job={existingJob} onViewDetails={onViewJobDetails} />
              )}
            </div>
          )}
        </div>
      </DrawerContent>

      <DrawerFooter>
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleOpenChange(false)}
          disabled={submitting}
        >
          Cancel
        </Button>
        {isCompany ? (
          <>
            <Button
              variant="default"
              size="sm"
              disabled={!canSubmit || submitting}
              onClick={() => handleSubmit(false)}
            >
              {submitting ? (
                <CircleNotch className="w-3 h-3 animate-spin" />
              ) : (
                <Plus className="w-3 h-3" />
              )}
              {submitting ? "Adding..." : "Add"}
            </Button>
            <Button variant="secondary" size="sm" disabled>
              {submitting ? (
                <CircleNotch className="w-3 h-3 animate-spin" />
              ) : (
                <Buildings className="w-3 h-3" />
              )}
              Add & Process
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="default"
              size="sm"
              disabled={!canSubmit || submitting}
              onClick={() => handleSubmit(false)}
            >
              {submitting ? (
                <CircleNotch className="w-3 h-3 animate-spin" />
              ) : (
                <Plus className="w-3 h-3" />
              )}
              {submitting ? "Adding..." : "Add"}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!canSubmit || submitting}
              onClick={() => handleSubmit(true)}
            >
              {submitting ? (
                <CircleNotch className="w-3 h-3 animate-spin" />
              ) : (
                <Buildings className="w-3 h-3" />
              )}
              {submitting ? "Adding..." : "Add & Queue"}
            </Button>
          </>
        )}
      </DrawerFooter>
    </Drawer>
  );
}
