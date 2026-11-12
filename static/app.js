// EcomCheck - animations and small interactions.
// This file (like the HTML and CSS) was designed and built with AI (Claude).
// Every number on the page comes from Flask: nothing is computed here.

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const finePointer = window.matchMedia("(pointer: fine)").matches;

// Run `callback` once, the first time `element` scrolls into view.
function onVisible(element, callback, threshold = 0.15) {
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

// ---------- Navigation background + scroll progress bar ----------
const nav = document.getElementById("nav");
const progressBar = document.getElementById("scroll-progress");
function onScroll() {
  nav.classList.toggle("scrolled", window.scrollY > 20);
  const total = document.documentElement.scrollHeight - window.innerHeight;
  progressBar.style.transform = `scaleX(${total > 0 ? window.scrollY / total : 0})`;
}
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

// ---------- Headline: split into words that slide up one by one ----------
document.querySelectorAll("[data-split]").forEach((title) => {
  let index = 0;
  function splitNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      const fragment = document.createDocumentFragment();
      node.textContent.split(/(\s+)/).forEach((part) => {
        if (!part.trim()) {
          fragment.appendChild(document.createTextNode(part));
          return;
        }
        const outer = document.createElement("span");
        outer.className = "w";
        const inner = document.createElement("span");
        inner.textContent = part;
        inner.style.setProperty("--w", index++);
        outer.appendChild(inner);
        fragment.appendChild(outer);
      });
      node.replaceWith(fragment);
    } else {
      Array.from(node.childNodes).forEach(splitNode);
    }
  }
  Array.from(title.childNodes).forEach(splitNode);
  title.classList.add("split-done");
});

// ---------- Reveal on scroll ----------
document.querySelectorAll(".reveal").forEach((element) => {
  onVisible(element, (el) => el.classList.add("in"), 0.1);
});

// ---------- Count-up numbers ----------
document.querySelectorAll("[data-count]").forEach((element) => {
  const target = Number(element.dataset.count);
  const format = element.dataset.format;
  if (reduceMotion) return;
  element.textContent = formatValue(0, format);
  onVisible(element, () => {
    const start = performance.now();
    const duration = 1600;
    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4); // fast at first, slow at the end
      element.textContent = formatValue(target * eased, format);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
});

// ---------- Pointer effects (mouse only) ----------
if (finePointer && !reduceMotion) {
  // a soft light that follows the cursor over the whole page
  const glow = document.getElementById("cursor-glow");
  let glowX = 0, glowY = 0, mouseX = 0, mouseY = 0;
  window.addEventListener("pointermove", (event) => {
    mouseX = event.clientX;
    mouseY = event.clientY;
    glow.classList.add("on");
  });
  (function follow() {
    glowX += (mouseX - glowX) * 0.12;
    glowY += (mouseY - glowY) * 0.12;
    glow.style.transform = `translate(${glowX}px, ${glowY}px)`;
    requestAnimationFrame(follow);
  })();

  // cards: a light under the pointer
  document.querySelectorAll(".spot").forEach((card) => {
    card.addEventListener("pointermove", (event) => {
      const box = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${event.clientX - box.left}px`);
      card.style.setProperty("--my", `${event.clientY - box.top}px`);
    });
  });

  // price tag and product cards: lean towards the pointer
  document.querySelectorAll(".tilt").forEach((card) => {
    card.addEventListener("pointermove", (event) => {
      const box = card.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width - 0.5;
      const y = (event.clientY - box.top) / box.height - 0.5;
      card.style.transition = "transform 0.1s linear";
      card.style.transform = `perspective(900px) rotateY(${x * 14}deg) rotateX(${-y * 14}deg) scale(1.03)`;
    });
    card.addEventListener("pointerleave", () => {
      card.style.transition = "transform 0.7s cubic-bezier(0.2, 0.8, 0.2, 1)";
      card.style.transform = "";
    });
  });

  // main buttons: pulled a little towards the pointer
  document.querySelectorAll(".magnetic").forEach((button) => {
    button.addEventListener("pointermove", (event) => {
      const box = button.getBoundingClientRect();
      const x = event.clientX - box.left - box.width / 2;
      const y = event.clientY - box.top - box.height / 2;
      button.style.transform = `translate(${x * 0.22}px, ${y * 0.3}px)`;
    });
    button.addEventListener("pointerleave", () => { button.style.transform = ""; });
  });
}

// ---------- Search box: example keywords typed in the placeholder ----------
const searchInput = document.querySelector("[data-typewriter]");
if (searchInput && !reduceMotion) {
  const words = searchInput.dataset.typewriter.split("|");
  let word = 0, letter = 0, deleting = false;
  const basePlaceholder = searchInput.placeholder; // "Nhập tên sản phẩm…"
  function type() {
    const text = words[word];
    letter += deleting ? -1 : 1;
    // never show a half-empty "Ví dụ:" - between two words, show the normal hint
    searchInput.placeholder = letter > 0 ? "Ví dụ: " + text.slice(0, letter) : basePlaceholder;
    let wait = deleting ? 35 : 80;
    if (!deleting && letter === text.length) { deleting = true; wait = 1800; }
    if (deleting && letter === 0) { deleting = false; word = (word + 1) % words.length; wait = 1200; }
    setTimeout(type, wait);
  }
  setTimeout(type, 1800); // start after the headline animation
}

// ---------- Home: shop window moves in layers with the pointer (parallax) ----------
// Each piece has a data-depth: the bigger it is, the further it moves.
const showcase = document.getElementById("showcase");
if (showcase && finePointer && !reduceMotion) {
  const layers = Array.from(showcase.querySelectorAll("[data-depth]"));
  let targetX = 0, targetY = 0, x = 0, y = 0;
  document.getElementById("hero").addEventListener("pointermove", (event) => {
    const box = showcase.getBoundingClientRect();
    targetX = (event.clientX - box.left) / box.width - 0.5;
    targetY = (event.clientY - box.top) / box.height - 0.5;
  });
  document.getElementById("hero").addEventListener("pointerleave", () => { targetX = 0; targetY = 0; });
  (function move() {
    x += (targetX - x) * 0.08; // ease towards the pointer
    y += (targetY - y) * 0.08;
    layers.forEach((layer) => {
      const depth = Number(layer.dataset.depth);
      layer.style.transform = `translate3d(${-x * depth}px, ${-y * depth}px, 0)`;
    });
    requestAnimationFrame(move);
  })();
}

// ---------- Click ripple on buttons and chips ----------
document.querySelectorAll(".btn, .chip").forEach((button) => {
  button.addEventListener("pointerdown", (event) => {
    if (reduceMotion) return;
    const box = button.getBoundingClientRect();
    const ripple = document.createElement("span");
    ripple.className = "ripple";
    ripple.style.left = `${event.clientX - box.left}px`;
    ripple.style.top = `${event.clientY - box.top}px`;
    button.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);
  });
});

// ---------- Example chips: fill the search box and submit ----------
const searchForm = document.querySelector("form.search");
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    searchForm.querySelector("input").value = chip.dataset.keyword;
    searchForm.requestSubmit();
  });
});

// ---------- Waiting screen while Flask collects the data ----------
// Only ONE timer at a time: the old version never stopped its timer, so after
// "Back" + a new search two timers wrote into the same place and the number jumped.
const loader = document.getElementById("loader");
const loaderSeconds = document.getElementById("loader-seconds");
const loaderHint = document.getElementById("loader-hint");
let loaderTimer = null;

function stopLoader() {
  clearInterval(loaderTimer);
  loaderTimer = null;
  loader.hidden = true;
}

// 75 -> "1 phút 15 giây"
function formatWait(total) {
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return minutes ? `${minutes} phút ${seconds} giây` : `${seconds} giây`;
}

document.querySelectorAll("form[data-loading]").forEach((form) => {
  form.addEventListener("submit", () => {
    stopLoader();
    loader.hidden = false;
    const keyword = form.querySelector("[name=keyword]").value.trim();
    document.getElementById("loader-keyword").textContent = `“${keyword}”`;
    loaderHint.textContent = "Thường mất khoảng 5–10 giây";
    loaderSeconds.textContent = formatWait(0);
    const start = Date.now();
    loaderTimer = setInterval(() => {
      const waited = Math.floor((Date.now() - start) / 1000);
      loaderSeconds.textContent = formatWait(waited);
      // when Tiki says "too many requests", scraper.py waits 10-20 s and tries again
      if (waited >= 15) loaderHint.textContent = "Tiki đang bận nên phải chờ rồi thử lại, bạn đợi thêm chút nhé";
    }, 250);
  });
});
// "Back" can show the page from the browser cache with the loader still open
window.addEventListener("pageshow", stopLoader);

// ---------- Messages (flash) ----------
document.querySelectorAll(".toast").forEach((toast) => {
  function close() {
    toast.classList.add("hide");
    setTimeout(() => toast.remove(), 400);
  }
  toast.querySelector(".toast-close").addEventListener("click", close);
  setTimeout(close, 8000);
});

// ---------- Home: a moving bar chart behind the hero ----------
// Decoration only: the bars draw the shape of a price distribution (many
// cheap products, a long tail of expensive ones). The peak follows the pointer.
const heroCanvas = document.getElementById("hero-bars");
if (heroCanvas) {
  const ctx = heroCanvas.getContext("2d");
  let width = 0, height = 0, bars = 0, peak = 0.35, target = 0.35, lastMove = 0, visible = true;

  function resize() {
    const box = heroCanvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = box.width;
    height = box.height;
    heroCanvas.width = width * ratio;
    heroCanvas.height = height * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    bars = Math.max(18, Math.floor(width / 22));
  }

  function draw(time) {
    ctx.clearRect(0, 0, width, height);
    if (time - lastMove > 2500) target = 0.35 + 0.18 * Math.sin(time / 3000); // idle: sway
    peak += (target - peak) * 0.05;
    const step = width / bars;
    for (let i = 0; i < bars; i++) {
      const x = i / (bars - 1);
      const bell = Math.exp(-Math.pow((x - peak) / 0.13, 2));
      const tail = 0.38 * Math.exp(-Math.pow((x - peak - 0.28) / 0.3, 2));
      const wave = 0.05 * Math.sin(time / 700 + i * 0.6) + 0.03 * Math.sin(time / 420 + i * 1.7);
      const barHeight = Math.max(0.05, 0.1 + 0.8 * bell + tail + wave) * height * 0.92;
      const gradient = ctx.createLinearGradient(0, height - barHeight, 0, height);
      gradient.addColorStop(0, "rgba(255, 103, 86, 0.85)");
      gradient.addColorStop(0.5, "rgba(255, 176, 72, 0.55)");
      gradient.addColorStop(1, "rgba(255, 197, 51, 0)");
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.roundRect(i * step + 3, height - barHeight, step - 6, barHeight, [6, 6, 0, 0]);
      ctx.fill();
    }
    if (visible && !reduceMotion) requestAnimationFrame(draw);
  }

  window.addEventListener("resize", () => { resize(); if (reduceMotion) draw(0); });
  document.getElementById("hero").addEventListener("pointermove", (event) => {
    target = event.clientX / window.innerWidth;
    lastMove = performance.now();
  });
  new IntersectionObserver((entries) => {
    const wasVisible = visible;
    visible = entries[0].isIntersecting;
    if (visible && !wasVisible && !reduceMotion) requestAnimationFrame(draw);
  }).observe(heroCanvas);
  resize();
  requestAnimationFrame(draw);
}

// ---------- Result page: charts (Chart.js) ----------
const dataTag = document.getElementById("report-data");
if (dataTag && window.Chart) {
  const report = JSON.parse(dataTag.textContent);
  Chart.defaults.color = "#646c8f";
  Chart.defaults.borderColor = "rgba(32, 38, 77, 0.08)";
  Chart.defaults.font.family = "'Be Vietnam Pro', sans-serif";
  Chart.defaults.font.size = 12.5;

  // coral -> yellow fill, along the direction of the bars
  function warmFill(context) {
    const { ctx, chartArea } = context.chart;
    if (!chartArea) return "#ff6756";
    const horizontal = context.chart.options.indexAxis === "y";
    const gradient = horizontal
      ? ctx.createLinearGradient(chartArea.left, 0, chartArea.right, 0)
      : ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
    gradient.addColorStop(0, "#ff6756");
    gradient.addColorStop(1, "#ffc533");
    return gradient;
  }
  const tooltip = {
    backgroundColor: "#1d2242",
    borderWidth: 0,
    padding: 12,
    cornerRadius: 12,
    titleFont: { weight: "600" },
  };
  // bars grow one after the other
  const animation = {
    duration: reduceMotion ? 0 : 1100,
    easing: "easeOutQuart",
    delay: (context) => (context.type === "data" && !reduceMotion ? context.dataIndex * 90 : 0),
  };

  const charts = {
    "chart-ranges": {
      type: "bar",
      data: {
        labels: report.ranges.map((row) => row.label),
        datasets: [
          { label: "% số sản phẩm", data: report.ranges.map((row) => row.product_share), backgroundColor: "rgba(88, 180, 255, 0.6)", borderRadius: 8 },
          { label: "% lượt bán", data: report.ranges.map((row) => row.sold_share), backgroundColor: warmFill, borderRadius: 8 },
        ],
      },
      options: {
        maintainAspectRatio: false,
        animation,
        plugins: {
          legend: { labels: { usePointStyle: true, pointStyle: "rectRounded", padding: 18 } },
          tooltip: {
            ...tooltip,
            callbacks: {
              label(context) {
                const row = report.ranges[context.dataIndex];
                const count = context.datasetIndex === 0
                  ? `${formatNumber(row.products)} sản phẩm`
                  : `${formatNumber(row.sold)} lượt bán`;
                return ` ${context.dataset.label}: ${context.parsed.y}% (${count})`;
              },
            },
          },
        },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: { callback: (value) => value + "%" } },
        },
      },
    },
    "chart-brands": {
      type: "bar",
      data: {
        labels: report.brands.labels,
        datasets: [{ label: "Lượt bán", data: report.brands.sold, backgroundColor: warmFill, borderRadius: 8 }],
      },
      options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        animation,
        plugins: {
          legend: { display: false },
          tooltip: { ...tooltip, callbacks: { label: (context) => ` ${formatNumber(context.parsed.x)} lượt bán` } },
        },
        scales: {
          x: { beginAtZero: true, ticks: { callback: (value) => formatNumber(value) } },
          y: { grid: { display: false } },
        },
      },
    },
  };
  Object.entries(charts).forEach(([id, config]) => {
    const canvas = document.getElementById(id);
    if (canvas) onVisible(canvas, () => new Chart(canvas, config), 0.3);
  });
}

// ---------- Result page: filter and sort the product table ----------
const tbody = document.getElementById("product-rows");
if (tbody) {
  const filterInput = document.getElementById("table-filter");
  const sortSelect = document.getElementById("table-sort");
  const moreButton = document.getElementById("show-more");
  const rowCount = document.getElementById("row-count");
  const rows = Array.from(tbody.rows);
  let shown = 12;

  // "Chuột" -> "chuot", so the filter works with or without accents
  function plain(text) {
    return text.toLowerCase().replace(/đ/g, "d").normalize("NFD").replace(/[̀-ͯ]/g, "");
  }
  const sorters = {
    "sold": (a, b) => b.dataset.sold - a.dataset.sold,
    "price-asc": (a, b) => a.dataset.price - b.dataset.price,
    "price-desc": (a, b) => b.dataset.price - a.dataset.price,
    "rating": (a, b) => b.dataset.rating - a.dataset.rating || b.dataset.sold - a.dataset.sold,
    "discount": (a, b) => b.dataset.discount - a.dataset.discount || b.dataset.sold - a.dataset.sold,
  };

  function update() {
    const query = plain(filterInput.value.trim());
    const matches = rows
      .filter((row) => plain(row.dataset.name).includes(query))
      .sort(sorters[sortSelect.value]);
    rows.forEach((row) => { row.hidden = true; });
    matches.forEach((row, index) => {
      row.hidden = index >= shown;
      tbody.appendChild(row); // moves the row to its new position
    });
    rowCount.textContent = matches.length;
    moreButton.hidden = matches.length <= shown;
  }

  filterInput.addEventListener("input", () => { shown = 12; update(); });
  sortSelect.addEventListener("change", () => { shown = 12; update(); });
  moreButton.addEventListener("click", () => { shown += 24; update(); });
  update();
}
