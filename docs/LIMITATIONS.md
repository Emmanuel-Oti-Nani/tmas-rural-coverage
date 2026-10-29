# Limitations

Known limitations of the analysis.

1. **"Active" is defined by volume data.** A station counts as active if it has at least one day of hourly volume in FHWA's 2024 monthly files. 2,841 of the 10,700 listed stations have none. Some of them may report only vehicle classification or weight data. Using all listed stations changes the rural share only slightly (46.2% vs 48.9%).
2. **Two rural definitions.** Stations, road miles, and VMT use FHWA's rural/urban code (based on FHWA-adjusted urban boundaries). Deaths come from the fatality panel, which uses 2020 Census urban areas. For active stations the two labels agree 87.6% of the time. Deaths-per-station ratios mix the definitions and should be read as orders of magnitude.
3. **Station IDs vs physical sites.** Some states give each direction its own ID. A sensitivity check that merges same-class stations within about 300 m leaves 7,085 sites, and the main percentages barely move (see report section 4).
4. **Coverage is not accuracy.** Few stations on a road class does not prove its traffic estimates are wrong. It means TMAS gives little ability to check them.
5. **Short counts are not included.** States collect many short-duration counts that do not go to TMAS.
6. **State coding.** Functional class and coordinates are as reported by states. 50 stations in 2024 lack usable coordinates, and 18 have coordinates just across a state line.
7. **2025 is provisional.** The 2025 station file uses a new layout with two-digit functional codes and no rural/urban suffix. It is mapped by a rule (codes under 10 = rural) and used only as a note.
8. **Nonmotorized counts.** No public TMAS bicycle or pedestrian station data were found. The statement that "only a handful of jurisdictions" submit them comes from a 2025 multistate report (TETC CAPABLE), not from FHWA.
