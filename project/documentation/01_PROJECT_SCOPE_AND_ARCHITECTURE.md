# 1. Project scope, business question, and architecture

**Working title:** From Raw Seattle Road Safety Data to a Trustworthy, Reproducible Data Product

**Question:** Which Seattle road segments and intersections had the highest *recorded collision counts* in 2019–2025, and which data quality, integration, and temporal-coverage limitations must be checked before using those findings in further analysis or AI?

**Intended user:** Seattle transportation analyst or road-safety researcher. **Decision supported:** prioritize locations for further investigation, *not* infer causal danger, predict future crashes, or make a traffic-normalized risk ranking from these files alone.

## Original snapshots (never edited)

| Source | File | Snapshot rows | Source key | Important use |
| --- | --- | ---: | --- | --- |
| SDOT Collisions All Years | `CRASHES_2019_2025.csv` | 53,936 | `INCKEY` | Crash date, location type, segment/intersection ID, injuries |
| Seattle Streets | `Seattle_Streets_1_7907262242317696645.csv` | 23,888 | `COMPKEY` | Street names, posted speed limit, segment endpoints |
| Traffic Counts by Study | `Traffic_Counts_by_Study_20261101.csv` | 64,532 | `STUDY_ID` | Date-specific traffic study statistics, road references |

Source catalogs: https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::sdot-collisions-all-years ; https://data.seattle.gov/dataset/Seattle-Streets/w3hh-bqt5 ; https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc.

**Important:** The crash file is a filtered, 2019–2025 project snapshot, not necessarily the full live SDOT portal; the live portals are refreshed. Keep the actual CSV SHA-256 checksums under `data/output/quality_metrics.json` rather than confusing the local subset with the live portal total.

## Architecture / data-flow blueprint

1. **Sources and collection:** SDOT collision and GIS data from Seattle Open Data/ArcGIS; traffic study metadata from Seattle Open Data. Original operational systems belong to the **City of Seattle/SDOT**; our group does not administer those systems.
2. **Raw zone:** Downloaded CSV snapshots stored unchanged in `data/raw/` with provenance and hashes. This is **local file storage organized like a small raw data-lake zone**, not a managed lake or warehouse.
3. **ETL transformation:** Tableau Prep visually cleans, unions intersection endpoints, joins aggregated groups, and creates four outputs. Separately, Python (`pipeline.py`) follows load → clean → validate → split → aggregate/enrich → output. Both are batch ETL because transformations occur before publication of curated files.
4. **Trusted/curated zone:** Local CSVs in `data/output/`; Tableau-generated files in `data/tableau_output/`. The latter is retained for comparison, not assumed to be a perfect replica of Python.
5. **Audit zone:** `data/quarantine/`, `logs/`, `evidence/`, and `documentation/` contain rejected rows (if any), run logs, metrics, rules, metadata and definitions.
   - **Outputs:** Python writes five curated files (`validated_crashes.csv`, `road_safety_by_segment_year.csv`, `intersection_crashes_by_year.csv`, `intersection_hotspots_with_streets.csv`, `crash_scope_summary.csv`); the Tableau flow writes the first four. The scope summary is Python-only.
   - **Quarantine rule:** a crash is quarantined only if its date cannot be parsed. In the current run this affects 0 rows, so `quarantine_crashes.csv` contains only a header.
6. **Consumption:** Analysts can query location-year aggregate tables to identify *count hotspots* and assess quality. No production dashboard or deployed ML model is claimed.

**Join relationships:** `Crashes.ADDR_SEGINTKEY` (when `ADDRTYPE=B`) → `Streets.COMPKEY`; `Traffic.COMPKEY + Study_Year` → crash road key + crash year (aggregate first). `Crashes.INTKEY` (when `ADDRTYPE=I`) → the *aggregated* union of `Streets.INTKEYLO` and `Streets.INTKEYHI`. Joining raw endpoint rows directly to crashes would duplicate collisions; aggregate endpoint facts before joining.

**Traffic eligibility and coverage:** A traffic study is used only if its start year is 2019–2025, `TRAFFIC_FLOW_DIR_ID = 11`, its cleaned ADT is greater than 0, and it has a road key (`pipeline.py`, `aggregate_traffic`). This leaves 4,730 eligible studies in 3,037 road-year groups. Traffic is joined to road-segment crashes only, not to intersections. Only **790 of 16,569 segment-year groups (4.8%)** have a same-year traffic study, so traffic-normalized risk cannot be calculated for most locations.

**Unmatched location groups:** 41 segment-year groups and 25 intersection-year groups have no matching record in the Streets snapshot. The left joins keep them, with empty street attributes, so no crashes are lost.

## Scope reconciliation

| Category | Records |
| --- | ---: |
| Included road-segment crashes | 23,774 |
| Included intersection crashes | 17,751 |
| Excluded: source location not matched | 12,215 |
| Excluded: alley | 196 |
| **Total source crashes** | **53,936** |

All 53,936 original crash IDs are retained in the *validated crashes* output with an explicit `Road_Analysis_Status`. **Analytically excluded is not equivalent to erroneous or quarantined.** The analytical summaries contain 41,525 included crashes (76.99%).

## What must not be claimed

- `STATUS=Matched` is the SDOT source's location-matching status; it is **not** proof of a match to the separate Streets snapshot.
- `SPEEDLIMIT` is a posted speed limit, **not** measured vehicle speed; zero may be a placeholder.
- `Mean_Study_ADT` averages eligible traffic studies. The data do not establish consistent full-year vehicle exposure.
- Segment and intersection summaries represent different crash populations. Do **not** add their counts to the same road segment.
- Street attributes may be current snapshots applied to historical collision years; don't describe them as verified historical road conditions.
