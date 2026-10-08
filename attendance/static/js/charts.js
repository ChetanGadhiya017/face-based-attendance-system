/* Small Chart.js helpers that follow the light/dark theme. */
(() => {
  const charts = [];
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  function base() {
    Chart.defaults.font.family = "Inter, system-ui, sans-serif";
    Chart.defaults.color = css("--muted");
    Chart.defaults.borderColor = css("--line");
  }
  window.lineChart = (id, labels, values, label, threshold) => {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    const brand = css("--brand");
    charts.push(new Chart(ctx, {
      type: "line",
      data: { labels, datasets: [
        { label, data: values, borderColor: brand, backgroundColor: brand + "22", fill: true, tension: .35, pointRadius: 3 },
        ...(threshold ? [{ label: `Minimum ${threshold}%`, data: labels.map(() => threshold), borderColor: css("--warn"), borderDash: [6, 6], pointRadius: 0, fill: false }] : []),
      ] },
      options: { maintainAspectRatio: false, scales: { y: { min: 0, max: 100, ticks: { callback: (v) => v + "%" } } },
        plugins: { legend: { display: !!threshold, labels: { boxWidth: 12 } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y}%` } } } },
    }));
  };
  window.doughnut = (id, labels, values) => {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    charts.push(new Chart(ctx, {
      type: "doughnut",
      data: { labels, datasets: [{ data: values, backgroundColor: [css("--brand"), css("--warn"), css("--muted")], borderWidth: 0 }] },
      options: { maintainAspectRatio: false, cutout: "68%", plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } } },
    }));
  };
  window.barChart = (id, labels, values, threshold) => {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    charts.push(new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ data: values, borderRadius: 6,
        backgroundColor: values.map((v) => (v < threshold ? css("--warn") : css("--brand"))) }] },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 100, ticks: { callback: (v) => v + "%" } } } },
    }));
  };
  window.drawCharts = (fn) => {
    const run = () => { charts.splice(0).forEach((c) => c.destroy()); base(); fn(); };
    if (window.Chart) run(); else window.addEventListener("load", run);
    window.addEventListener("themechange", run);
  };
})();
