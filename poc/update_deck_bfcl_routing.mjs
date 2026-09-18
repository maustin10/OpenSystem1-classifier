import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";

const artifactToolPath = "/Users/markaustin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";
const { FileBlob, PresentationFile } = await import(pathToFileURL(artifactToolPath).href);

const workspaceDir = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const sourcePath = path.join(workspaceDir, "results/OpenSystem1-classifier-comparison.pptx");
const modernPath = path.join(workspaceDir, "results/bfcl-routing-modernbert-results.json");
const typeSafePath = path.join(workspaceDir, "results/bfcl-routing-typesafe-results.json");
const finalPath = path.join(workspaceDir, "results/OpenSystem1-classifier-comparison-stage1.pptx");
const buildDir = path.join(workspaceDir, ".codex-deck-build/bfcl-routing");
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
const skillDir = "/Users/markaustin/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const runtimePython = "/Users/markaustin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const { finalizePresentation, applyPresentationChartFont } = await import(
  pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href,
);

const modern = JSON.parse(await fs.readFile(modernPath, "utf8"));
const typeSafe = JSON.parse(await fs.readFile(typeSafePath, "utf8"));
const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
if (presentation.slides.items.length !== 25) {
  throw new Error(`Expected 25-slide comparison deck, found ${presentation.slides.items.length}`);
}

const C = {
  deep: "#065A82", teal: "#1C7293", typeSafe: "#815AC0", typeSafeLight: "#D8CBEF",
  midnight: "#21295C", cloud: "#F4F7F9", border: "#D5DFE6", track: "#DDE4EA",
  ink: "#1A1F2B", muted: "#6B7A8C", white: "#FFFFFF", pass: "#1E7A4B",
  warn: "#B86E00", palePurple: "#F1ECFA", paleBlue: "#E9F2F6", paleWarn: "#FFF3DF",
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

function baseSlide(slide) {
  slide.shapes.deleteAll();
  rect(slide, 0, 0, W, H, C.cloud, { name: "background" });
  rect(slide, 0, 0, 27, H, C.teal, { name: "brand-spine" });
}

function panel(slide, left, top, width, height, header, color) {
  rect(slide, left, top, width, height, C.white, {
    line: { style: "solid", fill: C.border, width: 1 },
  });
  rect(slide, left, top, width, 38, color);
  textBox(slide, header, left + 16, top + 8, width - 32, 22, {
    fontSize: 14, bold: true, color: C.white,
  });
}

function addRoutingResultsSlide(slide) {
  baseSlide(slide);
  textBox(slide, "Stage 1 · BFCL-derived tool routing", 82, 40, 1098, 56, {
    typeface: FONT.head, fontSize: 40, bold: true, color: C.midnight,
  });
  textBox(slide, "30 official-source cases · 20 tool selections + 10 no-tool decisions", 82, 99, 1098, 28, {
    fontSize: 17, italic: true, color: C.muted,
  });

  const m = modern.summary;
  const t = typeSafe.summary;
  const chart = slide.charts.add("bar", {
    position: { left: 76, top: 150, width: 810, height: 445 },
    categories: ["Overall accuracy", "Tool selection", "No-tool recall", "Gate clearance"],
    series: [
      {
        name: "ModernBERT NLI",
        values: [m.accuracy, m.selection_accuracy, m.no_tool_recall, m.gate_clearance],
        valuesFormatCode: "0%", fill: C.deep,
        line: { style: "solid", fill: C.deep, width: 1 },
      },
      {
        name: "TypeSafe Jev 1.13.0",
        values: [t.accuracy, t.selection_accuracy, t.no_tool_recall, t.gate_clearance],
        valuesFormatCode: "0%", fill: C.typeSafe,
        line: { style: "solid", fill: C.typeSafe, width: 1 },
      },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 65 },
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { typeface: FONT.body, fontSize: 13, fill: C.ink } },
    xAxis: { visible: true, textStyle: { typeface: FONT.body, fontSize: 13, fill: C.ink }, line: { style: "solid", fill: C.border, width: 1 } },
    yAxis: { visible: true, min: 0, max: 1, majorUnit: 0.25, numberFormatCode: "0%", textStyle: { typeface: FONT.body, fontSize: 12, fill: C.muted }, line: { style: "solid", fill: C.border, width: 1 }, majorGridlines: { style: "solid", fill: C.border, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: FONT.body, fontSize: 13, bold: true, fill: C.ink } },
    chartFill: "none", chartLine: { fill: "none", width: 0 }, plotAreaFill: "none", plotAreaLine: { fill: "none", width: 0 },
  });
  applyPresentationChartFont(chart, { fontFamily: FONT.body });

  panel(slide, 922, 150, 258, 196, "TOP-LINE RESULT", C.midnight);
  textBox(slide, `${m.correct} / 30`, 938, 205, 108, 43, { typeface: FONT.head, fontSize: 27, bold: true, color: C.deep, alignment: "center" });
  textBox(slide, `${t.correct} / 30`, 1050, 205, 110, 43, { typeface: FONT.head, fontSize: 27, bold: true, color: C.typeSafe, alignment: "center" });
  textBox(slide, "ModernBERT", 942, 253, 100, 22, { fontSize: 12, bold: true, color: C.deep, alignment: "center" });
  textBox(slide, "TypeSafe", 1054, 253, 106, 22, { fontSize: 12, bold: true, color: C.typeSafe, alignment: "center" });
  textBox(slide, "TypeSafe led by 6 correct routes", 942, 295, 218, 28, { fontSize: 15, bold: true, color: C.ink, alignment: "center" });

  panel(slide, 922, 372, 258, 223, "GATE INTERPRETATION", C.warn);
  textBox(slide, "0 / 30", 942, 426, 218, 42, { typeface: FONT.head, fontSize: 34, bold: true, color: C.deep, alignment: "center" });
  textBox(slide, "ModernBERT routes cleared", 942, 470, 218, 24, { fontSize: 13, bold: true, color: C.deep, alignment: "center" });
  textBox(slide, "30 / 30", 942, 515, 218, 42, { typeface: FONT.head, fontSize: 34, bold: true, color: C.typeSafe, alignment: "center" });
  textBox(slide, "TypeSafe routes cleared", 942, 559, 218, 24, { fontSize: 13, bold: true, color: C.typeSafe, alignment: "center" });

  rect(slide, 82, 625, 1098, 47, C.midnight);
  textBox(slide, "Shared gate: top probability ≥ 0.65 AND top-two margin ≥ 0.15 · gate clearance does not guarantee correctness", 102, 638, 1058, 23, { fontSize: 14.5, bold: true, color: C.white, alignment: "center" });
  textBox(slide, "Derived subset—not an official BFCL leaderboard score", 82, 685, 1098, 19, { fontSize: 11.5, italic: true, color: C.muted, alignment: "center" });
  slide.speakerNotes.textFrame.setText([
    "Sources: results/bfcl-routing-modernbert-results.json and results/bfcl-routing-typesafe-results.json",
    "Dataset source: BFCL V4 at https://github.com/ShishirPatil/gorilla commit 6ea57973c7a6097fd7c5915698c54c17c5b1b6c8.",
    "Accuracy scores top-ranked routes even when the confidence gate would abstain.",
  ].join("\n"));
}

function addRoutingScopeSlide(slide) {
  baseSlide(slide);
  textBox(slide, "What Stage 1 measures", 82, 40, 1098, 56, {
    typeface: FONT.head, fontSize: 40, bold: true, color: C.midnight,
  });
  textBox(slide, "A fair classifier comparison now; AST and executable scoring later", 82, 99, 1098, 28, {
    fontSize: 17, italic: true, color: C.muted,
  });

  const stages = [
    ["1", "ROUTE", "Choose one declared tool\nor choose no tool", C.pass, C.white],
    ["2", "EXTRACT", "Generate typed\nargument values", C.border, C.ink],
    ["3", "EXECUTE", "Run the call and\nvalidate behavior", C.border, C.ink],
  ];
  stages.forEach(([number, title, body, color, textColor], index) => {
    const x = 82 + index * 268;
    rect(slide, x, 157, 228, 114, index === 0 ? C.pass : C.white, {
      line: { style: "solid", fill: color, width: 2 },
    });
    textBox(slide, number, x + 14, 171, 34, 33, { typeface: FONT.head, fontSize: 24, bold: true, color: index === 0 ? C.white : C.muted, alignment: "center" });
    textBox(slide, title, x + 58, 171, 150, 24, { fontSize: 14, bold: true, color: textColor });
    textBox(slide, body, x + 58, 204, 150, 48, { fontSize: 14, color: index === 0 ? C.white : C.muted });
    if (index < 2) textBox(slide, "→", x + 234, 190, 34, 42, { fontSize: 28, bold: true, color: C.teal, alignment: "center" });
  });
  rect(slide, 82, 282, 764, 34, C.paleBlue);
  textBox(slide, "Measured today", 82, 290, 228, 18, { fontSize: 12, bold: true, color: C.pass, alignment: "center" });
  textBox(slide, "Out of scope for classifiers alone", 350, 290, 496, 18, { fontSize: 12, bold: true, color: C.muted, alignment: "center" });

  panel(slide, 82, 346, 764, 265, "CATEGORY RESULTS", C.deep);
  const values = [
    ["Category", "Cases", "ModernBERT", "TypeSafe"],
    ["Multiple-function selection", "20", "17 / 20  (85%)", "20 / 20  (100%)"],
    ["No-tool detection", "10", "6 / 10  (60%)", "9 / 10  (90%)"],
    ["Overall", "30", "23 / 30  (76.7%)", "29 / 30  (96.7%)"],
  ];
  const table = slide.tables.add({ rows: 4, columns: 4, left: 104, top: 404, width: 720, height: 176, columnWidths: [282, 80, 178, 180], values });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: C.border, width: 0.5 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 4 }).assign({ fill: C.midnight, textStyle: { typeface: FONT.body, fontSize: 12, bold: true, color: C.white }, anchor: "middle", margins: { left: 8, right: 6, top: 4, bottom: 4 } });
  table.cells.block({ row: 1, column: 0, rowCount: 3, columnCount: 4 }).assign({ textStyle: { typeface: FONT.body, fontSize: 12.5, color: C.ink }, anchor: "middle", margins: { left: 8, right: 6, top: 4, bottom: 4 } });
  table.cells.block({ row: 1, column: 2, rowCount: 3, columnCount: 1 }).textStyle.color = C.deep;
  table.cells.block({ row: 1, column: 3, rowCount: 3, columnCount: 1 }).textStyle.color = C.typeSafe;

  panel(slide, 882, 157, 298, 454, "ERROR AUDIT", C.typeSafe);
  textBox(slide, "ModernBERT · 7 misses", 906, 216, 250, 24, { fontSize: 17, bold: true, color: C.deep });
  textBox(slide, "Tool selection: multiple_2, _4, _11\nNo-tool: irrelevance_20, _80, _160, _180", 906, 251, 250, 78, { typeface: FONT.mono, fontSize: 11.5, color: C.ink });
  rect(slide, 906, 344, 250, 1, C.border);
  textBox(slide, "TypeSafe · 1 miss", 906, 371, 250, 24, { fontSize: 17, bold: true, color: C.typeSafe });
  textBox(slide, "irrelevance_180\n‘cricket matches scheduled for today’", 906, 406, 250, 55, { typeface: FONT.mono, fontSize: 11.5, color: C.ink });
  rect(slide, 906, 480, 250, 92, C.paleWarn, { line: { style: "solid", fill: C.warn, width: 1 } });
  textBox(slide, "Important", 920, 492, 222, 18, { fontSize: 12, bold: true, color: C.warn });
  textBox(slide, "TypeSafe cleared the gate on its one wrong route. Thresholds control abstention—not truth.", 920, 518, 222, 45, { fontSize: 13, color: C.ink });

  rect(slide, 82, 637, 1098, 42, C.midnight);
  textBox(slide, "Next stage: add deterministic argument extraction, then use official BFCL AST / executable evaluation", 102, 649, 1058, 21, { fontSize: 14.5, bold: true, color: C.white, alignment: "center" });
  textBox(slide, "BFCL-derived data; exact source IDs and function schemas are committed in data/bfcl-routing-subset.json", 82, 690, 1098, 17, { fontSize: 11.5, italic: true, color: C.muted, alignment: "center" });
  slide.speakerNotes.textFrame.setText([
    "This derived subset maps BFCL's Multiple Function category to tool selection and its Irrelevance category to tool-vs-no-tool classification.",
    "Official BFCL documentation: https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/bfcl_eval/data/README.md",
    "Stage 2 is intentionally not scored here because neither classifier generates argument values.",
  ].join("\n"));
}

const anchor = presentation.slides.getItem(18);
presentation.slides.insert({ after: anchor });
const routingResultsSlide = presentation.slides.getItem(19);
addRoutingResultsSlide(routingResultsSlide);
presentation.slides.insert({ after: routingResultsSlide });
const routingScopeSlide = presentation.slides.getItem(20);
addRoutingScopeSlide(routingScopeSlide);

await fs.mkdir(buildDir, { recursive: true });
for (const slideNumber of [20, 21]) {
  const preview = await presentation.slides.getItem(slideNumber - 1).export({ format: "png", scale: 1 });
  await fs.writeFile(path.join(buildDir, `slide-${slideNumber}.png`), new Uint8Array(await preview.arrayBuffer()));
}

await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "bfcl-routing-comparison-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const sourceSha256 = crypto.createHash("sha256").update(await fs.readFile(sourcePath)).digest("hex");
const result = await finalizePresentation({
  explicitTotalSlideCount: 27,
  requiredNativeTableOwnerSlides: [16, 19, 21],
  requiredNativeChartOwnerSlides: [17, 20],
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
    "--require-native-table-slide", "16",
    "--require-native-table-slide", "19",
    "--require-native-table-slide", "21",
  ],
  fontPolicy: {
    basis: "reference",
    families: [FONT.head, FONT.body, FONT.mono],
    referencePath: sourcePath,
    referenceSha256: sourceSha256,
  },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "OpenSystem1-classifier-comparison-stage1.validation.json"),
});
console.log(JSON.stringify({ finalPath, result }, null, 2));
