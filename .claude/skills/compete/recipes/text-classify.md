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
