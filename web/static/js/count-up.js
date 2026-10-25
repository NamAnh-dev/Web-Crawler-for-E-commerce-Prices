// Small animation: numbers count up when the page opens.

// <span data-count="149900" data-decimals="0" data-suffix=" ₫"> counts from 0 to 149.900 ₫
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
