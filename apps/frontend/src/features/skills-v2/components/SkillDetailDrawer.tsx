"use client";

import {
  Drawer,
  DrawerHeader,
  DrawerContent,
  DrawerFooter,
} from "@/shared/components/Drawer";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import {
  Star,
  PencilSimple,
  Trash,
  Code,
  Scissors,
  MapPin,
} from "@phosphor-icons/react";
import { cn } from "@/shared/lib/utils";
import type { SkillListItem } from "@/entities/skill/types";
import { CategoryBadges, OriginBadge } from "./SkillRow";
import { useSkillReferencedJobs } from "@/entities/skill/hooks";
import { GradeBadge } from "@/shared/components/GradeBadge";
import { PinButton } from "@/shared/components/PinButton";
import { gradeForScore } from "@/shared/lib/grade";
import { SkillResources } from "./SkillResources";

interface SkillDetailDrawerProps {
  skillId: number | null;
  skill: SkillListItem | null;
  onOpenChange: (id: number | null) => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
  onBreakDown: (id: number) => void;
  onOpenJob?: (id: string) => void;
  onTogglePinned?: (id: number, pinned: boolean) => void;
}

function ReferencedJobsList({
  skillId,
  onOpenJob,
}: {
  skillId: number;
  onOpenJob?: (id: string) => void;
}) {
  const { data, isLoading, isError } = useSkillReferencedJobs(skillId);
  const jobs = data?.jobs ?? [];
  const n = jobs.length;

  return (
    <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
      <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
        Referenced Jobs ({n})
      </p>
      {isLoading ? (
        <p className="text-xs text-muted-foreground">Loading jobs…</p>
      ) : isError ? (
        <p className="text-xs text-destructive">Unable to load jobs</p>
      ) : n === 0 ? (
        <p className="text-xs text-muted-foreground">
          No jobs reference this skill yet.
        </p>
      ) : (
        <div className="space-y-1">
          {jobs.map((j) => {
            const overall = j.overall_score;
            const validOverall =
              overall != null && !Number.isNaN(overall) ? overall : null;
            return (
              <div
                key={j.id}
                className="flex items-center gap-1 p-2 rounded border border-border/50 hover:bg-muted/50 transition group cursor-pointer"
                onClick={() => onOpenJob?.(j.id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold truncate flex-1">
                      {j.title || "Untitled Job"}
                    </span>
                    {validOverall != null && (
                      <GradeBadge
                        grade={gradeForScore(validOverall)}
                        className="shrink-0"
                      />
                    )}
                  </div>
                  {j.location && (
                    <div className="text-2xs text-muted-foreground mt-0.5">
                      <MapPin className="w-2 h-2 inline mr-0.5" />
                      {j.location}
                    </div>
                  )}
                  {(j.fit_score != null || j.success_score != null) && (
                    <div className="flex items-center gap-2 mt-0.5">
                      {j.fit_score != null && (
                        <Badge variant="secondary" className="text-2xs">
                          Fit {j.fit_score}
                        </Badge>
                      )}
                      {j.success_score != null && (
                        <Badge variant="secondary" className="text-2xs">
                          Success {j.success_score}
                        </Badge>
                      )}
                      {overall != null && (
                        <Badge variant="secondary" className="text-2xs">
                          Overall {overall}
                        </Badge>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function SkillDetailDrawer({
  skillId,
  skill,
  onOpenChange,
  onEdit,
  onDelete,
  onBreakDown,
  onOpenJob,
  onTogglePinned,
}: SkillDetailDrawerProps) {
  const open = !!skill && !!skillId;

  if (!skill) return null;

  const confidence =
    skill.confidence != null ? Math.round(skill.confidence * 100) : null;
  const demand =
    skill.market_relevance != null
      ? Math.round(skill.market_relevance * 100)
      : null;

  return (
    <Drawer
      open={open}
      onOpenChange={(o) => {
        if (!o) onOpenChange(null);
      }}
    >
      <DrawerHeader
        title={
          <span className="flex items-center gap-1.5 min-w-0">
            <Code className="w-3.5 h-3.5 text-primary shrink-0" />
            <span className="truncate">{skill.name}</span>
            <OriginBadge sourceType={skill.source_type} />
          </span>
        }
        onClose={() => onOpenChange(null)}
        actions={
          <>
            {onTogglePinned ? (
              <PinButton
                pinned={skill.pinned ?? false}
                onToggle={() => onTogglePinned(skill.id, !(skill.pinned ?? false))}
                entityLabel="skill"
                className="h-7 w-7"
              />
            ) : undefined}
            {onEdit && skillId != null ? (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs text-muted-foreground"
                onClick={() => onEdit(skillId as number)}
                aria-label="Edit skill"
              >
                <PencilSimple className="w-3.5 h-3.5" /> Edit
              </Button>
            ) : undefined}
          </>
        }
      />
      <DrawerContent>
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            {skill.level > 0 && (
              <div className="flex items-center gap-1">
                <Star className="w-3 h-3 text-yellow-500" />
                <span className="text-xs font-bold">Lv.{skill.level}</span>
              </div>
            )}
            {confidence != null && (
              <div className="flex items-center gap-1">
                <span className="text-xs text-muted-foreground">
                  Confidence:
                </span>
                <span
                  className={cn(
                    "text-xs font-bold",
                    confidence >= 80
                      ? "text-green-500"
                      : confidence >= 50
                        ? "text-yellow-500"
                        : "text-orange-500",
                  )}
                >
                  {confidence}%
                </span>
              </div>
            )}
            {demand != null && (
              <div className="flex items-center gap-1">
                <span className="text-xs text-muted-foreground">Market:</span>
                <span
                  className={cn(
                    "text-xs font-bold",
                    demand >= 80
                      ? "text-green-500"
                      : demand >= 50
                        ? "text-yellow-500"
                        : "text-orange-500",
                  )}
                >
                  {demand}%
                </span>
              </div>
            )}
          </div>

          {(skill.categories?.length > 0 || skill.category) && (
            <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
              <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                Categories
              </p>
              <CategoryBadges
                categories={skill.categories}
                fallback={skill.category}
              />
            </div>
          )}

          {skill.roles && (
            <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
              <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                Relevant Roles
              </p>
              <p className="text-xs text-foreground">{skill.roles}</p>
            </div>
          )}

          {skill.path && (
            <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
              <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                Path
              </p>
              <p className="text-xs text-foreground whitespace-pre-wrap">
                {skill.path}
              </p>
            </div>
          )}

          {skill.tags && skill.tags.length > 0 && (
            <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
              <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                Tags
              </p>
              <div className="flex flex-wrap gap-1">
                {skill.tags.map((t, i) => (
                  <Badge key={i} variant="secondary" className="text-2xs">
                    {t}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {skill.aliases && skill.aliases.length > 0 && (
            <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
              <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                Also Known As
              </p>
              <div className="flex flex-wrap gap-1">
                {skill.aliases.map((a, i) => (
                  <Badge key={i} variant="outline" className="text-2xs">
                    {a}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {skill.evidence && skill.evidence !== "[]" && (
            <div className="rounded-lg border border-border/40 bg-muted/10 p-3">
              <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                Why This Skill Matters
              </p>
              <p className="text-xs text-muted-foreground">{skill.evidence}</p>
            </div>
          )}

          <SkillResources skill={skill} />

          {skillId != null && (
            <ReferencedJobsList skillId={skillId} onOpenJob={onOpenJob} />
          )}
        </div>
      </DrawerContent>
      <DrawerFooter>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1 h-7 text-2xs text-muted-foreground"
          onClick={() => skillId != null && onBreakDown(skillId)}
        >
          <Scissors className="w-3 h-3" /> Break down
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1 h-7 text-2xs text-destructive"
          onClick={() => skillId != null && onDelete(skillId)}
        >
          <Trash className="w-3 h-3" /> Delete
        </Button>
      </DrawerFooter>
    </Drawer>
  );
}
