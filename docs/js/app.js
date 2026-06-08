const state = {
  data: null,
  selectedYear: "all",
  search: "",
  selectedKeyword: "",
};

const tooltip = d3.select("#tooltip");

function showTooltip(html, event) {
  tooltip
    .style("opacity", 1)
    .html(html)
    .style("left", `${event.pageX + 12}px`)
    .style("top", `${event.pageY + 12}px`);
}

function hideTooltip() {
  tooltip.style("opacity", 0);
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
    const keywordOk =
      !state.selectedKeyword || item.keywords.includes(state.selectedKeyword);
    return yearOk && searchOk && keywordOk;
  });
}

function keywordCounts(submissions) {
  const counts = new Map();
  submissions.forEach((item) => {
    const unique = [...new Set(item.keywords)];
    unique.forEach((kw) => counts.set(kw, (counts.get(kw) || 0) + 1));
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
    .slice(0, 12);
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

  const nodes = [...nodeSet].map((id) => ({ id }));
  return { nodes, links };
}

function renderStatsBar() {
  const { metadata, stats } = state.data;
  const container = d3.select("#stats-bar");
  const cards = [
    { label: "Total submissions", value: metadata.total_count },
    { label: "Years covered", value: metadata.years.length },
    { label: "Unique keywords", value: stats.overall_top.length },
    { label: "Last updated", value: new Date(metadata.scraped_at).toLocaleDateString() },
  ];

  const card = container.selectAll(".stat-card").data(cards).join("div").attr("class", "stat-card");
  card.selectAll("*").remove();
  card.append("div").attr("class", "label").text((d) => d.label);
  card.append("div").attr("class", "value").text((d) => d.value);
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
    .text((d) => (d === "all" ? "All" : d))
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
  const height = 360;

  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
  const top = counts.slice(0, 80);
  if (!top.length) {
    svg.append("text").attr("x", 20).attr("y", 40).attr("fill", "#9aa8c7").text("No keywords for current filter.");
    return;
  }

  const max = d3.max(top, (d) => d.count) || 1;
  const fontSize = (d) => 12 + (d.count / max) * 34;

  const layout = d3.layout
    .cloud()
    .size([width, height])
    .words(top.map((d) => ({ text: d.text, size: fontSize(d), count: d.count })))
    .padding(4)
    .rotate(() => (~~(Math.random() * 2) * 90))
    .font("Inter")
    .fontSize((d) => d.size)
    .on("end", (words) => {
      const g = svg.append("g").attr("transform", `translate(${width / 2},${height / 2})`);
      g.selectAll("text")
        .data(words)
        .join("text")
        .style("font-size", (d) => `${d.size}px`)
        .style("font-family", "Inter")
        .style("fill", (d) =>
          d.text === state.selectedKeyword ? "#7c5cff" : d3.interpolateTurbo(d.count / max)
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
    });

  layout.start();
}

function renderKeywordBars(counts) {
  const container = d3.select("#keyword-bars");
  container.selectAll("*").remove();

  const width = container.node().clientWidth || 360;
  const height = 420;
  const margin = { top: 10, right: 20, bottom: 10, left: 130 };
  const data = counts.slice(0, 20);

  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`);

  const x = d3
    .scaleLinear()
    .domain([0, d3.max(data, (d) => d.count) || 1])
    .range([0, width - margin.left - margin.right]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.text))
    .range([0, height - margin.top - margin.bottom])
    .padding(0.15);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  g.selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", 0)
    .attr("y", (d) => y(d.text))
    .attr("height", y.bandwidth())
    .attr("width", (d) => x(d.count))
    .attr("fill", (d) => (d.text === state.selectedKeyword ? "#7c5cff" : "#5b8def"))
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
    .attr("fill", "#c7d2ea")
    .style("font-size", "11px")
    .text((d) => (d.text.length > 18 ? `${d.text.slice(0, 18)}…` : d.text));
}

function renderYearChart() {
  const container = d3.select("#year-chart");
  container.selectAll("*").remove();

  const counts = Object.entries(state.data.stats.counts_by_year)
    .map(([year, count]) => ({ year, count }))
    .sort((a, b) => +a.year - +b.year);

  const width = container.node().clientWidth || 500;
  const height = 300;
  const margin = { top: 20, right: 20, bottom: 40, left: 40 };
  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);

  const x = d3
    .scaleBand()
    .domain(counts.map((d) => d.year))
    .range([margin.left, width - margin.right])
    .padding(0.2);
  const y = d3
    .scaleLinear()
    .domain([0, d3.max(counts, (d) => d.count) || 1])
    .nice()
    .range([height - margin.bottom, margin.top]);

  const g = svg.append("g");

  g.selectAll("rect")
    .data(counts)
    .join("rect")
    .attr("x", (d) => x(d.year))
    .attr("y", (d) => y(d.count))
    .attr("width", x.bandwidth())
    .attr("height", (d) => y(0) - y(d.count))
    .attr("fill", (d) => (String(d.year) === state.selectedYear ? "#7c5cff" : "#5b8def"))
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
    .call(d3.axisBottom(x))
    .selectAll("text")
    .attr("fill", "#9aa8c7");

  g.append("g")
    .attr("transform", `translate(${margin.left},0)`)
    .call(d3.axisLeft(y).ticks(5))
    .selectAll("text")
    .attr("fill", "#9aa8c7");
}

function renderTopicChart(submissions) {
  const container = d3.select("#topic-chart");
  container.selectAll("*").remove();

  const data = topicCounts(submissions);
  const width = container.node().clientWidth || 500;
  const height = 300;
  const radius = Math.min(width, height) / 2 - 10;

  if (!data.length) {
    container.append("p").style("color", "#9aa8c7").text("No topic areas in current filter.");
    return;
  }

  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .append("g")
    .attr("transform", `translate(${width / 2},${height / 2})`);

  const color = d3.scaleOrdinal(d3.schemeTableau10);
  const pie = d3.pie().value((d) => d.count);
  const arc = d3.arc().innerRadius(radius * 0.45).outerRadius(radius);

  svg
    .selectAll("path")
    .data(pie(data))
    .join("path")
    .attr("d", arc)
    .attr("fill", (_, i) => color(i))
    .attr("stroke", "#141b2f")
    .style("cursor", "pointer")
    .on("mousemove", (event, d) =>
      showTooltip(`<strong>${d.data.text}</strong><br/>${d.data.count} submissions`, event)
    )
    .on("mouseleave", hideTooltip);

  svg
    .selectAll("text")
    .data(pie(data))
    .join("text")
    .attr("transform", (d) => `translate(${arc.centroid(d)})`)
    .attr("text-anchor", "middle")
    .attr("fill", "#fff")
    .style("font-size", "10px")
    .text((d) => (d.data.count > 8 ? d.data.text.split(" ")[0] : ""));
}

function renderNetwork(submissions) {
  const container = d3.select("#network-chart");
  container.selectAll("*").remove();

  const { nodes, links } = cooccurrenceForSelection(submissions);
  const width = container.node().clientWidth || 1100;
  const height = 420;

  if (!nodes.length) {
    container.append("p").style("color", "#9aa8c7").text("Not enough co-occurrence data for current filter.");
    return;
  }

  const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);

  const simulation = d3
    .forceSimulation(nodes)
    .force(
      "link",
      d3
        .forceLink(links)
        .id((d) => d.id)
        .distance(90)
    )
    .force("charge", d3.forceManyBody().strength(-180))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide(28));

  const link = svg
    .append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "#4d5f90")
    .attr("stroke-opacity", 0.7)
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
    .attr("fill", (d) => (d.id === state.selectedKeyword ? "#7c5cff" : "#5b8def"));

  node
    .append("text")
    .text((d) => (d.id.length > 14 ? `${d.id.slice(0, 14)}…` : d.id))
    .attr("x", 14)
    .attr("y", 4)
    .attr("fill", "#d7e0f5")
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
    .text((d) => `${d.year}${d.poster_number ? ` · Poster ${d.poster_number}` : ""}${d.authors ? ` · ${d.authors}` : ""}${d.topic_area ? ` · ${d.topic_area}` : ""}`);

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
  renderKeywordSelect(counts);
  renderWordCloud(counts);
  renderKeywordBars(counts);
  renderYearChart();
  renderTopicChart(submissions);
  renderNetwork(submissions);
  renderPaperList(submissions);

  d3.select("#year-chips")
    .selectAll(".year-chip")
    .classed("active", (d) => d === state.selectedYear);
}

async function init() {
  const response = await fetch("data/submissions.json");
  state.data = await response.json();

  renderStatsBar();
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

init().catch((error) => {
  console.error(error);
  d3.select("main").append("p").style("color", "#ff8f8f").text(`Failed to load data: ${error.message}`);
});
