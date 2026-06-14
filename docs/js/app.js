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
  const barH = gs(8);
  const rowGap = gs(3);
  const blockGap = gs(8);
  const maxVal = d3.max(data, getValue) || 1;
  const x = d3.scaleLinear().domain([0, maxVal]).range([0, innerW]);

  const rows = data.map((item) => {
    const lines = wrapThemeLabel(getLabel(item), innerW, labelFont);
    const labelH = lines.length * labelFont * 1.15;
    return { item, lines, rowHeight: labelH + rowGap + barH + blockGap };
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

    const valueInside = barWidth > innerW * 0.72;
    g.append("text")
      .attr("x", valueInside ? barWidth - gs(4) : barWidth + gs(4))
      .attr("y", barY + barH / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", valueInside ? "end" : "start")
      .attr("fill", CCN_COLORS.white)
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
  CCN_COLORS.pink,
  CCN_COLORS.blue,
  CCN_COLORS.green,
  "#9ecae1",
  "#fdae9f",
  "#a8ddb5",
  "#c7e9c0",
  "#fdd0a2",
  "#bcbddc",
  "#ffed6f",
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

const state = {
  data: null,
  embeddings: null,
  googleTopics: null,
  selectedYear: "all",
  search: "",
  selectedTheme: "",
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

function primaryTheme(submission) {
  if (submission.primary_theme) return submission.primary_theme;
  return submissionResearchTheme(submission);
}

function secondaryTopics(submission) {
  return submission.secondary_topics || [];
}

function submissionMatchesSearch(item, search) {
  const theme = primaryTheme(item);
  const secondaries = secondaryTopics(item);
  return (
    item.title.toLowerCase().includes(search) ||
    item.authors.toLowerCase().includes(search) ||
    (theme || "").toLowerCase().includes(search) ||
    secondaries.some((topic) => topic.toLowerCase().includes(search)) ||
    (item.topic_area || "").toLowerCase().includes(search)
  );
}

function filteredSubmissions() {
  const { submissions } = state.data;
  const search = state.search.trim().toLowerCase();

  return submissions.filter((item) => {
    const yearOk = state.selectedYear === "all" || String(item.year) === state.selectedYear;
    const theme = primaryTheme(item);
    const searchOk = !search || submissionMatchesSearch(item, search);
    const themeOk = !state.selectedTheme || theme === state.selectedTheme;
    return yearOk && searchOk && themeOk;
  });
}

function primaryThemeCounts(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    const theme = primaryTheme(item);
    if (!theme) return;
    counts.set(theme, (counts.get(theme) || 0) + 1);
  });
  return [...counts.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count);
}

function secondaryTopicCounts(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    secondaryTopics(item).forEach((topic) => {
      counts.set(topic, (counts.get(topic) || 0) + 1);
    });
  });
  return [...counts.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count);
}

function primaryThemeDistribution(submissions) {
  return primaryThemeCounts(submissions);
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

function researchThemeNames() {
  if (state.googleTopics?.enabled && state.googleTopics.topics?.length) {
    return state.googleTopics.topics;
  }
  if (state.embeddings?.clusters?.length) {
    return state.embeddings.clusters.map((c) => c.name);
  }
  return [];
}

function embeddingClusterMap() {
  return state.googleTopics?.embedding_cluster_map || {};
}

function mapClusterToTheme(clusterName) {
  if (!clusterName) return null;
  return embeddingClusterMap()[clusterName] || clusterName;
}

function buildThemeClassifier() {
  const profiles = new Map();
  researchThemeNames().forEach((name) => profiles.set(name, new Map()));

  state.data?.submissions?.forEach((submission) => {
    const theme = submission.primary_theme;
    if (!theme || !profiles.has(theme)) return;
    const weights = profiles.get(theme);
    tokenize(submission.title).forEach((term) => weights.set(term, (weights.get(term) || 0) + 1));
    tokenize(submission.abstract).forEach((term) => weights.set(term, (weights.get(term) || 0) + 1));
  });

  state.embeddings?.points?.forEach((point) => {
    const theme = mapClusterToTheme(point.cluster_name);
    if (!theme || !profiles.has(theme)) return;
    const weights = profiles.get(theme);
    tokenize(point.title).forEach((term) => weights.set(term, (weights.get(term) || 0) + 1));
    tokenize(point.abstract).forEach((term) => weights.set(term, (weights.get(term) || 0) + 1));
  });

  state.themeProfiles = profiles;
}

function embeddingPointForSubmission(submission) {
  if (!state.embeddings?.points) return null;
  return state.embeddings.points.find(
    (p) =>
      p.id === submission.id ||
      (submission.year === 2026 && String(p.poster_number) === String(submission.poster_number))
  );
}

function submissionResearchTheme(submission) {
  if (submission.primary_theme) return submission.primary_theme;

  const point = embeddingPointForSubmission(submission);
  if (point?.cluster_name) return mapClusterToTheme(point.cluster_name);

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
    const theme = primaryTheme(item);
    if (!theme) return;
    const year = String(item.year);
    if (!counts.has(year)) counts.set(year, new Map());
    const yearMap = counts.get(year);
    yearMap.set(theme, (yearMap.get(theme) || 0) + 1);
  });
  return counts;
}

function themeTotals(submissions) {
  const totals = new Map();
  submissions.forEach((item) => {
    const theme = primaryTheme(item);
    if (!theme) return;
    totals.set(theme, (totals.get(theme) || 0) + 1);
  });
  return totals;
}

function themeCumulativeByYear(years, byYear, themes) {
  const cumulative = new Map();
  const running = new Map(themes.map((theme) => [theme, 0]));

  years.forEach((year) => {
    const yearKey = String(year);
    const yearCounts = byYear.get(yearKey) || new Map();
    themes.forEach((theme) => {
      running.set(theme, running.get(theme) + (yearCounts.get(theme) || 0));
    });
    cumulative.set(yearKey, new Map(running));
  });

  return cumulative;
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

function researchThemeDeltas(submissions) {
  const themes = researchThemeNames();
  if (!themes.length) return { pair: null, rows: [] };

  const years = [...state.data.metadata.years].sort((a, b) => a - b);
  const byYear = themeCountsByYear(submissions);
  const pair = latestComparableYearPair(years, byYear, themes);
  if (!pair) return { pair: null, rows: [] };

  const rows = themes
    .map((theme) => {
      const fromCount = byYear.get(pair.fromYear)?.get(theme) || 0;
      const toCount = byYear.get(pair.toYear)?.get(theme) || 0;
      return {
        theme,
        fromYear: pair.fromYear,
        toYear: pair.toYear,
        fromCount,
        toCount,
        delta: toCount - fromCount,
      };
    })
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  return { pair, rows };
}

function truncateLabel(text, max = s(28)) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

function clusterMeta(clusterName) {
  const points = state.embeddings?.points?.filter((p) => p.cluster_name === clusterName) || [];
  const summary = state.embeddings?.clusters?.find((c) => c.name === clusterName);
  return {
    name: clusterName,
    count: summary?.count || points.length,
    points,
  };
}

function themeEmbeddingPoints(themeName) {
  return state.embeddings?.points?.filter((p) => mapClusterToTheme(p.cluster_name) === themeName) || [];
}

function displaySubmissions() {
  return filteredSubmissions();
}

function setThemeFilter(themeName) {
  const nextTheme = state.selectedTheme === themeName ? "" : themeName;
  state.selectedTheme = nextTheme;
  d3.select("#theme-select").property("value", state.selectedTheme);
  renderAll();
}

function embeddingActionHint(kind) {
  const action = isTouchLike() ? "Tap" : "Click";
  return kind === "cluster"
    ? `<em>${action} to filter submissions</em>`
    : `<em>${action} to filter by this primary theme</em>`;
}

function embeddingDefaultNote() {
  if (state.selectedTheme) {
    const clearHint = isTouchLike() ? "tap again to clear" : "click again to clear";
    return `Showing submissions with primary theme “${state.selectedTheme}” · ${clearHint}`;
  }
  return isTouchLike()
    ? "Tap a point or legend to filter by primary research theme"
    : "Click a point or legend to filter by primary research theme.";
}

function renderEmbeddingNote(note) {
  note.text(embeddingDefaultNote());
}

function embeddingPointTooltip(point) {
  const primary = mapClusterToTheme(point.cluster_name);
  const parts = [
    `<strong>${truncateLabel(point.title, s(72))}</strong>`,
    point.poster_number ? `Poster #${point.poster_number} · 2026 pending` : "2026 pending",
    `<strong>Primary theme:</strong> ${primary || "—"}`,
    point.cluster_name && point.cluster_name !== primary
      ? `<strong>Embedding cluster:</strong> ${point.cluster_name}`
      : "",
  ];
  if (point.primary_area) parts.push(`<strong>Area:</strong> ${truncateLabel(point.primary_area, s(48))}`);
  parts.push(embeddingActionHint("point"));
  return parts.filter(Boolean).join("<br/>");
}

function clusterLegendTooltip(clusterName) {
  const cluster = clusterMeta(clusterName);
  const areas = new Map();
  cluster.points.forEach((p) => {
    if (!p.primary_area) return;
    areas.set(p.primary_area, (areas.get(p.primary_area) || 0) + 1);
  });
  const topAreas = [...areas.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([area, count]) => `${truncateLabel(area, s(36))} (${count})`)
    .join("<br/>");

  const parts = [
    `<strong>${clusterName}</strong>`,
    `${cluster.count} abstracts in cluster`,
  ];
  if (topAreas) parts.push(`<strong>Top areas:</strong><br/>${topAreas}`);
  parts.push(embeddingActionHint("cluster"));
  return parts.join("<br/>");
}

function themeLegendTooltip(themeName) {
  const points = themeEmbeddingPoints(themeName);
  const areas = new Map();
  points.forEach((p) => {
    if (!p.primary_area) return;
    areas.set(p.primary_area, (areas.get(p.primary_area) || 0) + 1);
  });
  const topAreas = [...areas.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([area, count]) => `${truncateLabel(area, s(36))} (${count})`)
    .join("<br/>");

  const parts = [
    `<strong>${themeName}</strong>`,
    `${points.length} abstracts in the 2026 embedding map`,
  ];
  if (topAreas) parts.push(`<strong>Top areas:</strong><br/>${topAreas}`);
  parts.push(embeddingActionHint("cluster"));
  return parts.join("<br/>");
}

function renderKpis(filtered) {
  const { metadata, stats } = state.data;
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

function renderThemeSelect(counts) {
  const select = d3.select("#theme-select");
  select.selectAll("option:not(:first-child)").remove();
  select
    .selectAll("option.theme")
    .data(counts)
    .join("option")
    .attr("class", "theme")
    .attr("value", (d) => d.text)
    .text((d) => `${d.text} (${d.count})`);
  select.property("value", state.selectedTheme);
}

function renderWordCloud(counts) {
  const container = d3.select("#word-cloud");
  container.selectAll("*").remove();

  const width = container.node().clientWidth || s(800);
  const height = isPhoneLayout() ? gs(220) : s(300);
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .style("height", `${height}px`);
  const top = counts.slice(0, 40);

  if (!top.length) {
    svg.append("text").attr("x", s(20)).attr("y", s(40)).attr("fill", CCN_COLORS.muted).text("No secondary topics for current filter.");
    return;
  }

  if (typeof d3.layout === "undefined" || typeof d3.layout.cloud !== "function") {
    svg
      .append("text")
      .attr("x", s(20))
      .attr("y", s(40))
      .attr("fill", CCN_COLORS.muted)
      .text("Keyword cloud unavailable (d3-cloud failed to load).");
    return;
  }

  const max = d3.max(top, (d) => d.count) || 1;
  const fontSize = (d) => s(12) + (d.count / max) * s(32);
  const colorScale = d3.scaleOrdinal(CHART_PALETTE);
  const scrollSnapshot = { x: window.scrollX, y: window.scrollY };

  d3.layout
    .cloud()
    .size([width, height])
    .words(top.map((d) => ({ text: d.text, size: fontSize(d), count: d.count })))
    .padding(s(5))
    .rotate((_, i) => (i % 2 === 0 ? 0 : 90))
    .font("Open Sans")
    .fontSize((d) => d.size)
    .on("end", (words) => {
      const g = svg.append("g").attr("transform", `translate(${width / 2},${height / 2})`);
      g.selectAll("text")
        .data(words)
        .join("text")
        .style("font-size", (d) => `${d.size}px`)
        .style("font-family", "Open Sans")
        .style("fill", (d) =>
          d.text === state.selectedTheme ? CCN_COLORS.pink : colorScale(d.text)
        )
        .style("cursor", "default")
        .attr("text-anchor", "middle")
        .attr("transform", (d) => `translate(${d.x},${d.y})rotate(${d.rotate})`)
        .text((d) => d.text)
        .on("mousemove", (event, d) => showTooltip(`<strong>${d.text}</strong><br/>${d.count} secondary tags`, event))
        .on("mouseleave", hideTooltip);
      restorePageScroll(scrollSnapshot.x, scrollSnapshot.y);
    })
    .start();
}

function renderThemeBars(counts) {
  const container = d3.select("#theme-bars");
  if (isPhoneLayout()) {
    renderPhoneThemeBarChart(container, {
      data: counts,
      getLabel: (d) => d.text,
      getValue: (d) => d.count,
      getBarFill: (d) => {
        const i = counts.findIndex((row) => row.text === d.text);
        return d.text === state.selectedTheme ? CCN_COLORS.pink : CHART_PALETTE[i % CHART_PALETTE.length];
      },
      onBarClick: (d) => setThemeFilter(d.text),
      onBarTooltip: (event, d) => showTooltip(`<strong>${d.text}</strong><br/>${d.count} submissions`, event),
    });
    return;
  }

  container.selectAll("*").remove();

  const width = container.node().clientWidth || s(360);
  const data = counts;
  const leftMargin = themeBarLabelWidth(width);
  const rowHeight = themeBarRowHeight();
  const margin = { top: s(8), right: s(56), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + data.length * rowHeight;
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("width", "100%").style("height", `${height}px`);
  const innerW = width - margin.left - margin.right;
  const x = d3.scaleLinear().domain([0, d3.max(data, (d) => d.count) || 1]).range([0, innerW]);
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
    .attr("fill", (d, i) =>
      d.text === state.selectedTheme ? CCN_COLORS.pink : CHART_PALETTE[i % CHART_PALETTE.length]
    )
    .attr("rx", s(4))
    .style("cursor", "pointer")
    .on("click", (_, d) => setThemeFilter(d.text))
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

function renderKeywordBars(counts) {
  renderThemeBars(counts);
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

function renderTopicChart(submissions) {
  const container = d3.select("#topic-chart");
  container.selectAll("*").remove();

  const data = primaryThemeDistribution(submissions);
  const width = container.node().clientWidth || (isPhoneLayout() ? gs(320) : s(320));
  const height = isPhoneLayout() ? gs(220) : s(280);
  const radius = Math.min(width, height) / 2 - (isPhoneLayout() ? gs(12) : s(16));

  if (!data.length) {
    container.append("p").style("color", CCN_COLORS.muted).style("font-size", "0.85rem").text("No primary themes in filter.");
    return;
  }

  const total = d3.sum(data, (d) => d.count);
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .append("g")
    .attr("transform", `translate(${width / 2},${height / 2})`);

  const color = d3.scaleOrdinal(CHART_PALETTE);
  const pie = d3.pie().value((d) => d.count).sort(null);
  const arc = d3.arc().innerRadius(radius * 0.52).outerRadius(radius);
  const labelArc = d3.arc().innerRadius(radius * 0.72).outerRadius(radius * 0.72);

  svg
    .selectAll("path")
    .data(pie(data))
    .join("path")
    .attr("d", arc)
    .attr("fill", (_, i) => color(i))
    .attr("stroke", CCN_COLORS.card)
    .attr("stroke-width", isPhoneLayout() ? gs(1.5) : s(2))
    .style("cursor", "pointer")
    .on("click", (_, d) => setThemeFilter(d.data.text))
    .on("mousemove", (event, d) => {
      const pct = ((d.data.count / total) * 100).toFixed(1);
      showTooltip(`<strong>${d.data.text}</strong><br/>${d.data.count} (${pct}%)`, event);
    })
    .on("mouseleave", hideTooltip);

  svg
    .selectAll("text.slice-label")
    .data(pie(data))
    .join("text")
    .attr("class", "slice-label")
    .attr("transform", (d) => `translate(${labelArc.centroid(d)})`)
    .attr("text-anchor", "middle")
    .attr("fill", CCN_COLORS.navy)
    .style("font-size", themeFs(9))
    .style("font-weight", "600")
    .text((d) => (d.data.count / total > 0.08 ? `${Math.round((d.data.count / total) * 100)}%` : ""));
}

function renderResearchThemesOverTime(submissions) {
  const container = d3.select("#themes-over-time-chart");
  container.selectAll("*").remove();

  const themes = researchThemeNames();
  if (!themes.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("Research theme data not loaded.");
    return;
  }

  const years = [...state.data.metadata.years].sort((a, b) => a - b);
  const byYear = themeCountsByYear(submissions);
  const cumulative = themeCumulativeByYear(years, byYear, themes);
  const annualMax =
    d3.max(themes, (theme) => d3.max(years, (year) => byYear.get(String(year))?.get(theme) || 0)) || 1;
  const cumulativeMax =
    d3.max(themes, (theme) => d3.max(years, (year) => cumulative.get(String(year))?.get(theme) || 0)) ||
    1;
  const yMax = Math.max(annualMax, cumulativeMax);

  const width = chartContainerWidth(container);
  const legendCols = legendColumnCount(width);
  const legendFont = isPhoneLayout() ? chartThemePx(7) : themeLabelPx(9);
  const legendRowHeight = isPhoneLayout() ? legendFont * 2.05 : legendFont * 1.75;
  const legendRows = Math.ceil(themes.length / legendCols);
  const legendGap = isPhoneLayout() ? gs(12) : s(40);
  const legendBlock = legendRows * legendRowHeight + (isPhoneLayout() ? gs(8) : s(20));
  const chartHeight = isPhoneLayout() ? gs(210) : s(400);
  const footnoteHeight = (isPhoneLayout() ? chartThemePx(8) : themeLabelPx(9)) + (isPhoneLayout() ? gs(10) : s(16));
  const marginTop = isPhoneLayout() ? gs(12) : s(24);
  const marginBottom = isPhoneLayout() ? gs(36) : s(52);
  const yTitleText = "Submissions per year";
  let marginLeftForYTitle;
  let yTitleCenterX;
  let yTitleFontPx;
  let margin;
  if (isPhoneLayout()) {
    const yTitleFontPx = chartThemePx(7);
    const yTitleTextWidth = measureTextWidth(yTitleText, yTitleFontPx, '"Open Sans", sans-serif');
    const yTickFontPx = chartThemePx(7);
    const yTickLabelWidth = Math.ceil(
      d3.max(d3.scaleLinear().domain([0, yMax]).nice().ticks(4), (t) =>
        measureTextWidth(String(t), yTickFontPx, '"Open Sans", sans-serif')
      ) + gs(2)
    );
    const gapTitleToTicks = 2;
    marginLeftForYTitle = Math.ceil(yTickLabelWidth + gs(1));
    yTitleCenterX = marginLeftForYTitle - yTickLabelWidth - gapTitleToTicks - yTitleTextWidth / 2;
    margin = {
      top: gs(12),
      right: gs(4),
      bottom: gs(36),
      left: marginLeftForYTitle,
    };
  } else {
    yTitleFontPx = themeLabelPx(10);
    const yTitleTextWidth = measureTextWidth(yTitleText, yTitleFontPx);
    const yTickLabelWidth = s(42);
    const yTitleGapFromTicks = s(3);
    const yTitleShiftTowardAxis = s(52);
    const yTitleEdgePad = s(4);
    marginLeftForYTitle = Math.ceil(
      yTitleEdgePad + yTitleTextWidth + yTitleGapFromTicks + yTickLabelWidth
    );
    yTitleCenterX =
      marginLeftForYTitle -
      yTickLabelWidth -
      yTitleGapFromTicks -
      yTitleTextWidth / 2 +
      yTitleShiftTowardAxis;
    margin = {
      top: marginTop,
      right: s(24),
      bottom: marginBottom,
      left: marginLeftForYTitle,
    };
  }
  const height = chartHeight + legendGap + legendBlock + footnoteHeight;
  const svg = appendChartSvg(container, width, height);
  const innerW = width - margin.left - margin.right;
  const innerH = chartHeight - margin.top - margin.bottom;
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const x = d3.scalePoint().domain(years).range([0, innerW]).padding(isPhoneLayout() ? 0.12 : 0.45);
  const y = d3.scaleLinear().domain([0, yMax]).nice().range([innerH, 0]);
  const color = d3.scaleOrdinal(CHART_PALETTE).domain(themes);

  const annualLine = d3
    .line()
    .x((d) => x(d.year))
    .y((d) => y(d.count))
    .curve(d3.curveMonotoneX);

  const cumulativeLine = d3
    .line()
    .x((d) => x(d.year))
    .y((d) => y(d.count))
    .curve(d3.curveMonotoneX);

  themes.forEach((theme) => {
    const annualSeries = years.map((year) => ({
      year,
      count: byYear.get(String(year))?.get(theme) || 0,
      theme,
    }));
    const cumulativeSeries = years.map((year) => ({
      year,
      count: cumulative.get(String(year))?.get(theme) || 0,
      theme,
    }));

    g.append("path")
      .datum(cumulativeSeries)
      .attr("fill", "none")
      .attr("stroke", color(theme))
      .attr("stroke-width", isPhoneLayout() ? gs(1) : s(1.5))
      .attr("stroke-dasharray", isPhoneLayout() ? `${gs(4)} ${gs(3)}` : `${s(5)} ${s(4)}`)
      .attr("opacity", 0.45)
      .attr("d", cumulativeLine);

    g.append("path")
      .datum(annualSeries)
      .attr("fill", "none")
      .attr("stroke", color(theme))
      .attr("stroke-width", isPhoneLayout() ? gs(1.5) : s(2.5))
      .attr("opacity", 0.95)
      .attr("d", annualLine);

    g.selectAll(`.annual-dot-${theme.replace(/[^a-z0-9]/gi, "")}`)
      .data(annualSeries)
      .join("circle")
      .attr("cx", (d) => x(d.year))
      .attr("cy", (d) => y(d.count))
      .attr("r", (d) => (d.count > 0 ? (isPhoneLayout() ? gs(2.5) : s(4)) : 0))
      .attr("fill", color(theme))
      .attr("stroke", CCN_COLORS.navy)
      .attr("stroke-width", isPhoneLayout() ? gs(1) : s(1.5))
      .on("mousemove", (event, d) => {
        const cum = cumulative.get(String(d.year))?.get(theme) || 0;
        showTooltip(
          `<strong>${d.theme}</strong><br/>${d.year}: ${d.count} submissions<br/>Cumulative: ${cum}`,
          event
        );
      })
      .on("mouseleave", hideTooltip);
  });

  g.append("g")
    .attr("transform", `translate(0,${innerH})`)
    .call(d3.axisBottom(x).tickFormat(d3.format("d")).tickPadding(isPhoneLayout() ? gs(8) : s(16)))
    .call(styleThemeAxisLabels)
    .call((sel) => sel.selectAll("text").attr("dy", isPhoneLayout() ? gs(8) : s(14)))
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  g.append("g")
    .call(d3.axisLeft(y).ticks(isPhoneLayout() ? 4 : 5).tickPadding(isPhoneLayout() ? gs(2) : s(8)))
    .call(styleThemeAxisLabels)
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  svg
    .append("text")
    .attr("class", "y-axis-title")
    .attr("transform", `translate(${yTitleCenterX}, ${margin.top + innerH / 2}) rotate(-90)`)
    .attr("text-anchor", "middle")
    .attr("dominant-baseline", "middle")
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(10))
    .text(yTitleText);

  const legendLeft = isPhoneLayout() ? gs(4) : margin.left;
  const legendWidth = isPhoneLayout() ? width - gs(14) : width - margin.left - margin.right;
  const legend = svg.append("g").attr("transform", `translate(${legendLeft}, ${chartHeight + legendGap})`);
  const colWidth = legendWidth / legendCols;
  const legendLineWidth = isPhoneLayout() ? gs(8) : s(14);
  const legendTextX = isPhoneLayout() ? gs(11) : s(18);
  const legendItems = legend
    .selectAll("g")
    .data(themes)
    .join("g")
    .attr("transform", (_, i) => {
      const col = i % legendCols;
      const row = Math.floor(i / legendCols);
      return `translate(${col * colWidth}, ${row * legendRowHeight})`;
    });

  legendItems
    .append("line")
    .attr("x1", 0)
    .attr("x2", legendLineWidth)
    .attr("y1", legendFont * 0.6)
    .attr("y2", legendFont * 0.6)
    .attr("stroke", (d) => color(d))
    .attr("stroke-width", isPhoneLayout() ? gs(1.5) : s(2.5));

  legendItems
    .append("text")
    .attr("x", legendTextX)
    .attr("y", legendFont * 0.72)
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(9))
    .text((d) => fitLegendLabel(d, colWidth - legendTextX, legendFont));

  svg
    .append("text")
    .attr("x", legendLeft)
    .attr("y", chartHeight + legendGap + legendBlock + (isPhoneLayout() ? gs(6) : s(12)))
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(9))
    .text("Solid = annual count · dashed = cumulative total");
}

function renderResearchThemeTotals(submissions) {
  const container = d3.select("#theme-totals-chart");
  container.selectAll("*").remove();

  const themes = researchThemeNames();
  const totals = themeTotals(submissions);
  const data = themes
    .map((theme) => ({ theme, count: totals.get(theme) || 0 }))
    .sort((a, b) => b.count - a.count);

  if (!data.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("No theme totals available.");
    return;
  }

  if (isPhoneLayout()) {
    const color = d3.scaleOrdinal(CHART_PALETTE).domain(themes);
    renderPhoneThemeBarChart(container, {
      data,
      getLabel: (d) => d.theme,
      getValue: (d) => d.count,
      getBarFill: (d) => color(d.theme),
      onBarTooltip: (event, d) => showTooltip(`<strong>${d.theme}</strong><br/>${d.count} total submissions`, event),
    });
    return;
  }

  const width = container.node().clientWidth || s(480);
  const leftMargin = themeBarLabelWidth(width);
  const rowHeight = themeBarRowHeight();
  const margin = { top: s(8), right: s(52), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + data.length * rowHeight;
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("width", "100%").style("height", `${height}px`);
  const innerW = width - margin.left - margin.right;
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  const x = d3.scaleLinear().domain([0, d3.max(data, (d) => d.count) || 1]).range([0, innerW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.theme))
    .range([0, data.length * rowHeight])
    .padding(0.22);
  const color = d3.scaleOrdinal(CHART_PALETTE).domain(themes);

  g.selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", 0)
    .attr("y", (d) => y(d.theme))
    .attr("height", y.bandwidth())
    .attr("width", (d) => x(d.count))
    .attr("fill", (d) => color(d.theme))
    .attr("rx", s(4))
    .on("mousemove", (event, d) => showTooltip(`<strong>${d.theme}</strong><br/>${d.count} total submissions`, event))
    .on("mouseleave", hideTooltip);

  drawThemeBarLabels(g, data, y, (d) => d.theme);

  g.selectAll("text.value")
    .data(data)
    .join("text")
    .attr("class", "value")
    .attr("x", (d) => x(d.count) + s(6))
    .attr("y", (d) => y(d.theme) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", themeFs(10))
    .text((d) => d.count);
}

function renderResearchThemeDeltas(submissions) {
  const container = d3.select("#theme-delta-chart");
  container.selectAll("*").remove();

  const { pair, rows } = researchThemeDeltas(submissions);
  const sub = d3.select("#theme-delta-sub");

  if (!pair || !rows.length) {
    sub.text("Not enough theme history for year-over-year comparison.");
    container.append("p").style("color", CCN_COLORS.muted).text("No comparable years with theme data.");
    return;
  }

  sub.text(`${pair.fromYear} → ${pair.toYear} · one bar per research theme`);

  if (isPhoneLayout()) {
    renderPhoneThemeBarChart(container, {
      data: rows,
      getLabel: (d) => d.theme,
      getValue: (d) => Math.abs(d.delta),
      getBarFill: (d) => (d.delta >= 0 ? CCN_COLORS.green : CCN_COLORS.pink),
      onBarTooltip: (event, d) =>
        showTooltip(
          `<strong>${d.theme}</strong><br/>${d.fromYear}: ${d.fromCount}<br/>${d.toYear}: ${d.toCount}<br/>Change: ${d.delta >= 0 ? "+" : ""}${d.delta}`,
          event
        ),
      valueFormat: (_, d) => `${d.delta >= 0 ? "+" : ""}${d.delta}`,
    });
    return;
  }

  const width = container.node().clientWidth || s(480);
  const leftMargin = themeBarLabelWidth(width);
  const rowHeight = themeBarRowHeight();
  const margin = { top: s(8), right: s(60), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + rows.length * rowHeight;
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("width", "100%").style("height", `${height}px`);
  const innerW = width - margin.left - margin.right;
  const maxAbs = d3.max(rows, (d) => Math.abs(d.delta)) || 1;
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  const x = d3.scaleLinear().domain([0, maxAbs]).range([0, innerW]);
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
    .on("mousemove", (event, d) =>
      showTooltip(
        `<strong>${d.theme}</strong><br/>${d.fromYear}: ${d.fromCount}<br/>${d.toYear}: ${d.toCount}<br/>Change: ${d.delta >= 0 ? "+" : ""}${d.delta}`,
        event
      )
    )
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
    .text((d) => `${d.delta >= 0 ? "+" : ""}${d.delta}`);
}

function renderClusterBars() {
  const container = d3.select("#cluster-bars-chart");
  container.selectAll("*").remove();

  const themes = researchThemeNames();
  if (!themes.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("Research themes not loaded.");
    return;
  }

  const counts = primaryThemeCounts(filteredSubmissions());
  const countMap = new Map(counts.map((item) => [item.text, item.count]));
  const data = themes
    .map((name) => ({ name, count: countMap.get(name) || 0 }))
    .sort((a, b) => b.count - a.count);

  if (isPhoneLayout()) {
    const color = d3.scaleOrdinal(CHART_PALETTE).domain(data.map((d) => d.name));
    renderPhoneThemeBarChart(container, {
      data,
      getLabel: (d) => d.name,
      getValue: (d) => d.count,
      getBarFill: (d) => (d.name === state.selectedTheme ? CCN_COLORS.pink : color(d.name)),
      onBarClick: (d) => setThemeFilter(d.name),
      onBarTooltip: (event, d) => showTooltip(`<strong>${d.name}</strong><br/>${d.count} primary assignments`, event),
      labelFill: (d) => (d.name === state.selectedTheme ? CCN_COLORS.white : CCN_COLORS.muted),
    });
    return;
  }

  const width = container.node().clientWidth || s(360);
  const leftMargin = themeBarLabelWidth(width);
  const rowHeight = themeBarRowHeight();
  const margin = { top: s(8), right: s(56), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + Math.max(data.length * rowHeight, s(200));
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("width", "100%").style("height", `${height}px`);
  const innerW = width - margin.left - margin.right;

  const x = d3.scaleLinear().domain([0, d3.max(data, (d) => d.count) || 1]).range([0, innerW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.name))
    .range([0, data.length * rowHeight])
    .padding(0.18);
  const color = d3.scaleOrdinal(CHART_PALETTE).domain(data.map((d) => d.name));
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  g.selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", 0)
    .attr("y", (d) => y(d.name))
    .attr("height", y.bandwidth())
    .attr("width", (d) => x(d.count))
    .attr("fill", (d) => (d.name === state.selectedTheme ? CCN_COLORS.pink : color(d.name)))
    .attr("rx", s(4))
    .style("cursor", "pointer")
    .on("click", (_, d) => setThemeFilter(d.name))
    .on("mousemove", (event, d) => showTooltip(`<strong>${d.name}</strong><br/>${d.count} primary assignments`, event))
    .on("mouseleave", hideTooltip);

  drawThemeBarLabels(g, data, y, (d) => d.name, {
    fill: (d) => (d.name === state.selectedTheme ? CCN_COLORS.white : CCN_COLORS.muted),
    pointerEvents: "none",
  });

  g.selectAll("text.value")
    .data(data)
    .join("text")
    .attr("class", "value")
    .attr("x", (d) => x(d.count) + s(6))
    .attr("y", (d) => y(d.name) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", themeFs(10))
    .style("pointer-events", "none")
    .text((d) => d.count);
}

function renderEmbeddingCluster() {
  const container = d3.select("#embedding-chart");
  container.selectAll("*").remove();

  const note = d3.select("#embedding-note");
  if (!state.embeddings?.points?.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("2026 embedding map unavailable.");
    note.text("");
    return;
  }

  const points = state.embeddings.points;
  const width = chartContainerWidth(container);
  const mobileLegend = useStackedChartLegend(width) || isPhoneLayout();
  const legendFont = isPhoneLayout() ? chartThemePx(7) : themeLabelPx(10);
  const legendItemHeight = isPhoneLayout() ? legendFont * 2.2 : legendFont * 1.5;
  const themes = [...new Set(state.embeddings.points.map((d) => mapClusterToTheme(d.cluster_name)))];
  const legendCols = isPhoneLayout() ? 1 : mobileLegend ? (width < 520 ? 1 : 2) : 1;
  const legendRows = mobileLegend ? Math.ceil(themes.length / legendCols) : themes.length;
  const legendBlock = mobileLegend ? legendRows * legendItemHeight + (isPhoneLayout() ? gs(10) : s(16)) : 0;
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
  const color = d3.scaleOrdinal(CHART_PALETTE).domain(themes);
  const plotBottom = mobileLegend ? plotHeight - margin.bottom : height - margin.bottom;
  const pointRadius = isPhoneLayout() ? { base: 2.2, selected: 3 } : { base: 5.5, selected: 7 };

  const x = d3
    .scaleLinear()
    .domain(d3.extent(state.embeddings.points, (d) => d.x))
    .nice()
    .range([margin.left, width - margin.right]);
  const y = d3
    .scaleLinear()
    .domain(d3.extent(state.embeddings.points, (d) => d.y))
    .nice()
    .range([plotBottom, margin.top]);

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", margin.top)
    .attr("width", width - margin.left - margin.right)
    .attr("height", plotBottom - margin.top)
    .attr("fill", "rgba(197,224,243,0.04)")
    .attr("rx", isPhoneLayout() ? gs(8) : s(12));

  svg
    .selectAll("circle.embedding-point")
    .data(points)
    .join("circle")
    .attr("class", "embedding-point")
    .attr("cx", (d) => x(d.x))
    .attr("cy", (d) => y(d.y))
    .attr("r", (d) => {
      const theme = mapClusterToTheme(d.cluster_name);
      return state.selectedTheme && theme === state.selectedTheme
        ? (isPhoneLayout() ? gs(pointRadius.selected) : s(pointRadius.selected))
        : isPhoneLayout()
          ? gs(pointRadius.base)
          : s(pointRadius.base);
    })
    .attr("fill", (d) => color(mapClusterToTheme(d.cluster_name)))
    .attr("stroke", (d) => {
      const theme = mapClusterToTheme(d.cluster_name);
      return state.selectedTheme && theme === state.selectedTheme ? CCN_COLORS.pink : CCN_COLORS.navy;
    })
    .attr("stroke-width", (d) => {
      const theme = mapClusterToTheme(d.cluster_name);
      return state.selectedTheme && theme === state.selectedTheme
        ? (isPhoneLayout() ? gs(1.5) : s(2))
        : isPhoneLayout()
          ? gs(0.75)
          : s(1);
    })
    .attr("opacity", (d) => {
      const theme = mapClusterToTheme(d.cluster_name);
      return !state.selectedTheme || theme === state.selectedTheme ? 0.9 : 0.18;
    })
    .style("cursor", "pointer")
    .style("pointer-events", isTouchLike() ? "none" : "auto");

  if (isTouchLike()) {
    svg
      .selectAll("circle.embedding-hit")
      .data(points)
      .join("circle")
      .attr("class", "embedding-hit")
      .attr("cx", (d) => x(d.x))
      .attr("cy", (d) => y(d.y))
      .attr("r", isPhoneLayout() ? gs(14) : s(16))
      .attr("fill", "transparent")
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        event.stopPropagation();
        setThemeFilter(mapClusterToTheme(d.cluster_name));
      });
  } else {
    svg
      .selectAll("circle.embedding-point")
      .on("mousemove", (event, d) => showTooltip(embeddingPointTooltip(d), event))
      .on("mouseleave", hideTooltip)
      .on("click", (_, d) => setThemeFilter(mapClusterToTheme(d.cluster_name)));
  }

  const legend = svg.append("g");
  if (mobileLegend) {
    const colWidth = (width - margin.left - margin.right) / legendCols;
    const legendMarker = isPhoneLayout() ? gs(8) : s(12);
    const legendTextX = isPhoneLayout() ? gs(12) : s(18);
    legend.attr("transform", `translate(${margin.left}, ${plotHeight + (isPhoneLayout() ? gs(6) : s(8))})`);
    legend
      .selectAll("g")
      .data(themes)
      .join("g")
      .attr("transform", (_, i) => {
        const col = i % legendCols;
        const row = Math.floor(i / legendCols);
        return `translate(${col * colWidth}, ${row * legendItemHeight})`;
      })
      .style("cursor", "pointer")
      .on("click", (_, theme) => setThemeFilter(theme))
      .on("mousemove", isTouchLike() ? null : (event, theme) => showTooltip(themeLegendTooltip(theme), event))
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
          .attr("fill", (d) => (d === state.selectedTheme ? CCN_COLORS.white : CCN_COLORS.muted))
          .style("font-size", isPhoneLayout() ? chartThemeFs(7) : themeFs(10))
          .text((d) => fitLegendLabel(d, colWidth - legendTextX, legendFont));
      });
  } else {
    const legendItems = legend
      .attr("transform", `translate(${width - margin.right + s(12)}, ${margin.top})`)
      .selectAll("g")
      .data(themes)
      .join("g")
      .attr("transform", (_, i) => `translate(0, ${i * legendItemHeight})`)
      .style("cursor", "pointer")
      .on("click", (_, theme) => setThemeFilter(theme))
      .on("mousemove", isTouchLike() ? null : (event, theme) => showTooltip(themeLegendTooltip(theme), event))
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
      .attr("fill", (d) => (d === state.selectedTheme ? CCN_COLORS.white : CCN_COLORS.muted))
      .style("font-size", themeFs(10))
      .text((d) => d);
  }

  renderEmbeddingNote(note);
}

function renderPaperList() {
  const submissions = displaySubmissions();
  const list = d3.select("#paper-list");
  const countEl = d3.select("#results-count");
  countEl.selectAll("*").remove();

  const countLabel = state.selectedTheme
    ? `${submissions.length} submissions with primary theme “${state.selectedTheme}”`
    : `${submissions.length} matching submissions`;
  countEl.append("span").text(countLabel);

  if (state.selectedTheme) {
    countEl
      .append("span")
      .attr("class", "cluster-filter-pill")
      .text("Clear theme filter ×")
      .on("click", () => setThemeFilter(state.selectedTheme));
  }

  const items = list.selectAll(".paper-item").data(submissions).join("div").attr("class", "paper-item");
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
    .text((d) => {
      const primary = primaryTheme(d);
      const secondaries = secondaryTopics(d);
      const secondaryText = secondaries.length ? ` · also: ${secondaries.join(", ")}` : "";
      return `${d.year}${d.poster_number ? ` · Poster ${d.poster_number}` : ""}${d.authors ? ` · ${d.authors}` : ""}${primary ? ` · ${primary}` : ""}${secondaryText}`;
    });

  items.each(function renderTags(d) {
    const tagData = [primaryTheme(d), ...secondaryTopics(d)].filter(Boolean);
    const tags = d3.select(this).append("div").attr("class", "keyword-tags");
    tags
      .selectAll(".keyword-tag")
      .data(tagData)
      .join("span")
      .attr("class", (theme) => `keyword-tag${theme === state.selectedTheme ? " active" : ""}`)
      .text((theme) => theme)
      .on("click", (_, theme) => setThemeFilter(theme));
  });
}

function renderAll() {
  const scrollSnapshot = { x: window.scrollX, y: window.scrollY };
  removeChartScrollWrappers();
  const submissions = filteredSubmissions();
  const primaryCounts = primaryThemeCounts(submissions);
  const secondaryCounts = secondaryTopicCounts(submissions);

  renderKpis(submissions);
  renderThemeSelect(primaryCounts);
  renderYearChart();
  renderThemeBars(primaryCounts);
  renderTopicChart(submissions);
  renderWordCloud(secondaryCounts);
  renderResearchThemesOverTime(submissions);
  renderResearchThemeTotals(submissions);
  renderResearchThemeDeltas(submissions);
  renderClusterBars();
  renderEmbeddingCluster();
  renderPaperList();

  d3.select("#year-chips")
    .selectAll(".year-chip")
    .classed("active", (d) => d === state.selectedYear);

  restorePageScroll(scrollSnapshot.x, scrollSnapshot.y);
}

async function loadOptionalJson(path) {
  try {
    const response = await fetch(path);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

async function init() {
  ensureD3();

  const [submissionsRes, embeddings, googleTopics] = await Promise.all([
    fetch("data/submissions.json"),
    loadOptionalJson("data/embeddings_2026.json"),
    loadOptionalJson("data/google_topics.json"),
  ]);

  if (!submissionsRes.ok) {
    throw new Error(`Could not load data/submissions.json (${submissionsRes.status})`);
  }

  state.data = await submissionsRes.json();
  state.embeddings = embeddings;
  state.googleTopics = googleTopics;
  buildThemeClassifier();

  renderYearControls();

  d3.select("#year-select").on("change", (event) => {
    state.selectedYear = event.target.value;
    renderAll();
  });

  d3.select("#search-input").on("input", (event) => {
    state.search = event.target.value;
    renderAll();
  });

  d3.select("#theme-select").on("change", (event) => {
    state.selectedTheme = event.target.value;
    renderAll();
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
