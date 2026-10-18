# Prompt 226 - Default Terraform AI Provider to `opencode`

## Objective
Make the terraform-deployed stack run with `AI_PROVIDER=opencode` by default instead of `fcc-opencode`, then redeploy with `start terraform up` (tests first, per AGENTS.md rule 18).

## Current State
- `terraform/terraform.tfvars.example:28` → `ai_provider = "fcc-opencode"`.
- `terraform/variables.tf:85` → `default = "fcc-opencode"` (README.md:178 already documents `opencode` as the default).
- `apps/start.py:1042-1050` `_run_terraform_with_vars()` always passes `-var-file terraform.tfvars.example`, so the **var file**, not the variable default, is the value that actually reaches containers — both must change to keep them consistent.
- `terraform/main.tf:154,194,236,277` inject `AI_PROVIDER=${var.ai_provider}` into alembic / backend / background / scheduler containers.
- `apps/backend/ai/infrastructure/providers/__init__.py:54` maps **both** `opencode` and `fcc-opencode` to the same `OpencodeProvider`, so the rename is behavior-preserving on the provider-selection side (no adapter change needed).
- Pre-existing **uncommitted** worktree edits are present and are *kept* (not reverted): the `fcc-opencode` alias in `__init__.py`, the removed duplicate `volumes` block in `terraform/main.tf`, `opencode_bin` gaining a `default` in `variables.tf`, and the `086` doc path tweak. Only the `ai_provider` value(s) are changed here.

## Implementation Steps
1. `terraform/terraform.tfvars.example`: `ai_provider = "fcc-opencode"` → `"opencode"`.
2. `terraform/variables.tf`: variable `ai_provider` default `"fcc-opencode"` → `"opencode"` (description already lists `opencode/fcc-opencode`).
3. Leave `terraform/README.md:178` as-is (already says `opencode`); no other doc claims `fcc-opencode`.
4. Redeploy: `start terraform test all` (rule 18) then `start terraform up`, and verify `AI_PROVIDER=opencode` inside the containers.

## Testing Requirements
- `./scripts/docker-test.sh all` green before any `terraform up` (rule 18).
- Post-deploy smoke check: `docker exec job-search-backend printenv AI_PROVIDER` → `opencode`, and the backend resolves the provider without `Unknown provider` errors.

## Constraints
- AGENTS.md rules 18 (tests in Docker only, terraform test before up), 11 (`structlog`, not `print`) — no backend code changes.
- Scope confirmed with user: **terraform only** — do *not* touch the `mimo` default in `apps/backend/shared/infrastructure/config/app_config.py` or `factory.py`.
- No version bump (no release for a deploy-config tweak); no migration involved.
