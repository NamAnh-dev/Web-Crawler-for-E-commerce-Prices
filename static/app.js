// EcomCheck - animations and small interactions (front-end built with the help of AI).
// Every number shown here comes from the page itself (rendered by Flask).

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Run `callback` once, the first time `element` scrolls into view.
function onVisible(element, callback, threshold = 0.2) {
  if (!("IntersectionObserver" in window)) return callback(element);
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        observer.unobserve(entry.target);
        callback(entry.target);
      }
    });
  }, { threshold });
  observer.observe(element);
}

// ---------- Number formats (same as the Flask filters) ----------
function formatNumber(value) {
  return Math.round(value).toLocaleString("de-DE"); // 1.234.567
}
function formatValue(value, format) {
  return format === "vnd" ? formatNumber(value) + " ₫" : formatNumber(value);
}
function shortPrice(value) {
  if (value >= 1e6) return (value / 1e6).toFixed(1).replace(".0", "") + "Tr";
  return Math.round(value / 1e3) + "K";
}

// ---------- Navigation background after scrolling ----------
const nav = document.getElementById("nav");
function updateNav() { nav.classList.toggle("scrolled", window.scrollY > 20); }
window.addEventListener("scroll", updateNav, { passive: true });
updateNav();

// ---------- Reveal on scroll ----------
document.querySelectorAll(".reveal").forEach((element) => {
  onVisible(element, (el) => el.classList.add("in"), 0.12);
});

// ---------- Count-up numbers ----------
document.querySelectorAll("[data-count]").forEach((element) => {
  const target = Number(element.dataset.count);
  const format = element.dataset.format;
  if (reduceMotion) return;
  element.textContent = formatValue(0, format);
  onVisible(element, () => {
    const start = performance.now();
    const duration = 1400;
    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4); // fast at first, slow at the end
      element.textContent = formatValue(target * eased, format);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
});

// ---------- Mouse light on cards ----------
document.querySelectorAll(".glow").forEach((card) => {
  card.addEventListener("mousemove", (event) => {
    const box = card.getBoundingClientRect();
    card.style.setProperty("--mx", `${event.clientX - box.left}px`);
    card.style.setProperty("--my", `${event.clientY - box.top}px`);
  });
});

// ---------- 3D tilt of the hero preview ----------
const tilt = document.querySelector(".tilt");
if (tilt && !reduceMotion) {
  const area = tilt.parentElement;
  area.addEventListener("mousemove", (event) => {
    const box = area.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    tilt.style.transform = `perspective(900px) rotateY(${x * 16 - 6}deg) rotateX(${-y * 12 + 4}deg)`;
  });
  area.addEventListener("mouseleave", () => { tilt.style.transform = ""; });
}

// ---------- Loading screen while Flask collects the data ----------
const loader = document.getElementById("loader");
document.querySelectorAll("form[data-loading]").forEach((form) => {
  form.addEventListener("submit", () => {
    loader.hidden = false;
    const seconds = document.getElementById("loader-seconds");
    let elapsed = 0;
    setInterval(() => { elapsed += 1; seconds.textContent = elapsed; }, 1000);
  });
});
// Coming back with the browser's Back button: hide it again
window.addEventListener("pageshow", () => { loader.hidden = true; });

// Example keywords: fill the search box and submit
const searchForm = document.querySelector(".search");
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    searchForm.querySelector("input").value = chip.dataset.keyword;
    searchForm.requestSubmit();
  });
});

// ---------- Flash messages ----------
document.querySelectorAll(".toast").forEach((toast) => {
  const close = () => {
    toast.classList.add("hide");
    setTimeout(() => toast.remove(), 400);
  };
  toast.querySelector(".toast-close").addEventListener("click", close);
  setTimeout(close, 7000);
});

// ---------- Price range (log scale, like in the analysis) ----------
const range = document.querySelector(".range");
if (range) {
  const min = Math.log10(Number(range.dataset.min));
  const max = Math.log10(Number(range.dataset.max));
  const position = (value) => (max > min ? (100 * (Math.log10(value) - min)) / (max - min) : 50);

  onVisible(range, () => {
    range.classList.add("in");
    const band = range.querySelector(".range-band");
    const from = position(Number(band.dataset.from));
    const to = position(Number(band.dataset.to));
    band.style.left = `${from}%`;
    band.style.width = `${to - from}%`;
    range.querySelectorAll(".range-marker").forEach((marker) => {
      marker.style.left = `${position(Number(marker.dataset.value))}%`;
    });
  }, 0.4);
}

// ---------- Charts (Chart.js) ----------
const dataTag = document.getElementById("report-data");
if (dataTag && window.Chart) {
  const report = JSON.parse(dataTag.textContent);
  Chart.defaults.font.family = "'Be Vietnam Pro', system-ui, sans-serif";
  Chart.defaults.color = "#5d6380";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.tooltip.backgroundColor = "#0f1222";
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.cornerRadius = 10;

  // Bars appear one after another
  const animation = {
    duration: reduceMotion ? 0 : 1200,
    easing: "easeOutQuart",
    delay: (context) => (context.type === "data" && context.mode === "default" ? context.dataIndex * 90 : 0),
  };
  const grid = { color: "rgba(15, 18, 34, .06)" };

  function gradient(chart, from, to, horizontal = false) {
    const { ctx, chartArea } = chart;
    if (!chartArea) return from;
    const fill = horizontal
      ? ctx.createLinearGradient(chartArea.left, 0, chartArea.right, 0)
      : ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
    fill.addColorStop(0, from);
    fill.addColorStop(1, to);
    return fill;
  }

  function drawWhenVisible(id, config) {
    const canvas = document.getElementById(id);
    if (canvas) onVisible(canvas, () => new Chart(canvas, config), 0.3);
  }

  drawWhenVisible("chart-histogram", {
    type: "bar",
    data: {
      labels: report.histogram.labels,
      datasets: [{
        label: "Số sản phẩm",
        data: report.histogram.counts,
        backgroundColor: (context) => gradient(context.chart, "rgba(99, 102, 241, .55)", "#8b5cf6"),
        hoverBackgroundColor: "#06b6d4",
        borderRadius: 8,
        borderSkipped: false,
      }],
    },
    options: {
      maintainAspectRatio: false,
      animation,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { display: false } }, y: { grid, beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  const segmentNames = { budget: "Giá rẻ", mid: "Tầm trung", premium: "Cao cấp" };
  drawWhenVisible("chart-segments", {
    type: "bar",
    data: {
      labels: report.segments.map((s) => segmentNames[s.segment]),
      datasets: [
        { label: "% số sản phẩm", data: report.segments.map((s) => s.listing_share), backgroundColor: "#c7cbe0", borderRadius: 8 },
        {
          label: "% lượt bán",
          data: report.segments.map((s) => s.sold_share),
          backgroundColor: (context) => gradient(context.chart, "rgba(6, 182, 212, .6)", "#6366f1"),
          borderRadius: 8,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      animation,
      plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y.toFixed(0)}%` } } },
      scales: {
        x: { grid: { display: false } },
        y: { grid, beginAtZero: true, max: 100, ticks: { callback: (v) => `${v}%` } },
      },
    },
  });

  drawWhenVisible("chart-brands", {
    type: "bar",
    data: {
      labels: report.brands.labels,
      datasets: [{
        label: "Lượt bán",
        data: report.brands.sold,
        backgroundColor: (context) => gradient(context.chart, "rgba(139, 92, 246, .5)", "#06b6d4", true),
        borderRadius: 8,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      animation,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${formatNumber(c.parsed.x)} lượt bán` } } },
      scales: { x: { grid, beginAtZero: true, ticks: { callback: (v) => formatNumber(v) } }, y: { grid: { display: false } } },
    },
  });
}

// ---------- Product table: filter, sort, "show more" ----------
const tbody = document.getElementById("product-rows");
if (tbody) {
  const rows = Array.from(tbody.rows);
  const filterInput = document.getElementById("table-filter");
  const sortSelect = document.getElementById("table-sort");
  const moreButton = document.getElementById("show-more");
  const rowCount = document.getElementById("row-count");
  const PAGE = 15;
  let shown = PAGE;

  // "Chuột" -> "chuot", so a filter without accents still matches
  const plain = (text) => text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
  rows.forEach((row) => { row.dataset.name = plain(row.querySelector(".cell-name").textContent); });

  const sorters = {
    sold: (a, b) => b.dataset.sold - a.dataset.sold,
    "price-asc": (a, b) => a.dataset.price - b.dataset.price,
    "price-desc": (a, b) => b.dataset.price - a.dataset.price,
    rating: (a, b) => b.dataset.rating - a.dataset.rating || b.dataset.sold - a.dataset.sold,
    discount: (a, b) => b.dataset.discount - a.dataset.discount,
  };

  // Show the first `shown` matching rows; rows from `animateFrom` on fade in one by one
  function render(animateFrom = 0) {
    const query = plain(filterInput.value.trim());
    const matching = rows.filter((row) => row.dataset.name.includes(query));
    matching.sort(sorters[sortSelect.value]);

    rows.forEach((row) => { row.hidden = true; row.classList.remove("row-in"); });
    void tbody.offsetWidth; // let the browser forget the old animation so it can play again
    matching.forEach((row, index) => {
      tbody.appendChild(row); // moves the row to its new place
      if (index < shown) {
        row.hidden = false;
        if (index >= animateFrom) {
          row.style.setProperty("--row", index - animateFrom);
          row.classList.add("row-in");
        }
      }
    });
    rowCount.textContent = matching.length;
    moreButton.parentElement.hidden = matching.length <= shown;
  }

  filterInput.addEventListener("input", () => { shown = PAGE; render(); });
  sortSelect.addEventListener("change", () => { shown = PAGE; render(); });
  moreButton.addEventListener("click", () => { shown += PAGE; render(shown - PAGE); });
  render();
}
