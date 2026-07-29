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
  // Viewport + touch only. max-device-width is deprecated and disagrees across browsers.
  return viewportWidth() < PHONE_MAX_WIDTH && isTouchLike();
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

// Yesterday's clean phone chart constants (restored) — do not share desktop scale.
const PHONE_GRAPH_SCALE = 0.72;
const PHONE_CHART_SCALE = 1.2;
const PHONE_UI_SCALE = 1.12;
const PHONE_AXIS_LABEL_SIZE = 10;
const PHONE_THEME_TITLE_SIZE = 12;
const PHONE_BAR_VALUE_SIZE = 12;
const PHONE_LEGEND_HEADING_SIZE = 10.5;
const PHONE_EMBEDDING_LEGEND_HEADING_SIZE = 12.5;

// Shared desktop chart label bases — same in every desktop browser.
// Labels (axes, bar names, legend items) sit slightly above headings so
// in-chart text matches the graphics; card headers stay CSS-driven.
const DESKTOP_CHART_LABEL = 11;
const DESKTOP_CHART_HEADING = 10;

/**
 * Browser-agnostic desktop scale from viewport width only.
 * Prior Brave/Chrome/Windows multipliers stacked up so Mac Chrome needed ~50%
 * browser zoom and Windows needed ~70%. One CSS-px contract everywhere.
 */
let cachedChartScale = 1.25;
let cachedChartScaleKey = "";

function isWindowsPlatform() {
  if (typeof navigator === "undefined") return false;
  const uaDataPlatform = navigator.userAgentData?.platform || "";
  if (/Windows/i.test(uaDataPlatform)) return true;
  if (/Win/i.test(navigator.platform || "")) return true;
  return /Windows/i.test(navigator.userAgent || "");
}

function isBraveBrowser() {
  if (typeof navigator === "undefined") return false;
  if (navigator.brave) return true;
  if (document.documentElement?.classList.contains("is-brave")) return true;
  const brands = navigator.userAgentData?.brands;
  if (Array.isArray(brands) && brands.some((b) => /Brave/i.test(b?.brand || ""))) return true;
  return /\bBrave\b/i.test(navigator.userAgent || "");
}

/** Google Chrome only — not Brave/Edge (both also contain "Chrome" in UA). */
function isGoogleChrome() {
  if (typeof navigator === "undefined" || isBraveBrowser()) return false;
  const ua = navigator.userAgent || "";
  if (/\bEdg\//.test(ua) || /\bOPR\//.test(ua) || /\bSamsungBrowser\//.test(ua)) return false;
  const brands = navigator.userAgentData?.brands;
  if (Array.isArray(brands) && brands.length) {
    return brands.some((b) => /Google Chrome/i.test(b?.brand || ""));
  }
  return /\bChrome\//.test(ua) && !/\bChromium\//.test(ua);
}

/** Desktop root font from layout width (px, not rem/prefs). */
function desktopRootPxForViewport(w = viewportWidth()) {
  const width = Math.max(320, w);
  // ~16px on typical laptops; slight lift on very wide screens only.
  return Math.min(18, Math.max(16, 15.2 + width * 0.0012));
}

/** Desktop SVG design scale from layout width. */
function desktopChartScaleForViewport(w = viewportWidth()) {
  const width = Math.max(320, w);
  // ~1.25 on laptops — about half the old boosted ~2.5–3.2 chart scale.
  return Math.min(1.45, Math.max(1.15, 1.08 + width / 5000));
}

function rootFontPxForViewport() {
  return Math.round(desktopRootPxForViewport() * 100) / 100;
}

function chartDesignScale() {
  if (isPhoneLayout()) return PHONE_CHART_SCALE;
  const w = Math.max(320, viewportWidth());
  const key = `${w}:d`;
  if (key === cachedChartScaleKey) return cachedChartScale;
  cachedChartScaleKey = key;
  cachedChartScale = desktopChartScaleForViewport(w);
  return cachedChartScale;
}

/** Confirm Brave via async API (Shields can hide sync signals) for CSS class only. */
async function confirmBraveDesktopScale() {
  if (isPhoneLayout()) return false;
  try {
    if (!navigator.brave || typeof navigator.brave.isBrave !== "function") return false;
    const yes = await navigator.brave.isBrave();
    if (!yes) return false;
    const wasBrave = document.documentElement.classList.contains("is-brave");
    document.documentElement.classList.add("is-brave");
    applyPageScale();
    return !wasBrave;
  } catch {
    return false;
  }
}

function applyPageScale() {
  const root = document.documentElement;
  if (!root) return;

  cachedChartScaleKey = "";

  const phone = isPhoneLayout();
  const chrome = !phone && isGoogleChrome();
  const brave = !phone && isBraveBrowser();
  const windows = !phone && isWindowsPlatform();
  root.style.zoom = "";
  root.style.removeProperty("--page-zoom");
  root.classList.toggle("is-phone", phone);
  root.classList.toggle("is-chrome", chrome);
  root.classList.toggle("is-brave", brave);
  root.classList.toggle("is-windows", windows);
  root.classList.remove("no-css-zoom");

  if (phone) {
    root.style.fontSize = "100%";
    root.style.setProperty("--ui-scale", String(PHONE_UI_SCALE));
  } else {
    root.style.fontSize = `${rootFontPxForViewport()}px`;
    root.style.setProperty("--ui-scale", "1");
  }

  if (document.body) {
    document.body.style.zoom = "";
    document.body.style.width = "";
    document.body.style.maxWidth = "";
    document.body.style.transform = "";
  }
}

function enforceRootFontSize() {
  applyPageScale();
}

const s = (n) => n * (isPhoneLayout() ? PHONE_CHART_SCALE : chartDesignScale());
const gs = (n) => (isPhoneLayout() ? n * PHONE_CHART_SCALE * PHONE_GRAPH_SCALE : n * chartDesignScale());
const fs = (n) => `${s(n)}px`;

function chartThemePx(base) {
  return isPhoneLayout() ? gs(base) : s(base);
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

function styleDesktopChartText(selection) {
  if (isPhoneLayout()) return selection;
  selection.style("font-family", CHART_FONT);
  // Brave paints light type thinner — slightly heavier weight helps match Chrome/Safari.
  selection.style("font-weight", isBraveBrowser() ? "500" : "400");
  return selection;
}

// DOM measurement — not canvas.measureText(), which Brave Shields / privacy
// browsers noise or zero out as a fingerprinting surface, collapsing layouts.
let measureTextEl = null;

function heuristicTextWidth(text, fontSizePx) {
  return Math.max(1, String(text).length * fontSizePx * 0.58);
}

function ensureMeasureTextEl() {
  if (measureTextEl && measureTextEl.isConnected) return measureTextEl;
  if (typeof document === "undefined") return null;
  const host = document.body || document.documentElement;
  if (!host) return null;
  measureTextEl = document.createElement("span");
  measureTextEl.setAttribute("aria-hidden", "true");
  measureTextEl.style.cssText =
    "position:absolute;left:-99999px;top:0;visibility:hidden;white-space:pre;" +
    "margin:0;padding:0;border:0;pointer-events:none;contain:layout style;";
  host.appendChild(measureTextEl);
  return measureTextEl;
}

function measureTextWidth(text, fontSizePx, fontFamily = CHART_FONT) {
  const value = text == null ? "" : String(text);
  const size = Number(fontSizePx);
  const fontPx = Number.isFinite(size) && size > 0 ? size : 12;
  if (typeof document === "undefined") return heuristicTextWidth(value, fontPx);

  const el = ensureMeasureTextEl();
  if (!el) return heuristicTextWidth(value, fontPx);

  el.style.font = `${fontPx}px ${fontFamily}`;
  el.textContent = value;
  // offsetWidth / getBoundingClientRect use real layout metrics, not canvas.
  const width = el.offsetWidth || el.getBoundingClientRect().width;
  if (!Number.isFinite(width) || width <= 0) return heuristicTextWidth(value, fontPx);
  return width;
}

function themeBarLabelWidth(containerWidth = 0, labels = []) {
  const w = Math.max(containerWidth || viewportWidth(), 320);
  const labelFont = themeLabelPx(DESKTOP_CHART_LABEL);
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
  const fontPx = themeLabelPx(DESKTOP_CHART_LABEL);
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
  const valueFont = themeLabelPx(DESKTOP_CHART_LABEL);
  const maxLabelWidth =
    d3.max(rows, (row) => measureTextWidth(formatValue(row), valueFont)) || measureTextWidth("+0.0%", valueFont);
  const reserve = Math.max(maxLabelWidth + s(12), s(40));
  return Math.max(s(80), innerW - reserve);
}

function themeBarLabelX(gap = 8) {
  return -s(gap);
}

function drawThemeBarLabels(g, data, y, getLabel, options = {}) {
  const baseFont = options.baseFont ?? DESKTOP_CHART_LABEL;
  const fill = options.fill ?? CCN_COLORS.muted;
  const gap = options.gap ?? 8;
  const fontPx = themeLabelPx(baseFont);
  const maxLabelWidth = options.maxLabelWidth ?? 0;
  const labelX = themeBarLabelX(gap);
  const lineHeightEm = 1.15;

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
        .attr("dominant-baseline", "central")
        .attr("fill", typeof fill === "function" ? fill(d) : fill)
        .style("font-size", themeFs(baseFont))
        .style("pointer-events", options.pointerEvents || "auto");
      styleDesktopChartText(text);

      // Center the whole label block on the bar midline.
      const startDy = -((lines.length - 1) * lineHeightEm) / 2;
      lines.forEach((line, i) => {
        const dy = i === 0 ? `${startDy}em` : `${lineHeightEm}em`;
        text.append("tspan").attr("x", labelX).attr("dy", dy).text(line);
      });
    });
}

function styleThemeAxisLabels(selection) {
  const labels = selection
    .selectAll("text")
    .attr("fill", CCN_COLORS.muted)
    .attr("dominant-baseline", "central")
    .style("font-size", isPhoneLayout() ? chartThemeFs(8) : themeFs(DESKTOP_CHART_LABEL));
  styleDesktopChartText(labels);
}

// Topics: matplotlib turbo samples (t≈0.08→0.92), evenly spaced for wider
// hue gaps between adjacent themes. Avoids turbo's darkest blues so colors
// stay distinct from the cool bone year ramp.
const CHART_PALETTE = [
  "#424BB5", // 1. Reinforcement learning
  "#4778F0", // 2. Motor control & planning
  "#3BA0FD", // 3. Naturalistic encoding/decoding
  "#1FC9DD", // 4. Neural population geometry & dynamics
  "#1CE6B4", // 5. Decision-making and metacognition
  "#4AF880", // 6. Vision
  "#88FF4E", // 7. Perception
  "#B9F635", // 8. Language/auditory neuroscience
  "#DFDF37", // 9. AI, LLM, & neural networks
  "#F9BC39", // 10. Memory
  "#FE932A", // 11. Social cognition & theory of mind
  "#F26014", // 12. Attention & cognitive control / executive function
  "#DC3B07", // 13. Clinical / computational psychiatry
  "#B71D02", // 14. Methods and theory
];

// Years: matplotlib bone sequential (t≈0.32→1.0). Wider lightness steps so
// adjacent conference years read apart, still a quiet cool gray→white blend.
const YEAR_PALETTE = [
  "#474763", // 2017
  "#5D617D", // 2018
  "#737F92", // 2019
  "#889DA8", // 2022
  "#9EBBBE", // 2023
  "#BCD4D4", // 2024
  "#DEEAEA", // 2025
  "#FFFFFF", // 2026
];

const YEAR_COLORS = Object.fromEntries(
  [2017, 2018, 2019, 2022, 2023, 2024, 2025, 2026].map((year, i) => [
    year,
    YEAR_PALETTE[i % YEAR_PALETTE.length],
  ])
);

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
  "AI, LLM, & neural networks",
  "Memory",
  "Social cognition & theory of mind",
  "Attention & cognitive control / executive function",
  "Clinical / computational psychiatry",
  "Methods and theory",
];

// Single fixed dataset — first two topics only.
const FIXED_DATASET = "abstracts_2_topics.csv";

const state = {
  data: null,
  datasetFile: FIXED_DATASET,
  selectedYears: [],
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
let tooltipSticky = false; // tap/click popups stay until X (phone + desktop)
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
    // Sticky tap/click popups stay until the user hits X.
    if (tooltipVisible && !tooltipSticky) hideTooltip();
  };

  // Capture phase catches window scroll and nested scrollers (e.g. paper list).
  document.addEventListener("scroll", dismissOnScroll, { passive: true, capture: true });
  window.addEventListener("scroll", dismissOnScroll, { passive: true, capture: true });
  window.visualViewport?.addEventListener("scroll", dismissOnScroll, { passive: true });
  window.visualViewport?.addEventListener("resize", dismissOnScroll, { passive: true });

  // Click outside a sticky popup dismisses it (topic buttons / X stay interactive).
  document.addEventListener(
    "pointerdown",
    (event) => {
      if (!tooltipVisible || !tooltipSticky) return;
      const node = tooltip?.node();
      if (node && node.contains(event.target)) return;
      if (event.target?.closest?.(".embedding-point-group, .embedding-hit, .embedding-touch-layer")) {
        return;
      }
      hideTooltip();
    },
    true
  );

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && tooltipVisible) hideTooltip();
  });
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
  // Click/tap pins the popup so moving across nearby dots won't steal it.
  tooltipSticky = mode === "tap";
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

function refreshStickyTooltip() {
  if (!tooltipSticky || !tooltipAnchorPoint) return;
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

function buildStateFromCsv(rows, source = FIXED_DATASET) {
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

async function loadDataset(options = {}) {
  const { resetFilters = false } = options;
  const datasetFile = FIXED_DATASET;
  const csvRows = await d3.csv(`data/${datasetFile}?v=120`);
  if (!csvRows?.length) {
    throw new Error(`Could not load data/${datasetFile}`);
  }

  state.datasetFile = datasetFile;
  state.data = buildStateFromCsv(csvRows, datasetFile);

  if (resetFilters) {
    state.selectedYears = [];
    state.search = "";
    state.selectedThemes = [];
    state.themeFilterMode = "include";
    state.highlightedSubmissionKey = "";
    state.deltaFromYear = "";
    state.deltaToYear = "";
    d3.select("#search-input").property("value", "");
    closeYearMultiSelect();
  } else if (hasYearFilter()) {
    const available = new Set(state.data.metadata.years.map(String));
    state.selectedYears = state.selectedYears.filter((year) => available.has(String(year)));
  }

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

function hasSearchFilter() {
  return Boolean(state.search.trim());
}

function hasYearFilter() {
  return state.selectedYears.length > 0;
}

function hasAnyFilter() {
  return hasYearFilter() || hasSearchFilter() || hasThemeFilter();
}

function sortedSelectedYears() {
  return [...state.selectedYears]
    .map(String)
    .sort((a, b) => Number(a) - Number(b));
}

function submissionMatchesYearFilter(submission) {
  if (!hasYearFilter()) return true;
  return state.selectedYears.map(String).includes(String(submission.year));
}

/** Theme chips, text search, and/or years — used to highlight matching UMAP dots. */
function hasMapHighlightFilter() {
  return hasThemeFilter() || hasSearchFilter() || hasYearFilter();
}

function submissionMatchesThemeFilter(submission) {
  if (!hasThemeFilter()) return true;
  const assigned = assignedTopics(submission);
  // Multi-topic filters require all selected topics ("all of"), not any-of.
  const hitsAll = state.selectedThemes.every((theme) => assigned.includes(theme));
  return state.themeFilterMode === "exclude" ? !hitsAll : hitsAll;
}

function submissionMatchesMapHighlight(submission) {
  if (!submission) return !hasMapHighlightFilter();
  const search = state.search.trim().toLowerCase();
  const yearOk = submissionMatchesYearFilter(submission);
  const searchOk = !search || submissionMatchesSearch(submission, search);
  const themeOk = submissionMatchesThemeFilter(submission);
  return yearOk && searchOk && themeOk;
}

function filteredSubmissions() {
  const { submissions } = state.data;
  const search = state.search.trim().toLowerCase();

  return submissions.filter((item) => {
    const yearOk = submissionMatchesYearFilter(item);
    const searchOk = !search || submissionMatchesSearch(item, search);
    const themeOk = submissionMatchesThemeFilter(item);
    return yearOk && searchOk && themeOk;
  });
}

function submissionsForThemeTrends() {
  // YoY comparison keeps its own from/to year controls; apply search + topics only.
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
  // Stable index from the fixed topic list (not the filtered/sorted UI order).
  const index = GOOGLE_FORM_TOPICS.indexOf(theme);
  return CHART_PALETTE[(index >= 0 ? index : 0) % CHART_PALETTE.length];
}

function yearColor(year) {
  const key = Number(year);
  if (YEAR_COLORS[key]) return YEAR_COLORS[key];
  // Fallback for unexpected years: stable hash into the fixed palette.
  const palette = Object.values(YEAR_COLORS);
  const index = Number.isFinite(key) ? Math.abs(key) % palette.length : 0;
  return palette[index];
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
  if (state.selectedYears.length === 1) {
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
  if (state.selectedYears.length !== 1) return;
  const pair = conferenceYearPairForSelection(state.selectedYears[0]);
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

function toggleYearFilter(year, options = {}) {
  if (year == null || year === "") return;
  const { rerender = true } = options;
  const key = String(year);
  const selected = new Set(state.selectedYears.map(String));
  if (selected.has(key)) selected.delete(key);
  else selected.add(key);
  state.selectedYears = [...selected].sort((a, b) => Number(a) - Number(b));
  state.highlightedSubmissionKey = "";
  if (rerender) renderAll();
}

function clearThemeFilters() {
  state.selectedThemes = [];
  state.highlightedSubmissionKey = "";
  renderAll();
}

function clearAllFilters() {
  state.selectedYears = [];
  state.search = "";
  state.selectedThemes = [];
  state.themeFilterMode = "include";
  state.highlightedSubmissionKey = "";
  d3.select("#search-input").property("value", "");
  closeYearMultiSelect();
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

  if (hasYearFilter() && !submissionMatchesYearFilter(submission)) {
    state.selectedYears = [String(submission.year)];
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

function yearFilterDisplayText() {
  if (!hasYearFilter()) return "";
  const years = sortedSelectedYears();
  if (years.length === 1) return `Year ${years[0]}`;
  if (years.length === 2) return `Years ${years[0]} and ${years[1]}`;
  return `Years ${years.slice(0, -1).join(", ")}, and ${years[years.length - 1]}`;
}

function searchFilterDisplayText() {
  if (!hasSearchFilter()) return "";
  return `Search “${state.search.trim()}”`;
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

function activeFilterParts() {
  return [yearFilterDisplayText(), searchFilterDisplayText(), themeFilterDisplayText()].filter(Boolean);
}

function activeFilterDisplayText() {
  return activeFilterParts().join(" · ");
}

function yearMultiSelectLabel() {
  if (!hasYearFilter()) return "All years";
  const years = sortedSelectedYears();
  if (years.length <= 2) return years.join(", ");
  return `${years.length} years`;
}

function embeddingDefaultNote() {
  const count = embeddingDisplayPoints().length;
  const highlighted = embeddingHighlightCount();
  if (state.highlightedSubmissionKey) {
    return "Jumped to highlighted submission below — topic tags are shown on the card";
  }
  if (hasMapHighlightFilter()) {
    return `${count} papers on map · ${highlighted} highlighted · ${activeFilterDisplayText()}`;
  }
  return isTouchLike()
    ? `${count} submissions · colored by year · tap a dot to see topics and filter · or open the paper`
    : `${count} submissions · colored by year · hover a dot for topics · click a dot to pin the popup`;
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

/** Compact author line for embedding popups (drop affiliations / emails). */
function formatAuthorsForTooltip(submission, { maxNames = 6 } = {}) {
  const raw = String(submission?.authors || submission?.author || "").trim();
  if (!raw) return "";

  // Keep the name block before affiliation footnotes ("… ; 1 University…").
  let block = raw.split(";")[0].trim();
  block = block.replace(/\([^)]*@[^)]*\)/g, " ");
  block = block.replace(/\s+/g, " ").trim();

  const names = block
    .split(/\s*,\s*/)
    .map((part) => part.replace(/\s+\d+\s*$/g, "").replace(/\s*[\d†‡*#]+\s*$/g, "").trim())
    .filter((part) => part && !/^\d+$/.test(part) && part.length > 1);

  if (!names.length) {
    return String(submission?.author || "").trim();
  }
  if (names.length <= maxNames) {
    return names.join(", ");
  }
  return `${names.slice(0, maxNames).join(", ")}, et al.`;
}

function embeddingPointTooltipHtml(point) {
  const submission = submissionForEmbeddingPoint(point);
  const topics = embeddingPointTopics(point);
  const selected = new Set(state.selectedThemes);
  const title = escapeHtml(submission?.title || point.title || "Submission");
  const year = submission?.year ?? point.year;
  const yearLabel = year != null ? escapeHtml(String(year)) : "";
  const yearSwatch = year != null ? yearColor(year) : CCN_COLORS.muted;
  const authorsLabel = escapeHtml(formatAuthorsForTooltip(submission));
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
    : "Click a topic to filter · × closes pinned popup";
  return [
    `<strong>${title}</strong>`,
    yearLabel
      ? `<div class="tooltip-year"><span class="tooltip-year-swatch" style="background:${yearSwatch}"></span>${yearLabel}</div>`
      : "",
    authorsLabel ? `<div class="tooltip-authors">${authorsLabel}</div>` : "",
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
      // Keep pinned popups open and refresh active topic chips.
      if (tooltipSticky) {
        requestAnimationFrame(() => refreshStickyTooltip());
      }
    },
    onOpenPaper: () => {
      focusSubmissionFromPoint(point);
      hideTooltip();
    },
  });
}

function embeddingHighlightCount() {
  return embeddingDisplayPoints().filter((point) => pointMatchesMapHighlight(point)).length;
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

function closeYearMultiSelect() {
  const menuNode = document.getElementById("year-multi-menu");
  const toggle = d3.select("#year-multi-toggle");
  if (menuNode) menuNode.hidden = true;
  if (!toggle.empty()) toggle.attr("aria-expanded", "false");
}

function toggleYearMultiSelectMenu(forceOpen) {
  const menuNode = document.getElementById("year-multi-menu");
  const toggle = d3.select("#year-multi-toggle");
  if (!menuNode || toggle.empty()) return;
  const currentlyOpen = !menuNode.hidden;
  const shouldOpen = forceOpen != null ? Boolean(forceOpen) : !currentlyOpen;
  menuNode.hidden = !shouldOpen;
  toggle.attr("aria-expanded", shouldOpen ? "true" : "false");
}

function renderYearControls() {
  const years = (state.data?.metadata?.years || []).map(String);
  const selected = new Set(state.selectedYears.map(String));
  const toggle = d3.select("#year-multi-toggle");
  const menu = d3.select("#year-multi-menu");
  if (toggle.empty() || menu.empty()) return;

  toggle.html(`<span class="year-multi-toggle-label">${escapeHtml(yearMultiSelectLabel())}</span>`);

  menu
    .selectAll("button.year-option")
    .data(years, (d) => d)
    .join("button")
    .attr("type", "button")
    .attr("class", "year-option")
    .attr("role", "option")
    .attr("aria-selected", (year) => (selected.has(year) ? "true" : "false"))
    .style("--year-color", (year) => yearColor(year))
    .html(
      (year) =>
        `<span class="year-option-check" aria-hidden="true">${selected.has(year) ? "✓" : ""}</span>` +
        `<span class="year-option-swatch" aria-hidden="true"></span>` +
        `<span>${escapeHtml(year)}</span>`
    )
    .on("click", (event, year) => {
      event.preventDefault();
      event.stopPropagation();
      toggleYearFilter(year);
      // Keep the menu open for multi-select.
      toggleYearMultiSelectMenu(true);
    });
}

function renderFilterStatus() {
  const status = d3.select("#theme-filter-status");
  if (status.empty()) return;
  const node = status.node();
  const clearAll = d3.select("#clear-all-filters-btn");
  if (!clearAll.empty()) clearAll.node().hidden = !hasAnyFilter();

  if (!hasAnyFilter()) {
    if (node) node.hidden = true;
    status.text("");
    return;
  }
  if (node) node.hidden = false;
  status.html(`<strong>Active filter:</strong> ${escapeHtml(activeFilterDisplayText())}`);
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
    .style("--topic-color", (theme) => themeColor(theme))
    .attr("aria-pressed", (theme) => (selected.has(theme) ? "true" : "false"))
    .text((theme) => theme)
    .on("click", (_, theme) => toggleThemeFilter(theme));

  d3.select("#theme-mode-include").classed("active", !exclude);
  d3.select("#theme-mode-exclude").classed("active", exclude);

  const clearBtn = d3.select("#theme-clear-btn");
  if (!clearBtn.empty()) clearBtn.node().hidden = !hasThemeFilter();
  renderYearControls();
  renderFilterStatus();
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
    .attr("dominant-baseline", "central")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", themeFs(DESKTOP_CHART_LABEL))
    .call((sel) => styleDesktopChartText(sel))
    .text((d) => d.count);
}

function submissionsOverTimeCounts() {
  const filtered = filteredSubmissions();
  const countsMap = submissionCountByYear(filtered);
  const years = hasYearFilter()
    ? sortedSelectedYears().map(Number)
    : [...(state.data?.metadata?.years || [])].map(Number).sort((a, b) => a - b);
  return years.map((year) => ({
    year,
    count: countsMap.get(String(year)) || 0,
  }));
}

function renderYearChart() {
  const container = d3.select("#year-chart");
  container.selectAll("*").remove();

  const counts = submissionsOverTimeCounts();
  const selected = new Set(state.selectedYears.map(String));

  const width = chartContainerWidth(container);
  const axisFont = isPhoneLayout() ? chartThemePx(PHONE_AXIS_LABEL_SIZE) : themeLabelPx(DESKTOP_CHART_LABEL);
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
    .attr("r", (d) =>
      selected.has(String(d.year))
        ? isPhoneLayout()
          ? gs(4.5)
          : s(7)
        : isPhoneLayout()
          ? gs(3.5)
          : s(5)
    )
    .attr("fill", (d) => (selected.has(String(d.year)) ? CCN_COLORS.pink : CCN_COLORS.green))
    .attr("stroke", CCN_COLORS.navy)
    .attr("stroke-width", isPhoneLayout() ? gs(1.5) : s(2))
    .style("cursor", "pointer")
    .on("click", (event, d) => {
      toggleYearFilter(d.year);
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
    .call((sel) => {
      const ticks = sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .attr("text-anchor", "middle")
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(DESKTOP_CHART_LABEL))
        .attr("dy", isPhoneLayout() ? null : "1em");
      styleDesktopChartText(ticks);
    })
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
    .call((sel) => {
      const ticks = sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .attr("dominant-baseline", "central")
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(DESKTOP_CHART_LABEL));
      styleDesktopChartText(ticks);
    })
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));
}

function themeShareByYearRows(submissions) {
  const themes = researchThemeNames();
  const availableYears = [...(state.data?.metadata?.years || [])].sort((a, b) => a - b);
  const years = hasYearFilter()
    ? sortedSelectedYears().map(Number)
    : availableYears;
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

  const submissions = filteredSubmissions();
  const { themes, rows } = themeShareByYearRows(submissions);

  if (!themes.length || !rows.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("No theme data available.");
    return;
  }

  const width = chartContainerWidth(container);
  const stackedLegend = useStackedChartLegend(width);
  const legendFont = isPhoneLayout() ? chartThemePx(PHONE_THEME_TITLE_SIZE) : themeLabelPx(DESKTOP_CHART_LABEL);
  const legendHeadingFont = isPhoneLayout()
    ? chartThemePx(PHONE_THEME_TITLE_SIZE)
    : themeLabelPx(DESKTOP_CHART_HEADING);
  const legendCols = isPhoneLayout() ? 1 : stackedLegend ? (width < 520 ? 1 : 2) : 2;
  const legendItemHeight = isPhoneLayout() ? legendFont * 2.05 : legendFont * 1.55;
  const legendTitleHeight = legendHeadingFont * 1.6;
  const legendRowsCount = Math.ceil(themes.length / legendCols);
  const legendBlock = legendTitleHeight + legendRowsCount * legendItemHeight + (isPhoneLayout() ? gs(12) : s(18));

  const axisFont = isPhoneLayout() ? chartThemePx(PHONE_AXIS_LABEL_SIZE) : themeLabelPx(DESKTOP_CHART_LABEL);
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
    .call((sel) => {
      const ticks = sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .attr("text-anchor", "middle")
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(DESKTOP_CHART_LABEL))
        .attr("dy", isPhoneLayout() ? null : "1em");
      styleDesktopChartText(ticks);
    })
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
    .call((sel) => {
      const ticks = sel
        .selectAll("text")
        .attr("fill", CCN_COLORS.muted)
        .attr("dominant-baseline", "central")
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_AXIS_LABEL_SIZE) : themeFs(DESKTOP_CHART_LABEL));
      styleDesktopChartText(ticks);
    })
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  const legend = svg
    .append("g")
    .attr("transform", `translate(${margin.left}, ${plotHeight + (isPhoneLayout() ? gs(4) : s(6))})`);
  const colWidth = (width - margin.left - margin.right) / legendCols;
  const legendMarker = isPhoneLayout() ? gs(8) : s(12);
  const legendTextX = isPhoneLayout() ? gs(12) : s(18);
  const legendMidY = Math.max(legendMarker, legendFont) / 2;

  const legendTitle = legend
    .append("text")
    .attr("class", "theme-share-legend-title")
    .attr("x", 0)
    .attr("y", legendHeadingFont * 0.85)
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", `${legendHeadingFont}px`)
    .text("Research themes (counts)");
  styleDesktopChartText(legendTitle);

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
        .attr("y", legendMidY - legendMarker / 2)
        .attr("fill", themeColor(theme));
      const legendLabel = item
        .append("text")
        .attr("x", legendTextX)
        .attr("y", legendMidY)
        .attr("dominant-baseline", "central")
        .attr("fill", CCN_COLORS.muted)
        .style("font-size", isPhoneLayout() ? chartThemeFs(PHONE_THEME_TITLE_SIZE) : themeFs(DESKTOP_CHART_LABEL))
        .text(fitLegendLabel(theme, colWidth - legendTextX, legendFont));
      styleDesktopChartText(legendLabel);
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
  const trendFilterParts = [searchFilterDisplayText(), themeFilterDisplayText()].filter(Boolean);
  sub.text(
    trendFilterParts.length
      ? `${pair.fromYear} → ${pair.toYear} · ${trendFilterParts.join(" · ")} · change in theme share (percentage points)`
      : `${pair.fromYear} → ${pair.toYear} · change in share of submissions (percentage points)`
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
    .attr("dominant-baseline", "central")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", themeFs(DESKTOP_CHART_LABEL))
    .call((sel) => styleDesktopChartText(sel))
    .text((d) => formatDeltaPct(d.delta));
}

function pointMatchesThemeFilter(point) {
  const submission = submissionForEmbeddingPoint(point);
  if (!submission) return !hasThemeFilter();
  return submissionMatchesThemeFilter(submission);
}

function pointMatchesMapHighlight(point) {
  const submission = submissionForEmbeddingPoint(point);
  return submissionMatchesMapHighlight(submission);
}

function embeddingPlotDomain(extent, padRatio = 0.06) {
  const [min, max] = extent;
  if (min === undefined || max === undefined) return [0, 1];
  const span = max - min || 1;
  const pad = span * padRatio;
  return [min - pad, max + pad];
}

function renderEmbeddingYearLegend(svg, years, width, plotHeight, margin) {
  const legendFont = isPhoneLayout() ? chartThemePx(PHONE_THEME_TITLE_SIZE) : themeLabelPx(DESKTOP_CHART_LABEL);
  const legendHeadingFont = isPhoneLayout()
    ? chartThemePx(PHONE_EMBEDDING_LEGEND_HEADING_SIZE)
    : themeLabelPx(DESKTOP_CHART_HEADING);
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
    const midY = Math.max(marker, legendFont) / 2;
    item
      .append("circle")
      .attr("cx", marker / 2)
      .attr("cy", midY)
      .attr("r", marker / 2)
      .attr("fill", yearColor(year))
      .attr("stroke", "#0f2238")
      .attr("stroke-width", isPhoneLayout() ? gs(0.8) : s(1));
    item
      .append("text")
      .attr("x", marker + (isPhoneLayout() ? gs(4) : s(6)))
      .attr("y", midY)
      .attr("dominant-baseline", "central")
      .attr("fill", CCN_COLORS.muted)
      .style("font-size", `${legendFont}px`)
      .style("font-family", CHART_FONT)
      .text(label);

    cursorX += itemW + itemGapX;
  });

  const legendBlock = titleHeight + rows * itemGapY + (isPhoneLayout() ? gs(8) : s(12));
  return legendBlock;
}

/** Desktop dots track plot/viewport (+ Windows/Brave boost). Phone: slightly smaller gs() radii. */
function embeddingPointRadii(plotInnerW) {
  if (isPhoneLayout()) {
    const base = gs(2.1);
    return {
      base,
      selected: gs(2.8),
      dim: gs(1.75),
      stroke: gs(0.9),
      strokeActive: gs(1.5),
    };
  }
  const w = Math.max(320, viewportWidth());
  // ~0.8% of plot width — viewport only, no browser multiplier.
  const fromPlot = plotInnerW / 125;
  const fromViewport = w / 200;
  const raw = Math.max(fromPlot, fromViewport * 0.9);
  const base = Math.min(11, Math.max(3.8, raw));
  return {
    base,
    selected: base * 1.4,
    dim: base * 0.8,
    stroke: Math.max(1, base * 0.32),
    strokeActive: Math.max(1.25, base * 0.5),
  };
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

  // Keep equal data-units per pixel in x and y so the UMAP cloud keeps its
  // true shape (no vertical squeeze into a fixed wide rectangle).
  const unitsPerPxX = xSpan / plotInnerW;
  const plotInnerH = Math.max(120, ySpan / unitsPerPxX);
  const plotHeight = margin.top + plotInnerH + margin.bottom;
  // Provisional height; expand after measuring the year legend.
  const provisionalLegend = isPhoneLayout() ? gs(70) : s(56);
  const svg = appendChartSvg(container, width, plotHeight + provisionalLegend, {
    preserveAspectRatio: "xMidYMid meet",
  });

  const plotBottom = plotHeight - margin.bottom;
  const pointRadius = embeddingPointRadii(plotInnerW);

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
    const match = pointMatchesMapHighlight(point);
    const filtering = hasMapHighlightFilter();
    const highlighted =
      state.highlightedSubmissionKey && submissionRowKey(point) === state.highlightedSubmissionKey;
    const active = !filtering || match;
    let radius = active ? pointRadius.base : pointRadius.dim;
    if (highlighted || (active && filtering)) radius = pointRadius.selected;
    const fill = yearColor(point.year);
    return {
      radius,
      opacity: active ? (highlighted ? 1 : 0.9) : 0.14,
      stroke: highlighted || (active && filtering) ? CCN_COLORS.pink : "#0f2238",
      strokeWidth: highlighted || (active && filtering) ? pointRadius.strokeActive : pointRadius.stroke,
      fill,
    };
  };

  // Draw dimmed points first so highlighted matches stay on top.
  const ordered = [...points].sort((a, b) => {
    const aActive = pointMatchesMapHighlight(a) ? 1 : 0;
    const bActive = pointMatchesMapHighlight(b) ? 1 : 0;
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
      const maxTapDist = Math.max(16, pointRadius.selected * 2.8);
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
        .attr("r", Math.max(12, pointRadius.selected * 2.2))
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
        // Pinned click popup stays put — don't let nearby dots steal it.
        if (tooltipSticky) return;
        cancelHideTooltip();
        showEmbeddingPointTooltip(event, d, "hover");
      })
      .on("mouseleave", () => {
        if (tooltipSticky) return;
        scheduleHideTooltip();
      })
      .on("click", (event, d) => {
        event.stopPropagation();
        // Pin popup so topics stay clickable while moving across dense dots.
        showEmbeddingPointTooltip(event, d, "tap");
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
  const parts = activeFilterParts();
  if (!parts.length) return "";
  return parts.join(" · ");
}

function renderPaperList() {
  const submissions = filteredSubmissions();
  const list = d3.select("#paper-list");
  const countEl = d3.select("#results-count");
  countEl.selectAll("*").remove();

  const filterLabel = themeFilterSummaryLabel();
  const countLabel = filterLabel
    ? `${submissions.length} papers · ${filterLabel}`
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

  // Keep sticky tap/click popups open across re-renders; only X closes them.
  if (tooltipSticky && tooltipAnchorPoint) {
    requestAnimationFrame(() => refreshStickyTooltip());
  }

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
  applyPageScale();

  state.datasetFile = FIXED_DATASET;

  d3.select("#year-multi-toggle").on("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    toggleYearMultiSelectMenu();
  });

  d3.select("#clear-all-filters-btn").on("click", () => clearAllFilters());

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

  document.addEventListener(
    "pointerdown",
    (event) => {
      const root = document.getElementById("year-multi-select");
      if (!root || root.contains(event.target)) return;
      closeYearMultiSelect();
    },
    true
  );

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeYearMultiSelect();
  });

  await waitForChartFonts();
  applyPageScale();
  // Resolve Brave async so desktop type/charts match before first paint settles.
  await confirmBraveDesktopScale();
  await loadDataset();

  setupTooltipDismiss();

  let resizeTimer = null;
  const scheduleReflow = () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      applyPageScale();
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
