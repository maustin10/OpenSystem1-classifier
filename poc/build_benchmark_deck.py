#!/usr/bin/env python3
"""Render the obvious-answer benchmark results as a PowerPoint deck.

Reads the JSON emitted by `obvious_answers_benchmark.py --json` and produces one
slide per question showing the exact model input, the full probability
distribution, and the verdict -- plus a title, a methodology slide, a summary
table and a findings slide.

USAGE
    .venv/bin/python poc/build_benchmark_deck.py \
        --results .dev-logs/obvious-bench.json \
        --output models/zero-shot-nli-benchmark-results.pptx
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from deck_appendix import appendix_slides, pipeline_slide
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# "Ocean Gradient" palette: deep blue dominates, teal supports, midnight anchors
# the dark slides. Chosen because the subject is probability/measurement rather
# than anything warm -- and because red/green must stay reserved for pass/fail
# semantics, so the base palette deliberately avoids them.
DEEP = RGBColor(0x06, 0x5A, 0x82)
TEAL = RGBColor(0x1C, 0x72, 0x93)
MIDNIGHT = RGBColor(0x21, 0x29, 0x5C)
CLOUD = RGBColor(0xF4, 0xF7, 0xF9)
INK = RGBColor(0x1A, 0x1F, 0x2B)
MUTED = RGBColor(0x6B, 0x7A, 0x8C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PASS = RGBColor(0x1E, 0x7A, 0x4B)
WARN = RGBColor(0xB8, 0x6E, 0x00)

HEAD_FONT = "Georgia"
BODY_FONT = "Calibri"
MONO_FONT = "Consolas"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _blank(presentation: Presentation):
    return presentation.slides.add_slide(presentation.slide_layouts[6])


def _rect(slide, x, y, w, h, fill, *, shape=MSO_SHAPE.RECTANGLE, line=None):
    box = slide.shapes.add_shape(shape, x, y, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    if line is None:
        box.line.fill.background()
    else:
        box.line.color.rgb = line
        box.line.width = Pt(1)
    box.shadow.inherit = False
    return box


def _text(
    slide,
    x,
    y,
    w,
    h,
    runs: list[tuple[str, dict[str, Any]]],
    *,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    spacing: float | None = None,
):
    """Add a text box from (text, style) run tuples.

    margin=0 on all sides: PowerPoint's default internal padding (0.1" L/R,
    0.05" T/B) silently offsets text from any shape it is meant to align with.
    """
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0

    first = True
    for text, style in runs:
        paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        paragraph.alignment = style.get("align", align)
        if style.get("space_before"):
            paragraph.space_before = Pt(style["space_before"])
        if spacing is not None:
            paragraph.line_spacing = spacing
        run = paragraph.add_run()
        run.text = text
        font = run.font
        font.name = style.get("font", BODY_FONT)
        font.size = Pt(style.get("size", 14))
        font.bold = style.get("bold", False)
        font.italic = style.get("italic", False)
        font.color.rgb = style.get("color", INK)
    return box


def _bar(slide, x, y, w, h, fraction: float, colour):
    """Horizontal probability bar: track plus filled portion."""
    _rect(slide, x, y, w, h, RGBColor(0xDD, 0xE4, 0xEA))
    filled = int(w * max(fraction, 0.004))
    _rect(slide, x, y, Emu(filled), h, colour)


def _title_slide(presentation, cases: list[dict[str, Any]], model: str) -> None:
    slide = _blank(presentation)
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, MIDNIGHT)
    # Motif: a teal vertical spine on the left edge, repeated on every slide.
    _rect(slide, 0, 0, Inches(0.28), SLIDE_H, TEAL)

    _text(
        slide,
        Inches(1.0),
        Inches(1.5),
        Inches(11.0),
        Inches(0.5),
        [("ZERO-SHOT NLI DECISION POC", {"size": 15, "bold": True, "color": RGBColor(0x8F, 0xC7, 0xDC)})],
    )
    _text(
        slide,
        Inches(1.0),
        Inches(2.1),
        Inches(11.2),
        Inches(1.9),
        [
            ("Obvious-Answer", {"font": HEAD_FONT, "size": 52, "bold": True, "color": WHITE}),
            ("Sanity Benchmark", {"font": HEAD_FONT, "size": 52, "bold": True, "color": WHITE}),
        ],
        spacing=0.95,
    )
    _text(
        slide,
        Inches(1.0),
        Inches(4.3),
        Inches(10.5),
        Inches(0.6),
        [(
            "Twelve questions a competent human answers without hesitation — "
            "run through the local NLI scorer to establish a confidence floor.",
            {"size": 16, "italic": True, "color": RGBColor(0xC2, 0xD6, 0xE2)},
        )],
    )

    correct = sum(1 for c in cases if c["correct"])
    flagged = sum(1 for c in cases if c["review_required"])
    stats = [
        (f"{correct}/{len(cases)}", "correct answers"),
        (f"{flagged}", "flagged for review"),
        ("100%", "run fully offline"),
    ]
    for index, (value, label) in enumerate(stats):
        left = Inches(1.0 + index * 3.5)
        _text(
            slide,
            left,
            Inches(5.3),
            Inches(3.2),
            Inches(0.72),
            [(value, {"font": HEAD_FONT, "size": 40, "bold": True, "color": TEAL})],
        )
        _text(
            slide,
            left,
            Inches(6.08),
            Inches(3.2),
            Inches(0.35),
            [(label.upper(), {"size": 11, "bold": True, "color": RGBColor(0x9F, 0xB3, 0xC2)})],
        )

    _text(
        slide,
        Inches(1.0),
        Inches(6.85),
        Inches(11.2),
        Inches(0.35),
        [(f"model: {model}", {"font": MONO_FONT, "size": 10, "color": RGBColor(0x7A, 0x8C, 0x9E)})],
    )


def _method_slide(presentation, sample: dict[str, Any]) -> None:
    slide = _blank(presentation)
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, CLOUD)
    _rect(slide, 0, 0, Inches(0.28), SLIDE_H, TEAL)

    _text(
        slide,
        Inches(0.85),
        Inches(0.55),
        Inches(11.5),
        Inches(0.7),
        [("How the model is asked", {"font": HEAD_FONT, "size": 38, "bold": True, "color": MIDNIGHT})],
    )
    _text(
        slide,
        Inches(0.85),
        Inches(1.32),
        Inches(11.5),
        Inches(0.4),
        [(
            "The model never generates text. Every option becomes one "
            "premise/hypothesis pair, scored for entailment.",
            {"size": 15, "italic": True, "color": MUTED},
        )],
    )

    # Left: the JSON contract the caller writes.
    _rect(slide, Inches(0.85), Inches(2.0), Inches(5.75), Inches(4.5), WHITE, line=RGBColor(0xD5, 0xDF, 0xE6))
    _rect(slide, Inches(0.85), Inches(2.0), Inches(5.75), Inches(0.42), DEEP)
    _text(
        slide,
        Inches(1.05),
        Inches(2.08),
        Inches(5.4),
        Inches(0.3),
        [("1 · INPUT — what you send", {"size": 12, "bold": True, "color": WHITE})],
    )
    request = {
        "state": sample["state"],
        "decisions": [
            {
                "id": sample["id"],
                "kind": "choice",
                "question": sample["question"],
                "minimum_probability": 0.65,
                "minimum_margin": 0.15,
                "options": [{"id": k, "description": "..."} for k in sample["probabilities"]],
            }
        ],
    }
    _text(
        slide,
        Inches(1.05),
        Inches(2.6),
        Inches(5.4),
        Inches(3.75),
        [(json.dumps(request, indent=1)[:900], {"font": MONO_FONT, "size": 9, "color": INK})],
        spacing=1.15,
    )

    # Right: what the scorer does with it.
    _rect(slide, Inches(6.95), Inches(2.0), Inches(5.5), Inches(4.5), WHITE, line=RGBColor(0xD5, 0xDF, 0xE6))
    _rect(slide, Inches(6.95), Inches(2.0), Inches(5.5), Inches(0.42), TEAL)
    _text(
        slide,
        Inches(7.15),
        Inches(2.08),
        Inches(5.1),
        Inches(0.3),
        [("2 · SCORING — what happens inside", {"size": 12, "bold": True, "color": WHITE})],
    )
    steps = [
        ("Premise", "The state JSON, verbatim — the facts to reason over."),
        ("Hypothesis", "\"The correct option is 'X'. Definition: …\" — one per option."),
        ("Forward pass", "NLI head returns an entailment logit for each pair."),
        ("Softmax", "Logits normalised across options into probabilities."),
        ("Gate", "Answer withheld unless confidence \u2265 0.65 and margin \u2265 0.15."),
    ]
    top = 2.62
    for label, detail in steps:
        _rect(slide, Inches(7.15), Inches(top + 0.04), Inches(0.1), Inches(0.5), TEAL)
        _text(
            slide,
            Inches(7.42),
            Inches(top),
            Inches(4.85),
            Inches(0.28),
            [(label.upper(), {"size": 11.5, "bold": True, "color": DEEP})],
        )
        _text(
            slide,
            Inches(7.42),
            Inches(top + 0.28),
            Inches(4.85),
            Inches(0.42),
            [(detail, {"size": 11, "color": INK})],
        )
        top += 0.76

    _text(
        slide,
        Inches(0.85),
        Inches(6.72),
        Inches(11.5),
        Inches(0.3),
        [(
            "Because scores are softmaxed ACROSS options, absolute confidence "
            "falls as options are added — a 3-way 0.44 is not weaker evidence than a 2-way 0.79.",
            {"size": 11, "italic": True, "color": MUTED},
        )],
    )


def _case_slide(presentation, case: dict[str, Any], index: int, total: int) -> None:
    slide = _blank(presentation)
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, CLOUD)
    _rect(slide, 0, 0, Inches(0.28), SLIDE_H, TEAL)

    header = f"{index:02d} · {case['reasoning'].upper()}"
    _text(
        slide,
        Inches(0.85),
        Inches(0.42),
        Inches(8.0),
        Inches(0.3),
        [(header, {"size": 12, "bold": True, "color": TEAL})],
    )
    _text(
        slide,
        Inches(0.85),
        Inches(0.78),
        Inches(8.6),
        Inches(0.85),
        [(case["question"], {"font": HEAD_FONT, "size": 25, "bold": True, "color": MIDNIGHT})],
        spacing=1.0,
    )

    # Verdict chip, top-right. Green only when the pick is right AND ungated;
    # amber when right but withheld, so "correct" never hides an abstention.
    passed = case["correct"]
    gated = case["review_required"]
    chip_colour = PASS if (passed and not gated) else (WARN if passed else RGBColor(0xA3, 0x2A, 0x2A))
    chip_label = "CORRECT" if (passed and not gated) else ("CORRECT · GATED" if passed else "WRONG")
    chip = _rect(slide, Inches(9.85), Inches(0.5), Inches(2.6), Inches(0.5), chip_colour, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    frame = chip.text_frame
    frame.margin_left = frame.margin_right = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.CENTER
    run = paragraph.add_run()
    run.text = chip_label
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.name = BODY_FONT
    run.font.color.rgb = WHITE

    # --- Left column: the exact input the model received ------------------
    _rect(slide, Inches(0.85), Inches(1.85), Inches(5.35), Inches(4.15), WHITE, line=RGBColor(0xD5, 0xDF, 0xE6))
    _rect(slide, Inches(0.85), Inches(1.85), Inches(5.35), Inches(0.4), DEEP)
    _text(
        slide,
        Inches(1.03),
        Inches(1.93),
        Inches(5.0),
        Inches(0.28),
        [("INPUT · state JSON", {"size": 11.5, "bold": True, "color": WHITE})],
    )
    _text(
        slide,
        Inches(1.03),
        Inches(2.42),
        Inches(5.0),
        Inches(1.5),
        [(json.dumps(case["state"], indent=1), {"font": MONO_FONT, "size": 10, "color": INK})],
        spacing=1.2,
    )

    options_top = 4.05
    _text(
        slide,
        Inches(1.03),
        Inches(options_top),
        Inches(5.0),
        Inches(0.28),
        [("CANDIDATE OPTIONS", {"size": 10.5, "bold": True, "color": MUTED})],
    )
    row = options_top + 0.34
    for option_id in case["probabilities"]:
        marker = "\u25cf" if option_id == case["expected"] else "\u25cb"
        colour = PASS if option_id == case["expected"] else MUTED
        _text(
            slide,
            Inches(1.03),
            Inches(row),
            Inches(5.0),
            Inches(0.3),
            [(f"{marker}  {option_id}", {"font": MONO_FONT, "size": 11, "color": colour})],
        )
        row += 0.34
    _text(
        slide,
        Inches(1.03),
        Inches(row + 0.06),
        Inches(5.0),
        Inches(0.28),
        [("\u25cf = correct answer", {"size": 9.5, "italic": True, "color": MUTED})],
    )

    # --- Right column: probability output ---------------------------------
    _rect(slide, Inches(6.55), Inches(1.85), Inches(5.9), Inches(4.15), WHITE, line=RGBColor(0xD5, 0xDF, 0xE6))
    _rect(slide, Inches(6.55), Inches(1.85), Inches(5.9), Inches(0.4), TEAL)
    _text(
        slide,
        Inches(6.73),
        Inches(1.93),
        Inches(5.5),
        Inches(0.28),
        [("OUTPUT · probability distribution", {"size": 11.5, "bold": True, "color": WHITE})],
    )

    ordered = sorted(case["probabilities"].items(), key=lambda item: -item[1])
    bar_top = 2.5
    for option_id, probability in ordered:
        is_answer = option_id == case["picked"]
        colour = DEEP if is_answer else RGBColor(0x9F, 0xB8, 0xC7)
        _text(
            slide,
            Inches(6.73),
            Inches(bar_top),
            Inches(3.0),
            Inches(0.26),
            [(option_id, {"font": MONO_FONT, "size": 11, "bold": is_answer, "color": INK if is_answer else MUTED})],
        )
        _text(
            slide,
            Inches(11.35),
            Inches(bar_top),
            Inches(0.95),
            Inches(0.26),
            [(f"{probability:.4f}", {"font": MONO_FONT, "size": 11, "bold": is_answer, "color": INK if is_answer else MUTED})],
            align=PP_ALIGN.RIGHT,
        )
        _bar(slide, Inches(6.73), Inches(bar_top + 0.28), Inches(5.55), Inches(0.17), probability, colour)
        bar_top += 0.68

    metrics_top = max(bar_top + 0.12, 4.62)
    _rect(slide, Inches(6.73), Inches(metrics_top), Inches(5.55), Inches(0.02), RGBColor(0xDD, 0xE4, 0xEA))
    for offset, (label, value) in enumerate(
        [
            ("MODEL PICKED", case["picked"]),
            ("CONFIDENCE", f"{case['confidence']:.4f}"),
            ("TOP-2 MARGIN", f"{case['margin']:.4f}"),
        ]
    ):
        left = Inches(6.73 + offset * 1.87)
        _text(
            slide,
            left,
            Inches(metrics_top + 0.18),
            Inches(1.8),
            Inches(0.26),
            [(label, {"size": 9.5, "bold": True, "color": MUTED})],
        )
        _text(
            slide,
            left,
            Inches(metrics_top + 0.46),
            Inches(1.8),
            Inches(0.4),
            [(str(value), {"font": MONO_FONT, "size": 15, "bold": True, "color": DEEP})],
        )

    note = (
        "Answer withheld — below the 0.65 / 0.15 gate, so the POC abstains rather than guess."
        if gated
        else "Cleared the 0.65 / 0.15 gate — answer returned directly."
    )
    _text(
        slide,
        Inches(0.85),
        Inches(6.28),
        Inches(11.6),
        Inches(0.6),
        [(note, {"size": 12, "italic": True, "color": WARN if gated else PASS})],
    )
    _text(
        slide,
        Inches(0.85),
        Inches(6.95),
        Inches(11.6),
        Inches(0.28),
        [(f"case {index} of {total}   ·   id: {case['id']}", {"size": 9.5, "color": RGBColor(0x9A, 0xA8, 0xB6)})],
    )


def _summary_slide(presentation, cases: list[dict[str, Any]]) -> None:
    slide = _blank(presentation)
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, CLOUD)
    _rect(slide, 0, 0, Inches(0.28), SLIDE_H, TEAL)
    _text(
        slide,
        Inches(0.85),
        Inches(0.45),
        Inches(11.5),
        Inches(0.7),
        [("All twelve results", {"font": HEAD_FONT, "size": 36, "bold": True, "color": MIDNIGHT})],
    )
    _text(
        slide,
        Inches(0.85),
        Inches(1.18),
        Inches(11.5),
        Inches(0.35),
        [(
            "Ranked by confidence. Every pick is correct; the gate is what varies.",
            {"size": 14, "italic": True, "color": MUTED},
        )],
    )

    columns = [
        ("REASONING TYPE", 0.85, 3.05),
        ("PICKED", 3.95, 1.95),
        ("CONF", 5.95, 1.0),
        ("MARGIN", 7.05, 1.0),
        ("GATE", 8.2, 1.35),
        ("DISTRIBUTION", 9.6, 2.85),
    ]
    header_y = 1.72
    _rect(slide, Inches(0.85), Inches(header_y), Inches(11.6), Inches(0.38), MIDNIGHT)
    for label, left, width in columns:
        _text(
            slide,
            Inches(left + 0.12),
            Inches(header_y + 0.09),
            Inches(width),
            Inches(0.26),
            [(label, {"size": 10, "bold": True, "color": WHITE})],
        )

    row_y = header_y + 0.44
    for position, case in enumerate(sorted(cases, key=lambda c: -c["confidence"])):
        if position % 2 == 0:
            _rect(slide, Inches(0.85), Inches(row_y - 0.04), Inches(11.6), Inches(0.38), WHITE)
        gated = case["review_required"]
        cells = [
            (case["reasoning"], 0.85, 3.05, INK, BODY_FONT, False),
            (case["picked"], 3.95, 1.95, DEEP, MONO_FONT, True),
            (f"{case['confidence']:.4f}", 5.95, 1.0, INK, MONO_FONT, False),
            (f"{case['margin']:.4f}", 7.05, 1.0, INK, MONO_FONT, False),
            ("review" if gated else "clear", 8.2, 1.35, WARN if gated else PASS, BODY_FONT, True),
        ]
        for text, left, width, colour, font, bold in cells:
            _text(
                slide,
                Inches(left + 0.12),
                Inches(row_y + 0.04),
                Inches(width),
                Inches(0.28),
                [(text, {"size": 11, "bold": bold, "color": colour, "font": font})],
            )
        # Inline stacked bar: shows how much of the mass the winner actually holds.
        cursor = 9.72
        for _, probability in sorted(case["probabilities"].items(), key=lambda item: -item[1]):
            segment = 2.6 * probability
            shade = DEEP if cursor == 9.72 else RGBColor(0xB9, 0xCC, 0xD8)
            _rect(slide, Inches(cursor), Inches(row_y + 0.1), Inches(max(segment, 0.03)), Inches(0.16), shade)
            cursor += segment
        row_y += 0.38

    _text(
        slide,
        Inches(0.85),
        Inches(row_y + 0.25),
        Inches(11.6),
        Inches(0.3),
        [(
            "12/12 correct · 5 cleared the gate · 7 flagged for human review",
            {"size": 13, "bold": True, "color": MIDNIGHT},
        )],
    )


def _findings_slide(presentation, cases: list[dict[str, Any]]) -> None:
    slide = _blank(presentation)
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, MIDNIGHT)
    _rect(slide, 0, 0, Inches(0.28), SLIDE_H, TEAL)
    _text(
        slide,
        Inches(0.9),
        Inches(0.6),
        Inches(11.4),
        Inches(0.75),
        [("What this tells us", {"font": HEAD_FONT, "size": 38, "bold": True, "color": WHITE})],
    )

    two_way = [c for c in cases if len(c["probabilities"]) == 2]
    three_way = [c for c in cases if len(c["probabilities"]) == 3]
    avg_two = sum(c["confidence"] for c in two_way) / len(two_way)
    avg_three = sum(c["confidence"] for c in three_way) / len(three_way)

    findings = [
        (
            "Ranking is reliable — calibration is not",
            f"All 12 answers correct, but only 5 cleared the 0.65 gate. The model knows "
            f"the right answer and reports it with low confidence.",
        ),
        (
            "Confidence dilutes with option count",
            f"2-option questions average {avg_two:.2f} confidence; 3-option questions "
            f"average {avg_three:.2f}. Softmax spreads mass across candidates, so thresholds "
            f"cannot be shared across differently-shaped decisions.",
        ),
        (
            "Arithmetic is the weakest signal",
            "\"2 + 2\" scored 0.3854 with a 0.0733 margin — near-uniform across four/seven/twelve. "
            "An NLI entailment head does not compute; route arithmetic to a calculator or a reasoning model.",
        ),
        (
            "The abstention gate behaves correctly",
            "It withheld every low-margin answer rather than guessing. That is the desired failure "
            "mode, but at these thresholds it would defer 58% of obvious questions to a human.",
        ),
    ]
    top = 1.62
    for number, (heading, detail) in enumerate(findings, start=1):
        circle = _rect(slide, Inches(0.9), Inches(top), Inches(0.46), Inches(0.46), TEAL, shape=MSO_SHAPE.OVAL)
        frame = circle.text_frame
        frame.margin_left = frame.margin_right = 0
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        paragraph = frame.paragraphs[0]
        paragraph.alignment = PP_ALIGN.CENTER
        run = paragraph.add_run()
        run.text = str(number)
        run.font.size = Pt(15)
        run.font.bold = True
        run.font.color.rgb = WHITE
        run.font.name = BODY_FONT

        _text(
            slide,
            Inches(1.62),
            Inches(top + 0.02),
            Inches(10.6),
            Inches(0.34),
            [(heading, {"size": 17, "bold": True, "color": RGBColor(0x8F, 0xC7, 0xDC)})],
        )
        _text(
            slide,
            Inches(1.62),
            Inches(top + 0.4),
            Inches(10.6),
            Inches(0.72),
            [(detail, {"size": 12.5, "color": RGBColor(0xD5, 0xE2, 0xEA)})],
            spacing=1.15,
        )
        top += 1.28

    _text(
        slide,
        Inches(0.9),
        Inches(6.85),
        Inches(11.4),
        Inches(0.3),
        [(
            "Recommendation: use rank order, not absolute probability, and recalibrate "
            "thresholds per option count before production use.",
            {"size": 12, "italic": True, "bold": True, "color": TEAL},
        )],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=".dev-logs/obvious-bench.json")
    parser.add_argument("--output", default="models/zero-shot-nli-benchmark-results.pptx")
    parser.add_argument("--model", default="MoritzLaurer/ModernBERT-large-zeroshot-v2.0 (local weights)")
    arguments = parser.parse_args()

    cases = json.loads(Path(arguments.results).read_text())["cases"]

    presentation = Presentation()
    presentation.slide_width = SLIDE_W
    presentation.slide_height = SLIDE_H

    _title_slide(presentation, cases, arguments.model)
    _method_slide(presentation, cases[0])
    # Architecture before the per-case evidence: the reader needs to know what a
    # "probability" here actually is before being shown twelve of them.
    pipeline_slide(presentation)
    for index, case in enumerate(cases, start=1):
        _case_slide(presentation, case, index, len(cases))
    _summary_slide(presentation, cases)
    _findings_slide(presentation, cases)
    # Code last: it is reference material, not narrative.
    appendix_slides(presentation)

    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(str(output))
    print(f"wrote {output}  ({len(presentation.slides.__iter__.__self__._sldIdLst)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
