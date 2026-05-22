# -*- coding: utf-8 -*-

"""
Dashboard router — serves a local stats dashboard at /stats.

GET /stats      — HTML dashboard (no auth required)
GET /stats/api  — JSON stats data (no auth required)
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from kiro.stats_tracker import stats_tracker

router = APIRouter(tags=["dashboard"])

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Kiro Gateway — Stats</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0e27 0%, #0d1b3e 40%, #1a0a3e 100%);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    color: #e2e8f0;
    padding: 32px 16px;
  }

  .page-wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 24px;
  }

  h1 {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .subtitle {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-bottom: 28px;
  }

  /* Glass card */
  .card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 20px 24px;
  }

  /* Stat cards grid */
  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
  }

  .stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #7c3aed, #3b82f6);
    border-radius: 16px 16px 0 0;
  }

  .stat-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 1.7rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
    margin-bottom: 4px;
  }

  .stat-sub {
    font-size: 0.72rem;
    color: #64748b;
  }

  /* Chart section */
  .section-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 14px;
  }

  .chart-wrap {
    margin-bottom: 24px;
  }

  #bar-chart {
    width: 100%;
    height: 180px;
    display: flex;
    align-items: flex-end;
    gap: 8px;
    padding: 0 4px;
  }

  .bar-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    justify-content: flex-end;
    gap: 4px;
  }

  .bar-inner {
    width: 100%;
    border-radius: 6px 6px 0 0;
    background: linear-gradient(180deg, #7c3aed 0%, #3b82f6 100%);
    min-height: 2px;
    transition: height 0.4s ease;
    position: relative;
  }

  .bar-inner:hover::after {
    content: attr(data-tip);
    position: absolute;
    bottom: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15,23,42,0.95);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 0.7rem;
    white-space: nowrap;
    color: #e2e8f0;
    pointer-events: none;
    z-index: 10;
  }

  .bar-label {
    font-size: 0.6rem;
    color: #64748b;
    text-align: center;
    white-space: nowrap;
  }

  /* Two-column layout for lower sections */
  .two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }

  @media (max-width: 700px) {
    .two-col { grid-template-columns: 1fr; }
  }

  /* Account table */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
  }

  th {
    text-align: left;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    padding: 6px 8px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }

  td {
    padding: 8px 8px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    color: #cbd5e1;
  }

  tr:last-child td { border-bottom: none; }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }

  .badge-active {
    background: rgba(34,197,94,0.15);
    color: #4ade80;
    border: 1px solid rgba(34,197,94,0.3);
  }

  .badge-cooling {
    background: rgba(234,179,8,0.15);
    color: #facc15;
    border: 1px solid rgba(234,179,8,0.3);
  }

  .badge-warn {
    background: rgba(239,68,68,0.15);
    color: #f87171;
    border: 1px solid rgba(239,68,68,0.3);
  }

  /* Model breakdown */
  .model-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }

  .model-name {
    font-size: 0.75rem;
    color: #cbd5e1;
    min-width: 180px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .model-bar-bg {
    flex: 1;
    height: 8px;
    background: rgba(255,255,255,0.08);
    border-radius: 4px;
    overflow: hidden;
  }

  .model-bar-fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, #7c3aed, #3b82f6);
  }

  .model-pct {
    font-size: 0.7rem;
    color: #94a3b8;
    min-width: 36px;
    text-align: right;
  }

  .refresh-note {
    font-size: 0.68rem;
    color: #475569;
    text-align: right;
    margin-top: 20px;
  }

  .header-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 6px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .refresh-btn {
    background: rgba(124,58,237,0.2);
    border: 1px solid rgba(124,58,237,0.4);
    color: #a78bfa;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .non-claude-warn {
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 8px;
    font-size: 0.75rem;
    color: #fca5a5;
  }

</style>
</head>
<body>
<div class="page-wrap">
<div class="header-row">
  <div>
    <h1>Kiro Gateway</h1>
    <p class="subtitle" id="last-updated">Loading…</p>
  </div>
  <button class="refresh-btn" onclick="refresh()">↻ Refresh</button>
</div>

<div class="cards-grid" id="cards-grid">
  <!-- injected by JS -->
</div>

<div class="card chart-wrap">
  <div class="section-title">Daily Token Usage — Last 7 Days</div>
  <div id="bar-chart"></div>
</div>

<div class="two-col">
  <div class="card">
    <div class="section-title">Account Pool</div>
    <div id="account-table-wrap">—</div>
  </div>
  <div class="card">
    <div class="section-title">Model Breakdown (30 days)</div>
    <div id="model-breakdown">—</div>
  </div>
</div>

<p class="refresh-note">Auto-refreshes every 1 hour · or click Refresh above</p>
</div>

<script>
function fmt(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n);
}

function renderCards(data) {
  const today = data.today;
  const last7 = data.last_7_days;
  const last30 = data.last_30_days;
  const allTime = data.all_time;
  const modelBreakdown = data.model_breakdown;

  const total7 = last7.reduce((s, d) => s + d.input_tokens + d.output_tokens, 0);
  const total30 = last30.reduce((s, d) => s + d.input_tokens + d.output_tokens, 0);
  const avg7 = last7.length ? Math.round(total7 / last7.length) : 0;

  // Top model
  let topModel = '—', topPct = 0;
  const mbEntries = Object.entries(modelBreakdown);
  if (mbEntries.length) {
    const totalMb = mbEntries.reduce((s, [, v]) => s + v, 0);
    mbEntries.sort((a, b) => b[1] - a[1]);
    topModel = mbEntries[0][0];
    topPct = totalMb ? Math.round(mbEntries[0][1] / totalMb * 100) : 0;
  }

  const avgPerReq = allTime.requests
    ? Math.round((allTime.input_tokens + allTime.output_tokens) / allTime.requests)
    : 0;

  const cards = [
    {
      label: 'TODAY',
      value: fmt(today.input_tokens + today.output_tokens),
      sub: `${fmt(today.input_tokens)} in / ${fmt(today.output_tokens)} out`,
    },
    {
      label: 'LAST 7 DAYS',
      value: fmt(total7),
      sub: `avg ${fmt(avg7)} / day`,
    },
    {
      label: 'LAST 30 DAYS',
      value: fmt(total30),
      sub: `${last30.reduce((s,d)=>s+d.requests,0)} requests`,
    },
    {
      label: 'TOP MODEL',
      value: topModel.replace('claude-', '').replace(/-/g, ' ') || '—',
      sub: topPct ? topPct + '% of tokens' : '',
    },
    {
      label: 'TOTAL REQUESTS',
      value: fmt(allTime.requests),
      sub: 'all time',
    },
    {
      label: 'AVG TOKENS / REQ',
      value: fmt(avgPerReq),
      sub: `${fmt(allTime.input_tokens + allTime.output_tokens)} total`,
    },
  ];

  const grid = document.getElementById('cards-grid');
  grid.innerHTML = cards.map(c => `
    <div class="stat-card">
      <div class="stat-label">${c.label}</div>
      <div class="stat-value">${c.value}</div>
      <div class="stat-sub">${c.sub}</div>
    </div>
  `).join('');
}

function renderChart(last7) {
  const chart = document.getElementById('bar-chart');
  const maxVal = Math.max(...last7.map(d => d.input_tokens + d.output_tokens), 1);
  chart.innerHTML = last7.map(d => {
    const total = d.input_tokens + d.output_tokens;
    const pct = Math.max(total / maxVal * 100, total > 0 ? 2 : 0);
    const label = d.date.slice(5); // MM-DD
    const tip = `${d.date}: ${fmt(total)} tokens (${d.requests} req)`;
    return `
      <div class="bar-col">
        <div class="bar-inner" style="height:${pct}%" data-tip="${tip}"></div>
        <div class="bar-label">${label}</div>
      </div>
    `;
  }).join('');
}

function renderAccounts(accounts) {
  const wrap = document.getElementById('account-table-wrap');
  if (!accounts || !accounts.length) {
    wrap.innerHTML = '<p style="color:#475569;font-size:0.75rem">No account data available.</p>';
    return;
  }
  const rows = accounts.map(a => {
    const shortId = a.id.length > 8 ? a.id.slice(-8) : a.id;
    const statusBadge = a.cooling_down
      ? '<span class="badge badge-cooling">Cooling</span>'
      : '<span class="badge badge-active">Active</span>';
    const successRate = a.total_requests
      ? Math.round(a.successful_requests / a.total_requests * 100)
      : 100;
    const failBadge = a.failures > 0
      ? `<span class="badge badge-warn">${a.failures}</span>`
      : `<span style="color:#475569">0</span>`;
    return `<tr>
      <td style="font-family:monospace">${shortId}</td>
      <td>${statusBadge}</td>
      <td>${a.total_requests}</td>
      <td>${successRate}%</td>
      <td>${failBadge}</td>
    </tr>`;
  }).join('');
  wrap.innerHTML = `
    <table>
      <thead><tr>
        <th>Account</th><th>Status</th><th>Reqs</th><th>Success</th><th>Fails</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderModelBreakdown(modelBreakdown) {
  const wrap = document.getElementById('model-breakdown');
  const entries = Object.entries(modelBreakdown).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    wrap.innerHTML = '<p style="color:#475569;font-size:0.75rem">No data yet.</p>';
    return;
  }
  const total = entries.reduce((s, [, v]) => s + v, 0);
  const nonClaude = entries.filter(([k]) => !k.startsWith('claude-'));

  const rows = entries.map(([model, tokens]) => {
    const pct = total ? Math.round(tokens / total * 100) : 0;
    const isNonClaude = !model.startsWith('claude-');
    return `
      <div class="model-row">
        <div class="model-name" style="${isNonClaude ? 'color:#fca5a5' : ''}" title="${model}">${model}</div>
        <div class="model-bar-bg">
          <div class="model-bar-fill" style="width:${pct}%;${isNonClaude ? 'background:linear-gradient(90deg,#dc2626,#f97316)' : ''}"></div>
        </div>
        <div class="model-pct">${pct}%</div>
      </div>
    `;
  }).join('');

  let warn = '';
  if (nonClaude.length) {
    const names = nonClaude.map(([k]) => k).join(', ');
    warn = `<div class="non-claude-warn">Non-Anthropic models detected: ${names}</div>`;
  }

  wrap.innerHTML = rows + warn;
}

async function refresh() {
  try {
    const resp = await fetch('/stats/api');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();

    renderCards(data);
    renderChart(data.last_7_days);
    renderAccounts(data.accounts);
    renderModelBreakdown(data.model_breakdown);

    const now = new Date().toLocaleTimeString();
    document.getElementById('last-updated').textContent = 'Last updated: ' + now;
  } catch (e) {
    document.getElementById('last-updated').textContent = 'Error loading data: ' + e.message;
  }
}

refresh();
setInterval(refresh, 3600000);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/stats", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_html(request: Request) -> HTMLResponse:
    """Serve the stats dashboard HTML page. No auth required."""
    return HTMLResponse(content=_HTML_TEMPLATE)


@router.get("/stats/api", include_in_schema=False)
async def dashboard_api(request: Request) -> JSONResponse:
    """Return raw stats JSON. No auth required."""
    today = stats_tracker.get_today_stats()
    last_7 = stats_tracker.get_last_n_days(7)
    last_30 = stats_tracker.get_last_n_days(30)
    all_time = stats_tracker.get_all_time_totals()
    model_breakdown = stats_tracker.get_model_breakdown(days=30)

    # Account pool info from app.state if available
    accounts: list = []
    account_manager = getattr(getattr(request, "app", None), "state", None)
    if account_manager is not None:
        am = getattr(account_manager, "account_manager", None)
        if am is not None:
            try:
                import time as _time
                for acc_id, acc in am._accounts.items():
                    cooling = False
                    if acc.failures > 0 and acc.last_failure_time > 0:
                        # Simple heuristic: if last failure was recent, consider cooling
                        elapsed = _time.time() - acc.last_failure_time
                        backoff = min(60 * (2 ** (acc.failures - 1)), 86400)
                        cooling = elapsed < backoff
                    accounts.append(
                        {
                            "id": acc_id,
                            "cooling_down": cooling,
                            "failures": acc.failures,
                            "total_requests": acc.stats.total_requests,
                            "successful_requests": acc.stats.successful_requests,
                            "failed_requests": acc.stats.failed_requests,
                        }
                    )
            except Exception:
                pass

    return JSONResponse(
        {
            "today": today,
            "last_7_days": last_7,
            "last_30_days": last_30,
            "all_time": all_time,
            "model_breakdown": model_breakdown,
            "accounts": accounts,
        }
    )
