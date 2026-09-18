#!/usr/bin/env python3
"""Run the BFCL-derived Stage-1 routing benchmark on either classifier."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typesafe_decision_poc import (  # noqa: E402
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL as TYPESAFE_MODEL,
    _load_dotenv,
    _resolve_api_key,
    build_payload,
    call_api,
    summarise_answer,
)
from zero_shot_decision_poc import (  # noqa: E402
    TransformersNliScorer,
    evaluate,
    parse_request,
)


def load_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload.get("cases"), list) or not payload["cases"]:
        raise ValueError("Dataset must contain a non-empty cases array")
    return payload


def request_for(case: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": case["state"],
        "decisions": [
            {
                "id": case["id"],
                "kind": "choice",
                "question": case["question"],
                "minimum_probability": metadata["minimum_probability"],
                "minimum_margin": metadata["minimum_margin"],
                "options": [
                    {"id": option_id, "description": description}
                    for option_id, description in case["options"].items()
                ],
            }
        ],
    }


def modernbert_rows(
    dataset: dict[str, Any], model: str, device: str, batch_size: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scorer = TransformersNliScorer(model, device=device, batch_size=batch_size)
    rows: list[dict[str, Any]] = []
    for case in dataset["cases"]:
        started = time.perf_counter()
        result = evaluate(parse_request(request_for(case, dataset)), scorer)["results"][0]
        elapsed_ms = (time.perf_counter() - started) * 1000
        picked = result["recommended_option"]
        rows.append(
            {
                **case,
                "picked": picked,
                "picked_tool_name": case["tool_names"].get(picked),
                "correct": picked == case["expected"],
                "probabilities": result["probabilities"],
                "top_probability": result["top_probability"],
                "margin": result["top_two_margin"],
                "review_required": result["review_required"],
                "review_reason": result["review_reason"],
                "latency_ms": round(elapsed_ms, 3),
            }
        )
    return rows, []


def typesafe_rows(
    dataset: dict[str, Any], endpoint: str, model: str, api_key: str, timeout: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = dataset["cases"]
    payloads = build_payload(cases, model)
    rows: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    for index, (case, payload) in enumerate(zip(cases, payloads, strict=True), start=1):
        started = time.perf_counter()
        response = call_api(payload, api_key, endpoint=endpoint, timeout=timeout)
        elapsed_ms = (time.perf_counter() - started) * 1000
        row = summarise_answer(case, response)
        row["picked_tool_name"] = case["tool_names"].get(row["picked"])
        row["latency_ms"] = round(elapsed_ms, 3)
        row["source_id"] = case["source_id"]
        row["category"] = case["category"]
        row["tool_names"] = case["tool_names"]
        row["function_schemas"] = case["function_schemas"]
        rows.append(row)
        raw.append({"case_id": case["id"], "request": payload, "response": response})
        print(f"[{index:02d}/{len(cases)}] {case['id']}: {row['picked']}", file=sys.stderr)
    return rows, raw


def safe_mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def slice_for(category: str) -> list[dict[str, Any]]:
        return [row for row in rows if row["category"] == category]

    def accuracy(group: list[dict[str, Any]]) -> float:
        return sum(bool(row["correct"]) for row in group) / len(group) if group else 0.0

    positives = slice_for("multiple")
    negatives = slice_for("irrelevance")
    no_tool_predicted = [row for row in rows if row["picked"] == "no_tool"]
    true_no_tool = [row for row in no_tool_predicted if row["expected"] == "no_tool"]
    gate_clear = [row for row in rows if not row["review_required"]]
    correct_and_clear = [row for row in gate_clear if row["correct"]]
    return {
        "case_count": len(rows),
        "correct": sum(bool(row["correct"]) for row in rows),
        "accuracy": round(accuracy(rows), 6),
        "selection_accuracy": round(accuracy(positives), 6),
        "no_tool_recall": round(accuracy(negatives), 6),
        "no_tool_precision": round(
            len(true_no_tool) / len(no_tool_predicted) if no_tool_predicted else 0.0, 6
        ),
        "gate_clear_count": len(gate_clear),
        "gate_clearance": round(len(gate_clear) / len(rows), 6),
        "correct_and_gate_clear_count": len(correct_and_clear),
        "selective_accuracy": round(accuracy(gate_clear), 6) if gate_clear else None,
        "mean_top_probability": safe_mean([float(row["top_probability"]) for row in rows]),
        "mean_margin": safe_mean([float(row["margin"]) for row in rows]),
        "median_latency_ms": round(
            statistics.median(float(row["latency_ms"]) for row in rows), 3
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("modernbert", "typesafe"), required=True)
    parser.add_argument("--dataset", type=Path, default=Path("data/bfcl-routing-subset.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    started = time.perf_counter()
    if args.backend == "modernbert":
        model = args.model or "models/modernbert-zeroshot"
        rows, raw = modernbert_rows(dataset, model, args.device, args.batch_size)
    else:
        _load_dotenv(args.env_file)
        model = args.model or TYPESAFE_MODEL
        rows, raw = typesafe_rows(
            dataset, args.endpoint, model, _resolve_api_key(args.api_key), args.timeout
        )
    result = {
        "benchmark": dataset["benchmark"],
        "scope": dataset["scope"],
        "backend": args.backend,
        "model": model,
        "minimum_probability": dataset["minimum_probability"],
        "minimum_margin": dataset["minimum_margin"],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "summary": summary(rows),
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    if args.raw_output:
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_text(json.dumps({"calls": raw}, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
