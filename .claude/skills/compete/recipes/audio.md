# Recipe: audio (speech recognition, audio classification)

## Use when
Inputs are audio; output is a transcript (ASR) or a label (audio classification).

## Pick the model
- If the rules fix the base model, use it. Otherwise spend ≤15 min on a day-of check: search the Hugging Face Hub and recent leaderboards for a newer model of the same kind and size; switch only if it fits the GPU, its license is allowed, and it loads with the installed libraries. Else use the defaults below.
- ASR default: `openai/whisper-small`. Levers: `openai/whisper-medium`, `openai/whisper-large-v3-turbo`.
- Audio classification default: `MIT/ast-finetuned-audioset-10-10-0.4593`. Speech-like classes (speaker, emotion, keyword): `facebook/wav2vec2-base`.
- Smallest fallback: `openai/whisper-small` with max_steps cut in half.

## Starting hyperparameters
- All audio resampled to 16 kHz mono.
- ASR: lr 1e-5, warmup 10% of steps, batch 16 (use accumulation), ≈3 epochs as max_steps, bf16/fp16, gradient checkpointing, `predict_with_generate=True`, generation_max_length 225.
- Classification: lr 3e-5, batch 16, 5–10 epochs, clips cut or padded to 10 s.
- Speed tips: resample and compute features once into `data/derived/`; sort by duration to cut padding; batched generation for ASR inference.

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
