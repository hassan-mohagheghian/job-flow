"use client";

import { useEffect, useState, useCallback, useRef } from "react";
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
  CaretRight,
  CaretDown,
  Play,
  X,
  Repeat,
  Trash,
} from "@phosphor-icons/react";
import LinkDisplay from "@/shared/components/LinkDisplay";
import { Button } from "@/shared/ui/button";
import { toast } from "sonner";
import { processingApi } from "@/entities/processing/api";
import { mergeWorkflowStep } from "@/entities/processing/workflowMerge";
import { subscribeProcessingEvents } from "@/shared/api/processingEvents";
import type {
  QueueEntry,
  QueueSnapshot,
  SSEEventEnvelope,
  WorkflowStep,
  WorkflowProgress,
} from "@/entities/processing/types";

export type ProcessingTargetType = "job" | "company" | "candidate";

interface ProcessingDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reloadKey?: number;
  targetType?: ProcessingTargetType;
}

function stepStatusIcon(status: WorkflowStep["status"]) {
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

function WorkflowStepItem({
  step,
  depth,
}: {
  step: WorkflowStep;
  depth: number;
}) {
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = step.children.length > 0;

  return (
    <div className="min-w-0">
      <button
        type="button"
        className="w-full min-w-0 flex items-start gap-2 text-left p-1.5 rounded hover:bg-muted/40"
        style={{ paddingLeft: `${depth * 16 + 6}px` }}
        onClick={() => hasChildren && setExpanded((e) => !e)}
      >
        {hasChildren ? (
          expanded ? (
            <CaretDown className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
          ) : (
            <CaretRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
          )
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        {stepStatusIcon(step.status)}
        <div className="flex-1 min-w-0 overflow-hidden">
          <div className="flex items-center justify-between gap-2 min-w-0">
            <p className="text-xs font-medium text-foreground min-w-0 break-words">
              {step.title}
            </p>
            {step.progress !== null && step.progress !== undefined && (
              <span className="text-2xs text-muted-foreground shrink-0">
                {Math.round(step.progress)}%
              </span>
            )}
          </div>
          {step.progress !== null && step.progress !== undefined && (
            <div className="w-full h-1 bg-muted rounded-full mt-1 overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, Math.max(0, step.progress))}%`,
                }}
              />
            </div>
          )}
          {step.error && (
            <p className="text-2xs text-red-500 mt-1 break-words">
              {step.error.message}
            </p>
          )}
        </div>
      </button>
      {expanded && hasChildren && (
        <div>
          {step.children.map((child) => (
            <WorkflowStepItem key={child.id} step={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function WorkflowPanel({
  workflow,
  entry,
}: {
  workflow: WorkflowProgress | null;
  entry: QueueEntry;
}) {
  const steps = workflow?.steps ?? [];

  return (
    <div className="rounded-lg border border-border/40 bg-muted/10 p-3 space-y-1 min-w-0">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold text-foreground min-w-0 truncate">
          {workflow?.name ?? "Workflow"}
        </p>
        {workflow?.progress !== null && workflow?.progress !== undefined && (
          <span className="text-2xs text-muted-foreground shrink-0">
            {Math.round(workflow.progress)}%
          </span>
        )}
      </div>
      {workflow?.progress !== null && workflow?.progress !== undefined && (
        <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(100, Math.max(0, workflow.progress))}%`,
            }}
          />
        </div>
      )}
      <div className="pt-1 min-w-0">
        {steps.length === 0 ? (
          <p className="text-2xs text-muted-foreground">
            No steps recorded yet.
          </p>
        ) : (
          steps.map((step) => (
            <WorkflowStepItem key={step.id} step={step} depth={0} />
          ))
        )}
      </div>
      {entry.error && (
        <p className="text-2xs text-red-500 pt-1 break-words">{entry.error}</p>
      )}
    </div>
  );
}

function EntryLinks({ entry }: { entry: QueueEntry }) {
  const links = [
    ...(entry.url ? [{ url: entry.url }] : []),
    ...(entry.links ?? []),
  ];
  if (links.length === 0) return null;
  return (
    <div className="space-y-0.5 mt-1.5 px-1">
      {links.map((link, i) => (
        <LinkDisplay
          key={`${link.url}-${i}`}
          url={link.url}
          title={link.title}
          maxLength={48}
        />
      ))}
    </div>
  );
}

function QueueSection({
  title,
  items,
  color,
  emptyText,
  renderDetail,
  renderActions,
}: {
  title: string;
  items: QueueEntry[];
  color: string;
  emptyText: string;
  renderDetail: (entry: QueueEntry) => React.ReactNode;
  renderActions?: (entry: QueueEntry) => React.ReactNode;
}) {
  return (
    <div>
      <h3
        className={`text-xs font-semibold uppercase tracking-wide ${color} py-2`}
      >
        {title} ({items.length})
      </h3>
      {items.length === 0 ? (
        <p className="text-2xs text-muted-foreground pb-2">{emptyText}</p>
      ) : (
        <div className="space-y-2">
          {items.map((entry) => (
            <div key={entry.execution_id} className="min-w-0">
              <div className="flex items-start gap-3 p-2 rounded-lg border border-border/40 bg-muted/20 min-w-0 overflow-hidden">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground truncate">
                    {entry.title}
                  </p>
                  <p className="text-2xs text-muted-foreground truncate">
                    {entry.current_step
                      ? `Step: ${entry.current_step}`
                      : entry.status}
                  </p>
                  <EntryLinks entry={entry} />
                </div>
                {renderActions && (
                  <div className="shrink-0 flex items-center gap-1 pt-0.5">
                    {renderActions(entry)}
                  </div>
                )}
              </div>
              {renderDetail(entry)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ProcessingDrawer({
  open,
  onOpenChange,
  reloadKey,
  targetType = "job",
}: ProcessingDrawerProps) {
  const [snapshot, setSnapshot] = useState<QueueSnapshot>({
    processing: [],
    queued: [],
    failed: [],
  });
  const [workflows, setWorkflows] = useState<
    Record<string, WorkflowProgress | null>
  >({});
  const workflowsRef = useRef<Record<string, WorkflowProgress | null>>({});
  const loadedRef = useRef<Set<string>>(new Set());
  const inFlightRef = useRef<Set<string>>(new Set());
  const pendingEventsRef = useRef<Map<string, SSEEventEnvelope[]>>(new Map());

  const matchesTarget = useCallback(
    (entry: QueueEntry) => {
      const entryTarget = entry.target_type ?? "job";
      return entryTarget === targetType;
    },
    [targetType],
  );

  const loadSnapshot = useCallback(async () => {
    try {
      const data = await processingApi.queue();
      setSnapshot(data);
    } catch {
      // best effort
    }
  }, []);

  const setWorkflow = useCallback(
    (executionId: string, workflow: WorkflowProgress) => {
      workflowsRef.current[executionId] = workflow;
      setWorkflows({ ...workflowsRef.current });
    },
    [],
  );

  const clearWorkflow = useCallback((executionId: string) => {
    delete workflowsRef.current[executionId];
    setWorkflows({ ...workflowsRef.current });
  }, []);

  const applyPendingEvents = useCallback(
    (executionId: string) => {
      const pending = pendingEventsRef.current.get(executionId);
      if (!pending || pending.length === 0) return;
      const existing = workflowsRef.current[executionId];
      if (!existing) return;
      let workflow = existing;
      for (const evt of pending) {
        const step = evt.payload?.step;
        if (step) {
          workflow = mergeWorkflowStep(workflow, step);
        }
      }
      pendingEventsRef.current.delete(executionId);
      setWorkflow(executionId, workflow);
    },
    [setWorkflow],
  );

  const loadWorkflow = useCallback(
    async (executionId: string) => {
      if (workflowsRef.current[executionId]) return;
      if (
        loadedRef.current.has(executionId) ||
        inFlightRef.current.has(executionId)
      )
        return;
      inFlightRef.current.add(executionId);
      try {
        const detail = await processingApi.get(executionId);
        loadedRef.current.add(executionId);
        if (detail.workflow) {
          setWorkflow(executionId, detail.workflow);
          applyPendingEvents(executionId);
        }
      } catch {
        loadedRef.current.add(executionId);
      } finally {
        inFlightRef.current.delete(executionId);
      }
    },
    [setWorkflow, applyPendingEvents],
  );

  const ensureWorkflow = useCallback(
    (executionId: string) => {
      if (workflowsRef.current[executionId]) return;
      loadedRef.current.delete(executionId);
      loadWorkflow(executionId);
    },
    [loadWorkflow],
  );

  useEffect(() => {
    if (!open) return;
    loadSnapshot();
  }, [open, reloadKey, loadSnapshot]);

  useEffect(() => {
    if (!open) return;
    const allEntries = [
      ...snapshot.processing,
      ...snapshot.queued,
      ...snapshot.failed,
    ];
    for (const entry of allEntries) {
      if (matchesTarget(entry)) {
        loadWorkflow(entry.execution_id);
      }
    }
  }, [open, snapshot, loadWorkflow, matchesTarget]);

  useEffect(() => {
    if (!open) return;

    return subscribeProcessingEvents((type, data) => {
      const eventTarget = data.target_type ?? "job";
      if (eventTarget !== targetType) return;

      if (
        type === "workflow.step.started" ||
        type === "workflow.step.progress" ||
        type === "workflow.step.completed" ||
        type === "workflow.step.failed"
      ) {
        const incoming = data.payload.step;
        if (!incoming) return;
        const existing = workflowsRef.current[data.execution_id];
        if (!existing) {
          // Buffer the event until the workflow is loaded from the server.
          if (!pendingEventsRef.current.has(data.execution_id)) {
            pendingEventsRef.current.set(data.execution_id, []);
          }
          pendingEventsRef.current.get(data.execution_id)!.push(data);
          ensureWorkflow(data.execution_id);
          return;
        }
        setWorkflow(data.execution_id, mergeWorkflowStep(existing, incoming));
        // Update entry card's current_step from the incoming step.
        if (type === "workflow.step.started" && incoming.title) {
          setSnapshot((prev) => ({
            ...prev,
            processing: prev.processing.map((e) =>
              e.execution_id === data.execution_id
                ? { ...e, current_step: incoming.title }
                : e,
            ),
            queued: prev.queued.map((e) =>
              e.execution_id === data.execution_id
                ? { ...e, current_step: incoming.title }
                : e,
            ),
          }));
        }
        return;
      }

      if (type === "queue.entry.removed") {
        loadedRef.current.delete(data.execution_id);
        pendingEventsRef.current.delete(data.execution_id);
        clearWorkflow(data.execution_id);
        loadSnapshot();
        return;
      }

      if (
        type === "execution.started" ||
        type === "execution.completed" ||
        type === "execution.failed" ||
        type === "execution.cancelled"
      ) {
        if (!workflowsRef.current[data.execution_id]) {
          ensureWorkflow(data.execution_id);
        } else {
          applyPendingEvents(data.execution_id);
        }
        // Clear current_step on terminal events (snapshot refresh will handle it).
        if (type !== "execution.started") {
          setSnapshot((prev) => ({
            ...prev,
            processing: prev.processing.map((e) =>
              e.execution_id === data.execution_id
                ? { ...e, current_step: null }
                : e,
            ),
            queued: prev.queued.map((e) =>
              e.execution_id === data.execution_id
                ? { ...e, current_step: null }
                : e,
            ),
          }));
        }
      }
      loadSnapshot();
    });
  }, [
    open,
    targetType,
    loadSnapshot,
    loadWorkflow,
    ensureWorkflow,
    applyPendingEvents,
    setWorkflow,
    clearWorkflow,
  ]);

  const runAction = useCallback(
    async (label: string, action: () => Promise<unknown>) => {
      try {
        await action();
        toast.success(label);
        loadSnapshot();
      } catch {
        toast.error(label);
      }
    },
    [loadSnapshot],
  );

  const handleRetry = useCallback(
    (entry: QueueEntry) => {
      return runAction("Retrying execution", () =>
        processingApi.retry(entry.execution_id),
      );
    },
    [runAction],
  );

  const renderDetail = useCallback(
    (entry: QueueEntry) => {
      return (
        <WorkflowPanel
          workflow={workflows[entry.execution_id] ?? null}
          entry={entry}
        />
      );
    },
    [workflows],
  );

  const handleStart = useCallback(
    (entry: QueueEntry) => {
      return runAction("Started execution", () =>
        processingApi.start(entry.execution_id),
      );
    },
    [runAction],
  );

  const handleCancel = useCallback(
    (entry: QueueEntry) => {
      return runAction("Cancelled execution", () =>
        processingApi.cancel(entry.execution_id),
      );
    },
    [runAction],
  );

  const handleRemove = useCallback(
    (entry: QueueEntry) => {
      return runAction("Removed queue entry", () =>
        processingApi.removeQueueEntry(entry.execution_id),
      );
    },
    [runAction],
  );

  const processingActions = useCallback(
    (entry: QueueEntry) => (
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 shrink-0 text-yellow-500 hover:bg-yellow-500/10"
        onClick={() => handleCancel(entry)}
        title="Cancel"
      >
        <X className="w-3 h-3" />
      </Button>
    ),
    [handleCancel],
  );

  const queuedActions = useCallback(
    (entry: QueueEntry) => (
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0 text-emerald-500 hover:bg-emerald-500/10"
          onClick={() => handleStart(entry)}
          title="Start"
        >
          <Play className="w-3 h-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0 text-destructive hover:bg-destructive/10"
          onClick={() => handleRemove(entry)}
          title="Remove"
        >
          <Trash className="w-3 h-3" />
        </Button>
      </div>
    ),
    [handleStart, handleRemove],
  );

  const failedActions = useCallback(
    (entry: QueueEntry) => (
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0 text-blue-500 hover:bg-blue-500/10"
          onClick={() => handleRetry(entry)}
          title="Retry"
        >
          <Repeat className="w-3 h-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0 text-destructive hover:bg-destructive/10"
          onClick={() => handleRemove(entry)}
          title="Remove"
        >
          <Trash className="w-3 h-3" />
        </Button>
      </div>
    ),
    [handleRetry, handleRemove],
  );

  const filtered = {
    processing: snapshot.processing.filter(matchesTarget),
    queued: snapshot.queued.filter(matchesTarget),
    failed: snapshot.failed.filter(matchesTarget),
  };

  const emptyText =
    targetType === "company"
      ? "No companies in this state."
      : targetType === "candidate"
        ? "No candidate analysis in this state."
        : "No jobs in this state.";

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerHeader
        title="Processing Queue"
        onClose={() => onOpenChange(false)}
      />
      <DrawerContent>
        <div className="space-y-4 min-w-0">
          <QueueSection
            title="Running"
            items={filtered.processing}
            color="text-emerald-500"
            emptyText={emptyText}
            renderDetail={renderDetail}
            renderActions={processingActions}
          />
          <QueueSection
            title="Waiting"
            items={filtered.queued}
            color="text-blue-500"
            emptyText={emptyText}
            renderDetail={renderDetail}
            renderActions={queuedActions}
          />
          <QueueSection
            title="Failed"
            items={filtered.failed}
            color="text-red-500"
            emptyText={emptyText}
            renderDetail={renderDetail}
            renderActions={failedActions}
          />
        </div>
      </DrawerContent>
    </Drawer>
  );
}
