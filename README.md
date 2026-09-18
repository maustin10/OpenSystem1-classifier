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

The original 12-question presentation is in
[`results/OpenSystem1-classifier-comparison.pptx`](results/OpenSystem1-classifier-comparison.pptx).
The current deck, including the BFCL-derived Stage-1 results, is
[`results/OpenSystem1-classifier-comparison-stage1.pptx`](results/OpenSystem1-classifier-comparison-stage1.pptx).

## Stage 1: BFCL-derived tool routing

The second benchmark isolates the part of tool calling that both classifiers can
perform fairly: select one declared tool, or determine that no supplied tool is
callable. It uses 30 cases derived from the official BFCL V4 data at commit
`6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`:

| Measure | ModernBERT NLI | TypeSafe Jev 1.13.0 |
|---|---:|---:|
| Overall routing accuracy | 23/30 (76.7%) | 29/30 (96.7%) |
| Multiple-function selection | 17/20 (85%) | 20/20 (100%) |
| No-tool detection | 6/10 (60%) | 9/10 (90%) |
| Cleared the unchanged decision gate | 0/30 | 30/30 |

The TypeSafe responses were not uniformly `1.0` on this harder set: 25 of 30
had a top probability of `1.0`; the remaining five ranged from `0.70` to `0.97`.
Its one wrong route still cleared the gate at `0.72`, which is a useful reminder
that thresholding controls abstention rather than guaranteeing correctness.

This is a **BFCL-derived routing benchmark, not an official BFCL leaderboard
score**. Official AST and executable evaluation also requires argument
generation and execution, which neither classifier performs by itself. See
[`docs/bfcl-routing-benchmark.md`](docs/bfcl-routing-benchmark.md) for the
protocol and interpretation.

## Repository layout

```text
poc/
  build_bfcl_routing_subset.py    Reproducible extraction from official BFCL data
  bfcl_routing_benchmark.py       Shared ModernBERT / TypeSafe routing runner
  test_bfcl_routing_benchmark.py  Dataset and metric tests
  update_deck_bfcl_routing.mjs    Editable PowerPoint update
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
  OpenSystem1-classifier-comparison-stage1.pptx
  bfcl-routing-modernbert-results.json
  bfcl-routing-typesafe-results.json
  bfcl-routing-typesafe-raw-responses.json
data/
  bfcl-routing-subset.json
  README.md
docs/
  bfcl-routing-benchmark.md
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

## Run the BFCL-derived routing benchmark

The 30-case dataset is committed, so rebuilding it is optional. Run the local
model with:

```bash
HF_HUB_OFFLINE=1 python poc/bfcl_routing_benchmark.py \
  --backend modernbert \
  --dataset data/bfcl-routing-subset.json \
  --model models/modernbert-zeroshot \
  --output results/bfcl-routing-modernbert-results-new.json
```

Run TypeSafe with:

```bash
python poc/bfcl_routing_benchmark.py \
  --backend typesafe \
  --dataset data/bfcl-routing-subset.json \
  --env-file .env \
  --output results/bfcl-routing-typesafe-results-new.json \
  --raw-output results/bfcl-routing-typesafe-raw-responses-new.json
```

To regenerate the subset from the exact official source revision:

```bash
git clone https://github.com/ShishirPatil/gorilla.git ../gorilla
git -C ../gorilla checkout 6ea57973c7a6097fd7c5915698c54c17c5b1b6c8
python poc/build_bfcl_routing_subset.py \
  --bfcl-data-dir ../gorilla/berkeley-function-call-leaderboard/bfcl_eval/data \
  --output data/bfcl-routing-subset.json
```

## Run the tests

The tests use a fake scorer and do not download ModernBERT:

```bash
python -m pytest poc/test_zero_shot_decision_poc.py -q
```

Expected result: `15 passed`.

## Other zero-shot models to benchmark

The next useful comparison is [DeBERTa-v3-large-zeroshot-v2.0](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0), because it uses the same NLI task shape and model family source. Other candidates include [BART-large-MNLI](https://huggingface.co/facebook/bart-large-mnli), multilingual [mDeBERTa-v3-base-MNLI-XNLI](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli), and [GLiClass](https://huggingface.co/knowledgator/gliclass-small-v1.0), which uses a more efficient classification architecture.

See [`docs/zero-shot-alternatives.md`](docs/zero-shot-alternatives.md) for the suggested evaluation order.

## Responsible interpretation

The 12 questions intentionally have obvious answers. They check plumbing, option framing, typed output, and abstention behavior. They do not measure production accuracy or calibration. Before deployment, add ambiguous, incomplete, adversarial, and domain-specific cases, then select thresholds from observed error costs.
