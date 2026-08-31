// dashboard.js
// Drives the whole single-page dashboard: upload (drag/drop + click),
// empty vs. data view switching, filters, charts, table, export.

const state = { region: "all", category: "all", startDate: "", endDate: "" };
let trendChart, regionChart, productChart;

const fmtMoney = (n) => "\u20B9" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
const fmtNum = (n) => Number(n).toLocaleString("en-IN");

const emptyState = document.getElementById("emptyState");
const dataView = document.getElementById("dataView");

function buildQuery() {
  const params = new URLSearchParams();
  if (state.region !== "all") params.set("region", state.region);
  if (state.category !== "all") params.set("category", state.category);
  if (state.startDate) params.set("start_date", state.startDate);
  if (state.endDate) params.set("end_date", state.endDate);
  return params.toString();
}

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function showView(hasData) {
  emptyState.classList.toggle("hidden", hasData);
  dataView.classList.toggle("hidden", !hasData);
}

// ---------- Upload (shared by both dropzone and toolbar "add more") ----------

async function uploadFile(file, statusEl) {
  if (!file) return;
  if (statusEl) { statusEl.textContent = "Uploading..."; statusEl.className = statusEl.className.replace(/ (ok|err)/, ""); }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const data = await fetchJSON("/api/upload", { method: "POST", body: formData });
    if (statusEl) { statusEl.textContent = data.message; statusEl.classList.add("ok"); }
    await enterDataView();
  } catch (err) {
    if (statusEl) { statusEl.textContent = err.message; statusEl.classList.add("err"); }
    else showEmptyError(err.message);
  }
}

function showEmptyError(msg) {
  const el = document.getElementById("emptyError");
  el.textContent = msg;
  el.classList.remove("hidden");
}

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileInputToolbar = document.getElementById("fileInputToolbar");

dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => uploadFile(fileInput.files[0], null));

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("drag-over"); })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("drag-over"); })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file, null);
});

document.getElementById("sampleBtn").addEventListener("click", async () => {
  try {
    await fetchJSON("/api/load-sample", { method: "POST" });
    await enterDataView();
  } catch (err) {
    showEmptyError(err.message);
  }
});

document.getElementById("addMoreBtn").addEventListener("click", () => fileInputToolbar.click());
fileInputToolbar.addEventListener("change", () =>
  uploadFile(fileInputToolbar.files[0], document.getElementById("uploadStatus"))
);

document.getElementById("resetBtn").addEventListener("click", async () => {
  if (!confirm("Clear all uploaded data? This can't be undone.")) return;
  await fetchJSON("/api/reset", { method: "POST" });
  showView(false);
  document.getElementById("emptyError").classList.add("hidden");
  document.getElementById("lastUpdated").textContent = "";
});

// ---------- Filters ----------

document.getElementById("regionFilter").addEventListener("change", (e) => { state.region = e.target.value; refreshAll(); });
document.getElementById("categoryFilter").addEventListener("change", (e) => { state.category = e.target.value; refreshAll(); });
document.getElementById("startDate").addEventListener("change", (e) => { state.startDate = e.target.value; refreshAll(); });
document.getElementById("endDate").addEventListener("change", (e) => { state.endDate = e.target.value; refreshAll(); });
document.getElementById("exportBtn").addEventListener("click", () => { window.location.href = "/api/export?" + buildQuery(); });

async function loadFilterOptions() {
  const data = await fetchJSON("/api/filters");
  const regionSel = document.getElementById("regionFilter");
  const catSel = document.getElementById("categoryFilter");
  regionSel.innerHTML = '<option value="all">All regions</option>' + data.regions.map((r) => `<option value="${r}">${r}</option>`).join("");
  catSel.innerHTML = '<option value="all">All categories</option>' + data.categories.map((c) => `<option value="${c}">${c}</option>`).join("");
  return data.has_data;
}

// ---------- KPIs ----------

function animateValue(el, from, to, formatter, duration = 550) {
  const start = performance.now();
  const isReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (isReduced) { el.textContent = formatter(to); return; }
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = from + (to - from) * eased;
    el.textContent = formatter(current);
    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = formatter(to);
  }
  requestAnimationFrame(tick);
}

const prevKPI = { total_revenue: 0, total_units: 0, total_orders: 0, avg_order_value: 0 };

async function loadKPIs() {
  const data = await fetchJSON("/api/kpis?" + buildQuery());
  animateValue(document.getElementById("kpiRevenue"), prevKPI.total_revenue, data.total_revenue, fmtMoney);
  animateValue(document.getElementById("kpiUnits"), prevKPI.total_units, data.total_units, fmtNum);
  animateValue(document.getElementById("kpiOrders"), prevKPI.total_orders, data.total_orders, fmtNum);
  animateValue(document.getElementById("kpiAOV"), prevKPI.avg_order_value, data.avg_order_value, fmtMoney);
  Object.assign(prevKPI, data);
}

// ---------- Charts ----------

Chart.defaults.font.family = "Inter, sans-serif";
Chart.defaults.color = "#8a93a3";

const regionPalette = ["#c9a24b", "#3fb27f", "#6c9bd1", "#b97fd1", "#e2636e", "#8a93a3"];

async function loadTrendChart() {
  const data = await fetchJSON("/api/revenue-trend?" + buildQuery());
  const ctx = document.getElementById("trendChart");
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((d) => d.order_date),
      datasets: [{
        data: data.map((d) => d.revenue),
        borderColor: "#c9a24b",
        backgroundColor: "rgba(201,162,75,0.10)",
        fill: true,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 4,
        borderWidth: 1.75,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#565d6b", maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }, grid: { display: false }, border: { color: "#242a35" } },
        y: { ticks: { color: "#565d6b" }, grid: { color: "#1a1f28" }, border: { display: false } },
      },
    },
  });
}

async function loadRegionChart() {
  const data = await fetchJSON("/api/region-breakdown?" + buildQuery());
  const ctx = document.getElementById("regionChart");
  if (regionChart) regionChart.destroy();
  regionChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.map((d) => d.region),
      datasets: [{ data: data.map((d) => d.revenue), backgroundColor: regionPalette, borderColor: "#12151c", borderWidth: 2 }],
    },
    options: {
      responsive: true,
      cutout: "68%",
      plugins: { legend: { position: "bottom", labels: { color: "#8a93a3", boxWidth: 10, padding: 14, font: { size: 11 } } } },
    },
  });
}

async function loadProductChart() {
  const data = await fetchJSON("/api/top-products?" + buildQuery());
  const ctx = document.getElementById("productChart");
  if (productChart) productChart.destroy();
  productChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => d.product),
      datasets: [{ data: data.map((d) => d.revenue), backgroundColor: "#c9a24b", borderRadius: 2, maxBarThickness: 16 }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#565d6b" }, grid: { color: "#1a1f28" }, border: { display: false } },
        y: { ticks: { color: "#8a93a3" }, grid: { display: false }, border: { display: false } },
      },
    },
  });
}

// ---------- Table ----------

async function loadTable() {
  const data = await fetchJSON("/api/table?" + buildQuery());
  const wrap = document.getElementById("tableWrap");
  if (!data.length) {
    wrap.innerHTML = '<div class="table-empty">No orders match these filters.</div>';
    return;
  }
  const rows = data.slice(0, 40).map((r) => `
    <tr>
      <td>${r.order_date}</td>
      <td>${r.region}</td>
      <td>${r.product}</td>
      <td>${r.quantity}</td>
      <td>${fmtMoney(r.revenue)}</td>
    </tr>`).join("");
  wrap.innerHTML = `
    <table>
      <thead><tr><th>Date</th><th>Region</th><th>Product</th><th>Qty</th><th>Revenue</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ---------- Orchestration ----------

async function refreshAll() {
  await Promise.all([loadKPIs(), loadTrendChart(), loadRegionChart(), loadProductChart(), loadTable()]);
}

async function enterDataView() {
  showView(true);
  await loadFilterOptions();
  await refreshAll();
  document.getElementById("lastUpdated").textContent = "Updated " + new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

(async function init() {
  const hasData = await loadFilterOptions();
  if (hasData) {
    await enterDataView();
  } else {
    showView(false);
  }
})();
