# `/compete` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Tasks 4 and 5 must run in the main session** (they invoke the skill and use session-only tools); Tasks 1–3 can go to subagents.

**Goal:** Build the `/compete` project skill that drives a one-day fine-tuning competition (any modality) from setup to final submission, with autonomous improvement loops after the first submission.

**Architecture:** One project skill folder. `SKILL.md` holds the whole playbook (block detection from plain state files + clock, block checklists, loop, guardrails, runbook, skill map, templates). Five one-screen recipe cards hold per-modality defaults; Claude writes training scripts on the day from a card. The only code is `check_submission.py` (stdlib-only CSV format check with a built-in self-test). Autonomy reuses Claude Code's existing `/loop`.

**Tech Stack:** Markdown skill files; Python 3.13 stdlib (`check_submission.py`); rehearsal uses pandas, scikit-learn (installed), LightGBM and MLflow (installed in Task 4).

**Spec:** `docs/superpowers/specs/2026-11-23-compete-playbook-design.md`

## Global Constraints

- Skill path: `.claude/skills/compete/` in this repo; invoked as `/compete`; autonomous mode is `/loop /compete`.
- Day defaults: `start: 2026-11-28 09:00`, `end: 2026-11-28 24:00`. Deadlines are offsets from `start`: +3h30 first submission, +4h00 baseline hard rule, +11h00 final run, +13h00 verify & submit, +14h00 final submission deadline.
- No prep days for the user; no pre-written training scripts. `check_submission.py` is the only code.
- `check_submission.py`: Python stdlib only; CSV only (documented `shortcut:` comment).
- Never click a website's submit button; CLI/API submission only after the user says so in chat.
- Never edit the val split or test data; never delete experiments, checkpoints or submissions.
- Recipe cards: about one screen each (≤ ~70 lines), sections `## Use when`, `## Pick the model`, `## Starting hyperparameters`, `## Script outline`, `## Levers`, `## Crashes`.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Deviation from spec, on purpose: MLflow tracking URI is `sqlite:///mlflow.db` (works on MLflow 2.x and 3.x); artifacts still land in `mlruns/`.

## File structure

| File | Responsibility |
|---|---|
| `.claude/skills/compete/SKILL.md` | The playbook Claude follows on every `/compete` call |
| `.claude/skills/compete/check_submission.py` | Submission format check + `--self-test` |
| `.claude/skills/compete/recipes/llm.md` | Text generation (instruct model + QLoRA) |
| `.claude/skills/compete/recipes/text-classify.md` | Text classification / regression |
| `.claude/skills/compete/recipes/vision.md` | Images: classification, detection, segmentation |
| `.claude/skills/compete/recipes/audio.md` | ASR and audio classification |
| `.claude/skills/compete/recipes/tabular.md` | Tabular (LightGBM) |

Rehearsal files (fake competition) live in the session scratchpad and are **not** committed.

---

### Task 1: `check_submission.py` with self-test

**Files:**
- Create: `.claude/skills/compete/check_submission.py`

**Interfaces:**
- Produces: `check(sample_path: str, sub_path: str) -> list[str]` (empty list = valid).
- CLI: `python check_submission.py SAMPLE SUBMISSION` → prints `OK` and exits 0, or prints `INVALID:` followed by `- <problem>` lines and exits 1. `python check_submission.py --self-test` → prints `self-test passed (N cases)` and exits 0, or raises `AssertionError`.
- Assumes the first column is the ID column (documented shortcut).

- [ ] **Step 1: Write the self-test and a stub `check` that always says valid**

```python
#!/usr/bin/env python3
"""Check a competition submission CSV against the organizer's sample submission.

Usage:
  python check_submission.py SAMPLE SUBMISSION   -> "OK" (exit 0) or "INVALID:" + reasons (exit 1)
  python check_submission.py --self-test
"""
# shortcut: CSV only and the ID is the first column; extend if a competition uses JSON/JSONL/parquet or a different ID column.
import csv
import math
import os
import sys
import tempfile


def check(sample_path, sub_path):
    return []


def _write(folder, name, text):
    path = os.path.join(folder, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(text)
    return path


def self_test():
    num = "id,target\n1,0.5\n2,0.5\n3,0.5\n"
    lab = "id,label\n1,cat\n2,cat\n3,cat\n"
    cases = [
        ("good, rows reordered", num, "id,target\n3,0.1\n1,0.9\n2,0.4\n", True),
        ("good, BOM + CRLF", num, "﻿id,target\r\n1,0.1\r\n2,0.9\r\n3,0.4\r\n", True),
        ("good, text labels", lab, "id,label\n1,dog\n2,cat\n3,dog\n", True),
        ("wrong column name", num, "id,label\n1,0.1\n2,0.9\n3,0.4\n", False),
        ("columns swapped", num, "target,id\n0.1,1\n0.9,2\n0.4,3\n", False),
        ("missing row", num, "id,target\n1,0.1\n2,0.9\n", False),
        ("extra row", num, "id,target\n1,0.1\n2,0.9\n3,0.4\n4,0.2\n", False),
        ("unknown id", num, "id,target\n1,0.1\n2,0.9\n4,0.4\n", False),
        ("duplicate id", num, "id,target\n1,0.1\n1,0.9\n2,0.4\n", False),
        ("empty value", num, "id,target\n1,0.1\n2,\n3,0.4\n", False),
        ("nan value", num, "id,target\n1,0.1\n2,nan\n3,0.4\n", False),
        ("text in numeric column", num, "id,target\n1,0.1\n2,high\n3,0.4\n", False),
        ("short row", num, "id,target\n1,0.1\n2\n3,0.4\n", False),
        ("empty file", num, "", False),
        ("good, blank line ignored", num, "id,target\n1,0.1\n\n2,0.9\n3,0.4\n", True),
    ]
    with tempfile.TemporaryDirectory() as d:
        for i, (name, sample, sub, ok) in enumerate(cases):
            problems = check(_write(d, f"s{i}.csv", sample), _write(d, f"p{i}.csv", sub))
            assert (problems == []) == ok, f"{name}: expected {'valid' if ok else 'invalid'}, got {problems}"
    print(f"self-test passed ({len(cases)} cases)")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        sys.exit(0)
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    problems = check(sys.argv[1], sys.argv[2])
    if problems:
        print("INVALID:\n" + "\n".join(f"- {p}" for p in problems))
        sys.exit(1)
    print("OK")
```

- [ ] **Step 2: Run the self-test, confirm it fails**

Run: `python .claude/skills/compete/check_submission.py --self-test`
Expected: `AssertionError: wrong column name: expected invalid, got []`

- [ ] **Step 3: Implement `check`** (replace the stub)

```python
def _read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.reader(f) if r]
    return (rows[0], rows[1:]) if rows else ([], [])


def _is_number(value):
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def check(sample_path, sub_path):
    s_head, s_rows = _read(sample_path)
    head, rows = _read(sub_path)
    if not head:
        return ["submission is empty"]
    if head != s_head:
        return [f"columns {head} differ from sample columns {s_head} (names and order must match)"]
    problems = []
    if len(rows) != len(s_rows):
        problems.append(f"{len(rows)} rows, sample has {len(s_rows)}")
    ids = [r[0] for r in rows if r]
    if len(set(ids)) != len(ids):
        problems.append(f"{len(ids) - len(set(ids))} duplicate ids")
    s_ids = {r[0] for r in s_rows if r}
    missing, extra = s_ids - set(ids), set(ids) - s_ids
    if missing or extra:
        problems.append(f"id set differs from sample: {len(missing)} missing, {len(extra)} unknown (e.g. {sorted(missing or extra)[0]!r})")
    bad_len = [i for i, r in enumerate(rows, 2) if len(r) != len(head)]
    if bad_len:
        problems.append(f"{len(bad_len)} rows with wrong field count, first at line {bad_len[0]}")
    empty = [i for i, r in enumerate(rows, 2) if any(not v.strip() for v in r)]
    if empty:
        problems.append(f"{len(empty)} rows with empty values, first at line {empty[0]}")
    for j in range(1, len(head)):
        if s_rows and all(len(r) > j and _is_number(r[j]) for r in s_rows):
            bad = [r[j] for r in rows if len(r) > j and r[j].strip() and not _is_number(r[j])]
            if bad:
                problems.append(f"column {head[j]!r} must be a finite number, got e.g. {bad[0]!r}")
    return problems
```

- [ ] **Step 4: Run the self-test, confirm it passes**

Run: `python .claude/skills/compete/check_submission.py --self-test`
Expected: `self-test passed (15 cases)`

- [ ] **Step 5: Check the CLI exit codes by hand**

Run (Git Bash):
```bash
d=$(mktemp -d); printf 'id,target\n1,0.5\n2,0.5\n' > $d/s.csv; printf 'id,target\n2,0.3\n1,0.7\n' > $d/ok.csv; printf 'id,target\n1,0.3\n' > $d/bad.csv
python .claude/skills/compete/check_submission.py $d/s.csv $d/ok.csv; echo "exit=$?"
python .claude/skills/compete/check_submission.py $d/s.csv $d/bad.csv; echo "exit=$?"
```
Expected: `OK` / `exit=0`, then `INVALID:` with `- 1 rows, sample has 2` and `- id set differs ...` / `exit=1`.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/compete/check_submission.py
git commit -m "Add check_submission.py with self-test for /compete

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Recipe cards (5) + model-ID existence check

**Files:**
- Create: `.claude/skills/compete/recipes/llm.md`, `text-classify.md`, `vision.md`, `audio.md`, `tabular.md`

**Interfaces:**
- Produces: every card has the six headings `## Use when`, `## Pick the model`, `## Starting hyperparameters`, `## Script outline`, `## Levers`, `## Crashes`. `SKILL.md` (Task 3) refers to "the card's lever list" (`## Levers`) and "the card's smallest fallback model" (named in `## Pick the model`).

- [ ] **Step 1: Write `recipes/llm.md`**

````markdown
# Recipe: LLM text generation

## Use when
The output is generated text: answers, summaries, code, JSON extraction, chat replies, or the task says SFT / instruction tuning / preference tuning.

## Pick the model
- If the rules fix the base model, use it and skip the search.
- Otherwise spend ≤15 min: search "best open instruct model <size> <month year>" (Hugging Face trending, open leaderboards); check the license is allowed by the rules.
- Size by GPU memory (QLoRA 4-bit): 16 GB → ≤8B, 24 GB → ≤14B, 40–80 GB → ≤32B. On a one-day clock prefer ≤8B even on big GPUs: more loops beat a bigger model.
- Smallest fallback (smoke tests, tiny GPU, hard-rule rescue): `Qwen/Qwen2.5-1.5B-Instruct`. Solid default if search finds nothing better: `Qwen/Qwen2.5-7B-Instruct`.

## Starting hyperparameters
- QLoRA: 4-bit nf4, compute dtype bf16 (fp16 on T4/V100).
- LoRA: r=16, alpha=32, dropout=0.05, target_modules="all-linear".
- lr 2e-4, cosine schedule, warmup_ratio 0.03; epochs 2 (1 if >50k examples).
- max_seq_length = 95th percentile of tokenized train lengths, capped at 2048.
- per-device batch 2–4 (16 GB: 1–2), gradient accumulation so the effective batch ≈ 16; gradient_checkpointing on; packing off for the baseline.

## Script outline
- TRL `SFTTrainer` with the model's own chat template (`tokenizer.apply_chat_template`); train on the completion/assistant tokens only (check the current TRL docs for the flag name).
- Inference: vLLM if installed, else batched HF `generate`; greedy decoding (temperature 0); max_new_tokens ≈ longest train answer × 1.2.
- Score val generations with the competition metric. LLM-judge or fuzzy metrics: build a local scorer with `mlflow:build-a-scorer`.
- Preference pairs given → DPO on top of the SFT model; verifiable reward given → GRPO. Always get the SFT baseline submitted first.

## Levers
1. Identical prompt/chat template in training and inference (the most common silent bug).
2. lr 1e-4 / 2e-4 / 5e-4 and epochs 1–3.
3. Bigger or newer base model.
4. Data: dedupe, drop broken or very long outliers, add similar public data if allowed.
5. LoRA r 16 → 64.
6. Decoding and post-processing: strip whitespace, parse JSON, regex out the final answer, few-shot prompt at inference.
7. DPO on top of SFT if preference pairs exist.

## Crashes
- OOM → batch 1 + more accumulation → lower max_seq_length → smaller model.
- Loss NaN → lr ÷3; bf16 instead of fp16 on Ampere or newer GPUs.
- Repetitive or garbage output → wrong chat template, or EOS token missing from training targets.
- "pad token" error → `tokenizer.pad_token = tokenizer.eos_token`.
- bitsandbytes / CUDA error → `pip install -U bitsandbytes`; without an NVIDIA GPU skip 4-bit and use a smaller model.
- Very slow → packing on, shorter max_seq_length, vLLM for inference.
````

- [ ] **Step 2: Write `recipes/text-classify.md`**

````markdown
# Recipe: text classification / regression

## Use when
Input is text; output is a label, several labels, a score (regression) or per-token tags (NER).

## Pick the model
- Default (English): `microsoft/deberta-v3-base`.
- Long texts (>512 tokens) or need speed: `answerdotai/ModernBERT-base`.
- Multilingual: `FacebookAI/xlm-roberta-base`.
- `-large` variants are a lever, not the baseline. Smallest fallback: the `-base` model with max_length 128.
- If labels need multi-step reasoning or are free text, use `llm.md` instead.

## Starting hyperparameters
- lr 2e-5 (base) / 1e-5 (large); batch 16–32; epochs 3; warmup_ratio 0.1; weight_decay 0.01.
- max_length 256; raise to 512 if more than 10% of texts get truncated.
- bf16 if supported; DeBERTa-v3 can produce NaN in fp16 → use bf16 or fp32.
- Evaluate every epoch; keep the best checkpoint by the competition metric.

## Script outline
- `AutoModelForSequenceClassification`: `num_labels=K`; multi-label → `problem_type="multi_label_classification"`; regression → `num_labels=1`. NER → `AutoModelForTokenClassification`.
- HF `Trainer` with `compute_metrics` = the competition metric.
- Predict probabilities/scores on test, then map to the submission format.

## Levers
1. Truncation: keep head + tail of long documents; check label mapping (id ↔ label).
2. lr 1e-5 / 2e-5 / 3e-5 and epochs 2–5.
3. `-large` model.
4. Class weights or decision-threshold tuning for F1-type metrics.
5. 5-fold CV, average fold predictions (late, if time).
6. Pseudo-labels on test (only if the rules allow).
7. Ensemble DeBERTa + ModernBERT.

## Crashes
- OOM → batch 8 + accumulation → lower max_length → gradient checkpointing.
- NaN loss → bf16/fp32 instead of fp16; lr ÷2.
- Predicts only the majority class → lr too high or too low, labels mis-mapped; print the prediction distribution.
- Tokenizer error for DeBERTa-v3 → `pip install sentencepiece`.
````

- [ ] **Step 3: Write `recipes/vision.md`**

````markdown
# Recipe: images (classification, detection, segmentation)

## Use when
Inputs are images; output is a class, several labels, boxes (detection) or masks (segmentation).

## Pick the model
- Classification default: timm `convnext_tiny.fb_in22k_ft_in1k` (Hub: `timm/convnext_tiny.fb_in22k_ft_in1k`). Bigger lever: `timm/convnext_base.fb_in22k_ft_in1k`.
- Very little data (<1k images): frozen `facebook/dinov2-base` features + a linear head.
- Detection: `PekingU/rtdetr_r50vd` (transformers). YOLO-family only if its license (AGPL) is allowed by the rules.
- Segmentation: `nvidia/segformer-b0-finetuned-ade-512-512`.
- Smallest fallback: convnext_tiny at image size 160, head-only training.

## Starting hyperparameters
- Classification: image size 224; AdamW lr 1e-4 full fine-tune (1e-3 head-only), weight_decay 0.05; batch 32–64; 10–20 epochs, cosine, keep best epoch by val metric; mixed precision.
- Augmentation: RandomResizedCrop + horizontal flip (no flip if orientation matters: text, digits, medical laterality).
- Detection: image size 640, lr 1e-4 (backbone 1e-5), 30–50 epochs.

## Script outline
- `timm.create_model(name, pretrained=True, num_classes=K)`; normalization from `timm.data.resolve_data_config`; torchvision transforms; plain PyTorch loop or HF `Trainer`.
- Images: `Image.open(p).convert("RGB")`.
- Predict probabilities on test; average over TTA views if used.

## Levers
1. Check labels ↔ images alignment, correct normalization and resize.
2. lr and epochs.
3. Higher resolution 224 → 384.
4. Bigger backbone.
5. Stronger augmentation (RandAugment, mixup/cutmix) when train ≫ val score.
6. TTA: average original + flipped predictions.
7. Ensemble two backbones.

## Crashes
- OOM → smaller batch → smaller images → AMP + `channels_last`.
- Slow data loading → `num_workers` 4–8; pre-resize all images once into `data/derived/`.
- Val great, LB bad → leakage (same object/patient/source in train and val) → group split.
- Wrong channel count → `.convert("RGB")`.
````

- [ ] **Step 4: Write `recipes/audio.md`**

````markdown
# Recipe: audio (speech recognition, audio classification)

## Use when
Inputs are audio; output is a transcript (ASR) or a label (audio classification).

## Pick the model
- ASR default: `openai/whisper-small`. Levers: `openai/whisper-medium`, `openai/whisper-large-v3-turbo`.
- Audio classification default: `MIT/ast-finetuned-audioset-10-10-0.4593`. Speech-like classes (speaker, emotion, keyword): `facebook/wav2vec2-base`.
- Smallest fallback: `openai/whisper-small` with max_steps cut in half.

## Starting hyperparameters
- All audio resampled to 16 kHz mono.
- ASR: lr 1e-5, warmup 10% of steps, batch 16 (use accumulation), ≈3 epochs as max_steps, bf16/fp16, gradient checkpointing, `predict_with_generate=True`, generation_max_length 225.
- Classification: lr 3e-5, batch 16, 5–10 epochs, clips cut or padded to 10 s.

## Script outline
- ASR: `WhisperProcessor` + `WhisperForConditionalGeneration`, `Seq2SeqTrainer`, a padding data collator, WER/CER via `evaluate` (needs `jiwer`). Set language and task on the processor/generation config.
- Classification: `AutoFeatureExtractor` + `AutoModelForAudioClassification`, `Trainer`.
- Normalize text the same way the metric does (case, punctuation) before scoring val.

## Levers
1. 16 kHz audio, correct language/task tokens, text normalization matching the metric.
2. lr and number of steps.
3. Bigger Whisper.
4. Augmentation for small data: speed perturbation, added noise.
5. Decoding: beam search `num_beams=5`.
6. Long audio: 30 s chunking with overlap.
7. Ensemble (classification only).

## Crashes
- OOM → smaller batch → gradient checkpointing → whisper-small.
- Hallucinated or repeated text → set language and task explicitly, `no_repeat_ngram_size=3`, no timestamps.
- Cannot load audio → `pip install soundfile librosa`; mp3/m4a needs ffmpeg.
````

- [ ] **Step 5: Write `recipes/tabular.md`**

````markdown
# Recipe: tabular

## Use when
Data is rows and columns (CSV/parquet) of numbers and categories; target is a class or a number. No neural fine-tuning: gradient boosting wins here.

## Pick the model
- Default: LightGBM.
- Many categorical columns: CatBoost. Ensemble partner: XGBoost.
- Smallest fallback: LightGBM with defaults and 500 trees.

## Starting hyperparameters
- objective from the task: `binary` / `multiclass` / `regression` (match the metric, e.g. `regression_l1` for MAE).
- learning_rate 0.05, num_leaves 31, min_child_samples 20, feature_fraction 0.8, bagging_fraction 0.8, bagging_freq 1.
- n_estimators 5000 with early stopping (100 rounds) on the validation fold.
- Categorical columns as pandas `category` dtype, with the same categories in train and test.

## Script outline
- 5-fold CV (StratifiedKFold for classification, GroupKFold if an entity repeats, time split if test is later). Fold ids saved once to `data/folds.csv` (seed 42) and frozen: this is the val split.
- Out-of-fold score = val score. Test prediction = average of the 5 fold models.

## Levers
1. Drop ID and leaky columns; correct dtypes.
2. learning_rate 0.02 with more trees.
3. Feature engineering: ratios, date parts, group aggregates, count encoding.
4. Class weights or threshold tuning for the metric.
5. Tune num_leaves and min_child_samples.
6. CatBoost / XGBoost and average with LightGBM.
7. Average 3 seeds.

## Crashes
- Category mismatch between train and test → build categories from train+test, `pd.Categorical(..., categories=...)`.
- Val ≫ LB → leakage; switch to group or time split.
- Out of memory → downcast float64 → float32.
````

- [ ] **Step 6: Verify every card has the six headings**

Run:
```bash
for f in .claude/skills/compete/recipes/*.md; do n=$(grep -cE '^## (Use when|Pick the model|Starting hyperparameters|Script outline|Levers|Crashes)$' "$f"); echo "$n $f"; done
```
Expected: `6` for each of the five files.

- [ ] **Step 7: Verify every named model exists on the Hugging Face Hub**

Run:
```bash
for id in Qwen/Qwen2.5-1.5B-Instruct Qwen/Qwen2.5-7B-Instruct microsoft/deberta-v3-base answerdotai/ModernBERT-base FacebookAI/xlm-roberta-base timm/convnext_tiny.fb_in22k_ft_in1k timm/convnext_base.fb_in22k_ft_in1k facebook/dinov2-base PekingU/rtdetr_r50vd nvidia/segformer-b0-finetuned-ade-512-512 openai/whisper-small openai/whisper-medium openai/whisper-large-v3-turbo MIT/ast-finetuned-audioset-10-10-0.4593 facebook/wav2vec2-base; do echo "$(curl -s -o /dev/null -w '%{http_code}' https://huggingface.co/api/models/$id) $id"; done
```
Expected: `200` for every id. For any non-200, find the closest existing id (Hub search), replace it in the card, and re-run.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/compete/recipes/
git commit -m "Add /compete recipe cards for LLM, text, vision, audio, tabular

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `SKILL.md`

**Files:**
- Create: `.claude/skills/compete/SKILL.md`

**Interfaces:**
- Consumes: `check_submission.py` CLI (Task 1); recipe card headings `## Levers` and `## Pick the model` (Task 2).
- Produces: state file formats used by Task 4: `brief.md` (fields `start`, `end`, Rules fields with `TODO`, `card:`, `val_split:`, `final_submission:`), `experiments.md` (table columns `# | time | change | hypothesis | status | job / log | val | LB | kept | submission`), `submissions/NNN_<name>.<ext>`.

- [ ] **Step 1: Write `SKILL.md`**

````markdown
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
````

- [ ] **Step 2: Verify frontmatter and required sections**

Run:
```bash
f=.claude/skills/compete/SKILL.md
head -4 "$f" | grep -c '^name: compete$'
grep -cE '^## Block [1-7] ' "$f"
grep -cE '^## (Every call, in this order|Clock|Which block am I in \(first match wins\)|Running training|Submitting|Runbook \(apply without asking in autonomous mode\)|Skill map|Templates)$' "$f"
grep -c 'check_submission.py' "$f"
```
Expected: `1`, `7`, `8`, and a number ≥ 3.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/compete/SKILL.md
git commit -m "Add /compete SKILL.md playbook

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: CPU rehearsal on a fake tabular competition (main session)

**Files:**
- Modify (only if friction is found): `.claude/skills/compete/SKILL.md`, `.claude/skills/compete/recipes/tabular.md`
- Rehearsal folder (not committed): `<scratchpad>/rehearsal/`

**Interfaces:**
- Consumes: everything from Tasks 1–3.

Placeholders in this task: `<repo>` = this worktree's absolute path; `<scratchpad>` = the session's scratchpad directory (absolute path from the session environment).

- [ ] **Step 1: Install rehearsal dependencies**

Run: `python -m pip install lightgbm mlflow`
Expected: both import: `python -c "import lightgbm, mlflow; print('ok')"` → `ok`.

- [ ] **Step 2: Build the fake competition**

In `<scratchpad>/rehearsal/` create `make_fake_comp.py`:

```python
import os
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split

os.makedirs("data", exist_ok=True)
X, y = load_breast_cancer(return_X_y=True, as_frame=True)
df = X.rename(columns=lambda c: c.replace(" ", "_"))
df.insert(0, "id", range(1, len(df) + 1))
df["target"] = y
train, test = train_test_split(df, test_size=0.3, random_state=0, stratify=df["target"])
train.to_csv("data/train.csv", index=False)
test.drop(columns="target").to_csv("data/test.csv", index=False)
test[["id"]].assign(target=0.5).to_csv("data/sample_submission.csv", index=False)
test[["id", "target"]].to_csv("_answers.csv", index=False)
```

and `score.py` (the fake leaderboard):

```python
import sys
import pandas as pd
from sklearn.metrics import roc_auc_score

answers = pd.read_csv("_answers.csv")
sub = pd.read_csv(sys.argv[1])
merged = answers.merge(sub, on="id", suffixes=("", "_pred"))
print(f"LB AUC = {roc_auc_score(merged['target'], merged['target_pred']):.5f}")
```

Run: `cd <scratchpad>/rehearsal && python make_fake_comp.py && ls data`
Expected: `sample_submission.csv  test.csv  train.csv`

- [ ] **Step 3: Run the guided phase with `/compete`**

Invoke the `compete` skill (Skill tool; if it is not listed yet, read `.claude/skills/compete/SKILL.md` and follow it) with the competition folder `<scratchpad>/rehearsal`. Give these rules when Block 1 asks:
- competition: rehearsal; task: tabular binary classification of `target`; metric: ROC AUC, higher is better
- submission_method: `cli: python score.py <file>`; submission_cap: none
- compute: local CPU; budget_cap: 0, max_parallel_jobs 1; hf_checkpoint_repo: none (skip pushes)
- `start` = now (rounded down to the minute), `end` = start + 15h

Skip Block 1 steps 3–6 (no GPU, no HF, no Remote Control; reminders are tested in Task 5) and note any step that was confusing.

Expected after Blocks 1–3:
- `brief.md` has no `TODO`; `card: tabular.md`; `val_split: data/folds.csv` (or `data/val_ids.csv`).
- `experiments.md` row `001` with val AUC, LB AUC from `score.py`, `kept: yes`, `submissions/001_baseline.csv`.
- `check_submission.py data/sample_submission.csv submissions/001_baseline.csv` → `OK`.
- `mlflow.db` exists.
- Every reply ends with the status line.

- [ ] **Step 4: Run one improvement loop**

Invoke `/compete` again (Block 4). Expected: row `002` with one change, a hypothesis, val, LB, `kept` yes/no, `submissions/002_*.csv` that passed the check, and a status line.

- [ ] **Step 5: Format check rejects a broken file**

Run:
```bash
cd <scratchpad>/rehearsal
head -n 50 submissions/001_baseline.csv > broken.csv
python "<repo>/.claude/skills/compete/check_submission.py" data/sample_submission.csv broken.csv; echo "exit=$?"
```
Expected: `INVALID:` with a row-count problem, `exit=1`.

- [ ] **Step 6: Resume test from state files**

Dispatch a fresh `Explore` subagent with: "Read `<repo>/.claude/skills/compete/SKILL.md`. Using only its rules and the files in `<scratchpad>/rehearsal`, report which block the competition is in and the exact next step. Do not change any file. Under 100 words."
Expected: Block 4, next loop (row `003`).

- [ ] **Step 7: Fix friction**

For every confusing step, wrong block detection or missing instruction found in Steps 3–6, make the smallest edit to `SKILL.md` or `recipes/tabular.md`, then re-run the affected step.

- [ ] **Step 8: Commit (only if Step 7 changed files)**

```bash
git add .claude/skills/compete/
git commit -m "Fix /compete friction found in CPU rehearsal

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Check that `CronCreate` reminders fire in-session (main session)

**Files:**
- Modify (only if reminders do not fire): `.claude/skills/compete/SKILL.md` (Block 1 step 6)

- [ ] **Step 1: Schedule a one-shot reminder 3 minutes ahead**

Call `CronCreate` with `cron` = `<minute+3> <hour> <today_dom> <today_month> *`, `recurring: false`, `prompt: "[compete] reminder test - reply 'cron ok' with the time"`. Note the next run time from the result. End the turn and stay idle.

- [ ] **Step 2: Record the result**

Expected: the prompt arrives within a few minutes of the reported time; reply `cron ok HH:MM`.
If nothing arrives within 10 minutes of the reported time: delete Block 1 step 6 from `SKILL.md` and add to "Every call" step 5: "The status line is the only reminder; check it every step."

- [ ] **Step 3: Commit (only if Step 2 changed `SKILL.md`)**

```bash
git add .claude/skills/compete/SKILL.md
git commit -m "Drop CronCreate reminders from /compete; status line is the reminder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Spec coverage

| Spec section | Task |
|---|---|
| §2 Deliverable, one command, `/loop /compete` | 3 |
| §2 Recipe cards | 2 |
| §3 Day state files | 3 (templates), 4 (rehearsal) |
| §4 Timeline, hard rules, guided → autonomous | 3 |
| §5 Loop, lever list, LB rule, parallel mode | 3 |
| §6 Guardrails (budget, cap, untouchables, clock, stuck, submitting, notifications, keep-awake) | 3 |
| §7 Skill map | 3 |
| §8 Runbook, checkpoint push, numbered submissions | 3 |
| §9 `check_submission.py` | 1 |
| §10 Testing: self-test, CPU rehearsal, CronCreate check | 1, 4, 5 |
| §10 Not tested: GPU cards end to end | stated risk, no task |
