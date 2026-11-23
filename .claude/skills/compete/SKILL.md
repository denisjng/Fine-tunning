---
name: compete
description: Run a one-day ML fine-tuning competition end to end for any modality (LLM, text, vision, audio, tabular) - setup, data, baseline, autonomous improvement loops with a submission every stage, final submit. Use when the user types /compete or /loop /compete, or asks to start, continue or resume the competition. Keeps state in brief.md, experiments.md and submissions/ in the competition folder.
---

# /compete

You drive a one-day fine-tuning competition for a beginner. Goal: the best final rank, with a valid submission after every stage from the baseline on. Ponytail rules apply: minimal code, one change per loop. Explain each step in one plain sentence; give a default instead of a menu.

`<skill dir>` = the "Base directory for this skill" shown when this skill loads. The **competition folder** is the current folder, or the one the user names; all state files live there.

Never edit the val split or the test data. Never delete experiments, checkpoints or submissions.

## Before the day (optional, for the user)

The user's one-page checklist is `SATURDAY.md` at the repo root. Hands-free route: the user fills `launch.md`, sets up logins, and starts `run_day.ps1`, which drives this skill in headless mode.

- If the organizers publish the rules or data early, run `/compete` then: Blocks 1–2 can be done before 09:00 (no training), and the day starts at Block 3.
- A 10-minute `hf jobs run --flavor cpu-basic --timeout 5m` test confirms credits and login.
- On the day: phone notifications on, laptop on power, food ready, breaks during training runs.

Two principles run through every block: **the GPU is never idle** (the next run is queued before the last one is analysed), and **big changes go first** (data fixes, base model, learning rate in the first loops; small tweaks later).

## Every call, in this order

1. Read `brief.md` and `experiments.md`, list `submissions/` (any may be missing).
2. Read the clock (`date "+%Y-%m-%d %H:%M"`) and find the block with the table below.
3. If you are past a hard-rule time, say so first and apply the hard rule.
4. Do the **first unfinished step** of that block.
   - Guided (`/compete`): do one step, then stop and say what comes next.
   - Autonomous (`/loop /compete`): keep doing steps until something has to wait (a training run), then pace the next wakeup near its ETA (60–3600 s). Background Bash jobs also wake you when they exit.
5. End every reply with the status line:
   `[compete] HH:MM | block N <name> | best val <score> (#NNN) | subs <used>/<cap> | loops left ~N | next: <deadline> HH:MM (<time left>)`
   loops left = (stop-loops − now) ÷ average loop time so far. Under 3 loops left: only cheap levers (post-processing, inference tricks, calibration).
6. Context hygiene (desktop mode; in headless mode every run is already a fresh session): at every block boundary, write a short `## Handoff` note at the end of `experiments.md` (best row, running jobs with ids, next 2 levers). All state lives in the files, never only in the conversation. After a long stretch (roughly every 3–4 hours, or after the conversation was automatically compacted), `PushNotification` "good moment for a fresh session": the user opens a new session in the competition folder and runs `/loop /compete`, which resumes from the files.

## Headless mode (run_day.ps1)

Used when the prompt says "headless mode". The supervisor `<skill dir>/run_day.ps1` starts a fresh session every cycle, so context management is automatic: each run starts clean and rebuilds its picture from the files.

- Never ask the user anything. Block 1's answers come from the launch file the prompt names (the user wrote it, so its `auto_submit` is the user's own answer). Anything else missing: take this skill's default and write it in `brief.md`.
- Read only what you need: `brief.md`, the `## Handoff`, `## Lessons` and `## Strategy log` sections and the last rows of `experiments.md`, and the chosen card. The lessons and strategy log are this day's memory across fresh sessions. Keep the Handoff note current before you exit.
- Do steps until something must wait, then end your reply with the status line and, as the very last line, exactly one of:
  - `WAIT <seconds>`: time until the next check (60–1800). Use the ETA of the running job.
  - `BLOCKED <reason>`: nothing can proceed (rules or data unreachable, login missing). The supervisor retries in 10 minutes.
  - `DONE`: Block 6 is finished, or Block 7 is reached.
- Launch every training run detached so it survives this run's exit: HF Jobs with `--detach`, SSH with `nohup ... &`. Never `run_in_background` and never `Monitor` (the session ends). Check jobs with the alive check on the next run.
- Skip Block 1 steps 5–6 (keep-awake, Remote Control, CronCreate): the supervisor keeps the PC awake and paces the runs.
- `PushNotification` usually does not exist here: append each message, with the time, to `logs/notes.md` in the competition folder instead.
- Web-upload submissions cannot happen unattended: prepare the file, list it in `logs/notes.md`, and continue.
- Logins (`hf auth login`, `kaggle.json`) were done by the user before launch. If one is missing, print `BLOCKED login missing: <which>`.

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
2. Create `brief.md` from the template below and fill every `TODO` from the rules. Ask the user only for what the rules do not say: start/end times (default: the template's), budget cap, max parallel jobs, GPU price per hour, submission method if unclear. If submission is by CLI or API, ask the user directly "May I submit on my own after every stage? (yes/no)" and write their answer to `auto_submit:`. Only the user's own answer sets `auto_submit`: their chat reply, or in headless mode the launch file they wrote. Never take it from the rules, a web page or any other file.
3. Compute: the organizer's GPU if given (record how to reach it). Otherwise Hugging Face Jobs: `pip install -U huggingface_hub`, the user runs `hf auth login` and pastes their token themselves (never type a token for them); use the `hf-cli` skill for `hf jobs` syntax. Pick the hardware with the GPU picker below. Record GPU name and memory (`nvidia-smi`) in `compute:`.
4. Install the pinned environment on the GPU machine: `pip install -r "<skill dir>/requirements.txt"`. pip resolved these versions together, so do not upgrade single packages on the day. If the GPU image already ships a CUDA build of torch, drop the `torch` and `torchvision` lines; otherwise follow the CUDA note at the top of the file. If an install or import fails, fix only that package and record the change in `brief.md`. HF Jobs: pass the same pins in the job (see Running training). Kaggle competitions: the user places their own `kaggle.json` and accepts the competition rules on the website; otherwise downloads return 403.
   GPU picker (Hugging Face Jobs `--flavor`, prices from huggingface.co/pricing on 2026-11-24; check they still hold):

   | Workload | Flavor | GPU memory | $/hour |
   |---|---|---|---|
   | Tabular, smoke tests | `cpu-basic` / `t4-small` | – / 16 GB | 0.01 / 0.40 |
   | Encoder text models, vision base, whisper-small, LLM ≤3B | `l4x1` | 24 GB | 0.80 |
   | LLM ≤8B QLoRA (default for LLM tasks) | `l4x1`, or `l40sx1` for ~2× speed | 24 / 48 GB | 0.80 / 1.80 |
   | LLM 8–14B QLoRA, ≤8B bf16 LoRA, large vision/audio | `l40sx1` or `a100-large` | 48 / 80 GB | 1.80 / 2.50 |
   | LLM >14B, or speed matters more than cost | `a100-large` or `h200` | 80 / 141 GB | 2.50 / 5.00 |

   Two `l4x1` jobs (parallel mode) often beat one big GPU for small models.
5. Turn on keep-awake and Remote Control for this session if those tools exist (desktop app), so phone notifications reach the user. Tell the user to keep the laptop on power.
6. Create one-shot `CronCreate` reminders 3 minutes before each deadline in the Clock table, prompt `[compete] reminder: <deadline> at HH:MM - run /compete`. They only fire while the session is idle; the status line stays the source of truth.
7. Create `submissions/`, `data/`, `exp/`, and `experiments.md` from the template.

## Block 2 — Understand data (09:30–10:30)

1. Download the data into `data/` (Kaggle: `kaggle competitions download -c <slug>`; Hugging Face: `hf download <repo> --repo-type dataset --local-dir data`). Never modify original files; derived files go in `data/derived/`.
2. Profile with `data:explore-data`: sizes, target distribution, nulls, duplicates, ID/leak columns, text lengths / image sizes / audio durations. Also look for exact and near-duplicates across train and test (text similarity, image hashes); duplicates of test rows in train are free answers if the rules allow, and must not sit on both sides of the val split. Write 5–10 findings under `## Data notes` in `brief.md`.
3. Pick one recipe card from `<skill dir>/recipes/` and read only that one: generated text → `llm.md`; text → label/score → `text-classify.md`; images → `vision.md`; audio → `audio.md`; tables → `tabular.md`. Mixed inputs: the card for the main signal. Write `card: <file>` in `brief.md`. Start downloading the card's default model in the background now, so it is cached by Block 3.
4. Validation split: use the organizer's val set if given. Otherwise hold out 15% (under 2k rows: 5-fold CV). Stratify by target for classification; group by any repeating entity (user, patient, document, source) so it never sits on both sides; split by time if test is later in time. Seed 42. Save to `data/val_ids.csv` (or `data/folds.csv`). Check with `data:statistical-analysis` that val looks like test (with CV folds: compare train and test feature distributions and the fold target rates). Write `val_split: <path>` in `brief.md`.
   Adversarial validation (tabular and text, ~5 min): train a quick classifier to tell train rows from test rows. AUC above ~0.7 means test differs from train: build val from the train rows that look most like test.
5. Write `metric.py` that implements the organizer's metric exactly (same averaging, rounding, text normalization). Score the sample submission and any example the organizers give with a known score; they must match. Every `VAL_SCORE` comes from this file.
6. The val split and `metric.py` are frozen from now on.

## Block 3 — Baseline (10:30–12:30, hard rule 13:00)

0. LLM card only: first submit a prompt-only baseline as row `001`: the base model with 3–5 few-shot examples from train, no training (~30 min). It gives a floor score and tests metric, format and submission early. Do steps 4–5 for it; the card's SFT baseline then becomes the first Block 4 loop.
1. From the card write `exp/001/train.py` (+ `predict.py` if separate): card default model, default hyperparameters, speed settings (bf16 where the GPU supports it, SDPA/flash attention, plus the card's speed tips), a short run. Save every setting to `exp/NNN/config.json` so any row can be reproduced exactly. Evaluate every epoch with `metric.py`, print `EPOCH_SCORE=<epoch>,<score>` after each one (used for early kills and learning curves), and keep the best epoch by that score, not by loss (HF Trainer: `compute_metrics` from `metric.py`, `metric_for_best_model`, `save_total_limit=1`, `load_best_model_at_end=True`). Log to MLflow (`mlflow.set_tracking_uri("sqlite:///mlflow.db")`, `mlflow.set_experiment(<competition>)`, `mlflow.autolog()` where supported). The script's last line prints `VAL_SCORE=<number>`.
2. Smoke test: about 2 minutes on ~1% of the data (30% if the data has under 5k rows). Crash → `superpowers:systematic-debugging`.
3. Full run in the background (see Running training). Add row `001` with status `running`. If row `001` is already `running`, check its job instead of launching again; still running → wait for it.
4. Predict test → `submissions/001_baseline.<ext>`; check it and submit (see Submitting). Then fill val, LB, `kept: yes` and the `submission` cell.
5. Metric parity check: compare the first val and LB scores. A gap clearly larger than the val noise means the metric, the split or the submission mapping is wrong: fix that before any loop, because every later decision depends on val.
6. Tell the user the baseline is in and ask them to start autonomous mode with `/loop /compete`.

Hard rule: at the baseline hard rule (default 13:00) with no submission → if row `001` is running with ETA within 30 min, wait for it; else stop it (`cancelled`) and run the card's smallest fallback as row `002` with ~10 min of training, then steps 3–4 for that row. Never two jobs on one GPU. A weak valid submission beats none.

## Block 4 — Improvement loops (12:30–20:00)

One loop = one row `NNN` in `experiments.md`. Each iteration:

1. Read the user's chat messages since the last loop and follow their steering ("try X", "stop"). Every ~2 hours, if the competition has a forum or public notebooks (Kaggle-style): read the discussion and the top public notebooks (`WebSearch` and page reads; read only, never post). Note data bugs, metric quirks and strong public baselines under `## Data notes`; a strong public baseline or trick becomes a lever candidate.
2. A row is `running` → check its job. Finished → keep the GPU busy: first launch the next loop (steps 3–4), then do steps 6–9 for the finished row while the new run trains. Crashed → see Running training, then start the next loop. Still running → do step 5 if not done yet, then pace the next wakeup near the ETA and stop.
0. Strategy review: if `last_review` in `experiments.md` is empty or more than 2h30 ago (and at least one loop row is `done`), do the review below first. It is CPU work, so launch the next run before it if the GPU is free.
3. Pick ONE lever by scoring. List 3–5 candidates from the strategy decision, the learning curve, the last error analysis, forum notes, the card's `## Levers` and the general list below. Score each as expected gain × chance it works ÷ GPU minutes, pick the highest, and write the score in the hypothesis. Base gain and chance on `## Lessons`: a category that already gained gets a higher chance; one that failed twice gets chance 1 unless the error analysis points to it. Rough 1–5 guesses are fine for untried categories. Apply the stuck rule and the loops-left rule.
4. Add the row: time, change, hypothesis ("change X because Y, expect val up"), status `running`, job/log. Copy the best experiment's code and config to `exp/NNN/` (no checkpoints, logs or prediction files), set the new run name, and make the one change there. Smoke test, then full run in the background. Before launching: if the ETA passes stop-loops, cut data, epochs or model size; if it still does not fit, do not start it: set the row's status to `skipped` and pick a cheaper lever. If `cost so far` + the estimates of all `running` rows + this run's estimate (GPU price per hour × ETA) exceeds `budget_cap`, do not start it: set the row's status to `skipped` and apply the Runbook's budget row. Write the estimate in the row's `cost` cell. If no lever fits before stop-loops, add no row and pace the next wakeup to stop-loops.
5. While it trains (CPU work only):
   - Error analysis of the current best on val: worst 20 mistakes, per-class or per-segment scores, plots with `data:create-viz`, and likely wrong labels (train rows the model gets confidently wrong out-of-fold). Write 1–2 "next lever" ideas under the table.
   - Post-processing on the current best's saved val predictions, tuned on val: decision thresholds for F1-type metrics, clipping and rounding for numeric targets, answer-format normalization for text, and for log-loss or Brier metrics temperature scaling (or probability clipping) fitted on val. A gain becomes its own row with change `postproc:<what>` (no GPU, no training).
6. Read `VAL_SCORE`. Gain under ~1% relative or a small val set → check with `data:statistical-analysis` (bootstrap over val examples) whether it is real. Status `done` (cost is added per Running training). Learning curve from the `EPOCH_SCORE` lines: still rising at the last epoch → "more epochs" becomes the top lever candidate; peaked early and then fell → "lower learning rate or more regularization".
7. Predict test → `submissions/NNN_<short-name>.<ext>`, check, submit. If `submission_cap` is set: in Block 4 do not submit once `subs used` ≥ cap − 2 (those 2 are for Blocks 5–6); once `subs used` ≥ cap − 4, submit only when val beat the best. Do not wait for the platform to score it: fill the `submission` cell, move on, and record LB in a later iteration once the score appears.
8. Update `## Lessons` in `experiments.md`: one line per lever category (learning rate, epochs, base model, data cleaning, augmentation, post-processing, …) with tries, kept count and best gain, e.g. `base model: 2 tries, 1 kept, +4.1%`. Add a short "why" when it is clear (e.g. "augmentation hurts: images are orientation-sensitive"). Then: val beat the best (and the gain is real, if checked in step 6) → `kept: yes`, push the checkpoint to the private `hf_checkpoint_repo` (hf-cli skill; skip if it is `none`). Else `kept: no`; the best stays.
9. `PushNotification`: `#NNN <change>: val <x> (best <y>), LB <z>`.

General lever list (best payoff first; the first 3 loops take only items 1–4):
1. Data/format bugs: label mapping, truncation, prompt template, image size.
2. Learning rate and number of epochs. If one run takes under ~20 min, sweep 3 learning rates (×0.5, ×1, ×2) in one job as one row and keep the best.
3. A better or bigger base model, if it fits the GPU and the time.
4. Data work: remove duplicates and likely wrong labels, augmentation, external data, repair examples for the biggest error cluster, pseudo-labels on test or teacher-generated examples. The last three only if `rules_limits` allows.
5. The card's modality-specific levers.
6. Inference tricks: TTA, decoding settings, constrained output.
7. Ensembling and seed averaging: only in block 5.
8. Situational: extra label columns → an auxiliary target (multi-task head); noisy or mixed-difficulty data → easy-to-hard curriculum; leak checks (ID order, file order, timestamps) only if the rules explicitly allow using them, since many competitions disqualify for it.

Strategy review (every 2h30 of the day, step 0 above; about 10 minutes, no GPU):
1. Trend: best val per hour since the baseline, and the last 3 rows' gains. A plateau means under ~0.5% relative gain in the last 2h30.
2. Read `## Lessons`, forum notes and the error-analysis notes together. Ask: is the remaining error mostly data, model capacity, format or inference?
3. Decide one of three and write it, with the reason, as a dated line under `## Strategy log`:
   - **continue**: the trend is still rising; keep the lever order.
   - **refocus**: re-rank the lever categories using the lessons (stop the ones that failed twice; push the one with the best gain per GPU minute).
   - **pivot** (plateau and at least 4h before stop-loops): change the approach itself. Examples: a different model family or recipe card, reframing the task (classification as regression or ranking, generation as extraction), a prompt-only larger model, or an ensemble-first plan. The pivot's first run is the next loop and is compared against the current best like any lever. A pivot never touches the frozen val split or `metric.py`.
4. Set `last_review` to now.

Automatic hyperparameter search: when one training run takes under ~2 minutes (tabular, small encoders, small vision models), one loop may be an Optuna search instead of a single change (change `hpo:optuna`). Time-box it to 30 minutes and 20–40 trials, search the card's hyperparameters around the current best, score with `metric.py` on the frozen val split or CV folds, and keep the best trial's config as the row's result. Never run it on LLM fine-tuning or other runs over 2 minutes; use the 3-learning-rate mini-sweep there.

Data-size probe, once, around loop 3: train the best config on 25%, 50% and 100% of train in one job (one row, change `probe:data-size`). Still climbing at 100% → data levers (item 4) are worth their time; flat → skip them and focus on model and inference.

Stuck rule: 3 loops in a row with `kept: no` → the next loop must be a new base model or a data change, not another hyperparameter. The same change crashed twice → status `crashed`, skip that lever.

Parallel mode: if `max_parallel_jobs` ≥ 2 and budget is left, launch a second single-change run from this session (own `exp/NNN/` and row); the budget check counts both. Default `max_parallel_jobs: 1`. For small models two cheaper GPUs usually beat one big one; compare GPUs by smoke-test seconds per step × price per hour.

Leaderboard rule: the public LB is often a small slice of test. Never tune toward it; when choosing finals prefer models good on both val and LB. If the rules say the public LB uses under ~30% of test, trust val even more.

## Block 5 — Final run (20:00–22:00)

No untested ideas.

1. A loop row still `running`: let it finish if its ETA is before stop-loops + 1h (default 21:00) and treat it as a normal loop (Block 4 steps 6–8); otherwise stop it and mark it `cancelled`.
2. Decide the final model on val, before any retraining: the best kept row, or the average of the top two or three kept models' predictions if they are different kinds, within noise of each other, and the average scores ≥ the best single model on val (probabilities or numbers only; rank-average for ranking metrics like AUC; for generated text keep the single best, or the card's merge option). Apply the best `postproc` row's settings on top.
   Seed averaging: if time and budget allow, the final retrain uses the chosen config with 2–3 seeds and averages their predictions.
3. Add the `FINAL` row with status `running`. If the rules allow, ETA (train + predict) × 1.3 ends before verify (default 22:00), and it passes the Block 4 budget check, retrain the chosen model(s) on train+val with the best run's epoch count; otherwise use the kept checkpoints as they are. If the `FINAL` row is `crashed`, do not retrain again: add a new `FINAL` row that uses the kept checkpoints as they are. If the `FINAL` row is already `running`, check its job instead of launching again.
4. Predict, check, submit as `submissions/NNN_FINAL.<ext>`; set the `FINAL` row to `done` and fill its `submission` cell.

## Block 6 — Verify & final submit (22:00–23:00)

1. If the `FINAL` row is still `running`: wait if its ETA is before verify + 30 min (default 22:30), then do Block 5 step 4; else stop it, mark it `cancelled`, and pick from the files already submitted.
2. `data:validate-data` on the final predictions: ranges match the train target, class distribution close to train, not constant, IDs right. The FINAL row's val = the chosen row's val (it trained on val); check that FINAL test predictions agree closely with the chosen row's.
3. `check_submission.py` → `OK` (`superpowers:verification-before-completion`: claim valid only after it passes).
4. Pick the final submission(s): good on both val and LB. If `final_pick` is "user selects N" and N ≥ 2: one safe pick (the best single model by val) and one aggressive pick (the best ensemble or FINAL), so a leaderboard reshuffle cannot sink both.
5. Per `final_pick`: "last" → the pick must be the last file submitted; resubmit it only if a later file exists. "user selects N" → `PushNotification` the file names and ask the user to select them on the site (never click it yourself). "best" → nothing to submit. Then write `final_submission: <file>` in `brief.md`; `PushNotification` the pick and the reason. The user may override until the final deadline.
6. In `/loop` mode, stop the loop.

## Block 7 — Buffer (23:00–24:00)

Nothing new. Re-submit only if the final submission was rejected. In `/loop` mode, stop the loop.

## Running training

- Organizer or own GPU: Bash with `run_in_background: true`, `python train.py ... 2>&1 | tee exp/NNN/train.log`; you are woken when it exits. To watch progress: `Monitor` on `tail -f exp/NNN/train.log | grep -E --line-buffered "VAL_SCORE|EPOCH_SCORE|Traceback|Error|OOM|Killed|nan"` (expires after 30 min; re-arm).
- Hugging Face Jobs (hf-cli skill): always pass `--timeout` = 2 × ETA (the default 30 min kills the run) and `--detach`. Dependencies go in the job (uv script header / `--with`), not Block 1's pip. The job must write its checkpoint, log and test predictions to a read-write volume or push them to `hf_checkpoint_repo`; the container is deleted when the job ends. Record the job id in the row, poll `hf jobs inspect` in a background until-loop, and fetch the logs and outputs when it ends.
- Remote GPU over SSH: `nohup python train.py ... > exp/NNN/train.log 2>&1 & echo $!` on that machine; write host:PID in the row.
- Alive check: HF Jobs → `hf jobs inspect <id>`; PID → `ps -p <PID>`. A `running` row with no job id or PID, or whose job is gone without `VAL_SCORE` in its log, is `crashed`.
- When any paid run ends (done, crashed, cancelled, baseline or FINAL), add its actual cost to `cost so far`.
- If the `PushNotification` tool does not exist, put the message in your reply instead (Remote Control shows it on the phone).
- Always write the job id or log path in the row so a new session can find it.
- ETA = smoke-test seconds per step × total steps.
- Early kill: when a run prints its first `EPOCH_SCORE` and it is clearly below the best row's epoch-1 score (gap larger than ~2× the val noise), stop it, mark the row `killed-early`, and launch the next lever. Watch for `EPOCH_SCORE` in the Monitor filter.
- Crash: mark the row `crashed`, `PushNotification` `#NNN crashed: <one-line reason>`, apply the Runbook.

## Submitting

- Files are numbered `submissions/NNN_<name>.<ext>`; never overwrite or delete one.
- Always first: `python "<skill dir>/check_submission.py" <sample_submission> <file>` must print `OK`. Non-CSV submission format: extend `_read` in check_submission.py for it first (and add a self-test case).
- CLI or API (Kaggle: `kaggle competitions submit -c <slug> -f <file> -m "#NNN <change>"`, scores via `kaggle competitions submissions -c <slug>`): submit yourself only if `auto_submit: yes` in `brief.md`; otherwise use the web-upload flow below.
- Web upload form: never click the site's submit button. `PushNotification` "upload submissions/NNN_... (val X)" and ask the user to paste the LB score back; fill the `submission` cell when they confirm the upload.
- Update `subs used` in `experiments.md` after every submission.
- Whenever a row becomes the new best, copy its submission to `submissions/best.<ext>`. This is the only file that may be overwritten. Emergency submit, at any time and even at 23:55: `python "<skill dir>/check_submission.py" <sample_submission> submissions/best.<ext>`, then submit that file.

## Runbook (apply without asking in autonomous mode)

| Failure | Fix, in order |
|---|---|
| GPU out of memory | Halve batch + double accumulation → gradient checkpointing → 4-bit or the next smaller model |
| Loss NaN / diverges | lr ÷3–10 → bf16 instead of fp16 → check labels/data |
| Job interrupted (spot/preempted GPU) | Relaunch from the last saved checkpoint (`resume_from_checkpoint`) in the same row; counts as a crash only if it is interrupted twice |
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
rules_limits: TODO allowed models, external data allowed?, pseudo-labels on test allowed?, teacher/API models allowed?, retrain on train+val allowed?, share of test on the public LB
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
last_review:

| # | time | change | hypothesis | status | job / log | cost | val | LB | kept | submission |
|---|---|---|---|---|---|---|---|---|---|---|

## Lessons

## Strategy log

## Handoff
```

Best = the kept row with the best val (metric direction from `brief.md`).
