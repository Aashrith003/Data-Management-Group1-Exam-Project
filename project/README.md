# Seattle Road Safety: the data and the code

This folder contains everything needed to rebuild our results: the raw data, the Python code, the outputs, the evidence and the documentation. The main README one folder up gives the short overview.

## The question

Where in Seattle were the most collisions recorded between 2019 and 2025, on road segments and at intersections, and what problems in the data limit how far we can trust that answer?

We count recorded collisions. We do not estimate how dangerous a street is per vehicle, because traffic counts exist for only a small share of roads.

## The raw data (`data/raw/`)

| File | Rows | One row is | Key |
| --- | ---: | --- | --- |
| `CRASHES_2019_2025.csv` | 53,936 | one recorded collision | `INCKEY` |
| `Seattle_Streets_1_7907262242317696645.csv` | 23,888 | one street segment today | `COMPKEY` |
| `Traffic_Counts_by_Study_20261101.csv` | 64,532 | one traffic count study | `STUDY_ID` |

We downloaded all three on 2 November 2026 from the City of Seattle:
[SDOT Collisions All Years](https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::sdot-collisions-all-years),
[Seattle Streets](https://data.seattle.gov/dataset/Seattle-Streets/w3hh-bqt5) and
[Traffic Counts by Study](https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc).
The date in the traffic file name (`20261101`) is part of the name the portal gave the file, not our download date.

We never change these files. Their SHA-256 fingerprints are stored in `data/output/quality_metrics.json`, so anyone can check they have exactly the same files. The City updates its portals regularly, so a new download today will not match exactly.

Two things to keep in mind:
- The streets file describes the road network as it is now, not as it was in each crash year.
- The collision file is our 2019–2025 extract, not the full live table.

## Important fields

| Field | Meaning | Unit |
| --- | --- | --- |
| `INCKEY` | Collision ID | – |
| `INCDATE` | Date of the collision | date |
| `ADDRTYPE` | Where it happened: `B` block (road segment), `I` intersection, `A` alley | – |
| `ADDR_SEGINTKEY` | Road segment of the collision (links to `COMPKEY`) | – |
| `INTKEY` | Intersection of the collision | – |
| `INJURIES`, `SERIOUSINJURIES`, `FATALITIES` | People injured, seriously injured, killed | people |
| `WEATHER` | Weather at the time | often missing |
| `COMPKEY` | Road segment ID in the streets and traffic files | – |
| `SPEEDLIMIT` | Posted speed limit (0 is a placeholder) | miles per hour |
| `SEGLENGTH` | Length of the road segment | feet |
| `ADT` | Average daily traffic during a study | vehicles per day |
| `Crash_Count` | Collisions at one location in one year (our output) | collisions |

All 196 raw and output fields are described in `documentation/data_dictionary.csv`, together with where each definition comes from. Units are taken from SDOT's field documentation for [collisions](https://www.seattle.gov/Documents/Departments/SDOT/GIS/Collisions_OD.pdf) and [streets](https://www.seattle.gov/Documents/Departments/SDOT/GIS/Seattle_Streets_OD.pdf). Where the City does not explain a field, the dictionary says so.

One surprise: SDOT's document lists older severity codes. In our data the codes are 1 = property damage only, 2 = injury, 3 = serious injury, 4 = fatal.

## What we did

1. Checked that all IDs are present and unique, and read the dates.
2. Gave every collision a status: road segment, intersection, unmatched location or alley. A collision whose date cannot be read is marked as quarantined. Nothing was deleted.
3. Counted collisions per road segment and year, and per intersection and year.
4. Added street details and, where available, traffic counts from the same year. Traffic studies and street ends were summarised first, so no collision is counted twice.
5. Flagged problems such as missing weather or a speed limit of 0 instead of hiding or guessing them.

We did this twice: once in Tableau Prep (`../tableau/Seattle_Road_Safety_Final.tflx`) and once in Python (`pipeline.py`). Both give the same results. Every Python file is explained in `documentation/05_PYTHON_REPRODUCIBILITY.md`.

## The outputs (`data/output/`)

| File | Contents |
| --- | --- |
| `validated_crashes.csv` | All 53,936 collisions with the cleaned date, keys and status |
| `road_safety_by_segment_year.csv` | Collisions per road segment and year, with street and traffic details |
| `intersection_crashes_by_year.csv` | Collisions per intersection and year |
| `intersection_hotspots_with_streets.csv` | The same, with details of the streets that meet there |
| `crash_scope_summary.csv` | How many collisions are in each status |
| `quality_metrics.json` | Key numbers and fingerprints of all inputs and outputs |

The CSV outputs are included here, and `pipeline.py` recreates them exactly; you can compare your files with the checksums in `quality_metrics.json`. The Tableau versions of the first four files are in `data/tableau_output/`.

41,525 of the 53,936 collisions (77%) could be placed on a segment or intersection. The other 12,411 (12,215 unmatched locations and 196 alleys) stay in `validated_crashes.csv` with their status. No collision had an unreadable date, so the quarantine file in `data/quarantine/` is empty.

## Running it

From this folder, in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python pipeline.py
python profile.py
python audit_evidence.py
python pipeline.py
```

All 10 tests should pass, and the second `pipeline.py` run should leave the fingerprints in `quality_metrics.json` unchanged.

## Folder guide

| Folder or file | Contents |
| --- | --- |
| `data/raw/` | The three original files |
| `data/output/` | Python results and `quality_metrics.json` |
| `data/tableau_output/` | Tableau results, used for comparison |
| `data/quarantine/` | Collisions with unreadable dates (none) |
| `pipeline.py`, `rules.py`, `profile.py`, `audit_evidence.py` | The Python code |
| `tests/` | Automated tests |
| `scripts/` | Create and check the data contract |
| `evidence/` | Quality checks, comparisons and repeat-run proof |
| `documentation/` | Detailed write-ups for each part of the project |
| `logs/` | A line for every pipeline run |
| `metadata.json` | Description of the dataset in the Schema.org format |
| `data_contract.yaml` | Data contract in the Bitol ODCS v3.2.0 format |

## Limitations

- Weather is missing for 12,350 collisions (22.9%) and "Unknown" for 246 more.
- 140 road segments have a speed limit of 0 and 20 have none.
- Only 790 of 16,569 segment-years (4.8%) have a traffic count from the same year, so the data cannot show risk per vehicle.
- 41 segment-years and 25 intersection-years have no matching street record; they are kept with empty street details.
- Tableau's output files have more columns than Python's, but the shared values match.
- Street details are from today's network and are applied to earlier years.
- Repeating the calculation exactly does not prove that the City's original records are correct.

## Licence

Only the traffic data has a licence (Public Domain). The collision and street data show no licence, so we do not put a licence on the combined data. Please credit the City of Seattle / SDOT when you reuse it. More detail is in `documentation/02_FAIR_ASSESSMENT.md`.

Repository: https://github.com/Aashrith003/Data-Management-Group1-Exam-Project
