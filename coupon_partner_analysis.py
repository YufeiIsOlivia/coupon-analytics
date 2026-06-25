#!/usr/bin/env python3
"""
Priority Coupon Partner Deep Dive
Inputs:  coupon order data(raw).csv  |  coupon metric.csv
Output:  coupon_partner_report.html
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

TYPE_ORDER   = ['Public', 'Private', 'Uniqodo']
TYPE_COLORS  = {'Public': '#2563EB', 'Private': '#16A34A', 'Uniqodo': '#D97706'}
BADGE_CLASS  = {'Public': 'pub', 'Private': 'priv', 'Uniqodo': 'uniq'}
TYPE_PARTNER_COUNT = {'Public': 54, 'Private': 22, 'Uniqodo': 1}

# ── Load order data ────────────────────────────────────────────────────────────
df_all = pd.read_csv(os.path.join(BASE, "coupon order data(raw).csv"), skiprows=3, encoding='latin1')
df_all.columns = df_all.columns.str.strip()
df_all = df_all.loc[:, ~df_all.columns.str.startswith("Unnamed")]
num_cols = ["Gross_orders", "Net_orders", "GBV", "NBV", "GP", "Net_GP"]
for c in num_cols:
    df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)
df_all['yr'] = df_all['yr'].astype(str)
df_all['is_coupon'] = df_all['coupon_indicator'] == 'Coupon Applied'
df_all['partner_upper'] = df_all['partner_name'].str.upper().str.strip()

# Filter to partner dim
df = df_all[df_all['partner_upper'].isin(PARTNER_DIM.keys())].copy()
df['coupon_type'] = df['partner_upper'].map(PARTNER_DIM)

# ── Load coupon metric data ────────────────────────────────────────────────────
df_m_raw = pd.read_csv(os.path.join(BASE, "coupon metric.csv"), encoding='latin1', header=0)
df_m_raw.columns = ["partner_name", "n_coupon_card", "app_rate_str", "success_rate_str", "failure_rate_str"]

KNOWN_SEGMENTS = {"Content creators", "Shopping marketplace", "Financial institutions",
                  "Non Endemic Companies", "Technology", "Travel suppliers"}
SKIP = {"Grand Total", "nan", "UNMAPPED PARTNER"}

def pct_to_float(s):
    if isinstance(s, float) and np.isnan(s): return np.nan
    s = str(s).strip()
    if s in ("#DIV/0!", "", "nan"): return np.nan
    return float(s.replace("%", "")) / 100

metric_rows = []
current_segment = None
for _, row in df_m_raw.iterrows():
    name = str(row["partner_name"]).strip()
    if name in KNOWN_SEGMENTS:
        current_segment = name; continue
    if name in SKIP or name == "nan": continue
    metric_rows.append({
        "industry_segment": current_segment, "partner_name": name,
        "n_coupon_card": pd.to_numeric(row["n_coupon_card"], errors="coerce"),
        "app_rate": pct_to_float(row["app_rate_str"]),
        "success_rate": pct_to_float(row["success_rate_str"]),
        "failure_rate": pct_to_float(row["failure_rate_str"]),
    })
df_metric_all = pd.DataFrame(metric_rows)
df_metric_all = df_metric_all[df_metric_all["industry_segment"].notna()]

# Filter metric to partner dim
df_metric_all['partner_upper'] = df_metric_all['partner_name'].str.upper().str.strip()
df_metric = df_metric_all[df_metric_all['partner_upper'].isin(PARTNER_DIM.keys())].copy()
df_metric['coupon_type'] = df_metric['partner_upper'].map(PARTNER_DIM)

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt(n, d=0):
    if n is None or (isinstance(n, float) and np.isnan(n)): return "N/A"
    return f"{n:,.{d}f}"

def pct(n, d=1):
    if n is None or (isinstance(n, float) and np.isnan(n)): return "N/A"
    return f"{n:.{d}f}%"

def jn(lst, d=2):
    return json.dumps([round(float(x), d) if (x == x and x is not None) else 0 for x in lst])

def safe(v, fallback=0):
    try:
        f = float(v)
        return fallback if np.isnan(f) else f
    except: return fallback

# ── Analysis ───────────────────────────────────────────────────────────────────

# 1. Overall KPIs
total_orders    = int(df["Gross_orders"].sum())
coupon_orders   = int(df[df["is_coupon"]]["Gross_orders"].sum())
coupon_order_pct = coupon_orders / total_orders * 100
total_gbv       = df["GBV"].sum()
coupon_gbv      = df[df["is_coupon"]]["GBV"].sum()
coupon_gbv_pct  = coupon_gbv / total_gbv * 100
total_gp        = df["GP"].sum()
coupon_gp       = df[df["is_coupon"]]["GP"].sum()
coupon_gp_pct   = coupon_gp / total_gp * 100 if total_gp else 0
gp_margin_all   = total_gp / total_gbv * 100 if total_gbv else 0
gp_margin_coupon   = coupon_gp / coupon_gbv * 100 if coupon_gbv else 0
gp_margin_no_coupon = (total_gp - coupon_gp) / (total_gbv - coupon_gbv) * 100 if (total_gbv - coupon_gbv) else 0
total_coupon_cards = int(df_metric["n_coupon_card"].sum())
overall_success    = df_metric[df_metric["n_coupon_card"] > 0]["success_rate"].mean()

# 2. YoY
years = sorted(df['yr'].unique().tolist())
yoy = df.groupby(["yr", "is_coupon"])[num_cols].sum().reset_index()
yr_total  = df.groupby("yr")[["Gross_orders", "GBV", "GP"]].sum()
yr_coupon = df[df["is_coupon"]].groupby("yr")[["Gross_orders", "GBV", "GP"]].sum()
yr_pen = (yr_coupon / yr_total * 100).reset_index()
yr_pen.columns = ["yr", "order_pct", "gbv_pct", "gp_pct"]
yr_pen_dict = yr_pen.set_index("yr").to_dict()
yoy_coupon_idx = yoy[yoy["is_coupon"] == True].set_index("yr")
yoy_gp = yoy.copy()
yoy_gp["gp_margin"] = yoy_gp["GP"] / yoy_gp["GBV"].replace(0, np.nan) * 100
coupon_gp_margin_by_yr   = yoy_gp[yoy_gp["is_coupon"] == True].set_index("yr")["gp_margin"]
no_coupon_gp_margin_by_yr = yoy_gp[yoy_gp["is_coupon"] == False].set_index("yr")["gp_margin"]

# YoY by coupon_type
yoy_type = df.groupby(["yr", "coupon_type", "is_coupon"])[num_cols].sum().reset_index()

# 3. Financial (gp_compare)
gp_compare = df.groupby("is_coupon").apply(lambda x: pd.Series({
    "GP_margin": x["GP"].sum() / x["GBV"].sum() * 100 if x["GBV"].sum() else 0,
    "Net_order_rate": x["Net_orders"].sum() / x["Gross_orders"].sum() * 100 if x["Gross_orders"].sum() else 0,
    "NBV_GBV_ratio": x["NBV"].sum() / x["GBV"].sum() * 100 if x["GBV"].sum() else 0,
    "Avg_GBV_per_order": x["GBV"].sum() / x["Gross_orders"].sum() if x["Gross_orders"].sum() else 0,
}), include_groups=False).reset_index()

gp_c  = safe(gp_compare.loc[gp_compare['is_coupon']==True,  'GP_margin'].values[0]   if len(gp_compare[gp_compare['is_coupon']==True])  else 0)
gp_nc = safe(gp_compare.loc[gp_compare['is_coupon']==False, 'GP_margin'].values[0]   if len(gp_compare[gp_compare['is_coupon']==False]) else 0)
nr_c  = safe(gp_compare.loc[gp_compare['is_coupon']==True,  'Net_order_rate'].values[0] if len(gp_compare[gp_compare['is_coupon']==True])  else 0)
nr_nc = safe(gp_compare.loc[gp_compare['is_coupon']==False, 'Net_order_rate'].values[0] if len(gp_compare[gp_compare['is_coupon']==False]) else 0)
nbv_c  = safe(gp_compare.loc[gp_compare['is_coupon']==True,  'NBV_GBV_ratio'].values[0] if len(gp_compare[gp_compare['is_coupon']==True])  else 0)
nbv_nc = safe(gp_compare.loc[gp_compare['is_coupon']==False, 'NBV_GBV_ratio'].values[0] if len(gp_compare[gp_compare['is_coupon']==False]) else 0)
avg_gbv_c  = safe(gp_compare.loc[gp_compare['is_coupon']==True,  'Avg_GBV_per_order'].values[0] if len(gp_compare[gp_compare['is_coupon']==True])  else 0)
avg_gbv_nc = safe(gp_compare.loc[gp_compare['is_coupon']==False, 'Avg_GBV_per_order'].values[0] if len(gp_compare[gp_compare['is_coupon']==False]) else 0)
max_avg_gbv = max(avg_gbv_c, avg_gbv_nc, 1)

# Financial by coupon_type
fin_by_type = df.groupby(["coupon_type", "is_coupon"]).apply(lambda x: pd.Series({
    "GP_margin": x["GP"].sum() / x["GBV"].sum() * 100 if x["GBV"].sum() else 0,
    "Net_order_rate": x["Net_orders"].sum() / x["Gross_orders"].sum() * 100 if x["Gross_orders"].sum() else 0,
    "NBV_GBV_ratio": x["NBV"].sum() / x["GBV"].sum() * 100 if x["GBV"].sum() else 0,
}), include_groups=False).reset_index()

# 4. Cancellation
cancel = df.groupby("is_coupon").agg(gross=("Gross_orders","sum"), net=("Net_orders","sum")).reset_index()
cancel["net_rate"]    = cancel["net"] / cancel["gross"] * 100
cancel["cancel_rate"] = 100 - cancel["net_rate"]
cancel["label"] = cancel["is_coupon"].map({True:"Coupon Applied", False:"No Coupon"})
nr_coupon_overall   = float(cancel.loc[cancel["is_coupon"]==True,  "net_rate"].values[0])
nr_nocoupon_overall = float(cancel.loc[cancel["is_coupon"]==False, "net_rate"].values[0])

seg_cancel = df.groupby(["industry_segment","is_coupon"]).agg(gross=("Gross_orders","sum"),net=("Net_orders","sum")).reset_index()
seg_cancel["net_rate"] = seg_cancel["net"] / seg_cancel["gross"].replace(0, np.nan) * 100
seg_pivot = seg_cancel.pivot(index="industry_segment", columns="is_coupon", values="net_rate").reset_index()
seg_pivot.columns = ["industry_segment","net_rate_no_coupon","net_rate_coupon"]
seg_pivot["delta"] = seg_pivot["net_rate_coupon"] - seg_pivot["net_rate_no_coupon"]
seg_pivot = seg_pivot.dropna(subset=["net_rate_coupon","net_rate_no_coupon"])
seg_pivot_sorted = seg_pivot.sort_values("delta", ascending=False)

# Cancellation by coupon_type
cancel_by_type = df.groupby(["coupon_type","is_coupon"]).agg(gross=("Gross_orders","sum"),net=("Net_orders","sum")).reset_index()
cancel_by_type["net_rate"] = cancel_by_type["net"] / cancel_by_type["gross"].replace(0,np.nan) * 100

# 5. Industry Segment
seg_total  = df.groupby("industry_segment")[["Gross_orders","GBV","GP"]].sum().reset_index()
seg_total.columns = ["industry_segment","total_orders","total_gbv","total_gp"]
seg_coupon = df[df["is_coupon"]].groupby("industry_segment")[["Gross_orders","GBV","GP"]].sum().reset_index()
seg_coupon.columns = ["industry_segment","coupon_orders","coupon_gbv","coupon_gp"]
seg_pen = seg_total.merge(seg_coupon, on="industry_segment", how="left").fillna(0)
seg_pen["coupon_order_pct"] = seg_pen["coupon_orders"] / seg_pen["total_orders"].replace(0,np.nan) * 100
seg_pen["coupon_gbv_pct"]   = seg_pen["coupon_gbv"] / seg_pen["total_gbv"].replace(0,np.nan) * 100
_gp_all    = df.groupby("industry_segment")["GP"].sum() / df.groupby("industry_segment")["GBV"].sum().replace(0,np.nan) * 100
_gp_coupon = df[df["is_coupon"]].groupby("industry_segment")["GP"].sum() / \
             df[df["is_coupon"]].groupby("industry_segment")["GBV"].sum().replace(0,np.nan) * 100
seg_pen["gp_margin_all"]    = seg_pen["industry_segment"].map(_gp_all)
seg_pen["gp_margin_coupon"] = seg_pen["industry_segment"].map(_gp_coupon)
seg_pen = seg_pen.sort_values("total_gbv", ascending=False)
seg_can_delta = df.groupby(["industry_segment","is_coupon"]).agg(gross=("Gross_orders","sum"),net=("Net_orders","sum")).reset_index()
seg_can_delta["net_rate"] = seg_can_delta["net"] / seg_can_delta["gross"].replace(0,np.nan) * 100
seg_can_piv = seg_can_delta.pivot(index="industry_segment", columns="is_coupon", values="net_rate").reset_index()
seg_can_piv.columns = ["industry_segment","nr_no_coupon","nr_coupon"]
seg_can_piv["nr_delta"] = seg_can_piv["nr_coupon"] - seg_can_piv["nr_no_coupon"]
seg_pen = seg_pen.merge(seg_can_piv[["industry_segment","nr_coupon","nr_no_coupon","nr_delta"]], on="industry_segment", how="left")

# 6. Device
device = df.groupby(["cbe_purchase_device_type","is_coupon"])[["Gross_orders","GBV","GP"]].sum().reset_index()
device_pivot = device.pivot_table(index="cbe_purchase_device_type", columns="is_coupon",
                                   values=["Gross_orders","GBV","GP"], aggfunc="sum").fillna(0)
device_pivot.columns = ["_".join([str(c) for c in col]) for col in device_pivot.columns]
device_pivot = device_pivot.reset_index()
device_pivot["coupon_pct"] = device_pivot.get("Gross_orders_True",0) / \
    (device_pivot.get("Gross_orders_True",0) + device_pivot.get("Gross_orders_False",0)).replace(0,np.nan) * 100

device_by_type = df.groupby(["cbe_purchase_device_type","coupon_type","is_coupon"])["Gross_orders"].sum().reset_index()

# 7. Payment & Refund
pay   = df.groupby(["payment_type","is_coupon"])[["Gross_orders","GBV","GP"]].sum().reset_index()
refund = df.groupby(["refundable_indicator","is_coupon"])[["Gross_orders","Net_orders","GBV","GP"]].sum().reset_index()
refund["net_rate"] = refund["Net_orders"] / refund["Gross_orders"].replace(0,np.nan) * 100

pay_by_type = df.groupby(["payment_type","coupon_type","is_coupon"])[["GBV"]].sum().reset_index()

# 8. Coupon Metric
seg_metric_grp = df_metric.groupby("industry_segment").agg(
    n_coupon_card=("n_coupon_card","sum"),
    success_rate=("success_rate","mean"),
    failure_rate=("failure_rate","mean"),
    app_rate=("app_rate","mean"),
).reset_index().sort_values("n_coupon_card", ascending=False)

metric_by_type = df_metric.groupby("coupon_type").agg(
    n_coupon_card=("n_coupon_card","sum"),
    success_rate=("success_rate","mean"),
    failure_rate=("failure_rate","mean"),
).reset_index()

top_partners_metric = df_metric[df_metric["n_coupon_card"] > 0].sort_values("n_coupon_card", ascending=False).head(30)

# 9. Partner-level
order_partner = df.groupby("partner_upper").agg(
    total_orders=("Gross_orders","sum"),
    coupon_orders=("Gross_orders", lambda x: x[df.loc[x.index,"is_coupon"]].sum()),
    total_gbv=("GBV","sum"),
    coupon_gbv=("GBV", lambda x: x[df.loc[x.index,"is_coupon"]].sum()),
    total_gp=("GP","sum"),
    coupon_gp=("GP", lambda x: x[df.loc[x.index,"is_coupon"]].sum()),
).reset_index()
order_partner["gp_margin"]          = order_partner["total_gp"] / order_partner["total_gbv"].replace(0,np.nan) * 100
order_partner["coupon_penetration"] = order_partner["coupon_orders"] / order_partner["total_orders"].replace(0,np.nan) * 100
order_partner["coupon_type"] = order_partner["partner_upper"].map(PARTNER_DIM)

merged = order_partner.merge(
    df_metric[["partner_upper","n_coupon_card","app_rate","success_rate","failure_rate","industry_segment","coupon_type"]],
    on="partner_upper", how="inner", suffixes=("","_m")
)
merged["coupon_type"] = merged["coupon_type"].fillna(merged.get("coupon_type_m", ""))
merged = merged[merged["n_coupon_card"] > 0]

merged["is_high_failure"] = merged["failure_rate"] > 0.6
merged["is_high_gbv"]     = merged["total_gbv"] > merged["total_gbv"].quantile(0.75)
quadrant      = merged[merged["is_high_failure"] & merged["is_high_gbv"]].sort_values("total_gbv", ascending=False).head(20)
top_performers = merged[merged["success_rate"] > 0.5].sort_values("total_gbv", ascending=False).head(20)

neg_gp_coupon = df[df["is_coupon"] & (df["GP"] < 0)].groupby("partner_upper").agg(
    coupon_orders=("Gross_orders","sum"), coupon_gp=("GP","sum"), coupon_gbv=("GBV","sum")
).reset_index()
neg_gp_coupon["coupon_type"] = neg_gp_coupon["partner_upper"].map(PARTNER_DIM)
neg_gp_coupon = neg_gp_coupon.sort_values("coupon_gp").head(20)

# ── Build HTML ─────────────────────────────────────────────────────────────────
html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Priority Coupon Partner Deep Dive — 2025–2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
  :root { --bg:#F8FAFC; --card:#fff; --border:#E2E8F0; --text:#1E293B; --muted:#64748B;
          --blue:#2563EB; --gray:#94A3B8; --green:#16A34A; --red:#DC2626; --yellow:#D97706; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:var(--bg); color:var(--text); font-size:14px; line-height:1.6; }
  .header { background:#1E293B; color:white; padding:28px 40px; }
  .header h1 { font-size:22px; font-weight:700; }
  .header p { opacity:.7; font-size:13px; margin-top:4px; }
  .container { max-width:1280px; margin:0 auto; padding:24px 40px; }
  .section { margin-bottom:40px; }
  .section-title { font-size:16px; font-weight:700; border-left:4px solid var(--blue);
                   padding-left:10px; margin-bottom:16px; }
  .section-subtitle { font-size:12px; color:var(--muted); margin-bottom:14px; margin-top:-10px; }
  .kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:28px; }
  .kpi-grid-3 { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:20px; }
  .kpi-card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:16px 18px; }
  .kpi-label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }
  .kpi-value { font-size:22px; font-weight:700; margin:4px 0 2px; }
  .kpi-sub { font-size:11px; color:var(--muted); }
  .charts-row { display:grid; gap:16px; }
  .col2 { grid-template-columns:1fr 1fr; }
  .col3 { grid-template-columns:1fr 1fr 1fr; }
  .chart-card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:18px; }
  .chart-card h3 { font-size:13px; font-weight:600; margin-bottom:12px; }
  canvas { max-height:280px; }
  .note { font-size:11px; color:var(--muted); margin-top:8px; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th { background:var(--bg); color:var(--muted); font-weight:600; padding:7px 8px;
       text-align:left; border-bottom:2px solid var(--border); white-space:nowrap; }
  td { padding:6px 8px; border-bottom:1px solid var(--border); }
  tr:hover td { background:#F1F5F9; }
  .badge { display:inline-block; padding:2px 7px; border-radius:99px; font-size:10px; font-weight:600; }
  .pub { background:#DBEAFE; color:var(--blue); }
  .priv { background:#DCFCE7; color:var(--green); }
  .uniq { background:#FEF3C7; color:var(--yellow); }
  .badge-blue { background:#DBEAFE; color:var(--blue); }
  .badge-green { background:#DCFCE7; color:var(--green); }
  .badge-red { background:#FEE2E2; color:var(--red); }
  .badge-yellow { background:#FEF3C7; color:var(--yellow); }
  .insight-box { background:#EFF6FF; border-left:4px solid var(--blue); border-radius:0 8px 8px 0;
                 padding:12px 16px; margin-bottom:16px; font-size:13px; line-height:1.7; }
  .insight-box strong { color:var(--blue); }
  .divider { border:none; border-top:1px solid var(--border); margin:32px 0; }
  .toc { background:var(--card); border:1px solid var(--border); border-radius:10px;
         padding:16px 20px; margin-bottom:28px; }
  .toc h2 { font-size:13px; font-weight:600; margin-bottom:10px; }
  .toc ol { padding-left:20px; }
  .toc li { margin:4px 0; }
  .toc a { color:var(--blue); text-decoration:none; font-size:13px; }
  .toc a:hover { text-decoration:underline; }
  .mt16 { margin-top:16px; }
</style>
</head>
<body>
<div class="header">
  <h1>Priority Coupon Partner Deep Dive</h1>
  <p>77 partners from <code>insur_analytics.coupon_partner_dim</code> &nbsp;·&nbsp;
     <span style="background:#3B82F6;border-radius:4px;padding:1px 7px;font-size:11px">54 Public</span>
     <span style="background:#22C55E;border-radius:4px;padding:1px 7px;font-size:11px">22 Private</span>
     <span style="background:#F59E0B;border-radius:4px;padding:1px 7px;font-size:11px">1 Uniqodo</span>
     &nbsp;·&nbsp; Full Year 2025 + Jan–May 2026</p>
</div>
<div class="container">

<div class="toc">
  <h2>Table of Contents</h2>
  <ol>
    <li><a href="#overview">Overview — Scale & Key KPIs</a></li>
    <li><a href="#yoy">Year-over-Year — Coupon Penetration Trend</a></li>
    <li><a href="#financial">Financial Impact — GP Margin, Net Order Rate & NBV/GBV</a></li>
    <li><a href="#cancel">Cancellation & Retention — Does Coupon Reduce Cancellations?</a></li>
    <li><a href="#segment">Industry Segment Breakdown</a></li>
    <li><a href="#device">Device Analysis — Mobile vs Browser</a></li>
    <li><a href="#payment">Payment & Refund</a></li>
    <li><a href="#metric">Coupon Metric — Application, Success & Failure Rates</a></li>
    <li><a href="#partner">Partner-Level — High-Value, At-Risk & Negative GP</a></li>
  </ol>
</div>
"""

# ── SECTION 1: OVERVIEW ────────────────────────────────────────────────────────
html += f"""
<div class="section" id="overview">
  <div class="section-title">1. Overview — Scale & Key KPIs</div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Total Gross Orders</div>
      <div class="kpi-value">{fmt(total_orders)}</div>
      <div class="kpi-sub">77 priority partners, 2025–2026</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Coupon Order Share</div>
      <div class="kpi-value" style="color:var(--blue)">{pct(coupon_order_pct)}</div>
      <div class="kpi-sub">{fmt(coupon_orders)} coupon orders</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Coupon GBV Share</div>
      <div class="kpi-value" style="color:var(--blue)">{pct(coupon_gbv_pct)}</div>
      <div class="kpi-sub">${fmt(coupon_gbv/1e6, 1)}M coupon GBV</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">GP Margin — Coupon vs Overall</div>
      <div class="kpi-value" style="color:{'var(--red)' if gp_margin_coupon < gp_margin_all else 'var(--green)'}">{pct(gp_margin_coupon)}</div>
      <div class="kpi-sub">Overall {pct(gp_margin_all)} | No Coupon {pct(gp_margin_no_coupon)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total GBV</div>
      <div class="kpi-value">${fmt(total_gbv/1e6, 1)}M</div>
      <div class="kpi-sub">NBV: ${fmt(df['NBV'].sum()/1e6, 1)}M</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total GP</div>
      <div class="kpi-value">${fmt(total_gp/1e6, 1)}M</div>
      <div class="kpi-sub">Coupon GP: ${fmt(coupon_gp/1e6, 1)}M ({pct(coupon_gp_pct)})</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Coupon Card Uses</div>
      <div class="kpi-value" style="color:var(--blue)">{fmt(total_coupon_cards)}</div>
      <div class="kpi-sub">Avg Success Rate {pct(overall_success*100 if overall_success else 0)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Partners Tracked</div>
      <div class="kpi-value">77</div>
      <div class="kpi-sub"><span class="badge pub">54 Public</span> <span class="badge priv">22 Private</span> <span class="badge uniq">1 Uniqodo</span></div>
    </div>
  </div>

  <div class="insight-box">
    <strong>Key Insight:</strong>
    These 77 priority partners account for coupon order share of <strong>{pct(coupon_order_pct)}</strong>
    and <strong>{pct(coupon_gbv_pct)}</strong> of GBV.
    Coupon GP Margin is <strong>{pct(gp_margin_coupon)}</strong>,
    {'below' if gp_margin_coupon < gp_margin_no_coupon else 'above'} non-coupon
    ({pct(gp_margin_no_coupon)}), a gap of <strong>{pct(abs(gp_margin_coupon-gp_margin_no_coupon))}</strong>.
  </div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon vs No Coupon — Orders / GBV / GP Breakdown</h3>
      <canvas id="c_overall_bar"></canvas>
    </div>
    <div class="chart-card">
      <h3>GP Margin Comparison</h3>
      <canvas id="c_gp_margin"></canvas>
      <p class="note">⚠️ GP Margin = GP / GBV</p>
    </div>
  </div>

  <div class="charts-row col3 mt16">
    <div class="chart-card">
      <h3>Total GBV by Partner Type ($M)</h3>
      <canvas id="c_type_gbv"></canvas>
    </div>
    <div class="chart-card">
      <h3>Coupon Order Share by Type (%)</h3>
      <canvas id="c_type_coupon_pct"></canvas>
    </div>
    <div class="chart-card">
      <h3>GP Margin: Overall vs Coupon by Type (%)</h3>
      <canvas id="c_type_gp"></canvas>
      <p class="note">⚠️ GP Margin = GP / GBV</p>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 2: YoY ────────────────────────────────────────────────────────────
html += f"""
<div class="section" id="yoy">
  <div class="section-title">2. Year-over-Year — Coupon Penetration Trend</div>
  <div class="section-subtitle">Note: 2026 covers Jan–May only</div>

  <div class="charts-row col3">
    <div class="chart-card">
      <h3>Coupon Order Penetration (%)</h3>
      <canvas id="c_yoy_order_pct"></canvas>
      <p class="note">⚠️ Penetration = Coupon Gross_orders / All Gross_orders</p>
    </div>
    <div class="chart-card">
      <h3>Coupon GBV Penetration (%)</h3>
      <canvas id="c_yoy_gbv_pct"></canvas>
    </div>
    <div class="chart-card">
      <h3>Coupon GP Penetration (%)</h3>
      <canvas id="c_yoy_gp_pct"></canvas>
    </div>
  </div>

  <div class="charts-row col2 mt16">
    <div class="chart-card">
      <h3>2025 vs 2026 Absolute Metrics (Coupon Applied)</h3>
      <canvas id="c_yoy_abs"></canvas>
    </div>
    <div class="chart-card">
      <h3>GP Margin Trend — Coupon vs No Coupon (%)</h3>
      <canvas id="c_yoy_gp_margin"></canvas>
    </div>
  </div>

  <div class="charts-row col2 mt16">
    <div class="chart-card">
      <h3>GBV by Partner Type & Year ($M)</h3>
      <canvas id="c_yoy_type_gbv"></canvas>
    </div>
    <div class="chart-card">
      <h3>Coupon GP Margin by Partner Type & Year (%)</h3>
      <canvas id="c_yoy_type_gp"></canvas>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 3: FINANCIAL ──────────────────────────────────────────────────────
html += f"""
<div class="section" id="financial">
  <div class="section-title">3. Financial Impact — GP Margin, Net Order Rate & NBV/GBV</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Key Financial Metrics Comparison (Coupon vs No Coupon)</h3>
      <canvas id="c_fin_radar"></canvas>
      <p class="note">All radar dimensions normalised to 0–100</p>
    </div>
    <div class="chart-card">
      <h3>Net Order Rate & NBV/GBV Ratio</h3>
      <canvas id="c_fin_bar"></canvas>
      <p class="note">⚠️ Net Order Rate = Net_orders / Gross_orders</p>
    </div>
  </div>

  <div class="insight-box mt16">
    <strong>Interpretation:</strong>
    Net Order Rate — Coupon: <strong>{pct(nr_c)}</strong> vs No Coupon: <strong>{pct(nr_nc)}</strong>.
    Avg GBV/order — Coupon: <strong>${fmt(avg_gbv_c, 0)}</strong> vs No Coupon: <strong>${fmt(avg_gbv_nc, 0)}</strong>.
  </div>

  <div class="charts-row col3 mt16">
    <div class="chart-card">
      <h3>GP Margin by Type: Coupon vs No Coupon (%)</h3>
      <canvas id="c_type_fin_gp"></canvas>
      <p class="note">⚠️ GP Margin = GP / GBV</p>
    </div>
    <div class="chart-card">
      <h3>Net Order Rate by Type: Coupon vs No Coupon (%)</h3>
      <canvas id="c_type_fin_nor"></canvas>
    </div>
    <div class="chart-card">
      <h3>NBV/GBV Ratio by Type: Coupon vs No Coupon (%)</h3>
      <canvas id="c_type_fin_nbv"></canvas>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 4: CANCELLATION ───────────────────────────────────────────────────
html += f"""
<div class="section" id="cancel">
  <div class="section-title">4. Cancellation & Retention — Does Coupon Reduce Cancellations?</div>
  <div class="section-subtitle">Net Order Rate = Net Orders / Gross Orders — higher means fewer cancellations</div>

  <div class="kpi-grid-3">
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
      <div class="kpi-value" style="color:{'var(--green)' if nr_coupon_overall > nr_nocoupon_overall else 'var(--red)'}">
        {'+' if nr_coupon_overall > nr_nocoupon_overall else ''}{nr_coupon_overall - nr_nocoupon_overall:.1f}pp
      </div>
      <div class="kpi-sub">Coupon vs No Coupon</div>
    </div>
  </div>

  <div class="insight-box">
    <strong>Key Finding:</strong>
    Coupon orders have Net Order Rate <strong>{nr_coupon_overall:.1f}%</strong>
    vs <strong>{nr_nocoupon_overall:.1f}%</strong> non-coupon —
    <strong>+{nr_coupon_overall - nr_nocoupon_overall:.1f}pp</strong> retention uplift.
    Customers using coupons are more committed to completing their booking.
  </div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Net Order Rate: Coupon vs No Coupon (Overall)</h3>
      <canvas id="c_cancel_overall"></canvas>
      <p class="note">⚠️ Net Order Rate = Net_orders / Gross_orders</p>
    </div>
    <div class="chart-card">
      <h3>Net Order Rate Delta by Segment (Coupon − No Coupon, pp)</h3>
      <p class="note" style="margin-bottom:8px">Green = coupon reduces cancellations</p>
      <canvas id="c_cancel_seg" style="max-height:380px"></canvas>
    </div>
  </div>

  <div class="charts-row col2 mt16">
    <div class="chart-card">
      <h3>Net Order Rate by Partner Type — Coupon (%)</h3>
      <canvas id="c_cancel_type_nor"></canvas>
    </div>
    <div class="chart-card">
      <h3>Retention Uplift by Partner Type (pp)</h3>
      <canvas id="c_cancel_type_delta"></canvas>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 5: SEGMENT ────────────────────────────────────────────────────────
html += """
<div class="section" id="segment">
  <div class="section-title">5. Industry Segment Breakdown</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon Order Penetration vs Total GBV by Segment</h3>
      <canvas id="c_seg_pen"></canvas>
    </div>
    <div class="chart-card">
      <h3>GP Margin by Segment: Coupon vs Overall</h3>
      <canvas id="c_seg_gp"></canvas>
    </div>
  </div>

  <div class="mt16">
    <div class="chart-card">
      <h3>Industry Segment Detail Table</h3>
      <table style="font-size:11px">
        <thead>
          <tr>
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
    gp_diff = (row.get("gp_margin_coupon", 0) or 0) - (row.get("gp_margin_all", 0) or 0)
    nr_delta = row.get("nr_delta", float("nan"))
    nr_delta_fmt = f"{'+' if nr_delta >= 0 else ''}{nr_delta:.1f}pp" if nr_delta == nr_delta else "N/A"
    html += f"""
          <tr style="font-size:11px">
            <td style="padding:5px 7px">{row['industry_segment']}</td>
            <td style="padding:5px 7px">${fmt(row['total_gbv']/1e3, 0)}K</td>
            <td style="padding:5px 7px">{pct(row.get('coupon_gbv_pct',0))}</td>
            <td style="padding:5px 7px">{pct(row.get('coupon_order_pct',0))}</td>
            <td style="padding:5px 7px">{pct(row.get('gp_margin_all',0))}</td>
            <td style="padding:5px 7px">{pct(row.get('gp_margin_coupon',0))}</td>
            <td style="padding:5px 7px"><span class="badge {'badge-green' if gp_diff >= 0 else 'badge-red'}">{'+' if gp_diff >= 0 else ''}{gp_diff:.1f}%</span></td>
            <td style="padding:5px 7px">{pct(row.get('nr_coupon',0))}</td>
            <td style="padding:5px 7px">{pct(row.get('nr_no_coupon',0))}</td>
            <td style="padding:5px 7px"><span class="badge {'badge-green' if nr_delta == nr_delta and nr_delta >= 0 else 'badge-red'}">{nr_delta_fmt}</span></td>
          </tr>"""
html += """
        </tbody>
      </table>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 6: DEVICE ─────────────────────────────────────────────────────────
html += """
<div class="section" id="device">
  <div class="section-title">6. Device Analysis — Mobile vs Browser</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon Order Share by Device (%)</h3>
      <canvas id="c_device_pct"></canvas>
    </div>
    <div class="chart-card">
      <h3>GBV by Device: Coupon vs No Coupon</h3>
      <canvas id="c_device_gbv"></canvas>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 7: PAYMENT ────────────────────────────────────────────────────────
html += """
<div class="section" id="payment">
  <div class="section-title">7. Payment & Refund Analysis</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Merchant vs Agency — Coupon GBV Distribution</h3>
      <canvas id="c_payment"></canvas>
    </div>
    <div class="chart-card">
      <h3>Refundable Flag — Net Order Rate Comparison</h3>
      <canvas id="c_refund"></canvas>
    </div>
  </div>

  <div class="charts-row col2 mt16">
    <div class="chart-card">
      <h3>Coupon GBV by Payment Type & Partner Type ($K)</h3>
      <canvas id="c_pay_type"></canvas>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 8: METRIC ─────────────────────────────────────────────────────────
html += """
<div class="section" id="metric">
  <div class="section-title">8. Coupon Metric — Application, Success & Failure Rates</div>
  <div class="section-subtitle">Source: Coupon Metric file — filtered to 77 priority partners</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>Coupon Card Volume by Segment</h3>
      <canvas id="c_metric_vol"></canvas>
    </div>
    <div class="chart-card">
      <h3>Success vs Failure Rate by Segment (%)</h3>
      <canvas id="c_metric_rate"></canvas>
    </div>
  </div>

  <div class="charts-row col2 mt16">
    <div class="chart-card">
      <h3>Coupon Card Volume by Partner Type</h3>
      <canvas id="c_metric_type_vol"></canvas>
    </div>
    <div class="chart-card">
      <h3>Success vs Failure Rate by Partner Type (%)</h3>
      <canvas id="c_metric_type_rate"></canvas>
    </div>
  </div>

  <div class="mt16">
    <div class="chart-card">
      <h3>Top 30 Partners by Coupon Card Volume</h3>
      <canvas id="c_top_partners_metric" style="max-height:420px"></canvas>
    </div>
  </div>

  <div class="mt16">
    <div class="chart-card">
      <h3>Segment Summary Table</h3>
      <table>
        <thead>
          <tr><th>Industry Segment</th><th>Coupon Card Uses</th><th>App Rate</th><th>Success Rate</th><th>Failure Rate</th></tr>
        </thead>
        <tbody>
"""
for _, row in seg_metric_grp.iterrows():
    fail = (row.get("failure_rate") or 0)
    fc = "badge-red" if fail > 0.55 else "badge-yellow" if fail > 0.4 else "badge-green"
    html += f"""
          <tr>
            <td>{row['industry_segment']}</td>
            <td>{fmt(row['n_coupon_card'])}</td>
            <td>{pct((row.get('app_rate') or 0)*100)}</td>
            <td>{pct((row.get('success_rate') or 0)*100)}</td>
            <td><span class="badge {fc}">{pct(fail*100)}</span></td>
          </tr>"""
html += """
        </tbody>
      </table>
    </div>
  </div>
</div>

<hr class="divider">
"""

# ── SECTION 9: PARTNER ────────────────────────────────────────────────────────
html += """
<div class="section" id="partner">
  <div class="section-title">9. Partner-Level — High-Value, At-Risk & Negative GP</div>

  <div class="charts-row col2">
    <div class="chart-card">
      <h3>High GBV + High Failure Rate (Failure > 60% & GBV Top 25%)</h3>
      <p class="note" style="margin-bottom:8px">Optimization opportunity — high attempt failure</p>
      <table>
        <thead>
          <tr><th>Partner</th><th>Type</th><th>Segment</th><th>Total GBV</th><th>Failure Rate</th><th>Card Uses</th></tr>
        </thead>
        <tbody>
"""
for _, row in quadrant.iterrows():
    t = row.get('coupon_type','')
    bc = BADGE_CLASS.get(t,'pub')
    html += f"""
          <tr>
            <td>{row['partner_upper']}</td>
            <td><span class="badge {bc}">{t}</span></td>
            <td><span class="badge badge-blue">{row.get('industry_segment','')}</span></td>
            <td>${fmt(row['total_gbv']/1e3, 0)}K</td>
            <td><span class="badge badge-red">{pct((row.get('failure_rate') or 0)*100)}</span></td>
            <td>{fmt(row.get('n_coupon_card',0))}</td>
          </tr>"""
html += """
        </tbody>
      </table>
    </div>
    <div class="chart-card">
      <h3>High Success Rate Partners (Success > 50%, ranked by GBV)</h3>
      <p class="note" style="margin-bottom:8px">Effective coupon execution</p>
      <table>
        <thead>
          <tr><th>Partner</th><th>Type</th><th>Segment</th><th>Total GBV</th><th>Success Rate</th><th>GP Margin</th></tr>
        </thead>
        <tbody>
"""
for _, row in top_performers.iterrows():
    t = row.get('coupon_type','')
    bc = BADGE_CLASS.get(t,'pub')
    html += f"""
          <tr>
            <td>{row['partner_upper']}</td>
            <td><span class="badge {bc}">{t}</span></td>
            <td><span class="badge badge-blue">{row.get('industry_segment','')}</span></td>
            <td>${fmt(row['total_gbv']/1e3, 0)}K</td>
            <td><span class="badge badge-green">{pct((row.get('success_rate') or 0)*100)}</span></td>
            <td>{pct(row.get('gp_margin',0))}</td>
          </tr>"""
html += """
        </tbody>
      </table>
    </div>
  </div>

  <div class="mt16">
    <div class="chart-card">
      <h3>Partners with Negative Coupon GP (Top 20 Losses)</h3>
      <p class="note" style="margin-bottom:8px">Discount strategy needs review</p>
      <table>
        <thead>
          <tr><th>Partner</th><th>Type</th><th>Coupon Orders</th><th>Coupon GBV</th><th>Coupon GP</th><th>GP / Order</th></tr>
        </thead>
        <tbody>
"""
for _, row in neg_gp_coupon.iterrows():
    t = row.get('coupon_type','')
    bc = BADGE_CLASS.get(str(t),'pub')
    gp_per_order = row["coupon_gp"] / row["coupon_orders"] if row["coupon_orders"] > 0 else 0
    html += f"""
          <tr>
            <td>{row['partner_upper']}</td>
            <td><span class="badge {bc}">{t}</span></td>
            <td>{fmt(row['coupon_orders'])}</td>
            <td>${fmt(row['coupon_gbv'],0)}</td>
            <td style="color:var(--red)"><strong>${fmt(row['coupon_gp'],0)}</strong></td>
            <td style="color:var(--red)">${fmt(gp_per_order,0)}</td>
          </tr>"""
html += """
        </tbody>
      </table>
    </div>
  </div>
</div>

</div><!-- /container -->
"""

# ── CHARTS JS ─────────────────────────────────────────────────────────────────
html += """
<script>
Chart.register(ChartDataLabels);
Chart.defaults.font.family = "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.labels.boxWidth = 12;

const BLUE='#2563EB', GRAY='#94A3B8', GREEN='#16A34A', RED='#DC2626', YELLOW='#D97706';
const PALETTE=['#2563EB','#16A34A','#D97706','#DC2626','#7C3AED','#0891B2','#BE185D'];
const TYPE_C = {Public: '#2563EB', Private: '#16A34A', Uniqodo: '#D97706'};

const DL_BAR = {
  display:true, anchor:'end', align:'top', offset:2, clamp:false, clip:false,
  font:{size:9,weight:'600'}, color:'#334155',
  formatter: v => v==null||v===0?'':(Math.abs(v)>=1000?(v/1000).toFixed(1)+'K':v.toFixed(1))
};
const DL_HBAR = {
  display:true, anchor:'end', align:'right', offset:4, clamp:false, clip:false,
  font:{size:9,weight:'600'}, color:'#334155',
  formatter: v => v==null||v===0?'':(Math.abs(v)>=1000?(v/1000).toFixed(1)+'K':v.toFixed(1))
};

function bar(id, labels, datasets, opts={}) {
  const dlOpts = opts._dl !== false ? {datalabels:DL_BAR} : {datalabels:{display:false}};
  delete opts._dl;
  const ep = opts.plugins||{}; delete opts.plugins;
  new Chart(document.getElementById(id), {
    type:'bar', data:{labels,datasets},
    options:{responsive:true,clip:false,layout:{padding:{top:24}},
      plugins:{legend:{position:'bottom'},...dlOpts,...ep},
      scales:{y:{beginAtZero:true,grid:{color:'#F1F5F9'}},x:{grid:{display:false}}},...opts}
  });
}
function hbar(id, labels, datasets, opts={}) {
  const dlOpts = opts._dl !== false ? {datalabels:DL_HBAR} : {datalabels:{display:false}};
  delete opts._dl;
  const ep = opts.plugins||{}; delete opts.plugins;
  new Chart(document.getElementById(id), {
    type:'bar', data:{labels,datasets},
    options:{indexAxis:'y',responsive:true,clip:false,layout:{padding:{right:50}},
      plugins:{legend:{position:'bottom'},...dlOpts,...ep},
      scales:{x:{beginAtZero:true,grid:{color:'#F1F5F9'}},y:{grid:{display:false},ticks:{font:{size:10}}}},...opts}
  });
}
</script>
<script>
"""

# ── Chart data injection ───────────────────────────────────────────────────────

# Section 1 charts
html += f"""
// Chart 1: overall bar dual y-axis
new Chart(document.getElementById('c_overall_bar'), {{
  type:'bar', data:{{
    labels:['Gross Orders','GBV ($M)','GP ($M)'],
    datasets:[
      {{label:'Coupon Applied',backgroundColor:BLUE,yAxisID:'y',data:[{coupon_orders},null,null],datalabels:{{...DL_BAR}}}},
      {{label:'No Coupon',backgroundColor:GRAY,yAxisID:'y',data:[{total_orders-coupon_orders},null,null],datalabels:{{...DL_BAR}}}},
      {{label:'Coupon Applied (right)',backgroundColor:BLUE,yAxisID:'y1',data:[null,{coupon_gbv/1e6:.2f},{coupon_gp/1e6:.2f}],datalabels:{{...DL_BAR}}}},
      {{label:'No Coupon (right)',backgroundColor:GRAY,yAxisID:'y1',data:[null,{(total_gbv-coupon_gbv)/1e6:.2f},{(total_gp-coupon_gp)/1e6:.2f}],datalabels:{{...DL_BAR}}}},
    ]
  }},
  options:{{responsive:true,clip:false,layout:{{padding:{{top:24}}}},
    plugins:{{legend:{{position:'bottom',labels:{{filter:i=>!i.text.includes('right')}}}},datalabels:DL_BAR}},
    scales:{{y:{{beginAtZero:true,position:'left',title:{{display:true,text:'Orders'}}}},
             y1:{{beginAtZero:true,position:'right',title:{{display:true,text:'$M'}},grid:{{drawOnChartArea:false}}}},
             x:{{grid:{{display:false}}}}}}
  }}
}});

bar('c_gp_margin',['Coupon Applied','No Coupon','Overall'],
  [{{label:'GP Margin (%)',backgroundColor:[BLUE,GRAY,'#7C3AED'],
     data:[{gp_margin_coupon:.2f},{gp_margin_no_coupon:.2f},{gp_margin_all:.2f}]}}],
  {{plugins:{{legend:{{display:false}}}}}});
"""

# Type overview charts
type_summary = df.groupby("coupon_type").agg(
    total_gross=("Gross_orders","sum"), total_gbv=("GBV","sum"), total_gp=("GP","sum"),
).reset_index()
coupon_gross_by_type = df[df["is_coupon"]].groupby("coupon_type")["Gross_orders"].sum()
coupon_gbv_by_type   = df[df["is_coupon"]].groupby("coupon_type")["GBV"].sum()
coupon_gp_by_type    = df[df["is_coupon"]].groupby("coupon_type")["GP"].sum()
type_summary["coupon_pct"]      = type_summary["coupon_type"].map(coupon_gross_by_type) / type_summary["total_gross"] * 100
type_summary["gp_margin_all"]   = type_summary["total_gp"] / type_summary["total_gbv"].replace(0,np.nan) * 100
type_summary["gp_margin_coupon"]= type_summary["coupon_type"].map(coupon_gp_by_type) / type_summary["coupon_type"].map(coupon_gbv_by_type).replace(0,np.nan) * 100
type_summary = type_summary.set_index("coupon_type").reindex(TYPE_ORDER).reset_index().fillna(0)

t_colors = json.dumps([TYPE_COLORS[t] for t in TYPE_ORDER])
html += f"""
bar('c_type_gbv',{json.dumps(TYPE_ORDER)},
  [{{label:'Total GBV ($M)',backgroundColor:{t_colors},data:{jn((type_summary['total_gbv']/1e6).tolist())}}}],
  {{plugins:{{legend:{{display:false}}}}}});
bar('c_type_coupon_pct',{json.dumps(TYPE_ORDER)},
  [{{label:'Coupon Order Share (%)',backgroundColor:{t_colors},data:{jn(type_summary['coupon_pct'].tolist())}}}],
  {{plugins:{{legend:{{display:false}}}}}});
bar('c_type_gp',{json.dumps(TYPE_ORDER)},
  [
    {{label:'Overall GP Margin',backgroundColor:GRAY,data:{jn(type_summary['gp_margin_all'].tolist())}}},
    {{label:'Coupon GP Margin',backgroundColor:BLUE,data:{jn(type_summary['gp_margin_coupon'].tolist())}}},
  ]);
"""

# Section 2: YoY
html += f"""
bar('c_yoy_order_pct',{json.dumps(years)},
  [{{label:'Coupon Order Penetration (%)',backgroundColor:BLUE,
     data:{json.dumps([round(yr_pen_dict['order_pct'].get(y,0),2) for y in years])}}}],
  {{plugins:{{legend:{{display:false}}}}}});
bar('c_yoy_gbv_pct',{json.dumps(years)},
  [{{label:'Coupon GBV Penetration (%)',backgroundColor:GREEN,
     data:{json.dumps([round(yr_pen_dict['gbv_pct'].get(y,0),2) for y in years])}}}],
  {{plugins:{{legend:{{display:false}}}}}});
bar('c_yoy_gp_pct',{json.dumps(years)},
  [{{label:'Coupon GP Penetration (%)',backgroundColor:YELLOW,
     data:{json.dumps([round(yr_pen_dict['gp_pct'].get(y,0),2) for y in years])}}}],
  {{plugins:{{legend:{{display:false}}}}}});

// YoY abs dual axis
new Chart(document.getElementById('c_yoy_abs'),{{
  type:'bar',data:{{labels:{json.dumps(years)},datasets:[
    {{label:'Gross Orders',backgroundColor:BLUE,yAxisID:'y',
      data:{json.dumps([int(yoy_coupon_idx['Gross_orders'].get(y,0)) for y in years])}}},
    {{label:'GBV ($M)',backgroundColor:GREEN,yAxisID:'y1',
      data:{json.dumps([round(float(yoy_coupon_idx['GBV'].get(y,0))/1e6,2) for y in years])}}},
  ]}},
  options:{{responsive:true,clip:false,layout:{{padding:{{top:24}}}},
    plugins:{{legend:{{position:'bottom'}},datalabels:DL_BAR}},
    scales:{{y:{{beginAtZero:true,position:'left',title:{{display:true,text:'Orders'}}}},
             y1:{{beginAtZero:true,position:'right',title:{{display:true,text:'GBV $M'}},grid:{{drawOnChartArea:false}}}},
             x:{{grid:{{display:false}}}}}}
  }}
}});

bar('c_yoy_gp_margin',{json.dumps(years)},
  [
    {{label:'Coupon GP Margin (%)',backgroundColor:BLUE,data:{json.dumps([round(float(coupon_gp_margin_by_yr.get(y,0)),2) for y in years])}}},
    {{label:'No Coupon GP Margin (%)',backgroundColor:GRAY,data:{json.dumps([round(float(no_coupon_gp_margin_by_yr.get(y,0)),2) for y in years])}}},
  ]);
"""

# YoY by type
yoy_type_ds_gbv = []
yoy_type_ds_gp  = []
for t in TYPE_ORDER:
    color = TYPE_COLORS[t]
    gbv_vals, gp_vals = [], []
    for yr in years:
        sub = yoy_type[(yoy_type['yr']==yr) & (yoy_type['coupon_type']==t)]
        gbv_vals.append(round(float(sub['GBV'].sum())/1e6, 2))
        cs = sub[sub['is_coupon']]; cg = cs['GP'].sum(); cb = cs['GBV'].sum()
        gp_vals.append(round(float(cg/cb*100) if cb else 0, 2))
    yoy_type_ds_gbv.append(f"{{label:'{t}',backgroundColor:'{color}',data:{json.dumps(gbv_vals)}}}")
    yoy_type_ds_gp.append(f"{{label:'{t}',backgroundColor:'{color}',data:{json.dumps(gp_vals)}}}")

html += f"""
bar('c_yoy_type_gbv',{json.dumps(years)},[{','.join(yoy_type_ds_gbv)}]);
bar('c_yoy_type_gp', {json.dumps(years)},[{','.join(yoy_type_ds_gp)}]);
"""

# Section 3: Financial
html += f"""
new Chart(document.getElementById('c_fin_radar'),{{
  type:'radar',data:{{
    labels:['GP Margin','Net Order Rate','NBV/GBV Ratio','Avg GBV/Order (norm)'],
    datasets:[
      {{label:'Coupon Applied',borderColor:BLUE,backgroundColor:BLUE+'33',
        data:[{gp_c:.1f},{nr_c:.1f},{nbv_c:.1f},{avg_gbv_c/max_avg_gbv*100:.1f}]}},
      {{label:'No Coupon',borderColor:GRAY,backgroundColor:GRAY+'33',
        data:[{gp_nc:.1f},{nr_nc:.1f},{nbv_nc:.1f},{avg_gbv_nc/max_avg_gbv*100:.1f}]}},
    ]
  }},
  options:{{responsive:true,plugins:{{legend:{{position:'bottom'}},datalabels:{{display:false}}}},
    scales:{{r:{{beginAtZero:true,max:100,ticks:{{stepSize:20}},pointLabels:{{font:{{size:11}}}}}}}}
  }}
}});
bar('c_fin_bar',['Net Order Rate (%)','NBV/GBV Ratio (%)'],
  [
    {{label:'Coupon Applied',backgroundColor:BLUE,data:[{nr_c:.2f},{nbv_c:.2f}]}},
    {{label:'No Coupon',backgroundColor:GRAY,data:[{nr_nc:.2f},{nbv_nc:.2f}]}},
  ]);
"""

# Type financial
fin_type_c  = fin_by_type[fin_by_type['is_coupon']==True].set_index('coupon_type')
fin_type_nc = fin_by_type[fin_by_type['is_coupon']==False].set_index('coupon_type')
t_gp_c   = [safe(fin_type_c.loc[t,'GP_margin']    if t in fin_type_c.index else 0) for t in TYPE_ORDER]
t_gp_nc  = [safe(fin_type_nc.loc[t,'GP_margin']   if t in fin_type_nc.index else 0) for t in TYPE_ORDER]
t_nor_c  = [safe(fin_type_c.loc[t,'Net_order_rate'] if t in fin_type_c.index else 0) for t in TYPE_ORDER]
t_nor_nc = [safe(fin_type_nc.loc[t,'Net_order_rate'] if t in fin_type_nc.index else 0) for t in TYPE_ORDER]
t_nbv_c  = [safe(fin_type_c.loc[t,'NBV_GBV_ratio'] if t in fin_type_c.index else 0) for t in TYPE_ORDER]
t_nbv_nc = [safe(fin_type_nc.loc[t,'NBV_GBV_ratio'] if t in fin_type_nc.index else 0) for t in TYPE_ORDER]

html += f"""
bar('c_type_fin_gp',{json.dumps(TYPE_ORDER)},
  [
    {{label:'Coupon',backgroundColor:BLUE,data:{jn(t_gp_c)}}},
    {{label:'No Coupon',backgroundColor:GRAY,data:{jn(t_gp_nc)}}},
  ]);
bar('c_type_fin_nor',{json.dumps(TYPE_ORDER)},
  [
    {{label:'Coupon',backgroundColor:BLUE,data:{jn(t_nor_c)}}},
    {{label:'No Coupon',backgroundColor:GRAY,data:{jn(t_nor_nc)}}},
  ]);
bar('c_type_fin_nbv',{json.dumps(TYPE_ORDER)},
  [
    {{label:'Coupon',backgroundColor:BLUE,data:{jn(t_nbv_c)}}},
    {{label:'No Coupon',backgroundColor:GRAY,data:{jn(t_nbv_nc)}}},
  ]);
"""

# Section 4: Cancellation
cancel_labels = cancel["label"].tolist()
cancel_net_rates = [round(float(x),1) for x in cancel["net_rate"].tolist()]
seg_delta_labels = seg_pivot_sorted["industry_segment"].tolist()
seg_delta_vals   = [round(float(x),1) for x in seg_pivot_sorted["delta"].tolist()]
seg_delta_colors = json.dumps(["#16A34A" if v>=0 else "#DC2626" for v in seg_delta_vals])

cancel_c_type  = cancel_by_type[cancel_by_type['is_coupon']==True].set_index('coupon_type')
cancel_nc_type = cancel_by_type[cancel_by_type['is_coupon']==False].set_index('coupon_type')
t_nor_coupon = [safe(cancel_c_type.loc[t,'net_rate']  if t in cancel_c_type.index  else 0) for t in TYPE_ORDER]
t_nor_no_c   = [safe(cancel_nc_type.loc[t,'net_rate'] if t in cancel_nc_type.index else 0) for t in TYPE_ORDER]
t_nor_delta  = [round(c-n,2) for c,n in zip(t_nor_coupon, t_nor_no_c)]
t_delta_colors = json.dumps(["#16A34A" if v>=0 else "#DC2626" for v in t_nor_delta])

html += f"""
bar('c_cancel_overall',{json.dumps(cancel_labels)},
  [{{label:'Net Order Rate (%)',backgroundColor:[BLUE,GRAY],data:{json.dumps(cancel_net_rates)}}}],
  {{plugins:{{legend:{{display:false}}}}}});

new Chart(document.getElementById('c_cancel_seg'),{{
  type:'bar',data:{{labels:{json.dumps(seg_delta_labels)},datasets:[{{
    label:'Net Order Rate Delta (pp)',backgroundColor:{seg_delta_colors},
    data:{json.dumps(seg_delta_vals)},
    datalabels:{{...DL_HBAR,formatter:v=>(v>0?'+':'')+v.toFixed(1)}}
  }}]}},
  options:{{indexAxis:'y',responsive:true,clip:false,layout:{{padding:{{right:50}}}},
    plugins:{{legend:{{display:false}},datalabels:DL_HBAR}},
    scales:{{x:{{beginAtZero:false,grid:{{color:'#F1F5F9'}},title:{{display:true,text:'Delta (pp)'}}}},
             y:{{grid:{{display:false}},ticks:{{font:{{size:10}}}}}}}}
  }}
}});

bar('c_cancel_type_nor',{json.dumps(TYPE_ORDER)},
  [
    {{label:'Coupon NOR',backgroundColor:BLUE,data:{jn(t_nor_coupon)}}},
    {{label:'No Coupon NOR',backgroundColor:GRAY,data:{jn(t_nor_no_c)}}},
  ]);

new Chart(document.getElementById('c_cancel_type_delta'),{{
  type:'bar',data:{{labels:{json.dumps(TYPE_ORDER)},datasets:[{{
    label:'Retention Delta (pp)',backgroundColor:{t_delta_colors},data:{jn(t_nor_delta)},
    datalabels:{{...DL_BAR,formatter:v=>(v>0?'+':'')+v.toFixed(1)}}
  }}]}},
  options:{{responsive:true,clip:false,layout:{{padding:{{top:24}}}},
    plugins:{{legend:{{display:false}},datalabels:DL_BAR}},
    scales:{{y:{{beginAtZero:false,grid:{{color:'#F1F5F9'}}}},x:{{grid:{{display:false}}}}}}
  }}
}});
"""

# Section 5: Segment
seg_labels     = seg_pen["industry_segment"].tolist()
seg_pen_vals   = seg_pen["coupon_order_pct"].fillna(0).tolist()
seg_gbv_vals   = (seg_pen["total_gbv"]/1e6).tolist()
seg_gp_all     = seg_pen["gp_margin_all"].fillna(0).tolist()
seg_gp_coupon  = seg_pen["gp_margin_coupon"].fillna(0).tolist()

html += f"""
bar('c_seg_pen',{json.dumps(seg_labels)},
  [
    {{label:'Coupon Order Share (%)',backgroundColor:BLUE,yAxisID:'y',
      data:{json.dumps([round(float(x),2) for x in seg_pen_vals])}}},
    {{label:'Total GBV ($M)',backgroundColor:GRAY+'80',yAxisID:'y1',
      data:{json.dumps([round(float(x),2) for x in seg_gbv_vals])}}},
  ],
  {{_dl:false,scales:{{
    y:{{beginAtZero:true,position:'left',title:{{display:true,text:'Coupon Share (%)'}}}},
    y1:{{beginAtZero:true,position:'right',title:{{display:true,text:'GBV $M'}},grid:{{drawOnChartArea:false}}}},
    x:{{grid:{{display:false}},ticks:{{maxRotation:45,minRotation:30,font:{{size:10}}}}}}
  }}}});

bar('c_seg_gp',{json.dumps(seg_labels)},
  [
    {{label:'Overall GP Margin (%)',backgroundColor:GRAY,data:{json.dumps([round(float(x),2) for x in seg_gp_all])}}},
    {{label:'Coupon GP Margin (%)',backgroundColor:BLUE,data:{json.dumps([round(float(x),2) for x in seg_gp_coupon])}}},
  ],
  {{_dl:false,scales:{{x:{{grid:{{display:false}},ticks:{{maxRotation:45,minRotation:30,font:{{size:10}}}}}}}}}}
);
"""

# Section 6: Device
dev_labels    = device_pivot["cbe_purchase_device_type"].tolist()
dev_coup_pct  = device_pivot["coupon_pct"].fillna(0).tolist()
dev_gbv_c     = device_pivot.get("GBV_True",  pd.Series([0]*len(device_pivot))).fillna(0).tolist()
dev_gbv_nc    = device_pivot.get("GBV_False", pd.Series([0]*len(device_pivot))).fillna(0).tolist()

html += f"""
bar('c_device_pct',{json.dumps(dev_labels)},
  [{{label:'Coupon Order Share (%)',backgroundColor:PALETTE,
     data:{json.dumps([round(float(x),2) for x in dev_coup_pct])}}}],
  {{plugins:{{legend:{{display:false}}}}}});
bar('c_device_gbv',{json.dumps(dev_labels)},
  [
    {{label:'Coupon GBV ($K)',backgroundColor:BLUE,data:{json.dumps([round(float(x)/1e3,1) for x in dev_gbv_c])}}},
    {{label:'No Coupon GBV ($K)',backgroundColor:GRAY,data:{json.dumps([round(float(x)/1e3,1) for x in dev_gbv_nc])}}},
  ]);
"""

# Section 7: Payment & Refund
pay_labels = pay["payment_type"].unique().tolist()
pay_c  = pay[pay["is_coupon"]==True].set_index("payment_type")
pay_nc = pay[pay["is_coupon"]==False].set_index("payment_type")
refund_labels = refund["refundable_indicator"].unique().tolist()
ref_c  = refund[refund["is_coupon"]==True].set_index("refundable_indicator")
ref_nc = refund[refund["is_coupon"]==False].set_index("refundable_indicator")

pay_by_type_coupon = pay_by_type[pay_by_type["is_coupon"]==True]
pay_type_ds = []
for t in TYPE_ORDER:
    sub = pay_by_type_coupon[pay_by_type_coupon["coupon_type"]==t].set_index("payment_type")
    vals = [round(float(sub["GBV"].get(p,0))/1e3, 1) for p in pay_labels]
    pay_type_ds.append(f"{{label:'{t}',backgroundColor:'{TYPE_COLORS[t]}',data:{json.dumps(vals)}}}")

html += f"""
bar('c_payment',{json.dumps(pay_labels)},
  [
    {{label:'Coupon GBV ($K)',backgroundColor:BLUE,data:{json.dumps([round(float(pay_c['GBV'].get(p,0))/1e3,1) for p in pay_labels])}}},
    {{label:'No Coupon GBV ($K)',backgroundColor:GRAY,data:{json.dumps([round(float(pay_nc['GBV'].get(p,0))/1e3,1) for p in pay_labels])}}},
  ]);
bar('c_refund',{json.dumps(refund_labels)},
  [
    {{label:'Coupon NOR (%)',backgroundColor:BLUE,data:{json.dumps([round(float(ref_c['net_rate'].get(r,0)),1) for r in refund_labels])}}},
    {{label:'No Coupon NOR (%)',backgroundColor:GRAY,data:{json.dumps([round(float(ref_nc['net_rate'].get(r,0)),1) for r in refund_labels])}}},
  ]);
bar('c_pay_type',{json.dumps(pay_labels)},[{','.join(pay_type_ds)}]);
"""

# Section 8: Metric
seg_m_labels  = seg_metric_grp["industry_segment"].tolist()
seg_m_vol     = [int(x) for x in seg_metric_grp["n_coupon_card"].tolist()]
seg_m_success = [round(float(x or 0)*100, 1) for x in seg_metric_grp["success_rate"].tolist()]
seg_m_failure = [round(float(x or 0)*100, 1) for x in seg_metric_grp["failure_rate"].tolist()]

mbt = metric_by_type.set_index("coupon_type").reindex(TYPE_ORDER).fillna(0)
mt_vol = [int(mbt.loc[t,'n_coupon_card']) for t in TYPE_ORDER]
mt_suc = [round(float(mbt.loc[t,'success_rate'] or 0)*100, 1) for t in TYPE_ORDER]
mt_fai = [round(float(mbt.loc[t,'failure_rate'] or 0)*100, 1) for t in TYPE_ORDER]

tp_labels = top_partners_metric["partner_name"].str[:22].tolist()
tp_vals   = [int(x) for x in top_partners_metric["n_coupon_card"].tolist()]
tp_colors = []
for _, row in top_partners_metric.iterrows():
    sr = row.get("success_rate") or 0
    tp_colors.append("#16A34A" if sr > 0.5 else "#D97706" if sr > 0.3 else "#DC2626")

html += f"""
bar('c_metric_vol',{json.dumps(seg_m_labels)},
  [{{label:'Coupon Card Volume',backgroundColor:PALETTE,data:{json.dumps(seg_m_vol)}}}],
  {{plugins:{{legend:{{display:false}}}}}});
bar('c_metric_rate',{json.dumps(seg_m_labels)},
  [
    {{label:'Success Rate (%)',backgroundColor:GREEN,data:{json.dumps(seg_m_success)}}},
    {{label:'Failure Rate (%)',backgroundColor:RED,data:{json.dumps(seg_m_failure)}}},
  ]);
bar('c_metric_type_vol',{json.dumps(TYPE_ORDER)},
  [{{label:'Coupon Card Volume',backgroundColor:{t_colors},data:{json.dumps(mt_vol)}}}],
  {{plugins:{{legend:{{display:false}}}}}});
bar('c_metric_type_rate',{json.dumps(TYPE_ORDER)},
  [
    {{label:'Avg Success Rate (%)',backgroundColor:GREEN,data:{json.dumps(mt_suc)}}},
    {{label:'Avg Failure Rate (%)',backgroundColor:RED,data:{json.dumps(mt_fai)}}},
  ]);
hbar('c_top_partners_metric',{json.dumps(tp_labels)},
  [{{label:'n_coupon_card',backgroundColor:{json.dumps(tp_colors)},data:{json.dumps(tp_vals)}}}],
  {{plugins:{{legend:{{display:false}}}}}});
</script></body></html>
"""

# ── Write output ───────────────────────────────────────────────────────────────
out = os.path.join(BASE, "coupon_partner_report.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Report saved: {out}")
print(f"   Total orders (77 partners): {total_orders:,}")
print(f"   Coupon order share: {coupon_order_pct:.1f}%")
print(f"   GP Margin — Coupon: {gp_margin_coupon:.2f}%  |  No Coupon: {gp_margin_no_coupon:.2f}%")
print(f"   Net Order Rate — Coupon: {nr_coupon_overall:.1f}%  |  No Coupon: {nr_nocoupon_overall:.1f}%")
