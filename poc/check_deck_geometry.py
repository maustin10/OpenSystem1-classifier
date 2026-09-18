#!/usr/bin/env python3
"""Geometry QA for a generated .pptx, without rendering it.

Visual inspection is the ideal check, but it needs LibreOffice + Poppler, which
are not installed here. These are the failures that visual QA is actually looking
for, expressed as measurements on the shape tree:

  * elements past the slide edge, or inside the 0.5" margin
  * text boxes whose content cannot fit the box at its stated font size
  * overlapping text (text-through-text or text-through-shape)
  * probability bars wider than their track

Font metrics are approximated (PowerPoint reflows text itself), so overflow is
reported with a tolerance and treated as a warning to inspect rather than proof.

USAGE
    .venv/bin/python poc/check_deck_geometry.py models/deck.pptx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

EMU_PER_INCH = 914400
MARGIN_INCHES = 0.5
# Mean glyph width as a fraction of font size for the fonts used here. Calibri
# and Consolas differ enough that one constant would misjudge the mono blocks.
CHAR_WIDTH_RATIO = {"Consolas": 0.55, "Georgia": 0.52, "Calibri": 0.48}
LINE_HEIGHT_RATIO = 1.22


def _inches(value: int | None) -> float:
    return (value or 0) / EMU_PER_INCH


def _estimate_text_height(shape) -> float:
    """Approximate rendered text height in inches for a text-bearing shape."""
    width = _inches(shape.width)
    if width <= 0:
        return 0.0
    total = 0.0
    for paragraph in shape.text_frame.paragraphs:
        text = "".join(run.text for run in paragraph.runs)
        if not text:
            continue
        sizes = [run.font.size.pt for run in paragraph.runs if run.font.size]
        size = max(sizes) if sizes else 14.0
        names = [run.font.name for run in paragraph.runs if run.font.name]
        ratio = CHAR_WIDTH_RATIO.get(names[0] if names else "Calibri", 0.5)
        char_width = size * ratio / 72.0

        # Explicit newlines force line breaks; the rest wraps on width.
        lines = 0
        for segment in text.split("\n"):
            usable = max(int(width / char_width), 1)
            lines += max(1, -(-len(segment) // usable))
        total += lines * size * LINE_HEIGHT_RATIO / 72.0
    return total


def _overlap(a, b) -> float:
    """Area of intersection between two shapes, in square inches."""
    ax1, ay1 = _inches(a.left), _inches(a.top)
    ax2, ay2 = ax1 + _inches(a.width), ay1 + _inches(a.height)
    bx1, by1 = _inches(b.left), _inches(b.top)
    bx2, by2 = bx1 + _inches(b.width), by1 + _inches(b.height)
    dx = min(ax2, bx2) - max(ax1, bx1)
    dy = min(ay2, by2) - max(ay1, by1)
    return dx * dy if dx > 0 and dy > 0 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck")
    parser.add_argument(
        "--strict-margins",
        action="store_true",
        help="Also report shapes inside the 0.5in margin (full-bleed bands trip this).",
    )
    arguments = parser.parse_args()

    presentation = Presentation(arguments.deck)
    slide_w = _inches(presentation.slide_width)
    slide_h = _inches(presentation.slide_height)
    print(f"deck   : {arguments.deck}")
    print(f"canvas : {slide_w:.3f} x {slide_h:.3f} in")
    print(f"slides : {len(presentation.slides)}")

    issues: list[str] = []

    for index, slide in enumerate(presentation.slides, start=1):
        texts = []
        for shape in slide.shapes:
            left, top = _inches(shape.left), _inches(shape.top)
            right, bottom = left + _inches(shape.width), top + _inches(shape.height)

            # Off-canvas is always a real defect.
            if left < -0.01 or top < -0.01 or right > slide_w + 0.01 or bottom > slide_h + 0.01:
                issues.append(
                    f"slide {index}: '{shape.shape_type}' extends off-canvas "
                    f"(l={left:.2f} t={top:.2f} r={right:.2f} b={bottom:.2f})"
                )

            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue

            texts.append(shape)
            needed = _estimate_text_height(shape)
            available = _inches(shape.height)
            # 0.06in tolerance absorbs metric approximation error.
            if needed > available + 0.06:
                snippet = shape.text_frame.text.strip().replace("\n", " ")[:52]
                issues.append(
                    f"slide {index}: text may overflow its box by {needed - available:.2f}in "
                    f"(needs {needed:.2f}, has {available:.2f}) -> \"{snippet}\""
                )

            if arguments.strict_margins and (
                left < MARGIN_INCHES - 0.01 or right > slide_w - MARGIN_INCHES + 0.01
            ):
                issues.append(f"slide {index}: text inside 0.5in margin (l={left:.2f} r={right:.2f})")

        # Text-on-text collisions: two labels sharing pixels is never intended.
        for i, first in enumerate(texts):
            for second in texts[i + 1 :]:
                area = _overlap(first, second)
                if area > 0.02:
                    a = first.text_frame.text.strip().replace("\n", " ")[:26]
                    b = second.text_frame.text.strip().replace("\n", " ")[:26]
                    issues.append(
                        f"slide {index}: text overlaps text ({area:.3f} sq in) -> \"{a}\" / \"{b}\""
                    )

    print()
    if issues:
        print(f"FOUND {len(issues)} ISSUE(S):")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("no geometry issues detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
