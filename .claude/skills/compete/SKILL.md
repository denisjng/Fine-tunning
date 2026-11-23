---
name: compete
description: Run a one-day ML fine-tuning competition end to end for any modality (LLM, text, vision, audio, tabular) - setup, data, baseline, autonomous improvement loops with a submission every stage, final submit. Use when the user types /compete or /loop /compete, or asks to start, continue or resume the competition. Keeps state in brief.md, experiments.md and submissions/ in the competition folder.
---

# /compete

You drive a one-day fine-tuning competition for a beginner. Goal: the best final rank, with a valid submission after every stage from the baseline on. Ponytail rules apply: minimal code, one change per loop. Explain each step in one plain sentence; give a default instead of a menu.

`<skill dir>` = the "Base directory for this skill" shown when this skill loads. The **competition folder** is the current folder, or the one the user names; all state files live there.

Never edit the val split or the test data. Never delete experiments, checkpoints or submissions.

## Every call, in this order

1. Read `brief.md` and `experiments.md`, list `submissions/` (any may be missing).
2. Read the clock (`date "+%Y-%m-%d %H:%M"`) and find the block with the table below.
3. If you are past a hard-rule time, say so first and apply the hard rule.
4. Do the **first unfinished step** of that block.
   - Guided (`/compete`): do one step, then stop and say what comes next.
   - Autonomous (`/loop /compete`): keep doing steps until something has to wait (a training run), then pace the next wakeup near its ETA (60–3600 s). Background Bash jobs also wake you when they exit.
5. End every reply with the status line:
   `[compete] HH:MM | block N <name> | best val <score> (#NNN) | subs <used>/<cap> | next: <deadline> HH:MM (<time left>)`

## Clock

Deadlines are offsets from `start` in `brief.md` (default `2026-11-28 09:00`, `end` 24:00):

| Offset | Default time | Deadline |
|---|---|---|
| +3h30 | 12:30 | first submission |
| +4h00 | 13:00 | baseline hard rule |
| +11h00 | 20:00 | stop loops, start final run |
| +13h00 | 22:00 | verify & final submit |
| +14h00 | 23:00 | final submission deadline |
| +15h00 | 24:00 | end |

## Which block am I in (first match wins)

| Condition | Block |
|---|---|
| `brief.md` missing, or it still contains `TODO` | 1 Setup & rules |
| `card:` or `val_split:` empty in `brief.md` | 2 Understand data |
| `submissions/` empty | 3 Baseline |
| now < start+11h | 4 Improvement loops |
| now < start+13h and no `FINAL` row in `experiments.md` | 5 Final run |
| `final_submission:` empty in `brief.md` | 6 Verify & final submit |
| otherwise | 7 Buffer |

## Block 1 — Setup & rules (09:00–09:30)

No training before this block is done.

1. Ask the user for the rules, data description, metric and submission instructions (paste or URL). Read them fully.
2. Create `brief.md` from the template below and fill every `TODO` from the rules. Ask the user only for what the rules do not say: budget cap, max parallel jobs, submission method if unclear.
3. Compute: the organizer's GPU if given (record how to reach it). Otherwise Hugging Face Jobs: `pip install -U huggingface_hub`, the user runs `hf auth login` and pastes their token themselves (never type a token for them); use the `hf-cli` skill for `hf jobs` syntax. Record GPU name and memory (`nvidia-smi`) in `compute:`.
4. Install on the GPU machine what the likely card needs: `pip install -U transformers datasets accelerate peft trl bitsandbytes timm lightgbm mlflow evaluate`.
5. Turn on keep-awake and Remote Control for this session if those tools exist (desktop app), so phone notifications reach the user. Tell the user to keep the laptop on power.
6. Create one-shot `CronCreate` reminders 3 minutes before each deadline in the Clock table, prompt `[compete] reminder: <deadline> at HH:MM - run /compete`. They only fire while the session is idle; the status line stays the source of truth.
7. Create `submissions/`, `data/`, `exp/`, and `experiments.md` from the template.

## Block 2 — Understand data (09:30–10:30)

1. Download the data into `data/` (Kaggle: `kaggle competitions download -c <slug>`; Hugging Face: `hf download <repo> --repo-type dataset --local-dir data`). Never modify original files; derived files go in `data/derived/`.
2. Profile with `data:explore-data`: sizes, target distribution, nulls, duplicates, ID/leak columns, text lengths / image sizes / audio durations. Write 5–10 findings under `## Data notes` in `brief.md`.
3. Pick one recipe card from `<skill dir>/recipes/` and read only that one: generated text → `llm.md`; text → label/score → `text-classify.md`; images → `vision.md`; audio → `audio.md`; tables → `tabular.md`. Mixed inputs: the card for the main signal. Write `card: <file>` in `brief.md`.
4. Validation split: use the organizer's val set if given. Otherwise hold out 15% (under 2k rows: 5-fold CV). Stratify by target for classification; group by any repeating entity (user, patient, document, source) so it never sits on both sides; split by time if test is later in time. Seed 42. Save to `data/val_ids.csv` (or `data/folds.csv`). Check with `data:statistical-analysis` that val looks like test. Write `val_split: <path>` in `brief.md`.
5. The val split is frozen from now on.

## Block 3 — Baseline (10:30–12:30, hard rule 13:00)

1. From the card write `exp/001/train.py` (+ `predict.py` if separate): card default model, default hyperparameters, a short run. Log to MLflow (`mlflow.set_tracking_uri("sqlite:///mlflow.db")`, `mlflow.set_experiment(<competition>)`, `mlflow.autolog()` where supported). The script's last line prints `VAL_SCORE=<number>`.
2. Smoke test: about 2 minutes on ~1% of the data. Crash → `superpowers:systematic-debugging`.
3. Full run in the background (see Running training). Add row `001` with status `running`.
4. Predict test → `submissions/001_baseline.<ext>`; check it (see Submitting) and submit. Fill val, LB, `kept: yes`.
5. Tell the user the baseline is in, ask them to start autonomous mode with `/loop /compete`, and to say in chat whether you may submit via CLI/API on your own.

Hard rule: at 13:00 with no submission → switch to the card's smallest fallback and cut training to ~10 minutes. A weak valid submission beats none.

## Block 4 — Improvement loops (12:30–20:00)

One loop = one row `NNN` in `experiments.md`. Each iteration:

1. Read the user's chat messages since the last loop and follow their steering ("try X", "stop").
2. A row is `running` → check its job. Finished → step 6. Still running → do step 5 if not done yet, then pace the next wakeup near the ETA and stop.
3. Pick ONE lever: what the last error analysis suggested, else the top unused item from the card's `## Levers` merged with the general list below. Apply the stuck rule.
4. Add the row: time, change, hypothesis ("change X because Y, expect val up"), status `running`, job/log. Copy the best experiment's folder to `exp/NNN/` and make the one change there. Smoke test, then full run in the background. If the ETA passes the next deadline, cut data, epochs or model size first.
5. While it trains: error analysis of the current best on val (worst 20 mistakes, per-class or per-segment scores, plots with `data:create-viz`). Write 1–2 "next lever" ideas under the table.
6. Read `VAL_SCORE`. Gain under ~1% relative or a small val set → check with `data:statistical-analysis` (bootstrap over val examples) whether it is real. Status `done`.
7. Predict test → `submissions/NNN_<short-name>.<ext>`, check, submit. If submissions left today ≤ loops left, submit only when val beat the best. Record LB.
8. Val beat the best → `kept: yes`, push the checkpoint to the private `hf_checkpoint_repo` (hf-cli skill). Else `kept: no`; the best stays.
9. `PushNotification`: `#NNN <change>: val <x> (best <y>), LB <z>`.

General lever list (best payoff first):
1. Data/format bugs: label mapping, truncation, prompt template, image size.
2. Learning rate and number of epochs.
3. A better or bigger base model, if it fits the GPU and the time.
4. Data work: cleaning, augmentation, external data if allowed.
5. The card's modality-specific levers.
6. Inference tricks: TTA, threshold tuning, decoding settings.
7. Ensembling: only in block 5.

Stuck rule: 3 loops in a row with `kept: no` → the next loop must be a new base model or a data change, not another hyperparameter. The same change crashed twice → status `crashed`, skip that lever.

Parallel mode: if `max_parallel_jobs` ≥ 2 and budget is left, run two loops at once (one change each, own `exp/NNN/` and row) with `superpowers:dispatching-parallel-agents`.

Leaderboard rule: the public LB is often a small slice of test. Never tune toward it; when choosing finals prefer models good on both val and LB.

## Block 5 — Final run (20:00–22:00)

No untested ideas.

1. Take the best kept row. If the rules allow and ETA × 1.3 ends before 22:00, retrain the same config on train+val with the best run's epoch count. Otherwise use the best checkpoint as is.
2. If the top two kept models are different kinds and within noise of each other, average their test predictions (probabilities or numbers; for generated text keep the single best). Confirm on val that the average is ≥ the best single model.
3. Predict, check, submit as `submissions/NNN_FINAL.<ext>`; row change `FINAL`.

## Block 6 — Verify & final submit (22:00–23:00)

1. `data:validate-data` on the final predictions: ranges match the train target, class distribution close to train, not constant, IDs right.
2. `check_submission.py` → `OK` (`superpowers:verification-before-completion`: claim valid only after it passes).
3. Pick the final submission(s): good on both val and LB. Two picks allowed → best val + best LB if they differ.
4. Submit or select it; write `final_submission: <file>` in `brief.md`; `PushNotification` the pick and the reason. The user may override until 23:00.
5. In `/loop` mode, stop the loop.

## Block 7 — Buffer (23:00–24:00)

Nothing new. Re-submit only if the final submission was rejected.

## Running training

- Organizer or own GPU: Bash with `run_in_background: true`, `python train.py ... 2>&1 | tee exp/NNN/train.log`; you are woken when it exits. To watch progress: `Monitor` on `tail -f exp/NNN/train.log | grep -E --line-buffered "VAL_SCORE|Traceback|Error|OOM|Killed|nan"` (expires after 30 min; re-arm).
- Hugging Face Jobs: launch with the hf-cli skill; record the job id in the row; poll its status in a background until-loop every few minutes; fetch logs when it ends.
- Always write the job id or log path in the row so a new session can find it.
- ETA = smoke-test seconds per step × total steps.

## Submitting

- Files are numbered `submissions/NNN_<name>.<ext>`; never overwrite or delete one.
- Always first: `python "<skill dir>/check_submission.py" <sample_submission> <file>` must print `OK`.
- CLI or API (Kaggle: `kaggle competitions submit -c <slug> -f <file> -m "#NNN <change>"`, scores via `kaggle competitions submissions -c <slug>`): submit yourself only after the user said so in chat in this session.
- Web upload form: never click the site's submit button. `PushNotification` "upload submissions/NNN_... (val X)" and ask the user to paste the LB score back.
- Update `subs used` in `experiments.md` after every submission.

## Runbook (apply without asking in autonomous mode)

| Failure | Fix, in order |
|---|---|
| GPU out of memory | Halve batch + double accumulation → gradient checkpointing → 4-bit or the next smaller model |
| Loss NaN / diverges | lr ÷3–10 → bf16 instead of fp16 → check labels/data |
| Cloud job dies / no GPU | Retry once → organizer GPU or fallback provider |
| Submission rejected | Run `check_submission.py`, fix, resubmit |
| Val and LB disagree | Trust val unless the split looks unlike test; then re-check the split. Never tune to the LB |
| Session crash / full context | New session, `/loop /compete` resumes from the state files |
| Running late | The block's hard rule |
| Budget cap reached | Stop launching, `PushNotification`, wait for the user |

## Skill map

| When | Use |
|---|---|
| All day | `ponytail` |
| Setup, downloads, HF Jobs, checkpoint pushes | `hf-cli` |
| Rules: current best models, past winning approaches | `WebSearch`, 15-minute cap |
| Data profile | `data:explore-data` |
| Val split matches test; is a gain real | `data:statistical-analysis` |
| Training progress | `Monitor`, `PushNotification` |
| Any crash | `superpowers:systematic-debugging` |
| Error analysis plots | `data:create-viz` |
| Before every submission | `superpowers:verification-before-completion` + `check_submission.py` |
| Parallel mode | `superpowers:dispatching-parallel-agents` |
| LLM task with a judged or fuzzy metric | `mlflow:build-a-scorer` |
| Final predictions | `data:validate-data` |
| Autonomous phase | `/loop /compete` |

Not on the day: `brainstorming`, `writing-plans`, `deep-research`, `build-dashboard`.

## Templates

`brief.md`:

```markdown
# Brief
start: 2026-11-28 09:00
end: 2026-11-28 24:00

## Rules
competition: TODO name and URL/slug
task: TODO what goes in, what comes out
metric: TODO name; higher or lower is better
data: TODO files and what each holds
sample_submission: TODO path
submission_method: TODO cli (exact command) | api | web upload
submission_cap: TODO per day, or none
deadlines: TODO organizer deadlines if different from end
rules_limits: TODO allowed models, external data allowed?, retrain on train+val allowed?
compute: TODO GPU name + memory, how to reach it
budget_cap: TODO max spend; max_parallel_jobs
hf_checkpoint_repo: TODO <user>/<name> (private)

## Choices
card:
val_split:
final_submission:

## Data notes
```

`experiments.md`:

```markdown
# Experiments
subs used: 0 / <cap>

| # | time | change | hypothesis | status | job / log | val | LB | kept | submission |
|---|---|---|---|---|---|---|---|---|---|
```

Best = the kept row with the best val (metric direction from `brief.md`).
