const CCN_COLORS = {
  navy: "#1a3b5d",
  pink: "#f4c7c3",
  blue: "#c5e0f3",
  green: "#c8e6c9",
  white: "#f7fafc",
  muted: "#8fa8c4",
  card: "#162d47",
};

const COMPACT_LAYOUT_MAX_WIDTH = 960;
const STACKED_LEGEND_MAX_WIDTH = 960;
const PHONE_MAX_WIDTH = 640;

function viewportWidth() {
  return document.documentElement.clientWidth || window.innerWidth;
}

function isPhoneLayout() {
  return viewportWidth() < PHONE_MAX_WIDTH;
}

function isTouchLike() {
  return window.matchMedia("(hover: none) and (pointer: coarse)").matches;
}

function chartContainerWidth(container) {
  return container.node()?.clientWidth || viewportWidth();
}

let lastLayoutWidth = viewportWidth();
let lastLayoutHeight = window.innerHeight;

function shouldReflowOnResize() {
  const width = viewportWidth();
  const height = window.innerHeight;
  const widthChanged = Math.abs(width - lastLayoutWidth) >= 8;
  const heightChanged = Math.abs(height - lastLayoutHeight) >= 48;
  lastLayoutWidth = width;
  lastLayoutHeight = height;
  if (widthChanged) return true;
  if (isTouchLike()) return false;
  return heightChanged;
}

function restorePageScroll(scrollX, scrollY) {
  window.scrollTo(scrollX, scrollY);
  requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));
}

function removeChartScrollWrappers() {
  document.querySelectorAll(".chart-scroll-x").forEach((wrapper) => {
    const chart = wrapper.firstElementChild;
    if (chart && wrapper.parentNode) {
      wrapper.parentNode.insertBefore(chart, wrapper);
      wrapper.remove();
    }
  });
}

function appendChartSvg(container, width, height) {
  return container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .style("height", `${height}px`);
}

function wrapThemeLabel(text, maxWidth, fontPx) {
  const maxChars = Math.max(12, Math.floor(maxWidth / (fontPx * 0.48)));
  const words = String(text).split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length > maxChars && line) {
      lines.push(line);
      line = word;
    } else if (candidate.length > maxChars) {
      lines.push(`${candidate.slice(0, Math.max(1, maxChars - 1))}…`);
      line = "";
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines.slice(0, 3);
}

function renderPhoneThemeBarChart(container, options) {
  const {
    data,
    getLabel,
    getValue,
    getBarFill,
    onBarClick,
    onBarTooltip,
    valueFormat = (v, item) => String(v),
    labelFill = CCN_COLORS.muted,
  } = options;

  container.selectAll("*").remove();
  const width = chartContainerWidth(container);
  const margin = { top: gs(5), right: gs(30), bottom: gs(5), left: gs(5) };
  const innerW = width - margin.left - margin.right;
  const labelFont = chartThemePx(7);
  const valueFont = chartThemePx(8);
  const barH = gs(8);
  const rowGap = gs(3);
  const valueGap = gs(3);
  const blockGap = gs(8);
  const valueH = valueFont * 1.15;
  const maxVal = d3.max(data, getValue) || 1;
  const x = d3.scaleLinear().domain([0, maxVal]).range([0, innerW]);

  const rows = data.map((item) => {
    const lines = wrapThemeLabel(getLabel(item), innerW, labelFont);
    const labelH = lines.length * labelFont * 1.15;
    return { item, lines, rowHeight: labelH + rowGap + barH + valueGap + valueH + blockGap };
  });
  const height = margin.top + margin.bottom + d3.sum(rows, (r) => r.rowHeight);
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .style("height", `${height}px`);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  let yCursor = 0;
  rows.forEach(({ item, lines, rowHeight }) => {
    const text = g
      .append("text")
      .attr("x", 0)
      .attr("y", yCursor + labelFont)
      .attr("fill", typeof labelFill === "function" ? labelFill(item) : labelFill)
      .style("font-size", `${labelFont}px`);
    lines.forEach((ln, li) => {
      text
        .append("tspan")
        .attr("x", 0)
        .attr("dy", li === 0 ? 0 : labelFont * 1.15)
        .text(ln);
    });

    const barY = yCursor + lines.length * labelFont * 1.15 + rowGap;
    const val = getValue(item);
    const barWidth = Math.max(x(val), val > 0 ? gs(2) : 0);
    const rect = g
      .append("rect")
      .attr("x", 0)
      .attr("y", barY)
      .attr("height", barH)
      .attr("width", barWidth)
      .attr("fill", getBarFill(item))
      .attr("rx", gs(3));
    if (onBarClick) {
      rect.style("cursor", "pointer").on("click", () => onBarClick(item));
    }
    if (onBarTooltip) {
      rect.on("mousemove", (event) => onBarTooltip(event, item)).on("mouseleave", hideTooltip);
    }

    g.append("text")
      .attr("x", barWidth)
      .attr("y", barY + barH + valueGap + valueFont * 0.85)
      .attr("text-anchor", "end")
      .attr("fill", CCN_COLORS.muted)
      .style("font-size", chartThemeFs(8))
      .text(valueFormat(val, item));

    yCursor += rowHeight;
  });
}

function readCssNumber(property, fallback) {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(property).trim();
  const parsed = parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const PHONE_GRAPH_SCALE = 0.58;

function getUiScale() {
  return readCssNumber("--ui-scale", Math.min(3, Math.max(1, 0.6 + viewportWidth() / 500)));
}

const s = (n) => n * getUiScale();
const gs = (n) => (isPhoneLayout() ? n * getUiScale() * PHONE_GRAPH_SCALE : s(n));
const fs = (n) => `${s(n)}px`;

function chartThemePx(base) {
  return isPhoneLayout() ? gs(base) : themeLabelPx(base);
}

function chartThemeFs(base) {
  return `${chartThemePx(base)}px`;
}

function fitLegendLabel(text, maxWidth, fontPx) {
  const usable = Math.max(40, maxWidth - fontPx * 2.4);
  const maxChars = Math.max(10, Math.floor(usable / (fontPx * 0.48)));
  const label = String(text);
  if (label.length <= maxChars) return label;
  return `${label.slice(0, Math.max(1, maxChars - 1))}…`;
}

function isCompactLayout() {
  return viewportWidth() < COMPACT_LAYOUT_MAX_WIDTH;
}

function useStackedChartLegend(width = viewportWidth()) {
  return width < STACKED_LEGEND_MAX_WIDTH;
}

function legendColumnCount(width) {
  if (isPhoneLayout()) return 2;
  if (width < 480) return 1;
  if (width < 1400) return 2;
  return 3;
}

function themeLabelFontScale() {
  if (isPhoneLayout()) return 1;
  const ui = getUiScale();
  return 1 + ((ui - 1) / 2) * 0.8;
}

function themeLabelPx(base) {
  return s(base) * themeLabelFontScale();
}

function themeFs(base) {
  return `${themeLabelPx(base)}px`;
}

let measureTextCanvas = null;

function measureTextWidth(text, fontSizePx, fontFamily = 'system-ui, -apple-system, "Segoe UI", sans-serif') {
  if (typeof document === "undefined") return text.length * fontSizePx * 0.58;
  measureTextCanvas = measureTextCanvas || document.createElement("canvas");
  const ctx = measureTextCanvas.getContext("2d");
  if (!ctx) return text.length * fontSizePx * 0.58;
  ctx.font = `${fontSizePx}px ${fontFamily}`;
  return ctx.measureText(text).width;
}

function themeBarLabelWidth(containerWidth = 0) {
  const w = containerWidth || viewportWidth();
  const maxFromScale = s(300) * themeLabelFontScale();
  if (w >= COMPACT_LAYOUT_MAX_WIDTH) return maxFromScale;

  const fraction = isPhoneLayout()
    ? w < 400
      ? 0.32
      : 0.3
    : w < 400
      ? 0.45
      : w < 640
        ? 0.42
        : 0.36;
  return Math.min(maxFromScale, Math.max(w * fraction, s(40)));
}

function themeBarRowHeight() {
  return Math.max(s(36), themeLabelPx(10) * 1.3);
}

function themeBarPlotWidth(innerW, rows, formatValue) {
  const valueFont = themeLabelPx(10);
  const maxLabelWidth =
    d3.max(rows, (row) => measureTextWidth(formatValue(row), valueFont)) || measureTextWidth("+0.0%", valueFont);
  const reserve = Math.max(maxLabelWidth + s(12), s(40));
  return Math.max(s(48), innerW - reserve);
}

function themeBarLabelX(gap = 8) {
  return -s(gap);
}

function drawThemeBarLabels(g, data, y, getLabel, options = {}) {
  const baseFont = options.baseFont ?? 10;
  const fill = options.fill ?? CCN_COLORS.muted;
  const gap = options.gap ?? 8;
  g.selectAll("text.theme-label")
    .data(data)
    .join("text")
    .attr("class", "theme-label")
    .attr("x", themeBarLabelX(gap))
    .attr("y", (d) => y(getLabel(d)) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", "end")
    .attr("fill", (d) => (typeof fill === "function" ? fill(d) : fill))
    .style("font-size", themeFs(baseFont))
    .style("pointer-events", options.pointerEvents || "auto")
    .text(getLabel);
}

function styleThemeAxisLabels(selection) {
  selection
    .selectAll("text")
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", isPhoneLayout() ? chartThemeFs(8) : themeFs(10));
}

const CHART_PALETTE = [
  "#F34949", // red — Reinforcement learning
  "#C03030", // dark red — Motor control & planning
  "#F08519", // orange — Naturalistic encoding/decoding
  "#F3F349", // yellow — Neural population geometry & dynamics
  "#85F019", // chartreuse — Decision-making and metacognition
  "#49F349", // green — Vision
  "#84D854", // yellow-green — Perception
  "#19F085", // teal — Language/auditory neuroscience
  "#49F3F3", // cyan — AI, LLM, & Neural Networks
  "#1985F0", // blue — Memory
  "#4949F3", // indigo — Social cognition & theory of mind
  "#8519F0", // violet — Attention & cognitive control
  "#F349F3", // magenta — Clinical / computational psychiatry
  "#F01985", // rose — Methods and theory
  "#F680B0", // light rose — Everything else
];

const KPI_ICONS = {
  submissions:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 17V9"/><path d="M12 17V7"/><path d="M16 17v-5"/></svg>',
  filter:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/><path d="M8 11h6"/></svg>',
  keywords:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l-5 5v4l4 4h4l5-5"/><path d="M14 7l3 3"/><circle cx="9.5" cy="9.5" r="1.5"/></svg>',
  years:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4"/><path d="M16 3v4"/><path d="M4 10h16"/><path d="M8 14h3"/><path d="M13 14h3"/></svg>',
};

const LIST_DELIMITER = " | ";

const GOOGLE_FORM_TOPICS = [
  "Reinforcement learning",
  "Motor control & planning",
  "Naturalistic encoding/decoding",
  "Neural population geometry & dynamics",
  "Decision-making and metacognition",
  "Vision",
  "Perception",
  "Language/auditory neuroscience",
  "AI, LLM, & Neural Networks",
  "Memory",
  "Social cognition & theory of mind",
  "Attention & cognitive control / executive function",
  "Clinical / computational psychiatry",
  "Methods and theory",
  "Everything else",
];

const state = {
  data: null,
  embeddings: null,
  selectedYear: "all",
  search: "",
  selectedTheme: "",
  highlightedSubmissionId: "",
  deltaFromYear: "",
  deltaToYear: "",
};

let tooltip = null;

function ensureD3() {
  if (typeof d3 === "undefined") {
    throw new Error("D3.js failed to load. Check your network connection or ad blocker.");
  }
  if (!tooltip) {
    tooltip = d3.select("#tooltip");
  }
}

function showTooltip(html, event) {
  if (!tooltip) return;
  tooltip
    .style("opacity", 1)
    .html(html)
    .style("left", `${event.pageX + s(12)}px`)
    .style("top", `${event.pageY + s(12)}px`);
}

function hideTooltip() {
  if (!tooltip) return;
  tooltip.style("opacity", 0);
}

function showError(message) {
  const grid = document.querySelector(".dashboard-grid");
  if (!grid) return;
  grid.innerHTML = `<section class="card card-full"><p style="color:#f4c7c3;margin:0;">${message}</p></section>`;
}

function splitField(value) {
  if (!value) return [];
  return String(value)
    .split(/\s*\|\s*/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function csvRowToSubmission(row) {
  const umapX = row.umap_x === "" || row.umap_x == null ? null : Number(row.umap_x);
  const umapY = row.umap_y === "" || row.umap_y == null ? null : Number(row.umap_y);
  const keywords = splitField(row.keywords);
  return {
    id: row.id,
    year: Number(row.year),
    title: row.title || "",
    author: row.author || row.first_author || "",
    authors: row.authors || row.author || "",
    abstract: row.abstract || "",
    keywords,
    assigned_topics: splitField(row.assigned_topics),
    umap_x: Number.isFinite(umapX) ? umapX : null,
    umap_y: Number.isFinite(umapY) ? umapY : null,
    source_url: row.source_url || "",
    poster_number: row.poster_number || "",
  };
}

function buildStatsFromSubmissions(submissions) {
  const countsByYear = {};
  submissions.forEach((item) => {
    const year = String(item.year);
    countsByYear[year] = (countsByYear[year] || 0) + 1;
  });
  return { counts_by_year: countsByYear };
}

function buildStateFromCsv(rows) {
  const submissions = rows.map(csvRowToSubmission);
  const years = [...new Set(submissions.map((item) => item.year))].sort((a, b) => a - b);
  return {
    submissions,
    metadata: {
      years,
      total_count: submissions.length,
      source: "abstracts.csv",
    },
    stats: buildStatsFromSubmissions(submissions),
  };
}

function buildEmbeddingsFromSubmissions(submissions) {
  const points = submissions
    .filter((item) => item.umap_x != null && item.umap_y != null)
    .map((item) => ({
      id: item.id,
      poster_number: item.poster_number,
      x: item.umap_x,
      y: item.umap_y,
      title: item.title,
      abstract: item.abstract,
      year: item.year,
    }));
  if (!points.length) return null;
  return { points };
}

function embeddingDisplayPoints() {
  return filteredSubmissions()
    .filter((item) => item.umap_x != null && item.umap_y != null)
    .map((item) => ({
      id: item.id,
      x: item.umap_x,
      y: item.umap_y,
      year: item.year,
      title: item.title,
      poster_number: item.poster_number,
      abstract: item.abstract,
    }));
}

function assignedTopics(submission) {
  if (submission.assigned_topics?.length) return submission.assigned_topics;
  const fallback = [submission.primary_theme, ...(submission.secondary_topics || [])].filter(Boolean);
  return [...new Set(fallback)];
}

function primaryTheme(submission) {
  return assignedTopics(submission)[0] || null;
}

function submissionMatchesSearch(item, search) {
  const haystack = [
    item.title,
    item.authors,
    item.abstract,
    ...assignedTopics(item),
    ...(item.keywords || []),
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(search);
}

function filteredSubmissions() {
  const { submissions } = state.data;
  const search = state.search.trim().toLowerCase();

  return submissions.filter((item) => {
    const yearOk = state.selectedYear === "all" || String(item.year) === state.selectedYear;
    const searchOk = !search || submissionMatchesSearch(item, search);
    const themeOk =
      !state.selectedTheme || assignedTopics(item).includes(state.selectedTheme);
    return yearOk && searchOk && themeOk;
  });
}

function submissionsForThemeTrends() {
  const { submissions } = state.data;
  const search = state.search.trim().toLowerCase();

  return submissions.filter((item) => {
    const searchOk = !search || submissionMatchesSearch(item, search);
    const themeOk = !state.selectedTheme || assignedTopics(item).includes(state.selectedTheme);
    return searchOk && themeOk;
  });
}

function primaryThemeCounts(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    [...new Set(assignedTopics(item))].forEach((theme) => {
      counts.set(theme, (counts.get(theme) || 0) + 1);
    });
  });
  return [...counts.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count);
}

const THEME_STOPWORDS = new Set([
  "the", "and", "for", "with", "from", "that", "this", "using", "based", "study", "results",
  "show", "human", "brain", "neural", "model", "models", "data", "analysis", "abstract",
]);

function tokenize(text) {
  return (text || "")
    .toLowerCase()
    .match(/[a-z][a-z0-9\-]{2,}/g)
    ?.filter((t) => !THEME_STOPWORDS.has(t)) || [];
}

function globalThemeTotals() {
  const totals = new Map();
  state.data?.submissions?.forEach((submission) => {
    [...new Set(assignedTopics(submission))].forEach((topic) => {
      totals.set(topic, (totals.get(topic) || 0) + 1);
    });
  });
  return totals;
}

function googleTopicNames() {
  return GOOGLE_FORM_TOPICS;
}

function researchThemeNames() {
  const totals = globalThemeTotals();
  const hasAssignments = (theme) => (totals.get(theme) || 0) > 0;
  return GOOGLE_FORM_TOPICS.filter(hasAssignments);
}

function themeColor(theme) {
  const themes = googleTopicNames();
  const index = themes.indexOf(theme);
  return CHART_PALETTE[(index >= 0 ? index : 0) % CHART_PALETTE.length];
}

function themeLegendThemes() {
  return googleTopicNames();
}

function embeddingPointPrimaryTheme(point) {
  const submission = submissionForEmbeddingPoint(point);
  return submission ? primaryTheme(submission) : null;
}

function appendPrimaryTopicDot(parent, radius, primaryTopic, options = {}) {
  const { opacity = 0.92, stroke = CCN_COLORS.navy, strokeWidth = 1 } = options;
  const topic = primaryTopic || "Everything else";

  parent
    .append("circle")
    .attr("class", "embedding-point")
    .attr("r", radius)
    .attr("fill", themeColor(topic))
    .attr("stroke", stroke)
    .attr("stroke-width", strokeWidth)
    .attr("opacity", opacity);
}

function buildThemeClassifier() {
  const profiles = new Map();
  researchThemeNames().forEach((name) => profiles.set(name, new Map()));

  state.data?.submissions?.forEach((submission) => {
    assignedTopics(submission).forEach((theme) => {
      if (!profiles.has(theme)) return;
      const weights = profiles.get(theme);
      tokenize(submission.title).forEach((term) => weights.set(term, (weights.get(term) || 0) + 1));
      tokenize(submission.abstract).forEach((term) => weights.set(term, (weights.get(term) || 0) + 1));
    });
  });

  state.themeProfiles = profiles;
}

function submissionForEmbeddingPoint(point) {
  return state.data?.submissions?.find((item) => item.id === point.id);
}

function embeddingPointForSubmission(submission) {
  if (submission.umap_x == null || submission.umap_y == null) return null;
  return {
    id: submission.id,
    x: submission.umap_x,
    y: submission.umap_y,
    year: submission.year,
    title: submission.title,
    poster_number: submission.poster_number,
  };
}

function submissionResearchTheme(submission) {
  const assigned = primaryTheme(submission);
  if (assigned) return assigned;

  const profiles = state.themeProfiles;
  if (!profiles?.size) return null;

  const tokens = tokenize(
    [submission.title, submission.abstract, submission.topic_area, ...submission.keywords].join(" ")
  );
  if (!tokens.length) return null;

  let bestTheme = null;
  let bestScore = 0;
  profiles.forEach((weights, theme) => {
    let score = 0;
    tokens.forEach((term) => {
      if (weights.has(term)) score += weights.get(term);
    });
    if (score > bestScore) {
      bestScore = score;
      bestTheme = theme;
    }
  });

  return bestScore > 0 ? bestTheme : null;
}

function themeCountsByYear(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    const year = String(item.year);
    if (!counts.has(year)) counts.set(year, new Map());
    const yearMap = counts.get(year);
    [...new Set(assignedTopics(item))].forEach((theme) => {
      yearMap.set(theme, (yearMap.get(theme) || 0) + 1);
    });
  });
  return counts;
}

function submissionCountByYear(submissions) {
  const totals = new Map();
  submissions.forEach((item) => {
    const year = String(item.year);
    totals.set(year, (totals.get(year) || 0) + 1);
  });
  return totals;
}

function themeShareOfSubmissions(count, yearTotal) {
  return yearTotal > 0 ? (count / yearTotal) * 100 : 0;
}

function formatDeltaPct(value, digits = 1) {
  const rounded = value.toFixed(digits);
  return `${value >= 0 ? "+" : ""}${rounded}%`;
}

function latestComparableYearPair(years, byYear, themes) {
  const sorted = [...years].sort((a, b) => a - b);
  for (let i = sorted.length - 1; i > 0; i -= 1) {
    const toYear = String(sorted[i]);
    const fromYear = String(sorted[i - 1]);
    const hasFrom = themes.some((theme) => (byYear.get(fromYear)?.get(theme) || 0) > 0);
    const hasTo = themes.some((theme) => (byYear.get(toYear)?.get(theme) || 0) > 0);
    if (hasFrom || hasTo) return { fromYear, toYear };
  }
  return null;
}

function researchThemeDeltas(submissions, fromYear, toYear) {
  const themes = researchThemeNames();
  if (!themes.length) return { pair: null, rows: [] };

  const years = [...state.data.metadata.years].sort((a, b) => a - b);
  const byYear = themeCountsByYear(submissions);
  let pair = null;

  if (fromYear && toYear && String(fromYear) !== String(toYear)) {
    pair = { fromYear: String(fromYear), toYear: String(toYear) };
  } else {
    pair = latestComparableYearPair(years, byYear, themes);
  }
  if (!pair) return { pair: null, rows: [] };

  const yearTotals = submissionCountByYear(submissions);
  const fromYearTotal = yearTotals.get(pair.fromYear) || 0;
  const toYearTotal = yearTotals.get(pair.toYear) || 0;

  const rows = themes
    .map((theme) => {
      const fromCount = byYear.get(pair.fromYear)?.get(theme) || 0;
      const toCount = byYear.get(pair.toYear)?.get(theme) || 0;
      const fromPct = themeShareOfSubmissions(fromCount, fromYearTotal);
      const toPct = themeShareOfSubmissions(toCount, toYearTotal);
      return {
        theme,
        fromYear: pair.fromYear,
        toYear: pair.toYear,
        fromCount,
        toCount,
        fromYearTotal,
        toYearTotal,
        fromPct,
        toPct,
        delta: toPct - fromPct,
      };
    })
    .filter((row) => row.fromCount > 0 || row.toCount > 0)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  return { pair, rows };
}

function defaultDeltaYearPair() {
  const themes = researchThemeNames();
  if (!themes.length || !state.data?.metadata?.years?.length) return null;
  const years = [...state.data.metadata.years].sort((a, b) => a - b);
  const byYear = themeCountsByYear(submissionsForThemeTrends());
  return latestComparableYearPair(years, byYear, themes);
}

function syncDeltaYearState() {
  const pair = defaultDeltaYearPair();
  if (!state.deltaFromYear && pair) state.deltaFromYear = pair.fromYear;
  if (!state.deltaToYear && pair) state.deltaToYear = pair.toYear;
}

function renderDeltaYearControls() {
  const years = state.data.metadata.years;
  const fromSelect = d3.select("#delta-from-year");
  const toSelect = d3.select("#delta-to-year");
  if (fromSelect.empty() || toSelect.empty()) return;

  fromSelect.selectAll("option").data(years).join("option").attr("value", String).text(String);
  toSelect.selectAll("option").data(years).join("option").attr("value", String).text(String);

  syncDeltaYearState();
  fromSelect.property("value", state.deltaFromYear);
  toSelect.property("value", state.deltaToYear);
}

function truncateLabel(text, max = s(28)) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

function displaySubmissions() {
  return filteredSubmissions();
}

function syncThemeSelects() {
  d3.select("#theme-select").property("value", state.selectedTheme);
  d3.select("#embedding-theme-select").property("value", state.selectedTheme);
}

function setThemeFilter(themeName) {
  const nextTheme = state.selectedTheme === themeName ? "" : themeName;
  state.selectedTheme = nextTheme;
  state.highlightedSubmissionId = "";
  syncThemeSelects();
  renderAll();
}

function ensureSubmissionVisible(submission) {
  if (!submission) return;
  const isVisible = () => filteredSubmissions().some((item) => item.id === submission.id);

  if (isVisible()) return;

  state.selectedTheme = "";
  syncThemeSelects();

  if (state.selectedYear !== "all" && String(submission.year) !== state.selectedYear) {
    state.selectedYear = String(submission.year);
    d3.select("#year-select").property("value", state.selectedYear);
  }

  const search = state.search.trim().toLowerCase();
  if (search && !submissionMatchesSearch(submission, search)) {
    state.search = "";
    d3.select("#search-input").property("value", "");
  }
}

function navigateToSubmission(point) {
  const submission = submissionForEmbeddingPoint(point);
  if (!submission) return;

  ensureSubmissionVisible(submission);
  state.highlightedSubmissionId = submission.id;
  renderAll();
  requestAnimationFrame(() => {
    requestAnimationFrame(() => scrollToHighlightedSubmission());
  });
}

function scrollToHighlightedSubmission() {
  if (!state.highlightedSubmissionId) return;
  const el = document.querySelector(
    `.paper-item[data-id="${CSS.escape(state.highlightedSubmissionId)}"]`
  );
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function embeddingActionHint() {
  const action = isTouchLike() ? "Tap" : "Click";
  return `<em>${action} to view this submission below</em>`;
}

function embeddingDefaultNote() {
  const count = embeddingDisplayPoints().length;
  if (state.highlightedSubmissionId) {
    return "Jumped to highlighted submission below — all assigned topics are shown on the card";
  }
  if (state.selectedTheme) {
    const clearHint = isTouchLike() ? "choose “All topics” to clear" : "choose “All topics” to clear";
    return `Showing ${count} submissions with “${state.selectedTheme}” in any assigned topic · dots stay colored by primary topic · ${clearHint}`;
  }
  return isTouchLike()
    ? `${count} submissions · dots colored by primary topic · tap a dot to view all assigned topics below · use dropdown to filter by any topic`
    : `${count} submissions · dots colored by primary topic · click a dot to view all assigned topics below · use dropdown to filter by any topic`;
}

function renderEmbeddingNote(note) {
  note.text(embeddingDefaultNote());
}

function embeddingPointTooltip(point) {
  const submission = submissionForEmbeddingPoint(point);
  const topics = submission ? assignedTopics(submission) : [];
  const primary = topics[0];
  const topicLines = topics
    .map((topic, index) => {
      const label = index === 0 ? `${topic} (primary)` : topic;
      return `<span style="color:${themeColor(topic)}">■</span> ${label}`;
    })
    .join("<br/>");
  const parts = [
    `<strong>${truncateLabel(point.title, s(72))}</strong>`,
    `${point.year}${point.poster_number ? ` · Poster #${point.poster_number}` : ""}`,
    topicLines ? `<strong>Assigned topics:</strong><br/>${topicLines}` : "",
    primary ? `<span style="color:${themeColor(primary)}">Dot color = primary topic</span>` : "",
  ];
  parts.push(embeddingActionHint());
  return parts.filter(Boolean).join("<br/>");
}

function themeLegendTooltip(themeName) {
  const count = embeddingDisplayPoints().filter(
    (point) => embeddingPointPrimaryTheme(point) === themeName
  ).length;
  return [
    `<strong>${themeName}</strong>`,
    `${count} visible with this primary topic`,
    "Dropdown filter matches any assigned topic on a submission",
  ].join("<br/>");
}

function renderKpis(filtered) {
  const { metadata } = state.data;
  const cards = [
    { label: "Total submissions", value: metadata.total_count.toLocaleString(), icon: "submissions", tone: "blue" },
    { label: "Matching filter", value: filtered.length.toLocaleString(), icon: "filter", tone: "pink" },
    { label: "Research themes", value: String(researchThemeNames().length), icon: "keywords", tone: "green" },
    { label: "Years covered", value: String(metadata.years.length), icon: "years", tone: "navy" },
  ];

  const row = d3.select("#kpi-row");
  const card = row.selectAll(".kpi-card").data(cards).join("div").attr("class", "kpi-card");
  card.selectAll("*").remove();
  card
    .append("div")
    .attr("class", (d) => `kpi-icon ${d.tone}`)
    .html((d) => KPI_ICONS[d.icon]);
  const body = card.append("div");
  body.append("div").attr("class", "label").text((d) => d.label);
  body.append("div").attr("class", "value").text((d) => d.value);
}

function renderYearControls() {
  const years = state.data.metadata.years;
  const yearSelect = d3.select("#year-select");
  yearSelect.selectAll("option:not(:first-child)").remove();
  yearSelect
    .selectAll("option.year")
    .data(years)
    .join("option")
    .attr("class", "year")
    .attr("value", (d) => String(d))
    .text((d) => d);

  const chips = d3.select("#year-chips");
  const chipData = ["all", ...years.map(String)];
  chips
    .selectAll(".year-chip")
    .data(chipData)
    .join("button")
    .attr("class", (d) => `year-chip${d === state.selectedYear ? " active" : ""}`)
    .text((d) => (d === "all" ? "All years" : d))
    .on("click", (_, d) => {
      state.selectedYear = d;
      d3.select("#year-select").property("value", d);
      renderAll();
    });
}

function renderEmbeddingThemeSelect() {
  const select = d3.select("#embedding-theme-select");
  if (select.empty()) return;

  const topics = googleTopicNames();
  select.selectAll("option:not(:first-child)").remove();
  select
    .selectAll("option.theme")
    .data(topics)
    .join("option")
    .attr("class", "theme")
    .attr("value", String)
    .text(String);
  select.property("value", state.selectedTheme);
}

function renderThemeSelect(counts) {
  const select = d3.select("#theme-select");
  const countMap = new Map(counts.map((d) => [d.text, d.count]));
  const topics = googleTopicNames();
  select.selectAll("option:not(:first-child)").remove();
  select
    .selectAll("option.theme")
    .data(topics)
    .join("option")
    .attr("class", "theme")
    .attr("value", String)
    .text((theme) => {
      const count = countMap.get(theme) || 0;
      return count ? `${theme} (${count})` : theme;
    });
  select.property("value", state.selectedTheme);
}

function renderThemeBars(counts) {
  const container = d3.select("#theme-bars");
  if (isPhoneLayout()) {
    renderPhoneThemeBarChart(container, {
      data: counts,
      getLabel: (d) => d.text,
      getValue: (d) => d.count,
      getBarFill: (d) => themeColor(d.text),
      onBarTooltip: (event, d) => showTooltip(`<strong>${d.text}</strong><br/>${d.count} submissions`, event),
    });
    return;
  }

  container.selectAll("*").remove();

  const width = container.node().clientWidth || s(360);
  const data = counts;
  const leftMargin = themeBarLabelWidth(width);
  const rowHeight = themeBarRowHeight();
  const margin = { top: s(8), right: s(12), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + data.length * rowHeight;
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("width", "100%").style("height", `${height}px`);
  const innerW = width - margin.left - margin.right;
  const plotW = themeBarPlotWidth(innerW, data, (d) => String(d.count));
  const x = d3.scaleLinear().domain([0, d3.max(data, (d) => d.count) || 1]).range([0, plotW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.text))
    .range([0, data.length * rowHeight])
    .padding(0.2);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  g.selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", 0)
    .attr("y", (d) => y(d.text))
    .attr("height", y.bandwidth())
    .attr("width", (d) => x(d.count))
    .attr("fill", (d) => themeColor(d.text))
    .attr("rx", s(4))
    .on("mousemove", (event, d) => showTooltip(`<strong>${d.text}</strong><br/>${d.count} submissions`, event))
    .on("mouseleave", hideTooltip);

  drawThemeBarLabels(g, data, y, (d) => d.text);

  g.selectAll("text.value")
    .data(data)
    .join("text")
    .attr("class", "value")
    .attr("x", (d) => x(d.count) + s(6))
    .attr("y", (d) => y(d.text) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", themeFs(10))
    .text((d) => d.count);
}

function renderYearChart() {
  const container = d3.select("#year-chart");
  container.selectAll("*").remove();

  const counts = Object.entries(state.data.stats.counts_by_year)
    .map(([year, count]) => ({ year: +year, count }))
    .sort((a, b) => a.year - b.year);

  const width = chartContainerWidth(container);
  const height = isPhoneLayout() ? gs(200) : s(300);
  const margin = isPhoneLayout()
    ? { top: gs(12), right: gs(8), bottom: gs(42), left: gs(28) }
    : { top: s(24), right: s(24), bottom: s(36), left: s(44) };
  const svg = appendChartSvg(container, width, height);

  const x = d3
    .scalePoint()
    .domain(counts.map((d) => d.year))
    .range([margin.left, width - margin.right])
    .padding(isPhoneLayout() ? 0.15 : 0.5);
  const y = d3
    .scaleLinear()
    .domain([0, d3.max(counts, (d) => d.count) || 1])
    .nice()
    .range([height - margin.bottom, margin.top]);

  const line = d3
    .line()
    .x((d) => x(d.year))
    .y((d) => y(d.count))
    .curve(d3.curveMonotoneX);

  const g = svg.append("g");

  g.append("path")
    .datum(counts)
    .attr("fill", "none")
    .attr("stroke", CCN_COLORS.blue)
    .attr("stroke-width", isPhoneLayout() ? gs(2) : s(3))
    .attr("d", line);

  g.selectAll("circle")
    .data(counts)
    .join("circle")
    .attr("cx", (d) => x(d.year))
    .attr("cy", (d) => y(d.count))
    .attr("r", (d) => (String(d.year) === state.selectedYear ? (isPhoneLayout() ? gs(4.5) : s(7)) : isPhoneLayout() ? gs(3.5) : s(5)))
    .attr("fill", (d) => (String(d.year) === state.selectedYear ? CCN_COLORS.pink : CCN_COLORS.green))
    .attr("stroke", CCN_COLORS.navy)
    .attr("stroke-width", isPhoneLayout() ? gs(1.5) : s(2))
    .style("cursor", "pointer")
    .on("click", (_, d) => {
      state.selectedYear = String(d.year);
      d3.select("#year-select").property("value", state.selectedYear);
      renderAll();
    })
    .on("mousemove", (event, d) => showTooltip(`<strong>${d.year}</strong><br/>${d.count} submissions`, event))
    .on("mouseleave", hideTooltip);

  g.append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(d3.axisBottom(x).tickFormat(d3.format("d")).tickSizeOuter(0))
    .call((sel) =>
      sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(10))
    )
    .call((sel) => {
      if (isPhoneLayout()) {
        sel
          .selectAll("text")
          .attr("transform", "rotate(-40)")
          .attr("text-anchor", "end")
          .attr("dx", gs(-2))
          .attr("dy", gs(3));
      }
    })
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  g.append("g")
    .attr("transform", `translate(${margin.left},0)`)
    .call(d3.axisLeft(y).ticks(isPhoneLayout() ? 4 : 5))
    .call((sel) =>
      sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(10))
    )
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));
}

function renderResearchThemeDeltas(submissions) {
  const container = d3.select("#theme-delta-chart");
  container.selectAll("*").remove();

  renderDeltaYearControls();
  const { pair, rows } = researchThemeDeltas(submissions, state.deltaFromYear, state.deltaToYear);
  const sub = d3.select("#theme-delta-sub");

  if (!pair || !rows.length) {
    sub.text("Pick two different years to compare theme counts.");
    container.append("p").style("color", CCN_COLORS.muted).text("No theme data for the selected years.");
    return;
  }

  state.deltaFromYear = pair.fromYear;
  state.deltaToYear = pair.toYear;
  d3.select("#delta-from-year").property("value", pair.fromYear);
  d3.select("#delta-to-year").property("value", pair.toYear);
  sub.text(`${pair.fromYear} → ${pair.toYear} · change in share of submissions (percentage points)`);

  const deltaTooltip = (d) =>
    [
      `<strong>${d.theme}</strong>`,
      `${d.fromYear}: ${d.fromCount} / ${d.fromYearTotal} (${d.fromPct.toFixed(1)}%)`,
      `${d.toYear}: ${d.toCount} / ${d.toYearTotal} (${d.toPct.toFixed(1)}%)`,
      `Change: ${formatDeltaPct(d.delta)}`,
    ].join("<br/>");

  if (isPhoneLayout()) {
    renderPhoneThemeBarChart(container, {
      data: rows,
      getLabel: (d) => d.theme,
      getValue: (d) => Math.abs(d.delta),
      getBarFill: (d) => (d.delta >= 0 ? CCN_COLORS.green : CCN_COLORS.pink),
      onBarTooltip: (event, d) => showTooltip(deltaTooltip(d), event),
      valueFormat: (_, d) => formatDeltaPct(d.delta),
    });
    return;
  }

  const width = container.node().clientWidth || s(480);
  const leftMargin = themeBarLabelWidth(width);
  const rowHeight = themeBarRowHeight();
  const margin = { top: s(8), right: s(12), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + rows.length * rowHeight;
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("width", "100%").style("height", `${height}px`);
  const innerW = width - margin.left - margin.right;
  const maxAbs = d3.max(rows, (d) => Math.abs(d.delta)) || 1;
  const plotW = themeBarPlotWidth(innerW, rows, (d) => formatDeltaPct(d.delta));
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  const x = d3.scaleLinear().domain([0, maxAbs]).range([0, plotW]);
  const y = d3
    .scaleBand()
    .domain(rows.map((d) => d.theme))
    .range([0, rows.length * rowHeight])
    .padding(0.22);

  g.selectAll("rect")
    .data(rows)
    .join("rect")
    .attr("x", 0)
    .attr("y", (d) => y(d.theme))
    .attr("height", y.bandwidth())
    .attr("width", (d) => x(Math.abs(d.delta)))
    .attr("fill", (d) => (d.delta >= 0 ? CCN_COLORS.green : CCN_COLORS.pink))
    .attr("rx", s(4))
    .on("mousemove", (event, d) => showTooltip(deltaTooltip(d), event))
    .on("mouseleave", hideTooltip);

  drawThemeBarLabels(g, rows, y, (d) => d.theme);

  g.selectAll("text.value")
    .data(rows)
    .join("text")
    .attr("class", "value")
    .attr("x", (d) => x(Math.abs(d.delta)) + s(6))
    .attr("y", (d) => y(d.theme) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", themeFs(10))
    .text((d) => formatDeltaPct(d.delta));
}

function pointMatchesThemeFilter(point) {
  if (!state.selectedTheme) return true;
  const submission = submissionForEmbeddingPoint(point);
  if (submission) return assignedTopics(submission).includes(state.selectedTheme);
  return false;
}

function pointIsHighlighted(point) {
  const submission = submissionForEmbeddingPoint(point);
  return Boolean(submission && submission.id === state.highlightedSubmissionId);
}

function renderEmbeddingCluster() {
  const container = d3.select("#embedding-chart");
  container.selectAll("*").remove();

  const note = d3.select("#embedding-note");
  const points = embeddingDisplayPoints();
  if (!points.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("No submissions with map coordinates match the current filters.");
    note.text("");
    return;
  }

  const width = chartContainerWidth(container);
  const mobileLegend = useStackedChartLegend(width) || isPhoneLayout();
  const legendFont = isPhoneLayout() ? chartThemePx(7) : themeLabelPx(10);
  const legendItemHeight = isPhoneLayout() ? legendFont * 2.2 : legendFont * 1.5;
  const legendThemes = themeLegendThemes();
  const legendCols = isPhoneLayout() ? 1 : mobileLegend ? (width < 520 ? 1 : 2) : 1;
  const legendTitleHeight = legendFont * 1.6;
  const legendRows = mobileLegend ? Math.ceil(legendThemes.length / legendCols) : legendThemes.length;
  const legendBlock = mobileLegend
    ? legendTitleHeight + legendRows * legendItemHeight + (isPhoneLayout() ? gs(10) : s(16))
    : 0;
  const margin = mobileLegend
    ? isPhoneLayout()
      ? { top: gs(8), right: gs(8), bottom: gs(8), left: gs(8) }
      : { top: s(12), right: s(12), bottom: s(12), left: s(12) }
    : { top: s(20), right: s(320), bottom: s(20), left: s(20) };
  const plotSide = isPhoneLayout()
    ? width - margin.left - margin.right
    : mobileLegend
      ? s(300)
      : s(520);
  const plotHeight = mobileLegend ? margin.top + plotSide + margin.bottom : plotSide;
  const height = mobileLegend ? plotHeight + legendBlock : plotHeight;
  const svg = appendChartSvg(container, width, height);
  const color = (theme) => themeColor(theme);
  const plotBottom = mobileLegend ? plotHeight - margin.bottom : height - margin.bottom;
  const pointRadius = isPhoneLayout() ? { base: 1, selected: 1.375, highlighted: 1.5 } : { base: 7, selected: 8.5, highlighted: 10 };

  const x = d3.scaleLinear().domain(d3.extent(points, (d) => d.x)).nice().range([margin.left, width - margin.right]);
  const y = d3.scaleLinear().domain(d3.extent(points, (d) => d.y)).nice().range([plotBottom, margin.top]);

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", margin.top)
    .attr("width", width - margin.left - margin.right)
    .attr("height", plotBottom - margin.top)
    .attr("fill", "rgba(197,224,243,0.04)")
    .attr("rx", isPhoneLayout() ? gs(8) : s(12));

  const handlePointNavigate = (_, point) => {
    navigateToSubmission(point);
  };

  const pointStyle = (point) => {
    const highlighted = pointIsHighlighted(point);
    const matches = pointMatchesThemeFilter(point);
    const filtered = Boolean(state.selectedTheme);
    let radius = isPhoneLayout() ? gs(pointRadius.base) : s(pointRadius.base);
    if (highlighted) radius = isPhoneLayout() ? gs(pointRadius.highlighted) : s(pointRadius.highlighted);
    else if (matches && filtered) radius = isPhoneLayout() ? gs(pointRadius.selected) : s(pointRadius.selected);
    return {
      radius,
      opacity: !filtered || matches ? 0.92 : 0.14,
      stroke: highlighted ? CCN_COLORS.white : matches && filtered ? CCN_COLORS.pink : CCN_COLORS.navy,
      strokeWidth: highlighted
        ? isPhoneLayout()
          ? gs(2.5)
          : s(2.5)
        : matches && filtered
          ? isPhoneLayout()
            ? gs(1.75)
            : s(2)
          : isPhoneLayout()
            ? gs(1)
            : s(1.25),
    };
  };

  const pointGroups = svg
    .append("g")
    .attr("class", "embedding-points")
    .selectAll("g.embedding-point-group")
    .data(points, (d) => d.id)
    .join("g")
    .attr("class", "embedding-point-group")
    .attr("transform", (d) => `translate(${x(d.x)},${y(d.y)})`)
    .style("cursor", "pointer")
    .style("pointer-events", isTouchLike() ? "none" : "auto");

  pointGroups.each(function renderPrimaryPoint(point) {
    const group = d3.select(this);
    group.selectAll("*").remove();
    const style = pointStyle(point);
    appendPrimaryTopicDot(group, style.radius, embeddingPointPrimaryTheme(point), {
      opacity: style.opacity,
      stroke: style.stroke,
      strokeWidth: style.strokeWidth,
    });
  });

  if (isTouchLike()) {
    svg
      .selectAll("circle.embedding-hit")
      .data(points, (d) => d.id)
      .join("circle")
      .attr("class", "embedding-hit")
      .attr("cx", (d) => x(d.x))
      .attr("cy", (d) => y(d.y))
      .attr("r", isPhoneLayout() ? gs(16) : s(18))
      .attr("fill", "transparent")
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        event.stopPropagation();
        handlePointNavigate(null, d);
      });
  } else {
    pointGroups
      .on("mousemove", (event, d) => showTooltip(embeddingPointTooltip(d), event))
      .on("mouseleave", hideTooltip)
      .on("click", handlePointNavigate);
  }

  const legend = svg.append("g");
  if (mobileLegend) {
    const colWidth = (width - margin.left - margin.right) / legendCols;
    const legendMarker = isPhoneLayout() ? gs(8) : s(12);
    const legendTextX = isPhoneLayout() ? gs(12) : s(18);
    legend.attr("transform", `translate(${margin.left}, ${plotHeight + (isPhoneLayout() ? gs(6) : s(8))})`);
    legend
      .append("text")
      .attr("class", "embedding-legend-title")
      .attr("x", 0)
      .attr("y", legendFont * 0.85)
      .attr("fill", CCN_COLORS.muted)
      .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(10))
      .style("font-weight", 600)
      .text("Primary topic (dot color)");
    legend
      .selectAll("g.legend-item")
      .data(legendThemes)
      .join("g")
      .attr("class", "legend-item")
      .attr("transform", (_, i) => {
        const col = i % legendCols;
        const row = Math.floor(i / legendCols);
        return `translate(${col * colWidth}, ${legendTitleHeight + row * legendItemHeight})`;
      })
      .on("mousemove", isTouchLike() ? null : (event, themeName) => showTooltip(themeLegendTooltip(themeName), event))
      .on("mouseleave", isTouchLike() ? null : hideTooltip)
      .each(function appendMobileLegendItem() {
        const item = d3.select(this);
        item
          .append("rect")
          .attr("width", legendMarker)
          .attr("height", legendMarker)
          .attr("rx", isPhoneLayout() ? gs(2) : s(3))
          .attr("y", legendFont * 0.15)
          .attr("fill", (d) => color(d))
          .attr("stroke", (d) => (d === state.selectedTheme ? CCN_COLORS.pink : "transparent"))
          .attr("stroke-width", isPhoneLayout() ? gs(1.5) : s(2));
        item
          .append("text")
          .attr("x", legendTextX)
          .attr("y", legendFont * 0.85)
          .attr("fill", CCN_COLORS.muted)
          .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(10))
          .text((d) => fitLegendLabel(d, colWidth - legendTextX, legendFont));
      });
  } else {
    const legendRoot = legend.attr("transform", `translate(${width - margin.right + s(12)}, ${margin.top})`);
    legendRoot
      .append("text")
      .attr("class", "embedding-legend-title")
      .attr("x", 0)
      .attr("y", legendFont * 0.85)
      .attr("fill", CCN_COLORS.muted)
      .style("font-size", themeFs(10))
      .style("font-weight", 600)
      .text("Primary topic (dot color)");

    const legendItems = legendRoot
      .selectAll("g.legend-item")
      .data(legendThemes)
      .join("g")
      .attr("class", "legend-item")
      .attr("transform", (_, i) => `translate(0, ${legendTitleHeight + i * legendItemHeight})`)
      .on("mousemove", isTouchLike() ? null : (event, themeName) => showTooltip(themeLegendTooltip(themeName), event))
      .on("mouseleave", isTouchLike() ? null : hideTooltip);

    legendItems
      .append("rect")
      .attr("width", s(12))
      .attr("height", s(12))
      .attr("rx", s(3))
      .attr("y", legendFont * 0.15)
      .attr("fill", (d) => color(d))
      .attr("stroke", (d) => (d === state.selectedTheme ? CCN_COLORS.pink : "transparent"))
      .attr("stroke-width", s(2));

    legendItems
      .append("text")
      .attr("x", s(18))
      .attr("y", legendFont * 0.85)
      .attr("fill", CCN_COLORS.muted)
      .style("font-size", themeFs(10))
      .text((d) => fitLegendLabel(d, s(280), legendFont));
  }

  renderEmbeddingNote(note);
}

function renderPaperList() {
  const submissions = displaySubmissions();
  const list = d3.select("#paper-list");
  const countEl = d3.select("#results-count");
  countEl.selectAll("*").remove();

  const countLabel = state.selectedTheme
    ? `${submissions.length} submissions with “${state.selectedTheme}” in any assigned topic`
    : `${submissions.length} matching submissions`;
  countEl.append("span").text(countLabel);

  const items = list
    .selectAll(".paper-item")
    .data(submissions)
    .join("div")
    .attr("class", (d) => `paper-item${d.id === state.highlightedSubmissionId ? " highlighted" : ""}`)
    .attr("data-id", (d) => d.id);
  items.selectAll("*").remove();

  items
    .append("h3")
    .append("a")
    .attr("href", (d) => d.source_url)
    .attr("target", "_blank")
    .attr("rel", "noopener")
    .text((d) => d.title);

  items
    .append("div")
    .attr("class", "meta")
    .text((d) =>
      `${d.year}${d.poster_number ? ` · Poster ${d.poster_number}` : ""}${d.authors ? ` · ${d.authors}` : ""}`
    );

  items.each(function renderTags(d) {
    const tagData = assignedTopics(d);
    const tags = d3.select(this).append("div").attr("class", "keyword-tags");
    tags
      .selectAll(".keyword-tag")
      .data(tagData)
      .join("span")
      .attr("class", (theme, index) =>
        `keyword-tag topic-tag${index === 0 ? " topic-tag-primary" : ""}${theme === state.selectedTheme ? " active" : ""}`
      )
      .style("--topic-color", (theme) => themeColor(theme))
      .text((theme, index) => (index === 0 ? `${theme} (primary)` : theme));
  });
}

function renderAll() {
  const scrollSnapshot = { x: window.scrollX, y: window.scrollY };
  removeChartScrollWrappers();
  const submissions = filteredSubmissions();
  const primaryCounts = primaryThemeCounts(submissions);
  const trendSubmissions = submissionsForThemeTrends();

  renderKpis(submissions);
  renderThemeSelect(primaryCounts);
  renderEmbeddingThemeSelect();
  renderYearChart();
  renderThemeBars(primaryCounts);
  renderResearchThemeDeltas(trendSubmissions);
  renderEmbeddingCluster();
  renderPaperList();

  d3.select("#year-chips")
    .selectAll(".year-chip")
    .classed("active", (d) => d === state.selectedYear);

  restorePageScroll(scrollSnapshot.x, scrollSnapshot.y);
}

async function init() {
  ensureD3();

  const csvRows = await d3.csv("data/abstracts.csv");
  if (!csvRows?.length) {
    throw new Error("Could not load data/abstracts.csv");
  }

  state.data = buildStateFromCsv(csvRows);
  state.embeddings = buildEmbeddingsFromSubmissions(state.data.submissions);
  buildThemeClassifier();

  renderYearControls();
  renderDeltaYearControls();

  d3.select("#year-select").on("change", (event) => {
    state.selectedYear = event.target.value;
    state.highlightedSubmissionId = "";
    renderAll();
  });

  d3.select("#search-input").on("input", (event) => {
    state.search = event.target.value;
    state.highlightedSubmissionId = "";
    renderAll();
  });

  d3.select("#theme-select").on("change", (event) => {
    state.selectedTheme = event.target.value;
    state.highlightedSubmissionId = "";
    syncThemeSelects();
    renderAll();
  });

  d3.select("#embedding-theme-select").on("change", (event) => {
    state.selectedTheme = event.target.value;
    state.highlightedSubmissionId = "";
    syncThemeSelects();
    renderAll();
  });

  d3.select("#delta-from-year").on("change", (event) => {
    state.deltaFromYear = event.target.value;
    renderResearchThemeDeltas(submissionsForThemeTrends());
  });

  d3.select("#delta-to-year").on("change", (event) => {
    state.deltaToYear = event.target.value;
    renderResearchThemeDeltas(submissionsForThemeTrends());
  });

  renderAll();

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (shouldReflowOnResize()) renderAll();
    }, 150);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => init().catch(handleInitError));
} else {
  init().catch(handleInitError);
}

function handleInitError(error) {
  console.error(error);
  showError(`Failed to load dashboard: ${error.message}`);
}
