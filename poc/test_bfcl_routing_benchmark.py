from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "poc" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


benchmark = _load_module("bfcl_routing_benchmark", "bfcl_routing_benchmark.py")


def test_committed_subset_shape() -> None:
    dataset = benchmark.load_dataset(ROOT / "data" / "bfcl-routing-subset.json")
    assert len(dataset["cases"]) == 30
    assert sum(case["category"] == "multiple" for case in dataset["cases"]) == 20
    assert sum(case["category"] == "irrelevance" for case in dataset["cases"]) == 10
    assert all(
        ("no_tool" in case["options"]) == (case["category"] == "irrelevance")
        for case in dataset["cases"]
    )


def test_summary_metrics() -> None:
    rows = [
        {"category": "multiple", "expected": "tool_1", "picked": "tool_1", "correct": True,
         "review_required": False, "top_probability": 0.8, "margin": 0.6, "latency_ms": 10},
        {"category": "irrelevance", "expected": "no_tool", "picked": "no_tool", "correct": True,
         "review_required": True, "top_probability": 0.6, "margin": 0.2, "latency_ms": 20},
    ]
    result = benchmark.summary(rows)
    assert result["accuracy"] == 1.0
    assert result["selection_accuracy"] == 1.0
    assert result["no_tool_recall"] == 1.0
    assert result["no_tool_precision"] == 1.0
    assert result["gate_clearance"] == 0.5
    assert result["selective_accuracy"] == 1.0
