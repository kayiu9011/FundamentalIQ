const $ = (selector) => document.querySelector(selector);
const state = { symbol: null, criteria: null, defaults: null };

const thresholdMeta = {
  return_on_equity_min: ["Minimum ROE", "%", "Profit relative to shareholders’ equity"],
  return_on_assets_min: ["Minimum ROA", "%", "Profit relative to total assets"],
  profit_margin_min: ["Minimum net margin", "%", "Net income as a share of revenue"],
  operating_margin_min: ["Minimum operating margin", "%", "Operating income as a share of revenue"],
  price_earnings_min_exclusive: ["P/E lower bound (exclusive)", "×", "Must remain below the maximum"],
  price_earnings_max: ["Maximum P/E", "×", "Price relative to earnings per share"],
  debt_to_equity_max: ["Maximum debt / equity", "×", "Normalized debt relative to equity"],
  current_ratio_min: ["Minimum current ratio", "×", "Current assets relative to current liabilities"],
  quarterly_revenue_growth_min_exclusive: ["Quarterly revenue growth above", "%", "Provider-reported quarterly growth"],
  operating_cash_flow_min_exclusive: ["Operating cash flow above", "currency", "Positive operating cash generation"],
  levered_free_cash_flow_min_exclusive: ["Levered free cash flow above", "currency", "Cash after debt-related obligations"]
};
const percentKeys = new Set(["return_on_equity_min", "return_on_assets_min", "profit_margin_min", "operating_margin_min", "quarterly_revenue_growth_min_exclusive"]);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;", '"':"&quot;"}[char]));
}
function setVisible(element, visible) { element.classList.toggle("hidden", !visible); }
function showAlert(message, tone = "error") {
  const alert = $("#alert");
  alert.textContent = message;
  alert.className = `mt-6 rounded-xl border px-4 py-3 text-sm ${tone === "error" ? "border-rose-400/30 bg-rose-400/5 text-rose-200" : "border-amber-400/30 bg-amber-400/5 text-amber-100"}`;
}
function clearAlert() { setVisible($("#alert"), false); }
function formatNumber(value, maximumFractionDigits = 1) {
  return value == null ? "Not available" : new Intl.NumberFormat("en-US", { maximumFractionDigits }).format(value);
}
function compact(value, currency = "USD") {
  if (value == null) return "Not available";
  return new Intl.NumberFormat("en-US", { notation: "compact", style: "currency", currency, maximumFractionDigits: 1 }).format(value);
}
function metricValue(metric, currency) {
  if (metric.actual_value == null) return "Not available";
  if (metric.unit === "percent") return `${formatNumber(metric.actual_value * 100, 1)}%`;
  if (metric.unit === "currency") return compact(metric.actual_value, currency);
  return `${formatNumber(metric.actual_value, 2)}×`;
}
async function api(url, options) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.error || payload.detail || {};
    throw new Error(typeof detail === "string" ? detail : detail.message || payload.message || `Request failed (${response.status})`);
  }
  return payload;
}

async function initialize() {
  try {
    const [config, catalog] = await Promise.all([api("/api/config/status"), api("/api/screening/criteria")]);
    const badge = $("#modeBadge");
    const mockMode = config.provider_mode === "mock";
    badge.textContent = mockMode ? "● Illustrative mock data" : config.live_provider_ready ? "● Financial Modeling Prep configured" : "● Financial Modeling Prep needs API key";
    badge.className = `badge ${mockMode ? "bg-amber-400/10 text-amber-300" : config.live_provider_ready ? "bg-emerald-400/10 text-emerald-300" : "bg-rose-400/10 text-rose-300"}`;
    setVisible($("#fixtureHelp"), mockMode);
    $("#ticker").placeholder = mockMode ? "Try NOVA" : "Try AAPL";
    $("#tickerHelp").textContent = mockMode ? "Choose a fictional fixture or enter its ticker." : "Enter a ticker supported by Financial Modeling Prep.";
    $("#emptyTitle").textContent = mockMode ? "Start with an illustrative company" : "Search for a company";
    $("#emptyMessage").textContent = mockMode
      ? "Choose a fixture above to see the complete workflow. Sample companies are fictional and clearly labeled."
      : "Enter a ticker above to retrieve and screen its latest available fundamentals.";
    state.defaults = catalog.ruleset;
    const saved = localStorage.getItem("fundamentaliq-ruleset");
    try { state.criteria = saved ? JSON.parse(saved) : structuredClone(state.defaults); }
    catch { localStorage.removeItem("fundamentaliq-ruleset"); state.criteria = structuredClone(state.defaults); }
    renderCriteria();
  } catch (error) { showAlert(`Application configuration could not be loaded: ${error.message}`); }
}

function renderCriteria() {
  if (!state.criteria) return;
  $("#criteriaFields").innerHTML = Object.entries(thresholdMeta).map(([key, [label, unit, help]]) => {
    const raw = state.criteria.thresholds[key];
    const shown = percentKeys.has(key) ? raw * 100 : raw;
    return `<label class="metric"><span class="block text-sm font-semibold text-white">${escapeHtml(label)}</span><span class="mt-1 block text-xs text-slate-500">${escapeHtml(help)} · ${escapeHtml(unit)}</span><input class="input mt-3" name="${key}" type="number" required step="any" value="${shown}"></label>`;
  }).join("");
}

function renderCompany(company) {
  $("#companyName").textContent = company.long_name || company.symbol;
  $("#companySymbol").textContent = company.symbol;
  $("#companyContext").textContent = [company.sector, company.industry, company.exchange].filter(Boolean).join(" · ") || "Company context not available";
  $("#companyPrice").textContent = company.price == null ? "Not available" : new Intl.NumberFormat("en-US", { style: "currency", currency: company.currency || "USD" }).format(company.price);
  const overview = [["Market cap", compact(company.market_cap, company.currency || "USD")], ["Revenue", compact(company.revenue, company.currency || "USD")], ["Shares outstanding", company.shares_outstanding == null ? "Not available" : formatNumber(company.shares_outstanding / 1e6, 1) + "M"]];
  $("#overviewMetrics").innerHTML = overview.map(([label, value]) => `<div class="metric"><p class="label">${label}</p><p class="mt-1 font-bold text-white">${escapeHtml(value)}</p></div>`).join("");
  const periods = [company.last_fiscal_quarter_end && `Fiscal quarter: ${new Date(company.last_fiscal_quarter_end).toLocaleDateString()}`, company.last_fiscal_year_end && `Fiscal year: ${new Date(company.last_fiscal_year_end).toLocaleDateString()}`].filter(Boolean);
  $("#reportingPeriod").textContent = `${company.is_mock ? "Illustrative data — not a real issuer. " : "Provider snapshot. "}${periods.join(" · ") || "Reporting period unavailable"}`;
}

function renderScreening(company, screening) {
  $("#score").textContent = screening.score == null ? "—" : formatNumber(screening.score, 1);
  $("#classification").textContent = screening.classification;
  $("#assessment").textContent = screening.overall_assessment;
  $("#coverage").textContent = `Weighted data coverage ${formatNumber(screening.data_coverage, 1)}%`;
  const ringScore = screening.score || 0;
  $("#scoreRing").style.background = `conic-gradient(#55d6be ${ringScore * 3.6}deg, #21324a 0)`;
  $("#counts").innerHTML = `<span class="badge status-PASS">${screening.passing_checks} passed</span><span class="badge status-FAIL">${screening.failing_checks} failed</span><span class="badge status-NA">${screening.unavailable_checks} unavailable</span>`;
  const warnings = screening.applicability_warnings || [];
  setVisible($("#warnings"), warnings.length > 0);
  $("#warnings").innerHTML = warnings.map(item => `<p>⚠ ${escapeHtml(item)}</p>`).join("");
  const categories = { profitability: "Profitability", valuation: "Valuation", financial_stability: "Financial stability", growth: "Growth", cash_flow: "Cash flow" };
  $("#categoryCards").innerHTML = Object.entries(categories).map(([key, label]) => {
    const metrics = screening.metrics.filter(metric => metric.category === key);
    const pass = metrics.filter(metric => metric.status === "PASS").length;
    const fail = metrics.filter(metric => metric.status === "FAIL").length;
    const na = metrics.filter(metric => metric.status === "N/A").length;
    const color = fail ? "text-amber-300" : pass ? "text-emerald-300" : "text-slate-400";
    return `<article class="card p-5"><p class="label">${escapeHtml(label)}</p><p class="mt-3 text-2xl font-black ${color}">${pass}<span class="text-sm font-medium text-slate-500"> / ${metrics.length} pass</span></p><p class="mt-2 text-xs text-slate-500">${fail} fail · ${na} unavailable</p></article>`;
  }).join("");
  $("#metricsTable").innerHTML = screening.metrics.map(metric => `<tr class="align-top"><td class="px-5 py-4"><p class="font-semibold text-white">${escapeHtml(metric.metric_name)}</p><p class="mt-1 max-w-xs text-xs text-slate-500">${escapeHtml(metric.measures)}</p></td><td class="px-5 py-4 font-mono text-slate-200">${escapeHtml(metricValue(metric, company.currency || "USD"))}</td><td class="px-5 py-4 text-slate-300">${escapeHtml(metric.threshold)}</td><td class="px-5 py-4"><span class="badge status-${metric.status.replace("/", "")}">${metric.status}</span></td><td class="max-w-xl px-5 py-4 text-slate-400"><p>${escapeHtml(metric.explanation)}</p><details class="mt-2 text-xs"><summary class="cursor-pointer text-cyan">Context & limitations</summary><p class="mt-2">Why it matters: ${escapeHtml(metric.investor_relevance)} ${escapeHtml(metric.limitations)}</p></details></td></tr>`).join("");
  const list = (selector, items, empty) => { $(selector).innerHTML = (items.length ? items : [empty]).map(item => `<li class="flex gap-2"><span class="text-slate-600">—</span><span>${escapeHtml(item)}</span></li>`).join(""); };
  list("#strengths", screening.strengths, "No weighted checks passed in the available data.");
  list("#concerns", screening.concerns, "No failed checks were identified, though further research is still necessary.");
}

async function analyze(symbol, custom = false) {
  const clean = symbol.trim().toUpperCase();
  if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(clean)) { showAlert("Enter a valid ticker: 1–10 letters, numbers, periods, or hyphens, beginning with a letter."); return; }
  clearAlert(); setVisible($("#empty"), false); setVisible($("#results"), false); setVisible($("#loading"), true); $("#analyzeButton").disabled = true;
  try {
    const options = custom ? { method: "POST", body: JSON.stringify(state.criteria) } : undefined;
    const payload = await api(`/api/stocks/${encodeURIComponent(clean)}/screen`, options);
    state.symbol = clean;
    state.criteria = payload.screening.ruleset;
    renderCompany(payload.company); renderScreening(payload.company, payload.screening); renderCriteria();
    setVisible($("#results"), true);
  } catch (error) { showAlert(error.message); setVisible($("#empty"), true); }
  finally { setVisible($("#loading"), false); $("#analyzeButton").disabled = false; }
}

$("#searchForm").addEventListener("submit", event => { event.preventDefault(); analyze($("#ticker").value); });
$("#suggestions").addEventListener("click", event => { const symbol = event.target.dataset.symbol; if (symbol) { $("#ticker").value = symbol; analyze(symbol); } });
$("#criteriaForm").addEventListener("submit", event => {
  event.preventDefault();
  if (!state.symbol) return;
  const values = new FormData(event.currentTarget);
  for (const key of Object.keys(thresholdMeta)) {
    let value = Number(values.get(key));
    if (!Number.isFinite(value)) { showAlert(`Invalid value for ${thresholdMeta[key][0]}`); return; }
    if (percentKeys.has(key)) value /= 100;
    state.criteria.thresholds[key] = value;
  }
  localStorage.setItem("fundamentaliq-ruleset", JSON.stringify(state.criteria));
  analyze(state.symbol, true);
});
$("#restoreDefaults").addEventListener("click", () => { state.criteria = structuredClone(state.defaults); localStorage.removeItem("fundamentaliq-ruleset"); renderCriteria(); if (state.symbol) analyze(state.symbol, true); });

initialize();
