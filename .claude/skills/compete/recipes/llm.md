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
