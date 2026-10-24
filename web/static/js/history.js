// Reference prices over time on the history page.
// Data comes from the <script id="history-data"> tag rendered by Flask.

const snapshots = JSON.parse(document.getElementById("history-data").textContent);
const css = getComputedStyle(document.documentElement);
const token = (name) => css.getPropertyValue(name).trim();

// "2026-10-24 08:00:05" -> "24/10 08:00"
const label = (text) => `${text.slice(8, 10)}/${text.slice(5, 7)} ${text.slice(11, 16)}`;
const compactVnd = (value) =>
  value >= 1_000_000 ? `${(value / 1_000_000).toFixed(1).replace(".0", "").replace(".", ",")}Tr` : `${Math.round(value / 1000)}K`;
const series = (key) => snapshots.map((s) => s[key]);

new Chart(document.getElementById("history-chart"), {
  type: "line",
  data: {
    labels: snapshots.map((s) => label(s.created_at)),
    datasets: [
      // Q3 is filled down to Q1 ("+1" = the next dataset): the common price range
      { label: "Q3", data: series("q3"), borderWidth: 0, pointRadius: 0, fill: "+1",
        backgroundColor: token("--accent") + "26" },
      { label: "Q1", data: series("q1"), borderWidth: 0, pointRadius: 0, fill: false },
      { label: "Giá trung vị", data: series("median"), borderColor: token("--accent"), borderWidth: 2,
        pointRadius: 4, pointBackgroundColor: token("--accent"), pointBorderColor: token("--surface"), pointBorderWidth: 2 },
      { label: "Giá sàn", data: series("floor"), borderColor: token("--ink-2"), borderWidth: 1.5, pointRadius: 0 },
    ],
  },
  options: {
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: token("--surface"),
        titleColor: token("--ink-2"),
        bodyColor: token("--ink"),
        borderColor: token("--border"),
        borderWidth: 1,
        padding: 10,
        callbacks: { label: (item) => `${item.dataset.label}: ${compactVnd(item.raw)}` },
      },
    },
    scales: {
      x: { grid: { display: false }, border: { color: token("--axis") }, ticks: { color: token("--ink-2"), font: { size: 11 } } },
      y: {
        grid: { color: token("--grid") },
        border: { display: false },
        ticks: { color: token("--ink-2"), font: { size: 11 }, callback: (value) => compactVnd(value) },
      },
    },
  },
});
