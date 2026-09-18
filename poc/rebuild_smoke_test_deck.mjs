/*
Content summary: Reorders the existing comparison deck into a smoke-test story,
adds gate-clearance distribution statistics, adds every tool-routing result, and
keeps implementation/API code in a final appendix.

Design description: Retains the source deck's 16:9 Ocean Gradient palette,
Georgia display headings, Calibri body text, Consolas code, teal spine, editable
native charts, and native tables. Results use flat chart-led layouts; architecture
and appendix slides preserve the existing visual language.
*/
import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";

const artifactToolPath = "/Users/markaustin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";
const { FileBlob, PresentationFile } = await import(pathToFileURL(artifactToolPath).href);

const workspaceDir = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const sourcePath = path.join(workspaceDir, "results/OpenSystem1-classifier-comparison-stage1.pptx");
const simpleModernPath = path.join(workspaceDir, "results/benchmark-results.json");
const simpleTypeSafePath = path.join(workspaceDir, "results/typesafe-benchmark-results.json");
const toolModernPath = path.join(workspaceDir, "results/bfcl-routing-modernbert-results.json");
const toolTypeSafePath = path.join(workspaceDir, "results/bfcl-routing-typesafe-results.json");
const finalPath = path.join(workspaceDir, "results/Smoke-Test-Comparison-System1-vs-ModernBERT-final.pptx");
const buildDir = path.join(workspaceDir, ".codex-deck-build/smoke-test-rebuild");
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
const skillDir = "/Users/markaustin/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const runtimePython = "/Users/markaustin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const { finalizePresentation, applyPresentationChartFont } = await import(
  pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href,
);

const simpleModern = JSON.parse(await fs.readFile(simpleModernPath, "utf8"));
const simpleTypeSafe = JSON.parse(await fs.readFile(simpleTypeSafePath, "utf8"));
const toolModern = JSON.parse(await fs.readFile(toolModernPath, "utf8"));
const toolTypeSafe = JSON.parse(await fs.readFile(toolTypeSafePath, "utf8"));
const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
if (presentation.slides.items.length !== 27) {
  throw new Error(`Expected 27 source slides, found ${presentation.slides.items.length}`);
}

const C = {
  deep: "#065A82", teal: "#1C7293", typeSafe: "#815AC0", typeSafeLight: "#D8CBEF",
  midnight: "#21295C", cloud: "#F4F7F9", border: "#D5DFE6", track: "#DDE4EA",
  ink: "#1A1F2B", muted: "#6B7A8C", white: "#FFFFFF", pass: "#1E7A4B",
  warn: "#B86E00", fail: "#A33A3A", paleBlue: "#E9F2F6", palePurple: "#F1ECFA",
};
const FONT = { head: "Georgia", body: "Calibri", mono: "Consolas" };
const W = 1280;
const H = 720;
const MIN_PROBABILITY = 0.65;
const MIN_MARGIN = 0.15;

function rect(slide, left, top, width, height, fill, options = {}) {
  return slide.shapes.add({
    geometry: options.geometry ?? "rect",
    position: { left, top, width, height },
    fill,
    line: options.line ?? { fill: "none", width: 0 },
    shadow: options.shadow ?? "shadow-none",
    name: options.name,
  });
}

function textBox(slide, text, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { fill: "none", width: 0 },
    name: options.name,
  });
  shape.text = String(text);
  shape.text.style = {
    typeface: options.typeface ?? FONT.body,
    fontSize: options.fontSize ?? 18,
    bold: options.bold ?? false,
    italic: options.italic ?? false,
    color: options.color ?? C.ink,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "top",
    autoFit: options.autoFit ?? "none",
    wrap: options.wrap ?? "square",
    lineSpacing: options.lineSpacing,
    insets: options.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
  };
  return shape;
}

function baseSlide(slide, dark = false) {
  slide.shapes.deleteAll();
  rect(slide, 0, 0, W, H, dark ? C.midnight : C.cloud, { name: "background" });
  rect(slide, 0, 0, 27, H, C.teal, { name: "brand-spine" });
}

function chartBase() {
  return {
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { typeface: FONT.body, fontSize: 12.5, fill: C.ink } },
    xAxis: { visible: true, textStyle: { typeface: FONT.body, fontSize: 12.5, fill: C.ink }, line: { style: "solid", fill: C.border, width: 1 } },
    chartFill: "none", chartLine: { fill: "none", width: 0 }, plotAreaFill: "none", plotAreaLine: { fill: "none", width: 0 },
  };
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function clearanceStats(rows, probabilityField) {
  const values = rows.map((row) => Math.min(
    Number(row[probabilityField]) - MIN_PROBABILITY,
    Number(row.margin) - MIN_MARGIN,
  ));
  return {
    minimum: Math.min(...values),
    median: median(values),
    average: values.reduce((sum, value) => sum + value, 0) / values.length,
  };
}

function replaceText(slide, oldText, newText) {
  for (const shape of slide.shapes.items) {
    if (!shape.text) continue;
    const current = String(shape.text);
    if (current.includes(oldText)) shape.text.replace(oldText, newText);
  }
}

function addCover(slide) {
  baseSlide(slide, true);
  textBox(slide, "OPENSYSTEM1 CLASSIFIER BENCHMARK", 96, 102, 1040, 30, {
    fontSize: 17, bold: true, color: "#8FC7DC",
  });
  textBox(
    slide,
    'Smoke Test Comparison of TypeSafe.ai\n"System1" Classifier vs. Traditional\nOpenSystem1 ModernBERT classifier',
    96, 165, 1080, 260,
    { typeface: FONT.head, fontSize: 42, bold: true, color: C.white, lineSpacing: 0.96 },
  );
  textBox(slide, "Simple multiple-choice classification and tool calling", 96, 475, 980, 34, {
    fontSize: 20, italic: true, color: "#C2D6E2",
  });
  rect(slide, 96, 550, 990, 2, C.teal);
  textBox(slide, "12 simple choices", 96, 580, 260, 31, { fontSize: 18, bold: true, color: C.teal });
  textBox(slide, "30 tool routes", 390, 580, 260, 31, { fontSize: 18, bold: true, color: C.typeSafeLight });
  textBox(slide, "Prepared by Mark Austin", 865, 650, 315, 28, { fontSize: 15, bold: true, color: "#C2D6E2", alignment: "right" });
  slide.speakerNotes.textFrame.setText("Title and framing requested by Mark Austin. Results come from the committed benchmark JSON files.");
}

function addComparisonSlide(slide, config) {
  for (const chart of [...slide.charts.items]) slide.charts.deleteById(chart.id);
  baseSlide(slide);
  textBox(slide, config.title, 82, 40, 1098, 52, {
    typeface: FONT.head, fontSize: 38, bold: true, color: C.midnight,
  });
  textBox(slide, config.subtitle, 82, 96, 1098, 28, {
    fontSize: 17, italic: true, color: C.muted,
  });

  textBox(slide, "CLASSIFICATION ACCURACY", 82, 143, 475, 22, { fontSize: 13, bold: true, color: C.deep });
  const accuracyChart = slide.charts.add("bar", {
    ...chartBase(),
    position: { left: 70, top: 171, width: 505, height: 405 },
    categories: config.accuracyCategories,
    series: [
      { name: "ModernBERT NLI", values: config.modernAccuracy, valuesFormatCode: "0%", fill: C.deep, line: { style: "solid", fill: C.deep, width: 1 } },
      { name: 'TypeSafe.ai "System1"', values: config.typeSafeAccuracy, valuesFormatCode: "0%", fill: C.typeSafe, line: { style: "solid", fill: C.typeSafe, width: 1 } },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 70 },
    yAxis: { visible: true, min: 0, max: 1, majorUnit: 0.25, numberFormatCode: "0%", textStyle: { typeface: FONT.body, fontSize: 11.5, fill: C.muted }, line: { style: "solid", fill: C.border, width: 1 }, majorGridlines: { style: "solid", fill: C.border, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: FONT.body, fontSize: 13, bold: true, fill: C.ink } },
  });
  applyPresentationChartFont(accuracyChart, { fontFamily: FONT.body });

  textBox(slide, "GATE CLEARANCE DISTANCE", 625, 143, 555, 22, { fontSize: 13, bold: true, color: C.warn });
  const gateChart = slide.charts.add("bar", {
    ...chartBase(),
    position: { left: 608, top: 171, width: 592, height: 405 },
    categories: ["Minimum", "Median", "Average"],
    series: [
      { name: "ModernBERT NLI", values: [config.modernClearance.minimum, config.modernClearance.median, config.modernClearance.average], valuesFormatCode: "+0%;-0%;0%", fill: C.deep, line: { style: "solid", fill: C.deep, width: 1 } },
      { name: 'TypeSafe.ai "System1"', values: [config.typeSafeClearance.minimum, config.typeSafeClearance.median, config.typeSafeClearance.average], valuesFormatCode: "+0%;-0%;0%", fill: C.typeSafe, line: { style: "solid", fill: C.typeSafe, width: 1 } },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 65 },
    xAxis: { visible: true, tickLabelPosition: "low", textStyle: { typeface: FONT.body, fontSize: 12.5, fill: C.ink }, line: { style: "solid", fill: C.border, width: 1 } },
    yAxis: { visible: true, min: -0.4, max: 0.4, majorUnit: 0.1, numberFormatCode: "+0%;-0%;0%", textStyle: { typeface: FONT.body, fontSize: 11.5, fill: C.muted }, line: { style: "solid", fill: C.border, width: 1 }, majorGridlines: { style: "solid", fill: C.border, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: FONT.body, fontSize: 12, bold: true, fill: C.ink } },
  });
  applyPresentationChartFont(gateChart, { fontFamily: FONT.body });

  rect(slide, 82, 610, 1098, 45, C.midnight);
  textBox(slide, "Clearance = minimum of (top probability − 65 points) and (top-two margin − 15 points)", 102, 621, 1058, 21, { fontSize: 14.5, bold: true, color: C.white, alignment: "center" });
  textBox(slide, "Positive values clear both gate conditions. Negative values show the shortfall on the limiting condition.", 82, 672, 1098, 21, { fontSize: 12.5, italic: true, color: C.muted, alignment: "center" });
  slide.speakerNotes.textFrame.setText(config.notes);
}

function addFindingsSlide(slide) {
  baseSlide(slide);
  textBox(slide, "Correct score and gate clearance by use case", 82, 42, 1098, 52, {
    typeface: FONT.head, fontSize: 38, bold: true, color: C.midnight,
  });
  textBox(slide, "Correct uses the most likely option. Gate statistics are signed percentage points from the limiting threshold.", 82, 98, 1098, 28, {
    fontSize: 17, italic: true, color: C.muted,
  });

  const modernToolSelection = toolModern.cases.filter((row) => row.category === "multiple");
  const typeSafeToolSelection = toolTypeSafe.cases.filter((row) => row.category === "multiple");
  const modernNoTool = toolModern.cases.filter((row) => row.category === "irrelevance");
  const typeSafeNoTool = toolTypeSafe.cases.filter((row) => row.category === "irrelevance");
  const fmtCorrect = (rows) => {
    const correct = rows.filter((row) => row.correct).length;
    return `${correct}/${rows.length} (${(100 * correct / rows.length).toFixed(correct === rows.length ? 0 : 1)}%)`;
  };
  const fmtStats = (stats) => [stats.minimum, stats.median, stats.average]
    .map((value) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}`)
    .join(" / ");
  const categoryRows = [
    ["Simple multiple choice", simpleModern.cases, "confidence", simpleTypeSafe.cases, "top_probability"],
    ["Tool selection", modernToolSelection, "top_probability", typeSafeToolSelection, "top_probability"],
    ["No-tool detection", modernNoTool, "top_probability", typeSafeNoTool, "top_probability"],
    ["All tool routes", toolModern.cases, "top_probability", toolTypeSafe.cases, "top_probability"],
  ];
  const values = [["Use case", "n", "ModernBERT correct", "ModernBERT clearance\nmin / median / avg", "TypeSafe correct", "TypeSafe clearance\nmin / median / avg"]];
  for (const [label, modernRows, modernField, typeSafeRows, typeSafeField] of categoryRows) {
    values.push([
      label,
      String(modernRows.length),
      fmtCorrect(modernRows),
      fmtStats(clearanceStats(modernRows, modernField)),
      fmtCorrect(typeSafeRows),
      fmtStats(clearanceStats(typeSafeRows, typeSafeField)),
    ]);
  }
  const table = slide.tables.add({
    rows: values.length, columns: 6, left: 82, top: 158, width: 1098, height: 338,
    columnWidths: [224, 55, 155, 245, 155, 264], values,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: C.border, width: 0.5 });
  table.rows[0].height = 58;
  for (let row = 1; row < values.length; row += 1) table.rows[row].height = 68;
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 6 }).assign({ fill: C.midnight, textStyle: { typeface: FONT.body, fontSize: 11.5, bold: true, color: C.white }, anchor: "middle", margins: { left: 8, right: 6, top: 4, bottom: 4 } });
  table.cells.block({ row: 1, column: 0, rowCount: 4, columnCount: 6 }).assign({ textStyle: { typeface: FONT.body, fontSize: 13, color: C.ink }, anchor: "middle", margins: { left: 8, right: 6, top: 4, bottom: 4 } });
  table.cells.block({ row: 1, column: 2, rowCount: 4, columnCount: 2 }).textStyle.color = C.deep;
  table.cells.block({ row: 1, column: 4, rowCount: 4, columnCount: 2 }).textStyle.color = C.typeSafe;

  rect(slide, 82, 532, 1098, 86, C.paleBlue, { line: { style: "solid", fill: C.border, width: 1 } });
  textBox(slide, "Correct score", 105, 550, 165, 20, { fontSize: 13, bold: true, color: C.deep });
  textBox(slide, "Expected option equals the highest-probability option, even when the gate would abstain.", 280, 547, 870, 25, { fontSize: 15, color: C.ink });
  textBox(slide, "Gate caveat", 105, 585, 165, 20, { fontSize: 13, bold: true, color: C.warn });
  textBox(slide, "TypeSafe's one incorrect tool route still had +7.0 points of gate clearance.", 280, 582, 870, 25, { fontSize: 15, color: C.ink });
  textBox(slide, "Clearance statistics are min / median / average in percentage points; positive values clear both fixed conditions.", 82, 654, 1098, 24, { fontSize: 13, bold: true, color: C.midnight, alignment: "center" });
  slide.speakerNotes.textFrame.setText("All figures are computed from the four committed result files. Gate clearance uses the limiting signed distance to the fixed 0.65 probability and 0.15 margin thresholds.");
}

function addProtocolSlide(slide) {
  baseSlide(slide);
  textBox(slide, "Smoke test protocol", 82, 45, 1098, 52, { typeface: FONT.head, fontSize: 40, bold: true, color: C.midnight });
  textBox(slide, "The decision task stays fixed while the scorer changes", 82, 101, 1098, 28, { fontSize: 17, italic: true, color: C.muted });
  rect(slide, 82, 163, 520, 206, C.white, { line: { style: "solid", fill: C.border, width: 1 } });
  textBox(slide, "SIMPLE MULTIPLE-CHOICE CLASSIFICATION", 106, 188, 470, 22, { fontSize: 13, bold: true, color: C.deep });
  textBox(slide, "12 deliberately obvious questions", 106, 230, 470, 32, { fontSize: 23, bold: true, color: C.midnight });
  textBox(slide, "Measures typed option ranking and exposes confidence behavior before harder tests.", 106, 282, 458, 55, { fontSize: 16, color: C.ink });
  rect(slide, 660, 163, 520, 206, C.white, { line: { style: "solid", fill: C.border, width: 1 } });
  textBox(slide, "TOOL CALLING TEST", 684, 188, 470, 22, { fontSize: 13, bold: true, color: C.typeSafe });
  textBox(slide, "30 BFCL-derived routes", 684, 230, 470, 32, { fontSize: 23, bold: true, color: C.midnight });
  textBox(slide, "Measures one-tool selection and no-tool detection. Argument extraction and execution remain out of scope.", 684, 282, 458, 55, { fontSize: 16, color: C.ink });
  textBox(slide, "Shared inputs", 82, 415, 210, 24, { fontSize: 15, bold: true, color: C.deep });
  textBox(slide, "Same state, question, option descriptions, and expected answer for both classifiers", 82, 450, 1098, 32, { fontSize: 19, color: C.ink });
  textBox(slide, "Shared scoring", 82, 520, 210, 24, { fontSize: 15, bold: true, color: C.deep });
  textBox(slide, "Top-ranked accuracy plus signed clearance from the fixed probability and margin gate", 82, 555, 1098, 32, { fontSize: 19, color: C.ink });
  rect(slide, 82, 626, 1098, 45, C.midnight);
  textBox(slide, "Probability threshold 0.65     Margin threshold 0.15", 102, 638, 1058, 21, { fontSize: 16, bold: true, color: C.white, alignment: "center" });
  slide.speakerNotes.textFrame.setText("The tool routing subset is derived from BFCL V4 at commit 6ea57973c7a6097fd7c5915698c54c17c5b1b6c8.");
}

function compactRoute(row, optionId, expected = false) {
  if (optionId === "no_tool" || (expected && !row.expected_tool_name)) return "no tool";
  if (expected) return row.expected_tool_name ?? optionId;
  return row.tool_names?.[optionId] ?? row.picked_tool_name ?? optionId;
}

function addToolResultsSlide(slide, pairs, first, last) {
  baseSlide(slide);
  textBox(slide, `Tool calling results ${first + 1}–${last}`, 82, 42, 1098, 52, { typeface: FONT.head, fontSize: 38, bold: true, color: C.midnight });
  textBox(slide, "Top-ranked route for every BFCL-derived case", 82, 98, 1098, 27, { fontSize: 17, italic: true, color: C.muted });
  const rows = pairs.slice(first, last);
  const values = [["Case", "Expected route", "ModernBERT route", "p / margin", "TypeSafe route", "p / margin", "Correct"]];
  for (const { modern, typeSafe } of rows) {
    values.push([
      modern.source_id,
      compactRoute(modern, modern.expected, true),
      compactRoute(modern, modern.picked),
      `${Number(modern.top_probability).toFixed(3)} / ${Number(modern.margin).toFixed(3)}`,
      compactRoute(typeSafe, typeSafe.picked),
      `${Number(typeSafe.top_probability).toFixed(3)} / ${Number(typeSafe.margin).toFixed(3)}`,
      `${modern.correct ? "yes" : "no"} / ${typeSafe.correct ? "yes" : "no"}`,
    ]);
  }
  const table = slide.tables.add({
    rows: values.length, columns: 7, left: 82, top: 148, width: 1098, height: 492,
    columnWidths: [128, 220, 220, 120, 220, 120, 90], values,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: C.border, width: 0.5 });
  table.rows[0].height = 34;
  for (let row = 1; row < values.length; row += 1) table.rows[row].height = 30.5;
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 7 }).assign({ fill: C.midnight, textStyle: { typeface: FONT.body, fontSize: 11.5, bold: true, color: C.white }, anchor: "middle", margins: { left: 6, right: 5, top: 3, bottom: 3 } });
  table.cells.block({ row: 1, column: 0, rowCount: rows.length, columnCount: 7 }).assign({ textStyle: { typeface: FONT.body, fontSize: 10.5, color: C.ink }, anchor: "middle", margins: { left: 6, right: 5, top: 2, bottom: 2 } });
  table.cells.block({ row: 1, column: 2, rowCount: rows.length, columnCount: 1 }).textStyle.color = C.deep;
  table.cells.block({ row: 1, column: 4, rowCount: rows.length, columnCount: 1 }).textStyle.color = C.typeSafe;
  rows.forEach(({ modern, typeSafe }, index) => {
    const row = index + 1;
    table.getCell(row, 6).text.color = modern.correct && typeSafe.correct ? C.pass : C.fail;
    table.getCell(row, 6).text.bold = true;
  });
  textBox(slide, "Correct column reports ModernBERT / TypeSafe. Full schemas and probability distributions remain in the JSON artifacts.", 82, 661, 1098, 22, { fontSize: 12.5, italic: true, color: C.muted, alignment: "center" });
  slide.speakerNotes.textFrame.setText("Sources: results/bfcl-routing-modernbert-results.json and results/bfcl-routing-typesafe-results.json.");
}

function addApiAppendixSlide(slide) {
  baseSlide(slide);
  textBox(slide, "Appendix C · Calling both classifiers", 82, 42, 1098, 52, { typeface: FONT.head, fontSize: 38, bold: true, color: C.midnight });
  textBox(slide, "Python entry points for the simple classification and tool calling tests", 82, 98, 1098, 27, { fontSize: 17, italic: true, color: C.muted });
  rect(slide, 82, 150, 530, 482, "#1D2638");
  textBox(slide, "MODERNBERT · LOCAL", 104, 171, 486, 22, { fontSize: 13, bold: true, color: "#8FC7DC" });
  const modernCode = [
    "from zero_shot_decision_poc import (",
    "    TransformersNliScorer, evaluate, parse_request",
    ")",
    "scorer = TransformersNliScorer(MODEL_PATH)",
    "result = evaluate(parse_request(payload), scorer)",
    "",
    "# Simple multiple-choice smoke test",
    "python poc/obvious_answers_benchmark.py \\",
    "  --model models/modernbert-zeroshot --json",
    "",
    "# Tool calling routing test",
    "python poc/bfcl_routing_benchmark.py \\",
    "  --backend modernbert \\",
    "  --dataset data/bfcl-routing-subset.json \\",
    "  --model models/modernbert-zeroshot --output out.json",
  ].join("\n");
  textBox(slide, modernCode, 104, 211, 486, 395, { typeface: FONT.mono, fontSize: 11.2, color: "#E8EDF3", lineSpacing: 0.96 });

  rect(slide, 650, 150, 530, 482, "#241E35");
  textBox(slide, 'TYPESAFE.AI "SYSTEM1" · HOSTED', 672, 171, 486, 22, { fontSize: 13, bold: true, color: C.typeSafeLight });
  const typeSafeCode = [
    "POST https://api.typesafe.ai/v1/systemone",
    "Authorization: Bearer $TYPESAFE_API_KEY",
    "",
    "{",
    '  "model": "jev-latest",',
    '  "state": { ... },',
    '  "questions": {',
    '    "route": {',
    '      "type": "choice",',
    '      "instructions": "Which tool should handle this?",',
    '      "criteria": { "tool_1": "...", "no_tool": "..." }',
    "    }",
    "  }",
    "}",
    "",
    "python poc/typesafe_decision_poc.py --output simple.json",
    "python poc/bfcl_routing_benchmark.py --backend typesafe \\",
    "  --dataset data/bfcl-routing-subset.json --output tools.json",
  ].join("\n");
  textBox(slide, typeSafeCode, 672, 211, 486, 395, { typeface: FONT.mono, fontSize: 10.8, color: "#EEE9F6", lineSpacing: 0.94 });
  textBox(slide, "Credentials stay in .env. Saved request and response audits never contain the API key.", 82, 660, 1098, 22, { fontSize: 13, bold: true, color: C.deep, alignment: "center" });
  slide.speakerNotes.textFrame.setText(["TypeSafe API reference: https://docs.typesafe.ai/api", "Local implementation: poc/zero_shot_decision_poc.py", "Hosted implementation: poc/typesafe_decision_poc.py"].join("\n"));
}

const original = [...presentation.slides.items];
const [cover, method, protocol, ...rest] = original;
const cases = original.slice(3, 15);
const simpleTable = original[15];
const simpleChart = original[16];
const findings = original[17];
const alternatives = original[18];
const toolChart = original[19];
const scope = original[20];
const appendixA1 = original[21];
const appendixA2 = original[22];
const appendixA3 = original[23];
const pipeline = original[24];
const appendixB1 = original[25];
const appendixB2 = original[26];

addCover(cover);
const simpleModernClearance = clearanceStats(simpleModern.cases, "confidence");
const simpleTypeSafeClearance = clearanceStats(simpleTypeSafe.cases, "top_probability");
addComparisonSlide(simpleChart, {
  title: "Simple multiple-choice classification",
  subtitle: "12 obvious-answer cases with identical choices and a fixed gate",
  accuracyCategories: ["Accuracy"],
  modernAccuracy: [simpleModern.cases.filter((row) => row.correct).length / simpleModern.cases.length],
  typeSafeAccuracy: [simpleTypeSafe.cases.filter((row) => row.correct).length / simpleTypeSafe.cases.length],
  modernClearance: simpleModernClearance,
  typeSafeClearance: simpleTypeSafeClearance,
  notes: "Sources: results/benchmark-results.json and results/typesafe-benchmark-results.json. Clearance uses the signed distance from the limiting gate condition.",
});
const toolModernClearance = clearanceStats(toolModern.cases, "top_probability");
const toolTypeSafeClearance = clearanceStats(toolTypeSafe.cases, "top_probability");
addComparisonSlide(toolChart, {
  title: "Tool calling test",
  subtitle: "30 BFCL-derived cases covering tool selection and no-tool detection",
  accuracyCategories: ["Overall", "Tool selection", "No-tool recall"],
  modernAccuracy: [toolModern.summary.accuracy, toolModern.summary.selection_accuracy, toolModern.summary.no_tool_recall],
  typeSafeAccuracy: [toolTypeSafe.summary.accuracy, toolTypeSafe.summary.selection_accuracy, toolTypeSafe.summary.no_tool_recall],
  modernClearance: toolModernClearance,
  typeSafeClearance: toolTypeSafeClearance,
  notes: "Sources: results/bfcl-routing-modernbert-results.json and results/bfcl-routing-typesafe-results.json. This derived subset is not an official BFCL leaderboard score.",
});
addFindingsSlide(findings);
addProtocolSlide(protocol);
replaceText(method, "Same questions, two scorers", "Two classifier paths");
replaceText(method, "Each path receives the identical state, question, and multiple-choice definitions", "Both paths receive the same state, question, and declared options");
replaceText(scope, "What Stage 1 measures", "Tool calling architecture and scope");
replaceText(scope, "A fair classifier comparison now; AST and executable scoring later", "Routing is measured now. Argument extraction and execution remain separate stages.");
replaceText(pipeline, "Appendix A4 · ModernBERT pipeline + Mermaid source", "ModernBERT decision pipeline");
replaceText(alternatives, "Other zero-shot classifiers worth benchmarking", "Appendix D · Other zero-shot classifiers");

const toolPairs = toolModern.cases.map((modern) => {
  const typeSafe = toolTypeSafe.cases.find((row) => row.id === modern.id);
  if (!typeSafe) throw new Error(`Missing TypeSafe tool result for ${modern.id}`);
  return { modern, typeSafe };
});
const toolResults1 = presentation.slides.add();
const toolResults2 = presentation.slides.add();
const apiAppendix = presentation.slides.add();
addToolResultsSlide(toolResults1, toolPairs, 0, 15);
addToolResultsSlide(toolResults2, toolPairs, 15, 30);
addApiAppendixSlide(apiAppendix);

const desiredOrder = [
  cover,
  simpleChart,
  toolChart,
  findings,
  method,
  protocol,
  scope,
  pipeline,
  ...cases,
  simpleTable,
  toolResults1,
  toolResults2,
  appendixA1,
  appendixA2,
  appendixA3,
  appendixB1,
  appendixB2,
  apiAppendix,
  alternatives,
];
desiredOrder.forEach((slide, index) => slide.moveTo(index));

await fs.mkdir(buildDir, { recursive: true });
for (const slideNumber of [1, 2, 3, 4, 5, 6, 7, 8, 21, 22, 23, 27, 29, 30]) {
  const preview = await presentation.slides.getItem(slideNumber - 1).export({ format: "png", scale: 1 });
  await fs.writeFile(path.join(buildDir, `slide-${slideNumber}.png`), new Uint8Array(await preview.arrayBuffer()));
}

await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "smoke-test-comparison-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const sourceSha256 = crypto.createHash("sha256").update(await fs.readFile(sourcePath)).digest("hex");
const result = await finalizePresentation({
  explicitTotalSlideCount: 30,
  requiredNativeTableOwnerSlides: [4, 7, 21, 22, 23, 30],
  requiredNativeChartOwnerSlides: [2, 3],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12191695,6858000",
    "--validate-heading-fit",
    "--require-native-table-slide", "4",
    "--require-native-table-slide", "7",
    "--require-native-table-slide", "21",
    "--require-native-table-slide", "22",
    "--require-native-table-slide", "23",
    "--require-native-table-slide", "30",
  ],
  fontPolicy: {
    basis: "reference",
    families: [FONT.head, FONT.body, FONT.mono],
    referencePath: sourcePath,
    referenceSha256: sourceSha256,
  },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "Smoke-Test-Comparison-System1-vs-ModernBERT-final.validation.json"),
});
console.log(JSON.stringify({ finalPath, result }, null, 2));
