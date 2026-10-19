# Prompt 231 - Fix `docker-test.sh all` false-negative exit status

## Objective

`./scripts/docker-test.sh all` (and therefore `uv run apps/start.py terraform test all`,
the rule-18 gate before `start terraform up`) exits **1 even when both suites pass**,
blocking every deploy. Fix the exit-status logic so `all` fails only when a suite fails.

## Current state

- `scripts/docker-test.sh` line 70 (`all` branch):

  ```bash
  [ "$RB" -ne 0 ] || [ "$RF" -ne 0 ] && exit 1
  ```

  With `RB=0 RF=0` both tests are false, `exit 1` is skipped, and the `||`/`&&`
  list evaluates to status **1**, which becomes the script's exit code under
  `set -euo pipefail`. Verified on this host (bash 5.3.9):

  ```
  both-zero    → exit 1   # bug: both suites passed
  backend-fail → exit 1   # correct
  ```

- Evidence this is the sole cause of the latest gate failure
  (`uv run apps/start.py terraform test all`, 2026-10-18):
  - frontend half: vitest reported `94 files / 822 passed`;
  - backend half: pytest ran to completion (warnings summary printed, no
    `F`/`E` markers), and a standalone `./scripts/docker-test.sh backend`
    re-run passed (exit 0);
  - `apps/start.py:1127` just relays the script's exit code as
    `'all' tests FAILED. Fix failures before deploying.`

## Implementation steps

1. Replace line 70 in `scripts/docker-test.sh` with an explicit conditional whose
   status is 0 when both suites pass:

   ```bash
   if [ "$RB" -ne 0 ] || [ "$RF" -ne 0 ]; then exit 1; fi
   ```

   Keep `set -euo pipefail` and the parallel `run_backend &` / `run_frontend &`
   structure untouched — only the final gate changes.

2. Sanity-check the logic with the same one-liners used above:
   `RB=0 RF=0` → exit 0; any non-zero RB/RF → exit 1.

3. Run the full gate end-to-end: `./scripts/docker-test.sh all` must exit 0
   (this doubles as the rule-18 gate for `start terraform up`).

## Testing requirements

- `bash -c 'set -euo pipefail; RB=0; RF=0; <new line>'` exits 0.
- `bash -c 'set -euo pipefail; RB=1; RF=0; <new line>'` exits 1 (and RF=1 case).
- `./scripts/docker-test.sh all` exits 0 with both suites green (backend pytest
  + frontend vitest in capped containers).

## Constraints

- Test-infrastructure-only change: no product code, no UI, no docs/UX wireframes
  required; AGENTS.md's `./scripts/docker-test.sh` usage docs stay accurate.
- Do not relax the rule-18 gate semantics: `all` must still exit non-zero if
  **either** suite fails.
- Commit as a focused `fix(tests)` commit.
