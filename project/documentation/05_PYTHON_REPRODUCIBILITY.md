# 5. The Python pipeline and how to reproduce it

This document explains every Python file in the project, what each one reads and writes, and how we checked that the results can be reproduced. If you only want to run the code, the commands are in section 6.

All paths below are relative to the `project` folder.

## 1. How the files fit together

The work is split into small files with one job each:

| File | Job |
| --- | --- |
| `pipeline.py` | Reads the three raw CSV files, cleans them, combines them and writes the results |
| `rules.py` | The quality rules. `pipeline.py` calls them, and they stop the run if the data is unsafe |
| `profile.py` | Describes every column of the raw files (type, missing values, most common value) |
| `audit_evidence.py` | Checks the finished outputs independently and writes the evidence files |
| `tests/` | Ten automated tests for the quality rules and the cleaning steps |
| `scripts/build_data_contract.py` | Creates the data contract from the outputs and the data dictionary |
| `scripts/validate_data_contract.py` | Checks the data contract and runs its 49 quality checks |
| `scripts/generate_detailed_profile.py` | Recreates the 10 detailed profiling files in `evidence/profiling/` |

The order is always the same: run `pipeline.py` first, because the other files work with its outputs.

## 2. `pipeline.py`

This is the main program. It runs in seven steps: load, clean, validate, classify, aggregate, enrich and write. The raw files are only ever read, never changed, and nothing is written until every quality rule has passed.

**Loading (`load_raw`).** Reads the three files in `data/raw/`. Every column is read as text at first, so nothing is silently converted. It then checks that the columns the pipeline needs are present. If a file or a column is missing, the run stops.

**Turning text into numbers (`numeric`).** Some numbers in the source files contain thousands separators, for example the traffic volume `9,759.57`. This helper removes the commas and converts the value to a number. Anything that still cannot be read as a number becomes empty instead of being guessed.

**Cleaning the collisions (`clean_crashes`).**
- Checks that every collision ID (`INCKEY`) is present and unique.
- Reads the date from `INCDATE` into `Crash_Date` and takes the year as `Crash_Year`.
- Creates the two location keys: `Crash_Road_Key` from `ADDR_SEGINTKEY` (road segments) and `Intersection_Key` from `INTKEY` (intersections).
- Converts the injury, serious-injury and fatality counts to numbers and stops if any of them is negative or unreadable.
- Adds `Weather_Status`: `Recorded`, `Missing` (no value) or `Reported Unknown` (the value is literally "Unknown"). The weather itself is not changed or filled in.

**Cleaning the streets (`clean_streets`).** Checks that every street key (`COMPKEY`) is present and unique and stores it as `Street_Road_Key`. Converts the two end-point intersection keys (`INTKEYLO`, `INTKEYHI`) and the speed limit to numbers.

**Cleaning the traffic studies (`clean_traffic`).** Checks that every study ID is unique, converts the road key and the traffic volume (`ADT`) to numbers, reads the study start date and its year, and notes whether a study ran for fewer days than planned.

**Deciding which collisions are analysed (`classify_crashes`).** Every collision gets a `Road_Analysis_Status`:
- `Included - Road Segment`: SDOT matched the location, it is a block (`ADDRTYPE = B`) and it has a valid segment key.
- `Included - Intersection`: SDOT matched the location, it is an intersection (`ADDRTYPE = I`) and it has a valid intersection key.
- `Outside - Unmatched Location`: SDOT could not match the location.
- `Outside - Alley`: the collision happened in an alley.
- `Quarantined - Invalid Date`: the date cannot be read, so the collision cannot be given a year. This status wins over all the others.

Collisions outside the analysis are kept in the output with their reason. They are not errors and are not deleted. Only a collision whose date cannot be read is set aside: it gets the status `Quarantined - Invalid Date`, is copied to the quarantine file and is left out of the yearly counts. In our snapshot there are no such rows.

**Counting collisions (`aggregate_crashes`).** Groups the included collisions by location and year and counts them (`Crash_Count`), together with the total injuries, serious injuries and fatalities. This is done once for road segments and once for intersections.

**Summarising the traffic studies (`aggregate_traffic`).** Keeps only the studies that are useful for us: started between 2019 and 2025, count both directions together (`TRAFFIC_FLOW_DIR_ID = 11`), have a traffic volume above zero and have a road key. That leaves 4,730 studies. Because one road can have several studies in the same year, they are averaged per road and year (`Mean_Study_ADT`, `Traffic_Study_Count`) before anything is joined.

**Describing each intersection (`build_intersection_roads`).** Every street segment has two ends, and each end is an intersection. The function lists both ends of every segment, then summarises them per intersection: how many segments and street names meet there, the lowest and highest speed limit, how many ends have a speed limit of 0 or none at all, and a `Speed_Limit_Status`. If any end has a speed limit of 0, the status is `Contains Zero Speed Limit — Review`, because 0 is a placeholder, not a real speed.

**Adding street and traffic details (`enrich_segment`, `enrich_intersection`).** The segment counts are joined to the street details (name, speed limit, road class, length) and to the averaged traffic for the same road and year. The intersection counts are joined to the intersection summary. These are left joins, so a location without street or traffic information is kept with empty fields and a status saying so. After every join the program checks that the number of rows has not changed. If it has, a collision would be double-counted or lost, so the run stops.

**Writing the results (`run`).** Before writing anything, `run` checks again that every location-year appears only once and that the counts add up to the number of included collisions. It then writes:

| File in `data/output/` | One row per | What it contains |
| --- | --- | --- |
| `validated_crashes.csv` | collision (53,936) | All source columns plus the cleaned date, keys, weather status and analysis status |
| `road_safety_by_segment_year.csv` | road segment and year | Collision and injury counts, street details, traffic average and coverage status |
| `intersection_crashes_by_year.csv` | intersection and year | Collision and injury counts |
| `intersection_hotspots_with_streets.csv` | intersection and year | The counts plus the intersection summary and speed-limit status |
| `crash_scope_summary.csv` | analysis status | How many collisions are in each status (adds up to 53,936) |
| `quality_metrics.json` | — | Row counts, key checks and the SHA-256 fingerprint of every input and output file |

It also writes `data/quarantine/quarantine_crashes.csv` (collisions with unreadable dates) and adds one line to `logs/run_log.jsonl` with the time and result of the run.

The files are always written in the same order and format, with Unix line endings, so two runs on any computer produce exactly the same bytes.

**When something goes wrong (`main`).** If any rule fails, the run stops before writing outputs, prints the reason and records a `FAILED` line in the run log.

## 3. `rules.py`

These are the quality rules. Each one raises a `QualityGateError`, which stops the whole run.

| Rule | What it checks |
| --- | --- |
| `check_required_columns` | Each raw file still has the columns the pipeline needs (listed in `REQUIRED`) |
| `check_unique_required_key` | An ID column has no empty, unreadable or repeated values |
| `check_nonnegative_measures` | Injury and fatality counts are numbers and not negative |
| `verify_group_identity` | Each location-year appears only once, and the collision counts add up to the expected total |

We use plain pandas for these checks so the project needs no extra validation library.

## 4. `profile.py`

Writes `data/output/raw_column_profile.csv`, with one row for each of the 117 raw columns: the dataset, the column name, its type, the number and share of missing values, the number of different values and the most common value. Text columns are always labelled `str`, so the result is the same with pandas 2 and pandas 3.

## 5. `audit_evidence.py`

This script checks the outputs independently of the pipeline and writes the evidence files in `evidence/`. It reads the raw files and the finished outputs again instead of trusting the pipeline's own numbers.

| Evidence file | What it shows |
| --- | --- |
| `01_raw_column_profile_extended.csv` | Missing and distinct values for all 117 raw columns |
| `02_source_inventory.csv` | Rows, columns, key checks and SHA-256 fingerprint of each raw file |
| `03_quality_kpis.json` | The headline numbers: missing weather, zero speed limits, scope, traffic coverage, and whether counts were kept intact |
| `04_quality_dimension_scorecard.csv` | Results for the six quality dimensions (completeness, uniqueness, validity, consistency, timeliness, accuracy) |
| `05_crashes_by_year.csv` | Collisions per year |
| `06_scope_reconciliation.csv` | Collisions per analysis status |
| `07_inclusion_dependency.json` | How many collision road keys exist in the Streets file (99.65%) |
| `08_tableau_python_count_reconciliation.csv` | Tableau and Python compared location by location; all three files pass |
| `09_tableau_speed_status_differences.csv` | Intersections where Tableau and Python disagree on the speed-limit status (now none) |
| `10_output_data_dictionary.csv` | Short description of each output column |
| `13_severity_consistency.csv` | Collisions whose severity code contradicts their injury counts (331) or is blank (13) |

Three more files come from the repeat-run check described in section 7: `11_before_repeat_quality_metrics.json` (the metrics of the first run), `12_repeat_run_verification.json` (the comparison of both runs) and `12_second_run_console.txt` (the screen output of the second run).

The `evidence/profiling/` folder holds the more detailed profile from the quality phase: all column profiles, the source inventory, quality numbers, relationship checks, before/after notes, the ranked cleaning plan, value distributions and date ranges. They are recreated by `scripts/generate_detailed_profile.py`, which reads the raw files and `data/output/road_safety_by_segment_year.csv`, so run it after `pipeline.py`.

Two things to know about this script. Files 07 and 08 contain a few sentences whose numbers were written into the script for this snapshot (for example "53,936 raw events"); all other values are calculated. When two values are equally common, the "most common value" columns show the one that appears first in the file. Because of this fixed rule, one value in `01_full_column_profile.csv` (for `Shape__Length`, where two values each appear twice) differs from the very first version we made during the quality phase; both values are equally correct.

## 6. How to run it

You need Python 3.10 or newer. In PowerShell, from the `project` folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python pipeline.py
python profile.py
python audit_evidence.py
python scripts/generate_detailed_profile.py
python pipeline.py
```

What you should see:
- The tests report `Ran 10 tests` and `OK`.
- `pipeline.py` reports 53,936 validated collisions, 16,569 segment-year rows and 10,968 intersection-year rows, and ends with `SUCCESS`.
- After the second run, the `output_sha256` values in `data/output/quality_metrics.json` are unchanged.

The raw files in `data/raw/` are never changed. Each run adds one line to `logs/run_log.jsonl`.

To check the data contract as well:

```powershell
python -m pip install -r requirements-contract.txt
python scripts/validate_data_contract.py
```

It should print `Schema validation: PASS` and `49/49 passed`. Use `python scripts/build_data_contract.py` only if the data changes and the contract has to be recreated.

## 7. The tests

| Test | What it proves |
| --- | --- |
| `test_duplicate_street_key_causes_stop` | A repeated street key stops the run |
| `test_missing_key_stops` | An empty collision ID stops the run |
| `test_negative_injury_stops` | A negative injury count stops the run |
| `test_non_numeric_injury_stops` | An injury count like "unknown" stops the run |
| `test_valid_zero_injury_passes` | Zero injuries is accepted as a valid value |
| `test_wrong_crash_total_causes_stop` | Counts that do not add up stop the run |
| `test_conserved_crash_total_passes` | Counts that add up are accepted |
| `test_duplicated_output_groups_stop` | The same location-year appearing twice stops the run |
| `test_invalid_date_quarantined_but_unmatched_is_scope_excluded` | A collision with an unreadable date goes to quarantine and gets the status `Quarantined - Invalid Date`, while an unmatched one stays in the data with its own status |
| `test_street_join_preserves_group_row_count` | Adding street and traffic details does not change the number of rows |

The tests use small, made-up tables, so they run in under a second and do not need the real data.

## 8. Can the results be reproduced?

Yes. We checked this in three ways:

1. **Two runs give the same files.** We ran the pipeline twice on the same raw files. All five outputs had identical SHA-256 fingerprints (`evidence/12_repeat_run_verification.json`). Only the timestamps in the run log differ.
2. **Different computers give the same files.** On 7 November 2026 we ran the pipeline on Windows 11 (Python 3.11.0, pandas 2.3.3). At first the fingerprints differed from the recorded ones, although the content was the same, because Windows writes different line endings. We changed `pipeline.py`, `profile.py` and `audit_evidence.py` to always use Unix line endings. Since then, the Windows outputs are byte-for-byte identical to the recorded files.
3. **Different pandas versions give the same profile.** pandas 2 and pandas 3 name text columns differently (`object` and `str`). `profile.py` now writes `str` for both.

## 9. What the code stops, sets aside or keeps

- **Stops the run:** a missing column, a missing or repeated ID, an unreadable or negative injury count, a location-year listed twice, a join that changes the number of rows, or counts that do not add up. In any of these cases no new outputs are written.
- **Sets aside (quarantine):** collisions whose date cannot be read. They get the status `Quarantined - Invalid Date` and go to the quarantine file. There are none in this snapshot; a test shows that it works.
- **Keeps with a label:** unmatched locations and alleys. They are real collisions, so they stay in `validated_crashes.csv` with their reason.

## 10. Limits

- The tests prove that our rules work. They cannot prove that every source record is correct.
- Tableau and Python give the same counts, flags and lengths, but their output files have different columns (see `04_CLEANING_AND_TABLEAU.md`).
- `requirements.txt` allows pandas 2.0 up to 3.x instead of fixing one version. Section 8 records the versions we tested.
