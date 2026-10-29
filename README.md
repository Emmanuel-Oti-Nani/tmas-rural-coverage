# Rural Coverage of Federal Traffic Count Stations (TMAS), 2015–2024

**Version 1.0 (released 2026-10-29). DOI: [10.5281/zenodo.23772244](https://doi.org/10.5281/zenodo.23772244)**

Every state runs permanent traffic counters and reports their data to the Federal Highway Administration (FHWA) through the Travel Monitoring Analysis System (TMAS). This project measures how well those counters cover rural roads. It compares the counters with road miles, miles driven, and road deaths, by road class, state, and county. The results support a technical report and a public comment on FHWA's 2026 renewal of the TMAS information collection (docket FHWA-2026-1090).

**Headline (2024):** rural roads have about half of the active count stations, in line with their share of road deaths and above their share of traffic. But rural collectors and local roads, which make up 91% of rural road miles and saw 41% of rural road deaths in 2020–2024, have only 13% of rural stations. See `report/` for the full results.

## Outputs

| File | What it is |
|---|---|
| `report/Nani_TMAS_Rural_Coverage_Technical_Report.pdf` | Technical report |
| `comment/Nani_Comment_FHWA-2026-1090.pdf` | Public comment for Regulations.gov |
| `comment/regulations_gov_summary.txt` | Short text to paste into the comment box |
| `report/stats.json` | Every number quoted in the report and comment |
| `report/figures/` | Figures (PNG and PDF) |
| `data/processed/` | Station tables (2015–2025, 2024), tables by road class, state and county, trend, QA report |

## How to rebuild

Requires Python 3.10+ (about 10 minutes and 700 MB of downloads).

```
pip install -r requirements.txt
python code/01_fetch.py        # download every source, log sizes and SHA-256 to data/raw/PROVENANCE.txt
python code/02_build.py        # station tables, joins, summaries -> report/stats.json
python code/03_qa.py           # quality checks -> data/processed/qa_report.txt (expect "0 failed checks")
python code/04_figures.py      # figures (add --final after verification)
python code/05_documents.py    # report and comment PDFs (add --final after verification)
```

## Sources (all public)

| Source | Vintage | Link |
|---|---|---|
| FHWA TMAS station files and 2024 monthly hourly-volume files | 2015–2025 | https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/ |
| FHWA Highway Statistics, Tables HM-20 and VM-2 | 2024 | https://www.fhwa.dot.gov/policyinformation/statistics/2024/ |
| Census TIGER/Line 2020 urban areas | 2024 release | https://www2.census.gov/geo/tiger/TIGER2024/UAC20/ |
| Census cartographic county boundaries | 2023 | https://www2.census.gov/geo/tiger/GENZ2023/shp/ |
| U.S. Rural Road Fatality County Panel v1.0.0 (FARS-based) | 2015–2024 | https://doi.org/10.5281/zenodo.23547649 |
| FHWA Traffic Monitoring Guide 2022, Chapter 3 | 2022 | https://www.fhwa.dot.gov/policyinformation/tmguide/tmg_2022/traffic-data-methodologies.cfm |
| Federal Register notice, FR Doc. 2026-20718 | Oct 9, 2026 | 91 FR 64735 |

U.S. government works are in the public domain. The panel is CC BY 4.0.

## Limitations

See `docs/LIMITATIONS.md`. In short: "active" means the station reported hourly volume in 2024. Stations and miles use FHWA's rural/urban code, while deaths use 2020 Census urban areas. Station counts describe the network, not the accuracy of traffic estimates.

## License and citation

Code: MIT. Data, report, and comment: CC BY 4.0. Cite using `CITATION.cff`.

Maintainer: Emmanuel Oti Nani (ORCID 0009-0009-4175-8962).
