# Fine-Tuning Challenge Playbook

A practical collection of techniques for improving LLM fine-tuning results in a competition or benchmark challenge.

## 1. Core strategy

The most reliable path to a high score is not a single exotic algorithm. It is a closed loop:

1. Build a leakage-free evaluation harness.
2. Train a clean SFT baseline.
3. Analyze failures.
4. Create targeted data or preference pairs.
5. Retrain and select checkpoints using the real metric.
6. Improve inference with verification, selection, and repair.
7. Repeat.

Prioritize, in order:

1. Data quality and evaluation alignment.
2. LoRA/DoRA supervised fine-tuning.
3. Checkpoint selection and early stopping.
4. Verifier-guided rejection sampling.
5. Preference optimization.
6. Inference-time ensembling and self-consistency.
7. Model merging and robustness techniques.

## 2. Essential papers

| Priority | Paper | Why it matters |
|---|---|---|
| 1 | LoRA: Low-Rank Adaptation of Large Language Models | The default parameter-efficient fine-tuning method; freezes base weights and trains low-rank adapters. |
| 2 | QLoRA: Efficient Finetuning of Quantized LLMs | Enables fine-tuning with reduced GPU memory through quantization plus LoRA. |
| 3 | LIMA: Less Is More for Alignment | Shows the value of small, diverse, high-quality instruction data. |
| 4 | Direct Preference Optimization (DPO) | A practical alternative to RLHF for preference-based alignment. |
| 5 | FLAN / Finetuned Language Models are Zero-Shot Learners | Explains why instruction diversity improves generalization. |
| 6 | InstructGPT | Establishes the SFT, reward model, and RLHF alignment workflow. |
| 7 | DoRA: Weight-Decomposed Low-Rank Adaptation | A stronger LoRA variant that separates magnitude and direction. |
| 8 | NEFTune | Adds embedding noise during instruction fine-tuning; cheap and often useful. |
| 9 | RAFT: Reward rAnked FineTuning | A simple generate, rank, filter, and fine-tune alignment loop. |
| 10 | Self-Consistency Improves Chain of Thought Reasoning | A training-free inference method for reasoning tasks. |
| 11 | Model Soups | Averaging weights from multiple fine-tuned models can improve robustness and accuracy. |
| 12 | Editing Models with Task Arithmetic | Task vectors can be added, scaled, or combined for multi-task adaptation. |
| 13 | V-STaR | Trains a verifier alongside a self-improving reasoner. |
| 14 | Editing Models by Standard Fine-Tuning | Shows that conditional-likelihood training can improve targeted model editing. |

## 3. Data engineering

### 3.1 Build a clean dataset

- Remove exact and near-duplicate examples.
- Normalize whitespace, punctuation, casing, units, code formatting, and answer formats.
- Check every label manually or with a reliable verifier.
- Remove examples with ambiguous ground truth.
- Remove examples that leak the answer in the prompt.
- Remove contradictory instructions and malformed examples.
- Keep a small manually reviewed golden set for final checks.

### 3.2 Match the evaluation format

Train on examples that resemble the hidden test set:

- Same system prompt and user-message structure.
- Same role labels and delimiters.
- Same output schema.
- Similar input lengths.
- Similar task phrasing.
- Same expected answer format.
- Same constraints and refusal behavior.

If the scorer parses a final answer, teach a stable format such as:

```text
Reasoning: ...
FINAL_ANSWER: <answer>
```

### 3.3 Prioritize diversity

Include:

- Easy, medium, and hard examples.
- Multiple phrasings of the same task.
- Different input lengths.
- Different domains and edge cases.
- Correct and incorrect-looking distractors where appropriate.
- Rare categories.
- Long-context examples if relevant.
- Examples requiring refusal or clarification.

A small, diverse, high-quality dataset often outperforms a large noisy one. LIMA is the key reference for this principle.

### 3.4 Create targeted repair data

Instead of adding random data:

1. Run the current best model on validation data.
2. Cluster failures by type: format, reasoning, hallucination, missing constraint, off-topic response.
3. Create examples that target the largest failure cluster.
4. Add corrected demonstrations, preference pairs, or verifier-approved outputs.
5. Retrain and measure both the failure slice and the overall metric.

### 3.5 Synthetic data rules

Synthetic data is useful only when it is:

- Generated from realistic task distributions.
- Automatically verified or manually reviewed.
- Diverse in difficulty and phrasing.
- Balanced across classes and answer types.
- Free of leakage from validation or test data.

Avoid generating thousands of near-identical examples. A few hundred diverse, verified examples can be more valuable than a large repetitive corpus.

## 4. Supervised fine-tuning

### 4.1 Baseline setup

Start with a simple, reproducible baseline:

- Base model with few-shot prompting.
- LoRA SFT.
- QLoRA SFT if GPU memory is limited.
- Full SFT only if compute and data volume justify it.

### 4.2 Loss masking

Do not always compute loss over the full sequence. Mask the prompt and emphasize the scored output.

| Task | What to mask or emphasize |
|---|---|
| Math | Final answer, units, and critical reasoning steps |
| Code | Code tokens and executable solution |
| JSON extraction | Keys, values, delimiters, and schema-critical fields |
| Classification | Label token or label field |
| QA with citations | Evidence spans and final answer |
| Chat | Response tokens and instruction-compliance phrases |

For example, if the metric reads only the final answer, assign higher loss weight to:

```text
FINAL_ANSWER: 42
```

than to the preceding explanation.

### 4.3 Conditional-likelihood training

For knowledge injection or targeted correction, optimize only the conditional likelihood of the desired response or fact span.

Benefits:

- Reduces wasted capacity on prompt imitation.
- Makes targeted edits more local.
- Helps preserve unrelated model behavior.

Add paraphrases of the same fact and a few unrelated examples to improve generalization and reduce collateral damage.

## 5. LoRA and adapter methods

### 5.1 LoRA

LoRA is the practical default for most challenges.

Starting settings:

- Rank: 16
- Alpha: 32
- Dropout: 0.05 to 0.10
- Learning rate: 1e-4 to 2e-4
- Epochs: 1 to 3
- Effective batch size: 16 to 64

Suggested sweep:

- Rank: 8, 16, 32, 64
- Learning rate: 5e-5, 1e-4, 2e-4, 5e-4
- Epochs: 1, 2, 3
- Target modules: attention-only versus attention plus MLP

### 5.2 Target modules

Do not limit adapters to query projections. A stronger default is:

- q_proj
- k_proj
- v_proj
- o_proj
- gate_proj
- up_proj
- down_proj

If compute is tight, begin with attention projections. If quality plateaus, add MLP projections.

### 5.3 DoRA

DoRA decomposes pretrained weights into magnitude and direction, applying LoRA to the directional component. It aims to approximate full fine-tuning more closely while retaining parameter efficiency.

Test DoRA using the same data, rank, learning-rate sweep, and evaluation protocol as LoRA.

### 5.4 QLoRA

Use QLoRA when GPU memory is the main constraint. It combines quantization with LoRA adapters.

Compare it against bf16 LoRA if memory permits. Do not assume QLoRA is always better; it is a memory-efficiency method, not automatically a quality improvement.

### 5.5 Adapter routing

Train separate adapters for distinct subtasks:

- Domain adapter: legal, medical, finance, code, etc.
- Format adapter: JSON, Markdown, strict answer format.
- Difficulty adapter: easy factual tasks versus complex reasoning.
- Language adapter: if multiple languages are involved.
- Safety adapter: if refusal behavior is scored.

Route using:

- A lightweight classifier.
- Prompt embeddings.
- Task metadata.
- A first-pass model output.
- Rule-based detection.

## 6. Hyperparameters

Change one variable at a time.

| Setting | Starting point | Adjustment |
|---|---:|---|
| Learning rate | 1e-4 to 2e-4 for LoRA | Lower if unstable or overfitting; raise if underfitting |
| Epochs | 1 to 3 | Increase only if validation improves |
| Effective batch size | 16 to 64 | Use gradient accumulation if memory-limited |
| Sequence length | As long as necessary | Avoid unnecessary padding |
| Warmup | 3 to 10 percent of steps | Increase if early training is unstable |
| Weight decay | 0 or 0.01 | Test after core settings are stable |
| LoRA rank | 16 | Increase if underfitting; decrease if overfitting |
| LoRA alpha | 1 to 2 times rank | Keep ratio fixed while sweeping rank |

### 6.1 Learning rate

The learning rate is usually the most important hyperparameter.

- If loss decreases but validation performance is poor, lower it or reduce epochs.
- If loss barely moves, increase it or add more target modules.
- If loss spikes or outputs degrade, lower it.
- Use cosine or linear decay.
- Use warmup for stability.

### 6.2 Epochs and overfitting

Small datasets overfit quickly.

- Save checkpoints frequently.
- Evaluate every checkpoint.
- Keep the best checkpoint, not necessarily the final one.
- Begin with 1 to 2 epochs for small datasets.
- Stop if validation loss rises while training loss falls.
- Reduce epochs if the model memorizes training answers.

### 6.3 Batch size and sequence length

- Use gradient accumulation to reach a stable effective batch size.
- Start with per-device batch size 1 to 8.
- Accumulate to an effective batch size of 16 to 64.
- Use packing or length-grouped batching when examples vary greatly in length.
- For DPO, smaller batches are often more stable.

## 7. Preventing regressions

### 7.1 Catastrophic forgetting

Narrow fine-tuning can damage general skills.

Mitigations:

- Use LoRA rather than full fine-tuning.
- Keep the learning rate conservative.
- Limit epochs.
- Mix in 10 to 30 percent general instruction data.
- Evaluate both the challenge metric and general capabilities.
- Keep the base model and adapters separate.

### 7.2 Regression suite

Evaluate:

- Challenge metric.
- Format compliance.
- JSON or code validity.
- Instruction following.
- General reasoning.
- Refusal and safety behavior, if relevant.
- Length and language constraints.
- Performance by input slice.

## 8. Evaluation harness

### 8.1 Build it before training

Create a local validation set that mirrors the hidden test distribution.

Include:

- Same prompt format.
- Same answer format.
- Same difficulty distribution.
- Same scoring logic.
- Same edge cases.
- Same output constraints.

### 8.2 Metrics to track

Track more than one metric:

- Primary challenge score.
- Format validity.
- Parse success rate.
- Exact match or task-specific metric.
- Calibration, if relevant.
- Latency and token cost.
- Performance by category.
- Performance by difficulty.
- Performance after repair.
- Performance after best-of-N.

### 8.3 Avoid leakage

- Never tune on the test set.
- Deduplicate across train and validation splits.
- Check semantic as well as exact duplication.
- Do not generate synthetic data from validation or test prompts.
- Use the public test set only for final confirmation.

## 9. Self-improvement loops

### 9.1 Rejection-sampling fine-tuning

RFT is one of the strongest upgrades for tasks with verifiable outputs.

1. Fine-tune an initial SFT model.
2. Generate multiple responses per prompt.
3. Keep responses that pass the verifier or match the reference answer.
4. Add successful responses to the SFT dataset.
5. Retrain.
6. Repeat.

Useful verifiers:

- Unit tests for code.
- Exact-match checkers for math.
- Schema validators for JSON.
- Retrieval-grounding checks.
- Rubric-based judge models.
- Human review for a small high-value subset.

### 9.2 STaR

STaR iteratively uses model-generated correct reasoning as training data.

Use it when:

- You have final answers but not reasoning traces.
- The task is multi-step reasoning.
- You can validate final answers automatically.
- You want the model to learn its own successful reasoning style.

Retain only correct, concise, non-degenerate reasoning.

### 9.3 V-STaR

V-STaR trains both a generator and a verifier using correct and incorrect generated solutions.

Use it when:

- Best-of-N inference is allowed.
- You can label generated solutions as correct or incorrect.
- You want a verifier to select among candidates at test time.

### 9.4 RAFT

RAFT is a practical generate, rank, filter, and fine-tune loop.

1. Generate multiple candidate outputs.
2. Score them with a reward model, verifier, or rubric.
3. Keep the highest-scoring outputs.
4. Fine-tune on the filtered outputs.
5. Repeat.

It is usually simpler and more stable than PPO-based RLHF.

## 10. Preference optimization

### 10.1 DPO

Use DPO after SFT when you have meaningful preference pairs.

Good pairs:

- Correct versus subtly incorrect answer.
- Concise versus bloated response.
- Correct format versus malformed output.
- Complete versus incomplete solution.
- Safe versus unsafe response.
- Compliant versus non-compliant response.

Tips:

- Start from an SFT checkpoint.
- Use a low learning rate.
- Keep prompt distribution consistent with SFT.
- Ensure preferred and rejected responses differ in meaningful quality.
- Avoid pairs that differ only in length.

### 10.2 KTO

KTO can use unary labels: desired or undesired. It is useful when you have labels but not paired responses.

### 10.3 ORPO

ORPO combines SFT and preference optimization in one stage and does not require a separate reference model.

### 10.4 SimPO

SimPO is a reference-free preference objective. Test it after DPO if DPO plateaus.

## 11. Model merging and robustness

### 11.1 Model soups

Train several good checkpoints with different:

- Random seeds.
- Learning rates.
- LoRA ranks.
- Data orders.
- Prompt formats.
- Data-mixture variations.

Then average their weights.

Uniform soup:

\[
W_{\text{soup}} = \frac{1}{n}\sum_{i=1}^{n}W_i
\]

### 11.2 Greedy soup

1. Rank checkpoints by validation score.
2. Start with the best checkpoint.
3. Add the next-best checkpoint only if the average improves validation.
4. Stop when adding another checkpoint hurts performance.

### 11.3 WiSE-FT interpolation

If fine-tuning overfits or hurts out-of-distribution performance, interpolate between base and fine-tuned weights:

\[
W_{\lambda} = \lambda W_{\text{base}} + (1-\lambda)W_{\text{fine-tuned}}
\]

Try:

- lambda = 0.1
- lambda = 0.2
- lambda = 0.3
- lambda = 0.5

### 11.4 Task arithmetic

Compute task vectors by subtracting base weights from fine-tuned weights:

\[
\tau = W_{\text{fine-tuned}} - W_{\text{base}}
\]

Then add, scale, or combine task vectors.

This is useful for:

- Multi-task adaptation.
- Domain adaptation.
- Reducing catastrophic forgetting.
- Combining specialized adapters.

## 12. Inference-time improvements

### 12.1 Best-of-N selection

Generate multiple candidates and select the best using a verifier.

Useful selectors:

- Unit tests.
- Exact-match checkers.
- Schema validators.
- Rule-based constraints.
- Verifier model.
- Judge model.
- Token probability or self-certainty.

### 12.2 Self-consistency

For discrete-answer reasoning tasks:

1. Generate several reasoning paths.
2. Extract final answers.
3. Normalize them.
4. Majority-vote the final answer.
5. Use verifier score to break ties.

### 12.3 Self-certainty selection

If no external verifier is available, rank candidates using the model's own confidence or consistency.

### 12.4 Constrained decoding

Use grammar-constrained decoding or structured-output modes when the output must be valid JSON, SQL, code, or regex-matched text.

Benefits:

- Prevents malformed outputs.
- Improves parse success.
- Reduces wasted retries.
- Improves score when format is scored.

### 12.5 Repair loop

When output fails validation:

1. Detect the failure.
2. Send the original output and error back to the model.
3. Ask for a minimal repair.
4. Validate again.
5. Submit only if repaired output passes.

Example:

```text
Your previous response failed validation:
Error: missing required field "answer".

Previous response:
<response>

Return only corrected JSON matching this schema:
<schema>
```

## 13. Prompt and inference tuning

| Setting | What to try |
|---|---|
| Temperature | 0 for deterministic tasks; 0.7 to 1.0 for sampling |
| Top-p | 0.9 to 1.0 for diversity; lower for strict formatting |
| Max tokens | High enough to avoid truncation |
| Stop sequences | Stop after final-answer marker |
| System prompt | Minimal versus detailed instructions |
| Few-shot examples | 0, 2, 4, and 8 examples |
| Repetition penalty | Use only if repetition hurts quality |
| Beam search | Test for constrained tasks |

## 14. Ensembling

### 14.1 Prompt ensembling

Run the same input through several prompt variants:

- Zero-shot concise prompt.
- Few-shot prompt.
- Chain-of-thought prompt.
- Strict-format prompt.
- Task-specific prompt.

Then vote or select among outputs.

### 14.2 Checkpoint ensembling

Run the same input through several strong checkpoints or adapters.

Selection methods:

- Majority vote.
- Verifier score.
- Average log probability.
- Format constraints.
- Judge model.

### 14.3 Adapter ensembling

Use multiple adapters and select dynamically by task type, domain, difficulty, or language.

## 15. Advanced but underused techniques

### 15.1 Answer-span loss weighting

Up-weight the tokens that directly determine the score.

Examples:

- Final numeric answer.
- JSON fields.
- Code syntax.
- Citations.
- Evidence spans.
- Critical constraints.

### 15.2 Negative examples

Add plausible but subtly wrong responses as rejected examples.

Examples:

- Off-by-one code error.
- Correct reasoning but wrong format.
- Correct facts but unsupported claim.
- Correct answer but violates a constraint.
- Correct style but misses an instruction.

### 15.3 Contrastive SFT

Include:

- Near-miss labels.
- Ambiguous cases with disambiguation rules.
- Cases where the correct behavior is refusal.
- Cases where the correct behavior is asking for clarification.

### 15.4 Curriculum learning

Train from easier or cleaner examples toward harder ones.

Options:

- Difficulty curriculum.
- Quality curriculum.
- Domain-focused final stage.
- Progressive context length.

### 15.5 Retrieval-aware SFT

Train the model to use retrieved context correctly:

- Quote or cite relevant passages.
- Say when information is absent.
- Ignore distractors.
- Handle conflicting evidence.
- Produce a final answer only after using context.

### 15.6 Calibration-aware training

If the challenge uses probabilities, rankings, confidence, or multiple choice:

- Evaluate calibration, not only accuracy.
- Use temperature scaling after fine-tuning.
- Track Brier score and expected calibration error.
- Train abstention if wrong answers are penalized.

### 15.7 Test-time adaptation

Adapt a small part of the model during inference.

Options:

- Entropy minimization.
- Test-time fine-tuning.
- Prompt-specific adaptation.
- Adapter-only updates.

Use very small learning rates and reset adapters between unrelated test batches. Validate carefully because entropy minimization can make a model confidently wrong.

### 15.8 Knowledge editing

Use conditional-likelihood fine-tuning to inject or correct specific facts.

Best practices:

- Train only on the relevant response span.
- Add paraphrases.
- Add unrelated facts to preserve locality.
- Evaluate side effects on unrelated questions.

## 16. Judge models

If using an LLM judge:

- Give it a precise rubric.
- Provide few-shot examples, including borderline cases.
- Ask for structured output.
- Separate reasoning from final verdict.
- Measure agreement with human labels.
- Use multiple judges or majority voting for close calls.

## 17. Recommended experiment queue

Run these after a stable LoRA SFT baseline:

1. Loss masking on the scored answer span.
2. Prompt-format augmentation.
3. NEFTune.
4. DoRA.
5. Checkpoint selection and early stopping.
6. Greedy checkpoint soup.
7. WiSE-FT interpolation.
8. Verifier-guided RFT.
9. DPO with hard negatives.
10. ORPO or KTO.
11. Best-of-N with verifier.
12. Self-consistency.
13. Adapter routing.
14. Retrieval-aware SFT.
15. Test-time adaptation, only if permitted.

## 18. Common mistakes

- Tuning on the test set.
- Using a validation set that does not match the hidden distribution.
- Selecting checkpoints by training loss.
- Training too many epochs.
- Using a learning rate that is too high.
- Ignoring output parsing.
- Training on duplicated or contaminated data.
- Adding random synthetic data without verification.
- Using obviously bad rejected responses in DPO.
- Assuming more LoRA rank is always better.
- Merging incompatible adapters.
- Optimizing for verbosity when the metric rewards concision.
- Trusting a small improvement without repeated runs.

## 19. Final recommended recipe

For most fine-tuning challenges:

1. Build a strict evaluation harness.
2. Create a clean, diverse, leakage-free SFT dataset.
3. Train a LoRA SFT baseline.
4. Sweep learning rate, epochs, rank, and target modules.
5. Select the best checkpoint by the real metric.
6. Add answer-span loss masking and prompt-format augmentation.
7. Test DoRA and NEFTune.
8. Build a verifier and run RFT on failure clusters.
9. Construct DPO preference pairs from real failures.
10. Use best-of-N, self-consistency, constrained decoding, and repair loops at inference.
11. Merge or ensemble only strong, compatible checkpoints.
12. Confirm the final configuration once on the public test set.
