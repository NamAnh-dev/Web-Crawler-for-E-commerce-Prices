// Small animations: numbers count up and the search shows the pipeline steps.

// 1. <span data-count="149900" data-decimals="0" data-suffix=" ₫"> counts from 0 to 149.900 ₫
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const formatVi = (value, decimals) =>
  value.toLocaleString("vi-VN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

document.querySelectorAll("[data-count]").forEach((element) => {
  const target = Number(element.dataset.count);
  const decimals = Number(element.dataset.decimals || 0);
  const suffix = element.dataset.suffix || "";
  if (reduceMotion || !Number.isFinite(target)) return;

  const start = performance.now();
  const duration = 900;
  function frame(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // fast start, slow end
    element.textContent = formatVi(target * eased, decimals) + suffix;
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
});

// 2. While the server collects and analyses (5-10 s), light up the pipeline steps one by one.
const searchForm = document.getElementById("search-form");
if (searchForm) {
  searchForm.addEventListener("submit", () => {
    const overlay = document.getElementById("loading");
    const steps = overlay.querySelectorAll("li");
    document.getElementById("loading-keyword").textContent = `“${searchForm.keyword.value.trim()}”`;
    overlay.hidden = false;

    let current = 0;
    steps[0].classList.add("active");
    setInterval(() => {
      if (current === steps.length - 1) return; // the last step waits for the next page
      steps[current].classList.replace("active", "done");
      current += 1;
      steps[current].classList.add("active");
    }, 1800);
  });

  // Coming back with the browser's Back button must not show the old overlay.
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) document.getElementById("loading").hidden = true;
  });
}
