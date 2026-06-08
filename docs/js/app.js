const CCN_COLORS = {
  navy: "#1a3b5d",
  pink: "#f4c7c3",
  blue: "#c5e0f3",
  green: "#c8e6c9",
  white: "#f7fafc",
  muted: "#8fa8c4",
  card: "#162d47",
};

const CHART_PALETTE = [CCN_COLORS.pink, CCN_COLORS.blue, CCN_COLORS.green, "#9ecae1", "#fdae9f", "#a8ddb5"];

const state = {
  data: null,
  selectedYear: "all",
  search: "",
  selectedKeyword: "",
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

function cooccurrenceForSelection(submissions) {
  const pairCounts = new Map();
  submissions.forEach((item) => {
    const kws = [...new Set(item.keywords)].slice(0, 8);
    for (let i = 0; i < kws.length; i += 1) {
      for (let j = i + 1; j < kws.length; j += 1) {
        const a = kws[i];
        const b = kws[j];
        const key = a < b ? `${a}|||${b}` : `${b}|||${a}`;
        pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
      }
    }
  });

  const links = [...pairCounts.entries()]
    .map(([key, count]) => {
      const [source, target] = key.split("|||");
      return { source, target, count };
    })
    .filter((d) => d.count >= 2)
    .sort((a, b) => b.count - a.count)
    .slice(0, 80);

  const nodeSet = new Set();
  links.forEach((l) => {
    nodeSet.add(l.source);
    nodeSet.add(l.target);
  });

  return { nodes: [...nodeSet].map((id) => ({ id })), links };
}

function renderKpis(filtered) {
  const { metadata, stats } = state.data;
  const cards = [
    { label: "Total submissions", value: metadata.total_count.toLocaleString(), icon: "📊", tone: "blue" },
    { label: "Matching filter", value: filtered.length.toLocaleString(), icon: "🔍", tone: "pink" },
    { label: "Unique keywords", value: stats.overall_top.length.toLocaleString(), icon: "🏷", tone: "green" },
    { label: "Years covered", value: String(metadata.years.length), icon: "📅", tone: "navy" },
  ];

  const row = d3.select("#kpi-row");
  const card = row.selectAll(".kpi-card").data(cards).join("div").attr("class", "kpi-card");
  card.selectAll("*").remove();
  card
    .append("div")
    .attr("class", (d) => `kpi-icon ${d.tone}`)
    .text((d) => d.icon);
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

function renderGauge(filtered) {
  const container = d3.select("#gauge-chart");
  container.selectAll("*").remove();

  const total = state.data.metadata.total_count;
  const value = filtered.length;
  const pct = total ? value / total : 0;

  const width = container.node().clientWidth || 320;
  const height = 260;
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);

  const cx = width / 2;
  const cy = height * 0.62;
  const radius = Math.min(width, height) * 0.34;

  const arc = d3
    .arc()
    .innerRadius(radius * 0.68)
    .outerRadius(radius)
    .startAngle(-Math.PI / 2)
    .cornerRadius(6);

  svg
    .append("path")
    .attr("transform", `translate(${cx},${cy})`)
    .attr("d", arc({ endAngle: Math.PI / 2 }))
    .attr("fill", "rgba(197,224,243,0.12)");

  svg
    .append("path")
    .attr("transform", `translate(${cx},${cy})`)
    .attr("d", arc({ endAngle: -Math.PI / 2 + Math.PI * pct }))
    .attr("fill", CCN_COLORS.pink);

  svg
    .append("text")
    .attr("x", cx)
    .attr("y", cy - 4)
    .attr("text-anchor", "middle")
    .attr("fill", CCN_COLORS.white)
    .style("font-size", "28px")
    .style("font-weight", "700")
    .text(`${Math.round(pct * 100)}%`);

  svg
    .append("text")
    .attr("x", cx)
    .attr("y", cy + 20)
    .attr("text-anchor", "middle")
    .attr("fill", CCN_COLORS.muted)
    .style("font-size", "12px")
    .text(`${value.toLocaleString()} of ${total.toLocaleString()}`);
}

function renderNetwork(submissions) {
  const container = d3.select("#network-chart");
  container.selectAll("*").remove();

  const { nodes, links } = cooccurrenceForSelection(submissions);
  const width = container.node().clientWidth || 1100;
  const height = 360;

  if (!nodes.length) {
    container.append("p").style("color", CCN_COLORS.muted).text("Not enough co-occurrence data for current filter.");
    return;
  }

  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
  const color = d3.scaleOrdinal(CHART_PALETTE);

  const simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance(90))
    .force("charge", d3.forceManyBody().strength(-180))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide(28));

  const link = svg
    .append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "rgba(197,224,243,0.35)")
    .attr("stroke-width", (d) => Math.sqrt(d.count));

  const node = svg
    .append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .style("cursor", "pointer")
    .call(
      d3
        .drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    )
    .on("click", (_, d) => {
      state.selectedKeyword = state.selectedKeyword === d.id ? "" : d.id;
      d3.select("#keyword-select").property("value", state.selectedKeyword);
      renderAll();
    });

  node
    .append("circle")
    .attr("r", 12)
    .attr("fill", (d) => (d.id === state.selectedKeyword ? CCN_COLORS.pink : color(d.id)));

  node
    .append("text")
    .text((d) => (d.id.length > 14 ? `${d.id.slice(0, 14)}…` : d.id))
    .attr("x", 14)
    .attr("y", 4)
    .attr("fill", CCN_COLORS.white)
    .style("font-size", "10px");

  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);
    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
}

function renderPaperList(submissions) {
  const list = d3.select("#paper-list");
  d3.select("#results-count").text(`${submissions.length} matching submissions`);

  const items = list.selectAll(".paper-item").data(submissions.slice(0, 80)).join("div").attr("class", "paper-item");
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
      `${d.year}${d.poster_number ? ` · Poster ${d.poster_number}` : ""}${d.authors ? ` · ${d.authors}` : ""}${d.topic_area ? ` · ${d.topic_area}` : ""}`
    );

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
  renderGauge(submissions);
  renderWordCloud(counts);
  renderNetwork(submissions);
  renderPaperList(submissions);

  d3.select("#year-chips")
    .selectAll(".year-chip")
    .classed("active", (d) => d === state.selectedYear);
}

async function init() {
  ensureD3();

  const response = await fetch("data/submissions.json");
  if (!response.ok) {
    throw new Error(`Could not load data/submissions.json (${response.status})`);
  }
  state.data = await response.json();

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
