#!/usr/bin/env python3
"""
Coupon Data Analysis Report Generator
Inputs:
  - coupon order data(raw).csv
  - coupon metric.csv
Output:
  - coupon_report.html
"""

import pandas as pd
import numpy as np
import json
import os

# ── 1. Load Data ─────────────────────────────────────────────────────────────

BASE = os.path.dirname(os.path.abspath(__file__))

# Order data: skip first 3 metadata rows
df_order = pd.read_csv(
    os.path.join(BASE, "coupon order data(raw).csv"),
    skiprows=3,
    encoding="latin1",
)
df_order.columns = df_order.columns.str.strip()
# Drop trailing empty column if present
df_order = df_order.loc[:, ~df_order.columns.str.startswith("Unnamed")]
# Coerce numeric columns
num_cols = ["Gross_orders", "Net_orders", "GBV", "NBV", "GP", "Net_GP"]
for c in num_cols:
    df_order[c] = pd.to_numeric(df_order[c], errors="coerce").fillna(0)

df_order["yr"] = df_order["yr"].astype(str)
df_order["is_coupon"] = df_order["coupon_indicator"] == "Coupon Applied"

# ── Coupon Metric: hierarchical pivot table ───────────────────────────────────
df_m_raw = pd.read_csv(
    os.path.join(BASE, "coupon metric.csv"),
    encoding="latin1",
    header=0,
)
df_m_raw.columns = ["partner_name", "n_coupon_card", "app_rate_str", "success_rate_str", "failure_rate_str"]

KNOWN_SEGMENTS = {
    "Content creators", "Shopping marketplace", "Financial institutions",
    "Non Endemic Companies", "Technology", "Travel suppliers",
}
SKIP = {"Grand Total", "nan", "UNMAPPED PARTNER"}

def pct_to_float(s):
    if isinstance(s, float) and np.isnan(s):
        return np.nan
    s = str(s).strip()
    if s in ("#DIV/0!", "", "nan"):
        return np.nan
    return float(s.replace("%", "")) / 100

# Assign industry_segment to each partner row
metric_rows = []
current_segment = None
for _, row in df_m_raw.iterrows():
    name = str(row["partner_name"]).strip()
    if name in KNOWN_SEGMENTS:
        current_segment = name
        continue
    if name in SKIP or name == "nan":
        continue
    metric_rows.append({
        "industry_segment": current_segment,
        "partner_name": name,
        "n_coupon_card": pd.to_numeric(row["n_coupon_card"], errors="coerce"),
        "app_rate": pct_to_float(row["app_rate_str"]),
        "success_rate": pct_to_float(row["success_rate_str"]),
        "failure_rate": pct_to_float(row["failure_rate_str"]),
    })

df_metric = pd.DataFrame(metric_rows)
df_metric = df_metric[df_metric["industry_segment"].notna()]

# Segment-level summary from raw file
seg_summary_raw = {}
for _, row in df_m_raw.iterrows():
    name = str(row["partner_name"]).strip()
    if name in KNOWN_SEGMENTS:
        seg_summary_raw[name] = {
            "n_coupon_card": pd.to_numeric(row["n_coupon_card"], errors="coerce"),
            "app_rate": pct_to_float(row["app_rate_str"]),
            "success_rate": pct_to_float(row["success_rate_str"]),
            "failure_rate": pct_to_float(row["failure_rate_str"]),
        }

# ── 2. Analysis ───────────────────────────────────────────────────────────────

# 2.1 Overall Coupon vs Non-Coupon
overall = df_order.groupby("is_coupon")[num_cols].sum().reset_index()
overall["label"] = overall["is_coupon"].map({True: "Coupon Applied", False: "No Coupon"})
overall["gp_margin"] = overall["GP"] / overall["GBV"].replace(0, np.nan)
overall["net_order_rate"] = overall["Net_orders"] / overall["Gross_orders"].replace(0, np.nan)
overall["nbv_gbv_ratio"] = overall["NBV"] / overall["GBV"].replace(0, np.nan)

# 2.2 Year-over-Year trend
yoy = df_order.groupby(["yr", "is_coupon"])[num_cols].sum().reset_index()
yoy["label"] = yoy["is_coupon"].map({True: "Coupon Applied", False: "No Coupon"})

# Coupon penetration by year
yr_total = df_order.groupby("yr")[["Gross_orders", "GBV", "GP"]].sum()
yr_coupon = df_order[df_order["is_coupon"]].groupby("yr")[["Gross_orders", "GBV", "GP"]].sum()
yr_pen = (yr_coupon / yr_total * 100).reset_index()
yr_pen.columns = ["yr", "order_pct", "gbv_pct", "gp_pct"]

# 2.3 Industry Segment breakdown
seg = df_order.groupby(["industry_segment", "is_coupon"])[num_cols].sum().reset_index()
seg_total = df_order.groupby("industry_segment")[["Gross_orders", "GBV", "GP"]].sum().reset_index()
seg_total.columns = ["industry_segment", "total_orders", "total_gbv", "total_gp"]
seg_coupon = df_order[df_order["is_coupon"]].groupby("industry_segment")[["Gross_orders", "GBV", "GP"]].sum().reset_index()
seg_coupon.columns = ["industry_segment", "coupon_orders", "coupon_gbv", "coupon_gp"]
seg_pen = seg_total.merge(seg_coupon, on="industry_segment", how="left").fillna(0)
seg_pen["coupon_order_pct"] = seg_pen["coupon_orders"] / seg_pen["total_orders"].replace(0, np.nan) * 100
seg_pen["coupon_gbv_pct"] = seg_pen["coupon_gbv"] / seg_pen["total_gbv"].replace(0, np.nan) * 100
seg_pen["gp_margin_all"] = df_order.groupby("industry_segment")["GP"].sum().values / \
    df_order.groupby("industry_segment")["GBV"].sum().values * 100
seg_pen["gp_margin_coupon"] = df_order[df_order["is_coupon"]].groupby("industry_segment")["GP"].sum().reindex(
    seg_pen["industry_segment"]).fillna(0).values / \
    df_order[df_order["is_coupon"]].groupby("industry_segment")["GBV"].sum().reindex(
    seg_pen["industry_segment"]).fillna(0).replace(0, np.nan).values * 100
seg_pen = seg_pen.sort_values("total_gbv", ascending=False)

# Merge Net Order Rate delta into seg_pen
seg_cancel_delta = df_order.groupby(["industry_segment", "is_coupon"]).agg(
    gross=("Gross_orders", "sum"), net=("Net_orders", "sum")
).reset_index()
seg_cancel_delta["net_rate"] = seg_cancel_delta["net"] / seg_cancel_delta["gross"].replace(0, np.nan) * 100
seg_cancel_pivot = seg_cancel_delta.pivot(index="industry_segment", columns="is_coupon", values="net_rate").reset_index()
seg_cancel_pivot.columns = ["industry_segment", "nr_no_coupon", "nr_coupon"]
seg_cancel_pivot["nr_delta"] = seg_cancel_pivot["nr_coupon"] - seg_cancel_pivot["nr_no_coupon"]
seg_pen = seg_pen.merge(seg_cancel_pivot[["industry_segment", "nr_coupon", "nr_no_coupon", "nr_delta"]], on="industry_segment", how="left")

# 2.4 Device type analysis
device = df_order.groupby(["cbe_purchase_device_type", "is_coupon"])[["Gross_orders", "GBV", "GP"]].sum().reset_index()
device_pivot = device.pivot_table(index="cbe_purchase_device_type", columns="is_coupon",
                                   values=["Gross_orders", "GBV", "GP"], aggfunc="sum").fillna(0)
device_pivot.columns = ["_".join([str(c) for c in col]) for col in device_pivot.columns]
device_pivot = device_pivot.reset_index()
device_pivot["coupon_pct"] = device_pivot.get("Gross_orders_True", 0) / \
    (device_pivot.get("Gross_orders_True", 0) + device_pivot.get("Gross_orders_False", 0)).replace(0, np.nan) * 100

# 2.5 Payment type
pay = df_order.groupby(["payment_type", "is_coupon"])[["Gross_orders", "GBV", "GP"]].sum().reset_index()

# 2.6 Refundable
refund = df_order.groupby(["refundable_indicator", "is_coupon"])[["Gross_orders", "Net_orders", "GBV", "GP"]].sum().reset_index()
refund["net_rate"] = refund["Net_orders"] / refund["Gross_orders"].replace(0, np.nan) * 100

# 2.7 GP impact analysis
gp_compare = df_order.groupby("is_coupon").apply(lambda x: pd.Series({
    "GP_margin": x["GP"].sum() / x["GBV"].sum() * 100 if x["GBV"].sum() else 0,
    "Net_order_rate": x["Net_orders"].sum() / x["Gross_orders"].sum() * 100 if x["Gross_orders"].sum() else 0,
    "NBV_GBV_ratio": x["NBV"].sum() / x["GBV"].sum() * 100 if x["GBV"].sum() else 0,
    "Avg_GBV_per_order": x["GBV"].sum() / x["Gross_orders"].sum() if x["Gross_orders"].sum() else 0,
}), include_groups=False).reset_index()
gp_compare["label"] = gp_compare["is_coupon"].map({True: "Coupon Applied", False: "No Coupon"})

# 2.8 Coupon Metric: segment summary
seg_metric = pd.DataFrame([
    {"industry_segment": k, **v} for k, v in seg_summary_raw.items()
]).dropna(subset=["n_coupon_card"])
seg_metric = seg_metric.sort_values("n_coupon_card", ascending=False)

# 2.9 Cancellation / Net Order Rate analysis
cancel = df_order.groupby("is_coupon").agg(
    gross=("Gross_orders", "sum"),
    net=("Net_orders", "sum"),
).reset_index()
cancel["net_rate"] = cancel["net"] / cancel["gross"] * 100
cancel["cancel_rate"] = 100 - cancel["net_rate"]
cancel["label"] = cancel["is_coupon"].map({True: "Coupon Applied", False: "No Coupon"})

nr_coupon_overall   = float(cancel.loc[cancel["is_coupon"]==True,  "net_rate"].values[0])
nr_nocoupon_overall = float(cancel.loc[cancel["is_coupon"]==False, "net_rate"].values[0])

seg_cancel = df_order.groupby(["industry_segment", "is_coupon"]).agg(
    gross=("Gross_orders", "sum"), net=("Net_orders", "sum")
).reset_index()
seg_cancel["net_rate"] = seg_cancel["net"] / seg_cancel["gross"].replace(0, np.nan) * 100
seg_pivot = seg_cancel.pivot(index="industry_segment", columns="is_coupon", values="net_rate").reset_index()
seg_pivot.columns = ["industry_segment", "net_rate_no_coupon", "net_rate_coupon"]
seg_pivot["delta"] = seg_pivot["net_rate_coupon"] - seg_pivot["net_rate_no_coupon"]
seg_pivot = seg_pivot.dropna(subset=["net_rate_coupon", "net_rate_no_coupon"])
seg_pivot_sorted = seg_pivot.sort_values("delta", ascending=False)

# 2.10 Partner-level: top coupon users from metric
top_partners_metric = df_metric[df_metric["n_coupon_card"] > 0].sort_values("n_coupon_card", ascending=False).head(30)

# 2.10 Cross join: partner financial performance vs coupon metrics
order_partner = df_order.groupby("partner_name").agg(
    total_orders=("Gross_orders", "sum"),
    coupon_orders=("Gross_orders", lambda x: x[df_order.loc[x.index, "is_coupon"]].sum()),
    total_gbv=("GBV", "sum"),
    coupon_gbv=("GBV", lambda x: x[df_order.loc[x.index, "is_coupon"]].sum()),
    total_gp=("GP", "sum"),
    coupon_gp=("GP", lambda x: x[df_order.loc[x.index, "is_coupon"]].sum()),
).reset_index()
order_partner["gp_margin"] = order_partner["total_gp"] / order_partner["total_gbv"].replace(0, np.nan) * 100
order_partner["coupon_penetration"] = order_partner["coupon_orders"] / order_partner["total_orders"].replace(0, np.nan) * 100

merged = order_partner.merge(
    df_metric[["partner_name", "n_coupon_card", "app_rate", "success_rate", "failure_rate", "industry_segment"]],
    on="partner_name", how="inner"
)
merged = merged[merged["n_coupon_card"] > 0]

# Quadrant: high GBV + high failure rate
merged["is_high_failure"] = merged["failure_rate"] > 0.6
merged["is_high_gbv"] = merged["total_gbv"] > merged["total_gbv"].quantile(0.75)
quadrant = merged[merged["is_high_failure"] & merged["is_high_gbv"]].sort_values("total_gbv", ascending=False).head(20)

# Top performers: high GBV + high success rate
top_performers = merged[merged["success_rate"] > 0.5].sort_values("total_gbv", ascending=False).head(20)

# Negative GP with coupon
neg_gp_coupon = df_order[df_order["is_coupon"] & (df_order["GP"] < 0)].groupby("partner_name").agg(
    coupon_orders=("Gross_orders", "sum"),
    coupon_gp=("GP", "sum"),
    coupon_gbv=("GBV", "sum"),
).reset_index().sort_values("coupon_gp").head(20)


# ── 3. Helper: serialize DataFrames to JSON ────────────────────────────────────

def df_to_json(df, cols=None):
    if cols:
        df = df[cols]
    return json.dumps(df.replace({np.nan: None}).to_dict(orient="records"))

def fmt_num(n, decimals=0):
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "N/A"
    return f"{n:,.{decimals}f}"

def fmt_pct(n, decimals=1):
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "N/A"
    return f"{n:.{decimals}f}%"

# ── 4. Build HTML ──────────────────────────────────────────────────────────────

COLORS = {
    "coupon": "#2563EB",
    "no_coupon": "#94A3B8",
    "positive": "#16A34A",
    "negative": "#DC2626",
    "warn": "#D97706",
    "bg": "#F8FAFC",
    "card": "#FFFFFF",
    "border": "#E2E8F0",
    "text": "#1E293B",
    "muted": "#64748B",
}

# Precompute card KPIs
total_orders = int(df_order["Gross_orders"].sum())
coupon_orders = int(df_order[df_order["is_coupon"]]["Gross_orders"].sum())
coupon_order_pct = coupon_orders / total_orders * 100
total_gbv = df_order["GBV"].sum()
coupon_gbv = df_order[df_order["is_coupon"]]["GBV"].sum()
coupon_gbv_pct = coupon_gbv / total_gbv * 100
total_gp = df_order["GP"].sum()
coupon_gp = df_order[df_order["is_coupon"]]["GP"].sum()
coupon_gp_pct = coupon_gp / total_gp * 100
gp_margin_all = total_gp / total_gbv * 100
gp_margin_coupon = coupon_gp / coupon_gbv * 100
gp_margin_no_coupon = (total_gp - coupon_gp) / (total_gbv - coupon_gbv) * 100
total_coupon_cards = int(df_metric["n_coupon_card"].sum())
overall_success = df_metric[df_metric["n_coupon_card"] > 0]["success_rate"].mean()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Coupon Analytics Report 2025–2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
  :root {{
    --bg: {COLORS['bg']};
    --card: {COLORS['card']};
    --border: {COLORS['border']};
    --text: {COLORS['text']};
    --muted: {COLORS['muted']};
    --blue: {COLORS['coupon']};
    --gray: {COLORS['no_coupon']};
    --green: {COLORS['positive']};
    --red: {COLORS['negative']};
    --yellow: {COLORS['warn']};
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.6; }}
  .header {{ background: var(--blue); color: white; padding: 28px 40px; }}
  .header h1 {{ font-size: 22px; font-weight: 700; }}
  .header p {{ opacity: .8; font-size: 13px; margin-top: 4px; }}
  .container {{ max-width: 1280px; margin: 0 auto; padding: 24px 40px; }}
  .section {{ margin-bottom: 40px; }}
  .section-title {{ font-size: 16px; font-weight: 700; color: var(--text);
                    border-left: 4px solid var(--blue); padding-left: 10px; margin-bottom: 16px; }}
  .section-subtitle {{ font-size: 12px; color: var(--muted); margin-bottom: 14px; margin-top: -10px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }}
  .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
               padding: 16px 18px; }}
  .kpi-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }}
  .kpi-value {{ font-size: 22px; font-weight: 700; margin: 4px 0 2px; }}
  .kpi-sub {{ font-size: 11px; color: var(--muted); }}
  .kpi-sub .up {{ color: var(--green); }}
  .kpi-sub .down {{ color: var(--red); }}
  .charts-row {{ display: grid; gap: 16px; }}
  .charts-row.col2 {{ grid-template-columns: 1fr 1fr; }}
  .charts-row.col3 {{ grid-template-columns: 1fr 1fr 1fr; }}
  .chart-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}
  .chart-card h3 {{ font-size: 13px; font-weight: 600; margin-bottom: 12px; color: var(--text); }}
  .chart-card p.note {{ font-size: 11px; color: var(--muted); margin-top: 8px; }}
  canvas {{ max-height: 280px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ background: var(--bg); color: var(--muted); font-weight: 600; padding: 8px 10px;
        text-align: left; border-bottom: 2px solid var(--border); white-space: nowrap; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid var(--border); }}
  tr:hover td {{ background: #F1F5F9; }}
  .badge {{ display: inline-block; padding: 2px 7px; border-radius: 99px; font-size: 10px; font-weight: 600; }}
  .badge-blue {{ background: #DBEAFE; color: var(--blue); }}
  .badge-green {{ background: #DCFCE7; color: var(--green); }}
  .badge-red {{ background: #FEE2E2; color: var(--red); }}
  .badge-yellow {{ background: #FEF3C7; color: var(--yellow); }}
  .insight-box {{ background: #EFF6FF; border-left: 4px solid var(--blue); border-radius: 0 8px 8px 0;
                  padding: 12px 16px; margin-bottom: 16px; font-size: 13px; line-height: 1.7; }}
  .insight-box strong {{ color: var(--blue); }}
  .toc {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
          padding: 16px 20px; margin-bottom: 28px; }}
  .toc h2 {{ font-size: 13px; font-weight: 600; margin-bottom: 10px; }}
  .toc ol {{ padding-left: 20px; }}
  .toc li {{ margin: 4px 0; }}
  .toc a {{ color: var(--blue); text-decoration: none; font-size: 13px; }}
  .toc a:hover {{ text-decoration: underline; }}
  .tag-highlight {{ background: #FEF3C7; padding: 1px 5px; border-radius: 3px; color: #92400E; font-weight: 600; }}
  .divider {{ border: none; border-top: 1px solid var(--border); margin: 32px 0; }}
</style>
</head>
<body>

<div class="header">
  <h1>Coupon Analytics Report</h1>
  <p>Time Range: Full Year 2025 + Jan–May 2026  |  Source: SPA Affiliate Coupon Order Data & Coupon Metric</p>
</div>

<div class="container">

<!-- TOC -->
<div class="toc">
  <h2>Table of Contents</h2>
  <ol>
    <li><a href="#overview">Overview — Coupon Scale & Key KPIs</a></li>
    <li><a href="#yoy">Year-over-Year — Coupon Penetration Trend</a></li>
    <li><a href="#financial">Financial Impact — GP Margin, Net Order Rate & NBV/GBV</a></li>
    <li><a href="#cancel">Cancellation & Retention — Does Coupon Reduce Cancellations?</a></li>
    <li><a href="#segment">Industry Segment Breakdown — Coupon Behaviour by Segment</a></li>
    <li><a href="#device">Device Analysis — Mobile vs Browser Coupon Preference</a></li>
    <li><a href="#payment">Payment & Refund — Merchant/Agency and Refundable Differences</a></li>
    <li><a href="#metric">Coupon Metric — Application, Success & Failure Rates</a></li>
    <li><a href="#partner">Partner-Level — High-Value Partners & At-Risk Partners</a></li>
  </ol>
</div>

<!-- ═══════════════════════════════════════════════════════════
     SECTION 1: OVERVIEW KPIs
═══════════════════════════════════════════════════════════ -->
<div class="section" id="overview">
  <div class="section-title">1. Overview — Coupon Scale & Key KPIs</div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Total Gross Orders</div>
      <div class="kpi-value">{fmt_num(total_orders)}</div>
      <div class="kpi-sub">Gross Orders (2025-2026)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Coupon Order Share</div>
      <div class="kpi-value" style="color:var(--blue)">{fmt_pct(coupon_order_pct)}</div>
      <div class="kpi-sub">{fmt_num(coupon_orders)} coupon orders</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Coupon GBV Share</div>
      <div class="kpi-value" style="color:var(--blue)">{fmt_pct(coupon_gbv_pct)}</div>
      <div class="kpi-sub">${fmt_num(coupon_gbv/1e6, 1)}M Coupon GBV</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">GP Margin — Coupon vs Overall</div>
      <div class="kpi-value" style="color:{'var(--red)' if gp_margin_coupon < gp_margin_all else 'var(--green)'}">{fmt_pct(gp_margin_coupon)}</div>
      <div class="kpi-sub">Overall avg {fmt_pct(gp_margin_all)}  | No Coupon {fmt_pct(gp_margin_no_coupon)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total GBV</div>
      <div class="kpi-value">${fmt_num(total_gbv/1e6, 1)}M</div>
      <div class="kpi-sub">Net GBV (NBV): ${fmt_num(df_order['NBV'].sum()/1e6, 1)}M</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total GP</div>
      <div class="kpi-value">${fmt_num(total_gp/1e6, 1)}M</div>
      <div class="kpi-sub">Net GP: ${fmt_num(df_order['Net_GP'].sum()/1e6, 1)}M</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Coupon GP Share</div>
      <div class="kpi-value" style="color:var(--blue)">{fmt_pct(coupon_gp_pct)}</div>
      <div class="kpi-sub">Coupon GP: ${fmt_num(coupon_gp/1e6, 1)}M</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Coupon Card Uses</div>
      <div class="kpi-value" style="color:var(--blue)">{fmt_num(total_coupon_cards)}</div>
      <div class="kpi-sub">Avg Success Rate {fmt_pct(overall_success*100 if overall_success else 0)}</div>
    </div>
  </div>

  <div class="insight-box">
    <strong>Key Insight:</strong>
    Coupon orders account for <strong>{fmt_pct(coupon_order_pct)}</strong> of total orders, and <strong>{fmt_pct(coupon_gbv_pct)}</strong> of total GBV.
    Coupon order GP Margin is <strong>{fmt_pct(gp_margin_coupon)}</strong>，
    {'below' if gp_margin_coupon < gp_margin_no_coupon else 'above'} non-coupon orders ({fmt_pct(gp_margin_no_coupon)}),
    a gap of <strong>{fmt_pct(abs(gp_margin_coupon - gp_margin_no_coupon))}</strong>。
    This {'compression' if gp_margin_coupon < gp_margin_no_coupon else 'uplift'} in margin should be evaluated against business objectives.
  </div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon vs No Coupon — Orders / GBV / GP Breakdown</h3>
      <canvas id="chart_overall_bar"></canvas>
    </div>
    <div class="chart-card">
      <h3>GP Margin Comparison: Coupon Applied vs No Coupon</h3>
      <canvas id="chart_gp_margin"></canvas>
      <p class="note">⚠️ GP Margin = GP / GBV. If your team defines margin as GP / NBV, figures will differ.</p>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 2: YoY TREND
═══════════════════════════════════════════════════════════ -->
<div class="section" id="yoy">
  <div class="section-title">2. Year-over-Year — 2025 vs 2026 Coupon Penetration</div>
  <div class="section-subtitle">Note: 2026 data covers Jan–May only; interpret absolute comparisons with 2025 full-year accordingly.</div>

  <div class="charts-row col3">
    <div class="chart-card">
      <h3>Coupon Order Penetration (%)</h3>
      <canvas id="chart_yoy_order_pct"></canvas>
      <p class="note">⚠️ Penetration = sum of Coupon Gross_orders / sum of all Gross_orders. If the source data contains subtotal rows, figures may be double-counted.</p>
    </div>
    <div class="chart-card">
      <h3>Coupon GBV Penetration (%)</h3>
      <canvas id="chart_yoy_gbv_pct"></canvas>
    </div>
    <div class="chart-card">
      <h3>Coupon GP Penetration (%)</h3>
      <canvas id="chart_yoy_gp_pct"></canvas>
    </div>
  </div>

  <div class="charts-row col2" style="margin-top:16px">
    <div class="chart-card">
      <h3>2025 vs 2026 Absolute Metrics (Coupon Applied)</h3>
      <canvas id="chart_yoy_abs"></canvas>
    </div>
    <div class="chart-card">
      <h3>2025 vs 2026 GP Margin Trend (Coupon vs No Coupon)</h3>
      <canvas id="chart_yoy_gp_margin"></canvas>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 3: FINANCIAL IMPACT
═══════════════════════════════════════════════════════════ -->
<div class="section" id="financial">
  <div class="section-title">3. Financial Impact — GP Margin, Net Order Rate & NBV/GBV</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Key Financial Metrics Comparison (Coupon vs No Coupon)</h3>
      <canvas id="chart_financial_radar"></canvas>
      <p class="note">All radar dimensions normalised to 0–100 for visual comparison</p>
    </div>
    <div class="chart-card">
      <h3>Net Order Rate & NBV/GBV Ratio Comparison</h3>
      <canvas id="chart_financial_bar"></canvas>
      <p class="note">Net Order Rate = Net_orders / Gross_orders; NBV/GBV Ratio reflects refund erosion</p>
    </div>
  </div>

  <div class="insight-box" style="margin-top:16px">
    <strong>Interpretation:</strong>
    Net Order Retention Rate —
    Coupon: <strong>{fmt_pct(gp_compare.loc[gp_compare['is_coupon']==True, 'Net_order_rate'].values[0] if len(gp_compare[gp_compare['is_coupon']==True]) else 0)}</strong>
    vs No Coupon: <strong>{fmt_pct(gp_compare.loc[gp_compare['is_coupon']==False, 'Net_order_rate'].values[0] if len(gp_compare[gp_compare['is_coupon']==False]) else 0)}</strong>. A lower NBV/GBV ratio indicates higher refund erosion.
    Avg GBV per order — Coupon:
    <strong>${fmt_num(gp_compare.loc[gp_compare['is_coupon']==True, 'Avg_GBV_per_order'].values[0] if len(gp_compare[gp_compare['is_coupon']==True]) else 0, 0)}</strong>
    vs No Coupon <strong>${fmt_num(gp_compare.loc[gp_compare['is_coupon']==False, 'Avg_GBV_per_order'].values[0] if len(gp_compare[gp_compare['is_coupon']==False]) else 0, 0)}</strong>.
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 4: CANCELLATION & RETENTION
═══════════════════════════════════════════════════════════ -->
<div class="section" id="cancel">
  <div class="section-title">4. Cancellation & Retention — Does Coupon Reduce Cancellations?</div>
  <div class="section-subtitle">Net Order Rate = Net Orders / Gross Orders — higher means fewer cancellations/refunds</div>

  <div class="kpi-grid" style="grid-template-columns: repeat(3,1fr); margin-bottom:20px">
    <div class="kpi-card">
      <div class="kpi-label">Net Order Rate — Coupon</div>
      <div class="kpi-value" style="color:var(--blue)">{nr_coupon_overall:.1f}%</div>
      <div class="kpi-sub">of coupon orders retained</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Net Order Rate — No Coupon</div>
      <div class="kpi-value" style="color:var(--gray)">{nr_nocoupon_overall:.1f}%</div>
      <div class="kpi-sub">of non-coupon orders retained</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Retention Uplift from Coupon</div>
      <div class="kpi-value" style="color:{'var(--green)' if nr_coupon_overall > nr_nocoupon_overall else 'var(--red)'}">{'+' if nr_coupon_overall > nr_nocoupon_overall else ''}{nr_coupon_overall - nr_nocoupon_overall:.1f}pp</div>
      <div class="kpi-sub">Coupon vs No Coupon</div>
    </div>
  </div>

  <div class="insight-box">
    <strong>Key Finding:</strong>
    Coupon orders have a Net Order Rate of <strong>{nr_coupon_overall:.1f}%</strong> vs <strong>{nr_nocoupon_overall:.1f}%</strong> for non-coupon orders —
    a <strong>+{nr_coupon_overall - nr_nocoupon_overall:.1f}pp</strong> retention uplift.
    This suggests customers who use a coupon are more committed to completing their booking and less likely to cancel.
    However, this does not capture pre-booking conversion (funnel data required for that).
  </div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Net Order Rate: Coupon vs No Coupon (Overall)</h3>
      <canvas id="chart_cancel_overall"></canvas>
      <p class="note">⚠️ Net Order Rate = Net_orders / Gross_orders. Verify that Net_orders and Gross_orders match your team's definition of retained vs. cancelled orders.</p>
    </div>
    <div class="chart-card">
      <h3>Net Order Rate Delta by Segment (Coupon − No Coupon, pp)</h3>
      <p class="note" style="margin-bottom:8px">Green = coupon reduces cancellations; Red = coupon increases cancellations</p>
      <canvas id="chart_cancel_seg" style="max-height:380px"></canvas>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 5: INDUSTRY SEGMENT
═══════════════════════════════════════════════════════════ -->
<div class="section" id="segment">
  <div class="section-title">5. Industry Segment Breakdown — Coupon Behaviour by Segment</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon Order Penetration vs Total GBV by Segment</h3>
      <canvas id="chart_seg_pen"></canvas>
    </div>
    <div class="chart-card">
      <h3>GP Margin by Segment: Coupon vs Overall</h3>
      <canvas id="chart_seg_gp"></canvas>
    </div>
  </div>

  <div style="margin-top:16px">
    <div class="chart-card">
      <h3>Industry Segment Detail Table</h3>
      <table style="font-size:11px">
        <thead>
          <tr style="white-space:nowrap">
            <th style="padding:6px 7px">Industry Segment</th>
            <th style="padding:6px 7px">Total GBV</th>
            <th style="padding:6px 7px">Coupon GBV%</th>
            <th style="padding:6px 7px">Coupon Order%</th>
            <th style="padding:6px 7px">GP Margin</th>
            <th style="padding:6px 7px">Coupon GP Margin</th>
            <th style="padding:6px 7px">GP Δ</th>
            <th style="padding:6px 7px">NOR (Coupon)</th>
            <th style="padding:6px 7px">NOR (No Coupon)</th>
            <th style="padding:6px 7px">Retention Δ</th>
          </tr>
        </thead>
        <tbody>
"""

for _, row in seg_pen.iterrows():
    gp_diff = row.get("gp_margin_coupon", 0) - row.get("gp_margin_all", 0)
    gp_diff_fmt = f"{'+' if gp_diff >= 0 else ''}{gp_diff:.1f}%"
    gp_diff_class = "badge-green" if gp_diff >= 0 else "badge-red"
    nr_delta = row.get("nr_delta", float("nan"))
    nr_delta_fmt = f"{'+' if nr_delta >= 0 else ''}{nr_delta:.1f}pp" if nr_delta == nr_delta else "N/A"
    nr_delta_class = "badge-green" if nr_delta == nr_delta and nr_delta >= 0 else "badge-red"
    html += f"""
          <tr style="font-size:11px">
            <td style="padding:5px 7px">{row['industry_segment']}</td>
            <td style="padding:5px 7px">${fmt_num(row['total_gbv']/1e3, 0)}K</td>
            <td style="padding:5px 7px">{fmt_pct(row.get('coupon_gbv_pct', 0))}</td>
            <td style="padding:5px 7px">{fmt_pct(row.get('coupon_order_pct', 0))}</td>
            <td style="padding:5px 7px">{fmt_pct(row.get('gp_margin_all', 0))}</td>
            <td style="padding:5px 7px">{fmt_pct(row.get('gp_margin_coupon', 0))}</td>
            <td style="padding:5px 7px"><span class="badge {gp_diff_class}">{gp_diff_fmt}</span></td>
            <td style="padding:5px 7px">{fmt_pct(row.get('nr_coupon', 0))}</td>
            <td style="padding:5px 7px">{fmt_pct(row.get('nr_no_coupon', 0))}</td>
            <td style="padding:5px 7px"><span class="badge {nr_delta_class}">{nr_delta_fmt}</span></td>
          </tr>"""

html += """
        </tbody>
      </table>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 5: DEVICE TYPE
═══════════════════════════════════════════════════════════ -->
<div class="section" id="device">
  <div class="section-title">5. Device Analysis — Mobile vs Browser Coupon Preference</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon Order Share by Device</h3>
      <canvas id="chart_device_pct"></canvas>
    </div>
    <div class="chart-card">
      <h3>GBV by Device (Coupon vs No Coupon)</h3>
      <canvas id="chart_device_gbv"></canvas>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 6: PAYMENT & REFUND
═══════════════════════════════════════════════════════════ -->
<div class="section" id="payment">
  <div class="section-title">6. Payment Type & Refund Analysis</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Merchant vs Agency — Coupon GBV Distribution</h3>
      <canvas id="chart_payment"></canvas>
    </div>
    <div class="chart-card">
      <h3>Refundable Flag — Net Order Rate Comparison</h3>
      <canvas id="chart_refund"></canvas>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 7: COUPON METRIC
═══════════════════════════════════════════════════════════ -->
<div class="section" id="metric">
  <div class="section-title">7. Coupon Metric — Application, Success & Failure Rates</div>
  <div class="section-subtitle">Source: Coupon Metric file (coupon card application behaviour, independent of Order Data)</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon Card Volume by Segment</h3>
      <canvas id="chart_metric_volume"></canvas>
    </div>
    <div class="chart-card">
      <h3>Success vs Failure Rate by Segment</h3>
      <canvas id="chart_metric_rate"></canvas>
    </div>
  </div>

  <div style="margin-top:16px">
    <div class="chart-card">
      <h3>Top 30 Partners by Coupon Card Volume</h3>
      <canvas id="chart_top_partners_metric" style="max-height:400px"></canvas>
    </div>
  </div>

  <div style="margin-top:16px">
    <div class="chart-card">
      <h3>Segment Summary Table</h3>
      <table>
        <thead>
          <tr>
            <th>Industry Segment</th>
            <th>Total Coupon Card Uses</th>
            <th>Application Rate</th>
            <th>Success Rate</th>
            <th>Failure Rate</th>
          </tr>
        </thead>
        <tbody>
"""

for _, row in seg_metric.iterrows():
    fail_class = "badge-red" if (row.get("failure_rate", 0) or 0) > 0.55 else "badge-yellow" if (row.get("failure_rate", 0) or 0) > 0.4 else "badge-green"
    html += f"""
          <tr>
            <td>{row['industry_segment']}</td>
            <td>{fmt_num(row['n_coupon_card'])}</td>
            <td>{fmt_pct((row.get('app_rate') or 0)*100)}</td>
            <td>{fmt_pct((row.get('success_rate') or 0)*100)}</td>
            <td><span class="badge {fail_class}">{fmt_pct((row.get('failure_rate') or 0)*100)}</span></td>
          </tr>"""

html += """
        </tbody>
      </table>
    </div>
  </div>
</div>

<hr class="divider">

<!-- ═══════════════════════════════════════════════════════════
     SECTION 8: PARTNER LEVEL
═══════════════════════════════════════════════════════════ -->
<div class="section" id="partner">
  <div class="section-title">8. Partner-Level Analysis</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>High GBV + High Failure Rate Partners (Failure Rate > 60% & GBV Top 25%)</h3>
      <p class="note" style="margin-bottom:8px">These partners have high coupon attempt failure — optimization opportunity</p>
      <table>
        <thead>
          <tr><th>Partner</th><th>Segment</th><th>Total GBV</th><th>Failure Rate</th><th>n_coupon_card</th></tr>
        </thead>
        <tbody>
"""

for _, row in quadrant.iterrows():
    html += f"""
          <tr>
            <td>{row['partner_name']}</td>
            <td><span class="badge badge-blue">{row.get('industry_segment','')}</span></td>
            <td>${fmt_num(row['total_gbv']/1e3, 0)}K</td>
            <td><span class="badge badge-red">{fmt_pct((row.get('failure_rate') or 0)*100)}</span></td>
            <td>{fmt_num(row.get('n_coupon_card', 0))}</td>
          </tr>"""

html += """
        </tbody>
      </table>
    </div>
    <div class="chart-card">
      <h3>High-Value + High Success Rate Partners (Success Rate > 50%, ranked by GBV)</h3>
      <p class="note" style="margin-bottom:8px">Partners executing coupon strategy effectively</p>
      <table>
        <thead>
          <tr><th>Partner</th><th>Segment</th><th>Total GBV</th><th>Success Rate</th><th>GP Margin</th></tr>
        </thead>
        <tbody>
"""

for _, row in top_performers.iterrows():
    html += f"""
          <tr>
            <td>{row['partner_name']}</td>
            <td><span class="badge badge-blue">{row.get('industry_segment','')}</span></td>
            <td>${fmt_num(row['total_gbv']/1e3, 0)}K</td>
            <td><span class="badge badge-green">{fmt_pct((row.get('success_rate') or 0)*100)}</span></td>
            <td>{fmt_pct(row.get('gp_margin', 0))}</td>
          </tr>"""

html += """
        </tbody>
      </table>
    </div>
  </div>

  <div style="margin-top:16px">
    <div class="chart-card">
      <h3>Partners with Negative Coupon GP (Top 20 Losses)</h3>
      <p class="note" style="margin-bottom:8px">These partners generate net GP losses on coupon orders — discount strategy needs review</p>
      <table>
        <thead>
          <tr><th>Partner</th><th>Coupon Orders</th><th>Coupon GBV</th><th>Coupon GP</th><th>GP / Order</th></tr>
        </thead>
        <tbody>
"""

for _, row in neg_gp_coupon.iterrows():
    gp_per_order = row["coupon_gp"] / row["coupon_orders"] if row["coupon_orders"] > 0 else 0
    html += f"""
          <tr>
            <td>{row['partner_name']}</td>
            <td>{fmt_num(row['coupon_orders'])}</td>
            <td>${fmt_num(row['coupon_gbv'], 0)}</td>
            <td style="color:var(--red)"><strong>${fmt_num(row['coupon_gp'], 0)}</strong></td>
            <td style="color:var(--red)">${fmt_num(gp_per_order, 0)}</td>
          </tr>"""

html += """
        </tbody>
      </table>
    </div>
  </div>
</div>

</div><!-- /container -->

<!-- ═══════════════════════════════════════════════════════════
     CHART.JS SCRIPTS
═══════════════════════════════════════════════════════════ -->
<script>
const BLUE = '#2563EB', GRAY = '#94A3B8', GREEN = '#16A34A', RED = '#DC2626', YELLOW = '#D97706';
const PALETTE = ['#2563EB','#16A34A','#D97706','#DC2626','#7C3AED','#0891B2','#BE185D'];

Chart.register(ChartDataLabels);
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.labels.boxWidth = 12;

const FMT = (v) => v == null || v === 0 ? '' : (Math.abs(v) >= 1000 ? (v/1000).toFixed(1)+'K' : Math.abs(v) >= 1 ? v.toFixed(1) : v.toFixed(2));

const DL_BAR = {
  display: true,
  anchor: 'end',
  align: 'top',
  offset: 2,
  clamp: false,
  clip: false,
  font: { size: 9, weight: '600' },
  color: '#334155',
  formatter: FMT
};

const DL_HBAR = {
  display: true,
  anchor: 'end',
  align: 'right',
  offset: 4,
  clamp: false,
  clip: false,
  font: { size: 9, weight: '600' },
  color: '#334155',
  formatter: FMT
};

function makeBar(id, labels, datasets, opts={}) {
  const dlOpts = opts._dl !== false ? { datalabels: DL_BAR } : { datalabels: { display: false } };
  delete opts._dl;
  const extraPlugins = opts.plugins || {};
  delete opts.plugins;
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      clip: false,
      layout: { padding: { top: 24 } },
      plugins: { legend: { position: 'bottom' }, ...dlOpts, ...extraPlugins },
      scales: { y: { beginAtZero: true, grid: { color: '#F1F5F9' } },
                x: { grid: { display: false } } },
      ...opts
    }
  });
}

function makeHBar(id, labels, datasets, opts={}) {
  const dlOpts = opts._dl !== false ? { datalabels: DL_HBAR } : { datalabels: { display: false } };
  delete opts._dl;
  const extraPlugins = opts.plugins || {};
  delete opts.plugins;
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      indexAxis: 'y',
      responsive: true,
      clip: false,
      layout: { padding: { right: 50 } },
      plugins: { legend: { position: 'bottom' }, ...dlOpts, ...extraPlugins },
      scales: { x: { beginAtZero: true, grid: { color: '#F1F5F9' } },
                y: { grid: { display: false }, ticks: { font: { size: 10 } } } },
      ...opts
    }
  });
}
</script>
<script>
// ── Chart 1 & 2 injected below ──
"""

html += f"""
// ── Chart 1: Overall bar — dual y-axis ───────────────────────────
new Chart(document.getElementById('chart_overall_bar'), {{
  type: 'bar',
  data: {{
    labels: ['Gross Orders', 'GBV ($M)', 'GP ($M)'],
    datasets: [
      {{ label: 'Coupon Applied', backgroundColor: BLUE, yAxisID: 'y',
         data: [{coupon_orders}, null, null],
         datalabels: {{ ...DL_BAR }} }},
      {{ label: 'No Coupon', backgroundColor: GRAY, yAxisID: 'y',
         data: [{total_orders - coupon_orders}, null, null],
         datalabels: {{ ...DL_BAR }} }},
      {{ label: 'Coupon Applied (right)', backgroundColor: BLUE, yAxisID: 'y1',
         data: [null, {coupon_gbv/1e6:.2f}, {coupon_gp/1e6:.2f}],
         datalabels: {{ ...DL_BAR }} }},
      {{ label: 'No Coupon (right)', backgroundColor: GRAY, yAxisID: 'y1',
         data: [null, {(total_gbv - coupon_gbv)/1e6:.2f}, {(total_gp - coupon_gp)/1e6:.2f}],
         datalabels: {{ ...DL_BAR }} }},
    ]
  }},
  options: {{
    responsive: true,
    clip: false,
    layout: {{ padding: {{ top: 24 }} }},
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ filter: (item) => !item.text.includes('right') }} }},
      datalabels: DL_BAR
    }},
    scales: {{
      y:  {{ beginAtZero: true, position: 'left',  title: {{ display: true, text: 'Orders' }}, grid: {{ color: '#F1F5F9' }} }},
      y1: {{ beginAtZero: true, position: 'right', title: {{ display: true, text: '$M' }}, grid: {{ drawOnChartArea: false }} }},
      x:  {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ── Chart 2: GP Margin comparison ─────────────────────────────────
makeBar('chart_gp_margin',
  ['Coupon Applied', 'No Coupon', 'Overall'],
  [{{
    label: 'GP Margin (%)',
    backgroundColor: [BLUE, GRAY, '#7C3AED'],
    data: [{gp_margin_coupon:.2f}, {gp_margin_no_coupon:.2f}, {gp_margin_all:.2f}]
  }}],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);

// ── Chart 3-5: YoY penetration ─────────────────────────────────────
"""

# Serialize YoY data
yr_pen_dict = yr_pen.set_index("yr").to_dict()
years = yr_pen["yr"].tolist()

html += f"""
makeBar('chart_yoy_order_pct',
  {json.dumps(years)},
  [{{ label: 'Coupon Order Penetration (%)', backgroundColor: BLUE,
     data: {json.dumps([round(yr_pen_dict['order_pct'].get(y, 0), 2) for y in years])} }}],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);
makeBar('chart_yoy_gbv_pct',
  {json.dumps(years)},
  [{{ label: 'Coupon GBV Penetration (%)', backgroundColor: GREEN,
     data: {json.dumps([round(yr_pen_dict['gbv_pct'].get(y, 0), 2) for y in years])} }}],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);
makeBar('chart_yoy_gp_pct',
  {json.dumps(years)},
  [{{ label: 'Coupon GP Penetration (%)', backgroundColor: YELLOW,
     data: {json.dumps([round(yr_pen_dict['gp_pct'].get(y, 0), 2) for y in years])} }}],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);
"""

# YoY absolute values for coupon
yoy_coupon = yoy[yoy["is_coupon"] == True].set_index("yr")
html += f"""
makeBar('chart_yoy_abs',
  {json.dumps(years)},
  [
    {{ label: 'Gross Orders', backgroundColor: BLUE, yAxisID: 'y',
       data: {json.dumps([int(yoy_coupon["Gross_orders"].get(y, 0)) for y in years])} }},
    {{ label: 'GBV ($M)', backgroundColor: GREEN, yAxisID: 'y1',
       data: {json.dumps([round(float(yoy_coupon["GBV"].get(y, 0))/1e6, 2) for y in years])} }},
  ],
  {{
    scales: {{
      y: {{ beginAtZero: true, position: 'left', title: {{ display: true, text: 'Orders' }} }},
      y1: {{ beginAtZero: true, position: 'right', title: {{ display: true, text: 'GBV $M' }}, grid: {{ drawOnChartArea: false }} }}
    }}
  }}
);
"""

# YoY GP margin by coupon/no-coupon
yoy_gp = yoy.copy()
yoy_gp["gp_margin"] = yoy_gp["GP"] / yoy_gp["GBV"].replace(0, np.nan) * 100
coupon_gp_margin_by_yr = yoy_gp[yoy_gp["is_coupon"] == True].set_index("yr")["gp_margin"]
no_coupon_gp_margin_by_yr = yoy_gp[yoy_gp["is_coupon"] == False].set_index("yr")["gp_margin"]

html += f"""
makeBar('chart_yoy_gp_margin',
  {json.dumps(years)},
  [
    {{ label: 'Coupon GP Margin (%)', backgroundColor: BLUE,
       data: {json.dumps([round(float(coupon_gp_margin_by_yr.get(y, 0)), 2) for y in years])} }},
    {{ label: 'No Coupon GP Margin (%)', backgroundColor: GRAY,
       data: {json.dumps([round(float(no_coupon_gp_margin_by_yr.get(y, 0)), 2) for y in years])} }},
  ]
);
"""

# Financial radar
gp_c = float(gp_compare.loc[gp_compare['is_coupon']==True, 'GP_margin'].values[0]) if len(gp_compare[gp_compare['is_coupon']==True]) else 0
gp_nc = float(gp_compare.loc[gp_compare['is_coupon']==False, 'GP_margin'].values[0]) if len(gp_compare[gp_compare['is_coupon']==False]) else 0
nr_c = float(gp_compare.loc[gp_compare['is_coupon']==True, 'Net_order_rate'].values[0]) if len(gp_compare[gp_compare['is_coupon']==True]) else 0
nr_nc = float(gp_compare.loc[gp_compare['is_coupon']==False, 'Net_order_rate'].values[0]) if len(gp_compare[gp_compare['is_coupon']==False]) else 0
nbv_c = float(gp_compare.loc[gp_compare['is_coupon']==True, 'NBV_GBV_ratio'].values[0]) if len(gp_compare[gp_compare['is_coupon']==True]) else 0
nbv_nc = float(gp_compare.loc[gp_compare['is_coupon']==False, 'NBV_GBV_ratio'].values[0]) if len(gp_compare[gp_compare['is_coupon']==False]) else 0
avg_gbv_c = float(gp_compare.loc[gp_compare['is_coupon']==True, 'Avg_GBV_per_order'].values[0]) if len(gp_compare[gp_compare['is_coupon']==True]) else 0
avg_gbv_nc = float(gp_compare.loc[gp_compare['is_coupon']==False, 'Avg_GBV_per_order'].values[0]) if len(gp_compare[gp_compare['is_coupon']==False]) else 0
max_avg_gbv = max(avg_gbv_c, avg_gbv_nc, 1)

html += f"""
new Chart(document.getElementById('chart_financial_radar'), {{
  type: 'radar',
  data: {{
    labels: ['GP Margin', 'Net Order Rate', 'NBV/GBV Ratio', 'Avg GBV/Order (normalized)'],
    datasets: [
      {{ label: 'Coupon Applied', borderColor: BLUE, backgroundColor: BLUE+'33',
         data: [{gp_c:.1f}, {nr_c:.1f}, {nbv_c:.1f}, {avg_gbv_c/max_avg_gbv*100:.1f}] }},
      {{ label: 'No Coupon', borderColor: GRAY, backgroundColor: GRAY+'33',
         data: [{gp_nc:.1f}, {nr_nc:.1f}, {nbv_nc:.1f}, {avg_gbv_nc/max_avg_gbv*100:.1f}] }},
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ font: {{ size: 12 }} }} }},
      datalabels: {{ display: false }}
    }},
    scales: {{
      r: {{
        beginAtZero: true,
        max: 100,
        ticks: {{ font: {{ size: 11 }}, stepSize: 20 }},
        pointLabels: {{ font: {{ size: 12, weight: '600' }} }}
      }}
    }}
  }}
}});

makeBar('chart_financial_bar',
  ['Net Order Rate (%)', 'NBV/GBV Ratio (%)'],
  [
    {{ label: 'Coupon Applied', backgroundColor: BLUE, data: [{nr_c:.2f}, {nbv_c:.2f}] }},
    {{ label: 'No Coupon', backgroundColor: GRAY, data: [{nr_nc:.2f}, {nbv_nc:.2f}] }},
  ]
);
"""

# Cancellation charts
cancel_labels = cancel["label"].tolist()
cancel_net_rates = [round(float(x), 1) for x in cancel["net_rate"].tolist()]
cancel_cancel_rates = [round(float(x), 1) for x in cancel["cancel_rate"].tolist()]

seg_delta_labels = seg_pivot_sorted["industry_segment"].tolist()
seg_delta_vals   = [round(float(x), 1) for x in seg_pivot_sorted["delta"].tolist()]
seg_delta_nr_c   = [round(float(x), 1) for x in seg_pivot_sorted["net_rate_coupon"].tolist()]
seg_delta_nr_nc  = [round(float(x), 1) for x in seg_pivot_sorted["net_rate_no_coupon"].tolist()]
seg_delta_colors = json.dumps(["#16A34A" if v >= 0 else "#DC2626" for v in seg_delta_vals])

html += f"""
// ── Cancellation Overall ──────────────────────────────────────────
makeBar('chart_cancel_overall',
  {json.dumps(cancel_labels)},
  [
    {{ label: 'Net Order Rate (%)', backgroundColor: [BLUE, GRAY],
       data: {json.dumps(cancel_net_rates)} }},
  ],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);

// ── Cancellation by Segment (delta) ──────────────────────────────
new Chart(document.getElementById('chart_cancel_seg'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(seg_delta_labels)},
    datasets: [{{
      label: 'Net Order Rate Delta (pp)',
      backgroundColor: {seg_delta_colors},
      data: {json.dumps(seg_delta_vals)},
      datalabels: {{ ...DL_HBAR, formatter: v => (v > 0 ? '+' : '') + v.toFixed(1) }}
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    clip: false,
    layout: {{ padding: {{ right: 50 }} }},
    plugins: {{ legend: {{ display: false }}, datalabels: DL_HBAR }},
    scales: {{
      x: {{ beginAtZero: false, grid: {{ color: '#F1F5F9' }},
             title: {{ display: true, text: 'Delta (pp)' }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }}
    }}
  }}
}});
"""

# Segment penetration chart
seg_labels = seg_pen["industry_segment"].tolist()
seg_coupon_pcts = seg_pen["coupon_order_pct"].fillna(0).tolist()
seg_gbvs = (seg_pen["total_gbv"] / 1e6).tolist()

html += f"""
makeBar('chart_seg_pen',
  {json.dumps(seg_labels)},
  [
    {{ label: 'Coupon Order Share (%)', backgroundColor: BLUE, yAxisID: 'y',
       data: {json.dumps([round(float(x),2) for x in seg_coupon_pcts])} }},
    {{ label: 'Total GBV ($M)', backgroundColor: GRAY+'80', yAxisID: 'y1',
       data: {json.dumps([round(float(x),2) for x in seg_gbvs])} }},
  ],
  {{
    _dl: false,
    scales: {{
      y:  {{ beginAtZero: true, position: 'left',  title: {{ display: true, text: 'Coupon Share (%)' }} }},
      y1: {{ beginAtZero: true, position: 'right', title: {{ display: true, text: 'GBV $M' }}, grid: {{ drawOnChartArea: false }} }},
      x:  {{ grid: {{ display: false }}, ticks: {{ maxRotation: 45, minRotation: 30, font: {{ size: 10 }} }} }}
    }}
  }}
);

makeBar('chart_seg_gp',
  {json.dumps(seg_labels)},
  [
    {{ label: 'Overall GP Margin (%)', backgroundColor: GRAY, data: {json.dumps([round(float(x),2) for x in seg_pen['gp_margin_all'].fillna(0).tolist()])} }},
    {{ label: 'Coupon GP Margin (%)', backgroundColor: BLUE, data: {json.dumps([round(float(x),2) for x in seg_pen['gp_margin_coupon'].fillna(0).tolist()])} }},
  ],
  {{ _dl: false, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 45, minRotation: 30, font: {{ size: 10 }} }} }} }} }}
);
"""

# Device charts
dev_labels = device_pivot["cbe_purchase_device_type"].tolist()
dev_coupon_pct = device_pivot["coupon_pct"].fillna(0).tolist()
dev_gbv_coupon = device_pivot.get("GBV_True", pd.Series([0]*len(device_pivot))).fillna(0).tolist()
dev_gbv_no = device_pivot.get("GBV_False", pd.Series([0]*len(device_pivot))).fillna(0).tolist()

html += f"""
makeBar('chart_device_pct',
  {json.dumps(dev_labels)},
  [{{ label: 'Coupon Order Share (%)', backgroundColor: PALETTE,
     data: {json.dumps([round(float(x),2) for x in dev_coupon_pct])} }}],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);
makeBar('chart_device_gbv',
  {json.dumps(dev_labels)},
  [
    {{ label: 'Coupon GBV', backgroundColor: BLUE, data: {json.dumps([round(float(x)/1e3,1) for x in dev_gbv_coupon])} }},
    {{ label: 'No Coupon GBV', backgroundColor: GRAY, data: {json.dumps([round(float(x)/1e3,1) for x in dev_gbv_no])} }},
  ]
);
"""

# Payment chart
pay_coupon = pay[pay["is_coupon"] == True].set_index("payment_type")
pay_no = pay[pay["is_coupon"] == False].set_index("payment_type")
pay_labels = pay["payment_type"].unique().tolist()

html += f"""
makeBar('chart_payment',
  {json.dumps(pay_labels)},
  [
    {{ label: 'Coupon GBV', backgroundColor: BLUE,
       data: {json.dumps([round(float(pay_coupon["GBV"].get(p, 0))/1e3, 1) for p in pay_labels])} }},
    {{ label: 'No Coupon GBV', backgroundColor: GRAY,
       data: {json.dumps([round(float(pay_no["GBV"].get(p, 0))/1e3, 1) for p in pay_labels])} }},
  ]
);
"""

# Refund chart
refund_coupon = refund[refund["is_coupon"] == True].set_index("refundable_indicator")
refund_no = refund[refund["is_coupon"] == False].set_index("refundable_indicator")
refund_labels = refund["refundable_indicator"].unique().tolist()

html += f"""
makeBar('chart_refund',
  {json.dumps(refund_labels)},
  [
    {{ label: 'Coupon Net Order Rate (%)', backgroundColor: BLUE,
       data: {json.dumps([round(float(refund_coupon["net_rate"].get(r, 0)), 1) for r in refund_labels])} }},
    {{ label: 'No Coupon Net Order Rate (%)', backgroundColor: GRAY,
       data: {json.dumps([round(float(refund_no["net_rate"].get(r, 0)), 1) for r in refund_labels])} }},
  ]
);
"""

# Metric charts
seg_m_labels = seg_metric["industry_segment"].tolist()
seg_m_vol = [int(x) for x in seg_metric["n_coupon_card"].tolist()]
seg_m_success = [round(float(x or 0)*100, 1) for x in seg_metric["success_rate"].tolist()]
seg_m_failure = [round(float(x or 0)*100, 1) for x in seg_metric["failure_rate"].tolist()]

html += f"""
makeBar('chart_metric_volume',
  {json.dumps(seg_m_labels)},
  [{{ label: 'Coupon Card Volume', backgroundColor: PALETTE,
     data: {json.dumps(seg_m_vol)} }}],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);
makeBar('chart_metric_rate',
  {json.dumps(seg_m_labels)},
  [
    {{ label: 'Success Rate (%)', backgroundColor: GREEN, data: {json.dumps(seg_m_success)} }},
    {{ label: 'Failure Rate (%)', backgroundColor: RED, data: {json.dumps(seg_m_failure)} }},
  ]
);
"""

# Top partners metric
tp_labels = top_partners_metric["partner_name"].str[:20].tolist()
tp_vals = [int(x) for x in top_partners_metric["n_coupon_card"].tolist()]
PY_GREEN = "#16A34A"
PY_YELLOW = "#D97706"
PY_RED = "#DC2626"
tp_colors = []
for _, row in top_partners_metric.iterrows():
    sr = row.get("success_rate") or 0
    if sr > 0.5:
        tp_colors.append(PY_GREEN)
    elif sr > 0.3:
        tp_colors.append(PY_YELLOW)
    else:
        tp_colors.append(PY_RED)

html += f"""
makeHBar('chart_top_partners_metric',
  {json.dumps(tp_labels)},
  [{{ label: 'n_coupon_card', backgroundColor: {json.dumps(tp_colors)},
     data: {json.dumps(tp_vals)} }}],
  {{ plugins: {{ legend: {{ display: false }} }} }}
);
</script></body></html>
"""

# ── 5. Write output ────────────────────────────────────────────────────────────
out_path = os.path.join(BASE, "coupon_report.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Report saved to: {out_path}")
print(f"   Total order rows processed: {len(df_order):,}")
print(f"   Total metric rows processed: {len(df_metric):,}")
print(f"   Coupon Applied orders: {coupon_orders:,} ({coupon_order_pct:.1f}%)")
print(f"   GP Margin — Coupon: {gp_margin_coupon:.2f}%  |  No Coupon: {gp_margin_no_coupon:.2f}%")
