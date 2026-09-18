/*
Content summary: Reorders the existing comparison deck into a smoke-test story,
adds correct-answer clearance distributions and average margins, adds every
tool-routing result, and keeps implementation/API code in a final appendix.

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
const finalPath = path.join(workspaceDir, "results/Smoke-Test-Comparison-System1-vs-ModernBERT-clearance-distributions.pptx");
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

const CLEARANCE_BIN_LABELS = ["Correct (0)", "Wrong <10", "Wrong 10–40", "Wrong 40+"];

function correctAnswerDistance(row) {
  const chosen = Number(row.probabilities?.[row.picked]);
  const correct = Number(row.probabilities?.[row.expected]);
  if (!Number.isFinite(chosen) || !Number.isFinite(correct)) {
    throw new Error(`Missing chosen or correct probability for ${row.id}`);
  }
  return Number(Math.max(0, chosen - correct).toFixed(10));
}

function topTwoMargin(row) {
  const chosen = Number(row.probabilities?.[row.picked]);
  const alternatives = Object.entries(row.probabilities ?? {})
    .filter(([option]) => option !== row.picked)
    .map(([, probability]) => Number(probability));
  if (!Number.isFinite(chosen) || alternatives.length === 0 || alternatives.some((value) => !Number.isFinite(value))) {
    throw new Error(`Missing chosen or next-best probability for ${row.id}`);
  }
  return Number(Math.max(0, chosen - Math.max(...alternatives)).toFixed(10));
}

function average(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function metricSummary(rows) {
  return {
    averageClearance: average(rows.map(correctAnswerDistance)),
    averageMargin: average(rows.map(topTwoMargin)),
  };
}

function clearanceDistribution(rows) {
  const counts = Array(CLEARANCE_BIN_LABELS.length).fill(0);
  for (const row of rows) {
    const value = correctAnswerDistance(row);
    const index = value === 0 ? 0 : value < 0.1 ? 1 : value < 0.4 ? 2 : 3;
    counts[index] += 1;
  }
  return counts;
}

function replaceText(slide, oldText, newText) {
  for (const shape of slide.shapes.items) {
    if (!shape.text) continue;
    const current = String(shape.text);
    if (current.includes(oldText)) shape.text.replace(oldText, newText);
  }
}

function replaceExactText(slide, oldText, newText, color) {
  for (const shape of slide.shapes.items) {
    if (!shape.text || String(shape.text).trim() !== oldText) continue;
    shape.text.replace(oldText, newText);
    if (color) shape.text.color = color;
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
      { name: "TypeSafe.ai JEV", values: config.typeSafeAccuracy, valuesFormatCode: "0%", fill: C.typeSafe, line: { style: "solid", fill: C.typeSafe, width: 1 } },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 70 },
    yAxis: { visible: true, min: 0, max: 1, majorUnit: 0.25, numberFormatCode: "0%", textStyle: { typeface: FONT.body, fontSize: 11.5, fill: C.muted }, line: { style: "solid", fill: C.border, width: 1 }, majorGridlines: { style: "solid", fill: C.border, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: FONT.body, fontSize: 13, bold: true, fill: C.ink } },
  });
  applyPresentationChartFont(accuracyChart, { fontFamily: FONT.body });

  textBox(slide, "CLEARANCE TO CORRECT ANSWER (CASE COUNT)", 625, 143, 555, 22, { fontSize: 13, bold: true, color: C.warn });
  const gateChart = slide.charts.add("bar", {
    ...chartBase(),
    position: { left: 608, top: 171, width: 592, height: 405 },
    categories: CLEARANCE_BIN_LABELS,
    series: [
      { name: "ModernBERT NLI", values: clearanceDistribution(config.modernRows), valuesFormatCode: "0", fill: C.deep, line: { style: "solid", fill: C.deep, width: 1 } },
      { name: "TypeSafe.ai JEV", values: clearanceDistribution(config.typeSafeRows), valuesFormatCode: "0", fill: C.typeSafe, line: { style: "solid", fill: C.typeSafe, width: 1 } },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 35 },
    xAxis: { visible: true, tickLabelPosition: "low", textStyle: { typeface: FONT.body, fontSize: 10.5, fill: C.ink }, line: { style: "solid", fill: C.border, width: 1 } },
    yAxis: { visible: true, min: 0, max: config.histogramMax, majorUnit: config.histogramMajorUnit, numberFormatCode: "0", textStyle: { typeface: FONT.body, fontSize: 11.5, fill: C.muted }, line: { style: "solid", fill: C.border, width: 1 }, majorGridlines: { style: "solid", fill: C.border, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: FONT.body, fontSize: 11, bold: true, fill: C.ink } },
  });
  applyPresentationChartFont(gateChart, { fontFamily: FONT.body });

  const modernMetrics = metricSummary(config.modernRows);
  const typeSafeMetrics = metricSummary(config.typeSafeRows);
  textBox(slide, `Average margin     ModernBERT ${(100 * modernMetrics.averageMargin).toFixed(1)}%     TypeSafe.ai JEV ${(100 * typeSafeMetrics.averageMargin).toFixed(1)}%`, 625, 582, 555, 21, { fontSize: 12.5, bold: true, color: C.deep, alignment: "center" });
  rect(slide, 82, 610, 1098, 45, C.midnight);
  textBox(slide, "Clearance = P(chosen answer) − P(correct answer). Correct choices have zero clearance.", 102, 621, 1058, 21, { fontSize: 14.5, bold: true, color: C.white, alignment: "center" });
  textBox(slide, "Margin = average of P(chosen answer) − P(next-best answer). Lower clearance and higher margin are better.", 82, 672, 1098, 21, { fontSize: 12.5, italic: true, color: C.muted, alignment: "center" });
  slide.speakerNotes.textFrame.setText(config.notes);
}

function addFindingsSlide(slide) {
  baseSlide(slide);
  textBox(slide, "Correct score, clearance, and margin by use case", 82, 42, 1098, 52, {
    typeface: FONT.head, fontSize: 38, bold: true, color: C.midnight,
  });
  textBox(slide, "Each model column reports correct answers, average clearance, and average top-two margin.", 82, 98, 1098, 28, {
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
  const fmtMetrics = (rows) => {
    const metrics = metricSummary(rows);
    return `${fmtCorrect(rows)}     ${(100 * metrics.averageClearance).toFixed(1)}%     ${(100 * metrics.averageMargin).toFixed(1)}%`;
  };
  const categoryRows = [
    ["Simple multiple choice", simpleModern.cases, simpleTypeSafe.cases],
    ["Tool selection", modernToolSelection, typeSafeToolSelection],
    ["No-tool detection", modernNoTool, typeSafeNoTool],
    ["All tool routes", toolModern.cases, toolTypeSafe.cases],
  ];
  const values = [["Use case", "n", "ModernBERT\ncorrect / clearance / margin", "TypeSafe.ai JEV\ncorrect / clearance / margin"]];
  for (const [label, modernRows, typeSafeRows] of categoryRows) {
    values.push([
      label,
      String(modernRows.length),
      fmtMetrics(modernRows),
      fmtMetrics(typeSafeRows),
    ]);
  }
  const table = slide.tables.add({
    rows: values.length, columns: 4, left: 82, top: 158, width: 1098, height: 338,
    columnWidths: [270, 60, 384, 384], values,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: C.border, width: 0.5 });
  table.rows[0].height = 58;
  for (let row = 1; row < values.length; row += 1) table.rows[row].height = 68;
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 4 }).assign({ fill: C.midnight, textStyle: { typeface: FONT.body, fontSize: 11.5, bold: true, color: C.white }, anchor: "middle", margins: { left: 8, right: 6, top: 4, bottom: 4 } });
  table.cells.block({ row: 1, column: 0, rowCount: 4, columnCount: 4 }).assign({ textStyle: { typeface: FONT.body, fontSize: 13, color: C.ink }, anchor: "middle", margins: { left: 8, right: 6, top: 4, bottom: 4 } });
  table.cells.block({ row: 1, column: 2, rowCount: 4, columnCount: 1 }).textStyle.color = C.deep;
  table.cells.block({ row: 1, column: 3, rowCount: 4, columnCount: 1 }).textStyle.color = C.typeSafe;

  rect(slide, 82, 532, 1098, 86, C.paleBlue, { line: { style: "solid", fill: C.border, width: 1 } });
  textBox(slide, "Clearance", 105, 550, 165, 20, { fontSize: 13, bold: true, color: C.deep });
  textBox(slide, "Average P(chosen) − P(correct). It is zero when the chosen answer is correct. Lower is better.", 280, 547, 870, 25, { fontSize: 15, color: C.ink });
  textBox(slide, "Margin", 105, 585, 165, 20, { fontSize: 13, bold: true, color: C.warn });
  textBox(slide, "Average P(chosen) − P(next best). Larger values mean a more separated winner.", 280, 582, 870, 25, { fontSize: 15, color: C.ink });
  textBox(slide, "JEV's one wrong tool route had 72% on the chosen option and 28% on the correct option, a 44-point clearance.", 82, 654, 1098, 24, { fontSize: 13, bold: true, color: C.midnight, alignment: "center" });
  slide.speakerNotes.textFrame.setText("All figures are computed from the four committed result files. Clearance is the average probability distance from the chosen answer to the labeled correct answer. Margin is the average probability distance from the chosen answer to the next-best answer.");
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
  textBox(slide, "Top-ranked accuracy, correct-answer clearance, and average top-two margin", 82, 555, 1098, 32, { fontSize: 19, color: C.ink });
  rect(slide, 82, 626, 1098, 45, C.midnight);
  textBox(slide, "Clearance: P(chosen) − P(correct)     Margin: average P(chosen) − P(next best)", 102, 638, 1058, 21, { fontSize: 16, bold: true, color: C.white, alignment: "center" });
  slide.speakerNotes.textFrame.setText("The tool routing subset is derived from BFCL V4 at commit 6ea57973c7a6097fd7c5915698c54c17c5b1b6c8. Clearance is lower-is-better. Average margin is higher-is-better.");
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
  const values = [["Case", "Expected route", "ModernBERT route", "p / margin", "TypeSafe.ai JEV route", "p / margin", "Correct"]];
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
  textBox(slide, "Correct column reports ModernBERT / TypeSafe.ai JEV. Full schemas and probability distributions remain in the JSON artifacts.", 82, 661, 1098, 22, { fontSize: 12.5, italic: true, color: C.muted, alignment: "center" });
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
addComparisonSlide(simpleChart, {
  title: "Simple multiple-choice classification",
  subtitle: "12 obvious-answer cases with identical choices",
  accuracyCategories: ["Accuracy"],
  modernAccuracy: [simpleModern.cases.filter((row) => row.correct).length / simpleModern.cases.length],
  typeSafeAccuracy: [simpleTypeSafe.cases.filter((row) => row.correct).length / simpleTypeSafe.cases.length],
  modernRows: simpleModern.cases,
  typeSafeRows: simpleTypeSafe.cases,
  histogramMax: 12,
  histogramMajorUnit: 2,
  notes: "Sources: results/benchmark-results.json and results/typesafe-benchmark-results.json. Clearance is P(chosen) minus P(correct). Margin is the average of P(chosen) minus P(next-best).",
});
addComparisonSlide(toolChart, {
  title: "Tool calling test",
  subtitle: "30 BFCL-derived cases covering tool selection and no-tool detection",
  accuracyCategories: ["Overall", "Tool selection", "No-tool recall"],
  modernAccuracy: [toolModern.summary.accuracy, toolModern.summary.selection_accuracy, toolModern.summary.no_tool_recall],
  typeSafeAccuracy: [toolTypeSafe.summary.accuracy, toolTypeSafe.summary.selection_accuracy, toolTypeSafe.summary.no_tool_recall],
  modernRows: toolModern.cases,
  typeSafeRows: toolTypeSafe.cases,
  histogramMax: 30,
  histogramMajorUnit: 5,
  notes: "Sources: results/bfcl-routing-modernbert-results.json and results/bfcl-routing-typesafe-results.json. Clearance is P(chosen) minus P(correct). Margin is the average of P(chosen) minus P(next-best). This derived subset is not an official BFCL leaderboard score.",
});
addFindingsSlide(findings);
addProtocolSlide(protocol);
replaceText(method, "Same questions, two scorers", "Two classifier paths");
replaceText(method, "Each path receives the identical state, question, and multiple-choice definitions", "Both paths receive the same state, question, and declared options");
replaceText(method, "Jev 1.13.0", "JEV 1.13.0");
replaceText(method, "Comparison rule: top probability ≥ 0.65 and top-two margin ≥ 0.15", "Metrics: clearance to the correct answer and average top-two margin");
for (const caseSlide of cases) {
  replaceExactText(caseSlide, "GATE", "CLEARANCE");
  replaceExactText(caseSlide, "clear", "0.0000", C.pass);
  replaceExactText(caseSlide, "review", "0.0000", C.pass);
}
replaceText(simpleTable, "Both scorers ranked every expected answer first. The gate separates them", "Both scorers ranked every expected answer first. Their probability separation differs");
replaceText(simpleTable, "ModernBERT: 12/12 correct, 5/12 clear  ·  TypeSafe: 12/12 correct, 12/12 clear", "Clearance: 0.0% for both  ·  Average margin: ModernBERT 38.4%, TypeSafe.ai JEV 100.0%");
const simpleResultsTable = simpleTable.tables.items[0];
simpleResultsTable.getCell(0, 4).value = "Local margin";
simpleResultsTable.getCell(0, 7).value = "JEV margin";
for (let row = 0; row < simpleModern.cases.length; row += 1) {
  simpleResultsTable.getCell(row + 1, 4).value = Number(simpleModern.cases[row].margin).toFixed(4);
  simpleResultsTable.getCell(row + 1, 7).value = Number(simpleTypeSafe.cases[row].margin).toFixed(4);
}
for (const shape of scope.shapes.items) {
  if (shape.text && String(shape.text).includes("cleared the gate")) {
    shape.text.set("One wrong route scored 72% chosen vs. 28% correct: a 44-point clearance.");
  }
}
replaceText(appendixB2, "It was returned by the API—not created by the 0.65 / 0.15 decision gate", "It was returned by the API—not created by local metric calculations");
replaceText(appendixB2, "margin = top₁ − top₂ = 1.0 − 0.0 = 1.0", "margin = P(chosen) − P(next best) = 1.0");
replaceText(appendixB2, "review = top p < .65 OR margin < .15", "clearance = P(chosen) − P(correct) = 0.0");
replaceText(appendixB2, "AUDIT RESULT  12 / 12 exact one-hot distributions; no client rounding or thresholding", "AUDIT: 12/12 exact one-hot responses; no client rounding or thresholding");
replaceText(scope, "What Stage 1 measures", "Tool calling architecture and scope");
replaceText(scope, "A fair classifier comparison now; AST and executable scoring later", "Routing is measured now. Argument extraction and execution remain separate stages.");
replaceText(scope, "TypeSafe", "TypeSafe.ai JEV");
scope.tables.items[0].getCell(0, 3).value = "TypeSafe.ai JEV";
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
  receiptPath: path.join(stagingDir, "Smoke-Test-Comparison-System1-vs-ModernBERT-clearance-distributions-v13.validation.json"),
});
console.log(JSON.stringify({ finalPath, result }, null, 2));
