"use client";

import { useState } from "react";
import {
  Drawer,
  DrawerHeader,
  DrawerContent,
  DrawerFooter,
} from "@/shared/components/Drawer";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import { Button } from "@/shared/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/shared/ui/select";
import { Plus, Warning, CircleNotch, TagSimple } from "@phosphor-icons/react";
import { useSkillCategories } from "@/entities/skill/hooks";
import { CategoryMultiSelect } from "./CategoryMultiSelect";

interface AddSkillDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: {
    name: string;
    level: number;
    roles: string;
    path: string;
    category: string;
    categories: string[];
  }) => void;
  submitting?: boolean;
  error?: string | null;
}

function Field({
  label,
  required = false,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
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
    </div>
  );
}

export default function AddSkillDrawer({
  open,
  onOpenChange,
  onSubmit,
  submitting = false,
  error = null,
}: AddSkillDrawerProps) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState(1);
  const [categories, setCategories] = useState<string[]>([]);
  const [roles, setRoles] = useState("");
  const [path, setPath] = useState("");
  const { categories: categoryOptions, createMutation } = useSkillCategories();

  const canSubmit = name.trim().length > 0;

  const handleOpenChange = (next: boolean) => {
    onOpenChange(next);
    if (!next) {
      setName("");
      setLevel(1);
      setCategories([]);
      setRoles("");
      setPath("");
    }
  };

  const handleSubmit = () => {
    if (!canSubmit || submitting) return;
    onSubmit({
      name: name.trim(),
      level,
      roles: roles.trim(),
      path: path.trim(),
      category: categories[0] ?? "",
      categories,
    });
  };

  const handleAddCategory = async (name: string) => {
    await createMutation.mutateAsync(name);
    return { name };
  };

  return (
    <Drawer open={open} onOpenChange={handleOpenChange}>
      <DrawerHeader
        title={
          <span className="flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" /> Add Skill
          </span>
        }
        onClose={() => handleOpenChange(false)}
      />
      <DrawerContent>
        <div className="space-y-3">
          <Field label="Name" required>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Kubernetes"
              autoFocus
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Level">
              <Select
                value={String(level)}
                onValueChange={(v) => setLevel(Number(v))}
              >
                <SelectTrigger className="h-8 text-xs">{level}</SelectTrigger>
                <SelectContent position="popper">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Categories">
              <CategoryMultiSelect
                value={categories}
                onChange={setCategories}
                options={categoryOptions.map((c) => c.category)}
                onCreate={handleAddCategory}
                size="md"
              />
            </Field>
          </div>
          <Field label="Relevant Roles">
            <Input
              value={roles}
              onChange={(e) => setRoles(e.target.value)}
              placeholder="e.g. project manager, program manager"
            />
          </Field>
          <Field label="Path">
            <Textarea
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="Where this skill fits your career path..."
              className="min-h-[70px] text-xs resize-none"
            />
          </Field>

          {error && (
            <div className="flex items-start gap-1 text-xs text-destructive bg-destructive/10 rounded p-2">
              <Warning className="w-3.5 h-3.5 shrink-0" />
              {error}
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
        <Button
          variant="default"
          size="sm"
          disabled={!canSubmit || submitting}
          onClick={handleSubmit}
        >
          {submitting ? (
            <CircleNotch className="w-3 h-3 animate-spin" />
          ) : (
            <TagSimple className="w-3 h-3" />
          )}
          {submitting ? "Adding..." : "Add Skill"}
        </Button>
      </DrawerFooter>
    </Drawer>
  );
}
