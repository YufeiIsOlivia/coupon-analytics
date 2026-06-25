#!/usr/bin/env python3
"""
Focused analysis for coupon_partner_dim partners
Output: coupon_partner_report.html
"""

import pandas as pd
import numpy as np
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Partner dimension ──────────────────────────────────────────────────────────
PARTNER_DIM = {
    'RETAILMENOT': 'Public', 'DOTDASH MEREDITH': 'Public', 'NEXTGEN SHOPPING': 'Public',
    'GROUPON': 'Public', 'ATOLLS COUPONS US': 'Public', 'COUPONCABIN': 'Public',
    'CUPONOMIA': 'Public', 'PASSAGEIRA DE PRIMEIRA': 'Public', 'MELHORES DESTINOS': 'Public',
    'VOUCHERCODES': 'Public', 'BRAVO SAVINGS NETWORK': 'Public', 'OBERST': 'Public',
    'URLAUBSTRACKER': 'Public', 'MYVOUCHERCODES': 'Public', 'WIDILO': 'Public',
    'AFILIZA': 'Public', 'LINKPRICE': 'Public', 'VISA JP': 'Public', 'JCB': 'Public',
    'AMERICAN EXPRESS JP': 'Public', 'AEON CARD': 'Public', 'ATOLLS COUPONS UK': 'Public',
    'ATOLLS COUPONS CH': 'Public', 'ATOLLS COUPONS AT': 'Public', 'ATOLLS COUPONS DE': 'Public',
    'ATOLLS COUPONS NORDICS': 'Public', 'ATOLLS COUPONS NL': 'Public', 'ATOLLS COUPONS ES': 'Public',
    'ATOLLS COUPONS IT': 'Public', 'ATOLLS COUPONS LATAM': 'Public', 'ATOLLS COUPONS APAC': 'Public',
    'ATOLLS COUPONS AU': 'Public', 'AEON CARD HK': 'Public', 'CITIBANK ROA': 'Public',
    'DBS BANK ROA': 'Public', 'HANG SENG BANK': 'Public', 'STANDARD CHARTERED BANK ROA': 'Public',
    'CITIBANK SG': 'Public', 'DBS BANK SG': 'Public', 'STANDARD CHARTERED BANK SG': 'Public',
    'UOB BANK': 'Public', 'CATHAY UNITED BANK': 'Public', 'CTBC': 'Public',
    'ESUN BANK': 'Public', 'TAISHIN BANK': 'Public', 'HSBC': 'Public', 'HSBC PREMIER': 'Public',
    'AMERICAN EXPRESS ROA': 'Public', 'MASTERCARD AU': 'Public', 'MASTERCARD ROA': 'Public',
    'VISA HK': 'Public', 'VISA ROA': 'Public', 'VISA AU': 'Public', 'ASIA MILES': 'Public',
    'IDME': 'Private', 'UNIDAYS': 'Private', 'ACROBAT VENTURES': 'Private',
    'BANK OF AMERICA CORP': 'Private', 'STUDENTBEANS': 'Private', 'TOTUM': 'Private',
    'INSPIRINGBENEFITS': 'Private', 'BENIFY': 'Private', 'MECENAT': 'Private',
    'VISMA': 'Private', 'STUDENTKORTET NORWAY': 'Private', 'ADDREAX': 'Private',
    'KEY EXPERIENCE': 'Private', 'SAMSUNG CARD': 'Private', 'KB CARD': 'Private',
    'HYUNDAI CARD': 'Private', 'MITSUI SUMITOMO CARD': 'Private', 'EPOS CARD': 'Private',
    'EDENRED': 'Private', 'CORPORATE BENEFITS': 'Private', 'BLUE LIGHT CARD': 'Private',
    'VC.BENEFITSTATION': 'Private', 'VITALITY UK': 'Uniqodo',
}

TYPE_COLORS = {'Public': '#2563EB', 'Private': '#16A34A', 'Uniqodo': '#D97706'}

# ── Load data ──────────────────────────────────────────────────────────────────
df_all = pd.read_csv(os.path.join(BASE, "coupon order data(raw).csv"), skiprows=3, encoding='latin1')
df_all.columns = df_all.columns.str.strip()
num_cols = ["Gross_orders", "Net_orders", "GBV", "NBV", "GP", "Net_GP"]
for c in num_cols:
    df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)
df_all['yr'] = df_all['yr'].astype(str)
df_all['is_coupon'] = df_all['coupon_indicator'] == 'Coupon Applied'
df_all['partner_upper'] = df_all['partner_name'].str.upper().str.strip()

# Filter to coupon partners only
df = df_all[df_all['partner_upper'].isin(PARTNER_DIM.keys())].copy()
df['coupon_type'] = df['partner_upper'].map(PARTNER_DIM)

# ── Analysis ───────────────────────────────────────────────────────────────────

# 1. KPIs
total_orders = int(df["Gross_orders"].sum())
coupon_orders = int(df[df["is_coupon"]]["Gross_orders"].sum())
coupon_order_pct = coupon_orders / total_orders * 100
total_gbv = df["GBV"].sum()
coupon_gbv = df[df["is_coupon"]]["GBV"].sum()
coupon_gbv_pct = coupon_gbv / total_gbv * 100
total_gp = df["GP"].sum()
coupon_gp = df[df["is_coupon"]]["GP"].sum()
gp_margin_all = total_gp / total_gbv * 100
gp_margin_coupon = coupon_gp / coupon_gbv * 100 if coupon_gbv else 0
gp_margin_no_coupon = (total_gp - coupon_gp) / (total_gbv - coupon_gbv) * 100 if (total_gbv - coupon_gbv) else 0

# Net order rate
nor_coupon = df[df["is_coupon"]]["Net_orders"].sum() / df[df["is_coupon"]]["Gross_orders"].sum() * 100
nor_no_coupon = df[~df["is_coupon"]]["Net_orders"].sum() / df[~df["is_coupon"]]["Gross_orders"].sum() * 100

# 2. By coupon_type
by_type = df.groupby(["coupon_type", "is_coupon"]).agg(
    gross=("Gross_orders", "sum"), net=("Net_orders", "sum"),
    gbv=("GBV", "sum"), gp=("GP", "sum")
).reset_index()
by_type["gp_margin"] = by_type["gp"] / by_type["gbv"].replace(0, np.nan) * 100
by_type["nor"] = by_type["net"] / by_type["gross"].replace(0, np.nan) * 100

type_summary = df.groupby("coupon_type").agg(
    total_gross=("Gross_orders", "sum"), total_gbv=("GBV", "sum"), total_gp=("GP", "sum"),
    coupon_gross=("Gross_orders", lambda x: x[df.loc[x.index, "is_coupon"]].sum()),
    coupon_gbv=("GBV", lambda x: x[df.loc[x.index, "is_coupon"]].sum()),
    coupon_gp=("GP", lambda x: x[df.loc[x.index, "is_coupon"]].sum()),
    coupon_net=("Net_orders", lambda x: x[df.loc[x.index, "is_coupon"]].sum()),
).reset_index()
type_summary["coupon_order_pct"] = type_summary["coupon_gross"] / type_summary["total_gross"].replace(0, np.nan) * 100
type_summary["gp_margin_all"] = type_summary["total_gp"] / type_summary["total_gbv"].replace(0, np.nan) * 100
type_summary["gp_margin_coupon"] = type_summary["coupon_gp"] / type_summary["coupon_gbv"].replace(0, np.nan) * 100
type_summary["nor_coupon"] = type_summary["coupon_net"] / type_summary["coupon_gross"].replace(0, np.nan) * 100
type_summary = type_summary.sort_values("total_gbv", ascending=False)

# 3. YoY by type
yoy_type = df.groupby(["yr", "coupon_type", "is_coupon"]).agg(
    gross=("Gross_orders", "sum"), gbv=("GBV", "sum"), gp=("GP", "sum")
).reset_index()
yoy_type["gp_margin"] = yoy_type["gp"] / yoy_type["gbv"].replace(0, np.nan) * 100

# 4. Partner-level table (coupon orders only, sorted by GBV)
partner_tbl = df[df["is_coupon"]].groupby(["partner_upper", "coupon_type"]).agg(
    coupon_orders=("Gross_orders", "sum"),
    coupon_net=("Net_orders", "sum"),
    coupon_gbv=("GBV", "sum"),
    coupon_gp=("GP", "sum"),
).reset_index()
partner_tbl_all = df.groupby("partner_upper").agg(
    total_gbv=("GBV", "sum"), total_gp=("GP", "sum")
).reset_index()
partner_tbl = partner_tbl.merge(partner_tbl_all, on="partner_upper", how="left")
partner_tbl["gp_margin"] = partner_tbl["coupon_gp"] / partner_tbl["coupon_gbv"].replace(0, np.nan) * 100
partner_tbl["nor"] = partner_tbl["coupon_net"] / partner_tbl["coupon_orders"].replace(0, np.nan) * 100
partner_tbl = partner_tbl.sort_values("coupon_gbv", ascending=False)

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt(n, d=0):
    if n is None or (isinstance(n, float) and np.isnan(n)): return "N/A"
    return f"{n:,.{d}f}"

def pct(n, d=1):
    if n is None or (isinstance(n, float) and np.isnan(n)): return "N/A"
    return f"{n:.{d}f}%"

def jn(lst): return json.dumps([round(float(x), 2) if x == x else 0 for x in lst])

types = ['Public', 'Private', 'Uniqodo']
years = sorted(df['yr'].unique().tolist())

# ── Build HTML ─────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Coupon Partner Deep Dive — 2025–2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#F8FAFC; color:#1E293B; font-size:14px; line-height:1.6; }}
  .header {{ background:#1E293B; color:white; padding:28px 40px; }}
  .header h1 {{ font-size:22px; font-weight:700; }}
  .header p {{ opacity:.7; font-size:13px; margin-top:4px; }}
  .container {{ max-width:1280px; margin:0 auto; padding:24px 40px; }}
  .section {{ margin-bottom:40px; }}
  .section-title {{ font-size:16px; font-weight:700; border-left:4px solid #2563EB; padding-left:10px; margin-bottom:16px; }}
  .section-subtitle {{ font-size:12px; color:#64748B; margin-bottom:14px; margin-top:-10px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:24px; }}
  .kpi-card {{ background:#fff; border:1px solid #E2E8F0; border-radius:10px; padding:16px 18px; }}
  .kpi-label {{ font-size:11px; color:#64748B; text-transform:uppercase; letter-spacing:.5px; }}
  .kpi-value {{ font-size:22px; font-weight:700; margin:4px 0 2px; }}
  .kpi-sub {{ font-size:11px; color:#64748B; }}
  .charts-row {{ display:grid; gap:16px; }}
  .col2 {{ grid-template-columns:1fr 1fr; }}
  .col3 {{ grid-template-columns:1fr 1fr 1fr; }}
  .chart-card {{ background:#fff; border:1px solid #E2E8F0; border-radius:10px; padding:18px; }}
  .chart-card h3 {{ font-size:13px; font-weight:600; margin-bottom:12px; }}
  canvas {{ max-height:280px; }}
  .note {{ font-size:11px; color:#64748B; margin-top:8px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th {{ background:#F8FAFC; color:#64748B; font-weight:600; padding:7px 8px; text-align:left; border-bottom:2px solid #E2E8F0; white-space:nowrap; }}
  td {{ padding:6px 8px; border-bottom:1px solid #E2E8F0; }}
  tr:hover td {{ background:#F1F5F9; }}
  .badge {{ display:inline-block; padding:2px 7px; border-radius:99px; font-size:10px; font-weight:600; }}
  .pub {{ background:#DBEAFE; color:#2563EB; }}
  .priv {{ background:#DCFCE7; color:#16A34A; }}
  .uniq {{ background:#FEF3C7; color:#D97706; }}
  .badge-red {{ background:#FEE2E2; color:#DC2626; }}
  .badge-green {{ background:#DCFCE7; color:#16A34A; }}
  .insight-box {{ background:#EFF6FF; border-left:4px solid #2563EB; border-radius:0 8px 8px 0; padding:12px 16px; margin-bottom:16px; font-size:13px; line-height:1.7; }}
  .insight-box strong {{ color:#2563EB; }}
  .divider {{ border:none; border-top:1px solid #E2E8F0; margin:32px 0; }}
  .toc {{ background:#fff; border:1px solid #E2E8F0; border-radius:10px; padding:16px 20px; margin-bottom:28px; }}
  .toc h2 {{ font-size:13px; font-weight:600; margin-bottom:10px; }}
  .toc ol {{ padding-left:20px; }}
  .toc li {{ margin:4px 0; }}
  .toc a {{ color:#2563EB; text-decoration:none; font-size:13px; }}
</style>
</head>
<body>
<div class="header">
  <h1>Coupon Partner Deep Dive</h1>
  <p>77 partners from <code>insur_analytics.coupon_partner_dim</code> · Public / Private / Uniqodo · 2025–2026</p>
</div>
<div class="container">

<div class="toc">
  <h2>Table of Contents</h2>
  <ol>
    <li><a href="#overview">Overview — 77 Partner KPIs</a></li>
    <li><a href="#bytype">By Coupon Type — Public vs Private vs Uniqodo</a></li>
    <li><a href="#yoy">Year-over-Year Trend by Type</a></li>
    <li><a href="#partners">Partner-Level Table</a></li>
  </ol>
</div>

<!-- ═══ SECTION 1: OVERVIEW ═══ -->
<div class="section" id="overview">
  <div class="section-title">1. Overview — 77 Coupon Partners</div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Total Gross Orders</div>
      <div class="kpi-value">{fmt(total_orders)}</div>
      <div class="kpi-sub">All 77 partners, 2025–2026</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Coupon Order Share</div>
      <div class="kpi-value" style="color:#2563EB">{pct(coupon_order_pct)}</div>
      <div class="kpi-sub">{fmt(coupon_orders)} coupon orders</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Coupon GBV Share</div>
      <div class="kpi-value" style="color:#2563EB">{pct(coupon_gbv_pct)}</div>
      <div class="kpi-sub">${fmt(coupon_gbv/1e6, 1)}M coupon GBV</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">GP Margin — Coupon</div>
      <div class="kpi-value" style="color:{'#DC2626' if gp_margin_coupon < gp_margin_no_coupon else '#16A34A'}">{pct(gp_margin_coupon)}</div>
      <div class="kpi-sub">No Coupon: {pct(gp_margin_no_coupon)} · Overall: {pct(gp_margin_all)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total GBV</div>
      <div class="kpi-value">${fmt(total_gbv/1e6, 1)}M</div>
      <div class="kpi-sub">All orders (coupon + non-coupon)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total GP</div>
      <div class="kpi-value">${fmt(total_gp/1e6, 1)}M</div>
      <div class="kpi-sub">Coupon GP: ${fmt(coupon_gp/1e6, 1)}M</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Net Order Rate — Coupon</div>
      <div class="kpi-value" style="color:#16A34A">{pct(nor_coupon)}</div>
      <div class="kpi-sub">No Coupon: {pct(nor_no_coupon)} · Δ {'+' if nor_coupon > nor_no_coupon else ''}{nor_coupon - nor_no_coupon:.1f}pp</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Partners Tracked</div>
      <div class="kpi-value">77</div>
      <div class="kpi-sub"><span class="badge pub">54 Public</span> <span class="badge priv">22 Private</span> <span class="badge uniq">1 Uniqodo</span></div>
    </div>
  </div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon vs No Coupon — Orders / GBV / GP</h3>
      <canvas id="c_overall"></canvas>
    </div>
    <div class="chart-card">
      <h3>GP Margin: Coupon vs No Coupon vs Overall</h3>
      <canvas id="c_gp_margin"></canvas>
      <p class="note">⚠️ GP Margin = GP / GBV</p>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══ SECTION 2: BY TYPE ═══ -->
<div class="section" id="bytype">
  <div class="section-title">2. By Coupon Type — Public vs Private vs Uniqodo</div>

  <div class="charts-row col3">
    <div class="chart-card">
      <h3>Total GBV by Type ($M)</h3>
      <canvas id="c_type_gbv"></canvas>
    </div>
    <div class="chart-card">
      <h3>Coupon Order Share by Type (%)</h3>
      <canvas id="c_type_coupon_pct"></canvas>
    </div>
    <div class="chart-card">
      <h3>Net Order Rate — Coupon by Type (%)</h3>
      <canvas id="c_type_nor"></canvas>
    </div>
  </div>

  <div style="margin-top:16px" class="charts-row col2">
    <div class="chart-card">
      <h3>GP Margin by Type: Overall vs Coupon (%)</h3>
      <canvas id="c_type_gp"></canvas>
      <p class="note">⚠️ GP Margin = GP / GBV</p>
    </div>
    <div class="chart-card">
      <h3>Type Summary Table</h3>
      <table>
        <thead>
          <tr>
            <th>Type</th><th>Partners</th><th>Total GBV</th><th>Coupon Order%</th>
            <th>GP Margin</th><th>Coupon GP Margin</th><th>GP Δ</th><th>NOR (Coupon)</th>
          </tr>
        </thead>
        <tbody>"""

type_partner_count = {'Public': 54, 'Private': 22, 'Uniqodo': 1}
for _, row in type_summary.iterrows():
    t = row['coupon_type']
    badge = 'pub' if t == 'Public' else 'priv' if t == 'Private' else 'uniq'
    gp_diff = row['gp_margin_coupon'] - row['gp_margin_all']
    gp_diff_class = 'badge-green' if gp_diff >= 0 else 'badge-red'
    html += f"""
          <tr>
            <td><span class="badge {badge}">{t}</span></td>
            <td>{type_partner_count.get(t, '—')}</td>
            <td>${fmt(row['total_gbv']/1e6, 1)}M</td>
            <td>{pct(row['coupon_order_pct'])}</td>
            <td>{pct(row['gp_margin_all'])}</td>
            <td>{pct(row['gp_margin_coupon'])}</td>
            <td><span class="badge {gp_diff_class}">{'+' if gp_diff >= 0 else ''}{gp_diff:.1f}%</span></td>
            <td>{pct(row['nor_coupon'])}</td>
          </tr>"""

html += """
        </tbody>
      </table>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══ SECTION 3: YoY ═══ -->
<div class="section" id="yoy">
  <div class="section-title">3. Year-over-Year Trend by Type</div>
  <div class="section-subtitle">Note: 2026 = Jan–May only</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>GBV by Type & Year ($M)</h3>
      <canvas id="c_yoy_gbv"></canvas>
    </div>
    <div class="chart-card">
      <h3>Coupon GP Margin by Type & Year (%)</h3>
      <canvas id="c_yoy_gp"></canvas>
      <p class="note">⚠️ GP Margin = GP / GBV</p>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══ SECTION 4: PARTNER TABLE ═══ -->
<div class="section" id="partners">
  <div class="section-title">4. Partner-Level Table — Coupon Orders Only</div>
  <div class="section-subtitle">Sorted by Coupon GBV descending · ⚠️ NOR = Net_orders / Gross_orders</div>

  <div class="chart-card">
    <table>
      <thead>
        <tr>
          <th>Partner</th><th>Type</th><th>Coupon Orders</th><th>Coupon GBV</th>
          <th>Coupon GP</th><th>GP Margin</th><th>Net Order Rate</th>
        </tr>
      </thead>
      <tbody>"""

for _, row in partner_tbl.iterrows():
    t = row['coupon_type']
    badge = 'pub' if t == 'Public' else 'priv' if t == 'Private' else 'uniq'
    gp_class = 'badge-red' if row['gp_margin'] < 0 else ''
    html += f"""
        <tr>
          <td>{row['partner_upper']}</td>
          <td><span class="badge {badge}">{t}</span></td>
          <td>{fmt(row['coupon_orders'])}</td>
          <td>${fmt(row['coupon_gbv']/1e3, 0)}K</td>
          <td class="{'color:#DC2626' if row['coupon_gp'] < 0 else ''}">${fmt(row['coupon_gp']/1e3, 1)}K</td>
          <td><span class="{'badge badge-red' if row['gp_margin'] < 0 else ''}">{pct(row['gp_margin'])}</span></td>
          <td>{pct(row['nor'])}</td>
        </tr>"""

html += """
      </tbody>
    </table>
  </div>
</div>

</div><!-- /container -->
<script>
Chart.register(ChartDataLabels);
Chart.defaults.font.family = "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.labels.boxWidth = 12;

const BLUE='#2563EB', GREEN='#16A34A', YELLOW='#D97706', GRAY='#94A3B8', RED='#DC2626';
const TYPE_COLORS = {'Public': BLUE, 'Private': GREEN, 'Uniqodo': YELLOW};

const DL = {
  display: true, anchor:'end', align:'top', offset:2, clamp:false, clip:false,
  font:{size:9,weight:'600'}, color:'#334155',
  formatter: v => v==null||v===0?'':(Math.abs(v)>=1000?(v/1000).toFixed(1)+'K':v.toFixed(1))
};

function bar(id, labels, datasets, opts={}) {
  const ep = opts.plugins||{}; delete opts.plugins;
  new Chart(document.getElementById(id), {
    type:'bar', data:{labels,datasets},
    options:{responsive:true,clip:false,layout:{padding:{top:24}},
      plugins:{legend:{position:'bottom'},datalabels:DL,...ep},
      scales:{y:{beginAtZero:true,grid:{color:'#F1F5F9'}},x:{grid:{display:false}}},
      ...opts}
  });
}
</script>
<script>
"""

# Chart 1: overall
html += f"""
bar('c_overall', ['Gross Orders','GBV ($M)','GP ($M)'], [
  {{label:'Coupon', backgroundColor:BLUE, data:[{coupon_orders},{coupon_gbv/1e6:.2f},{coupon_gp/1e6:.2f}]}},
  {{label:'No Coupon', backgroundColor:GRAY, data:[{total_orders-coupon_orders},{(total_gbv-coupon_gbv)/1e6:.2f},{(total_gp-coupon_gp)/1e6:.2f}]}},
]);

bar('c_gp_margin', ['Coupon','No Coupon','Overall'], [{{
  label:'GP Margin (%)', backgroundColor:[BLUE,GRAY,'#7C3AED'],
  data:[{gp_margin_coupon:.2f},{gp_margin_no_coupon:.2f},{gp_margin_all:.2f}]
}}], {{plugins:{{legend:{{display:false}}}}}});
"""

# Chart 2: by type
t_labels = type_summary["coupon_type"].tolist()
t_gbv = (type_summary["total_gbv"]/1e6).tolist()
t_pct = type_summary["coupon_order_pct"].fillna(0).tolist()
t_nor = type_summary["nor_coupon"].fillna(0).tolist()
t_gp_all = type_summary["gp_margin_all"].fillna(0).tolist()
t_gp_c = type_summary["gp_margin_coupon"].fillna(0).tolist()
t_colors = json.dumps([TYPE_COLORS.get(t, '#94A3B8') for t in t_labels])

html += f"""
bar('c_type_gbv', {json.dumps(t_labels)},
  [{{label:'Total GBV ($M)', backgroundColor:{t_colors}, data:{jn(t_gbv)}}}],
  {{plugins:{{legend:{{display:false}}}}}});

bar('c_type_coupon_pct', {json.dumps(t_labels)},
  [{{label:'Coupon Order Share (%)', backgroundColor:{t_colors}, data:{jn(t_pct)}}}],
  {{plugins:{{legend:{{display:false}}}}}});

bar('c_type_nor', {json.dumps(t_labels)},
  [{{label:'Net Order Rate — Coupon (%)', backgroundColor:{t_colors}, data:{jn(t_nor)}}}],
  {{plugins:{{legend:{{display:false}}}}}});

bar('c_type_gp', {json.dumps(t_labels)},
  [
    {{label:'Overall GP Margin', backgroundColor:GRAY, data:{jn(t_gp_all)}}},
    {{label:'Coupon GP Margin', backgroundColor:BLUE, data:{jn(t_gp_c)}}},
  ]);
"""

# Chart 3: YoY
for yr in years:
    for t in types:
        sub = yoy_type[(yoy_type['yr'] == yr) & (yoy_type['coupon_type'] == t) & (yoy_type['is_coupon'])]

yoy_datasets_gbv = []
yoy_datasets_gp  = []
for t in types:
    color = TYPE_COLORS[t]
    gbv_vals = []
    gp_vals  = []
    for yr in years:
        sub = yoy_type[(yoy_type['yr'] == yr) & (yoy_type['coupon_type'] == t)]
        gbv_vals.append(round(float(sub['gbv'].sum()) / 1e6, 2))
        coupon_sub = sub[sub['is_coupon']]
        cg = coupon_sub['gp'].sum(); cb = coupon_sub['gbv'].sum()
        gp_vals.append(round(float(cg / cb * 100) if cb else 0, 2))
    yoy_datasets_gbv.append(f"{{label:'{t}', backgroundColor:'{color}', data:{json.dumps(gbv_vals)}}}")
    yoy_datasets_gp.append(f"{{label:'{t}', backgroundColor:'{color}', data:{json.dumps(gp_vals)}}}")

html += f"""
bar('c_yoy_gbv', {json.dumps(years)}, [{','.join(yoy_datasets_gbv)}]);
bar('c_yoy_gp',  {json.dumps(years)}, [{','.join(yoy_datasets_gp)}]);
</script></body></html>
"""

out = os.path.join(BASE, "coupon_partner_report.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Report saved: {out}")
print(f"   Partners matched: 77")
print(f"   Total orders: {total_orders:,}")
print(f"   Coupon order share: {coupon_order_pct:.1f}%")
print(f"   GP Margin — Coupon: {gp_margin_coupon:.2f}%  |  No Coupon: {gp_margin_no_coupon:.2f}%")
print(f"   Net Order Rate — Coupon: {nor_coupon:.1f}%  |  No Coupon: {nor_no_coupon:.1f}%")
