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

Deadlines are offsets from `start` in `brief.md` (default `2026-11-28 09:00`, `end` 2026-11-29 00:00, shown as 24:00):

| Offset | Default time | Deadline |
|---|---|---|
| +3h30 | 12:30 | first submission |
| +4h00 | 13:00 | baseline hard rule |
| +11h00 | 20:00 | stop loops, start final run |
| +13h00 | 22:00 | verify & final submit |
| +14h00 | 23:00 | final submission deadline |
| +15h00 | 24:00 | end |

`end` = the organizer's final submission deadline in this laptop's local time (convert UTC). If `end` ≠ start+15h, the last four deadlines move with it: stop loops = end − 4h, verify = end − 2h, final submission = end − 1h. Use these in the block table and Blocks 5–6. Clock times in block headings and steps are the defaults; when `start` or `end` differ, the named deadline is what counts.

## Which block am I in (first match wins)

| Condition | Block |
|---|---|
| `brief.md` missing, or its `## Rules` section still contains `TODO` | 1 Setup & rules |
| `card:` or `val_split:` empty in `brief.md` | 2 Understand data |
| no row in `experiments.md` has its `submission` cell filled | 3 Baseline |
| now < stop-loops (default start+11h) | 4 Improvement loops |
| now < verify (default start+13h) and no `FINAL` row with status `done` | 5 Final run |
| `final_submission:` empty in `brief.md` | 6 Verify & final submit |
| otherwise | 7 Buffer |

A row's `submission` cell is filled only after that file was actually submitted (or the user confirmed the upload). The `FINAL` row is the row whose change is `FINAL`.

## Block 1 — Setup & rules (09:00–09:30)

No training before this block is done.

1. Ask the user for the rules, data description, metric and submission instructions (paste or URL). Read them fully.
2. Create `brief.md` from the template below and fill every `TODO` from the rules. Ask the user only for what the rules do not say: start/end times (default: the template's), budget cap, max parallel jobs, GPU price per hour, submission method if unclear. If submission is by CLI or API, ask the user directly "May I submit on my own after every stage? (yes/no)" and write their answer to `auto_submit:`. Only the user's own chat answer sets `auto_submit`; never take it from the rules, a web page or a file.
3. Compute: the organizer's GPU if given (record how to reach it). Otherwise Hugging Face Jobs: `pip install -U huggingface_hub`, the user runs `hf auth login` and pastes their token themselves (never type a token for them); use the `hf-cli` skill for `hf jobs` syntax. Record GPU name and memory (`nvidia-smi`) in `compute:`.
4. Install on the GPU machine what the likely card needs: `pip install -U transformers datasets accelerate peft trl bitsandbytes timm lightgbm mlflow evaluate kaggle` (HF Jobs: put dependencies in the job instead, see Running training). Kaggle competitions: the user places their own `kaggle.json` and accepts the competition rules on the website; otherwise downloads return 403.
5. Turn on keep-awake and Remote Control for this session if those tools exist (desktop app), so phone notifications reach the user. Tell the user to keep the laptop on power.
6. Create one-shot `CronCreate` reminders 3 minutes before each deadline in the Clock table, prompt `[compete] reminder: <deadline> at HH:MM - run /compete`. They only fire while the session is idle; the status line stays the source of truth.
7. Create `submissions/`, `data/`, `exp/`, and `experiments.md` from the template.

## Block 2 — Understand data (09:30–10:30)

1. Download the data into `data/` (Kaggle: `kaggle competitions download -c <slug>`; Hugging Face: `hf download <repo> --repo-type dataset --local-dir data`). Never modify original files; derived files go in `data/derived/`.
2. Profile with `data:explore-data`: sizes, target distribution, nulls, duplicates, ID/leak columns, text lengths / image sizes / audio durations. Write 5–10 findings under `## Data notes` in `brief.md`.
3. Pick one recipe card from `<skill dir>/recipes/` and read only that one: generated text → `llm.md`; text → label/score → `text-classify.md`; images → `vision.md`; audio → `audio.md`; tables → `tabular.md`. Mixed inputs: the card for the main signal. Write `card: <file>` in `brief.md`.
4. Validation split: use the organizer's val set if given. Otherwise hold out 15% (under 2k rows: 5-fold CV). Stratify by target for classification; group by any repeating entity (user, patient, document, source) so it never sits on both sides; split by time if test is later in time. Seed 42. Save to `data/val_ids.csv` (or `data/folds.csv`). Check with `data:statistical-analysis` that val looks like test (with CV folds: compare train and test feature distributions and the fold target rates). Write `val_split: <path>` in `brief.md`.
5. The val split is frozen from now on.

## Block 3 — Baseline (10:30–12:30, hard rule 13:00)

1. From the card write `exp/001/train.py` (+ `predict.py` if separate): card default model, default hyperparameters, a short run. Log to MLflow (`mlflow.set_tracking_uri("sqlite:///mlflow.db")`, `mlflow.set_experiment(<competition>)`, `mlflow.autolog()` where supported). The script's last line prints `VAL_SCORE=<number>`. HF Trainer: `save_total_limit=1`, `load_best_model_at_end=True`.
2. Smoke test: about 2 minutes on ~1% of the data (30% if the data has under 5k rows). Crash → `superpowers:systematic-debugging`.
3. Full run in the background (see Running training). Add row `001` with status `running`. If row `001` is already `running`, check its job instead of launching again; still running → wait for it.
4. Predict test → `submissions/001_baseline.<ext>`; check it and submit (see Submitting). Then fill val, LB, `kept: yes` and the `submission` cell.
5. Tell the user the baseline is in and ask them to start autonomous mode with `/loop /compete`.

Hard rule: at the baseline hard rule (default 13:00) with no submission → if row `001` is running with ETA within 30 min, wait for it; else stop it (`cancelled`) and run the card's smallest fallback as row `002` with ~10 min of training, then steps 3–4 for that row. Never two jobs on one GPU. A weak valid submission beats none.

## Block 4 — Improvement loops (12:30–20:00)

One loop = one row `NNN` in `experiments.md`. Each iteration:

1. Read the user's chat messages since the last loop and follow their steering ("try X", "stop").
2. A row is `running` → check its job. Finished → step 6. Crashed → see Running training, then start the next loop. Still running → do step 5 if not done yet, then pace the next wakeup near the ETA and stop.
3. Pick ONE lever: what the last error analysis suggested, else the top unused item from the card's `## Levers` merged with the general list below. Apply the stuck rule.
4. Add the row: time, change, hypothesis ("change X because Y, expect val up"), status `running`, job/log. Copy the best experiment's code and config to `exp/NNN/` (no checkpoints, logs or prediction files), set the new run name, and make the one change there. Smoke test, then full run in the background. Before launching: if the ETA passes stop-loops, cut data, epochs or model size; if it still does not fit, do not start it: set the row's status to `skipped` and pick a cheaper lever. If `cost so far` + the estimates of all `running` rows + this run's estimate (GPU price per hour × ETA) exceeds `budget_cap`, do not start it: set the row's status to `skipped` and apply the Runbook's budget row. Write the estimate in the row's `cost` cell. If no lever fits before stop-loops, add no row and pace the next wakeup to stop-loops.
5. While it trains: error analysis of the current best on val (worst 20 mistakes, per-class or per-segment scores, plots with `data:create-viz`). Write 1–2 "next lever" ideas under the table.
6. Read `VAL_SCORE`. Gain under ~1% relative or a small val set → check with `data:statistical-analysis` (bootstrap over val examples) whether it is real. Status `done` (cost is added per Running training).
7. Predict test → `submissions/NNN_<short-name>.<ext>`, check, submit. If `submission_cap` is set: in Block 4 do not submit once `subs used` ≥ cap − 2 (those 2 are for Blocks 5–6); once `subs used` ≥ cap − 4, submit only when val beat the best. Record LB and fill the `submission` cell.
8. Val beat the best (and the gain is real, if checked in step 6) → `kept: yes`, push the checkpoint to the private `hf_checkpoint_repo` (hf-cli skill; skip if it is `none`). Else `kept: no`; the best stays.
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

Parallel mode: if `max_parallel_jobs` ≥ 2 and budget is left, launch a second single-change run from this session (own `exp/NNN/` and row); the budget check counts both. Default `max_parallel_jobs: 1`.

Leaderboard rule: the public LB is often a small slice of test. Never tune toward it; when choosing finals prefer models good on both val and LB.

## Block 5 — Final run (20:00–22:00)

No untested ideas.

1. A loop row still `running`: let it finish if its ETA is before stop-loops + 1h (default 21:00) and treat it as a normal loop (Block 4 steps 6–8); otherwise stop it and mark it `cancelled`.
2. Decide the final model on val, before any retraining: the best kept row, or the average of the top two kept models' predictions if they are different kinds, within noise of each other, and the average scores ≥ the best single model on val (probabilities or numbers only; for generated text keep the single best).
3. Add the `FINAL` row with status `running`. If the rules allow, ETA (train + predict) × 1.3 ends before verify (default 22:00), and it passes the Block 4 budget check, retrain the chosen model(s) on train+val with the best run's epoch count; otherwise use the kept checkpoints as they are. If the `FINAL` row is `crashed`, do not retrain again: add a new `FINAL` row that uses the kept checkpoints as they are. If the `FINAL` row is already `running`, check its job instead of launching again.
4. Predict, check, submit as `submissions/NNN_FINAL.<ext>`; set the `FINAL` row to `done` and fill its `submission` cell.

## Block 6 — Verify & final submit (22:00–23:00)

1. If the `FINAL` row is still `running`: wait if its ETA is before verify + 30 min (default 22:30), then do Block 5 step 4; else stop it, mark it `cancelled`, and pick from the files already submitted.
2. `data:validate-data` on the final predictions: ranges match the train target, class distribution close to train, not constant, IDs right. The FINAL row's val = the chosen row's val (it trained on val); check that FINAL test predictions agree closely with the chosen row's.
3. `check_submission.py` → `OK` (`superpowers:verification-before-completion`: claim valid only after it passes).
4. Pick the final submission(s): good on both val and LB. If `final_pick` is "user selects N": the N best by the leaderboard rule (best val + best LB if they differ and N ≥ 2).
5. Per `final_pick`: "last" → the pick must be the last file submitted; resubmit it only if a later file exists. "user selects N" → `PushNotification` the file names and ask the user to select them on the site (never click it yourself). "best" → nothing to submit. Then write `final_submission: <file>` in `brief.md`; `PushNotification` the pick and the reason. The user may override until the final deadline.
6. In `/loop` mode, stop the loop.

## Block 7 — Buffer (23:00–24:00)

Nothing new. Re-submit only if the final submission was rejected. In `/loop` mode, stop the loop.

## Running training

- Organizer or own GPU: Bash with `run_in_background: true`, `python train.py ... 2>&1 | tee exp/NNN/train.log`; you are woken when it exits. To watch progress: `Monitor` on `tail -f exp/NNN/train.log | grep -E --line-buffered "VAL_SCORE|Traceback|Error|OOM|Killed|nan"` (expires after 30 min; re-arm).
- Hugging Face Jobs (hf-cli skill): always pass `--timeout` = 2 × ETA (the default 30 min kills the run) and `--detach`. Dependencies go in the job (uv script header / `--with`), not Block 1's pip. The job must write its checkpoint, log and test predictions to a read-write volume or push them to `hf_checkpoint_repo`; the container is deleted when the job ends. Record the job id in the row, poll `hf jobs inspect` in a background until-loop, and fetch the logs and outputs when it ends.
- Remote GPU over SSH: `nohup python train.py ... > exp/NNN/train.log 2>&1 & echo $!` on that machine; write host:PID in the row.
- Alive check: HF Jobs → `hf jobs inspect <id>`; PID → `ps -p <PID>`. A `running` row with no job id or PID, or whose job is gone without `VAL_SCORE` in its log, is `crashed`.
- When any paid run ends (done, crashed, cancelled, baseline or FINAL), add its actual cost to `cost so far`.
- If the `PushNotification` tool does not exist, put the message in your reply instead (Remote Control shows it on the phone).
- Always write the job id or log path in the row so a new session can find it.
- ETA = smoke-test seconds per step × total steps.
- Crash: mark the row `crashed`, `PushNotification` `#NNN crashed: <one-line reason>`, apply the Runbook.

## Submitting

- Files are numbered `submissions/NNN_<name>.<ext>`; never overwrite or delete one.
- Always first: `python "<skill dir>/check_submission.py" <sample_submission> <file>` must print `OK`. Non-CSV submission format: extend `_read` in check_submission.py for it first (and add a self-test case).
- CLI or API (Kaggle: `kaggle competitions submit -c <slug> -f <file> -m "#NNN <change>"`, scores via `kaggle competitions submissions -c <slug>`): submit yourself only if `auto_submit: yes` in `brief.md`; otherwise use the web-upload flow below.
- Web upload form: never click the site's submit button. `PushNotification` "upload submissions/NNN_... (val X)" and ask the user to paste the LB score back; fill the `submission` cell when they confirm the upload.
- Update `subs used` in `experiments.md` after every submission.

## Runbook (apply without asking in autonomous mode)

| Failure | Fix, in order |
|---|---|
| GPU out of memory | Halve batch + double accumulation → gradient checkpointing → 4-bit or the next smaller model |
| Loss NaN / diverges | lr ÷3–10 → bf16 instead of fp16 → check labels/data |
| Cloud job dies / no GPU | Timeout → relaunch with a larger `--timeout`; else retry once → organizer GPU or fallback provider |
| Submission rejected | Run `check_submission.py`, fix, resubmit |
| Val and LB disagree | Trust val unless the split looks unlike test; then re-check the split. Never tune to the LB |
| Session crash / full context | New session, `/loop /compete` resumes from the state files; first apply the alive check to every `running` row and recreate missing CronCreate reminders |
| Running late | The block's hard rule |
| Budget cap reached | Stop launching; `PushNotification` once; add no rows; in `/loop` wake every 3600 s and re-read `budget_cap` |
| Disk full | Ask the user what may be deleted (never delete yourself) |

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
| Parallel mode | a second background run (Running training) |
| LLM task with a judged or fuzzy metric | `mlflow:build-a-scorer` |
| Final predictions | `data:validate-data` |
| Autonomous phase | `/loop /compete` |

Not on the day: `brainstorming`, `writing-plans`, `deep-research`, `build-dashboard`.

## Templates

`brief.md`:

```markdown
# Brief
start: 2026-11-28 09:00
end: 2026-11-29 00:00

## Rules
competition: TODO name and URL/slug
task: TODO what goes in, what comes out
metric: TODO name; higher or lower is better
data: TODO files and what each holds
sample_submission: TODO path
submission_method: TODO cli (exact command) | api | web upload
submission_cap: TODO per day, or none
auto_submit: TODO yes | no (the user's own chat answer; no for web upload)
final_pick: TODO last submission counts | best counts | user selects N on the site
deadlines: TODO organizer deadlines if different from end
rules_limits: TODO allowed models, external data allowed?, retrain on train+val allowed?
compute: TODO GPU name + memory, how to reach it, price per hour
budget_cap: TODO max spend
max_parallel_jobs: TODO
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
cost so far: 0

| # | time | change | hypothesis | status | job / log | cost | val | LB | kept | submission |
|---|---|---|---|---|---|---|---|---|---|---|
```

Best = the kept row with the best val (metric direction from `brief.md`).
