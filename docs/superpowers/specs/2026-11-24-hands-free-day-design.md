# Hands-free competition day: design

**Date:** 2026-11-24 · **Status:** approved in chat (approach A)

## Goal
Run the whole competition day (2026-11-28 09:00–24:00) with no user interaction after launch, including session and context management.

## Approach
A PowerShell supervisor starts a fresh headless Claude Code run (`claude -p`) every cycle. Each run follows the `/compete` skill in headless mode: it reads the state files, does steps until something must wait, and exits with `WAIT <s>`, `BLOCKED <reason>` or `DONE`. Fresh context every cycle replaces manual session handoffs. All state stays in files, as before.

## Components
- `.claude/skills/compete/run_day.ps1`: the supervisor.
  - Waits for `start`; loops until `end`, `DONE` or a `STOP` file.
  - One run per cycle, from the repo root, with the prompt passed on stdin.
  - Logs per cycle, plus `supervisor.log`.
  - 45-minute hang kill (process tree), single-instance lock, Windows keep-awake.
  - Backs off to 10 min after 3 failed cycles or a `BLOCKED`.
- `launch.md` (repo root): a template the user fills once.
  - Fields: competition, rules, competition folder, start, end, budget, max parallel jobs, `auto_submit`, HF checkpoint repo, notes.
  - The script refuses to start while any field is `TODO`.
- `SKILL.md`: a "Headless mode" section.
  - Never ask; answers come from `launch.md` (the user's own written answer, so it counts for `auto_submit`).
  - Last-line protocol (`WAIT`, `BLOCKED`, `DONE`).
  - Training launched detached (HF Jobs `--detach`, SSH `nohup`); never `run_in_background` or Monitor.
  - Desktop-only steps skipped.
  - Notes go to `logs/notes.md` instead of phone notifications.
- `SATURDAY.md`: the hands-free route first; the desktop `/loop /compete` route as the fallback.

## User-only steps (never done by Claude)
- Install the Claude Code CLI and log in.
- `hf auth login`, plus `kaggle.json` if needed.
- Set `$PermissionArgs` in `run_day.ps1`. It is a safety setting, so the user chooses it.

## Known limits
- Web-upload competitions cannot be submitted unattended; the files are prepared and listed in `logs/notes.md`.
- A training process started locally on this PC (not on HF Jobs or SSH) may be killed by the 45-minute hang kill. There is no local GPU, so this is not expected.
- Untested until a supervisor cycle runs; the user deferred tests.
