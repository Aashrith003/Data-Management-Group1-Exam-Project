# Seattle Road Safety — From Raw Open Data to a Trustworthy, Reproducible Data Product

**SRH University · Data Management · Group 1**
Pulakanti Aashrith Reddy · Nukala Megha Sri Sai Vardhan · Jonnala Bhavya Sri · Nagothi Ram Dileep

This repository contains our data-management examination project. We combine three public City of Seattle datasets (collisions, streets and traffic studies) into curated tables of **recorded collision counts by road segment and intersection, 2019–2025**. The same transformation is built twice, visually in **Tableau Prep** and in a tested **Python** pipeline, and both produce the same results. Every quality problem we found is documented, flagged and kept visible instead of being silently "cleaned".

> **Question:** Which Seattle road segments and intersections had the highest *recorded* collision counts in 2019–2025, and which data-quality, integration and coverage limits must be checked before those findings are used in further analysis or AI?
>
> **Answer in one line:** The data supports a reliable ranking of *recorded collision counts*, but **not** traffic-adjusted risk, because only 4.77% of segment-years have a same-year traffic study.

---

## Contents

1. [What is in this folder](#1-what-is-in-this-folder)
2. [Team and roles](#2-team-and-roles)
3. [Source data](#3-source-data)
4. [Architecture](#4-architecture)
5. [Results](#5-results)
6. [Data quality findings](#6-data-quality-findings)
7. [FAIR assessment](#7-fair-assessment)
8. [Tableau Prep and Python parity](#8-tableau-prep-and-python-parity)
9. [How to reproduce](#9-how-to-reproduce)
10. [Data contract (ODCS v3.2.0)](#10-data-contract-odcs-v320)
11. [Governance and AI readiness](#11-governance-and-ai-readiness)
12. [Limitations](#12-limitations)
13. [Licence and attribution](#13-licence-and-attribution)

---

## 1. What is in this folder

```text
DM_Project_Group1/
├── README.md                         ← this file
├── tableau/
│   ├── Seattle_Road_Safety_Final.tflx   packaged Tableau Prep flow (includes the 3 source CSVs)
│   └── Seattle_Road_Safety_Final.tfl    editable flow
└── project/                          ← runnable project: run all commands from here
    ├── pipeline.py                   Python ETL: load → clean → validate → classify → aggregate → enrich → output
    ├── rules.py                      quality gates (STOP rules)
    ├── profile.py                    raw-column profile
    ├── audit_evidence.py             independent audit + Tableau/Python comparison → evidence/
    ├── scripts/
    │   ├── build_data_contract.py    regenerates data_contract.yaml
    │   └── validate_data_contract.py validates the contract + runs its 49 quality checks
    ├── tests/                        10 automated tests
    ├── requirements.txt              pandas
    ├── requirements-contract.txt     pandas, pyyaml, jsonschema (contract tools only)
    ├── metadata.json                 Schema.org Dataset metadata
    ├── data_contract.yaml            data contract (Bitol ODCS v3.2.0)
    ├── README.md                     detailed data README (fields, units, outputs)
    ├── data/
    │   ├── raw/                      3 original CSV snapshots — never modified
    │   ├── output/                   quality_metrics.json (hashes); the 5 output CSVs are recreated by pipeline.py
    │   ├── tableau_output/           4 Tableau Prep outputs (for comparison)
    │   └── quarantine/               rows rejected for unparseable dates (0 in this snapshot)
    ├── documentation/
    │   ├── 01_PROJECT_SCOPE_AND_ARCHITECTURE.md
    │   ├── 02_FAIR_ASSESSMENT.md
    │   ├── 03_QUALITY_AND_PROFILE.md
    │   ├── 04_CLEANING_AND_TABLEAU.md
    │   ├── 05_PYTHON_REPRODUCIBILITY.md
    │   ├── 06_GOVERNANCE_AND_AI.md
    │   ├── 07_CLEANING_LOG.csv
    │   ├── data_dictionary.csv       196 raw + output fields, each with its definition source
    │   └── governance/               roles, risk register, lineage, AI-readiness checklist, ODCS schema
    ├── evidence/                     quality KPIs, scorecard, reconciliations, repeat-run proof
    │   └── profiling/                extended profile: all 117 raw columns, domains, relationships, dates
    │   └── profiling/                extended profile: all 117 raw columns, domains, relationships, dates
    └── logs/run_log.jsonl            pipeline run history
```

## 2. Team and roles

| Member | Role | Responsibilities |
| --- | --- | --- |
| Nagothi Ram Dileep | Derived data owner | Approves scope, release conditions, limitations and version |
| Jonnala Bhavya Sri | Data steward | Data dictionary, quality definitions, scope decisions, issue log |
| Pulakanti Aashrith Reddy | Pipeline custodian | Raw snapshots, Python and Tableau code, tests, hashes, reruns |
| Nukala Megha Sri Sai Vardhan | Quality reviewer | Independent Tableau/Python comparison, limitations, documentation checks |

The City of Seattle / SDOT remains the owner of the source data; the group owns only the derived product.

## 3. Source data

All three files were downloaded on **2 November 2026** and are kept unchanged in `project/data/raw/`. Their SHA-256 hashes are in `project/data/output/quality_metrics.json`.

| Dataset | File | Rows | Key | Licence shown by the portal (checked 7 Nov 2026) |
| --- | --- | ---: | --- | --- |
| [SDOT Collisions All Years](https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::sdot-collisions-all-years) | `CRASHES_2019_2025.csv` | 53,936 | `INCKEY` | None displayed |
| [Seattle Streets](https://data.seattle.gov/dataset/Seattle-Streets/w3hh-bqt5) | `Seattle_Streets_1_7907262242317696645.csv` | 23,888 | `COMPKEY` | None; no-warranty disclaimer only |
| [Traffic Counts by Study](https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc) | `Traffic_Counts_by_Study_20261101.csv` | 64,532 | `STUDY_ID` | Public Domain |

Field definitions come from SDOT's documentation ([Collisions](https://www.seattle.gov/Documents/Departments/SDOT/GIS/Collisions_OD.pdf), [Streets](https://www.seattle.gov/Documents/Departments/SDOT/GIS/Seattle_Streets_OD.pdf)): `SEGLENGTH` is in feet and `SPEEDLIMIT` in miles per hour. The live portals are refreshed regularly, so their current row counts differ from these snapshots.

## 4. Architecture

```text
Seattle open-data portals
   → raw zone: data/raw (unchanged CSVs + SHA-256)
   → profiling and quality checks (audit_evidence.py)
   → two independent ETL implementations
        ├── Tableau Prep flow  → data/tableau_output
        └── Python pipeline    → data/output (authoritative)
   → reconciliation (evidence/08, 09)
   → curated count tables → analysts
```

This is a local, file-based batch ETL organised like raw / curated / audit zones. It is **not** a cloud data lake, warehouse or deployed AI system.

**Join logic (and why it matters):**
- Segment crashes (`ADDRTYPE = B`): `ADDR_SEGINTKEY` → Streets `COMPKEY`; traffic studies are filtered and aggregated per road and year **before** joining on `COMPKEY + year`.
- Intersection crashes (`ADDRTYPE = I`): `INTKEY` → a union of the Streets low and high endpoints (`INTKEYLO`, `INTKEYHI`), aggregated per intersection **before** joining.
- Joining raw studies or raw endpoints directly would multiply crash rows. The pipeline stops if any join changes a row count or loses a crash.

## 5. Results

**Analysis scope** — all 53,936 collisions are kept in `validated_crashes.csv` with a status:

| Status | Collisions |
| --- | ---: |
| Included – road segment | 23,774 |
| Included – intersection | 17,751 |
| Outside – location not matched by the source | 12,215 |
| Outside – alley | 196 |
| **Total** | **53,936** (41,525 included = 76.99%) |

**Recorded collisions per year:** 2019: 11,236 · 2020: 7,254 · 2021: 8,170 · 2022: 7,681 · 2023: 7,369 · 2024: 6,464 · 2025: 5,762

**Top recorded-count road segments (2019–2025)**

| Segment key | Street | Collisions | Injuries | Serious injuries |
| ---: | --- | ---: | ---: | ---: |
| 1270 | 1ST AV S BR NB | 106 | 46 | 0 |
| 8995 | AURORA AVE N | 66 | 38 | 2 |
| 12364 | RAINIER AVE S | 61 | 37 | 3 |
| 8991 | AURORA AVE N | 59 | 44 | 8 |
| 1267 | 1ST AV S BR NB | 56 | 26 | 3 |

**Top recorded-count intersections (2019–2025)**

| Intersection key | Location | Collisions | Injuries | Serious injuries |
| ---: | --- | ---: | ---: | ---: |
| 30509 | 4TH AVE S AND S JACKSON ST | 79 | 50 | 3 |
| 29973 | 6TH AVE AND JAMES ST | 57 | 27 | 0 |
| 35910 | MERIDIAN AVE N AND N 145TH ST | 54 | 32 | 3 |
| 33022 | EAST MARGINAL WAY S AND S DAWSON ST | 46 | 46 | 0 |
| 36360 | AURORA AVE N AND N NORTHGATE WAY | 44 | 15 | 0 |

These are **recorded counts**, not risk rates: busier roads naturally record more collisions. Segment and intersection counts are different populations and must not be added together.

## 6. Data quality findings

| Dimension | Finding | Handling |
| --- | --- | --- |
| Completeness | `WEATHER` missing for 12,350 crashes (22.90%), plus 246 "Unknown" | Kept and flagged (`Weather_Status`); no imputation |
| Uniqueness | 0 duplicate or missing keys in all three sources | STOP rule if this ever fails |
| Validity | 0 bad dates, 0 bad injury cells; traffic `ADT` stored as text with thousands separators | Commas removed before parsing |
| Consistency | 140 zero and 20 missing speed limits; `SEVERITYCODE` contradicts casualty counts in 331 crashes, 13 blank | Flagged for review; source values unchanged |
| Timeliness / coverage | Only 790 of 16,569 segment-years (4.77%) have a same-year traffic study | No traffic-adjusted risk claims |
| Accuracy | No independent ground truth available | Internally consistent only; not externally certified |

Details: `project/documentation/03_QUALITY_AND_PROFILE.md` and `project/evidence/`.

## 7. FAIR assessment

| Object | F | A | I | R | Score |
| --- | :-: | :-: | :-: | :-: | :-: |
| Original sources combined | 2 | 2 | 1 | 1 | **6/8** |
| (per source: Collisions 6/8, Streets 6/8, Traffic 7/8) | | | | | |
| Our project package, before → after | 0→1 | 1→1 | 1→2 | 1→1 | **3/8 → 5/8** |

These are reasoned rubric scores, not an official certification. Details: `project/documentation/02_FAIR_ASSESSMENT.md`.

## 8. Tableau Prep and Python parity

Both implementations were run on the same snapshot on 7 November 2026 and compared field by field:

| Comparison | Result |
| --- | --- |
| Crash counts (16,569 segment-years, 10,968 intersection-years ×2) | Identical |
| Intersection speed-status flags | Identical (fixed from 114 differences: zero-speed rule added in Tableau) |
| Segment lengths (`SEGLENGTH`) | Identical (fixed from 8 differences: decimal type set at the Tableau input) |
| Column layout | Differs (Tableau keeps extra pass-through columns) |

Details: `project/documentation/04_CLEANING_AND_TABLEAU.md`, `project/evidence/08_…csv`, `09_…csv`.

## 9. How to reproduce

Requirements: Python 3.10+ (tested with 3.11.0 and pandas 2.3.3 on Windows 11). Run in PowerShell from the `project` folder:

```powershell
cd project
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v      # expect: 10 tests OK
python pipeline.py                           # rebuilds data/output
python audit_evidence.py                     # rebuilds evidence/
python pipeline.py                           # second run: identical output hashes
```

The outputs are **byte-identical** across runs and operating systems (Windows and Linux); compare `output_sha256` in `data/output/quality_metrics.json`. Raw files are never modified. To open the Tableau flow, open `tableau/Seattle_Road_Safety_Final.tflx` in Tableau Prep Builder; it contains its own copy of the three source files.

## 10. Data contract (ODCS v3.2.0)

`project/data_contract.yaml` follows the [Bitol Open Data Contract Standard v3.2.0](https://bitol-io.github.io/open-data-contract-standard/). Status: **active** (approved by the group on 7 November 2026).

- 5 tables, 79 columns with types, units, keys and descriptions
- 49 executable quality checks: row counts, unique grain, required fields, crash conservation (23,774 / 17,751 / 53,936), and monitoring of missing weather, traffic coverage and severity mismatches
- team, access roles, sources and licences, download date, input hashes, STOP and quarantine rules

Validate it yourself:

```powershell
python -m pip install -r requirements-contract.txt
python scripts/validate_data_contract.py     # expect: Schema PASS, 49/49 checks passed
```

## 11. Governance and AI readiness

- **Lineage, roles, risk register and AI-readiness checklist:** `project/documentation/governance/` and `06_GOVERNANCE_AND_AI.md`.
- **STOP rules** (pipeline halts before writing): missing columns, duplicate or invalid keys, negative or non-numeric injury counts, duplicate grain, crash non-conservation, join row-count change.
- **AI readiness:** ready for descriptive aggregates and reproducible quality demonstrations. **Not** ready for per-vehicle risk ranking, causal claims about speed or weather, individual-level prediction or automated resource allocation. No predictive model was trained.

## 12. Limitations

- Counts are not exposure-adjusted: 95.23% of segment-years have no same-year traffic study, and study ADT is not full-year traffic.
- Street attributes come from a current snapshot applied to past crash years.
- `STATUS = Matched` is SDOT's own location matching, not proof of a match to the Streets snapshot.
- 41 segment-year and 25 intersection-year groups have no matching street record (kept with empty street attributes).
- Source accuracy cannot be independently verified with these files.

## 13. Licence and attribution

Source data © City of Seattle / Seattle Department of Transportation. Only *Traffic Counts by Study* carries an explicit licence (Public Domain); *Collisions* and *Streets* show none. **We therefore assign no licence to the combined derived data** and credit the City of Seattle/SDOT as the source. Our own code and documentation were written for an SRH University course examination.
