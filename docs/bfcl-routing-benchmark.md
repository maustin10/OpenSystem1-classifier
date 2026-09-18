# BFCL-derived tool-routing benchmark

## Purpose

This Stage-1 benchmark compares ModernBERT and TypeSafe System One on the part
of function calling that both systems natively support: selecting a declared
tool or declining to call one. It deliberately does not score argument values,
parallel calls, multi-turn behavior, or execution.

The source is the [Berkeley Function Calling Leaderboard (BFCL)](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard)
V4 data at commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`.
BFCL describes its Multiple Function category as choosing one function from two
to four schemas and its Irrelevance category as recognizing that no function
should be invoked.

## Dataset design

The committed [`data/bfcl-routing-subset.json`](../data/bfcl-routing-subset.json)
contains:

- The first 20 non-live `BFCL_v4_multiple.json` cases.
- 10 evenly spaced non-live `BFCL_v4_irrelevance.json` cases at indices 0, 20,
  40, 60, 80, 100, 120, 140, 160, and 180.
- The original user request and complete function schemas.
- Stable option IDs mapped back to the original BFCL function names.
- A `no_tool` option only for irrelevance cases, matching BFCL's separation of
  function selection and relevance detection.

The transformation is reproducible with
[`poc/build_bfcl_routing_subset.py`](../poc/build_bfcl_routing_subset.py).

## Shared protocol

Both backends receive the same user request, question, option IDs, function
descriptions, parameter names, required flags, and parameter descriptions.

The fixed gate is unchanged from the original benchmark:

- Top probability must be at least `0.65`.
- Top-two margin must be at least `0.15`.

Top-ranked accuracy is scored independently of the gate. This keeps two
questions separate: “Did the system rank the expected route first?” and “Would
the application automate that route under this policy?”

## Results

| Measure | ModernBERT NLI | TypeSafe Jev 1.13.0 |
|---|---:|---:|
| Overall | 23/30 (76.7%) | 29/30 (96.7%) |
| Multiple-function selection | 17/20 (85%) | 20/20 (100%) |
| No-tool recall | 6/10 (60%) | 9/10 (90%) |
| No-tool precision | 100% | 100% |
| Gate clearance | 0/30 (0%) | 30/30 (100%) |
| Mean top probability | 0.4870 | 0.9770 |
| Mean top-two margin | 0.0867 | 0.9540 |

ModernBERT missed `multiple_2`, `multiple_4`, `multiple_11`, and four no-tool
cases. TypeSafe missed only `irrelevance_180`, where the request asks for cricket
matches “scheduled for today” and the supplied function requires explicit
`date` and `sport` arguments.

TypeSafe returned exact one-hot probabilities on 25 of 30 cases, not all 30.
The five non-saturated top probabilities were `0.70`, `0.97`, `0.97`, `0.95`,
and `0.72`. The last value was the wrong route, and it still cleared the gate.
The client did not round or threshold these values; the raw responses are in
[`results/bfcl-routing-typesafe-raw-responses.json`](../results/bfcl-routing-typesafe-raw-responses.json).

## Interpretation

The unchanged gate did not transfer well to ModernBERT's more ambiguous routing
distributions: none of its 30 routes cleared even though 23 ranked correctly.
TypeSafe was much more decisive, but its one error also passed the gate. The
result therefore supports two conclusions:

1. TypeSafe performed better on this routing subset.
2. Confidence thresholds need validation against representative errors; they
   are abstention policies, not correctness guarantees.

Latency numbers are retained in the JSON artifacts for reproducibility but are
not treated as a controlled comparison. The local run used CPU inference, while
TypeSafe latency includes a hosted network request.

## Scope boundary and next stage

This is not an official BFCL leaderboard score. A full BFCL AST or executable
run requires a system to emit the selected function name and correctly typed
argument values, and executable categories additionally validate runtime
behavior. A future Stage 2 can add a deterministic, schema-aware argument
extractor and then use BFCL's official evaluator without changing the Stage-1
routing comparison.
