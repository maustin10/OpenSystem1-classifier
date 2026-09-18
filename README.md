# OpenSystem1 Classifier

An experiment by **Mark Austin** comparing two non-generative, zero-shot ways to make typed decisions over structured state:

1. A local Natural Language Inference classifier using [ModernBERT-large-zeroshot-v2.0](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0).
2. The hosted [TypeSafe System One API](https://docs.typesafe.ai/api), using Jev.

Both implementations answer the same 12 multiple-choice questions. They return only declared options and probability distributions. Neither path generates an unrestricted answer.

## Benchmark result

| Measure | ModernBERT NLI | TypeSafe Jev 1.13.0 |
|---|---:|---:|
| Correct top-ranked answers | 12/12 | 12/12 |
| Cleared the shared decision gate | 5/12 | 12/12 |
| Accuracy | 100% | 100% |
| Gate clearance | 41.7% | 100% |

The shared gate requires a top probability of at least `0.65` and a top-two margin of at least `0.15`.

TypeSafe returned literal `1.0` / `0.0` probability distributions and `confidence: 1.0` for all 12 cases. The client did not round or threshold those responses. The POC calculates the top-two margin locally after receiving the API response. This easy benchmark demonstrates separation on gate clearance, but it does not establish real-world calibration.

The presentation is in [`results/OpenSystem1-classifier-comparison.pptx`](results/OpenSystem1-classifier-comparison.pptx).

## Repository layout

```text
poc/
  zero_shot_decision_poc.py       Local typed decision engine
  obvious_answers_benchmark.py    Shared 12-question benchmark
  typesafe_decision_poc.py        TypeSafe HTTP client
  test_zero_shot_decision_poc.py  Unit tests that require no model download
  zero_shot_decision_input.json   Single-request example
  requirements-zero-shot-decisions.txt
  build_benchmark_deck.py         Original ModernBERT deck builder
  deck_appendix.py                ModernBERT architecture and code appendix
  check_deck_geometry.py          PowerPoint geometry checks
results/
  benchmark-results.json
  typesafe-benchmark-results.json
  typesafe-benchmark-raw-responses.json
  modernbert-benchmark-results.pptx
  OpenSystem1-classifier-comparison.pptx
docs/
  linkedin-post.md
  zero-shot-alternatives.md
```

Model weights and API credentials are intentionally excluded.

## Requirements

- Python 3.10 or later
- About 1 GB of free disk space for the ModernBERT checkpoint and tokenizer
- PyTorch-compatible CPU, CUDA GPU, or Apple Silicon GPU
- A TypeSafe API key only if you want to run the hosted comparison

Create an environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r poc/requirements-zero-shot-decisions.txt
```

For tests and model download support:

```bash
python -m pip install pytest huggingface_hub
```

## Download ModernBERT

The local scorer defaults to `MoritzLaurer/ModernBERT-large-zeroshot-v2.0`. The model card describes a 0.4B-parameter, Apache-2.0 checkpoint built on ModernBERT-large.

### Option A: let Transformers download and cache it

Pass the Hugging Face repository id directly:

```bash
python poc/obvious_answers_benchmark.py \
  --model MoritzLaurer/ModernBERT-large-zeroshot-v2.0
```

Transformers downloads the files into the Hugging Face cache on the first run.

### Option B: download a portable local copy

This is the recommended setup for repeatable or offline use:

```bash
mkdir -p models
hf download MoritzLaurer/ModernBERT-large-zeroshot-v2.0 \
  --local-dir models/modernbert-zeroshot
```

Confirm that the weights exist:

```bash
ls -lh models/modernbert-zeroshot/model.safetensors
```

Then force offline inference:

```bash
export HF_HUB_OFFLINE=1
python poc/obvious_answers_benchmark.py \
  --model models/modernbert-zeroshot
```

Do not copy a Hugging Face cache snapshot without dereferencing symlinks. Using `hf download --local-dir` creates ordinary files and avoids dangling weight links.

## Run a single typed decision

```bash
python poc/zero_shot_decision_poc.py \
  --input poc/zero_shot_decision_input.json \
  --model models/modernbert-zeroshot
```

The scorer supports `--device auto`, `cpu`, `cuda`, or `mps`. `auto` prefers CUDA, then Apple MPS, then CPU.

## Run the 12-question ModernBERT benchmark

```bash
python poc/obvious_answers_benchmark.py \
  --model models/modernbert-zeroshot \
  --json > results/benchmark-results-new.json
```

The model loads once and scores every premise/hypothesis pair in batches.

## Run the TypeSafe comparison

Copy the safe example and add your key locally:

```bash
cp .env.example .env
```

Never commit `.env`. Then run:

```bash
python poc/typesafe_decision_poc.py \
  --output results/typesafe-benchmark-results-new.json \
  --raw-output results/typesafe-benchmark-raw-responses-new.json
```

The raw audit file records request and response JSON but never stores the API key. Use `--dry-run` to inspect the payload without calling the service.

## Run the tests

The tests use a fake scorer and do not download ModernBERT:

```bash
python -m pytest poc/test_zero_shot_decision_poc.py -q
```

Expected result: `13 passed`.

## Other zero-shot models to benchmark

The next useful comparison is [DeBERTa-v3-large-zeroshot-v2.0](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0), because it uses the same NLI task shape and model family source. Other candidates include [BART-large-MNLI](https://huggingface.co/facebook/bart-large-mnli), multilingual [mDeBERTa-v3-base-MNLI-XNLI](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli), and [GLiClass](https://huggingface.co/knowledgator/gliclass-small-v1.0), which uses a more efficient classification architecture.

See [`docs/zero-shot-alternatives.md`](docs/zero-shot-alternatives.md) for the suggested evaluation order.

## Responsible interpretation

The 12 questions intentionally have obvious answers. They check plumbing, option framing, typed output, and abstention behavior. They do not measure production accuracy or calibration. Before deployment, add ambiguous, incomplete, adversarial, and domain-specific cases, then select thresholds from observed error costs.
