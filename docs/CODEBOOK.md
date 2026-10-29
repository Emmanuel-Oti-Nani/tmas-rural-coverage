# Codebook

Every column in the processed tables, its meaning, and its source.

## data/processed/stations_2024.csv and stations_2015_2025.csv (one row per state + station ID + year)

| Column | Meaning | Source / how computed |
|---|---|---|
| sid | Unique key: 2-digit state FIPS + "-" + station ID | TMAS station file |
| state_fips, state | State FIPS code and postal abbreviation | TMAS station file |
| station_id | State's station ID | TMAS station file |
| fsys | Functional system 1–7 (1 Interstate, 2 Other freeway/expressway, 3 Other principal arterial, 4 Minor arterial, 5 Major collector, 6 Minor collector, 7 Local). Blank for 2025 (new code layout) | Most common F_System value across the station's lane records |
| ru_fhwa | R or U: FHWA rural/urban code | Suffix of F_System (2015–2024); for 2025, codes under 10 = R, 10+ = U |
| ru_conflict | True if the station's lanes carry both R and U codes | Computed |
| lat, lon | Coordinates in decimal degrees | Median across lane records; pre-2025 values divided by 1,000,000 and longitude made negative; values outside the U.S. bounding box blanked |
| county_code_reported | County code as reported by the state | TMAS station file |
| n_lane_records | Number of direction/lane records | Computed |
| uace20 | 2020 Census urban area code if the station falls inside one | Spatial join, TIGER 2024 UAC20 |
| ru_census | R or U by 2020 Census urban areas | Computed from uace20 |
| county_fips | County containing the coordinates | Spatial join, Census 2023 counties |
| county_state_mismatch | True if the coordinates fall in a different state than reported | Computed |
| days_with_volume_2024 | Days in 2024 with at least one hourly volume record (2024 file only) | 12 monthly TMAS .VOL files |
| active_2024 | days_with_volume_2024 > 0 | Computed |

## table_by_road_class_2024.csv / table_broad_class_deaths_2024.csv

Active 2024 stations by rural/urban and functional system, with road miles (HM-20 2024), VMT in billions (VM-2 2024), stations per 1,000 miles, and stations per billion VMT. The broad-class table adds road deaths in 2020–2024 from the fatality panel (rural deaths = panel `deaths_rural_<class>`; urban = `deaths_<class>` minus rural) and deaths per station. Broad classes: interstate_fwy = 1–2, arterial = 3–4, collector = 5–6, local = 7.

## table_by_state_2024.csv

Per state: active rural and urban stations, rural and urban miles, rural VMT, rural deaths 2020–2024, rural stations per 1,000 rural miles, rural share of stations / miles / deaths, rural deaths per rural station, active rural collector and local stations.

## table_by_county_2024.csv

Per county (3,143, panel geography): rural deaths and all deaths 2020–2024, rural road miles 2024, share of 2020 population that is rural, active stations, active rural stations.

## trend_2015_2025.csv

Per year: stations in the station file, rural and urban by FHWA code, rural share by FHWA and Census definitions, number of states.
