#!/usr/bin/env python3
"""Step 1: download every public input and log where it came from.

This script downloads the federal files the report uses
(FHWA traffic-counter station lists 2015-2025, FHWA road-mile and miles-driven
tables, Census urban-area and county maps, and the author's own fatality panel
from Zenodo). Each download is recorded in data/raw/PROVENANCE.txt with its size
and a fingerprint (SHA-256) so anyone can confirm they have the same files.
"""
import datetime, hashlib, os, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
LOG = os.path.join(RAW, "PROVENANCE.txt")
TMAS = "https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/{y}/{y}_station_data.zip"
HS = "https://www.fhwa.dot.gov/policyinformation/statistics/{y}/xls/{t}.xlsx"

SOURCES = [(f"tmas/{y}_station_data.zip", TMAS.format(y=y)) for y in range(2015, 2026)]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
# 2024 monthly volume files: used only to confirm which listed stations actually reported data in 2024
SOURCES += [(f"tmas_monthly/{m}_2024_ccs_data.zip",
             f"https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/2024/{m}_2024_ccs_data.zip") for m in MONTHS]
SOURCES += [(f"hs/{y}_{t}.xlsx", HS.format(y=y, t=t)) for y in (2023, 2024) for t in ("hm20", "vm2")]
SOURCES += [
    ("census/tl_2024_us_uac20.zip", "https://www2.census.gov/geo/tiger/TIGER2024/UAC20/tl_2024_us_uac20.zip"),
    ("census/cb_2023_us_county_500k.zip", "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"),
    ("panel/rural-road-fatality-panel-v1.0.0.zip",
     "https://zenodo.org/api/records/23547650/files/Emmanuel-Oti-Nani/rural-road-fatality-panel-v1.0.0.zip/content"),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    for rel, url in SOURCES:
        dest = os.path.join(RAW, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print("have", rel); continue
        print("get ", rel)
        subprocess.run(["curl", "-sSfL", "-m", "900", "-o", dest, url], check=True)
        line = " | ".join([datetime.date.today().isoformat(), rel, f"{os.path.getsize(dest)} bytes",
                           f"sha256:{sha256(dest)}", url])
        with open(LOG, "a") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    main()
