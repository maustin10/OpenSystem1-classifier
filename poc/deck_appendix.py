#!/usr/bin/env python3
"""Architecture diagram + annotated code appendix slides for the benchmark deck.

Kept separate from build_benchmark_deck.py so the results deck stays focused on
measurements; this module supplies the "how it works" and "show me the code"
material appended after the findings slide.

The pipeline diagram is drawn with native PowerPoint shapes rather than a
rendered Mermaid image. mermaid-cli is not installable here (the npm registry
mirror rejects the credentials), and native shapes are strictly better for a
deliverable anyway: they stay editable, scale without resampling, and carry no
external asset dependency. The equivalent Mermaid source is shown on the slide
itself so the diagram is reproducible elsewhere.
"""
from __future__ import annotations

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

DEEP = RGBColor(0x06, 0x5A, 0x82)
TEAL = RGBColor(0x1C, 0x72, 0x93)
MIDNIGHT = RGBColor(0x21, 0x29, 0x5C)
CLOUD = RGBColor(0xF4, 0xF7, 0xF9)
INK = RGBColor(0x1A, 0x1F, 0x2B)
MUTED = RGBColor(0x6B, 0x7A, 0x8C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PASS = RGBColor(0x1E, 0x7A, 0x4B)
WARN = RGBColor(0xB8, 0x6E, 0x00)
CODE_BG = RGBColor(0x1B, 0x22, 0x33)
CODE_FG = RGBColor(0xE6, 0xED, 0xF3)
CODE_COMMENT = RGBColor(0x7F, 0xB0, 0x8A)
CODE_KEY = RGBColor(0x8F, 0xC7, 0xDC)

HEAD_FONT = "Georgia"
BODY_FONT = "Calibri"
MONO_FONT = "Consolas"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Mermaid source for the pipeline. Shown verbatim on the diagram slide so the
# picture can be regenerated outside PowerPoint.
MERMAID_SOURCE = """flowchart LR
  A[state JSON] --> P[premise]
  Q[question] --> P
  O[option descriptions] --> H[hypothesis x N]
  P --> T[tokenizer<br/>premise + hypothesis pairs]
  H --> T
  T --> M[ModernBERT-large<br/>NLI head]
  M --> L[entailment logit<br/>one per option]
  L --> S[softmax across options]
  S --> G{confidence >= 0.65<br/>AND margin >= 0.15?}
  G -- yes --> R[answer returned]
  G -- no --> V[abstain -> human review]"""


def _blank(presentation):
    return presentation.slides.add_slide(presentation.slide_layouts[6])


def _rect(slide, x, y, w, h, fill, *, shape=MSO_SHAPE.RECTANGLE, line=None):
    box = slide.shapes.add_shape(shape, x, y, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    if line is None:
        box.line.fill.background()
    else:
        box.line.color.rgb = line
        box.line.width = Pt(1.25)
    box.shadow.inherit = False
    return box


def _label(shape, lines: list[tuple[str, dict]], *, align=PP_ALIGN.CENTER):
    """Write centred text directly into a shape, with zero internal padding."""
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    for index, (text, style) in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = align
        run = paragraph.add_run()
        run.text = text
        run.font.name = style.get("font", BODY_FONT)
        run.font.size = Pt(style.get("size", 11))
        run.font.bold = style.get("bold", False)
        run.font.italic = style.get("italic", False)
        run.font.color.rgb = style.get("color", WHITE)


def _text(slide, x, y, w, h, runs, *, align=PP_ALIGN.LEFT, spacing=None):
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    for index, (text, style) in enumerate(runs):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = style.get("align", align)
        if spacing is not None:
            paragraph.line_spacing = spacing
        if style.get("space_before"):
            paragraph.space_before = Pt(style["space_before"])
        run = paragraph.add_run()
        run.text = text
        run.font.name = style.get("font", BODY_FONT)
        run.font.size = Pt(style.get("size", 13))
        run.font.bold = style.get("bold", False)
        run.font.italic = style.get("italic", False)
        run.font.color.rgb = style.get("color", INK)
    return box


def _arrow(slide, x1, y1, x2, y2, colour=TEAL, width=1.75):
    connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    connector.line.color.rgb = colour
    connector.line.width = Pt(width)
    return connector


def pipeline_slide(presentation) -> None:
    """Left-to-right flow of one decision through the scorer."""
    slide = _blank(presentation)
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, CLOUD)
    _rect(slide, 0, 0, Inches(0.28), SLIDE_H, TEAL)

    _text(
        slide,
        Inches(0.85),
        Inches(0.42),
        Inches(11.5),
        Inches(0.62),
        [("How it works", {"font": HEAD_FONT, "size": 36, "bold": True, "color": MIDNIGHT})],
    )
    _text(
        slide,
        Inches(0.85),
        Inches(1.08),
        Inches(11.5),
        Inches(0.32),
        [(
            "One decision, N options \u2192 N premise/hypothesis pairs \u2192 one batched forward pass \u2192 softmax \u2192 gate.",
            {"size": 14, "italic": True, "color": MUTED},
        )],
    )

    # --- Stage 1: inputs (three stacked sources) --------------------------
    inputs = [
        ("state JSON", "the facts", 1.62),
        ("question", "what to decide", 2.42),
        ("option descriptions", "one per candidate", 3.22),
    ]
    for title, subtitle, top in inputs:
        box = _rect(slide, Inches(0.85), Inches(top), Inches(2.35), Inches(0.66), WHITE, line=DEEP)
        _label(
            box,
            [
                (title, {"size": 11.5, "bold": True, "color": DEEP}),
                (subtitle, {"size": 9, "italic": True, "color": MUTED}),
            ],
        )

    # --- Stage 2: pair construction --------------------------------------
    pair = _rect(slide, Inches(3.75), Inches(1.95), Inches(2.15), Inches(1.6), DEEP)
    _label(
        pair,
        [
            ("PAIR BUILDER", {"size": 10.5, "bold": True, "color": CODE_KEY}),
            ("premise = state + question", {"font": MONO_FONT, "size": 8.5, "color": WHITE}),
            ("hypothesis = one per option", {"font": MONO_FONT, "size": 8.5, "color": WHITE}),
        ],
    )
    for _, _, top in inputs:
        _arrow(slide, Inches(3.2), Inches(top + 0.33), Inches(3.75), Inches(2.75))

    # --- Stage 3: the model ----------------------------------------------
    model = _rect(slide, Inches(6.45), Inches(1.95), Inches(2.35), Inches(1.6), MIDNIGHT)
    _label(
        model,
        [
            ("ModernBERT-large", {"size": 12, "bold": True, "color": WHITE}),
            ("zeroshot-v2.0", {"size": 9.5, "italic": True, "color": CODE_KEY}),
            ("NLI head \u00b7 395M params", {"size": 9, "color": RGBColor(0xA8, 0xBC, 0xCC)}),
            ("local \u00b7 offline \u00b7 MPS", {"font": MONO_FONT, "size": 8.5, "color": TEAL}),
        ],
    )
    _arrow(slide, Inches(5.9), Inches(2.75), Inches(6.45), Inches(2.75))

    # --- Stage 4: logits -> softmax --------------------------------------
    softmax = _rect(slide, Inches(9.35), Inches(1.95), Inches(1.95), Inches(1.6), TEAL)
    _label(
        softmax,
        [
            ("SOFTMAX", {"size": 11, "bold": True, "color": WHITE}),
            ("across options", {"size": 9, "italic": True, "color": RGBColor(0xD5, 0xE8, 0xF0)}),
            ("\u03a3 p = 1.0", {"font": MONO_FONT, "size": 9.5, "color": WHITE}),
        ],
    )
    _arrow(slide, Inches(8.8), Inches(2.75), Inches(9.35), Inches(2.75))
    _text(
        slide,
        Inches(8.72),
        Inches(1.6),
        Inches(2.9),
        Inches(0.3),
        [("entailment logit \u00d7 N", {"font": MONO_FONT, "size": 9, "color": MUTED})],
    )

    # --- Stage 5: the gate, with both outcomes ---------------------------
    gate = _rect(slide, Inches(11.55), Inches(1.98), Inches(1.5), Inches(1.55), WHITE, shape=MSO_SHAPE.DIAMOND, line=WARN)
    _label(
        gate,
        [
            ("GATE", {"size": 10, "bold": True, "color": WARN}),
            ("\u22650.65", {"font": MONO_FONT, "size": 8.5, "color": INK}),
            ("\u22650.15", {"font": MONO_FONT, "size": 8.5, "color": INK}),
        ],
    )
    _arrow(slide, Inches(11.3), Inches(2.75), Inches(11.55), Inches(2.75))

    answered = _rect(slide, Inches(10.05), Inches(4.02), Inches(3.0), Inches(0.62), PASS)
    _label(answered, [("answer returned  (5/12)", {"size": 11, "bold": True, "color": WHITE})])
    _arrow(slide, Inches(12.3), Inches(3.53), Inches(11.55), Inches(4.02), PASS)

    abstain = _rect(slide, Inches(10.05), Inches(4.85), Inches(3.0), Inches(0.62), WARN)
    _label(abstain, [("abstain \u2192 review  (7/12)", {"size": 11, "bold": True, "color": WHITE})])
    _arrow(slide, Inches(12.3), Inches(3.53), Inches(12.3), Inches(4.85), WARN)

    # --- Mermaid source, so the diagram is reproducible elsewhere --------
    _rect(slide, Inches(0.85), Inches(4.15), Inches(8.85), Inches(2.6), CODE_BG)
    _text(
        slide,
        Inches(1.05),
        Inches(4.28),
        Inches(8.4),
        Inches(0.26),
        [("EQUIVALENT MERMAID SOURCE", {"size": 9.5, "bold": True, "color": CODE_KEY})],
    )
    _text(
        slide,
        Inches(1.05),
        Inches(4.6),
        Inches(8.45),
        Inches(2.0),
        [(MERMAID_SOURCE, {"font": MONO_FONT, "size": 8, "color": CODE_FG})],
        spacing=1.08,
    )

    _text(
        slide,
        Inches(0.85),
        Inches(6.92),
        Inches(11.6),
        Inches(0.3),
        [(
            "The model never generates text \u2014 it only scores entailment, so it cannot invent an option that was not offered.",
            {"size": 11.5, "italic": True, "bold": True, "color": DEEP},
        )],
    )


def _code_slide(presentation, title: str, subtitle: str, blocks: list[tuple[str, str, list[str]]]) -> None:
    """Render one appendix slide: heading plus up to two annotated code blocks.

    `blocks` entries are (label, why_it_matters, code_lines). Comment lines are
    tinted differently from code so the annotation reads as annotation.
    """
    slide = _blank(presentation)
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, CLOUD)
    _rect(slide, 0, 0, Inches(0.28), SLIDE_H, TEAL)

    _text(
        slide,
        Inches(0.85),
        Inches(0.4),
        Inches(11.5),
        Inches(0.55),
        [(title, {"font": HEAD_FONT, "size": 30, "bold": True, "color": MIDNIGHT})],
    )
    _text(
        slide,
        Inches(0.85),
        Inches(1.0),
        Inches(11.5),
        Inches(0.3),
        [(subtitle, {"size": 13, "italic": True, "color": MUTED})],
    )

    top = 1.5
    width = 11.6 if len(blocks) == 1 else 5.68
    for index, (label, why, lines) in enumerate(blocks):
        left = 0.85 if index == 0 else 6.77
        block_top = top if len(blocks) <= 2 else top + index * 2.6
        if len(blocks) == 1:
            left, block_top = 0.85, top

        height = 4.55 if len(blocks) == 1 else 4.55
        _rect(slide, Inches(left), Inches(block_top), Inches(width), Inches(0.38), DEEP)
        _text(
            slide,
            Inches(left + 0.15),
            Inches(block_top + 0.07),
            Inches(width - 0.3),
            Inches(0.26),
            [(label, {"font": MONO_FONT, "size": 10.5, "bold": True, "color": WHITE})],
        )
        _rect(slide, Inches(left), Inches(block_top + 0.38), Inches(width), Inches(height), CODE_BG)

        runs = []
        for line in lines:
            stripped = line.strip()
            colour = CODE_COMMENT if stripped.startswith("#") else CODE_FG
            runs.append((line if line else " ", {"font": MONO_FONT, "size": 8.5, "color": colour}))
        _text(
            slide,
            Inches(left + 0.18),
            Inches(block_top + 0.52),
            Inches(width - 0.36),
            Inches(height - 0.28),
            runs,
            spacing=1.1,
        )

        _text(
            slide,
            Inches(left),
            Inches(block_top + height + 0.46),
            Inches(width),
            Inches(0.55),
            [(why, {"size": 11, "italic": True, "color": DEEP})],
            spacing=1.1,
        )


def appendix_slides(presentation) -> None:
    """Three annotated code slides covering the full path of one decision."""

    # --- A1: how the prompt pair is constructed ---------------------------
    _code_slide(
        presentation,
        "Appendix A1 \u00b7 Building the premise / hypothesis pairs",
        "poc/zero_shot_decision_poc.py \u2014 _build_comparisons()  \u00b7  this is the entire \"prompt\"",
        [
            (
                "premise \u2014 identical for every option",
                "Sorting keys makes the premise deterministic: the same state always "
                "produces the same string, so scores are reproducible run to run.",
                [
                    "# The state is serialised ONCE and reused for every option, so the",
                    "# only thing that varies across candidates is the hypothesis.",
                    "state_text = json.dumps(",
                    "    request.state,",
                    "    sort_keys=True,        # deterministic -> reproducible scores",
                    "    ensure_ascii=False,",
                    "    separators=(\",\", \":\"),  # compact: fewer tokens per pair",
                    ")",
                    "",
                    "premise = (",
                    "    f\"State evidence:\\n{state_text}\\n\\n\"",
                    "    f\"Decision question:\\n{decision.question}\"",
                    ")",
                ],
            ),
            (
                "hypothesis \u2014 one per candidate option",
                "The option DESCRIPTION carries the semantics, not the id. A bare label "
                "like 'positive' gives the NLI head almost nothing to entail against.",
                [
                    "for candidate in decision.candidates:",
                    "    noun = \"option\" if decision.kind == \"choice\" else \"score level\"",
                    "    comparisons.append(",
                    "        Comparison(",
                    "            decision_id=decision.identifier,",
                    "            candidate_id=candidate.identifier,",
                    "            premise=premise,",
                    "            # Asserted as TRUE on purpose: the NLI head is asked",
                    "            # 'does the premise entail this claim?' -- so each option",
                    "            # is phrased as a positive statement to be tested.",
                    "            hypothesis=(",
                    "                f\"The correct {noun} is '{candidate.identifier}'. \"",
                    "                f\"Definition: {candidate.description}\"",
                    "            ),",
                    "            numeric_value=candidate.numeric_value,",
                    "        )",
                    "    )",
                ],
            ),
        ],
    )

    # --- A2: the forward pass --------------------------------------------
    _code_slide(
        presentation,
        "Appendix A2 \u00b7 The forward pass",
        "poc/zero_shot_decision_poc.py \u2014 TransformersNliScorer.score()  \u00b7  no text generation anywhere",
        [
            (
                "batched inference over all pairs",
                "All pairs for a decision go through together, so cost scales with "
                "batches rather than with options. inference_mode() disables autograd "
                "bookkeeping \u2014 measurably faster and lower-memory than no_grad().",
                [
                    "for start in range(0, len(comparisons), self._batch_size):",
                    "    chunk = comparisons[start:start + self._batch_size]",
                    "",
                    "    # Premises and hypotheses are passed as TWO lists -- the",
                    "    # tokenizer joins each pair with [SEP], which is the input",
                    "    # format an NLI cross-encoder is trained on.",
                    "    encoded = self._tokenizer(",
                    "        [c.premise for c in chunk],",
                    "        [c.hypothesis for c in chunk],",
                    "        padding=True, truncation=True, return_tensors=\"pt\",",
                    "    )",
                    "    encoded = {k: v.to(self._device) for k, v in encoded.items()}",
                    "",
                    "    with self._torch.inference_mode():   # no autograd graph",
                    "        logits = self._model(**encoded).logits",
                    "        probabilities = self._torch.softmax(logits, dim=-1)",
                ],
            ),
            (
                "reading the entailment channel",
                "_entailment_index is resolved from config.label2id rather than "
                "hardcoded, so a model with reversed label order still works. Both the "
                "logit and the per-pair probability are kept.",
                [
                    "for row_logits, row_probabilities in zip(",
                    "    logits, probabilities, strict=True   # length mismatch = bug",
                    "):",
                    "    evidence.append(",
                    "        NliEvidence(",
                    "            # Index comes from config.label2id, NOT a constant:",
                    "            # label order differs between NLI checkpoints.",
                    "            entailment_logit=float(",
                    "                row_logits[self._entailment_index].item()",
                    "            ),",
                    "            entailment_probability=float(",
                    "                row_probabilities[self._entailment_index].item()",
                    "            ),",
                    "        )",
                    "    )",
                    "",
                    "# Device selection: cuda -> mps (Apple GPU) -> cpu",
                    "return evidence",
                ],
            ),
        ],
    )

    # --- A3: turning scores into a decision ------------------------------
    _code_slide(
        presentation,
        "Appendix A3 \u00b7 From logits to a decision",
        "poc/zero_shot_decision_poc.py \u2014 softmax across options, then the abstention gate",
        [
            (
                "cross-option softmax",
                "This is what makes confidence depend on option COUNT: mass is shared "
                "across candidates, so a 3-way 0.44 and a 2-way 0.79 can be equally "
                "strong evidence.",
                [
                    "def _softmax(logits: Sequence[float]) -> list[float]:",
                    "    # Subtract the max before exp() -- standard guard against",
                    "    # overflow on large positive logits.",
                    "    maximum = max(logits)",
                    "    exponentials = [math.exp(logit - maximum) for logit in logits]",
                    "    total = sum(exponentials)",
                    "    return [value / total for value in exponentials]",
                    "",
                    "# NOTE: applied ACROSS the options of one decision, not across",
                    "# the model's own entailment/not_entailment axis. That is what",
                    "# turns N independent entailment scores into one distribution.",
                ],
            ),
            (
                "the abstention gate",
                "Two independent conditions. Confidence alone would pass a 0.66 vs 0.34 "
                "coin flip; margin alone would pass 0.20 vs 0.05. Requiring both is what "
                "makes 'no answer' a deliberate outcome rather than a failure.",
                [
                    "# A correct-but-unconfident pick is still not safe to act on,",
                    "# so the answer is withheld unless BOTH gates clear.",
                    "top_probability = probabilities[0]",
                    "top_two_margin = probabilities[0] - probabilities[1]",
                    "",
                    "review_required = (",
                    "    top_probability < decision.minimum_probability   # 0.65",
                    "    or top_two_margin < decision.minimum_margin      # 0.15",
                    ")",
                    "",
                    "# 'answer' is None when gated; 'recommended_option' always",
                    "# holds the top-ranked candidate, so the caller can show a",
                    "# suggestion to a reviewer without it reading as a decision.",
                    "return {",
                    "    \"answer\": None if review_required else best.candidate_id,",
                    "    \"recommended_option\": best.candidate_id,",
                    "    \"review_required\": review_required,",
                    "}",
                ],
            ),
        ],
    )
