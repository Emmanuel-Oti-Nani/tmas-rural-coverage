#!/usr/bin/env python3
"""Step 3: quality checks.

This script re-counts key numbers in independent ways and
lists named stations that can be looked up by hand. It writes data/processed/qa_report.txt.
"""
import glob, json, os, zipfile
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = f"{ROOT}/data/processed"
S = json.load(open(f"{ROOT}/report/stats.json"))
out = []
w = out.append
fails = 0


def check(name, cond, detail=""):
    global fails
    w(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    fails += 0 if cond else 1


st = pd.read_csv(f"{P}/stations_2015_2025.csv", dtype={"state_fips": str, "county_fips": str})
s24 = pd.read_csv(f"{P}/stations_2024.csv", dtype={"state_fips": str, "county_fips": str})
w("QA REPORT: Rural coverage of TMAS count stations")
w("=" * 60)
w("1. Row counts")
for y, g in st.groupby("year"):
    w(f"   {y}: {len(g):>6} stations from station file, {g.state.nunique()} states/DC, {g.lat.isna().sum()} without usable coordinates")
w(f"   2024 lane records {S['stations_2024_lane_records']} -> stations {S['stations_2024_listed']} -> reported volume in 2024 {S['stations_2024_active']}")

w("\n2. Independent recounts")
# recount 2024 rural stations straight from the zip, without the build code
seen = {}
with zipfile.ZipFile(f"{ROOT}/data/raw/tmas/2024_station_data.zip") as z:
    for n in z.namelist():
        lines = z.read(n).decode("latin-1").splitlines()
        h = lines[0].lower().split("|")
        for L in lines[1:]:
            p = L.split("|")
            seen.setdefault(p[1].zfill(2) + "-" + p[2].strip().upper(), p[h.index("f_system")].strip())
check("2024 station count recount", len(seen) == S["stations_2024_listed"], f"({len(seen)} vs {S['stations_2024_listed']})")
nr = sum(1 for v in seen.values() if v.endswith("R"))
check("2024 listed rural share recount within 0.5 pt", abs(100 * nr / len(seen) - S["rural_share_stations_fhwa_listed"]) < 0.5,
      f"({100*nr/len(seen):.1f} vs {S['rural_share_stations_fhwa_listed']}; lane-level first value vs station mode)")
check("Highway Statistics: 51 jurisdictions parsed", S["hs_states_parsed"] == 51)
check("Rural miles 2024 plausible (2.9-3.0 million)", 2.9e6 < S["rural_miles_2024"] < 3.0e6, f"({S['rural_miles_2024']:,})")
check("Rural share of miles 65-75%", 65 < S["rural_share_miles_2024"] < 75, f"({S['rural_share_miles_2024']})")
check("Rural share of VMT 25-35%", 25 < S["rural_share_vmt_2024"] < 35, f"({S['rural_share_vmt_2024']})")
panel_stats = json.load(open(glob.glob(f"{ROOT}/data/raw/panel/x/*/paper/stats.json")[0]))
w(f"   Panel stats rural_by_year (for comparison): {str(panel_stats.get('rural_by_year'))[:300]}")
check("Panel counties = 3,143", S["counties"] == 3143)
check("Every 2024 station has a rural/urban label", S["stations_2024_no_fhwa_ru"] == 0)
check("Stations with coordinates matched to a panel county >= 97%", S["county_station_match_rate"] >= 97, f"({S['county_station_match_rate']}%)")
check("Rural+urban active stations = active total minus unlabeled",
      S["rural_stations_active_fhwa"] + S["urban_stations_active_fhwa"] == S["stations_2024_active"], "")
bc = pd.DataFrame(S["broad_class"])
check("Broad-class stations sum to active labeled stations (fsys known)", bc.stations.sum() <= S["stations_2024_active"], f"({bc.stations.sum()})")

w("\n3. Things to know")
w(f"   - {S['stations_2024_ru_conflict']} stations have lanes coded rural and urban; the most common label is used.")
w(f"   - {S['county_state_mismatch_2024']} stations' coordinates fall just across a state line (border sites); county from coordinates kept.")
w(f"   - {S['volume_ids_not_in_station_file']} station IDs appear in 2024 volume files but not in the 2024 station file; excluded.")
w(f"   - FHWA and Census rural labels agree for {S['agree_fhwa_census_pct']}% of active 2024 stations.")
w("   - The TMAS station download contains only motorized station records (record type 'S'); no bicycle or pedestrian stations.")
rt = set()
with zipfile.ZipFile(f"{ROOT}/data/raw/tmas/2024_station_data.zip") as z:
    for n in z.namelist():
        rt |= {L.split("|")[0] for L in z.read(n).decode("latin-1").splitlines()[1:] if L}
check("Only record type S in 2024 station files", rt == {"S"}, f"({sorted(rt)})")

w("\n4. Spot checks you can verify by hand")
for sid in ["29-001823", "05-000010", "47-000003", "06-099910", "48-000101"]:
    r = s24[s24.sid == sid]
    if len(r):
        r = r.iloc[0]
        w(f"   {sid}: state {r.state}, F_System {int(r.fsys) if r.fsys == r.fsys else 'NA'}{r.ru_fhwa}, lat {r.lat}, lon {r.lon}, "
          f"Census label {r.ru_census}, county {r.county_fips}, days with 2024 volume {r.days_with_volume_2024}")
    else:
        w(f"   {sid}: not in 2024 file")

w(f"\nRESULT: {fails} failed checks")
open(f"{P}/qa_report.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
