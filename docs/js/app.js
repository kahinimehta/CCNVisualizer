const CCN_COLORS = {
  navy: "#1a3b5d",
  pink: "#f4c7c3",
  blue: "#c5e0f3",
  green: "#c8e6c9",
  white: "#f7fafc",
  muted: "#8fa8c4",
  card: "#162d47",
};

const CHART_FONT = '"Open Sans", "Segoe UI", system-ui, sans-serif';

const COMPACT_LAYOUT_MAX_WIDTH = 960;
const STACKED_LEGEND_MAX_WIDTH = 960;
const PHONE_MAX_WIDTH = 640;

function viewportWidth() {
  // Use layout viewport only — visualViewport changes with pinch-zoom and
  // would otherwise reflow charts as if the device width changed.
  const client = document.documentElement.clientWidth;
  const inner = window.innerWidth;
  return Math.round(client || inner || 0);
}

function isDesktopPointer() {
  return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

function isPhoneLayout() {
  // Require device width so a narrowed desktop/Brave window is not treated as a phone.
  const phoneDevice = window.matchMedia(`(max-device-width: ${PHONE_MAX_WIDTH - 1}px)`).matches;
  return viewportWidth() < PHONE_MAX_WIDTH && isTouchLike() && phoneDevice;
}

function isTouchLike() {
  return window.matchMedia("(hover: none) and (pointer: coarse)").matches;
}

function chartContainerWidth(container) {
  const node = container.node();
  if (!node) return viewportWidth();

  // Prefer layout widths (client/offset) over getBoundingClientRect so
  // pinch-zoom visual scaling does not rewrite chart geometry.
  const readWidth = (el) => {
    if (!el) return 0;
    const width = Math.round(el.clientWidth || el.offsetWidth || 0);
    return Number.isFinite(width) ? width : 0;
  };

  let width = readWidth(node);
  if (width >= 160) return width;

  const card = node.closest(".card");
  width = readWidth(card);
  if (width >= 160) return Math.max(width - 32, 280);

  const main = node.closest(".main-area");
  width = readWidth(main);
  if (width >= 160) return Math.max(width - 48, 280);

  return viewportWidth();
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

function appendChartSvg(container, width, height, options = {}) {
  // Always size via viewBox + width:100% + height:auto so browser zoom and
  // container width scale charts uniformly without distorting proportions.
  const { preserveAspectRatio = "xMidYMid meet" } = options;
  return container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .attr("height", null)
    .attr("preserveAspectRatio", preserveAspectRatio)
    .style("width", "100%")
    .style("height", "auto")
    .style("max-width", "100%")
    .style("overflow", "visible");
}

function wrapThemeLabel(text, maxWidth, fontPx) {
  const width = Math.max(40, maxWidth);
  const words = String(text).split(/\s+/);
  const lines = [];
  let line = "";

  const pushTruncated = (value) => {
    let truncated = value;
    while (truncated.length > 1 && measureTextWidth(`${truncated}…`, fontPx) > width) {
      truncated = truncated.slice(0, -1);
    }
    lines.push(`${truncated}…`);
  };

  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    const candidateWidth = measureTextWidth(candidate, fontPx);
    if (candidateWidth > width && line) {
      lines.push(line);
      line = word;
    } else if (candidateWidth > width) {
      pushTruncated(candidate);
      line = "";
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines.slice(0, 3);
}

function phoneBarValueClipsLeft(barWidth, valueText, valueFont) {
  const textWidth = measureTextWidth(valueText, valueFont);
  return barWidth - textWidth < gs(5);
}

function phoneBarLabelLines(item, innerW, labelFont, getLabel, splitLabel) {
  if (splitLabel) {
    const { prefix, suffix } = splitLabel(item);
    return wrapThemeLabel(prefix + suffix, innerW, labelFont);
  }
  return wrapThemeLabel(getLabel(item), innerW, labelFont);
}

function appendPhoneBarLabel(textSel, lines, item, { x, labelFont, labelFill, splitLabel }) {
  const fill = typeof labelFill === "function" ? labelFill(item) : labelFill;
  const suffix = splitLabel ? splitLabel(item).suffix : null;
  const suffixFill = splitLabel ? splitLabel(item).suffixFill : null;

  lines.forEach((line, lineIndex) => {
    const dy = lineIndex === 0 ? 0 : labelFont * 1.15;
    if (suffix && line.endsWith(suffix)) {
      const prefix = line.slice(0, line.length - suffix.length);
      textSel.append("tspan").attr("x", x).attr("dy", dy).attr("fill", fill).text(prefix);
      textSel.append("tspan").attr("fill", suffixFill).text(suffix);
      return;
    }
    textSel.append("tspan").attr("x", x).attr("dy", dy).attr("fill", fill).text(line);
  });
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
    showValueLabel = true,
    splitLabel = null,
  } = options;

  container.selectAll("*").remove();
  const width = chartContainerWidth(container);
  const margin = { top: gs(5), right: gs(5), bottom: gs(5), left: gs(5) };
  const innerW = width - margin.left - margin.right;
  const labelFont = chartThemePx(PHONE_THEME_TITLE_SIZE);
  const valueFont = chartThemePx(PHONE_BAR_VALUE_SIZE);
  const barH = gs(8);
  const rowGap = gs(3);
  const valueBelowGap = gs(5);
  const valueGap = gs(3);
  const blockGap = gs(8);
  const sideGap = gs(5);
  const valueH = valueFont * 1.15;
  const maxVal = d3.max(data, getValue) || 1;
  const x = d3.scaleLinear().domain([0, maxVal]).range([0, innerW]);

  const rows = data.map((item) => {
    const val = getValue(item);
    const barWidth = Math.max(x(val), val > 0 ? gs(2) : 0);
    const valueText = valueFormat(val, item);
    const sideLayout =
      showValueLabel && phoneBarValueClipsLeft(barWidth, valueText, valueFont);

    if (sideLayout) {
      const labelMaxW = Math.max(gs(48), innerW - barWidth - sideGap);
      const lines = wrapThemeLabel(getLabel(item), labelMaxW, labelFont);
      const labelH = lines.length * labelFont * 1.15;
      const stackH = labelH + valueGap + valueH;
      return {
        item,
        val,
        barWidth,
        valueText,
        sideLayout: true,
        lines,
        labelX: barWidth + sideGap,
        rowHeight: Math.max(barH, stackH) + blockGap,
      };
    }

    const lines = phoneBarLabelLines(item, innerW, labelFont, getLabel, splitLabel);
    const labelH = lines.length * labelFont * 1.15;
    const valueBlock = showValueLabel ? valueBelowGap + valueH : 0;
    return {
      item,
      val,
      barWidth,
      valueText,
      sideLayout: false,
      lines,
      rowHeight: labelH + rowGap + barH + valueBlock + blockGap,
    };
  });

  const height = margin.top + margin.bottom + d3.sum(rows, (r) => r.rowHeight);
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .style("height", `${height}px`);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  let yCursor = 0;
  rows.forEach((row) => {
    const { item, val, barWidth, valueText, sideLayout, lines, rowHeight } = row;

    if (sideLayout) {
      const barY = yCursor + Math.max(0, (rowHeight - blockGap - barH) / 2);
      const labelX = row.labelX;
      const labelY = barY + labelFont;
      const labelH = lines.length * labelFont * 1.15;

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
      bindBarTooltipEvents(rect, onBarTooltip, item);

      const label = g
        .append("text")
        .attr("x", labelX)
        .attr("y", labelY)
        .attr("fill", typeof labelFill === "function" ? labelFill(item) : labelFill)
        .style("font-size", `${labelFont}px`);
      lines.forEach((ln, li) => {
        label
          .append("tspan")
          .attr("x", labelX)
          .attr("dy", li === 0 ? 0 : labelFont * 1.15)
          .text(ln);
      });

      g.append("text")
        .attr("class", "bar-value")
        .attr("x", labelX)
        .attr("y", labelY + labelH + valueGap)
        .attr("text-anchor", "start")
        .attr("dominant-baseline", "hanging")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", chartThemeFs(PHONE_BAR_VALUE_SIZE))
        .text(valueText);

      yCursor += rowHeight;
      return;
    }

    const text = g
      .append("text")
      .attr("x", 0)
      .attr("y", yCursor + labelFont)
      .style("font-size", `${labelFont}px`);
    appendPhoneBarLabel(text, lines, item, { x: 0, labelFont, labelFill, splitLabel });

    const barY = yCursor + lines.length * labelFont * 1.15 + rowGap;
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
    bindBarTooltipEvents(rect, onBarTooltip, item);

    if (showValueLabel) {
      g.append("text")
        .attr("class", "bar-value")
        .attr("x", barWidth)
        .attr("y", barY + barH + valueBelowGap)
        .attr("text-anchor", "end")
        .attr("dominant-baseline", "hanging")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", chartThemeFs(PHONE_BAR_VALUE_SIZE))
        .text(valueText);
    }

    yCursor += rowHeight;
  });
}

function readCssNumber(property, fallback) {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(property).trim();
  const parsed = parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const PHONE_GRAPH_SCALE = 0.72;
const PHONE_AXIS_LABEL_SIZE = 8.5;
const PHONE_THEME_TITLE_SIZE = 10.5;
const PHONE_BAR_VALUE_SIZE = 10.5;
const PHONE_LEGEND_HEADING_SIZE = 10.5;
const PHONE_EMBEDDING_LEGEND_HEADING_SIZE = 12.5;

// Fixed chart design scales — not tied to viewport/zoom.
// Desktop stays large; phones use a calmer scale so plots aren't cramped.
const DESKTOP_CHART_SCALE = 4.53;
const PHONE_CHART_SCALE = 1.2;
const DESKTOP_ROOT_FONT_PX = 64;
const PHONE_ROOT_FONT_PX = 16;

function enforceRootFontSize() {
  const root = document.documentElement;
  if (!root) return;
  root.style.fontSize = `${isPhoneLayout() ? PHONE_ROOT_FONT_PX : DESKTOP_ROOT_FONT_PX}px`;
}

function getUiScale() {
  return isPhoneLayout() ? PHONE_CHART_SCALE : DESKTOP_CHART_SCALE;
}

const s = (n) => n * getUiScale();
const gs = (n) => (isPhoneLayout() ? n * PHONE_CHART_SCALE * PHONE_GRAPH_SCALE : s(n));
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
  return viewportWidth() < COMPACT_LAYOUT_MAX_WIDTH && isTouchLike() && !isDesktopPointer();
}

function useStackedChartLegend(width = viewportWidth()) {
  return width < STACKED_LEGEND_MAX_WIDTH && isTouchLike() && !isDesktopPointer();
}

function themeLabelPx(base) {
  return s(base);
}

function themeFs(base) {
  return `${themeLabelPx(base)}px`;
}

let measureTextCanvas = null;

function measureTextWidth(text, fontSizePx, fontFamily = CHART_FONT) {
  if (typeof document === "undefined") return text.length * fontSizePx * 0.58;
  measureTextCanvas = measureTextCanvas || document.createElement("canvas");
  const ctx = measureTextCanvas.getContext("2d");
  if (!ctx) return text.length * fontSizePx * 0.58;
  ctx.font = `${fontSizePx}px ${fontFamily}`;
  return ctx.measureText(text).width;
}

function themeBarLabelWidth(containerWidth = 0, labels = []) {
  const w = Math.max(containerWidth || viewportWidth(), 320);
  const labelFont = themeLabelPx(10);
  const gap = s(8);
  const safety = s(18);

  if (isPhoneLayout()) {
    const fraction = w < 400 ? 0.34 : 0.32;
    const cap = Math.max(w * fraction, s(48));
    const measured =
      labels.length > 0
        ? (d3.max(labels, (label) => measureTextWidth(String(label), labelFont)) || 0) * 1.15 + gap + s(14)
        : s(160);
    return Math.min(measured, cap) + safety;
  }

  const cap = Math.max(s(140), Math.min(w * 0.62, s(420)));
  const wrapWidth = Math.max(s(96), cap - gap - s(20));
  let measured = s(140);
  for (const label of labels) {
    const lines = wrapThemeLabel(String(label), wrapWidth, labelFont);
    for (const line of lines) {
      measured = Math.max(measured, measureTextWidth(line, labelFont));
    }
  }

  return Math.min(Math.max(measured, s(140)) * 1.1 + gap + s(14) + safety, cap + safety);
}

function themeBarRowHeight(labels = [], labelWidth = 0) {
  const fontPx = themeLabelPx(10);
  const lineHeight = fontPx * 1.15;
  const wrapWidth = Math.max(s(72), labelWidth - s(18));
  const maxLines =
    labels.length > 0
      ? d3.max(labels, (label) => wrapThemeLabel(String(label), wrapWidth, fontPx).length) || 1
      : 1;
  return Math.max(s(36), maxLines * lineHeight + s(10));
}

function themeBarViewPad() {
  return s(10);
}

function appendThemeBarSvg(container, width, height) {
  const leftPad = themeBarViewPad();
  return container
    .append("svg")
    .attr("viewBox", `${-leftPad} 0 ${width + leftPad} ${height}`)
    .attr("width", "100%")
    .attr("height", null)
    .attr("preserveAspectRatio", "xMidYMid meet")
    .style("width", "100%")
    .style("height", "auto")
    .style("max-width", "100%")
    .style("overflow", "visible");
}

function themeBarPlotWidth(innerW, rows, formatValue) {
  const valueFont = themeLabelPx(10);
  const maxLabelWidth =
    d3.max(rows, (row) => measureTextWidth(formatValue(row), valueFont)) || measureTextWidth("+0.0%", valueFont);
  const reserve = Math.max(maxLabelWidth + s(12), s(40));
  return Math.max(s(80), innerW - reserve);
}

function themeBarLabelX(gap = 8) {
  return -s(gap);
}

function drawThemeBarLabels(g, data, y, getLabel, options = {}) {
  const baseFont = options.baseFont ?? 10;
  const fill = options.fill ?? CCN_COLORS.muted;
  const gap = options.gap ?? 8;
  const fontPx = themeLabelPx(baseFont);
  const maxLabelWidth = options.maxLabelWidth ?? 0;
  const labelX = themeBarLabelX(gap);

  g.selectAll("g.theme-label-group")
    .data(data, (d) => getLabel(d))
    .join("g")
    .attr("class", "theme-label-group")
    .attr("transform", (d) => `translate(0,${y(getLabel(d)) + y.bandwidth() / 2})`)
    .each(function renderThemeLabel(d) {
      const group = d3.select(this);
      group.selectAll("*").remove();
      const label = String(getLabel(d));
      const lines = maxLabelWidth > 0 ? wrapThemeLabel(label, maxLabelWidth, fontPx) : [label];
      const text = group
        .append("text")
        .attr("class", "theme-label")
        .attr("x", labelX)
        .attr("text-anchor", "end")
        .attr("fill", typeof fill === "function" ? fill(d) : fill)
        .style("font-size", themeFs(baseFont))
        .style("font-family", CHART_FONT)
        .style("pointer-events", options.pointerEvents || "auto");

      lines.forEach((line, i) => {
        const dy = i === 0 ? (lines.length === 1 ? "0.35em" : `${-((lines.length - 1) * 0.58)}em`) : "1.15em";
        text.append("tspan").attr("x", labelX).attr("dy", dy).text(line);
      });
    });
}

function styleThemeAxisLabels(selection) {
  selection
    .selectAll("text")
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", isPhoneLayout() ? chartThemeFs(8) : themeFs(10));
}

const CHART_PALETTE = [
  "#EF4444", // red — Reinforcement learning
  "#F97316", // orange — Motor control & planning
  "#FB923C", // light orange — Naturalistic encoding/decoding
  "#FACC15", // yellow — Neural population geometry & dynamics
  "#F59E0B", // amber — Decision-making and metacognition
  "#16A34A", // forest green — Vision
  "#84CC16", // lime — Perception
  "#0284C7", // sky blue — Language/auditory neuroscience
  "#06B6D4", // cyan — AI, LLM, & Neural Networks
  "#2563EB", // blue — Memory
  "#6366F1", // indigo — Social cognition & theory of mind
  "#9333EA", // purple — Attention & cognitive control
  "#C026D3", // fuchsia — Clinical / computational psychiatry
  "#EC4899", // pink — Methods and theory
];

// Distinct year colors for the UMAP map (2017–2026).
const YEAR_PALETTE = [
  "#F97316", // 2017 orange
  "#EAB308", // 2018 yellow
  "#84CC16", // 2019 lime
  "#14B8A6", // 2020 teal
  "#0EA5E9", // 2021 sky
  "#3B82F6", // 2022 blue
  "#8B5CF6", // 2023 violet
  "#D946EF", // 2024 fuchsia
  "#F43F5E", // 2025 rose
  "#F4C7C3", // 2026 CCN pink
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
];

const DATASET_OPTIONS = [
  {
    file: "abstracts.csv",
    label: "Full topics (abstracts.csv)",
  },
  {
    file: "abstracts_2_topics.csv",
    label: "First two topics only",
  },
  {
    file: "abstract_v_3.csv",
    label: "Drop Methods unless top-two",
  },
];

const DATASET_STORAGE_KEY = "ccn-visualizer-dataset";
const DEFAULT_DATASET = DATASET_OPTIONS[0].file;

const state = {
  data: null,
  datasetFile: DEFAULT_DATASET,
  selectedYear: "all",
  search: "",
  selectedThemes: [],
  themeFilterMode: "include",
  highlightedSubmissionKey: "",
  deltaFromYear: "",
  deltaToYear: "",
};

let tooltip = null;
let tooltipDismissBound = false;
let tooltipVisible = false;
let tooltipMode = null; // "hover" | "tap"
let tooltipInteractive = false;
let tooltipSticky = false; // phone tap popups stay until X
let tooltipHideTimer = null;
let tooltipAnchorPoint = null;

function ensureD3() {
  if (typeof d3 === "undefined") {
    throw new Error("D3.js failed to load. Check your network connection or ad blocker.");
  }
  if (!tooltip) {
    tooltip = d3.select("#tooltip");
  }
}

function cancelHideTooltip() {
  if (tooltipHideTimer != null) {
    clearTimeout(tooltipHideTimer);
    tooltipHideTimer = null;
  }
}

function scheduleHideTooltip(delayMs = 160) {
  cancelHideTooltip();
  tooltipHideTimer = setTimeout(() => {
    tooltipHideTimer = null;
    hideTooltip();
  }, delayMs);
}

function setupTooltipDismiss() {
  if (tooltipDismissBound) return;
  tooltipDismissBound = true;

  const dismissOnScroll = () => {
    // Sticky phone tap popups stay until the user hits X.
    if (tooltipVisible && !tooltipSticky) hideTooltip();
  };

  // Capture phase catches window scroll and nested scrollers (e.g. paper list).
  document.addEventListener("scroll", dismissOnScroll, { passive: true, capture: true });
  window.addEventListener("scroll", dismissOnScroll, { passive: true, capture: true });
  window.visualViewport?.addEventListener("scroll", dismissOnScroll, { passive: true });
  window.visualViewport?.addEventListener("resize", dismissOnScroll, { passive: true });
}

function bindBarTooltipEvents(rect, onBarTooltip, item) {
  if (!onBarTooltip) return;
  // Phone: tap only. Desktop pointer: hover. Other touch: no hover tooltips.
  if (isPhoneLayout()) {
    rect.on("click", (event) => {
      event.stopPropagation();
      onBarTooltip(event, item);
    });
    return;
  }
  if (isTouchLike() || !isDesktopPointer()) return;
  rect
    .on("mousemove", (event) => onBarTooltip(event, item))
    .on("mouseleave", hideTooltip);
}

function bindTooltipInteractions(options = {}) {
  if (!tooltip) return;
  const { onTopicClick = null, onOpenPaper = null } = options;

  tooltip.selectAll(".tooltip-close").on("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    hideTooltip();
  });

  tooltip.selectAll("button.tooltip-topic").on("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const theme = event.currentTarget?.getAttribute("data-theme");
    if (!theme) return;
    if (typeof onTopicClick === "function") {
      onTopicClick(theme);
      return;
    }
    toggleThemeFilter(theme);
  });

  tooltip.selectAll("button.tooltip-open-paper").on("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (typeof onOpenPaper === "function") {
      onOpenPaper();
      return;
    }
    if (tooltipAnchorPoint) focusSubmissionFromPoint(tooltipAnchorPoint);
    hideTooltip();
  });

  tooltip
    .on("mouseenter", () => {
      if (tooltipInteractive) cancelHideTooltip();
    })
    .on("mouseleave", () => {
      if (tooltipInteractive && tooltipMode === "hover") scheduleHideTooltip();
    });
}

function showTooltip(html, event, options = {}) {
  if (!tooltip) return;
  const phone = isPhoneLayout();
  const mode = options.mode || (phone ? "tap" : "hover");
  const interactive = Boolean(options.interactive);

  // Phone never uses hover tooltips — only explicit taps.
  if (phone && mode === "hover") return;
  if (!phone && isTouchLike() && mode === "hover") return;

  cancelHideTooltip();
  const offset = s(12);
  tooltipMode = mode;
  tooltipInteractive = interactive;
  tooltipSticky = phone && mode === "tap";
  tooltipAnchorPoint = options.anchorPoint || null;

  if (phone || mode === "tap") {
    tooltip.html(
      `<div class="tooltip-phone-inner"><div class="tooltip-body">${html}</div><button type="button" class="tooltip-close" aria-label="Close tooltip">×</button></div>`
    );
    tooltip.classed("tooltip-phone", true);
    tooltip.classed("tooltip-phone-centered", phone);
  } else {
    tooltip.classed("tooltip-phone", false);
    tooltip.classed("tooltip-phone-centered", false);
    tooltip.html(html);
  }

  tooltip.classed("tooltip-interactive", interactive);
  tooltipVisible = true;
  const allowPointer = interactive || phone || mode === "tap";
  tooltip.style("opacity", 1).style("pointer-events", allowPointer ? "auto" : "none");

  bindTooltipInteractions({
    onTopicClick: options.onTopicClick,
    onOpenPaper: options.onOpenPaper,
  });

  if (phone && mode === "tap") {
    // Centered half-size phone popup; CSS handles transform.
    tooltip.style("left", "50%").style("top", "50%");
    return;
  }

  const node = tooltip.node();
  const width = node?.offsetWidth || 0;
  const height = node?.offsetHeight || 0;
  const maxLeft = window.innerWidth - width - offset;
  const maxTop = window.innerHeight - height - offset;
  const clientX = event?.clientX ?? window.innerWidth / 2;
  const clientY = event?.clientY ?? window.innerHeight / 2;
  const left = Math.max(offset, Math.min(clientX + offset, maxLeft));
  const top = Math.max(offset, Math.min(clientY + offset, maxTop));
  tooltip.style("left", `${left}px`).style("top", `${top}px`);
}

function hideTooltip() {
  if (!tooltip) return;
  cancelHideTooltip();
  tooltipVisible = false;
  tooltipMode = null;
  tooltipInteractive = false;
  tooltipSticky = false;
  tooltipAnchorPoint = null;
  tooltip.style("opacity", 0).style("pointer-events", "none");
  tooltip.style("left", null).style("top", null);
  tooltip.classed("tooltip-phone", false);
  tooltip.classed("tooltip-phone-centered", false);
  tooltip.classed("tooltip-interactive", false);
  tooltip.on("mouseenter", null).on("mouseleave", null);
  tooltip.selectAll(".tooltip-close").on("click", null);
  tooltip.selectAll("button.tooltip-topic").on("click", null);
  tooltip.selectAll("button.tooltip-open-paper").on("click", null);
}

function refreshStickyPhoneTooltip() {
  if (!tooltipSticky || !tooltipAnchorPoint || !isPhoneLayout()) return;
  const anchor = tooltipAnchorPoint;
  showEmbeddingPointTooltip(null, anchor, "tap");
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

function submissionRowKey(submission) {
  const year = submission?.year ?? "";
  const paperId = String(submission?.id ?? submission?.poster_number ?? submission?.title ?? "");
  return `${year}:${paperId}`;
}

function csvRowToSubmission(row) {
  const umapX = row.umap_x === "" || row.umap_x == null ? null : Number(row.umap_x);
  const umapY = row.umap_y === "" || row.umap_y == null ? null : Number(row.umap_y);
  const keywords = splitField(row.keywords);
  return {
    id: row.id,
    year: Number(row.year),
    title: row.title || "",
    author: row.author || "",
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

function buildStateFromCsv(rows, source = DEFAULT_DATASET) {
  const submissions = rows.map(csvRowToSubmission);
  const years = [...new Set(submissions.map((item) => item.year))].sort((a, b) => a - b);
  return {
    submissions,
    metadata: {
      years,
      total_count: submissions.length,
      source,
    },
    stats: buildStatsFromSubmissions(submissions),
  };
}

function isValidDatasetFile(file) {
  return DATASET_OPTIONS.some((option) => option.file === file);
}

function readStoredDatasetFile() {
  try {
    const stored = localStorage.getItem(DATASET_STORAGE_KEY);
    if (stored && isValidDatasetFile(stored)) return stored;
  } catch {
    /* ignore storage errors */
  }
  return DEFAULT_DATASET;
}

function persistDatasetFile(file) {
  try {
    localStorage.setItem(DATASET_STORAGE_KEY, file);
  } catch {
    /* ignore storage errors */
  }
}

function renderDatasetSelect() {
  const select = d3.select("#dataset-select");
  if (select.empty()) return;
  select.selectAll("option").remove();
  select
    .selectAll("option")
    .data(DATASET_OPTIONS)
    .join("option")
    .attr("value", (d) => d.file)
    .text((d) => d.label);
  select.property("value", state.datasetFile);
}

async function loadDataset(file, options = {}) {
  const { resetFilters = false } = options;
  const datasetFile = isValidDatasetFile(file) ? file : DEFAULT_DATASET;
  const csvRows = await d3.csv(`data/${datasetFile}`);
  if (!csvRows?.length) {
    throw new Error(`Could not load data/${datasetFile}`);
  }

  state.datasetFile = datasetFile;
  persistDatasetFile(datasetFile);
  state.data = buildStateFromCsv(csvRows, datasetFile);

  if (resetFilters) {
    state.selectedYear = "all";
    state.search = "";
    state.selectedThemes = [];
    state.themeFilterMode = "include";
    state.highlightedSubmissionKey = "";
    state.deltaFromYear = "";
    state.deltaToYear = "";
    d3.select("#search-input").property("value", "");
    d3.select("#year-select").property("value", "all");
  } else if (
    state.selectedYear !== "all" &&
    !state.data.metadata.years.map(String).includes(String(state.selectedYear))
  ) {
    state.selectedYear = "all";
  }

  renderDatasetSelect();
  renderYearControls();
  renderDeltaYearControls();
  renderAll();
}

function embeddingDisplayPoints() {
  // Always include every paper with coordinates; filters only highlight matches.
  return (state.data?.submissions || [])
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
  return submission.assigned_topics?.length ? submission.assigned_topics : [];
}

function sortedTopics(topics) {
  return [...topics].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

function assignedTopicsSorted(submission) {
  return sortedTopics(assignedTopics(submission));
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

function hasThemeFilter() {
  return state.selectedThemes.length > 0;
}

function submissionMatchesThemeFilter(submission) {
  if (!hasThemeFilter()) return true;
  const assigned = assignedTopics(submission);
  // Multi-topic filters require all selected topics ("all of"), not any-of.
  const hitsAll = state.selectedThemes.every((theme) => assigned.includes(theme));
  return state.themeFilterMode === "exclude" ? !hitsAll : hitsAll;
}

function filteredSubmissions() {
  const { submissions } = state.data;
  const search = state.search.trim().toLowerCase();

  return submissions.filter((item) => {
    const yearOk = state.selectedYear === "all" || String(item.year) === state.selectedYear;
    const searchOk = !search || submissionMatchesSearch(item, search);
    const themeOk = submissionMatchesThemeFilter(item);
    return yearOk && searchOk && themeOk;
  });
}

function submissionsForThemeTrends() {
  const { submissions } = state.data;
  const search = state.search.trim().toLowerCase();

  return submissions.filter((item) => {
    const searchOk = !search || submissionMatchesSearch(item, search);
    const themeOk = submissionMatchesThemeFilter(item);
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

function yearColor(year) {
  const years = state.data?.metadata?.years || [];
  const index = years.indexOf(Number(year));
  if (index >= 0) return YEAR_PALETTE[index % YEAR_PALETTE.length];
  const fallbackYears = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
  const fallbackIndex = fallbackYears.indexOf(Number(year));
  return YEAR_PALETTE[(fallbackIndex >= 0 ? fallbackIndex : 0) % YEAR_PALETTE.length];
}

function appendEmbeddingDot(parent, radius, options = {}) {
  const { opacity = 0.88, stroke = "#0f2238", strokeWidth = 1, fill = "#111827" } = options;

  parent
    .append("circle")
    .attr("class", "embedding-point")
    .attr("r", radius)
    .attr("fill", fill)
    .attr("stroke", stroke)
    .attr("stroke-width", strokeWidth)
    .attr("opacity", opacity);
}

function submissionForEmbeddingPoint(point) {
  const key = submissionRowKey(point);
  return state.data?.submissions?.find((item) => submissionRowKey(item) === key);
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
    pair = defaultDeltaYearPair() || latestComparableYearPair(years, byYear, themes);
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
  const years = state.data?.metadata?.years;
  if (!years?.length) return null;
  const yearSet = new Set(years.map(String));
  if (yearSet.has("2017") && yearSet.has("2026")) {
    return { fromYear: "2017", toYear: "2026" };
  }
  const sorted = [...years].sort((a, b) => a - b);
  return { fromYear: String(sorted[0]), toYear: String(sorted[sorted.length - 1]) };
}

function syncDeltaYearState() {
  if (state.selectedYear !== "all") {
    syncDeltaYearsForYearFilter();
    return;
  }
  const pair = defaultDeltaYearPair();
  if (!state.deltaFromYear && pair) state.deltaFromYear = pair.fromYear;
  if (!state.deltaToYear && pair) state.deltaToYear = pair.toYear;
}

function conferenceYearPairForSelection(selectedYear) {
  const years = [...state.data.metadata.years].sort((a, b) => a - b);
  const idx = years.indexOf(Number(selectedYear));
  if (idx < 0) return null;
  if (idx > 0) {
    return { fromYear: String(years[idx - 1]), toYear: String(years[idx]) };
  }
  if (years.length > 1) {
    return { fromYear: String(years[0]), toYear: String(years[1]) };
  }
  return null;
}

function syncDeltaYearsForYearFilter() {
  if (state.selectedYear === "all") return;
  const pair = conferenceYearPairForSelection(state.selectedYear);
  if (!pair) return;
  state.deltaFromYear = pair.fromYear;
  state.deltaToYear = pair.toYear;
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

function toggleThemeFilter(theme, options = {}) {
  if (!theme) return;
  const { rerender = true } = options;
  const idx = state.selectedThemes.indexOf(theme);
  if (idx >= 0) {
    state.selectedThemes = state.selectedThemes.filter((item) => item !== theme);
  } else {
    state.selectedThemes = sortedTopics([...state.selectedThemes, theme]);
  }
  state.highlightedSubmissionKey = "";
  if (rerender) renderAll();
}

function clearThemeFilters() {
  state.selectedThemes = [];
  state.highlightedSubmissionKey = "";
  renderAll();
}

function setThemeFilterMode(mode) {
  state.themeFilterMode = mode === "exclude" ? "exclude" : "include";
  state.highlightedSubmissionKey = "";
  renderAll();
}

function ensureSubmissionVisible(submission) {
  if (!submission) return;
  const key = submissionRowKey(submission);
  const isVisible = () => filteredSubmissions().some((item) => submissionRowKey(item) === key);
  if (isVisible()) return;

  state.selectedThemes = [];

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

function focusSubmissionFromPoint(point) {
  const submission = submissionForEmbeddingPoint(point);
  if (!submission) return;
  ensureSubmissionVisible(submission);
  state.highlightedSubmissionKey = submissionRowKey(submission);
  renderAll();
  requestAnimationFrame(() => {
    requestAnimationFrame(() => scrollToHighlightedSubmission());
  });
}

function scrollToHighlightedSubmission() {
  if (!state.highlightedSubmissionKey) return;
  const el = document.querySelector(
    `.paper-item[data-id="${CSS.escape(state.highlightedSubmissionKey)}"]`
  );
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function themeFilterDisplayText() {
  if (!hasThemeFilter()) return "";
  const topics = sortedTopics(state.selectedThemes);
  const joined =
    topics.length === 1
      ? `“${topics[0]}”`
      : topics.length === 2
        ? `“${topics[0]}” and “${topics[1]}”`
        : `${topics.slice(0, -1).map((t) => `“${t}”`).join(", ")}, and “${topics[topics.length - 1]}”`;
  const allLabel = topics.length === 1 ? joined : `all of ${joined}`;
  if (state.themeFilterMode === "exclude") {
    return `Exclude papers with ${allLabel}`;
  }
  return `Include papers with ${allLabel}`;
}

function embeddingDefaultNote() {
  const count = embeddingDisplayPoints().length;
  const highlighted = embeddingHighlightCount();
  if (state.highlightedSubmissionKey) {
    return "Jumped to highlighted submission below — topic tags are shown on the card";
  }
  if (hasThemeFilter()) {
    return `${count} papers on map · ${highlighted} highlighted · ${themeFilterDisplayText()}`;
  }
  return isTouchLike()
    ? `${count} submissions · colored by year · tap a dot to see topics and filter · or open the paper`
    : `${count} submissions · colored by year · hover a dot to see topics and click a topic to filter`;
}

function renderEmbeddingNote(note) {
  note.text(embeddingDefaultNote());
}

function embeddingPointTopics(point) {
  const submission = submissionForEmbeddingPoint(point);
  return submission ? assignedTopicsSorted(submission) : [];
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function embeddingPointTooltipHtml(point) {
  const submission = submissionForEmbeddingPoint(point);
  const topics = embeddingPointTopics(point);
  const selected = new Set(state.selectedThemes);
  const title = escapeHtml(submission?.title || point.title || "Submission");
  const year = submission?.year ?? point.year;
  const yearLabel = year != null ? escapeHtml(String(year)) : "";
  const yearSwatch = year != null ? yearColor(year) : CCN_COLORS.muted;
  const topicButtons = topics.length
    ? topics
        .map((theme) => {
          const active = selected.has(theme) ? " active" : "";
          const color = themeColor(theme);
          const safeTheme = escapeHtml(theme);
          return `<button type="button" class="tooltip-topic${active}" data-theme="${safeTheme}" style="--topic-color:${color}">${safeTheme}</button>`;
        })
        .join("")
    : `<span class="tooltip-hint">No topics assigned</span>`;
  const hint = isPhoneLayout()
    ? "Tap a topic to filter · Open paper below"
    : "Click a topic to filter by it";
  return [
    `<strong>${title}</strong>`,
    yearLabel
      ? `<div class="tooltip-year"><span class="tooltip-year-swatch" style="background:${yearSwatch}"></span>${yearLabel}</div>`
      : "",
    `<div class="tooltip-topics">${topicButtons}</div>`,
    `<div class="tooltip-actions"><button type="button" class="tooltip-action tooltip-open-paper">Open paper</button></div>`,
    `<span class="tooltip-hint">${hint}</span>`,
  ].join("");
}

function showEmbeddingPointTooltip(event, point, mode = "hover") {
  showTooltip(embeddingPointTooltipHtml(point), event, {
    mode,
    interactive: true,
    anchorPoint: point,
    onTopicClick: (theme) => {
      toggleThemeFilter(theme);
      // Keep the phone popup open and refresh active topic chips.
      if (isPhoneLayout()) {
        requestAnimationFrame(() => refreshStickyPhoneTooltip());
      }
    },
    onOpenPaper: () => {
      focusSubmissionFromPoint(point);
      // Phone sticky popup stays until X; desktop closes after jump.
      if (!isPhoneLayout()) hideTooltip();
    },
  });
}

function embeddingHighlightCount() {
  return embeddingDisplayPoints().filter((point) => pointMatchesThemeFilter(point)).length;
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
      state.highlightedSubmissionKey = "";
      d3.select("#year-select").property("value", d);
      renderAll();
    });
}

function renderThemeFilterStatus() {
  const status = d3.select("#theme-filter-status");
  if (status.empty()) return;
  const node = status.node();
  if (!hasThemeFilter()) {
    if (node) node.hidden = true;
    status.text("");
    return;
  }
  if (node) node.hidden = false;
  status.html(`<strong>Active filter:</strong> ${escapeHtml(themeFilterDisplayText())}`);
}

function renderThemeMultiSelect() {
  const host = d3.select("#theme-multi-select");
  if (host.empty()) return;

  const topics = sortedTopics(googleTopicNames());
  const selected = new Set(state.selectedThemes);
  const exclude = state.themeFilterMode === "exclude";

  host
    .selectAll("button.theme-chip")
    .data(topics, (d) => d)
    .join("button")
    .attr("type", "button")
    .attr("class", (theme) => {
      const classes = ["theme-chip"];
      if (selected.has(theme)) {
        classes.push("selected");
        if (exclude) classes.push("exclude");
      }
      return classes.join(" ");
    })
    .attr("aria-pressed", (theme) => (selected.has(theme) ? "true" : "false"))
    .text((theme) => theme)
    .on("click", (_, theme) => toggleThemeFilter(theme));

  d3.select("#theme-mode-include").classed("active", !exclude);
  d3.select("#theme-mode-exclude").classed("active", exclude);

  const clearBtn = d3.select("#theme-clear-btn");
  if (!clearBtn.empty()) clearBtn.node().hidden = !hasThemeFilter();
  renderThemeFilterStatus();
}

function renderThemeBars(counts) {
  const container = d3.select("#theme-bars");
  const onThemeBarClick = (d) => toggleThemeFilter(d.text);
  if (isPhoneLayout()) {
    renderPhoneThemeBarChart(container, {
      data: counts,
      getLabel: (d) => d.text,
      getValue: (d) => d.count,
      getBarFill: (d) => themeColor(d.text),
      onBarClick: onThemeBarClick,
      onBarTooltip: (event, d) =>
        showTooltip(`<strong>${d.text}</strong><br/>${d.count} submissions`, event, {
          mode: isPhoneLayout() ? "tap" : "hover",
        }),
    });
    return;
  }

  container.selectAll("*").remove();

  const width = chartContainerWidth(container);
  const data = counts;
  const labels = data.map((d) => d.text);
  const leftMargin = themeBarLabelWidth(width, labels);
  const rowHeight = themeBarRowHeight(labels, leftMargin);
  const margin = { top: s(8), right: s(12), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + data.length * rowHeight;
  const svg = appendThemeBarSvg(container, width, height);
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
    .style("cursor", "pointer")
    .on("click", (_, d) => onThemeBarClick(d))
    .on(
      "mousemove",
      isDesktopPointer()
        ? (event, d) =>
            showTooltip(`<strong>${d.text}</strong><br/>${d.count} submissions`, event, { mode: "hover" })
        : null
    )
    .on("mouseleave", isDesktopPointer() ? hideTooltip : null);

  drawThemeBarLabels(g, data, y, (d) => d.text, { maxLabelWidth: leftMargin - s(18) });

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
  const axisFont = isPhoneLayout() ? chartThemePx(PHONE_AXIS_LABEL_SIZE) : themeLabelPx(10);
  const extraBottom = Math.max(isPhoneLayout() ? gs(10) : s(14), axisFont * 1.1);
  const plotHeight = isPhoneLayout() ? gs(200) : s(300);
  const height = plotHeight + extraBottom;
  const margin = isPhoneLayout()
    ? { top: gs(12), right: gs(8), bottom: gs(42) + extraBottom, left: gs(28) }
    : { top: s(24), right: s(24), bottom: s(36) + extraBottom, left: s(44) };
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
    .on("click", (event, d) => {
      state.selectedYear = String(d.year);
      d3.select("#year-select").property("value", state.selectedYear);
      renderAll();
      if (isPhoneLayout()) {
        showTooltip(`<strong>${d.year}</strong><br/>${d.count} submissions`, event, { mode: "tap" });
      }
    })
    .on(
      "mousemove",
      isDesktopPointer()
        ? (event, d) => showTooltip(`<strong>${d.year}</strong><br/>${d.count} submissions`, event, { mode: "hover" })
        : null
    )
    .on("mouseleave", isDesktopPointer() ? hideTooltip : null);

  g.append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(d3.axisBottom(x).tickFormat(d3.format("d")).tickSizeOuter(0))
    .call((sel) =>
      sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(10))
        .style("font-family", CHART_FONT)
        .attr("dy", isPhoneLayout() ? null : "0.82em")
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
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(10))
    )
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));
}

function themeShareByYearRows(submissions) {
  const themes = researchThemeNames();
  const years = [...(state.data?.metadata?.years || [])].sort((a, b) => a - b);
  const byYear = themeCountsByYear(submissions);
  const yearTotals = submissionCountByYear(submissions);
  const totals = globalThemeTotals();
  const orderedThemes = [...themes].sort((a, b) => (totals.get(b) || 0) - (totals.get(a) || 0));

  const rows = years.map((year) => {
    const yearKey = String(year);
    const yearMap = byYear.get(yearKey) || new Map();
    const yearTotal = yearTotals.get(yearKey) || 0;
    const row = { year, yearTotal };
    orderedThemes.forEach((theme) => {
      row[theme] = yearMap.get(theme) || 0;
    });
    return row;
  });

  return { themes: orderedThemes, rows };
}

function renderThemeShareByYear() {
  const container = d3.select("#theme-share-by-year");
  if (container.empty()) return;
  container.selectAll("*").remove();

  const submissions = state.data?.submissions || [];
  const { themes, rows } = themeShareByYearRows(submissions);

  if (!themes.length || !rows.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("No theme data available.");
    return;
  }

  const width = chartContainerWidth(container);
  const stackedLegend = useStackedChartLegend(width);
  const legendFont = isPhoneLayout() ? chartThemePx(PHONE_THEME_TITLE_SIZE) : themeLabelPx(10);
  const legendHeadingFont = isPhoneLayout()
    ? chartThemePx(PHONE_THEME_TITLE_SIZE)
    : themeLabelPx(11);
  const legendCols = isPhoneLayout() ? 1 : stackedLegend ? (width < 520 ? 1 : 2) : 2;
  const legendItemHeight = isPhoneLayout() ? legendFont * 2.05 : legendFont * 1.55;
  const legendTitleHeight = legendHeadingFont * 1.6;
  const legendRowsCount = Math.ceil(themes.length / legendCols);
  const legendBlock = legendTitleHeight + legendRowsCount * legendItemHeight + (isPhoneLayout() ? gs(12) : s(18));

  const axisFont = isPhoneLayout() ? chartThemePx(PHONE_AXIS_LABEL_SIZE) : themeLabelPx(10);
  const extraBottom = Math.max(isPhoneLayout() ? gs(10) : s(14), axisFont * 1.1);
  const plotHeight = isPhoneLayout() ? gs(220) : s(320);
  const margin = isPhoneLayout()
    ? { top: gs(12), right: gs(10), bottom: gs(42) + extraBottom, left: gs(40) }
    : { top: s(20), right: s(20), bottom: s(36) + extraBottom, left: s(52) };
  const height = plotHeight + legendBlock;
  const svg = appendChartSvg(container, width, height);

  const years = rows.map((d) => d.year);
  const x = d3
    .scaleBand()
    .domain(years)
    .range([margin.left, width - margin.right])
    .padding(isPhoneLayout() ? 0.18 : 0.28);

  const stack = d3.stack().keys(themes).order(d3.stackOrderNone).offset(d3.stackOffsetNone);
  const series = stack(rows);
  const maxStack = d3.max(series[series.length - 1], (d) => d[1]) || 1;
  const y = d3
    .scaleLinear()
    .domain([0, Math.max(1, maxStack)])
    .nice()
    .range([plotHeight - margin.bottom, margin.top]);

  const countsByYear = themeCountsByYear(submissions);

  const shareTooltip = (d) => {
    const count = countsByYear.get(String(d.data.year))?.get(d.theme) || 0;
    const yearTotal = d.data.yearTotal || 0;
    return [
      `<strong>${d.theme}</strong>`,
      `${d.data.year}: ${count} topic assignments · ${yearTotal} submissions that year`,
    ].join("<br/>");
  };

  const g = svg.append("g");

  const bands = g
    .selectAll("g.theme-share-series")
    .data(series)
    .join("g")
    .attr("class", "theme-share-series")
    .attr("fill", (d) => themeColor(d.key));

  bands
    .selectAll("rect")
    .data((d) => d.map((point) => ({ theme: d.key, ...point })))
    .join("rect")
    .attr("x", (d) => x(d.data.year))
    .attr("y", (d) => y(d[1]))
    .attr("height", (d) => Math.max(0, y(d[0]) - y(d[1])))
    .attr("width", x.bandwidth())
    .attr("rx", isPhoneLayout() ? gs(1) : s(2))
    .style("cursor", "default")
    .on(
      "mousemove",
      isDesktopPointer() ? (event, d) => showTooltip(shareTooltip(d), event, { mode: "hover" }) : null
    )
    .on("mouseleave", isDesktopPointer() ? hideTooltip : null)
    .on(
      "click",
      isPhoneLayout() ? (event, d) => showTooltip(shareTooltip(d), event, { mode: "tap" }) : null
    );

  g.append("g")
    .attr("transform", `translate(0,${plotHeight - margin.bottom})`)
    .call(d3.axisBottom(x).tickFormat(d3.format("d")).tickSizeOuter(0))
    .call((sel) =>
      sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(10))
        .style("font-family", CHART_FONT)
        .attr("dy", isPhoneLayout() ? null : "0.82em")
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
    .call(
      d3
        .axisLeft(y)
        .ticks(isPhoneLayout() ? 4 : 5)
        .tickFormat((d) => (Number.isInteger(d) ? String(d) : d3.format(".1f")(d)))
    )
    .call((sel) =>
      sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(10))
    )
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  const legend = svg
    .append("g")
    .attr("transform", `translate(${margin.left}, ${plotHeight + (isPhoneLayout() ? gs(4) : s(6))})`);
  const colWidth = (width - margin.left - margin.right) / legendCols;
  const legendMarker = isPhoneLayout() ? gs(8) : s(12);
  const legendTextX = isPhoneLayout() ? gs(12) : s(18);

  legend
    .append("text")
    .attr("class", "theme-share-legend-title")
    .attr("x", 0)
    .attr("y", legendHeadingFont * 0.85)
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", `${legendHeadingFont}px`)
    .style("font-family", CHART_FONT)
    .text("Research themes (counts)");

  legend
    .selectAll("g.legend-item")
    .data(themes)
    .join("g")
    .attr("class", "legend-item")
    .attr("transform", (_, i) => {
      const col = i % legendCols;
      const row = Math.floor(i / legendCols);
      return `translate(${col * colWidth}, ${legendTitleHeight + row * legendItemHeight})`;
    })
    .each(function drawLegendItem(theme) {
      const item = d3.select(this);
      item
        .append("rect")
        .attr("width", legendMarker)
        .attr("height", legendMarker)
        .attr("rx", isPhoneLayout() ? gs(2) : s(3))
        .attr("y", legendFont * 0.15)
        .attr("fill", themeColor(theme));
      item
        .append("text")
        .attr("x", legendTextX)
        .attr("y", legendFont * 0.85)
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_THEME_TITLE_SIZE) : themeFs(10))
        .style("font-family", CHART_FONT)
        .text(fitLegendLabel(theme, colWidth - legendTextX, legendFont));
    });
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
  sub.text(
    state.selectedYear === "all"
      ? `${pair.fromYear} → ${pair.toYear} · change in share of submissions (percentage points)`
      : `${pair.fromYear} → ${pair.toYear} · filtered to year ${state.selectedYear} · change in theme share (percentage points)`
  );

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
      getLabel: (d) => `${d.theme}: ${formatDeltaPct(d.delta)}`,
      getValue: (d) => Math.abs(d.delta),
      getBarFill: (d) => (d.delta >= 0 ? CCN_COLORS.green : CCN_COLORS.pink),
      onBarTooltip: (event, d) =>
        showTooltip(deltaTooltip(d), event, { mode: isPhoneLayout() ? "tap" : "hover" }),
      showValueLabel: false,
      splitLabel: (d) => ({
        prefix: `${d.theme}: `,
        suffix: formatDeltaPct(d.delta),
        suffixFill: d.delta >= 0 ? CCN_COLORS.green : CCN_COLORS.pink,
      }),
    });
    return;
  }

  const width = chartContainerWidth(container);
  const labels = rows.map((d) => d.theme);
  const leftMargin = themeBarLabelWidth(width, labels);
  const rowHeight = themeBarRowHeight(labels, leftMargin);
  const margin = { top: s(8), right: s(12), bottom: s(8), left: leftMargin };
  const height = margin.top + margin.bottom + rows.length * rowHeight;
  const svg = appendThemeBarSvg(container, width, height);
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
    .on(
      "mousemove",
      isDesktopPointer() ? (event, d) => showTooltip(deltaTooltip(d), event, { mode: "hover" }) : null
    )
    .on("mouseleave", isDesktopPointer() ? hideTooltip : null);

  drawThemeBarLabels(g, rows, y, (d) => d.theme, { maxLabelWidth: leftMargin - s(18) });

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
  const submission = submissionForEmbeddingPoint(point);
  if (!submission) return !hasThemeFilter();
  return submissionMatchesThemeFilter(submission);
}

function embeddingPlotDomain(extent, padRatio = 0.06) {
  const [min, max] = extent;
  if (min === undefined || max === undefined) return [0, 1];
  const span = max - min || 1;
  const pad = span * padRatio;
  return [min - pad, max + pad];
}

function renderEmbeddingYearLegend(svg, years, width, plotHeight, margin) {
  const legendFont = isPhoneLayout() ? chartThemePx(PHONE_THEME_TITLE_SIZE) : themeLabelPx(10);
  const legendHeadingFont = isPhoneLayout()
    ? chartThemePx(PHONE_EMBEDDING_LEGEND_HEADING_SIZE)
    : themeLabelPx(11);
  const marker = isPhoneLayout() ? gs(8) : s(10);
  const itemGapX = isPhoneLayout() ? gs(10) : s(14);
  const itemGapY = isPhoneLayout() ? legendFont * 1.7 : legendFont * 1.55;
  const titleHeight = legendHeadingFont * 1.55;
  const usableW = Math.max(120, width - margin.left - margin.right);

  const legendRoot = svg
    .append("g")
    .attr("class", "embedding-year-legend")
    .attr("transform", `translate(${margin.left}, ${plotHeight + (isPhoneLayout() ? gs(6) : s(8))})`);

  legendRoot
    .append("text")
    .attr("class", "embedding-legend-title")
    .attr("x", 0)
    .attr("y", legendHeadingFont * 0.85)
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", `${legendHeadingFont}px`)
    .style("font-family", CHART_FONT)
    .style("font-weight", 600)
    .text("Year (dot color)");

  let cursorX = 0;
  let cursorY = titleHeight;
  let rows = 1;

  years.forEach((year) => {
    const label = String(year);
    const labelW = measureTextWidth(label, legendFont);
    const itemW = marker + (isPhoneLayout() ? gs(4) : s(6)) + labelW;
    if (cursorX > 0 && cursorX + itemW > usableW) {
      cursorX = 0;
      cursorY += itemGapY;
      rows += 1;
    }

    const item = legendRoot.append("g").attr("transform", `translate(${cursorX}, ${cursorY})`);
    item
      .append("circle")
      .attr("cx", marker / 2)
      .attr("cy", legendFont * 0.35)
      .attr("r", marker / 2)
      .attr("fill", yearColor(year))
      .attr("stroke", "#0f2238")
      .attr("stroke-width", isPhoneLayout() ? gs(0.8) : s(1));
    item
      .append("text")
      .attr("x", marker + (isPhoneLayout() ? gs(4) : s(6)))
      .attr("y", legendFont * 0.55)
      .attr("fill", CCN_COLORS.muted)
      .style("font-size", `${legendFont}px`)
      .style("font-family", CHART_FONT)
      .text(label);

    cursorX += itemW + itemGapX;
  });

  const legendBlock = titleHeight + rows * itemGapY + (isPhoneLayout() ? gs(8) : s(12));
  return legendBlock;
}

function renderEmbeddingCluster() {
  const container = d3.select("#embedding-chart");
  container.selectAll("*").remove();

  const note = d3.select("#embedding-note");
  const points = embeddingDisplayPoints();
  if (!points.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("No submissions with map coordinates.");
    note.text("");
    return;
  }

  const years = [...(state.data?.metadata?.years || [])].sort((a, b) => a - b);
  const width = Math.max(280, chartContainerWidth(container));
  const margin = isPhoneLayout()
    ? { top: 10, right: 10, bottom: 10, left: 10 }
    : { top: 16, right: 16, bottom: 16, left: 16 };
  const plotInnerW = Math.max(160, width - margin.left - margin.right);

  const xDomain = embeddingPlotDomain(d3.extent(points, (d) => d.x));
  const yDomain = embeddingPlotDomain(d3.extent(points, (d) => d.y));
  const xSpan = Math.max(xDomain[1] - xDomain[0], 1e-6);
  const ySpan = Math.max(yDomain[1] - yDomain[0], 1e-6);

  // Full-width isotropic layout: same data units per pixel on both axes.
  const unitsPerPx = xSpan / plotInnerW;
  const plotInnerH = ySpan / unitsPerPx;
  const plotHeight = margin.top + plotInnerH + margin.bottom;
  // Provisional height; expand after measuring the year legend.
  const provisionalLegend = isPhoneLayout() ? gs(70) : s(56);
  const svg = appendChartSvg(container, width, plotHeight + provisionalLegend, {
    preserveAspectRatio: "xMidYMid meet",
  });

  const plotBottom = plotHeight - margin.bottom;
  const pointRadius = isPhoneLayout()
    ? { base: 2.4, selected: 3.2, dim: 2.0 }
    : { base: 3.5, selected: 4.25, dim: 2.75 };
  const scaleR = (n) => (isPhoneLayout() ? gs(n) : s(n));

  const x = d3.scaleLinear().domain(xDomain).range([margin.left, width - margin.right]);
  const y = d3.scaleLinear().domain(yDomain).range([plotBottom, margin.top]);

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", margin.top)
    .attr("width", plotInnerW)
    .attr("height", plotInnerH)
    .attr("fill", "rgba(197,224,243,0.04)")
    .attr("rx", isPhoneLayout() ? gs(8) : s(12));

  const pointStyle = (point) => {
    const themeMatch = pointMatchesThemeFilter(point);
    const filtering = hasThemeFilter();
    const highlighted =
      state.highlightedSubmissionKey && submissionRowKey(point) === state.highlightedSubmissionKey;
    const active = !filtering || themeMatch;
    let radius = scaleR(active ? pointRadius.base : pointRadius.dim);
    if (highlighted || (active && filtering)) radius = scaleR(pointRadius.selected);
    const fill = yearColor(point.year);
    return {
      radius,
      opacity: active ? (highlighted ? 1 : 0.9) : 0.14,
      stroke: highlighted || (active && filtering) ? CCN_COLORS.pink : "#0f2238",
      strokeWidth: highlighted || (active && filtering)
        ? isPhoneLayout()
          ? gs(1.75)
          : s(2)
        : isPhoneLayout()
          ? gs(1)
          : s(1.25),
      fill,
    };
  };

  // Draw dimmed points first so highlighted matches stay on top.
  const ordered = [...points].sort((a, b) => {
    const aActive = pointMatchesThemeFilter(a) ? 1 : 0;
    const bActive = pointMatchesThemeFilter(b) ? 1 : 0;
    return aActive - bActive;
  });

  const pointGroups = svg
    .append("g")
    .attr("class", "embedding-points")
    .selectAll("g.embedding-point-group")
    .data(ordered, submissionRowKey)
    .join("g")
    .attr("class", "embedding-point-group")
    .attr("transform", (d) => `translate(${x(d.x)},${y(d.y)})`)
    .style("cursor", "pointer")
    .style("pointer-events", isTouchLike() ? "none" : "auto");

  pointGroups.each(function renderYearPoint(point) {
    const group = d3.select(this);
    group.selectAll("*").remove();
    const style = pointStyle(point);
    appendEmbeddingDot(group, style.radius, {
      opacity: style.opacity,
      stroke: style.stroke,
      strokeWidth: style.strokeWidth,
      fill: style.fill,
    });
  });

  const legendBlock = renderEmbeddingYearLegend(svg, years, width, plotHeight, margin);
  const totalHeight = plotHeight + legendBlock;
  svg.attr("viewBox", `0 0 ${width} ${totalHeight}`);

  if (isTouchLike()) {
    if (isPhoneLayout()) {
      const maxTapDist = 14;
      svg
        .append("rect")
        .attr("class", "embedding-touch-layer")
        .attr("x", margin.left)
        .attr("y", margin.top)
        .attr("width", plotInnerW)
        .attr("height", plotInnerH)
        .attr("fill", "transparent")
        .style("cursor", "pointer")
        .style("touch-action", "manipulation")
        .on("click", (event) => {
          const [px, py] = d3.pointer(event, svg.node());
          let nearest = null;
          let nearestDist = Infinity;
          points.forEach((point) => {
            const dist = Math.hypot(px - x(point.x), py - y(point.y));
            if (dist <= maxTapDist && dist < nearestDist) {
              nearestDist = dist;
              nearest = point;
            }
          });
          if (nearest) {
            event.stopPropagation();
            showEmbeddingPointTooltip(event, nearest, "tap");
          }
        });
    } else {
      svg
        .selectAll("circle.embedding-hit")
        .data(points, submissionRowKey)
        .join("circle")
        .attr("class", "embedding-hit")
        .attr("cx", (d) => x(d.x))
        .attr("cy", (d) => y(d.y))
        .attr("r", 12)
        .attr("fill", "transparent")
        .style("cursor", "pointer")
        .on("click", (event, d) => {
          event.stopPropagation();
          showEmbeddingPointTooltip(event, d, "tap");
        });
    }
  } else if (isDesktopPointer()) {
    pointGroups
      .on("mousemove", (event, d) => {
        cancelHideTooltip();
        showEmbeddingPointTooltip(event, d, "hover");
      })
      .on("mouseleave", () => scheduleHideTooltip())
      .on("click", (event, d) => {
        event.stopPropagation();
        focusSubmissionFromPoint(d);
        hideTooltip();
      });
  } else {
    pointGroups.on("click", (event, d) => {
      event.stopPropagation();
      showEmbeddingPointTooltip(event, d, "tap");
    });
  }

  renderEmbeddingNote(note);
}

function themeFilterSummaryLabel() {
  if (!hasThemeFilter()) return "";
  return themeFilterDisplayText().replace(/^Include papers with /i, "with ").replace(/^Exclude papers with /i, "excluding ");
}

function renderPaperList() {
  const submissions = filteredSubmissions();
  const list = d3.select("#paper-list");
  const countEl = d3.select("#results-count");
  countEl.selectAll("*").remove();

  const filterLabel = themeFilterSummaryLabel();
  const countLabel = filterLabel
    ? `${submissions.length} papers ${filterLabel}`
    : `${submissions.length} matching submissions`;
  countEl.append("span").text(countLabel);

  const selected = new Set(state.selectedThemes);
  const items = list
    .selectAll(".paper-item")
    .data(submissions, submissionRowKey)
    .join("div")
    .attr("class", (d) =>
      `paper-item${submissionRowKey(d) === state.highlightedSubmissionKey ? " highlighted" : ""}`
    )
    .attr("data-id", submissionRowKey);
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
    const tagData = assignedTopicsSorted(d);
    const tags = d3.select(this).append("div").attr("class", "keyword-tags");
    tags
      .selectAll(".keyword-tag")
      .data(tagData)
      .join("span")
      .attr("class", (theme) => `keyword-tag topic-tag${selected.has(theme) ? " active" : ""}`)
      .style("--topic-color", (theme) => themeColor(theme))
      .text((theme) => theme);
  });
}

function renderAll() {
  const scrollSnapshot = { x: window.scrollX, y: window.scrollY };
  removeChartScrollWrappers();
  syncDeltaYearsForYearFilter();
  const submissions = filteredSubmissions();
  const primaryCounts = primaryThemeCounts(submissions);
  const trendSubmissions = submissionsForThemeTrends();

  renderKpis(submissions);
  renderThemeMultiSelect();
  renderYearChart();
  renderThemeShareByYear();
  renderThemeBars(primaryCounts);
  renderResearchThemeDeltas(trendSubmissions);
  renderEmbeddingCluster();
  renderPaperList();

  // Keep sticky phone tap popups open across re-renders; only X closes them.
  if (isPhoneLayout() && tooltipSticky && tooltipAnchorPoint) {
    requestAnimationFrame(() => refreshStickyPhoneTooltip());
  }

  d3.select("#year-chips")
    .selectAll(".year-chip")
    .classed("active", (d) => d === state.selectedYear);

  restorePageScroll(scrollSnapshot.x, scrollSnapshot.y);
}

async function waitForChartFonts() {
  if (!document.fonts?.ready) return;
  try {
    await document.fonts.ready;
  } catch {
    /* ignore font load errors */
  }
}

async function init() {
  ensureD3();
  enforceRootFontSize();

  state.datasetFile = readStoredDatasetFile();
  renderDatasetSelect();

  d3.select("#dataset-select").on("change", async (event) => {
    const nextFile = event.target.value;
    try {
      await loadDataset(nextFile, { resetFilters: true });
    } catch (error) {
      console.error(error);
      showError(`Failed to load dataset: ${error.message}`);
      renderDatasetSelect();
    }
  });

  d3.select("#year-select").on("change", (event) => {
    state.selectedYear = event.target.value;
    state.highlightedSubmissionKey = "";
    renderAll();
  });

  d3.select("#search-input").on("input", (event) => {
    state.search = event.target.value;
    state.highlightedSubmissionKey = "";
    renderAll();
  });

  d3.select("#theme-mode-include").on("click", () => setThemeFilterMode("include"));
  d3.select("#theme-mode-exclude").on("click", () => setThemeFilterMode("exclude"));
  d3.select("#theme-clear-btn").on("click", () => clearThemeFilters());

  d3.select("#delta-from-year").on("change", (event) => {
    state.deltaFromYear = event.target.value;
    renderResearchThemeDeltas(submissionsForThemeTrends());
  });

  d3.select("#delta-to-year").on("change", (event) => {
    state.deltaToYear = event.target.value;
    renderResearchThemeDeltas(submissionsForThemeTrends());
  });

  await waitForChartFonts();
  await loadDataset(state.datasetFile);

  setupTooltipDismiss();

  let resizeTimer = null;
  const scheduleReflow = () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      enforceRootFontSize();
      if (shouldReflowOnResize()) {
        renderAll();
      }
    }, 150);
  };
  // Reflow on layout resize only — not visualViewport pinch-zoom.
  window.addEventListener("resize", scheduleReflow);
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
