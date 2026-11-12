# Seattle Road Safety — collision hotspot data product (2019–2025)

This project combines three City of Seattle datasets to find where **recorded collisions** occur most often on road segments and at intersections between 2019 and 2025. It produces count-based hotspot tables plus quality evidence. It does **not** estimate which streets are most dangerous per vehicle, because traffic measurements cover only a small share of locations.

**Intended user:** a Seattle transportation analyst or road-safety researcher choosing locations for further investigation.

## Source data (kept unchanged in `data/raw/`)

| File | Records | What one row represents | Main key |
| --- | ---: | --- | --- |
| `CRASHES_2019_2025.csv` | 53,936 | One recorded collision in our 2019–2025 extract | `INCKEY` |
| `Seattle_Streets_1_7907262242317696645.csv` | 23,888 | One current street-network segment | `COMPKEY` |
| `Traffic_Counts_by_Study_20261101.csv` | 64,532 | One traffic-volume study | `STUDY_ID` |

The three files cover different time periods. The Streets file is a current snapshot of the network, not a historical street map for each crash year. The live portals are refreshed regularly (Collisions daily), so their current record counts will differ from these files. Use the SHA-256 checksums in `data/output/quality_metrics.json` to identify the exact files analysed.

**Download date:** all three files were downloaded on **2 November 2026** (confirmed by the group and by the original files' timestamps). The `20261101` in the traffic file name is part of the name given by the portal and is not the download date.

## Where the data came from

1. [SDOT Collisions All Years](https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::sdot-collisions-all-years): SPD/SDOT recorded collision locations and attributes. Our CSV is a project extract, **not** the full live table.
2. [Seattle Streets](https://data.seattle.gov/dataset/Seattle-Streets/w3hh-bqt5): current street names and characteristics. Field documentation: [Seattle_Streets_OD.pdf](https://www.seattle.gov/Documents/Departments/SDOT/GIS/Seattle_Streets_OD.pdf).
3. [Traffic Counts by Study](https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc): study locations, dates and traffic-volume summaries.

The City of Seattle/SDOT produced the original data. We did not measure the collisions, road geometry or traffic volumes ourselves.

## Main fields and units

| Field | Meaning | Unit / note |
| --- | --- | --- |
| `INCKEY` | Unique collision record ID | Identifier |
| `INCDATE` | Recorded collision date | Calendar date (normalized to `Crash_Date` in our pipeline) |
| `ADDRTYPE` | Collision location category (`B` = block/segment, `I` = intersection, `A` = alley) | Category |
| `INTKEY` | Intersection identifier | Identifier |
| `ADDR_SEGINTKEY` | Collision segment/intersection location reference | Identifier |
| `INJURIES` / `SERIOUSINJURIES` / `FATALITIES` | Recorded people affected per collision | People (count) |
| `WEATHER` | Recorded weather description | Category; often missing |
| `COMPKEY` | Street segment key shared by Streets and Traffic | Identifier |
| `ONSTREET` | Street name | Text |
| `SPEEDLIMIT` | **Posted** speed limit, not measured vehicle speed | Miles per hour (SDOT field documentation); 0 appears to be a placeholder |
| `SEGLENGTH` | Street segment length | Feet (SDOT field documentation; matches the GIS shape length) |
| `STUDY_ID` | Traffic-study identifier | Identifier |
| `START_DATE` | Start of traffic study | Calendar date/time |
| `ADT` | Average daily traffic during the study | Vehicles/day during the study, not an annual average |
| `Crash_Count` | Collisions in a location/year group | Collisions (count) |
| `Mean_Study_ADT` | Mean ADT of eligible same-year studies | Vehicles/day during studies; not citywide exposure |

The full dictionary of every raw and output field (196 entries) is in `documentation/data_dictionary.csv`. Each entry names its definition source: SDOT's field documentation ([Collisions](https://www.seattle.gov/Documents/Departments/SDOT/GIS/Collisions_OD.pdf), [Streets](https://www.seattle.gov/Documents/Departments/SDOT/GIS/Seattle_Streets_OD.pdf)), the portal, our pipeline, or observed values. 29 raw fields that the sources do not document are marked as such rather than guessed. Note: the SDOT document's severity codes differ from this snapshot, which uses 1 = Property Damage Only, 2 = Injury, 3 = Serious Injury, 4 = Fatal.

## What we did to the data

- Parsed dates and checked the three source keys for missing or duplicate values (all unique).
- Kept every original collision ID and recorded whether each crash belongs to the segment analysis, the intersection analysis, or neither (`Road_Analysis_Status`).
- Joined segment crashes to Streets (`ADDR_SEGINTKEY` → `COMPKEY`) and to aggregated same-year traffic studies; joined intersection crashes to an aggregated union of street endpoints (`INTKEYLO`/`INTKEYHI`) so that no crash is duplicated.
- Grouped collisions by location and year to produce **counts**, not traffic-adjusted risk scores.
- Kept flagged values and excluded groups visible in the quality evidence instead of silently changing source facts.

The same transformation is implemented twice: visually in Tableau Prep (`../tableau/Seattle_Road_Safety_Final.tflx`) and in Python (`pipeline.py`). Full detail: `documentation/01_PROJECT_SCOPE_AND_ARCHITECTURE.md` and `documentation/04_CLEANING_AND_TABLEAU.md`.

## Outputs (`data/output/`)

| File | Content |
| --- | --- |
| `validated_crashes.csv` | One row per original collision (53,936), with normalized date and analysis status |
| `road_safety_by_segment_year.csv` | Collision counts by street segment and year, with street and traffic attributes |
| `intersection_crashes_by_year.csv` | Collision counts by intersection and year |
| `intersection_hotspots_with_streets.csv` | Intersection counts with pre-aggregated street attributes |
| `crash_scope_summary.csv` | Collisions inside and outside the analysis scope |
| `quality_metrics.json` | Run metrics and SHA-256 checksums of all inputs and outputs |

41,525 of 53,936 collisions (76.99%) enter the segment or intersection summaries. The remaining 12,411 are kept in `validated_crashes.csv` with their exclusion reason (12,215 unmatched location, 196 alley). Excluded does not mean erroneous. Crashes with an unparseable date go to `data/quarantine/` (0 in the current run).

All outputs are plain UTF-8 CSV or JSON. Tableau's versions of the first four outputs are kept in `data/tableau_output/` for comparison.

## How to reproduce the Python outputs

Windows PowerShell, from this folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python pipeline.py
python audit_evidence.py
python pipeline.py
```

Expected: **10/10 tests pass**. The two `pipeline.py` runs produce identical output SHA-256 values (see `evidence/12_repeat_run_verification.json`). Files in `data/raw/` are never modified.

## Folder structure

| Folder | Content |
| --- | --- |
| `data/raw/` | Original source CSVs, unchanged |
| `data/output/` | Python curated outputs and `quality_metrics.json` |
| `data/tableau_output/` | Tableau Prep outputs, kept for comparison |
| `data/quarantine/` | Rows rejected for unparseable dates |
| `../tableau/` | Tableau Prep flow: editable `.tfl` and packaged `.tflx` (with embedded source data) |
| `pipeline.py`, `rules.py`, `profile.py`, `audit_evidence.py` | Python pipeline, validation rules, profiling and evidence generation |
| `tests/` | Automated tests |
| `evidence/` | Profiling, quality scorecard, reconciliation and repeat-run evidence |
| `logs/` | Pipeline run log |
| `documentation/` | Architecture, FAIR, quality, cleaning, Python and governance documents |
| `metadata.json` | Structured Schema.org metadata (sources, licences, checksums, units, creators) |
| `data_contract.yaml` | Data contract in Bitol ODCS v3.2.0 format (5 outputs, 79 columns, 49 quality checks) |
| `scripts/` | `build_data_contract.py` and `validate_data_contract.py` (needs `requirements-contract.txt`) |

## Known limitations

- 12,350 of 53,936 crashes (22.90%) have no weather value; 246 more are recorded as Unknown.
- 140 Streets segments have a posted speed limit of 0 and 20 have none.
- Only 790 of 16,569 segment-year groups (4.77%) have an eligible same-year traffic study, so this is **not** a reliable citywide rate-based risk dataset.
- 41 segment-year and 25 intersection-year groups have no matching Streets record and keep empty street attributes.
- Tableau and Python outputs agree on all crash counts, speed-status flags and segment lengths (corrected 7 November 2026). They still differ in column layout: Tableau's segment output carries extra pass-through columns (see `documentation/04_CLEANING_AND_TABLEAU.md`).
- Street attributes are a current snapshot applied to past crash years.
- A repeatable pipeline proves repeatable calculations, not that the original reports are accurate.

## Licence and reuse

Portal metadata checked on 7 November 2026:

- **Traffic Counts by Study:** Public Domain (attribution: SDOT Traffic Counts Group).
- **Seattle Streets:** no licence shown; only a disclaimer that the City makes no warranty as to accuracy.
- **SDOT Collisions All Years:** no licence shown on the catalog entry.

Because two sources show no explicit licence, **we do not assign CC BY, CC0 or any other licence to this combined package.** Credit the City of Seattle/SDOT as the source when reusing it. See `documentation/02_FAIR_ASSESSMENT.md`.

**Repository:** the link will be added here once the project is published. No DOI has been created.
