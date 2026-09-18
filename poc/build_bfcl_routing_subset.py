#!/usr/bin/env python3
"""Build the committed Stage-1 routing subset from official BFCL data.

The resulting dataset deliberately evaluates only function selection and
irrelevance detection. It does not ask either classifier to synthesize function
arguments, so ModernBERT and TypeSafe System One receive the same task.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

BFCL_REPOSITORY = "https://github.com/ShishirPatil/gorilla"
BFCL_COMMIT = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
MULTIPLE_INDICES = tuple(range(20))
IRRELEVANCE_INDICES = (0, 20, 40, 60, 80, 100, 120, 140, 160, 180)
MULTIPLE_QUESTION = "Which available tool best handles the user's request?"
IRRELEVANCE_QUESTION = (
    "Should the available tool be called now, or is no supplied tool callable for this request?"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def user_text(entry: dict[str, Any]) -> str:
    messages = entry["question"]
    return "\n".join(
        message["content"]
        for turn in messages
        for message in turn
        if message.get("role") == "user"
    )


def parameter_summary(function: dict[str, Any]) -> str:
    parameters = function.get("parameters") or {}
    properties = parameters.get("properties") or {}
    required = set(parameters.get("required") or [])
    parts: list[str] = []
    for name, definition in properties.items():
        type_name = definition.get("type", "value")
        description = " ".join(str(definition.get("description", "")).split())
        status = "required" if name in required else "optional"
        detail = f"{name} ({type_name}, {status})"
        if description:
            detail += f": {description}"
        parts.append(detail)
    return "; ".join(parts) if parts else "No parameters documented."


def option_description(function: dict[str, Any]) -> str:
    description = " ".join(str(function.get("description", "")).split())
    return (
        f"Use tool {function['name']}. {description} "
        f"Parameters: {parameter_summary(function)}"
    ).strip()


def answer_name(ground_truth: dict[str, Any]) -> str:
    calls = ground_truth["ground_truth"]
    if len(calls) != 1 or len(calls[0]) != 1:
        raise ValueError(f"Expected one function in {ground_truth['id']}")
    return next(iter(calls[0]))


def adapt(
    entry: dict[str, Any], *, category: str, expected_function: str | None
) -> dict[str, Any]:
    options: dict[str, str] = {}
    tool_names: dict[str, str | None] = {}
    expected = "no_tool"
    for index, function in enumerate(entry["function"], start=1):
        option_id = f"tool_{index}"
        options[option_id] = option_description(function)
        tool_names[option_id] = function["name"]
        if function["name"] == expected_function:
            expected = option_id
    if category == "irrelevance":
        options["no_tool"] = (
            "No supplied tool should be called: either the request does not match a "
            "listed tool or it lacks required argument values needed for a valid call."
        )
        tool_names["no_tool"] = None
    if expected_function is not None and expected == "no_tool":
        raise ValueError(f"Ground-truth function missing in {entry['id']}: {expected_function}")

    stable_id = re.sub(r"[^a-z0-9_-]", "_", f"routing_{entry['id']}")
    return {
        "id": stable_id,
        "source_id": entry["id"],
        "category": category,
        "reasoning": "tool selection" if category == "multiple" else "no-tool detection",
        "state": {"user_request": user_text(entry)},
        "question": MULTIPLE_QUESTION if category == "multiple" else IRRELEVANCE_QUESTION,
        "expected": expected,
        "expected_tool_name": expected_function,
        "options": options,
        "tool_names": tool_names,
        "function_schemas": entry["function"],
    }


def build(data_dir: Path) -> dict[str, Any]:
    multiple = load_jsonl(data_dir / "BFCL_v4_multiple.json")
    answers = {
        row["id"]: row
        for row in load_jsonl(data_dir / "possible_answer" / "BFCL_v4_multiple.json")
    }
    irrelevance = load_jsonl(data_dir / "BFCL_v4_irrelevance.json")

    cases = [
        adapt(
            multiple[index],
            category="multiple",
            expected_function=answer_name(answers[multiple[index]["id"]]),
        )
        for index in MULTIPLE_INDICES
    ]
    cases.extend(
        adapt(irrelevance[index], category="irrelevance", expected_function=None)
        for index in IRRELEVANCE_INDICES
    )
    return {
        "benchmark": "OpenSystem1 BFCL-derived routing subset v1",
        "scope": "Stage 1: single-tool routing and no-tool detection only",
        "case_count": len(cases),
        "minimum_probability": 0.65,
        "minimum_margin": 0.15,
        "source": {
            "name": "Berkeley Function Calling Leaderboard (BFCL) V4",
            "repository": BFCL_REPOSITORY,
            "commit": BFCL_COMMIT,
            "license": "Apache-2.0",
            "files": ["BFCL_v4_multiple.json", "BFCL_v4_irrelevance.json"],
        },
        "selection": {
            "multiple_indices": list(MULTIPLE_INDICES),
            "irrelevance_indices": list(IRRELEVANCE_INDICES),
            "method": (
                "First 20 non-live multiple-function cases plus 10 evenly spaced "
                "non-live irrelevance cases. no_tool is present only in the irrelevance "
                "cases, matching BFCL's separate category design."
            ),
        },
        "limitations": [
            "This is a derived routing subset, not an official BFCL leaderboard score.",
            "Arguments, parallel calls, multi-turn execution, and executability are out of scope.",
            "Thresholds are fixed in advance and are not tuned on these 30 cases.",
        ],
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bfcl-data-dir",
        type=Path,
        required=True,
        help="Path to berkeley-function-call-leaderboard/bfcl_eval/data.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.bfcl_data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {payload['case_count']} cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
