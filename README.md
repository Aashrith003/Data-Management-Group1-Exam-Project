# Seattle Road Safety: from raw open data to a dataset you can trust

SRH University · Data Management · Group 1

This is our data management exam project. We took three public datasets from the City of Seattle (collisions, streets and traffic counts) and turned them into clean tables that show **how many collisions were recorded on each road segment and at each intersection from 2019 to 2025**.

We did the cleaning twice: once in **Tableau Prep** and once in **Python**. Both give the same results. When we found a problem in the data, we did not hide it or guess a value. We kept it visible and marked it.

> **Our question:** Which Seattle road segments and intersections had the most recorded collisions in 2019–2025, and what problems in the data do people need to know about before they use these numbers?
>
> **Short answer:** We can rank places by the number of *recorded* collisions. We cannot rank them by risk per vehicle, because only 4.77% of road segment years have a traffic count from the same year.

## Our team

| Name | Role | What they looked after |
| --- | --- | --- |
| **Nagothi Ram Dileep** | Data owner | Decided the scope, the limits and when a version is ready |
| **Jonnala Bhavya Sri** | Data steward | The data dictionary, quality rules and the list of known issues |
| **Pulakanti Aashrith Reddy** | Pipeline custodian | The raw files, the Python and Tableau work, the tests and the checksums |
| **Nukala Megha Sri Sai Vardhan** | Quality reviewer | Comparing Tableau with Python, the limitations and checking the documentation |

The City of Seattle and its transport department (SDOT) own the original data. We only own what we built from it. More about the roles: [06 Governance – Roles](project/documentation/06_GOVERNANCE_AND_AI.md#roles-srh-university-data-management-group-1).

## Contents

1. [What is in this repository](#1-what-is-in-this-repository)
2. [The data we used](#2-the-data-we-used)
3. [How the project is built](#3-how-the-project-is-built)
4. [Results](#4-results)
5. [Problems we found in the data](#5-problems-we-found-in-the-data)
6. [FAIR assessment](#6-fair-assessment)
7. [Tableau and Python give the same results](#7-tableau-and-python-give-the-same-results)
8. [How to run it yourself](#8-how-to-run-it-yourself)
9. [Data contract](#9-data-contract)
10. [Governance and AI readiness](#10-governance-and-ai-readiness)
11. [Limitations](#11-limitations)
12. [Licence](#12-licence)

## 1. What is in this repository

Click a name to open it, or click the link on the right to read what it does.

| Folder or file | What it is | Explained in |
| --- | --- | --- |
| [`tableau/`](tableau/) | The Tableau Prep flow. The `.tflx` file also contains the three source files. | [04 Cleaning and Tableau](project/documentation/04_CLEANING_AND_TABLEAU.md) |
| [`project/pipeline.py`](project/pipeline.py) | The main Python program: reads, cleans, counts and writes the results | [05 Python – pipeline.py](project/documentation/05_PYTHON_REPRODUCIBILITY.md#2-pipelinepy) |
| [`project/rules.py`](project/rules.py) | The quality rules that stop the run if the data is unsafe | [05 Python – rules.py](project/documentation/05_PYTHON_REPRODUCIBILITY.md#3-rulespy) |
| [`project/profile.py`](project/profile.py) | Describes every column of the raw files | [05 Python – profile.py](project/documentation/05_PYTHON_REPRODUCIBILITY.md#4-profilepy) |
| [`project/audit_evidence.py`](project/audit_evidence.py) | Checks the results again and writes the evidence files | [05 Python – audit_evidence.py](project/documentation/05_PYTHON_REPRODUCIBILITY.md#5-audit_evidencepy) |
| [`project/tests/`](project/tests/) | 10 automated tests | [05 Python – the tests](project/documentation/05_PYTHON_REPRODUCIBILITY.md#7-the-tests) |
| [`project/scripts/`](project/scripts/) | Tools that create and check the data contract | [06 Governance – data contract](project/documentation/06_GOVERNANCE_AND_AI.md#data-contract) |
| [`project/data/raw/`](project/data/raw/) | The three original files, never changed | [project README – raw data](project/README.md#the-raw-data-dataraw) |
| [`project/data/output/`](project/data/output/) | `quality_metrics.json` with all checksums. The output CSVs are made by running `pipeline.py`. | [project README – outputs](project/README.md#the-outputs-dataoutput) |
| [`project/data/tableau_output/`](project/data/tableau_output/) | The four files Tableau produced, used for the comparison | [04 Cleaning and Tableau](project/documentation/04_CLEANING_AND_TABLEAU.md#verified-comparison-tableau-run-of-7-november-2026) |
| [`project/evidence/`](project/evidence/) | Quality checks, the Tableau-vs-Python comparison and proof that runs repeat exactly | [05 Python – evidence files](project/documentation/05_PYTHON_REPRODUCIBILITY.md#5-audit_evidencepy) |
| [`project/documentation/`](project/documentation/) | One detailed write-up for each part of the project | see the links in each section below |
| [`project/documentation/data_dictionary.csv`](project/documentation/data_dictionary.csv) | Meaning, unit and source of all 196 fields | [project README – important fields](project/README.md#important-fields) |
| [`project/metadata.json`](project/metadata.json) | A description of the dataset in the Schema.org format | [02 FAIR](project/documentation/02_FAIR_ASSESSMENT.md) |
| [`project/data_contract.yaml`](project/data_contract.yaml) | Our data contract, with 49 checks | [06 Governance – data contract](project/documentation/06_GOVERNANCE_AND_AI.md#data-contract) |
| [`project/README.md`](project/README.md) | A longer guide to the data, the fields and the outputs | – |

## 2. The data we used

We downloaded all three files on **2 November 2026**. They are in [`project/data/raw/`](project/data/raw/) and we never changed them. Their checksums are in [`quality_metrics.json`](project/data/output/quality_metrics.json), so anyone can check that they have exactly the same files.

| Dataset | File | Rows | ID column | Licence |
| --- | --- | ---: | --- | --- |
| [SDOT Collisions All Years](https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::sdot-collisions-all-years) | `CRASHES_2019_2025.csv` | 53,936 | `INCKEY` | none shown |
| [Seattle Streets](https://data.seattle.gov/dataset/Seattle-Streets/w3hh-bqt5) | `Seattle_Streets_1_7907262242317696645.csv` | 23,888 | `COMPKEY` | none shown, only a disclaimer |
| [Traffic Counts by Study](https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc) | `Traffic_Counts_by_Study_20261101.csv` | 64,532 | `STUDY_ID` | Public Domain |

A **road segment** is one piece of street between two intersections. Each collision is linked either to a road segment or to an intersection. What every column means, and its unit (for example, segment length is in feet and the speed limit in miles per hour), is explained in [project README – important fields](project/README.md#important-fields) and in the full [data dictionary](project/documentation/data_dictionary.csv).

The City updates these datasets regularly, so a download made today will have different row counts.

More detail: [01 Scope – original snapshots](project/documentation/01_PROJECT_SCOPE_AND_ARCHITECTURE.md#original-snapshots-never-edited).

## 3. How the project is built

```text
City of Seattle open data
   → data/raw            the three files, unchanged, with checksums
   → quality checks      audit_evidence.py
   → cleaning, done twice
        ├── Tableau Prep → data/tableau_output
        └── Python       → data/output   (the main result)
   → comparison          evidence/08 and 09
   → count tables for analysts
```

Everything runs on local files. There is no cloud database, data warehouse or AI model.

How the three datasets are joined:
- A collision on a road segment (`ADDRTYPE = B`) is linked to the street through `ADDR_SEGINTKEY` = `COMPKEY`. Traffic counts are first averaged per road and year, and only then added.
- A collision at an intersection (`ADDRTYPE = I`) is linked through `INTKEY`. Every street segment has two ends, so we first make one summary row per intersection, and only then add it.
- If we joined before summarising, some collisions would be counted twice. The program checks this after every join and stops if the number of rows changes.

More detail: [01 Scope – architecture](project/documentation/01_PROJECT_SCOPE_AND_ARCHITECTURE.md#architecture--data-flow-blueprint) and [05 Python – pipeline.py](project/documentation/05_PYTHON_REPRODUCIBILITY.md#2-pipelinepy).

## 4. Results

All 53,936 collisions are kept in `validated_crashes.csv`, each with a status:

| Status | Collisions |
| --- | ---: |
| On a road segment | 23,774 |
| At an intersection | 17,751 |
| Location not matched by SDOT | 12,215 |
| In an alley | 196 |
| **Total** | **53,936** (41,525 used in the counts, 76.99%) |

Collisions recorded per year: 2019: 11,236 · 2020: 7,254 · 2021: 8,170 · 2022: 7,681 · 2023: 7,369 · 2024: 6,464 · 2025: 5,762

**Road segments with the most recorded collisions (2019–2025)**

| Segment ID | Street | Collisions | Injuries | Serious injuries |
| ---: | --- | ---: | ---: | ---: |
| 1270 | 1ST AV S BR NB | 106 | 46 | 0 |
| 8995 | AURORA AVE N | 66 | 38 | 2 |
| 12364 | RAINIER AVE S | 61 | 37 | 3 |
| 8991 | AURORA AVE N | 59 | 44 | 8 |
| 1267 | 1ST AV S BR NB | 56 | 26 | 3 |

**Intersections with the most recorded collisions (2019–2025)**

| Intersection ID | Location | Collisions | Injuries | Serious injuries |
| ---: | --- | ---: | ---: | ---: |
| 30509 | 4TH AVE S AND S JACKSON ST | 79 | 50 | 3 |
| 29973 | 6TH AVE AND JAMES ST | 57 | 27 | 0 |
| 35910 | MERIDIAN AVE N AND N 145TH ST | 54 | 32 | 3 |
| 33022 | EAST MARGINAL WAY S AND S DAWSON ST | 46 | 46 | 0 |
| 36360 | AURORA AVE N AND N NORTHGATE WAY | 44 | 15 | 0 |

These are counts of recorded collisions, not risk. A busy road will record more collisions simply because more cars use it. Segment counts and intersection counts are separate groups and should not be added together.

More detail: [01 Scope – scope](project/documentation/01_PROJECT_SCOPE_AND_ARCHITECTURE.md#scope-reconciliation) and [project README – outputs](project/README.md#the-outputs-dataoutput).

## 5. Problems we found in the data

| Area | What we found | What we did |
| --- | --- | --- |
| Missing values | Weather is missing for 12,350 collisions (22.90%), and 246 more say "Unknown" | Kept them and marked them; we did not guess the weather |
| Duplicates | No missing or repeated IDs in any of the three files | The program stops if this ever changes |
| Format | No unreadable dates or injury counts. Traffic volumes are stored as text with commas, like `9,759.57` | Removed the commas before reading the numbers |
| Contradictions | 140 roads have a speed limit of 0 and 20 have none. In 331 collisions the severity code does not match the injury counts, and 13 have no code | Marked them for review; the original values are unchanged |
| Coverage | Only 790 of 16,569 road segment years (4.77%) have a traffic count from the same year | We make no claims about risk per vehicle |
| Accuracy | There is no independent source to check the records against | The data agrees with itself, but we cannot prove it is correct |

More detail: [03 Data quality](project/documentation/03_QUALITY_AND_PROFILE.md), with all the numbers in [03 – detailed profiling](project/documentation/03_QUALITY_AND_PROFILE.md#detailed-profiling-recomputed-from-the-raw-csvs-7-november-2026), and the evidence files in [`project/evidence/`](project/evidence/).

## 6. FAIR assessment

FAIR means Findable, Accessible, Interoperable and Reusable. Each letter gets 0, 1 or 2 points.

| What we scored | F | A | I | R | Total |
| --- | :-: | :-: | :-: | :-: | :-: |
| The three original datasets together | 2 | 2 | 1 | 1 | **6/8** |
| (each on its own: Collisions 6/8, Streets 6/8, Traffic 7/8) | | | | | |
| Our project files, before and after our work | 0→1 | 1→1 | 1→2 | 1→1 | **3/8 → 5/8** |

These are our own scores using the course rubric, not an official rating. More detail: [02 FAIR assessment](project/documentation/02_FAIR_ASSESSMENT.md).

## 7. Tableau and Python give the same results

On 7 November 2026 we ran both versions on the same files and compared them value by value:

| What we compared | Result |
| --- | --- |
| Collision counts (16,569 segment years and 10,968 intersection years) | The same |
| Speed limit status at intersections | The same, after we added the zero-speed rule in Tableau (there were 114 differences before) |
| Segment length (`SEGLENGTH`) | The same, after we set the length to a decimal number in Tableau (there were 8 differences before) |
| Columns in the files | Different: Tableau keeps some extra columns |

More detail: [04 – comparison](project/documentation/04_CLEANING_AND_TABLEAU.md#verified-comparison-tableau-run-of-7-november-2026), [04 – fixes we made in Tableau](project/documentation/04_CLEANING_AND_TABLEAU.md#fixes-applied) and the evidence files [`08`](project/evidence/08_tableau_python_count_reconciliation.csv) and [`09`](project/evidence/09_tableau_speed_status_differences.csv).

## 8. How to run it yourself

You need Python 3.10 or newer. We tested with Python 3.11.0 and pandas 2.3.3 on Windows 11. In PowerShell:

```powershell
cd project
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v      # all 10 tests should pass
python pipeline.py                           # creates data/output
python audit_evidence.py                     # creates the evidence files
python pipeline.py                           # run again: the checksums do not change
```

Run `pipeline.py` first, because it creates the output files the other steps need. Every run gives exactly the same files, on Windows and on Linux. You can check this with the `output_sha256` values in [`quality_metrics.json`](project/data/output/quality_metrics.json). The raw files are never changed.

To open the Tableau flow, open [`tableau/Seattle_Road_Safety_Final.tflx`](tableau/Seattle_Road_Safety_Final.tflx) in Tableau Prep Builder. It already contains the three source files.

What each file does and what you should see when you run it: [05 Python – how to run it](project/documentation/05_PYTHON_REPRODUCIBILITY.md#6-how-to-run-it) and [05 Python – can the results be reproduced?](project/documentation/05_PYTHON_REPRODUCIBILITY.md#8-can-the-results-be-reproduced).

## 9. Data contract

[`project/data_contract.yaml`](project/data_contract.yaml) follows the [Bitol Open Data Contract Standard v3.2.0](https://bitol-io.github.io/open-data-contract-standard/). Our group approved it on 7 November 2026. It contains:

- all 5 output tables and their 79 columns, with types, units and descriptions
- 49 checks that a computer can run, for example that the collision totals stay at 23,774, 17,751 and 53,936
- the team, the sources and their licences, the download date and the file checksums

To check it yourself (after running `pipeline.py`):

```powershell
python -m pip install -r requirements-contract.txt
python scripts/validate_data_contract.py     # should say: Schema PASS, 49/49 passed
```

More detail: [06 Governance – data contract](project/documentation/06_GOVERNANCE_AND_AI.md#data-contract).

## 10. Governance and AI readiness

- **Records:** the roles, risk register, data lineage and AI checklist are in [`project/documentation/governance/`](project/documentation/governance/).
- **When the program stops:** a missing column, a missing or repeated ID, a negative or unreadable injury count, a location listed twice, a join that changes the number of rows, or totals that do not add up. In these cases it writes nothing.
- **AI readiness:** the data is good enough for counting and describing collisions. It is not good enough for ranking risk per vehicle, for saying what causes collisions, for predictions about individual people or for automatic decisions. We did not train any model.

More detail: [06 Governance – risk register](project/documentation/06_GOVERNANCE_AND_AI.md#risk-register) and [06 – AI readiness](project/documentation/06_GOVERNANCE_AND_AI.md#ai-readiness-assessment).

## 11. Limitations

- The counts do not take traffic into account: 95.23% of road segment years have no traffic count from the same year, and each traffic study we use covers at most 7 days.
- The street details describe the road network today, but we use them for earlier years too.
- When SDOT says a location is "Matched", that is SDOT's own check. It does not prove that the street exists in our streets file.
- 41 road segment years and 25 intersection years have no matching street. We kept them with empty street details.
- We cannot prove that the City's original records are correct.

More detail: [01 Scope – what must not be claimed](project/documentation/01_PROJECT_SCOPE_AND_ARCHITECTURE.md#what-must-not-be-claimed) and [project README – limitations](project/README.md#limitations).

## 12. Licence

The data belongs to the City of Seattle / SDOT. Only *Traffic Counts by Study* has a licence (Public Domain); *Collisions* and *Streets* show none. That is why we do not put a licence on the combined data. If you reuse it, please credit the City of Seattle / SDOT. We wrote our code and documentation for an SRH University exam.

More detail: [02 FAIR – source evidence](project/documentation/02_FAIR_ASSESSMENT.md).
