#!/usr/bin/env python3
"""Step 5: build the technical report and the public comment from stats.json.

This script writes the technical report and the public
comment as web pages and PDFs (report/ and comment/). Every number in them is read
from report/stats.json, so the text cannot disagree with the data. They carry a
DRAFT banner unless run with --final. The report's DOI is
read from report/DOI.txt once Zenodo has issued it.
"""
import base64, datetime, json, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL = "--final" in sys.argv
S = json.load(open(f"{ROOT}/report/stats.json"))
A = json.load(open(f"{ROOT}/AUTHORS.json"))["authors"][0]
doi_file = f"{ROOT}/report/DOI.txt"
DOI = open(doi_file).read().strip() if os.path.exists(doi_file) else "[REPORT DOI PENDING]"
PANEL_DOI = "10.5281/zenodo.23547649"
TODAY = datetime.date.today().strftime("%B %-d, %Y")
VERSION = "1.0"
bc = pd.DataFrame(S["broad_class"]).set_index(["area", "road_class"])
st = pd.read_csv(f"{ROOT}/data/processed/table_by_state_2024.csv")
f0 = lambda x: f"{x:,.0f}"
f1 = lambda x: f"{x:,.1f}"
def b(area, cls, col): return bc.loc[(area, cls), col]

CSS = """
@page { size: Letter; margin: 0.9in 0.9in 0.9in 0.9in; }
body { font-family: 'DejaVu Serif', Georgia, serif; font-size: 10.5pt; line-height: 1.42; color: #111; }
h1 { font-size: 17pt; line-height: 1.2; margin: 0 0 6pt; font-family: 'DejaVu Sans', sans-serif; }
h2 { font-size: 12pt; margin: 16pt 0 4pt; font-family: 'DejaVu Sans', sans-serif; }
h3 { font-size: 10.5pt; margin: 10pt 0 2pt; font-family: 'DejaVu Sans', sans-serif; break-after: avoid; page-break-after: avoid; }
h2 { break-after: avoid; page-break-after: avoid; }
.cap { break-before: avoid; }
p { margin: 0 0 7pt; text-align: left; }
.meta { font-family: 'DejaVu Sans', sans-serif; font-size: 9pt; color: #333; margin-bottom: 10pt; }
.box { border: 1px solid #bbb; background: #f6f6f4; padding: 8pt 10pt; margin: 8pt 0 10pt; }
.draft { background: #e34948; color: white; font: bold 9pt 'DejaVu Sans', sans-serif; padding: 4pt 8pt; margin-bottom: 8pt; }
table { page-break-inside: avoid; border-collapse: collapse; width: 100%; font: 8.6pt 'DejaVu Sans', sans-serif; margin: 6pt 0 4pt; }
th, td { border-bottom: 1px solid #ddd; padding: 2.5pt 4pt; text-align: right; }
th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align: left; }
th { border-bottom: 1.5px solid #555; }
.cap { font: 8.5pt 'DejaVu Sans', sans-serif; color: #444; margin: 2pt 0 10pt; }
img { width: 100%; }
figure { margin: 8pt 0; page-break-inside: avoid; }
ol li, ul li { margin-bottom: 4pt; }
.refs p { font-size: 9pt; padding-left: 14pt; text-indent: -14pt; margin-bottom: 4pt; }
.sig { margin-top: 14pt; }
"""

def img(name):
    data = base64.b64encode(open(f"{ROOT}/report/figures/{name}.png", "rb").read()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="{name}">'

banner = "" if FINAL else '<div class="draft">DRAFT for author verification. Not for distribution.</div>'

# ---------------- shared numbers ----------------
N = dict(
    listed=f0(S["stations_2024_listed"]), active=f0(S["stations_2024_active"]), notrep=f0(S["listed_not_reporting_2024"]),
    rural_st=f0(S["rural_stations_active_fhwa"]), urban_st=f0(S["urban_stations_active_fhwa"]),
    sh_st=f1(S["rural_share_stations_fhwa_active"]), sh_st_c=f1(S["rural_share_stations_census_active"]),
    sh_mi=f1(S["rural_share_miles_2024"]), sh_vmt=f1(S["rural_share_vmt_2024"]), sh_d=f1(S["rural_share_deaths_2024"]),
    r_mi=f0(S["rural_miles_2024"]), r_vmt=f1(S["rural_vmt_bil_2024"]),
    r_pm=f"{S['rural_stations_per_1000mi']:.2f}", u_pm=f"{S['urban_stations_per_1000mi']:.2f}",
    r_pv=f"{S['rural_stations_per_bvmt']:.2f}", u_pv=f"{S['urban_stations_per_bvmt']:.2f}",
    ratio=f1(S["urban_to_rural_density_ratio_miles"]),
    low_mi_sh=f1(S["rural_collector_local_miles_share_of_rural"]), low_st_sh=f1(S["rural_collector_local_station_share_of_rural"]),
    low_st=f0(S["rural_collector_local_stations"]), low_mi=f"{S['rural_collector_local_miles']/1e6:.2f} million",
    low_d=f0(S["rural_low_deaths_2020_2024"]), low_d_sh=f1(S["rural_deaths_collector_local_share"]),
    loc_st=f0(S["rural_local_stations"]), loc_mi=f"{S['rural_local_miles']/1e6:.2f} million",
    loc_dps=f0(b("Rural", "local", "deaths_per_station")), int_dps=f0(b("Rural", "interstate_fwy", "deaths_per_station")),
    col_dps=f0(b("Rural", "collector", "deaths_per_station")), loc_d=f0(b("Rural", "local", "deaths_2020_2024")),
    low_pv=f"{S['rural_low_stations_per_bvmt']:.2f}", high_pv=f"{S['rural_high_stations_per_bvmt']:.2f}",
    low_vmt_sh=f1(S["rural_low_vmt_share_of_rural"]),
    rd5=f0(S["rural_deaths_2020_2024"]),
    nocty=f0(S["counties_no_station"]), ncty=f0(S["counties"]), nocty_pct=f1(S["counties_no_station_pct"]),
    mr=f0(S["mostly_rural_counties"]), mr_pct=f1(S["mostly_rural_counties_no_station_pct"]), mu_pct=f1(S["mostly_urban_counties_no_station_pct"]),
    nocty_d=f0(S["rural_deaths_in_no_station_counties"]), nocty_d_pct=f1(S["rural_deaths_in_no_station_counties_pct"]),
    nocty_mi_pct=f1(S["rural_miles_in_no_station_counties_pct"]),
    gr_u=f0(S["urban_growth_2015_2024_pct"]), gr_r=f0(S["rural_growth_2015_2024_pct"]),
    new=f0(S["new_stations_2015_2024"]), new_r=f0(S["new_rural_2015_2024"]), new_u=f0(S["new_urban_2015_2024"]),
    sh15=f1(S["trend"][0]["rural_share_fhwa"]), sh24=f1([t for t in S["trend"] if t["year"] == 2024][0]["rural_share_fhwa"]),
    sh25=f1([t for t in S["trend"] if t["year"] == 2025][0]["rural_share_fhwa"]),
    st_below_d=f0(S["states_rural_share_stations_below_deaths"]), st_n=f0(S["states_with_rural_miles"]),
    st_ge6=f0(S["states_rural_low_ge6"]), st_lt6=f0(S["states_with_rural_miles"] - S["states_rural_low_ge6"]),
    st_zero=" and ".join(S["states_rural_low_zero"]),
    med=f"{S['state_rural_density_median']:.2f}", agree=f1(S["agree_fhwa_census_pct"]),
    days_r=S["median_days_R"], days_u=S["median_days_U"],
    lanes=f0(S["stations_2024_lane_records"]), nocoord=f0(S["stations_2024_no_coords"]),
    rd24=f0(S["rural_deaths_2024"]), u_mi=f0(S["urban_miles_2024"]),
)
N["mo"] = st[st.state == "MO"].iloc[0]

def class_table():
    names = {"interstate_fwy": "Interstates and other freeways", "arterial": "Arterials", "collector": "Collectors", "local": "Local roads"}
    rows = ""
    for area in ("Rural", "Urban"):
        for k, nm in names.items():
            r = bc.loc[(area, k)]
            rows += (f"<tr><td>{area}</td><td>{nm}</td><td>{f0(r.stations)}</td><td>{f0(r.miles)}</td><td>{f1(r.vmt_billion)}</td>"
                     f"<td>{r.stations / (r.miles / 1000):.2f}</td><td>{r.stations_per_bvmt:.2f}</td><td>{f0(r.deaths_2020_2024)}</td><td>{f1(r.deaths_per_station)}</td></tr>")
    return ("<table><tr><th>Area</th><th>Road class</th><th>Active stations</th><th>Road miles</th><th>VMT (billion)</th>"
            "<th>Stations per 1,000 mi</th><th>Stations per billion VMT</th><th>Deaths 2020-24</th><th>Deaths per station</th></tr>" + rows + "</table>")

def state_table():
    t = st[st.rural_miles > 0].sort_values("rural_stations_per_1000mi")
    pick = pd.concat([t.head(10), t.tail(5)])
    rows = ""
    for i, r in enumerate(pick.itertuples()):
        if i == 10:
            rows += '<tr><td colspan="7" style="text-align:center;color:#666">...</td></tr>'
        rows += (f"<tr><td>{r.state}</td><td></td><td>{f0(r.rural_stations)}</td><td>{f0(r.rural_miles)}</td><td>{r.rural_stations_per_1000mi:.2f}</td>"
                 f"<td>{f0(r.rural_collector_local_stations)}</td><td>{f1(r.rural_share_stations)} / {f1(r.rural_share_deaths_2020_2024)}</td></tr>")
    return ("<table><tr><th>State</th><th></th><th>Active rural stations</th><th>Rural road miles</th><th>Rural stations per 1,000 mi</th>"
            "<th>Rural collector and local stations</th><th>Rural share of stations / of deaths (%)</th></tr>" + rows + "</table>")

REFS = f"""
<div class="refs">
<p>Federal Highway Administration. (2026, October 9). Agency information collection activities: Notice of request for an extension of currently approved information collection [Travel Monitoring Analysis System (TMAS), OMB Control No. 2125-0587]. <i>Federal Register</i>, 91(195), 64735. Docket No. FHWA-2026-1090. FR Doc. 2026-20718.</p>
<p>Federal Highway Administration. (2022). <i>Traffic Monitoring Guide</i> (2022 ed.), Chapter 3. https://www.fhwa.dot.gov/policyinformation/tmguide/tmg_2022/traffic-data-methodologies.cfm</p>
<p>Federal Highway Administration. (2024). <i>2016 Traffic Monitoring Guide nonmotorized data format, August 2024 updates.</i> https://www.fhwa.dot.gov/policyinformation/tmguide/2016_TMG_nonmotorized_20241008.pdf</p>
<p>Federal Highway Administration. (2025). <i>U.S. traffic volume data</i> (TMAS station and monthly continuous count files, 2015-2025). Accessed {TODAY}. https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/</p>
<p>Federal Highway Administration. (2025). <i>Highway Statistics 2024</i>, Tables HM-20 (public road length) and VM-2 (functional system travel). https://www.fhwa.dot.gov/policyinformation/statistics/2024/</p>
<p>Nani, E. O. (2026). <i>U.S. Rural Road Fatality County Panel, 2015-2024</i> (Version 1.0.0) [Data set]. Zenodo. https://doi.org/{PANEL_DOI}</p>
<p>Transportation Engineering and Technology Coalition (TETC). (2025). <i>CAPABLE: Count All Pedestrian and Bicycle Locations</i> (final draft report). https://tetcoalition.org/wp-content/uploads/2025/01/CAPABLE-Report-FINAL-DRAFT.pdf</p>
<p>U.S. Census Bureau. (2024). <i>TIGER/Line Shapefiles: 2020 Urban Areas</i>; (2023) <i>Cartographic boundary files: counties</i>. https://www.census.gov/geographies/mapping-files.html</p>
</div>"""

author_line = f'{A["name"]} &middot; {A["affiliation"]} &middot; ORCID <a href="https://orcid.org/{A["orcid"]}">{A["orcid"]}</a> &middot; {A["email"]}'

# ======================= TECHNICAL REPORT =======================
report = f"""<!doctype html><html><head><meta charset="utf-8"><title>Rural Coverage of TMAS Count Stations</title><style>{CSS}</style></head><body>
{banner}
<div class="meta">Technical Report &middot; Version {VERSION} &middot; {TODAY} &middot; DOI: {DOI}</div>
<h1>How Well Do Federal Traffic Count Stations Cover Rural Roads? Evidence from the Travel Monitoring Analysis System, 2015&ndash;2024</h1>
<div class="meta">{author_line}<br>License: CC BY 4.0. Data and code: https://github.com/{A["github"]}/tmas-rural-coverage</div>

<div class="box"><b>Key findings</b>
<ul>
<li>In 2024, {N['active']} permanent count stations reported hourly traffic volume to the Federal Highway Administration's Travel Monitoring Analysis System (TMAS). Of these, {N['sh_st']}% are on roads coded rural. Rural roads carry {N['sh_vmt']}% of vehicle-miles traveled (VMT), make up {N['sh_mi']}% of public road miles, and account for {N['sh_d']}% of road deaths.</li>
<li>Per vehicle-mile, rural roads are not under-covered: they have {N['r_pv']} stations per billion VMT against {N['u_pv']} for urban roads. Per road mile, they have {N['ratio']} times fewer stations ({N['r_pm']} vs {N['u_pm']} per 1,000 miles).</li>
<li>Coverage is concentrated on rural interstates and arterials. Rural collectors and local roads are {N['low_mi_sh']}% of rural mileage and carry {N['low_vmt_sh']}% of rural VMT, and {N['low_d_sh']}% of rural road deaths in 2020&ndash;2024 ({N['low_d']} deaths) occurred on them. Yet they have {N['low_st_sh']}% of rural stations ({N['low_st']}). Rural local roads have {N['loc_st']} stations for {N['loc_mi']} miles: {N['loc_dps']} deaths per station, against {N['int_dps']} on rural interstates.</li>
<li>{N['nocty']} of {N['ncty']} counties ({N['nocty_pct']}%) had no station reporting volume in 2024, including {N['mr_pct']}% of mostly rural counties. Those counties recorded {N['nocty_d_pct']}% of the nation's rural road deaths in 2020&ndash;2024.</li>
<li>From 2015 to 2024 the number of stations in the TMAS station file grew {N['gr_u']}% on urban roads and {N['gr_r']}% on rural roads. The rural share fell from {N['sh15']}% to {N['sh24']}%.</li>
<li>The public TMAS download contains no bicycle or pedestrian count stations, so rural nonmotorized coverage cannot be assessed from public data.</li>
</ul></div>

<h2>1. Why station coverage matters</h2>
<p>States operate permanent, continuously recording traffic counters and report their data to FHWA monthly through TMAS (OMB Control No. 2125-0587). These continuous count stations do two jobs. Directly, they measure traffic where they sit. Indirectly, they supply the seasonal and day-of-week adjustment factors that convert short, temporary counts into annual average daily traffic on the much larger network that has no permanent counter. Annual average daily traffic, in turn, is the basis for the vehicle-miles traveled estimates behind national travel trends and fatality rates per 100 million VMT.</p>
<p>The Traffic Monitoring Guide (TMG) asks states to build factor groups from continuous stations and recommends "a minimum of 6 per factor group" for non-recreational roads (FHWA, 2022, Section 3.1.4.5). Its minimum recommended volume factor groups place every rural road below the interstate (HPMS functional codes 2 through 7, from rural freeways to rural local roads) in one "Other Rural" group (Table 3-1). A state can therefore meet the minimum with stations on rural arterials only, and apply their seasonal pattern to rural collectors and local roads that carry a different mix of farm, freight, school, and recreational traffic.</p>
<p>FHWA has published a 60-day notice to extend the TMAS collection (FHWA, 2026). This report measures rural coverage with public TMAS data to inform comments on that notice.</p>

<h2>2. Data and methods</h2>
<p><b>Stations.</b> FHWA's annual TMAS station files list each station by direction and lane. The 2024 file has {N['lanes']} lane records, which collapse to {N['listed']} unique stations (state plus station ID). Each record carries a functional system code with a rural (R) or urban (U) suffix and coordinates. Not every listed station reports data, so the main analysis uses the {N['active']} stations that appear in at least one of FHWA's twelve 2024 monthly hourly-volume files ("active"). The {N['notrep']} listed stations without 2024 volume records may report classification or weight data only, or may be inactive. The station file's discontinuation field is not consistent enough to tell these cases apart.</p>
<p><b>Rural and urban.</b> The main analysis uses FHWA's own rural/urban code, which matches the definition used for road miles and VMT in Highway Statistics. As a check, each station was also placed in or out of a 2020 Census urban area. The two labels agree for {N['agree']}% of active stations, and under the Census definition the rural share of active stations is {N['sh_st_c']}%.</p>
<p><b>Denominators.</b> Road miles and VMT by functional system come from Highway Statistics 2024 Tables HM-20 and VM-2 (50 states and DC). Road deaths come from the author's U.S. Rural Road Fatality County Panel (Nani, 2026), which assigns each FARS fatal crash to a county and classifies it as rural or urban using 2020 Census urban areas. Stations were assigned to counties from their coordinates.</p>
<p><b>Trend.</b> Station counts for 2015&ndash;2024 use each year's station file with the same rules. The 2025 file uses a revised record layout with two-digit functional codes and no R/U suffix. It is shown separately and treated as provisional.</p>

<h2>3. Results</h2>
<h3>3.1 National shares</h3>
<figure>{img("fig1_rural_shares")}</figure>
<p class="cap">Figure 1. Rural share of U.S. public road miles, VMT, road deaths, and active TMAS count stations, 2024.</p>
<p>Rural stations number {N['rural_st']}, against {N['urban_st']} urban. That is {N['r_pm']} stations per 1,000 rural road miles (one per {f0(S['rural_miles_per_station'])} miles) and {N['u_pm']} per 1,000 urban miles (one per {f0(S['urban_miles_per_station'])} miles). Relative to traffic, rural roads have more stations than urban roads. The station network is roughly proportional to rural deaths, but far below rural mileage.</p>

<h3>3.2 By road class</h3>
{class_table()}
<p class="cap">Table 1. Active TMAS stations (2024, FHWA rural/urban code) against road miles and VMT (Highway Statistics 2024) and road deaths (2020&ndash;2024, Census 2020 urban areas) by road class. Interstates and freeways are HPMS codes 1&ndash;2, arterials 3&ndash;4, collectors 5&ndash;6, local roads 7. Urban deaths are all deaths on the class minus rural deaths.</p>
<figure>{img("fig2_deaths_per_station")}</figure>
<p class="cap">Figure 2. Road deaths in 2020&ndash;2024 per active count station, by road class.</p>
<p>The gap is a road-class gap more than a rural-urban gap. Rural interstates have {S['rural_interstate_per_1000mi']:.1f} stations per 1,000 miles. Rural minor collectors have {S['rural_minor_collector_per_1000mi']:.2f}, and rural local roads {S['rural_local_per_1000mi']:.2f}. Even per vehicle-mile, rural collectors and local roads have {N['low_pv']} stations per billion VMT, against {N['high_pv']} on rural interstates and arterials. Urban collectors and local roads are covered even more thinly per VMT. In rural areas, however, these roads are where most of the mileage lies and where {N['low_d_sh']}% of deaths occur.</p>
<p>By state, {N['st_ge6']} of {N['st_n']} states have at least six active stations on rural collectors and local roads combined, the TMG's minimum for a single factor group. {N['st_lt6']} do not, and {N['st_zero']} reported none.</p>

<h3>3.3 By county</h3>
<figure>{img("fig4_map")}</figure>
<p class="cap">Figure 3. Active TMAS stations in 2024 and counties without one (lower 48 states).</p>
<p>{N['nocty']} counties ({N['nocty_pct']}%) had no active station in 2024. Among the {N['mr']} counties where at least half the population lived outside urban areas in 2020, {N['mr_pct']}% had none, against {N['mu_pct']}% of other counties. Counties without a station hold {N['nocty_mi_pct']}% of rural road miles and recorded {N['nocty_d']} rural road deaths in 2020&ndash;2024 ({N['nocty_d_pct']}% of the national rural total). A county without a station still has traffic estimates. They come from short counts factored with patterns measured elsewhere.</p>

<h3>3.4 By state</h3>
{state_table()}
<p class="cap">Table 2. The ten states with the fewest active rural stations per 1,000 rural road miles, and the five with the most (2024). The median state has {N['med']}. Full table in the data repository.</p>
<p>In {N['st_below_d']} of {N['st_n']} states, the rural share of active stations is below the rural share of road deaths. Missouri, for example, has {int(N['mo'].rural_stations)} active rural stations ({N['mo'].rural_stations_per_1000mi:.2f} per 1,000 rural miles), {int(N['mo'].rural_collector_local_stations)} of them on rural collectors or local roads.</p>

<h3>3.5 Trend, 2015&ndash;2024</h3>
<figure>{img("fig3_trend")}</figure>
<p class="cap">Figure 4. Stations listed in the TMAS station file by FHWA rural/urban code, 2015&ndash;2024.</p>
<p>The station file grew by {N['new']} stations between 2015 and 2024. {N['new_u']} were urban and {N['new_r']} rural. The provisional 2025 file lists more stations under the new layout, with a rural share of {N['sh25']}%.</p>

<h3>3.6 Bicycle and pedestrian counts</h3>
<p>TMAS accepts nonmotorized count data, and the TMG nonmotorized station record already includes latitude, longitude, and a functional class and area type (urban or rural) field (FHWA, 2024). FHWA's public TMAS download, however, contains only motorized station records. A 2025 multistate review reported that "only a handful of jurisdictions" had submitted nonmotorized data to TMAS (TETC, 2025, p. 26). The rural coverage of federal bicycle and pedestrian counts therefore cannot be measured from public sources. Rural pedestrian and cyclist deaths have no published exposure denominator from TMAS at all.</p>

<h2>4. Limitations</h2>
<ol>
<li>"Active" means at least one day of hourly volume in a 2024 monthly file. Stations reporting only classification or weight data are counted as not active.</li>
<li>Station and mileage counts use FHWA's rural/urban code (adjusted urban boundaries). Deaths use 2020 Census urban areas. The labels agree for {N['agree']}% of stations. Per-station death ratios mix the two and should be read as orders of magnitude.</li>
<li>Station functional codes are as reported by states, and {N['nocoord']} 2024 stations lack usable coordinates (excluded from county counts).</li>
<li>Station counts measure the network, not the accuracy of the resulting traffic estimates. A sparse network does not by itself prove estimates are biased. It means their accuracy on low-class rural roads cannot be checked from TMAS.</li>
<li>Some states give each direction of travel its own station ID. Collapsing active stations of the same road class within about 300 meters into one physical site gives {f0(S['sites_active'])} sites. The rural share ({f1(S['sites_rural_share'])}%) and the share of rural sites on collectors and local roads ({f1(S['sites_rural_collector_local_share_of_rural'])}%) barely change.</li>
<li>States also run short-duration counts that are not reported to TMAS and are not counted here.</li>
</ol>

<h2>5. Implications</h2>
<p>The TMAS station network follows traffic volume, which is what it was designed to do. Rural road safety programs, however, need exposure on the rural collectors and local roads where many rural deaths occur. On those roads TMAS has few or no permanent stations, so the denominators of rural fatality rates rest on factors borrowed from busier roads. Low-cost steps within the existing collection could make this visible and start to close the gap. These include publishing coverage by road class each year, reporting a rural low-volume factor group, publishing an active-station flag, and releasing the nonmotorized station file.</p>

<h2>Data availability</h2>
<p>All inputs are public. Code, processed tables, a quality-assurance report, and provenance records (file sizes and SHA-256 hashes) are in the project repository and archived with this report at DOI {DOI}.</p>
<h2>References</h2>
{REFS}
</body></html>"""

# ======================= PUBLIC COMMENT =======================
comment = f"""<!doctype html><html><head><meta charset="utf-8"><title>Comment on FHWA-2026-1090</title><style>{CSS}
body {{ font-size: 11pt; }}</style></head><body>
{banner}
<div class="meta">Docket No. FHWA-2026-1090 &middot; OMB Control No. 2125-0587 &middot; FR Doc. 2026-20718, 91 FR 64735 (October 9, 2026)</div>
<h1 style="font-size:14pt">Comment on the Travel Monitoring Analysis System (TMAS) information collection: rural road and nonmotorized coverage of count stations</h1>
<div class="meta">Submitted by {A["name"]}, {A["affiliation"]}<br>ORCID {A["orcid"]}<br>{TODAY}</div>

<p>I submit this comment in my individual capacity as an independent researcher in transportation and regional planning. I do not represent any agency or organization. The comment draws on a technical report I prepared from public FHWA, Census, and FARS data: <i>How Well Do Federal Traffic Count Stations Cover Rural Roads? Evidence from the Travel Monitoring Analysis System, 2015&ndash;2024</i> (DOI {DOI}). The report's code and data are public.</p>

<h2>1. I support extending the collection</h2>
<p>The notice states that TMAS data will be used to "evaluate changes in vehicular and nonmotorized travel in order to assess impacts on highway safety." TMAS is the national compilation of states' continuous traffic counts, and it supports the travel estimates behind fatality rates. In response to the notice's first question, the collection is necessary, and I support its extension. My comments address the third question: how FHWA can improve the quality, usefulness, and clarity of the information collected. Each recommendation uses data FHWA already receives, so none should add meaningful burden for respondents (the second and fourth questions).</p>

<h2>2. What the public TMAS data show about rural coverage</h2>
<p>Using FHWA's 2024 TMAS station file and the twelve 2024 monthly volume files, I identified {N['active']} stations that reported hourly volume in 2024. I compared them with Highway Statistics 2024 (Tables HM-20 and VM-2) and with FARS-based county death counts.</p>
<ol>
<li><b>Rural roads are covered in proportion to traffic, not mileage.</b> Rural roads have {N['sh_st']}% of active stations, {N['sh_vmt']}% of VMT, {N['sh_mi']}% of road miles, and {N['sh_d']}% of 2024 road deaths. That is {N['r_pv']} stations per billion VMT (urban: {N['u_pv']}) but only {N['r_pm']} stations per 1,000 miles (urban: {N['u_pm']}).</li>
<li><b>Rural collectors and local roads are almost unmonitored.</b> They are {N['low_mi_sh']}% of rural road miles and carry {N['low_vmt_sh']}% of rural VMT. In 2020&ndash;2024, {N['low_d']} people ({N['low_d_sh']}% of rural road deaths) died on them. They have {N['low_st']} active stations ({N['low_st_sh']}% of rural stations). Rural local roads have {N['loc_st']} stations for {N['loc_mi']} miles, or {N['loc_dps']} deaths per station, compared with {N['int_dps']} on rural interstates. Only {N['st_ge6']} of {N['st_n']} states have at least six active stations on these roads combined, the number the Traffic Monitoring Guide (TMG) recommends as a minimum for a single factor group.</li>
<li><b>Many rural counties have no station at all.</b> {N['nocty']} of {N['ncty']} counties had no active station in 2024, including {N['mr_pct']}% of mostly rural counties. These counties recorded {N['nocty_d_pct']}% of U.S. rural road deaths in 2020&ndash;2024.</li>
<li><b>Growth has been mostly urban.</b> Between 2015 and 2024 the stations listed in TMAS grew {N['gr_u']}% on urban roads and {N['gr_r']}% on rural roads.</li>
<li><b>Nonmotorized coverage cannot be assessed.</b> The public TMAS download contains no bicycle or pedestrian stations, even though TMAS accepts these data and the TMG nonmotorized station record already includes coordinates and an urban/rural field.</li>
</ol>
<p>These figures do not show that rural traffic estimates are wrong. They show that, for most rural road mileage, TMAS offers little means to check them. The TMG's minimum volume factor groups (Table 3-1) combine all rural roads below the interstate into one "Other Rural" group. A state can meet that minimum with stations on rural arterials alone, and then apply their seasonal patterns to rural collectors and local roads.</p>
<figure>{img("fig2_deaths_per_station")}</figure>
<p class="cap">Figure 1. Road deaths in 2020&ndash;2024 per TMAS station that reported volume in 2024, by road class. From the technical report (DOI {DOI}).</p>

<h2>3. Recommendations</h2>
<ol>
<li><b>Publish an annual coverage table.</b> With each year's TMAS release, FHWA could publish, by state, the number of stations that reported data, by functional system and rural/urban area, next to HM-20 mileage. This uses only data FHWA already holds.</li>
<li><b>Add an "active this year" flag and fix field consistency in the public station file.</b> In 2024, {N['notrep']} of {N['listed']} listed stations had no volume records, and the discontinuation field cannot separate inactive stations from classification-only or weight-only sites. The 2025 file also changed the functional-code layout and dropped the rural/urban suffix. Its rural/urban area should be stated explicitly.</li>
<li><b>Encourage a separate rural low-volume factor group.</b> In the TMAS instructions or the next TMG update, FHWA could recommend that states with substantial rural collector and local mileage keep a factor group for those roads, with at least six continuous stations. Where a state does not, it could report which factor group it applies to those roads.</li>
<li><b>Release the nonmotorized station file.</b> FHWA could publish TMAS bicycle and pedestrian station locations, with their urban/rural field, and the number of jurisdictions submitting. This would let researchers and states see where rural nonmotorized counts are missing.</li>
<li><b>Allow and encourage rural sites in coverage gaps.</b> FHWA could point states to counties and road classes with no continuous station, especially those with high rural death counts, when they add or relocate sites.</li>
</ol>

<h2>4. Conclusion</h2>
<p>TMAS should be extended. Small changes to how its data are reported and published would show where rural roads are counted and where they are not. They would help states place stations where rural people are dying, at little or no added burden. The full analysis, data, and code are available at DOI {DOI}.</p>
<p class="sig">Respectfully submitted,<br><br>{A["name"]}<br>{A["affiliation"]}<br>ORCID {A["orcid"]}</p>

<h2>References</h2>
<div class="refs"><p>Nani, E. O. ({datetime.date.today().year}). <i>How Well Do Federal Traffic Count Stations Cover Rural Roads? Evidence from the Travel Monitoring Analysis System, 2015&ndash;2024</i> (Technical Report v{VERSION}). Zenodo. https://doi.org/{DOI}</p></div>
{REFS}
</body></html>"""

summary = f"""Comment of {A["name"]}, {A["affiliation"]} (individual capacity), on Docket FHWA-2026-1090, Travel Monitoring Analysis System (OMB 2125-0587).

I support extending the TMAS collection. My attached comment addresses the quality and usefulness of the data for rural roads, based on a technical report built from public FHWA, Census and FARS data (DOI {DOI}).

Key findings (2024): {N['active']} TMAS stations reported volume. Rural roads have {N['sh_st']}% of them, {N['sh_mi']}% of road miles, {N['sh_vmt']}% of VMT and {N['sh_d']}% of road deaths. Rural collectors and local roads are {N['low_mi_sh']}% of rural miles and had {N['low_d']} deaths in 2020-2024, but have only {N['low_st']} stations. Rural local roads have {N['loc_st']} stations for {N['loc_mi']} miles. {N['nocty']} of {N['ncty']} counties had no active station, and they recorded {N['nocty_d_pct']}% of rural road deaths. The public TMAS download has no bicycle or pedestrian stations.

Recommendations, all using data FHWA already receives: (1) publish an annual coverage table by state, road class and rural/urban area; (2) add an active-station flag and consistent rural/urban coding to the public station file; (3) encourage a separate rural low-volume factor group with at least six continuous stations; (4) publish the nonmotorized station file with its urban/rural field; (5) direct new or relocated sites toward uncovered rural counties and road classes.

Full comment attached (PDF).
"""

os.makedirs(f"{ROOT}/comment", exist_ok=True)
open(f"{ROOT}/report/report.html", "w").write(report)
open(f"{ROOT}/comment/comment.html", "w").write(comment)
open(f"{ROOT}/comment/regulations_gov_summary.txt", "w").write(summary)
print("summary characters:", len(summary))

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.launch()
    for src, dst in ((f"{ROOT}/report/report.html", f"{ROOT}/report/Nani_TMAS_Rural_Coverage_Technical_Report.pdf"),
                     (f"{ROOT}/comment/comment.html", f"{ROOT}/comment/Nani_Comment_FHWA-2026-1090.pdf")):
        pg = br.new_page(); pg.goto("file://" + src); pg.wait_for_timeout(300)
        pg.pdf(path=dst, format="Letter", print_background=True, display_header_footer=True,
               header_template="<span></span>",
               footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#666"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
               margin={"top": "0.8in", "bottom": "0.8in", "left": "0.9in", "right": "0.9in"})
        print("wrote", dst)
    br.close()
