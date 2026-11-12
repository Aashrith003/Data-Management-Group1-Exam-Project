# Seattle Road Safety: Data Management Project, Group 1

SRH University, Data Management.
Pulakanti Aashrith Reddy, Nukala Megha Sri Sai Vardhan, Jonnala Bhavya Sri, Nagothi Ram Dileep.

We combined three public City of Seattle datasets (collisions, streets and traffic counts) to find where the most collisions were recorded between 2019 and 2025. We cleaned the data twice, in Tableau Prep and in Python, and both give the same results.

**Main finding:** we can rank roads and intersections by recorded collisions, but not by risk per vehicle, because only 4.8% of road-segment years have a traffic count from the same year.

## Contents

| Folder or file | In short | Details |
| --- | --- | --- |
| `tableau/` | The Tableau Prep flow. The `.tflx` file includes the source data. | [04 Cleaning and Tableau](project/documentation/04_CLEANING_AND_TABLEAU.md) |
| `project/` | The Python code, data, results and evidence. | [project README](project/README.md) |
| `project/*.py`, `project/tests/`, `project/scripts/` | The Python pipeline, its quality rules, tests and data-contract tools. | [05 Python pipeline](project/documentation/05_PYTHON_REPRODUCIBILITY.md) |
| `project/data/` | The three original files, the Python results and the Tableau results. | [project README](project/README.md) |
| `project/evidence/` | Quality checks, Tableau-vs-Python comparison and repeat-run proof. | [05 Python pipeline](project/documentation/05_PYTHON_REPRODUCIBILITY.md) |
| `project/documentation/` | One write-up per part of the project, plus the data dictionary. | see below |
| `project/metadata.json` | Description of the dataset (Schema.org). | [02 FAIR](project/documentation/02_FAIR_ASSESSMENT.md) |
| `project/data_contract.yaml` | Data contract (Bitol ODCS v3.2.0) with 49 checks. | [06 Governance](project/documentation/06_GOVERNANCE_AND_AI.md) |

## Documentation

1. [Scope and architecture](project/documentation/01_PROJECT_SCOPE_AND_ARCHITECTURE.md): the question, the data and how the parts connect.
2. [FAIR assessment](project/documentation/02_FAIR_ASSESSMENT.md): how findable, accessible, interoperable and reusable the data is.
3. [Data quality](project/documentation/03_QUALITY_AND_PROFILE.md): the problems we found in the data.
4. [Cleaning and Tableau](project/documentation/04_CLEANING_AND_TABLEAU.md): the Tableau Prep flow and how it matches Python.
5. [Python pipeline](project/documentation/05_PYTHON_REPRODUCIBILITY.md): every Python file explained, and how to reproduce the results.
6. [Governance and AI](project/documentation/06_GOVERNANCE_AND_AI.md): roles, risks, data contract and what the data can be used for.

## Run it

```powershell
cd project
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python pipeline.py
python audit_evidence.py
```

Run `pipeline.py` before the other scripts, because it creates the output files (they are not stored on GitHub). The full steps are in [05 Python pipeline](project/documentation/05_PYTHON_REPRODUCIBILITY.md).

## Team

| Member | Role |
| --- | --- |
| Nagothi Ram Dileep | Data owner |
| Jonnala Bhavya Sri | Data steward |
| Pulakanti Aashrith Reddy | Pipeline custodian |
| Nukala Megha Sri Sai Vardhan | Quality reviewer |

## Data and licence

Data from the City of Seattle / SDOT, downloaded on 2 November 2026. Only the traffic data has a licence (Public Domain), so we put no licence on the combined data. Please credit the City of Seattle / SDOT when you reuse it.
