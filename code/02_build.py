#!/usr/bin/env python3
"""Step 2: clean, combine and summarize.

This script turns FHWA's counter-lane records into one row
per permanent count station, labels each station rural or urban two ways (FHWA's
own label, and whether it sits inside a 2020 Census urban area), finds its county,
checks which stations actually sent traffic data in 2024, and compares station
counts with road miles, miles driven and road deaths. Every number the report and
comment quote is written to report/stats.json.
"""
import glob, json, os, re, zipfile, io
import numpy as np, pandas as pd, geopandas as gpd, openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, PROC = f"{ROOT}/data/raw", f"{ROOT}/data/processed"
REP = f"{ROOT}/report"
os.makedirs(PROC, exist_ok=True); os.makedirs(REP, exist_ok=True)
YEARS = list(range(2015, 2026))
FS_NAMES = {1: "Interstate", 2: "Other freeway/expressway", 3: "Other principal arterial", 4: "Minor arterial",
            5: "Major collector", 6: "Minor collector", 7: "Local"}
states = pd.read_csv(glob.glob(f"{RAW}/panel/x/*/code/state_codes.csv")[0], dtype=str)
FIPS2ABBR = dict(zip(states.fips_state, states.abbr))
STATS = {}


def read_station_year(y):
    rows = []
    with zipfile.ZipFile(f"{RAW}/tmas/{y}_station_data.zip") as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            txt = z.read(n).decode("latin-1").splitlines()
            hdr = [h.strip().lower() for h in txt[0].split("|")]
            for line in txt[1:]:
                p = line.split("|")
                if len(p) < 10:
                    continue
                rows.append(dict(zip(hdr, [x.strip() for x in p])))
    df = pd.DataFrame(rows)
    df["year"] = y
    return df


def parse_coord(v, is_lon):
    v = (v or "").strip()
    if not v:
        return np.nan
    try:
        if "." in v:
            x = float(v)
        else:
            x = int(v) / 1e6
    except ValueError:
        return np.nan
    if is_lon and x > 0:
        x = -x  # pre-2025 format drops the sign; all US stations are west of Greenwich
    return x


def classify(code, y):
    """Return (functional system 1-7 or None, 'R'/'U' or None) from the F_System field."""
    code = code.strip()
    m = re.fullmatch(r"([1-7])([RU])", code)
    if m:
        return int(m.group(1)), m.group(2)
    if y >= 2025 and code.isdigit():  # 2025 files use the older two-digit HPMS codes: <10 rural, >=10 urban
        c = int(code)
        return None, ("R" if c < 10 else "U")
    return None, None


def stations_for_year(y):
    d = read_station_year(y)
    lanes = len(d)
    d["state_fips"] = d["state_code"].str.zfill(2)
    d["sid"] = d["state_fips"] + "-" + d["station_id"].str.strip().str.upper()
    fs = d["f_system"].apply(lambda c: classify(c, y))
    d["fsys"] = [a for a, b in fs]
    d["ru_fhwa"] = [b for a, b in fs]
    d["lat"] = d["latitude"].apply(lambda v: parse_coord(v, False))
    d["lon"] = d["longitude"].apply(lambda v: parse_coord(v, True))
    # one row per station: most common value across its direction/lane records
    g = d.groupby("sid")
    st = pd.DataFrame({
        "state_fips": g["state_fips"].first(),
        "station_id": g["station_id"].first(),
        "fsys": g["fsys"].agg(lambda s: s.mode().iloc[0] if s.notna().any() else np.nan),
        "ru_fhwa": g["ru_fhwa"].agg(lambda s: s.mode().iloc[0] if s.notna().any() else None),
        "lat": g["lat"].median(), "lon": g["lon"].median(),
        "county_code_reported": g["county_code"].first(),
        "n_lane_records": g.size(),
        "ru_conflict": g["ru_fhwa"].nunique() > 1,
    }).reset_index()
    st["year"] = y
    st["state"] = st["state_fips"].map(FIPS2ABBR)
    return st, lanes


# ---------- A. station tables, all years ----------
allst, lane_counts = [], {}
for y in YEARS:
    s, n = stations_for_year(y)
    allst.append(s); lane_counts[y] = n
st = pd.concat(allst, ignore_index=True)

# coordinate sanity: inside a box around the 50 states + DC + PR
ok = st.lat.between(17, 72) & st.lon.between(-180, -64)
st.loc[~ok, ["lat", "lon"]] = np.nan

# ---------- B. spatial joins: Census 2020 urban areas, counties ----------
ua = gpd.read_file(f"zip://{RAW}/census/tl_2024_us_uac20.zip")[["UACE20", "NAME20", "geometry"]].to_crs(4269)
cty = gpd.read_file(f"zip://{RAW}/census/cb_2023_us_county_500k.zip")[["GEOID", "STATEFP", "geometry"]].to_crs(4269)
pts = gpd.GeoDataFrame(st, geometry=gpd.points_from_xy(st.lon, st.lat), crs=4269)
has = pts.lat.notna()
j1 = gpd.sjoin(pts[has], ua, how="left", predicate="within")
j1 = j1[~j1.index.duplicated()]
st.loc[has, "uace20"] = j1["UACE20"]
st["ru_census"] = np.where(st.lat.isna(), None, np.where(st["uace20"].notna(), "U", "R"))
j2 = gpd.sjoin(pts[has], cty, how="left", predicate="within")
j2 = j2[~j2.index.duplicated()]
st.loc[has, "county_fips"] = j2["GEOID"]
st.loc[has, "county_state_fips"] = j2["STATEFP"]
st["county_state_mismatch"] = st["county_state_fips"].notna() & (st["county_state_fips"] != st["state_fips"])

# ---------- C. which 2024 stations actually reported volume data ----------
days = {}
for zf in sorted(glob.glob(f"{RAW}/tmas_monthly/*_2024_ccs_data.zip")):
    with zipfile.ZipFile(zf) as z:
        for n in z.namelist():
            if not n.upper().endswith(".VOL"):
                continue
            with z.open(n) as fh:
                hdr = None
                for raw in io.TextIOWrapper(fh, encoding="latin-1"):
                    p = raw.split("|")
                    if hdr is None:
                        hdr = [h.strip().lower() for h in p]
                        ix = [hdr.index(k) for k in ("state_code", "station_id", "month_record", "day_record")]
                        continue
                    if len(p) < 10:
                        continue
                    sid = p[ix[0]].strip().zfill(2) + "-" + p[ix[1]].strip().upper()
                    days.setdefault(sid, set()).add((p[ix[2]].strip(), p[ix[3]].strip()))
vol_days = pd.Series({k: len(v) for k, v in days.items()}, name="days_with_volume_2024")
s24 = st[st.year == 2024].copy()
s24["days_with_volume_2024"] = s24["sid"].map(vol_days).fillna(0).astype(int)
s24["active_2024"] = s24["days_with_volume_2024"] > 0
STATS["volume_ids_not_in_station_file"] = int(len(set(vol_days.index) - set(s24.sid)))

st.drop(columns=[]).to_csv(f"{PROC}/stations_2015_2025.csv", index=False)
s24.to_csv(f"{PROC}/stations_2024.csv", index=False)

# ---------- D. highway statistics 2024 ----------
def read_hs(path):
    ws = openpyxl.load_workbook(path, data_only=True).active
    out = {}
    for r in ws.iter_rows(values_only=True):
        name = r[0]
        if isinstance(name, str) and isinstance(r[8], (int, float)) and isinstance(r[17], (int, float)):
            out[name.strip().rstrip("(0123456789) ").strip()] = [float(x or 0) for x in r[1:18]]
    df = pd.DataFrame(out, index=[f"R{i}" for i in range(1, 8)] + ["R_total"] + [f"U{i}" for i in range(1, 8)] + ["U_total", "total"]).T
    return df

hm20 = read_hs(f"{RAW}/hs/2024_hm20.xlsx")
vm2 = read_hs(f"{RAW}/hs/2024_vm2.xlsx")
name2abbr = dict(zip(states.state_name, states.abbr))
for df in (hm20, vm2):
    df["state"] = df.index.map(name2abbr)
US_ROW = [i for i in hm20.index if i.lower().startswith("u.s. total") or i.lower() == "total"]
STATS["hs_total_row_used"] = US_ROW
us_m = hm20.loc[hm20.state.notna()].drop(columns="state").sum()
us_v = vm2.loc[vm2.state.notna()].drop(columns="state").sum()
STATS["hs_states_parsed"] = int(hm20.state.notna().sum())

# ---------- E. headline: 2024 shares ----------
a = s24[s24.state.notna()]  # 50 states + DC
STATS["stations_2024_lane_records"] = lane_counts[2024]
STATS["stations_2024_listed"] = int(len(a))
STATS["stations_2024_active"] = int(a.active_2024.sum())
STATS["stations_2024_no_coords"] = int(a.lat.isna().sum())
STATS["stations_2024_no_fhwa_ru"] = int(a.ru_fhwa.isna().sum())
STATS["stations_2024_ru_conflict"] = int(a.ru_conflict.sum())
act = a[a.active_2024]

def share(series, val):
    s = series.dropna()
    return round(100 * (s == val).mean(), 1)

STATS["rural_share_stations_fhwa_listed"] = share(a.ru_fhwa, "R")
STATS["rural_share_stations_fhwa_active"] = share(act.ru_fhwa, "R")
STATS["rural_share_stations_census_active"] = share(act.ru_census, "R")
STATS["rural_stations_active_fhwa"] = int((act.ru_fhwa == "R").sum())
STATS["urban_stations_active_fhwa"] = int((act.ru_fhwa == "U").sum())
STATS["rural_share_miles_2024"] = round(100 * us_m.R_total / us_m.total, 1)
STATS["rural_share_vmt_2024"] = round(100 * us_v.R_total / us_v.total, 1)
STATS["rural_miles_2024"] = round(us_m.R_total)
STATS["urban_miles_2024"] = round(us_m.U_total)
STATS["rural_vmt_bil_2024"] = round(us_v.R_total / 1000, 1)
STATS["urban_vmt_bil_2024"] = round(us_v.U_total / 1000, 1)
STATS["agree_fhwa_census_pct"] = round(100 * (act.dropna(subset=["ru_fhwa", "ru_census"]).pipe(lambda d: (d.ru_fhwa == d.ru_census).mean())), 1)

# deaths from the author's panel (Census 2020 urban-area definition)
panel = pd.read_csv(glob.glob(f"{RAW}/panel/x/*/powerbi/panel_county_year_2015_2024.csv")[0], dtype={"fips": str, "state_fips": str})
p24 = panel[panel.year == 2024]
STATS["rural_share_deaths_2024"] = round(100 * p24.deaths_rural.sum() / p24.deaths.sum(), 1)  # same convention as the panel paper
STATS["rural_deaths_2024"] = int(p24.deaths_rural.sum())
p5 = panel[panel.year.between(2020, 2024)]
STATS["rural_deaths_2020_2024"] = int(p5.deaths_rural.sum())

per = lambda n, d: round(n / d, 2)
STATS["rural_stations_per_1000mi"] = per(STATS["rural_stations_active_fhwa"], us_m.R_total / 1000)
STATS["urban_stations_per_1000mi"] = per(STATS["urban_stations_active_fhwa"], us_m.U_total / 1000)
STATS["rural_stations_per_bvmt"] = per(STATS["rural_stations_active_fhwa"], us_v.R_total / 1000)
STATS["urban_stations_per_bvmt"] = per(STATS["urban_stations_active_fhwa"], us_v.U_total / 1000)
STATS["urban_to_rural_density_ratio_miles"] = round(STATS["urban_stations_per_1000mi"] / STATS["rural_stations_per_1000mi"], 1)
STATS["rural_miles_per_station"] = round(us_m.R_total / STATS["rural_stations_active_fhwa"])
STATS["urban_miles_per_station"] = round(us_m.U_total / STATS["urban_stations_active_fhwa"])

# ---------- F. by functional system ----------
rows = []
for ru in ("R", "U"):
    for f in range(1, 8):
        n = int(((act.ru_fhwa == ru) & (act.fsys == f)).sum())
        mi, v = us_m[f"{ru}{f}"], us_v[f"{ru}{f}"]
        rows.append(dict(area="Rural" if ru == "R" else "Urban", fsys=f, road_class=FS_NAMES[f], stations=n,
                         miles=round(mi), vmt_billion=round(v / 1000, 2),
                         stations_per_1000mi=round(n / (mi / 1000), 2) if mi else None,
                         stations_per_bvmt=round(n / (v / 1000), 2) if v else None))
fsys_t = pd.DataFrame(rows)
fsys_t.to_csv(f"{PROC}/table_by_road_class_2024.csv", index=False)
rl = fsys_t[(fsys_t.area == "Rural")]
low = rl[rl.fsys >= 5]  # rural collectors and locals
STATS["rural_collector_local_miles_share_of_rural"] = round(100 * low.miles.sum() / rl.miles.sum(), 1)
STATS["rural_collector_local_station_share_of_rural"] = round(100 * low.stations.sum() / rl.stations.sum(), 1)
STATS["rural_collector_local_stations"] = int(low.stations.sum())
STATS["rural_collector_local_miles"] = int(low.miles.sum())
STATS["rural_local_stations"] = int(rl[rl.fsys == 7].stations.iloc[0])
STATS["rural_local_miles"] = int(rl[rl.fsys == 7].miles.iloc[0])
STATS["rural_interstate_per_1000mi"] = float(rl[rl.fsys == 1].stations_per_1000mi.iloc[0])
STATS["rural_minor_collector_per_1000mi"] = float(rl[rl.fsys == 6].stations_per_1000mi.iloc[0])
STATS["rural_local_per_1000mi"] = float(rl[rl.fsys == 7].stations_per_1000mi.iloc[0])
# deaths by rural road class from the panel, 2020-2024
STATS["rural_deaths_2020_2024_by_class"] = {k: int(p5[f"deaths_rural_{k}"].sum()) for k in ("interstate_fwy", "arterial", "collector", "local", "road_unknown")}
cl = STATS["rural_deaths_2020_2024_by_class"]
STATS["rural_deaths_collector_local_share"] = round(100 * (cl["collector"] + cl["local"]) / sum(cl.values()), 1)

# stations, VMT and deaths by broad road class (panel classes: 1-2 interstate/freeway, 3-4 arterial, 5-6 collector, 7 local)
BROAD = {"interstate_fwy": [1, 2], "arterial": [3, 4], "collector": [5, 6], "local": [7]}
brows = []
for ru, area in (("R", "Rural"), ("U", "Urban")):
    for k, fl in BROAD.items():
        sub = fsys_t[(fsys_t.area == area) & fsys_t.fsys.isin(fl)]
        if ru == "R":
            dth = int(p5[f"deaths_rural_{k}"].sum())
        else:  # urban = all deaths on that class minus rural (panel's unknown-location deaths excluded)
            dth = int(p5[f"deaths_{k}"].sum() - p5[f"deaths_rural_{k}"].sum())
        n = int(sub.stations.sum())
        brows.append(dict(area=area, road_class=k, stations=n, miles=int(sub.miles.sum()), vmt_billion=round(sub.vmt_billion.sum(), 1),
                          deaths_2020_2024=dth, stations_per_bvmt=round(n / sub.vmt_billion.sum(), 2),
                          deaths_per_station=round(dth / n, 1) if n else None))
broad = pd.DataFrame(brows)
broad.to_csv(f"{PROC}/table_broad_class_deaths_2024.csv", index=False)
STATS["broad_class"] = broad.to_dict("records")
rcl = broad[(broad.area == "Rural") & broad.road_class.isin(["collector", "local"])]
rhi = broad[(broad.area == "Rural") & broad.road_class.isin(["interstate_fwy", "arterial"])]
STATS["rural_low_stations_per_bvmt"] = round(rcl.stations.sum() / rcl.vmt_billion.sum(), 2)
STATS["rural_high_stations_per_bvmt"] = round(rhi.stations.sum() / rhi.vmt_billion.sum(), 2)
STATS["rural_low_vmt_bil"] = round(rcl.vmt_billion.sum(), 1)
STATS["rural_low_vmt_share_of_rural"] = round(100 * rcl.vmt_billion.sum() / STATS["rural_vmt_bil_2024"], 1)
STATS["rural_low_deaths_per_station"] = round(rcl.deaths_2020_2024.sum() / rcl.stations.sum(), 1)
STATS["rural_high_deaths_per_station"] = round(rhi.deaths_2020_2024.sum() / rhi.stations.sum(), 1)
STATS["rural_low_deaths_2020_2024"] = int(rcl.deaths_2020_2024.sum())

# sensitivity: some states give each direction its own station ID. Collapse active stations in the same
# state, same F_System code, within about 300 m of each other into one physical "site".
from sklearn.neighbors import BallTree  # noqa: E402
ac = act[act.lat.notna()].copy()
site = pd.Series(index=ac.index, dtype=object)
for (stt, fs_, ru_), g in ac.groupby(["state", "fsys", "ru_fhwa"], dropna=False):
    X = np.radians(g[["lat", "lon"]].values)
    tree = BallTree(X, metric="haversine")
    nbrs = tree.query_radius(X, r=0.3 / 6371.0)
    lab = -np.ones(len(g), int); c = 0
    for i in range(len(g)):  # connected components
        if lab[i] >= 0:
            continue
        stack = [i]; lab[i] = c
        while stack:
            k = stack.pop()
            for nb in nbrs[k]:
                if lab[nb] < 0:
                    lab[nb] = c; stack.append(nb)
        c += 1
    site.loc[g.index] = [f"{stt}-{fs_}-{ru_}-{l}" for l in lab]
ac["site"] = site
sites = ac.drop_duplicates("site")
STATS["sites_active"] = int(len(sites))
STATS["sites_rural_share"] = share(sites.ru_fhwa, "R")
STATS["sites_rural_collector_local_share_of_rural"] = round(100 * ((sites.ru_fhwa == "R") & (sites.fsys >= 5)).sum() / (sites.ru_fhwa == "R").sum(), 1)
STATS["sites_rural_local"] = int(((sites.ru_fhwa == "R") & (sites.fsys == 7)).sum())
STATS["sites_rural_collector_local"] = int(((sites.ru_fhwa == "R") & (sites.fsys >= 5)).sum())
STATS["sites_rural_per_bvmt"] = round((sites.ru_fhwa == "R").sum() / (us_v.R_total / 1000), 2)
STATS["sites_urban_per_bvmt"] = round((sites.ru_fhwa == "U").sum() / (us_v.U_total / 1000), 2)

# ---------- G. by state ----------
srows = []
for ab, g in act.groupby("state"):
    if ab not in set(hm20.state):
        continue
    m, v = hm20[hm20.state == ab].iloc[0], vm2[vm2.state == ab].iloc[0]
    nr, nu = int((g.ru_fhwa == "R").sum()), int((g.ru_fhwa == "U").sum())
    pr = p5[p5.state == ab]
    srows.append(dict(state=ab, rural_stations=nr, urban_stations=nu, rural_miles=round(m.R_total), urban_miles=round(m.U_total),
                      rural_vmt_billion=round(v.R_total / 1000, 2), rural_deaths_2020_2024=int(pr.deaths_rural.sum()),
                      rural_stations_per_1000mi=round(nr / (m.R_total / 1000), 2) if m.R_total else None,
                      rural_share_stations=round(100 * nr / (nr + nu), 1) if nr + nu else None,
                      rural_share_miles=round(100 * m.R_total / m.total, 1),
                      rural_share_deaths_2020_2024=round(100 * pr.deaths_rural.sum() / max(1, pr.deaths.sum()), 1)))
state_t = pd.DataFrame(srows)
low_by_state = act[(act.ru_fhwa == "R") & (act.fsys >= 5)].groupby("state").size()
state_t["rural_collector_local_stations"] = state_t.state.map(low_by_state).fillna(0).astype(int)
STATS["states_rural_low_ge6"] = int((state_t[state_t.rural_miles > 0].rural_collector_local_stations >= 6).sum())
STATS["states_rural_low_zero"] = sorted(state_t[(state_t.rural_miles > 0) & (state_t.rural_collector_local_stations == 0)].state.tolist())
STATS["listed_not_reporting_2024"] = int(STATS["stations_2024_listed"] - STATS["stations_2024_active"])
state_t["rural_deaths_per_rural_station"] = (state_t.rural_deaths_2020_2024 / state_t.rural_stations.replace(0, np.nan)).round(1)
state_t.to_csv(f"{PROC}/table_by_state_2024.csv", index=False)
STATS["states_in_state_table"] = int(len(state_t))
STATS["missing_states_2024"] = sorted(set(hm20.state.dropna()) - set(state_t.state))
sr = state_t[state_t.rural_miles > 0]
STATS["states_rural_share_stations_below_miles"] = int((sr.rural_share_stations < sr.rural_share_miles).sum())
STATS["states_rural_share_stations_below_deaths"] = int((sr.rural_share_stations < sr.rural_share_deaths_2020_2024).sum())
STATS["states_with_rural_miles"] = int(len(sr))
STATS["state_rural_density_median"] = round(float(sr.rural_stations_per_1000mi.median()), 2)
STATS["state_rural_density_min"] = sr.nsmallest(1, "rural_stations_per_1000mi")[["state", "rural_stations_per_1000mi"]].to_dict("records")[0]
STATS["state_rural_density_max"] = sr.nlargest(1, "rural_stations_per_1000mi")[["state", "rural_stations_per_1000mi"]].to_dict("records")[0]
STATS["states_under_10_rural_stations"] = sorted(sr[sr.rural_stations < 10].state.tolist())
STATS["states_under_6_rural_stations"] = sorted(sr[sr.rural_stations < 6].state.tolist())

# ---------- H. by county ----------
cnt = act.groupby("county_fips").agg(stations=("sid", "size"), rural_stations=("ru_fhwa", lambda s: int((s == "R").sum())))
pc = p5.groupby("fips").agg(rural_deaths=("deaths_rural", "sum"), deaths=("deaths", "sum"),
                             rural_miles=("miles_rural_fhwa_2024", "first"), state=("state", "first"), county=("county_name", "first"),
                             pct_rural_2020=("pct_rural_2020", "first"))
cc = pc.join(cnt, how="left").fillna({"stations": 0, "rural_stations": 0})
cc.to_csv(f"{PROC}/table_by_county_2024.csv")
STATS["counties"] = int(len(cc))
STATS["county_station_match_rate"] = round(100 * act.county_fips.isin(pc.index).mean(), 1)
z = cc[cc.stations == 0]
STATS["counties_no_station"] = int(len(z))
STATS["counties_no_station_pct"] = round(100 * len(z) / len(cc), 1)
STATS["rural_deaths_in_no_station_counties"] = int(z.rural_deaths.sum())
STATS["rural_deaths_in_no_station_counties_pct"] = round(100 * z.rural_deaths.sum() / cc.rural_deaths.sum(), 1)
STATS["rural_miles_in_no_station_counties_pct"] = round(100 * z.rural_miles.sum() / cc.rural_miles.sum(), 1)
zr = cc[cc.rural_stations == 0]
STATS["counties_no_rural_station"] = int(len(zr))
STATS["rural_deaths_in_no_rural_station_counties_pct"] = round(100 * zr.rural_deaths.sum() / cc.rural_deaths.sum(), 1)
mostly_rural = cc[cc.pct_rural_2020 >= 50]
STATS["mostly_rural_counties"] = int(len(mostly_rural))
STATS["mostly_rural_counties_no_station_pct"] = round(100 * (mostly_rural.stations == 0).mean(), 1)
STATS["mostly_urban_counties_no_station_pct"] = round(100 * (cc[cc.pct_rural_2020 < 50].stations == 0).mean(), 1)
top = z.sort_values("rural_deaths", ascending=False).head(10).reset_index()
top[["fips", "county", "state", "rural_deaths", "rural_miles"]].to_csv(f"{PROC}/top_no_station_counties.csv", index=False)
STATS["top_no_station_counties"] = top[["fips", "county", "state", "rural_deaths"]].to_dict("records")

# ---------- I. data completeness 2024 ----------
for ru in ("R", "U"):
    g = act[act.ru_fhwa == ru]
    STATS[f"median_days_{ru}"] = int(g.days_with_volume_2024.median())
    STATS[f"pct_300plus_days_{ru}"] = round(100 * (g.days_with_volume_2024 >= 300).mean(), 1)

# ---------- J. trend ----------
tr = []
for y in YEARS:
    g = st[(st.year == y) & st.state.notna()]
    tr.append(dict(year=y, stations=len(g), rural_fhwa=int((g.ru_fhwa == "R").sum()), urban_fhwa=int((g.ru_fhwa == "U").sum()),
                   rural_share_fhwa=share(g.ru_fhwa, "R"), rural_share_census=share(g.ru_census, "R"),
                   states=int(g.state.nunique())))
trend = pd.DataFrame(tr)
trend.to_csv(f"{PROC}/trend_2015_2025.csv", index=False)
t15, t24 = trend.set_index("year").loc[2015], trend.set_index("year").loc[2024]
STATS["trend"] = trend.to_dict("records")
STATS["stations_growth_2015_2024_pct"] = round(100 * (t24.stations / t15.stations - 1), 1)
STATS["rural_growth_2015_2024_pct"] = round(100 * (t24.rural_fhwa / t15.rural_fhwa - 1), 1)
STATS["urban_growth_2015_2024_pct"] = round(100 * (t24.urban_fhwa / t15.urban_fhwa - 1), 1)
STATS["new_stations_2015_2024"] = int(t24.stations - t15.stations)
STATS["new_rural_2015_2024"] = int(t24.rural_fhwa - t15.rural_fhwa)
STATS["new_urban_2015_2024"] = int(t24.urban_fhwa - t15.urban_fhwa)

# ---------- K. QA extras ----------
STATS["coords_missing_by_year"] = {int(y): int(g.lat.isna().sum()) for y, g in st.groupby("year")}
STATS["county_state_mismatch_2024"] = int(a.county_state_mismatch.sum())
STATS["stations_outside_50dc_2024"] = int(s24.state.isna().sum())

json.dump(STATS, open(f"{REP}/stats.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps({k: v for k, v in STATS.items() if k not in ("trend",)}, indent=1, default=str))
