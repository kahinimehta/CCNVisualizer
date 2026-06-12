const CCN_COLORS = {
  navy: "#1a3b5d",
  pink: "#f4c7c3",
  blue: "#c5e0f3",
  green: "#c8e6c9",
  white: "#f7fafc",
  muted: "#8fa8c4",
  card: "#162d47",
};

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

const BLOCKED_TOPICS = new Set(["view pdf", "view paper pdf", "uncategorized", ""]);

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
  selectedKeyword: "",
  selectedCluster: "",
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
    .style("left", `${event.pageX + 12}px`)
    .style("top", `${event.pageY + 12}px`);
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

function filteredSubmissions() {
  const { submissions } = state.data;
  return submissions.filter((item) => {
    const yearOk = state.selectedYear === "all" || String(item.year) === state.selectedYear;
    const search = state.search.trim().toLowerCase();
    const searchOk =
      !search ||
      item.title.toLowerCase().includes(search) ||
      item.authors.toLowerCase().includes(search) ||
      item.keywords.some((kw) => kw.includes(search)) ||
      (item.topic_area || "").toLowerCase().includes(search);
    const keywordOk = !state.selectedKeyword || item.keywords.includes(state.selectedKeyword);
    return yearOk && searchOk && keywordOk;
  });
}

function keywordCounts(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    [...new Set(item.keywords)].forEach((kw) => counts.set(kw, (counts.get(kw) || 0) + 1));
  });
  return [...counts.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count);
}

function topicCounts(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    if (!item.topic_area) return;
    const topic = item.topic_area.toLowerCase();
    counts.set(topic, (counts.get(topic) || 0) + 1);
  });
  return [...counts.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);
}

function submissionTopic(submission) {
  if (state.googleTopics?.enabled) {
    const assigned = state.googleTopics.assignments?.[submission.id];
    if (assigned) return assigned.toLowerCase();
    const topics = state.googleTopics.topics || [];
    if (topics.length) return "unassigned";
  }
  if (submission.topic_area && !BLOCKED_TOPICS.has(submission.topic_area.toLowerCase())) {
    return submission.topic_area.toLowerCase();
  }
  const tokenTopic = submission.keywords.find((kw) => kw && !BLOCKED_TOPICS.has(kw));
  return tokenTopic || "uncategorized";
}

function topicCountsByYear(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    const year = String(item.year);
    const topic = submissionTopic(item);
    if (BLOCKED_TOPICS.has(topic)) return;
    if (!counts.has(year)) counts.set(year, new Map());
    const yearMap = counts.get(year);
    yearMap.set(topic, (yearMap.get(topic) || 0) + 1);
  });
  return counts;
}

function topTopicsOverTime(submissions, limit = 8) {
  const totals = new Map();
  submissions.forEach((item) => {
    const topic = submissionTopic(item);
    if (BLOCKED_TOPICS.has(topic)) return;
    totals.set(topic, (totals.get(topic) || 0) + 1);
  });
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([topic]) => topic);
}

function topicYearDeltas(submissions, limit = 10) {
  const byYear = topicCountsByYear(submissions);
  const years = [...state.data.metadata.years].sort((a, b) => a - b).map(String);
  const deltas = [];

  for (let i = 1; i < years.length; i += 1) {
    const prevYear = years[i - 1];
    const currYear = years[i];
    const prev = byYear.get(prevYear) || new Map();
    const curr = byYear.get(currYear) || new Map();
    const topics = new Set([...prev.keys(), ...curr.keys()]);

    topics.forEach((topic) => {
      if (BLOCKED_TOPICS.has(topic)) return;
      const delta = (curr.get(topic) || 0) - (prev.get(topic) || 0);
      deltas.push({
        topic,
        fromYear: prevYear,
        toYear: currYear,
        delta,
        absDelta: Math.abs(delta),
      });
    });
  }

  return deltas.sort((a, b) => b.absDelta - a.absDelta).slice(0, limit);
}

function truncateLabel(text, max = 28) {
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

function submissionInCluster(submission, clusterName) {
  if (!clusterName || !state.embeddings?.points) return true;
  const point = state.embeddings.points.find(
    (p) =>
      p.id === submission.id ||
      (submission.year === 2026 && String(p.poster_number) === String(submission.poster_number))
  );
  return point?.cluster_name === clusterName;
}

function displaySubmissions() {
  let submissions = filteredSubmissions();
  if (state.selectedCluster) {
    submissions = submissions.filter((item) => submissionInCluster(item, state.selectedCluster));
  }
  return submissions;
}

function setClusterFilter(clusterName) {
  state.selectedCluster = state.selectedCluster === clusterName ? "" : clusterName;
  renderAll();
}

function embeddingPointTooltip(point) {
  const cluster = clusterMeta(point.cluster_name);
  const parts = [
    `<strong>${truncateLabel(point.title, 72)}</strong>`,
    point.poster_number ? `Poster #${point.poster_number} · 2026 pending` : "2026 pending",
    `<strong>Cluster:</strong> ${point.cluster_name}`,
    `${cluster.count} abstracts in this theme`,
  ];
  if (point.primary_area) parts.push(`<strong>Primary area:</strong> ${truncateLabel(point.primary_area, 48)}`);
  if (point.secondary_area) parts.push(`<strong>Secondary:</strong> ${truncateLabel(point.secondary_area, 48)}`);
  parts.push("<em>Click to list all papers in this cluster</em>");
  return parts.join("<br/>");
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
    .map(([area, count]) => `${truncateLabel(area, 36)} (${count})`)
    .join("<br/>");

  const parts = [
    `<strong>${clusterName}</strong>`,
    `${cluster.count} abstracts in cluster`,
  ];
  if (topAreas) parts.push(`<strong>Top areas:</strong><br/>${topAreas}`);
  parts.push("<em>Click to filter submissions</em>");
  return parts.join("<br/>");
}

function renderKpis(filtered) {
  const { metadata, stats } = state.data;
  const cards = [
    { label: "Total submissions", value: metadata.total_count.toLocaleString(), icon: "submissions", tone: "blue" },
    { label: "Matching filter", value: filtered.length.toLocaleString(), icon: "filter", tone: "pink" },
    { label: "Unique keywords", value: stats.overall_top.length.toLocaleString(), icon: "keywords", tone: "green" },
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

function renderKeywordSelect(counts) {
  const select = d3.select("#keyword-select");
  select.selectAll("option:not(:first-child)").remove();
  select
    .selectAll("option.kw")
    .data(counts.slice(0, 100))
    .join("option")
    .attr("class", "kw")
    .attr("value", (d) => d.text)
    .text((d) => `${d.text} (${d.count})`);
  select.property("value", state.selectedKeyword);
}

function renderWordCloud(counts) {
  const container = d3.select("#word-cloud");
  container.selectAll("*").remove();

  const width = container.node().clientWidth || 800;
  const height = 300;
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
  const top = counts.slice(0, 70);

  if (!top.length) {
    svg.append("text").attr("x", 20).attr("y", 40).attr("fill", CCN_COLORS.muted).text("No keywords for current filter.");
    return;
  }

  if (typeof d3.layout === "undefined" || typeof d3.layout.cloud !== "function") {
    svg
      .append("text")
      .attr("x", 20)
      .attr("y", 40)
      .attr("fill", CCN_COLORS.muted)
      .text("Keyword cloud unavailable (d3-cloud failed to load).");
    return;
  }

  const max = d3.max(top, (d) => d.count) || 1;
  const fontSize = (d) => 12 + (d.count / max) * 32;
  const colorScale = d3.scaleOrdinal(CHART_PALETTE);

  d3.layout
    .cloud()
    .size([width, height])
    .words(top.map((d) => ({ text: d.text, size: fontSize(d), count: d.count })))
    .padding(5)
    .rotate(() => (~~(Math.random() * 2) * 90))
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
          d.text === state.selectedKeyword ? CCN_COLORS.pink : colorScale(d.text)
        )
        .style("cursor", "pointer")
        .attr("text-anchor", "middle")
        .attr("transform", (d) => `translate(${d.x},${d.y})rotate(${d.rotate})`)
        .text((d) => d.text)
        .on("click", (_, d) => {
          state.selectedKeyword = state.selectedKeyword === d.text ? "" : d.text;
          d3.select("#keyword-select").property("value", state.selectedKeyword);
          renderAll();
        })
        .on("mousemove", (event, d) => showTooltip(`<strong>${d.text}</strong><br/>${d.count} submissions`, event))
        .on("mouseleave", hideTooltip);
    })
    .start();
}

function renderKeywordBars(counts) {
  const container = d3.select("#keyword-bars");
  container.selectAll("*").remove();

  const width = container.node().clientWidth || 360;
  const height = 340;
  const margin = { top: 8, right: 52, bottom: 8, left: 120 };
  const data = counts.slice(0, 12);

  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
  const innerW = width - margin.left - margin.right;

  const x = d3.scaleLinear().domain([0, d3.max(data, (d) => d.count) || 1]).range([0, innerW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.text))
    .range([0, height - margin.top - margin.bottom])
    .padding(0.18);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  g.selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", 0)
    .attr("y", (d) => y(d.text))
    .attr("height", y.bandwidth())
    .attr("width", (d) => x(d.count))
    .attr("fill", (d, i) =>
      d.text === state.selectedKeyword ? CCN_COLORS.pink : CHART_PALETTE[i % CHART_PALETTE.length]
    )
    .attr("rx", 4)
    .style("cursor", "pointer")
    .on("click", (_, d) => {
      state.selectedKeyword = state.selectedKeyword === d.text ? "" : d.text;
      d3.select("#keyword-select").property("value", state.selectedKeyword);
      renderAll();
    })
    .on("mousemove", (event, d) => showTooltip(`<strong>${d.text}</strong><br/>${d.count}`, event))
    .on("mouseleave", hideTooltip);

  g.selectAll("text.label")
    .data(data)
    .join("text")
    .attr("class", "label")
    .attr("x", -8)
    .attr("y", (d) => y(d.text) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", "end")
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", "10px")
    .text((d) => (d.text.length > 16 ? `${d.text.slice(0, 16)}…` : d.text));

  g.selectAll("text.value")
    .data(data)
    .join("text")
    .attr("class", "value")
    .attr("x", (d) => x(d.count) + 6)
    .attr("y", (d) => y(d.text) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", "10px")
    .text((d) => d.count);
}

function renderYearChart() {
  const container = d3.select("#year-chart");
  container.selectAll("*").remove();

  const counts = Object.entries(state.data.stats.counts_by_year)
    .map(([year, count]) => ({ year: +year, count }))
    .sort((a, b) => a.year - b.year);

  const width = container.node().clientWidth || 640;
  const height = 300;
  const margin = { top: 24, right: 24, bottom: 36, left: 44 };
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);

  const x = d3
    .scalePoint()
    .domain(counts.map((d) => d.year))
    .range([margin.left, width - margin.right]);
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
    .attr("stroke-width", 3)
    .attr("d", line);

  g.selectAll("circle")
    .data(counts)
    .join("circle")
    .attr("cx", (d) => x(d.year))
    .attr("cy", (d) => y(d.count))
    .attr("r", (d) => (String(d.year) === state.selectedYear ? 7 : 5))
    .attr("fill", (d) => (String(d.year) === state.selectedYear ? CCN_COLORS.pink : CCN_COLORS.green))
    .attr("stroke", CCN_COLORS.navy)
    .attr("stroke-width", 2)
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
    .call(d3.axisBottom(x).tickFormat(d3.format("d")))
    .call((sel) => sel.selectAll("text").attr("fill", CCN_COLORS.muted))
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  g.append("g")
    .attr("transform", `translate(${margin.left},0)`)
    .call(d3.axisLeft(y).ticks(5))
    .call((sel) => sel.selectAll("text").attr("fill", CCN_COLORS.muted))
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));
}

function renderTopicChart(submissions) {
  const container = d3.select("#topic-chart");
  container.selectAll("*").remove();

  const data = topicCounts(submissions);
  const width = container.node().clientWidth || 320;
  const height = 280;
  const radius = Math.min(width, height) / 2 - 16;

  if (!data.length) {
    container.append("p").style("color", CCN_COLORS.muted).style("font-size", "0.85rem").text("No topic areas in filter.");
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
    .attr("stroke-width", 2)
    .style("cursor", "pointer")
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
    .style("font-size", "9px")
    .style("font-weight", "600")
    .text((d) => (d.data.count / total > 0.08 ? `${Math.round((d.data.count / total) * 100)}%` : ""));
}

function renderTopicsOverTime(submissions) {
  const container = d3.select("#topics-over-time-chart");
  container.selectAll("*").remove();

  const sub = d3.select("#topics-over-time-sub");
  if (state.googleTopics?.enabled) {
    sub.text("Topic counts by year · Google Form responses");
  } else if (state.googleTopics?.topics?.length) {
    sub.text("Topic counts by year · Google topics configured (assignments pending)");
  } else {
    sub.text("Topic counts by year · token method (Google Form topics when uploaded)");
  }

  const years = [...state.data.metadata.years].sort((a, b) => a - b);
  const topics = topTopicsOverTime(submissions, 8);
  const byYear = topicCountsByYear(submissions);

  const width = container.node().clientWidth || 760;
  const height = 300;
  const margin = { top: 16, right: 16, bottom: 36, left: 44 };

  if (!topics.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("No topic data for current filter.");
    return;
  }

  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const x = d3.scalePoint().domain(years).range([0, innerW]).padding(0.5);
  const y = d3
    .scaleLinear()
    .domain([0, d3.max(topics, (topic) => d3.max(years, (year) => byYear.get(String(year))?.get(topic) || 0)) || 1])
    .nice()
    .range([innerH, 0]);
  const color = d3.scaleOrdinal(CHART_PALETTE).domain(topics);

  const line = d3
    .line()
    .x((d) => x(d.year))
    .y((d) => y(d.count))
    .curve(d3.curveMonotoneX);

  topics.forEach((topic) => {
    const series = years.map((year) => ({
      year,
      count: byYear.get(String(year))?.get(topic) || 0,
      topic,
    }));

    g.append("path")
      .datum(series)
      .attr("fill", "none")
      .attr("stroke", color(topic))
      .attr("stroke-width", 2.5)
      .attr("opacity", 0.9)
      .attr("d", line);

    g.selectAll(`.dot-${topic.replace(/[^a-z0-9]/gi, "")}`)
      .data(series.filter((d) => d.count > 0))
      .join("circle")
      .attr("cx", (d) => x(d.year))
      .attr("cy", (d) => y(d.count))
      .attr("r", 4)
      .attr("fill", color(topic))
      .attr("stroke", CCN_COLORS.navy)
      .attr("stroke-width", 1.5)
      .on("mousemove", (event, d) =>
        showTooltip(`<strong>${truncateLabel(d.topic, 40)}</strong><br/>${d.year}: ${d.count}`, event)
      )
      .on("mouseleave", hideTooltip);
  });

  g.append("g")
    .attr("transform", `translate(0,${innerH})`)
    .call(d3.axisBottom(x).tickFormat(d3.format("d")))
    .call((sel) => sel.selectAll("text").attr("fill", CCN_COLORS.muted))
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  g.append("g")
    .call(d3.axisLeft(y).ticks(5))
    .call((sel) => sel.selectAll("text").attr("fill", CCN_COLORS.muted))
    .call((sel) => sel.selectAll("line, path").attr("stroke", "rgba(197,224,243,0.2)"));

  const legend = svg
    .append("g")
    .attr("transform", `translate(${margin.left}, ${height - 8})`);
  const legendItems = legend
    .selectAll("g")
    .data(topics)
    .join("g")
    .attr("transform", (_, i) => `translate(${i * 118}, 0)`);
  legendItems.append("rect").attr("width", 10).attr("height", 10).attr("rx", 2).attr("fill", (d) => color(d));
  legendItems
    .append("text")
    .attr("x", 14)
    .attr("y", 9)
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", "9px")
    .text((d) => truncateLabel(d, 16));
}

function renderTopicDelta(submissions) {
  const container = d3.select("#topic-delta-chart");
  container.selectAll("*").remove();

  const data = topicYearDeltas(submissions, 10);
  const width = container.node().clientWidth || 360;
  const height = 340;
  const margin = { top: 8, right: 52, bottom: 8, left: 150 };

  if (!data.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("Not enough topic history for deltas.");
    return;
  }

  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
  const innerW = width - margin.left - margin.right;
  const maxAbs = d3.max(data, (d) => d.absDelta) || 1;

  const x = d3.scaleLinear().domain([-maxAbs, maxAbs]).range([0, innerW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.topic))
    .range([0, height - margin.top - margin.bottom])
    .padding(0.2);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  g.append("line")
    .attr("x1", x(0))
    .attr("x2", x(0))
    .attr("y1", 0)
    .attr("y2", height - margin.top - margin.bottom)
    .attr("stroke", "rgba(197,224,243,0.25)");

  g.selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", (d) => (d.delta < 0 ? x(d.delta) : x(0)))
    .attr("y", (d) => y(d.topic))
    .attr("width", (d) => Math.abs(x(d.delta) - x(0)))
    .attr("height", y.bandwidth())
    .attr("fill", (d) => (d.delta >= 0 ? CCN_COLORS.green : CCN_COLORS.pink))
    .attr("rx", 4)
    .on("mousemove", (event, d) =>
      showTooltip(
        `<strong>${truncateLabel(d.topic, 42)}</strong><br/>${d.fromYear}→${d.toYear}: ${d.delta >= 0 ? "+" : ""}${d.delta}`,
        event
      )
    )
    .on("mouseleave", hideTooltip);

  g.selectAll("text.label")
    .data(data)
    .join("text")
    .attr("class", "label")
    .attr("x", -8)
    .attr("y", (d) => y(d.topic) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", "end")
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", "9px")
    .text((d) => truncateLabel(d.topic, 22));
}

function renderClusterBars() {
  const container = d3.select("#cluster-bars-chart");
  container.selectAll("*").remove();

  if (!state.embeddings?.clusters?.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("2026 embedding clusters not loaded.");
    return;
  }

  const data = [...state.embeddings.clusters].sort((a, b) => b.count - a.count);
  const width = container.node().clientWidth || 360;
  const height = 380;
  const margin = { top: 8, right: 36, bottom: 8, left: 132 };
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
  const innerW = width - margin.left - margin.right;

  const x = d3.scaleLinear().domain([0, d3.max(data, (d) => d.count) || 1]).range([0, innerW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.name))
    .range([0, height - margin.top - margin.bottom])
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
    .attr("fill", (d) => (d.name === state.selectedCluster ? CCN_COLORS.pink : color(d.name)))
    .attr("rx", 4)
    .style("cursor", "pointer")
    .on("click", (_, d) => setClusterFilter(d.name))
    .on("mousemove", (event, d) => showTooltip(clusterLegendTooltip(d.name), event))
    .on("mouseleave", hideTooltip);

  g.selectAll("text.label")
    .data(data)
    .join("text")
    .attr("class", "label")
    .attr("x", -8)
    .attr("y", (d) => y(d.name) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", "end")
    .attr("fill", (d) => (d.name === state.selectedCluster ? CCN_COLORS.white : CCN_COLORS.muted))
    .style("font-size", "9px")
    .style("pointer-events", "none")
    .text((d) => truncateLabel(d.name, 20));

  g.selectAll("text.value")
    .data(data)
    .join("text")
    .attr("class", "value")
    .attr("x", (d) => x(d.count) + 6)
    .attr("y", (d) => y(d.name) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", "9px")
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
  const width = container.node().clientWidth || 1100;
  const height = 520;
  const margin = { top: 20, right: 200, bottom: 20, left: 20 };
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);

  const x = d3
    .scaleLinear()
    .domain(d3.extent(state.embeddings.points, (d) => d.x))
    .nice()
    .range([margin.left, width - margin.right]);
  const y = d3
    .scaleLinear()
    .domain(d3.extent(state.embeddings.points, (d) => d.y))
    .nice()
    .range([height - margin.bottom, margin.top]);

  const themes = [...new Set(state.embeddings.points.map((d) => d.cluster_name))];
  const color = d3.scaleOrdinal(CHART_PALETTE).domain(themes);

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", margin.top)
    .attr("width", width - margin.left - margin.right)
    .attr("height", height - margin.top - margin.bottom)
    .attr("fill", "rgba(197,224,243,0.04)")
    .attr("rx", 12);

  svg
    .selectAll("circle")
    .data(points)
    .join("circle")
    .attr("cx", (d) => x(d.x))
    .attr("cy", (d) => y(d.y))
    .attr("r", (d) =>
      state.selectedCluster && d.cluster_name === state.selectedCluster ? 7 : 5.5
    )
    .attr("fill", (d) => color(d.cluster_name))
    .attr("stroke", (d) =>
      state.selectedCluster && d.cluster_name === state.selectedCluster ? CCN_COLORS.pink : CCN_COLORS.navy
    )
    .attr("stroke-width", (d) =>
      state.selectedCluster && d.cluster_name === state.selectedCluster ? 2 : 1
    )
    .attr("opacity", (d) =>
      !state.selectedCluster || d.cluster_name === state.selectedCluster ? 0.9 : 0.18
    )
    .style("cursor", "pointer")
    .on("mousemove", (event, d) => showTooltip(embeddingPointTooltip(d), event))
    .on("mouseleave", hideTooltip)
    .on("click", (_, d) => setClusterFilter(d.cluster_name));

  const legend = svg
    .append("g")
    .attr("transform", `translate(${width - margin.right + 12}, ${margin.top})`);
  const legendItems = legend
    .selectAll("g")
    .data(themes)
    .join("g")
    .attr("transform", (_, i) => `translate(0, ${i * 22})`)
    .style("cursor", "pointer")
    .on("click", (_, theme) => setClusterFilter(theme))
    .on("mousemove", (event, theme) => showTooltip(clusterLegendTooltip(theme), event))
    .on("mouseleave", hideTooltip);

  legendItems
    .append("rect")
    .attr("width", 12)
    .attr("height", 12)
    .attr("rx", 3)
    .attr("fill", (d) => color(d))
    .attr("stroke", (d) => (d === state.selectedCluster ? CCN_COLORS.pink : "transparent"))
    .attr("stroke-width", 2);

  legendItems
    .append("text")
    .attr("x", 18)
    .attr("y", 10)
    .attr("fill", (d) => (d === state.selectedCluster ? CCN_COLORS.white : CCN_COLORS.muted))
    .style("font-size", "10px")
    .text((d) => truncateLabel(d, 24));

  note.text(
    state.selectedCluster
      ? `Showing submissions in “${state.selectedCluster}” (${clusterMeta(state.selectedCluster).count} abstracts) · click again to clear`
      : "Hover for cluster details · click a point or legend to filter matching submissions below."
  );
}

function renderPaperList() {
  const submissions = displaySubmissions();
  const list = d3.select("#paper-list");
  const countEl = d3.select("#results-count");
  countEl.selectAll("*").remove();

  const countLabel = state.selectedCluster
    ? `${submissions.length} submissions in “${state.selectedCluster}”`
    : `${submissions.length} matching submissions`;
  countEl.append("span").text(countLabel);

  if (state.selectedCluster) {
    countEl
      .append("span")
      .attr("class", "cluster-filter-pill")
      .text("Clear cluster filter ×")
      .on("click", () => setClusterFilter(state.selectedCluster));
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
      const point = state.embeddings?.points?.find(
        (p) =>
          p.id === d.id ||
          (d.year === 2026 && String(p.poster_number) === String(d.poster_number))
      );
      const cluster = point?.cluster_name ? ` · ${point.cluster_name}` : "";
      return `${d.year}${d.poster_number ? ` · Poster ${d.poster_number}` : ""}${d.authors ? ` · ${d.authors}` : ""}${d.topic_area ? ` · ${d.topic_area}` : ""}${cluster}`;
    });

  items.each(function renderTags(d) {
    const tags = d3.select(this).append("div").attr("class", "keyword-tags");
    tags
      .selectAll(".keyword-tag")
      .data(d.keywords.slice(0, 10))
      .join("span")
      .attr("class", (kw) => `keyword-tag${kw === state.selectedKeyword ? " active" : ""}`)
      .text((kw) => kw)
      .on("click", (_, kw) => {
        state.selectedKeyword = state.selectedKeyword === kw ? "" : kw;
        d3.select("#keyword-select").property("value", state.selectedKeyword);
        renderAll();
      });
  });
}

function renderAll() {
  const submissions = filteredSubmissions();
  const counts = keywordCounts(submissions);

  renderKpis(submissions);
  renderKeywordSelect(counts);
  renderYearChart();
  renderKeywordBars(counts);
  renderTopicChart(submissions);
  renderWordCloud(counts);
  renderTopicsOverTime(submissions);
  renderTopicDelta(submissions);
  renderClusterBars();
  renderEmbeddingCluster();
  renderPaperList();

  d3.select("#year-chips")
    .selectAll(".year-chip")
    .classed("active", (d) => d === state.selectedYear);
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

  renderYearControls();

  d3.select("#year-select").on("change", (event) => {
    state.selectedYear = event.target.value;
    renderAll();
  });

  d3.select("#search-input").on("input", (event) => {
    state.search = event.target.value;
    renderAll();
  });

  d3.select("#keyword-select").on("change", (event) => {
    state.selectedKeyword = event.target.value;
    renderAll();
  });

  renderAll();
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
