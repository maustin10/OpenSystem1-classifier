# Other zero-shot classifiers to benchmark

These models have not been run on the 12-question benchmark yet. They are suggested next experiments, not measured results.

## Recommended order

1. **DeBERTa-v3-large-zeroshot-v2.0**
   - Best apples-to-apples local comparison because it uses the same NLI formulation and comes from the same zero-shot model series as the ModernBERT checkpoint.
   - The model card reports higher average accuracy than ModernBERT on its published task set, with lower throughput and higher memory use.
   - Model: <https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0>

2. **BART-large-MNLI**
   - A widely used baseline for NLI-based zero-shot classification.
   - Useful as a compatibility and historical baseline, although it uses an older encoder-decoder architecture.
   - Model: <https://huggingface.co/facebook/bart-large-mnli>

3. **mDeBERTa-v3-base-MNLI-XNLI**
   - The most relevant addition when multilingual decisions matter.
   - Its model card lists support for 16 languages and provides the standard Transformers zero-shot pipeline.
   - Model: <https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli>

4. **GLiClass**
   - A different classifier design that scores labels in one forward path rather than running a cross-encoder pair for every option.
   - Worth testing when label count or latency makes NLI cross-encoding expensive.
   - Model: <https://huggingface.co/knowledgator/gliclass-small-v1.0>

## Evaluation fields

Record these fields for every candidate:

- Top-ranked accuracy
- Gate clearance at the same thresholds
- Expected calibration error or reliability curves on a larger dataset
- Accuracy by number of options
- CPU, CUDA, and Apple MPS latency
- Peak memory and checkpoint size
- Multilingual performance where relevant
- Model and training-data license constraints

