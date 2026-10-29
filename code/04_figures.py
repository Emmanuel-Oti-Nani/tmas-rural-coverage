#!/usr/bin/env python3
"""Step 4: figures.

Draws the report's four figures from the processed tables
and saves PNG and PDF copies in report/figures/. Figures carry a DRAFT stamp unless
run with --final.
"""
import json, os, sys
import pandas as pd, geopandas as gpd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P, F = f"{ROOT}/data/processed", f"{ROOT}/report/figures"
os.makedirs(F, exist_ok=True)
FINAL = "--final" in sys.argv
S = json.load(open(f"{ROOT}/report/stats.json"))
RURAL, URBAN, INK, INK2, GRID, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#c9c8c2"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name, source):
    fig.text(0.01, -0.06, source, fontsize=7, color=INK2, ha="left", va="bottom")
    if not FINAL:
        fig.text(0.99, 0.99, "DRAFT", fontsize=10, color="#e34948", ha="right", va="top", weight="bold")
    for ext in ("png", "pdf"):
        fig.savefig(f"{F}/{name}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


# Fig 1: rural share of four quantities (single series)
items = [("Public road miles", S["rural_share_miles_2024"]), ("Road deaths (2024)", S["rural_share_deaths_2024"]),
         ("Count stations reporting volume", S["rural_share_stations_fhwa_active"]), ("Vehicle-miles traveled", S["rural_share_vmt_2024"])]
fig, ax = plt.subplots(figsize=(6.5, 2.6))
y = range(len(items))[::-1]
ax.barh(list(y), [v for _, v in items], color=RURAL, height=0.55)
for yi, (lab, v) in zip(y, items):
    ax.text(v + 1, yi, f"{v:.1f}%", va="center", color=INK, fontsize=9)
ax.set_yticks(list(y)); ax.set_yticklabels([l for l, _ in items], color=INK)
ax.set_xlim(0, 100); ax.set_xlabel("Rural share of U.S. total (%)")
ax.axvline(50, color=MUTED, lw=0.8, ls=(0, (3, 3)))
ax.xaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.set_title("Rural roads: 70% of the mileage, about half the deaths, half the count stations", loc="left", fontsize=10, color=INK)
save(fig, "fig1_rural_shares", "Sources: FHWA TMAS 2024 station and volume files; Highway Statistics 2024 HM-20, VM-2; Rural Road Fatality County Panel v1.0.0.")

# Fig 2: deaths per count station by road class, rural vs urban (two series)
b = pd.DataFrame(S["broad_class"])
order = ["interstate_fwy", "arterial", "collector", "local"]
labels = ["Interstates &\nfreeways", "Arterials", "Collectors", "Local roads"]
fig, ax = plt.subplots(figsize=(6.5, 3.2))
w = 0.38
for i, (area, col) in enumerate((("Rural", RURAL), ("Urban", URBAN))):
    vals = [b[(b.area == area) & (b.road_class == k)].deaths_per_station.iloc[0] for k in order]
    xs = [j + (i - 0.5) * (w + 0.02) for j in range(4)]
    ax.bar(xs, vals, width=w, color=col, label=area)
    for x, v in zip(xs, vals):
        ax.text(x, v + 6, f"{v:.0f}", ha="center", fontsize=8, color=INK)
ax.set_xticks(range(4)); ax.set_xticklabels(labels, color=INK)
ax.set_ylabel("Road deaths 2020-2024 per\nactive count station")
ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left")
ax.set_title("Deaths per count station rise steeply on collectors and local roads", loc="left", fontsize=10, color=INK)
save(fig, "fig2_deaths_per_station", "Stations: TMAS 2024, FHWA rural/urban code. Deaths: Rural Road Fatality County Panel (Census 2020 urban areas).")

# Fig 3: trend 2015-2024
t = pd.DataFrame(S["trend"]); t = t[t.year <= 2024]
fig, ax = plt.subplots(figsize=(6.5, 3.0))
for col, c, lab in (("rural_fhwa", RURAL, "Rural"), ("urban_fhwa", URBAN, "Urban")):
    ax.plot(t.year, t[col], color=c, lw=2, marker="o", ms=4, label=lab)
    ax.text(2024.2, t[col].iloc[-1], f"{lab} {t[col].iloc[-1]:,}", va="center", color=INK, fontsize=8)
ax.text(2015, t.rural_fhwa.iloc[0] + 120, f"{t.rural_fhwa.iloc[0]:,}", ha="center", fontsize=8, color=INK)
ax.text(2015, t.urban_fhwa.iloc[0] - 260, f"{t.urban_fhwa.iloc[0]:,}", ha="center", fontsize=8, color=INK)
ax.set_xlim(2014.6, 2025.6); ax.set_ylim(3000, 6200)
ax.set_ylabel("Stations listed in TMAS station file")
ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left")
ax.set_title(f"Since 2015 urban stations grew {S['urban_growth_2015_2024_pct']:.0f}%, rural stations {S['rural_growth_2015_2024_pct']:.0f}%", loc="left", fontsize=10, color=INK)
save(fig, "fig3_trend", "Source: FHWA TMAS station files 2015-2024 (one row per state and station ID; FHWA rural/urban code).")

# Fig 4: map, lower 48
RAW = f"{ROOT}/data/raw"
cty = gpd.read_file(f"zip://{RAW}/census/cb_2023_us_county_500k.zip")
cty = cty[~cty.STATEFP.isin(["02", "15", "60", "66", "69", "72", "78"])].to_crs(5070)
cc = pd.read_csv(f"{P}/table_by_county_2024.csv", dtype={"fips": str})
cty = cty.merge(cc[["fips", "stations"]], left_on="GEOID", right_on="fips", how="left")
s = pd.read_csv(f"{P}/stations_2024.csv")
s = s[s.active_2024 & s.lat.notna() & ~s.state.isin(["AK", "HI"])]
pts = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s.lon, s.lat), crs=4269).to_crs(5070)
fig, ax = plt.subplots(figsize=(7.5, 4.8))
cty[cty.stations.fillna(0) == 0].plot(ax=ax, color="#cfcdc6", edgecolor="white", lw=0.1)
cty[cty.stations.fillna(0) > 0].plot(ax=ax, color="#f4f3f0", edgecolor="white", lw=0.1)
for ru, c, lab in (("U", URBAN, "Urban station"), ("R", RURAL, "Rural station")):
    g = pts[pts.ru_fhwa == ru]
    g.plot(ax=ax, color=c, markersize=1.6, label=f"{lab} ({len(g):,})")
ax.set_axis_off()
from matplotlib.patches import Patch
h, l = ax.get_legend_handles_labels()
h.append(Patch(color="#cfcdc6")); l.append(f"County with no active station ({S['counties_no_station']:,} of {S['counties']:,} nationally)")
ax.legend(h, l, frameon=False, loc="lower left", fontsize=7, markerscale=4)
ax.set_title("Count stations reporting traffic volume in 2024", loc="left", fontsize=10, color=INK)
save(fig, "fig4_map", "Source: FHWA TMAS 2024 station and monthly volume files; Census 2023 county boundaries. Alaska and Hawaii not shown.")
print("figures written", "(final)" if FINAL else "(draft)")
