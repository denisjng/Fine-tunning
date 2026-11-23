# `/compete` — one-day fine-tuning competition playbook

**Date:** 2026-11-23
**Event:** Saturday 2026-11-28, 09:00–24:00 (15 h, one day, no prep days)
**Status:** design approved section by section; awaiting spec review

## 1. Goal and constraints

Win as high a leaderboard rank as possible in one day, as a beginner, with Claude doing most of the work.

- Task, modality, base model, metric and submission method are unknown until 09:00 on the day. The playbook must cover any modality: LLM text generation, text classification/regression, vision, audio, tabular.
- Compute: organizer-provided GPU if available, otherwise paid cloud (default: Hugging Face Jobs via `hf-cli`; fallback: RunPod or similar). No local GPU assumed.
- The user wants a submission after **every** stage to climb the leaderboard.
- After the first submission, improvement loops run **autonomously**; the user watches and steps in when they want.
- No preparation days. Everything the user does happens on the day; everything built in advance lives in the skill.

## 2. Deliverable

A project skill in this repo:

```
.claude/skills/compete/
  SKILL.md              timeline, hard rules, loop, lever list, skill map, runbook, autonomy guardrails
  check_submission.py   format check against the organizer's sample submission, with self-test
  recipes/
    llm.md              text generation: instruct model + QLoRA (TRL SFT)
    text-classify.md    text classification / regression: encoder model
    vision.md           image classification / detection: pretrained backbone
    audio.md            speech / audio: Whisper-family
    tabular.md          tabular: LightGBM (no fine-tuning needed)
```

One command: `/compete`. Each call reads the clock plus the state files, finds the current block and the first unfinished step, runs it, and prints time left to the next deadline. If behind schedule it says so and applies the block's hard rule. Autonomous mode is `/loop /compete` (the existing Claude Code self-paced loop; nothing new is built for it).

### Recipe cards (one screen each, no pre-written training scripts)

Each card contains:
- Default model family and how to pick the current best model of a given size on the day (quick web search, 15-min cap) plus one named fallback.
- Starting hyperparameters by GPU memory (e.g. 16 GB / 24 GB / 40–80 GB).
- The 3–5 levers specific to the modality (e.g. LoRA rank and target modules, max sequence length, image augmentations, decoding settings).
- Common crashes and their fixes.

Claude writes the actual train/inference scripts on the day from the chosen card, because pre-written scripts would likely not fit the real task.

## 3. Day state (created in the competition working folder)

| File | Content |
|---|---|
| `brief.md` | Task, metric (and direction: higher/lower is better), data description, submission format and method (CLI/API vs web upload), daily submission cap, deadlines, GPU budget cap, max parallel jobs, whether train+val retraining is allowed |
| `experiments.md` | One row per loop: `#`, time, change, hypothesis, val score, LB score, kept/reverted, submission file |
| `submissions/` | Every submitted file, numbered (`001_baseline.csv`, …), never overwritten |
| `mlruns/` | MLflow local tracking of training metrics |

Plain files, so a crashed or new Claude session resumes exactly where the last one stopped.

## 4. Day timeline

| Time | Block | Output | Hard rule |
|---|---|---|---|
| 09:00–09:30 | **Setup & rules:** read rules, metric, submission format, limits; start GPU; set HF token; turn on keep-awake; laptop on power | `brief.md` | No training before the brief exists |
| 09:30–10:30 | **Understand data:** profile it, build a local validation split that mirrors the test set, pick a recipe card | val split + chosen card | The val split is frozen after this block |
| 10:30–12:30 | **Baseline:** card default model, short training, inference to a submission file | **Submission #1 by 12:30** | No submission by 13:00 → smaller model or simpler card |
| 12:30–20:00 | **Autonomous improvement loops** (~6–8 × 45–75 min) | one logged experiment + submission per loop | One change per loop |
| 20:00–22:00 | **Final run:** retrain best config (on train+val if allowed) or average the top 2 if cheap | final predictions + submission | No untested ideas |
| 22:00–23:00 | **Verify & final submit:** format check, sanity check, submit, select final submission(s); ping user to allow override | **Final submission by 23:00** | |
| 23:00–24:00 | **Buffer** | — | Emergency resubmit only |

From the baseline block on, every block ends with a submission. Meals go into training waits (~13:00 and ~18:00).

The guided phase is 09:00 → submission #1: the user runs `/compete` step by step, because only they can read the rules, confirm the submission method and set the budget. From submission #1 the user starts `/loop /compete`.

## 5. The improvement loop

1. **Pick one lever:** the top unused item from the priority list, or what the last error analysis pointed to.
2. **Hypothesis:** one line in `experiments.md`: "change X because Y, expect val ↑".
3. **Smoke test, then train:** run 2 minutes on a tiny sample to catch crashes, then the full run in the background. If the full run will not finish inside the loop's time, cut data, epochs or model size first.
4. **Error analysis while it trains:** look at the current best model's worst validation mistakes to choose the next lever.
5. **Evaluate & log:** val score to MLflow and to `experiments.md`.
6. **Submit and decide:** every loop submits (after `check_submission.py` passes). If val beats the best so far, it becomes the new best and its checkpoint is pushed to a private HF repo; otherwise revert the change and keep the score. If the daily submission cap is lower than the number of stages, skip submitting loops that did not beat the best val.

### Lever priority list (all modalities)

1. Data/format bugs: label mapping, truncation, prompt template, image size.
2. Learning rate and number of epochs.
3. A better or bigger base model, if it fits the GPU and time.
4. Data work: cleaning, augmentation, external data if the rules allow.
5. Modality-specific levers from the recipe card.
6. Inference tricks: test-time augmentation, threshold tuning, decoding settings.
7. Ensemble the top 2–3: only in the 20:00 final block.

### Leaderboard rule

The public leaderboard is often scored on a small slice of the test set. For the final choice prefer the model that is good on **both** local val and public LB over one that only tops the public LB.

### Optional parallel mode

With 2+ GPUs and budget left, run two loops at once, each testing a different single change, via `superpowers:dispatching-parallel-agents`.

## 6. Autonomy guardrails

Set in `brief.md` during the 09:00 block; the loop never crosses them.

- **Budget:** max GPU spend and max parallel jobs. When the budget is reached the loop stops launching and notifies the user.
- **Submission cap:** respect the competition's daily limit (see §5 step 6).
- **Untouchables:** never edit the val split or the test data; never delete experiments, checkpoints or submissions.
- **Clock:** never start a run that cannot finish before the next block's deadline. At 20:00 switch to the final block; at 22:00 to verify & submit.
- **Stuck rule:** 3 loops in a row with no gain → jump to a bigger lever category (e.g. a new base model). The same change crashes twice → revert and skip that lever.
- **Submitting:** if the platform has a CLI or API (Kaggle CLI, HF Hub, REST endpoint), Claude submits itself after the user says so in chat when starting autonomous mode. If it is a web upload form, Claude prepares the file and sends a phone notification for the user to upload; Claude does not click website submit buttons.
- **Staying in touch:** a phone notification (`PushNotification`) after every submission (val, LB, what changed) and on every crash. The user steers by typing in the session ("try a bigger model next", "stop"); the loop reads it on its next iteration.
- **Keep-awake:** autonomy runs on the user's PC; the setup block turns on keep-awake. If the PC sleeps, the loop stops.

## 7. Skill map

| Block / step | Skill or tool | Purpose |
|---|---|---|
| Whole day | `ponytail` | Minimal code, less to debug late |
| 09:00 setup | `hf-cli` | Login, model/dataset download, HF Jobs, private checkpoint repo |
| 09:00 rules | `WebSearch` (15-min cap) | Current best open models, past winning approaches |
| 09:30 data | `data:explore-data` | Sizes, label balance, nulls, duplicates, leakage hints |
| 09:30 val split | `data:statistical-analysis` | Val distribution matches test |
| Loop 3 train | `Monitor` + `PushNotification` | Stream logs; ping when done or crashed |
| Any crash/OOM/NaN | `superpowers:systematic-debugging` | Root cause, not guessing |
| Loop 4 errors | `data:create-viz` | Learning curves, confusion/error plots |
| Loop 5 decide | `data:statistical-analysis` | Is the gain real or noise |
| Before every submit | `superpowers:verification-before-completion` + `check_submission.py` | Claim "valid" only after the check passes |
| Parallel mode | `superpowers:dispatching-parallel-agents` | Two single-change experiments at once |
| LLM tasks with generated-text metric | `mlflow:build-a-scorer` | Local scorer mimicking the organizer's metric |
| 22:00 verify | `data:validate-data` | Sanity-check final predictions |
| Block boundaries | Timed reminders (`CronCreate`) | "12:30: submit baseline", "20:00: start final run" |
| Autonomous phase | `/loop` (dynamic, self-paced) | Runs `/compete` repeatedly |

Not used on the day: `brainstorming` and `writing-plans` (too slow, the plan exists), `deep-research` (too slow, use `WebSearch`), `build-dashboard` (`experiments.md` is enough), MLflow GenAI tracing skills (not relevant unless the task is an agent or RAG system).

If `CronCreate` reminders turn out not to fire inside a session, `/compete` prints the clock and the next deadline at every step instead (verified during implementation).

## 8. Failure runbook (in `SKILL.md`, applied without asking in autonomous mode)

| Failure | Fix, in order |
|---|---|
| GPU out of memory | Halve batch size and double gradient accumulation → gradient checkpointing → 4-bit loading or next smaller model |
| Loss NaN / diverges | LR ÷3–10 → bf16 instead of fp16 → check labels/data |
| Cloud job dies / no GPU | Retry once → organizer GPU or fallback provider |
| Submission rejected | `check_submission.py` finds the issue → fix → resubmit |
| Val and LB disagree | Trust val unless the split looks unlike test, then re-check the split; never tune to the public LB |
| Claude session crash / full context | New session, `/loop /compete` resumes from state files |
| Running late | That block's hard rule (§4) |

Best checkpoint pushed to a private HF repo after every kept loop; submissions numbered and never overwritten. No crash or bad loop can lose the best result.

## 9. `check_submission.py`

`python check_submission.py <sample_submission> <submission>` exits non-zero with a clear message unless the submission matches the sample on: column names and order, row count, ID set, no empty values, columns that are numeric in the sample are numeric in the submission. Value ranges are task-specific, so they are checked by `data:validate-data` (22:00 block), not by this script. Supports CSV (the common case); other formats are noted as a shortcut limit in the code. Includes a self-test (`--self-test`) that builds a good and several broken files and asserts the right verdicts.

## 10. Testing (done during implementation, not the user's time)

- `check_submission.py --self-test` passes.
- CPU rehearsal of `/compete` on a tiny public tabular dataset with `recipes/tabular.md`: state files get created, blocks advance, one loop iteration logs and keeps/reverts correctly, the format check rejects a deliberately broken file.
- Verify whether `CronCreate` reminders fire in-session; fall back to printed deadlines if not.
- **Not tested:** GPU recipe cards end to end (needs paid GPU time and the real task). This is the main remaining risk; the 2-minute smoke test in every loop is the safety net.

## Out of scope

Prep days, dry runs by the user, pre-written training scripts, hyperparameter-search frameworks, ensembling frameworks, dashboards, a custom AutoML layer.
