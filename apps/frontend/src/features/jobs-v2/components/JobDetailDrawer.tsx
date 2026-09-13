"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Drawer,
  DrawerHeader,
  DrawerContent,
} from "@/shared/components/Drawer";
import {
  CircleNotch,
  Clock,
  CheckCircle,
  XCircle,
  LinkSimple,
  PencilSimple,
  CaretDown,
  CaretRight,
  Question,
  PaperPlaneTilt,
  Repeat,
  ArrowsClockwise,
} from "@phosphor-icons/react";
import { jobApi } from "@/entities/job/api";
import type { JobDetail, JobDetailWorkflowStep } from "@/entities/job/types";
import { formatCompanyType } from "@/entities/company/lib";
import DateTime from "@/shared/components/DateTime";
import NotesLinksReadOnly from "@/shared/components/NotesLinksReadOnly";
import { GradeBadge } from "@/shared/components/GradeBadge";
import { RankBadge } from "@/shared/components/RankBadge";
import { gradeForScore, scoreColor } from "@/shared/lib/grade";
import { RecommendationBadge } from "./RecommendationBadge";
import { TrackingStatusSelect } from "./TrackingStatusSelect";
import { DismissDialog } from "./DismissDialog";
import { CompanyPicker } from "./CompanyPicker";
import { Button } from "@/shared/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/shared/ui/tooltip";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/shared/ui/collapsible";

interface JobDetailDrawerProps {
  jobId: string | null;
  onOpenChange: (jobId: string | null) => void;
  onEdit?: (id: string) => void;
  onReprocess?: (id: string) => void;
}

function stepIcon(status: JobDetailWorkflowStep["status"]) {
  switch (status) {
    case "processing":
      return (
        <CircleNotch className="w-3.5 h-3.5 text-emerald-500 animate-spin shrink-0" />
      );
    case "completed":
      return <CheckCircle className="w-3.5 h-3.5 text-green-500 shrink-0" />;
    case "failed":
      return <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />;
    case "skipped":
      return (
        <Clock className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
      );
    default:
      return <Clock className="w-3.5 h-3.5 text-blue-500 shrink-0" />;
  }
}

function StepItem({
  step,
  depth,
}: {
  step: JobDetailWorkflowStep;
  depth: number;
}) {
  return (
    <div className="min-w-0">
      <div
        className="flex items-start gap-2 p-1 min-w-0"
        style={{ paddingLeft: `${depth * 16}px` }}
      >
        {stepIcon(step.status)}
        <div className="flex-1 min-w-0 overflow-hidden">
          <p className="text-2xs font-medium text-foreground min-w-0 break-words">
            {step.title}
          </p>
          {step.error && (
            <p className="text-2xs text-red-500 break-words">
              {step.error.message}
            </p>
          )}
        </div>
        {step.progress !== null && step.progress !== undefined && (
          <span className="text-2xs text-muted-foreground shrink-0">
            {Math.round(step.progress)}%
          </span>
        )}
      </div>
      {step.children.map((child) => (
        <StepItem key={child.id} step={child} depth={depth + 1} />
      ))}
    </div>
  );
}

function TruncatedValue({ value }: { value: string | null | undefined }) {
  const [expanded, setExpanded] = useState(false);
  const text = value || "—";

  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className={`inline-block align-middle text-left cursor-pointer ${
              expanded
                ? "whitespace-normal break-words"
                : "max-w-[30ch] truncate"
            }`}
            aria-label={
              expanded ? "Collapse value" : "Expand to see full value"
            }
          >
            {text}
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs break-words">
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5">
      <span className="text-2xs text-muted-foreground uppercase tracking-wide shrink-0">
        {label}
      </span>
      <span className="text-xs text-foreground text-right break-words">
        {value ?? "—"}
      </span>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md border border-border/60 px-2 py-0.5 text-2xs font-medium text-foreground">
      {children}
    </span>
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

function ScoresExplanationBody({
  explanation,
}: {
  explanation: NonNullable<
    NonNullable<JobDetail["analysis"]>["scores_explanation"]
  >;
}) {
  return (
    <>
      {explanation.fit_factors.length > 0 && (
        <>
          <p className="text-2xs font-medium text-muted-foreground uppercase mb-1">
            Why it fits
          </p>
          <ul className="mb-2 space-y-1">
            {explanation.fit_factors.map((f, i) => (
              <li key={i} className="text-xs text-foreground flex gap-1.5">
                <span className="shrink-0">•</span>
                <span className="break-words">{f}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {explanation.success_factors.length > 0 && (
        <>
          <p className="text-2xs font-medium text-muted-foreground uppercase mb-1">
            Chance of success
          </p>
          <ul className="mb-2 space-y-1">
            {explanation.success_factors.map((f, i) => (
              <li key={i} className="text-xs text-foreground flex gap-1.5">
                <span className="shrink-0">•</span>
                <span className="break-words">{f}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {explanation.concerns.length > 0 && (
        <>
          <p className="text-2xs font-medium text-muted-foreground uppercase mb-1">
            Concerns
          </p>
          <ul className="space-y-1">
            {explanation.concerns.map((c, i) => (
              <li key={i} className="text-xs text-red-500/90 flex gap-1.5">
                <span className="shrink-0">•</span>
                <span className="break-words">{c}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

function ScoresExplanationButton({
  explanation,
}: {
  explanation: NonNullable<
    NonNullable<JobDetail["analysis"]>["scores_explanation"]
  >;
}) {
  const [hovered, setHovered] = useState(false);
  const [pinned, setPinned] = useState(false);
  const open = hovered || pinned;

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setHovered(false);
          setPinned(false);
        }
      }}
    >
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className="flex items-center"
      >
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label="Show scores explanation"
            onClick={() => setPinned((p) => !p)}
            className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2 py-1 text-2xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
          >
            <Question className="w-3.5 h-3.5" />
            Why
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="start"
          className="w-80 p-3"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
            Scores Explanation
          </p>
          <ScoresExplanationBody explanation={explanation} />
        </PopoverContent>
      </div>
    </Popover>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
      <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
        {title}
      </p>
      {children}
    </div>
  );
}

function AnalysisSection({
  analysis,
}: {
  analysis: NonNullable<JobDetail["analysis"]>;
}) {
  return (
    <div className="space-y-1">
      <Section title="AI Analysis">
        {analysis.generated_at && (
          <span className="text-2xs text-muted-foreground">
            Generated <DateTime value={analysis.generated_at} />
          </span>
        )}
        {analysis.insights && analysis.insights.length > 0 && (
          <ul className="mt-2 space-y-1">
            {analysis.insights.map((insight, i) => (
              <li
                key={i}
                className="text-xs text-muted-foreground flex gap-1.5"
              >
                <span className="shrink-0">•</span>
                <span className="break-words">{insight}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {analysis.summary &&
        (analysis.summary.summary ||
          analysis.summary.resume_fit ||
          analysis.summary.note) && (
          <Section title="Summary">
            {analysis.summary.summary && (
              <p className="text-xs text-foreground whitespace-pre-wrap mb-2">
                {analysis.summary.summary}
              </p>
            )}
            {analysis.summary.resume_fit && (
              <p className="text-xs text-muted-foreground whitespace-pre-wrap mb-2">
                <span className="font-medium text-foreground">
                  Resume fit:{" "}
                </span>
                {analysis.summary.resume_fit}
              </p>
            )}
            {analysis.summary.note && (
              <p className="text-xs text-muted-foreground whitespace-pre-wrap">
                {analysis.summary.note}
              </p>
            )}
          </Section>
        )}
    </div>
  );
}

function PublishedBySection({
  recruiters,
}: {
  recruiters: NonNullable<JobDetail["related_companies"]>;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex items-center gap-1.5 w-full">
          {open ? (
            <CaretDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          ) : (
            <CaretRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          )}
          <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wide shrink-0">
            Published by
          </span>
          {!open && (
            <span className="text-2xs text-foreground truncate min-w-0">
              {recruiters.map((c) => c.name || "Recruiting company").join(", ")}
            </span>
          )}
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2">
          <ul className="space-y-1.5">
            {recruiters.map((c) => (
              <li
                key={c.company_id}
                className="flex items-center justify-between gap-3"
              >
                <a
                  href={`/companies?company=${c.company_id}`}
                  className="text-xs text-primary hover:underline break-words"
                >
                  {c.name || "Recruiting company"}
                </a>
                {c.company_type && (
                  <Badge>{c.company_type.replace(/_/g, " ")}</Badge>
                )}
              </li>
            ))}
          </ul>
          {recruiters.some((c) => c.reason) && (
            <ul className="mt-2 space-y-1">
              {recruiters
                .filter((c) => c.reason)
                .map((c) => (
                  <li
                    key={c.company_id}
                    className="text-2xs text-muted-foreground flex gap-1.5"
                  >
                    <span className="shrink-0">•</span>
                    <span className="break-words">{c.reason}</span>
                  </li>
                ))}
            </ul>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

function ProcessingSection({
  exec,
}: {
  exec: JobDetail["latest_processing_execution"];
}) {
  const [open, setOpen] = useState(false);
  const steps = exec?.workflow?.steps ?? [];

  return (
    <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex items-center gap-1.5 w-full">
          {open ? (
            <CaretDown className="w-3.5 h-3.5 text-muted-foreground" />
          ) : (
            <CaretRight className="w-3.5 h-3.5 text-muted-foreground" />
          )}
          <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wide">
            Processing
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2">
          <DetailRow label="Execution" value={exec?.execution_id} />
          <DetailRow label="Status" value={exec?.status} />
          <DetailRow label="Current Step" value={exec?.current_step} />
          {exec?.error && (
            <p className="text-2xs text-red-500 pt-1 animate-in fade-in-0 duration-300">
              {exec.error.message}
            </p>
          )}
          {steps.length > 0 && (
            <div className="mt-2">
              {steps.map((step) => (
                <StepItem key={step.id} step={step} depth={0} />
              ))}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

function ProcessingErrorBanner({
  message,
  onRetry,
  onCheckStatus,
}: {
  message: string;
  onRetry?: () => void;
  onCheckStatus: () => void;
}) {
  return (
    <div
      data-testid="processing-error-banner"
      className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 animate-in fade-in-0 duration-300"
    >
      <div className="flex items-start gap-2">
        <XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <p className="text-2xs font-medium text-red-500 uppercase tracking-wide">
            Processing failed
          </p>
          <p className="text-xs text-foreground break-words mt-0.5">{message}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-2">
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs gap-1"
            onClick={onRetry}
          >
            <Repeat className="w-3.5 h-3.5" /> Retry
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs gap-1 text-muted-foreground"
          onClick={onCheckStatus}
          aria-label="Check processing status"
        >
          <ArrowsClockwise className="w-3.5 h-3.5" /> Check status
        </Button>
      </div>
    </div>
  );
}

function DismissToggle({ jobId, jobTitle, dismissed }: { jobId: string; jobTitle: string | null; dismissed?: boolean }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const setDismissed = useMutation({
    mutationFn: ({ dismissed, note }: { dismissed: boolean; note?: string }) =>
      jobApi.setDismissed(jobId, dismissed, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-detail", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs-v2-infinite"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  if (dismissed) {
    return (
      <Button size="sm" variant="outline" onClick={() => setDismissed.mutate({ dismissed: false })} disabled={setDismissed.isPending}>
        {setDismissed.isPending ? 'Restoring…' : 'Undismiss'}
      </Button>
    );
  }
  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        Mark as dismissed
      </Button>
      <DismissDialog
        open={open}
        onOpenChange={setOpen}
        jobTitle={jobTitle ?? undefined}
        onDismiss={(note) => {
          setDismissed.mutate(
            { dismissed: true, note: note || undefined },
            { onSuccess: () => setOpen(false) },
          );
        }}
        isPending={setDismissed.isPending}
      />
    </>
  );
}

function JobDetailContent({
  detail,
  onReprocess,
}: {
  detail: JobDetail;
  onReprocess?: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const handleCheckStatus = () =>
    queryClient.invalidateQueries({ queryKey: ["job-detail", detail.id] });
  const exec = detail.latest_processing_execution;
  const execError =
    exec?.status === "failed" && exec.error?.message ? exec.error.message : null;
  const setCompany = useMutation({
    mutationFn: (companyId: string | null) =>
      jobApi.setCompany(detail.id, companyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-detail", detail.id] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const recruiters = (detail.related_companies ?? []).filter(
    (c) => c.role === "recruiter",
  );

  return (
    <div className="space-y-1 min-w-0">
      {execError && (
        <ProcessingErrorBanner
          message={execError}
          onRetry={onReprocess ? () => onReprocess(detail.id) : undefined}
          onCheckStatus={handleCheckStatus}
        />
      )}
      <div className="flex   justify-between">
        <div className="flex items-center gap-3 mb-1">
          <GradeBadge
            grade={gradeForScore(detail.scores?.overall ?? null)}
            className="w-10 h-8 text-sm"
          />
          {detail.scores?.overall != null && (
            <JobScoreCard label="Overall" value={detail.scores.overall} />
          )}
          {detail.scores?.success != null && (
            <JobScoreCard label="Success" value={detail.scores.success} />
          )}
          {detail.scores?.fit != null && (
            <JobScoreCard label="Fit" value={detail.scores.fit} />
          )}
          <RankBadge rank={detail.rank ?? null} />
          {detail.analysis?.scores_explanation && (
            <ScoresExplanationButton
              explanation={detail.analysis.scores_explanation}
            />
          )}
        </div>
        {detail.url && (
          <a
            href={detail.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline mt-2"
          >
            <LinkSimple className="w-3.5 h-3.5" /> Open job posting
          </a>
        )}
      </div>
      <div>
        <h2 className="text-base font-semibold text-foreground">
          {detail.title || detail.role || "Untitled"}
        </h2>
        <div className="grid grid-cols-2 gap-12 ">
          <div className="min-w-0 ">
            <DetailRow
              label="Company"
              value={
                <CompanyPicker
                  companyId={detail.company_id ?? null}
                  companyName={detail.company_name ?? null}
                  onSelect={(id) => setCompany.mutate(id)}
                  pending={setCompany.isPending}
                />
              }
            />
            {detail.company_type && (
              <DetailRow label="Type" value={formatCompanyType(detail.company_type)} />
            )}
            <DetailRow
              label="Location"
              value={<TruncatedValue value={detail.location} />}
            />
            <DetailRow
              label="Visa"
              value={<TruncatedValue value={detail.visa} />}
            />
            {detail.easy_apply && (
              <div className="flex items-center justify-between gap-4 py-1.5">
                <span className="text-2xs text-muted-foreground uppercase tracking-wide shrink-0">
                  Apply
                </span>
                <span className="inline-flex items-center gap-1 text-2xs px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-500 border border-sky-500/20 whitespace-nowrap font-medium">
                  Easy Apply
                </span>
              </div>
            )}
            <DetailRow
              label="Tracking"
              value={
                <div className="flex flex-col gap-1.5">
                  <TrackingStatusSelect jobId={detail.id} />
                  <DismissToggle jobId={detail.id} jobTitle={detail.title} dismissed={detail.dismissed} />
                </div>
              }
            />
          </div>
          <div className="min-w-0">
            <DetailRow
              label="Employment"
              value={detail.employment_types?.join(", ")}
            />
            <DetailRow label="Salary" value={detail.salary} />

            <DetailRow
              label="Work Types"
              value={detail.work_types?.join(", ")}
            />
          </div>
        </div>
      </div>

      {detail.analysis?.recommendation && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
          <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
            Recommendation
          </p>
          <div className="flex items-center gap-2 mb-2">
            <RecommendationBadge
              recommendation={detail.analysis.recommendation}
            />
            {detail.analysis.generated_at && (
              <span className="text-2xs text-muted-foreground">
                <DateTime value={detail.analysis.generated_at} />
              </span>
            )}
          </div>
          {detail.analysis.apply_reason && (
            <p className="text-xs text-foreground whitespace-pre-wrap">
              {detail.analysis.apply_reason}
            </p>
          )}
        </div>
      )}

      {detail.analysis?.skills && detail.analysis.skills.length > 0 && (
        <Section title="Tagged Skills">
          <div className="flex flex-wrap gap-1.5">
            {detail.analysis.skills.map((skill, i) => (
              <Badge key={i}>
                {skill.name}
                {skill.level != null && (
                  <span className="text-muted-foreground">
                    {" "}
                    · L{skill.level}
                  </span>
                )}
                {skill.category && (
                  <span className="text-muted-foreground">
                    {" "}
                    · {skill.category}
                  </span>
                )}
              </Badge>
            ))}
          </div>
        </Section>
      )}

      {detail.analysis && <AnalysisSection analysis={detail.analysis} />}

      {detail.description && (
        <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
          <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
            Description
          </p>
          <p className="text-xs text-foreground whitespace-pre-wrap">
            {detail.description}
          </p>
        </div>
      )}
      {detail.notes && detail.notes.length > 0 && (
        <NotesLinksReadOnly notes={detail.notes} links={[]} heading="Notes" />
      )}
      {detail.links && detail.links.length > 0 && (
        <NotesLinksReadOnly notes={[]} links={detail.links} heading="Links" />
      )}

      {recruiters.length > 0 && <PublishedBySection recruiters={recruiters} />}

      <ProcessingSection exec={detail.latest_processing_execution} />
    </div>
  );
}

export function JobDetailDrawer({
  jobId,
  onOpenChange,
  onEdit,
  onReprocess,
}: JobDetailDrawerProps) {
  const router = useRouter();
  const {
    data: detail,
    isLoading,
    isError,
  } = useQuery<JobDetail>({
    queryKey: ["job-detail", jobId],
    queryFn: () => jobApi.getDetail(jobId!),
    enabled: !!jobId,
  });

  return (
    <Drawer
      open={!!jobId}
      onOpenChange={(open) => {
        if (!open) onOpenChange(null);
      }}
    >
      <DrawerHeader
        title="Job Details"
        onClose={() => onOpenChange(null)}
        actions={
          <div className="flex items-center gap-1">
            {onReprocess && jobId ? (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs text-muted-foreground"
                onClick={() => onReprocess(jobId)}
                aria-label="Reprocess job"
              >
                <Repeat className="w-3.5 h-3.5" /> Reprocess
              </Button>
            ) : undefined}
            {jobId && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 gap-1 text-xs text-blue-600"
                onClick={() => router.push(`/jobs/${jobId}/application`)}
                aria-label="Open application workspace"
              >
                <PaperPlaneTilt className="w-3.5 h-3.5" /> Application
              </Button>
            )}
            {onEdit && jobId ? (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs text-muted-foreground"
                onClick={() => onEdit(jobId)}
                aria-label="Edit job"
              >
                <PencilSimple className="w-3.5 h-3.5" /> Edit
              </Button>
            ) : undefined}
          </div>
        }
      />
      <DrawerContent>
        {isLoading && (
          <div className="flex items-center justify-center h-40">
            <CircleNotch className="w-6 h-6 text-muted-foreground animate-spin" />
          </div>
        )}
        {isError && (
          <div className="flex items-center justify-center h-40">
            <p className="text-sm text-red-500">Unable to load job details.</p>
          </div>
        )}
        {detail && !isLoading && (
          <JobDetailContent detail={detail} onReprocess={onReprocess} />
        )}
      </DrawerContent>
    </Drawer>
  );
}
