#!/usr/bin/env python3
"""Sanity-check the zero-shot NLI decision POC on questions with obvious answers.

WHY THIS EXISTS
Before trusting a zero-shot scorer on ambiguous production decisions, it has to
clear a floor: questions where any competent human answers correctly and
confidently. Failures here are not "hard problem" failures, they are signs the
premise/hypothesis framing or the entailment-index resolution is wrong.

Twelve cases span deliberately different reasoning types (lexical sentiment,
arithmetic, geography, taxonomy, negation, temporal order, units, spam intent,
language ID, physical property, code language, urgency triage) so a systematic
framing problem shows up as a pattern rather than a single miss.

The model is loaded ONCE and reused for all cases -- loading 755MB of weights
per case would dominate runtime.

USAGE
    HF_HUB_OFFLINE=1 .venv-zero-shot312/bin/python poc/obvious_answers_benchmark.py \
        --model models/modernbert-zeroshot
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from zero_shot_decision_poc import (  # noqa: E402
    TransformersNliScorer,
    evaluate,
    parse_request,
)

# Each case: (id, state, question, expected_option_id, {option_id: description}).
# Descriptions are written as standalone definitions because they become the NLI
# hypothesis -- a bare label like "positive" gives the model nothing to entail.
CASES: list[dict[str, Any]] = [
    {
        "id": "sentiment_obvious",
        "reasoning": "lexical sentiment",
        "state": {"review": "This is the best meal I have ever eaten. Absolutely wonderful."},
        "question": "What sentiment does the review express?",
        "expected": "positive",
        "options": {
            "positive": "The review expresses praise, enjoyment, satisfaction, or a favourable opinion.",
            "negative": "The review expresses criticism, disappointment, dislike, or an unfavourable opinion.",
        },
    },
    {
        "id": "arithmetic",
        "reasoning": "arithmetic",
        "state": {"expression": "2 + 2"},
        "question": "What is the value of the expression?",
        "expected": "four",
        "options": {
            "four": "The expression evaluates to the number 4.",
            "seven": "The expression evaluates to the number 7.",
            "twelve": "The expression evaluates to the number 12.",
        },
    },
    {
        "id": "geography_capital",
        "reasoning": "world knowledge",
        "state": {"country": "France"},
        "question": "What is the capital city of this country?",
        "expected": "paris",
        "options": {
            "paris": "The capital city is Paris.",
            "berlin": "The capital city is Berlin.",
            "tokyo": "The capital city is Tokyo.",
        },
    },
    {
        "id": "animal_taxonomy",
        "reasoning": "taxonomy",
        "state": {"animal": "a dog with four legs that barks and wags its tail"},
        "question": "What kind of animal is described?",
        "expected": "mammal",
        "options": {
            "mammal": "The animal is a mammal: warm-blooded, has fur or hair, and feeds milk to its young.",
            "fish": "The animal is a fish: lives in water and breathes through gills.",
            "insect": "The animal is an insect: has six legs and an exoskeleton.",
        },
    },
    {
        "id": "explicit_negation",
        "reasoning": "negation handling",
        "state": {"statement": "The server is not running and has been completely shut down."},
        "question": "What is the current state of the server?",
        "expected": "stopped",
        "options": {
            "stopped": "The server is not running; it is offline, stopped, or shut down.",
            "running": "The server is running normally and is available.",
        },
    },
    {
        "id": "temporal_order",
        "reasoning": "temporal ordering",
        "state": {"events": "The package was ordered on Monday and delivered on Friday of the same week."},
        "question": "Which event happened first?",
        "expected": "ordering",
        "options": {
            "ordering": "The order was placed before the delivery occurred.",
            "delivery": "The delivery occurred before the order was placed.",
        },
    },
    {
        "id": "unit_magnitude",
        "reasoning": "unit comparison",
        "state": {"comparison": "one kilometre versus one centimetre"},
        "question": "Which distance is larger?",
        "expected": "kilometre",
        "options": {
            "kilometre": "One kilometre is the larger distance.",
            "centimetre": "One centimetre is the larger distance.",
        },
    },
    {
        "id": "spam_intent",
        "reasoning": "intent classification",
        "state": {
            "email": "CONGRATULATIONS!!! You have WON $10,000,000. Send your bank details and a $500 fee to claim now!!!"
        },
        "question": "How should this email be classified?",
        "expected": "spam",
        "options": {
            "spam": "The message is unsolicited spam, a scam, or a fraudulent attempt to obtain money or credentials.",
            "legitimate": "The message is a normal, legitimate piece of correspondence.",
        },
    },
    {
        "id": "language_id",
        "reasoning": "language identification",
        "state": {"text": "Bonjour, je m'appelle Marie et j'habite a Paris."},
        "question": "In which language is the text written?",
        "expected": "french",
        "options": {
            "french": "The text is written in the French language.",
            "german": "The text is written in the German language.",
            "japanese": "The text is written in the Japanese language.",
        },
    },
    {
        "id": "physical_property",
        "reasoning": "physical reasoning",
        "state": {"object": "a solid block of iron dropped into a bathtub of water"},
        "question": "What will the object do in water?",
        "expected": "sink",
        "options": {
            "sink": "The object is denser than water and will sink to the bottom.",
            "float": "The object is less dense than water and will float on the surface.",
        },
    },
    {
        "id": "code_language",
        "reasoning": "code recognition",
        "state": {"snippet": "def greet(name):\n    print(f'Hello, {name}')"},
        "question": "Which programming language is this snippet written in?",
        "expected": "python",
        "options": {
            "python": "The snippet is written in Python, using def and indentation-based blocks.",
            "java": "The snippet is written in Java, using classes and curly braces.",
            "sql": "The snippet is written in SQL, a query language for databases.",
        },
    },
    {
        "id": "urgency_triage",
        "reasoning": "severity triage",
        "state": {
            "ticket": "Production database is completely down. All customers are unable to log in. Revenue impact ongoing."
        },
        "question": "What priority should this ticket receive?",
        "expected": "critical",
        "options": {
            "critical": "The issue is a critical outage causing widespread customer impact and requires immediate response.",
            "low": "The issue is a minor inconvenience with no customer impact and can wait.",
        },
    },
]


def _build_request(case: dict[str, Any]) -> dict[str, Any]:
    """Convert a compact case definition into the POC's input schema.

    Thresholds are set to the POC defaults used in the sample input so
    `review_required` means the same thing here as in normal use: on an obvious
    question, a flagged review is itself a finding.
    """
    return {
        "state": case["state"],
        "decisions": [
            {
                "id": case["id"],
                "kind": "choice",
                "question": case["question"],
                "minimum_probability": 0.65,
                "minimum_margin": 0.15,
                "options": [
                    {"id": option_id, "description": description}
                    for option_id, description in case["options"].items()
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="models/modernbert-zeroshot",
        help="Local model directory or Hugging Face repo id.",
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the summary table.",
    )
    arguments = parser.parse_args()

    # Loaded once: 755MB of weights per case would dominate runtime.
    scorer = TransformersNliScorer(
        arguments.model, device=arguments.device, batch_size=arguments.batch_size
    )

    rows: list[dict[str, Any]] = []
    for case in CASES:
        result = evaluate(parse_request(_build_request(case)), scorer)["results"][0]
        probabilities: dict[str, float] = result["probabilities"]
        # `answer` is None when the decision fails its confidence/margin gate --
        # the POC abstains rather than guessing. `recommended_option` still holds
        # the top-ranked candidate, which is what we want to score against, so
        # abstention is reported separately from a wrong pick.
        picked = result["answer"] or result["recommended_option"]
        rows.append(
            {
                "id": case["id"],
                "reasoning": case["reasoning"],
                # state/question/options are echoed so downstream consumers (the
                # slide builder) can show the exact model input without having to
                # re-import CASES and stay in sync with it.
                "state": case["state"],
                "question": case["question"],
                "options": case["options"],
                "expected": case["expected"],
                "picked": picked,
                "correct": picked == case["expected"],
                "confidence": result["top_probability"],
                "margin": result["top_two_margin"],
                "review_required": result["review_required"],
                "review_reason": result["review_reason"],
                "probabilities": probabilities,
            }
        )

    if arguments.json:
        print(json.dumps({"cases": rows}, indent=2))
        return 0

    correct = sum(1 for row in rows if row["correct"])
    flagged = sum(1 for row in rows if row["review_required"])

    print()
    print(f"model: {arguments.model}")
    print(f"cases: {len(rows)}   correct: {correct}/{len(rows)}   flagged for review: {flagged}")
    print()
    header = f"{'':2} {'case':20} {'reasoning':22} {'picked':12} {'conf':>7} {'margin':>7}  review"
    print(header)
    print("-" * len(header))
    for row in rows:
        mark = "OK" if row["correct"] else "XX"
        review = "yes" if row["review_required"] else "-"
        print(
            f"{mark:2} {row['id']:20} {row['reasoning']:22} {row['picked']:12} "
            f"{row['confidence']:7.4f} {row['margin']:7.4f}  {review}"
        )

    # Full distributions matter: a correct pick at 0.34 vs 0.33 is a coin flip
    # that happened to land right, and should not read as a pass.
    print()
    print("full probability distributions:")
    for row in rows:
        ordered = sorted(row["probabilities"].items(), key=lambda item: -item[1])
        rendered = "  ".join(f"{name}={value:.4f}" for name, value in ordered)
        print(f"  {row['id']:20} {rendered}")

    misses = [row for row in rows if not row["correct"]]
    if misses:
        print()
        print("MISSES:")
        for row in misses:
            print(f"  {row['id']}: expected {row['expected']!r}, picked {row['picked']!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
