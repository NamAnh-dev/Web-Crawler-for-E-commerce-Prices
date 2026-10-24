// Price distribution chart on the dashboard page.
// Data comes from the <script id="chart-data"> tag rendered by Flask.

const { histogram, band } = JSON.parse(document.getElementById("chart-data").textContent);
const css = getComputedStyle(document.documentElement);
const token = (name) => css.getPropertyValue(name).trim();

// 85000 -> "85K", 1500000 -> "1,5Tr" (same format as the Python filter)
function compactVnd(value) {
  if (value >= 1_000_000) {
    return (value / 1_000_000).toFixed(1).replace(".0", "").replace(".", ",") + "Tr";
  }
  return Math.round(value / 1000) + "K";
}

const edges = histogram.edges;
const labels = histogram.counts.map((_, i) => `${compactVnd(edges[i])}–${compactVnd(edges[i + 1])}`);
const counts = [...histogram.counts];
const centers = histogram.counts.map((_, i) => (edges[i] + edges[i + 1]) / 2);

if (histogram.tail > 0) {  // long tail of expensive products in one last bar
  labels.push(`≥ ${compactVnd(edges[edges.length - 1])}`);
  counts.push(histogram.tail);
  centers.push(Infinity);
}

// Highlight bins whose centre is inside the common price range (Q1–Q3).
const colors = centers.map((c) => (c >= band.q1 && c <= band.q3 ? token("--accent") : token("--muted-bar")));

new Chart(document.getElementById("price-chart"), {
  type: "bar",
  data: {
    labels,
    datasets: [{
      data: counts,
      backgroundColor: colors,
      hoverBackgroundColor: colors,
      borderRadius: { topLeft: 4, topRight: 4 },
      borderSkipped: "bottom",
      categoryPercentage: 0.92,
      barPercentage: 1,
    }],
  },
  options: {
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: token("--surface"),
        titleColor: token("--ink-2"),
        bodyColor: token("--ink"),
        borderColor: token("--border"),
        borderWidth: 1,
        padding: 10,
        displayColors: false,
        titleFont: { weight: "500" },
        bodyFont: { weight: "600", size: 14 },
        callbacks: {
          title: (items) => `Giá ${items[0].label}`,
          label: (item) => `${item.raw} sản phẩm`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { color: token("--axis") },
        ticks: { color: token("--ink-2"), font: { size: 11 }, maxRotation: 0, autoSkip: true, autoSkipPadding: 12 },
      },
      y: {
        beginAtZero: true,
        grid: { color: token("--grid") },
        border: { display: false },
        ticks: { color: token("--ink-2"), font: { size: 11 }, precision: 0 },
      },
    },
  },
});
