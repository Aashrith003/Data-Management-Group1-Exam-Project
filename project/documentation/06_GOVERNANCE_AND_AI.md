# 6. Governance, data contract, lineage and AI readiness (Chapter 4)

Editable records for this chapter are in `documentation/governance/` (`roles_matrix.csv`, `risk_register.csv`, `lineage_edges.csv`, `ai_readiness_checklist.csv`).

## Roles (SRH University Data Management, Group 1)

| Role | Holder | Accountabilities |
| --- | --- | --- |
| Source data owner | City of Seattle / SDOT (upstream) | Original datasets' collection, publication and upstream definitions |
| Derived data owner | Nagothi Ram Dileep | Approves scope, release conditions, limitations and version |
| Data steward | Jonnala Bhavya Sri | Data dictionary, quality definitions, scope decisions and issue log |
| Pipeline custodian | Pulakanti Aashrith Reddy | Unchanged raw copies, Python and Tableau code, tests, hashes and reruns |
| Quality reviewer | Nukala Megha Sri Sai Vardhan | Independent Tableau/Python comparison, limitations and documentation checks |
| Consumers | Transportation analysts, road-safety researchers | Use outputs within the documented limitations |

**Upstream roles cannot be transferred to students.** The group's roles cover only the derived product, not the City's source systems.

## Lineage narrative

`Seattle source portals → raw CSV snapshots downloaded 2 November 2026, kept unchanged with SHA-256 hashes → source profiling and quality checks → Tableau Prep and Python ETL branches → scope classification → segment or intersection aggregations → left-joined street and traffic context → curated CSVs → Tableau/Python reconciliation → count-hotspot summaries and audit evidence → users`. Both branches were re-run on 7 November 2026 and agree on crash counts, speed-status flags and segment lengths. Detailed flow: `01_PROJECT_SCOPE_AND_ARCHITECTURE.md`; edge list: `governance/lineage_edges.csv`.

## Data contract

The machine-readable contract `data_contract.yaml` follows the **Bitol Open Data Contract Standard (ODCS) v3.2.0** (contract version 2.0.0, status `active`: approved by Group 1 on 7 November 2026). It contains:

- **description:** purpose, intended usage and limitations, with links to SDOT's field documentation;
- **servers:** the Python outputs (`data/output`, authoritative) and the Tableau exports (`data/tableau_output`, validation);
- **schema:** all five outputs and their 79 columns, with logical and physical types, descriptions and units from the data dictionary, primary keys and required/unique flags;
- **quality:** 49 executable checks: row counts, grain uniqueness, required fields, positive counts, crash conservation (23,774 segment, 17,751 intersection, 53,936 overall) and monitoring checks for missing weather (12,350), traffic coverage (790) and severity mismatches (331);
- **team and roles:** the four group members with their roles, plus read and write access roles;
- **slaProperties, authoritativeDefinitions, customProperties:** manual refresh, the three source datasets and their licences, download date (2026-11-02), input hashes, STOP and quarantine rules, change policy.

The contract passes the official ODCS v3.2.0 JSON schema (`documentation/governance/odcs-json-schema-v3.2.0.json`) and all 49 checks pass on the data. To reproduce:

```powershell
python -m pip install -r requirements-contract.txt
python scripts/build_data_contract.py      # regenerate from outputs and dictionary
python scripts/validate_data_contract.py   # schema validation + 49 quality checks
```

Every STOP rule is also enforced in `rules.py` and `pipeline.py`, which stop before writing any output if a rule fails. Change policy: schema-breaking changes need a new major version, a full test rerun and group approval; source refreshes are tracked by hash and download date.

## Risk register

| Risk | Evidence | Control | Status |
| --- | --- | --- | --- |
| Sparse traffic coverage | 95.23% of segment-years lack an eligible same-year study | Coverage KPI; claims limited to collision counts | Open |
| Current streets vs. historical crashes | 2019–2025 crashes joined to a current Streets snapshot | Label street attributes as a snapshot; no retrospective causal claims | Open |
| Join multiplication | 5,298 road keys with several studies; two endpoints per segment | Aggregate before joining; STOP on row-count change or non-conservation | Controlled |
| Missing weather | 22.90% null plus 246 Unknown | Weather_Status flag; no imputation | Open |
| Zero or missing speed limits | 140 zero, 20 missing | Speed_Limit_Status flag; no imputation | Open |
| Severity code inconsistency | 331 codes contradict casualty counts; 13 blank | Flagged in `evidence/13_severity_consistency.csv`; source unchanged | Open |
| Tableau/Python divergence | Previously 114 speed-status and 8 length differences | Tableau flow corrected; field-level comparison in evidence 08/09 | Resolved (0 differences) |
| Source schema or content drift | Live portals refresh regularly | Required-column and key rules, tests, input hashes, recorded download date | Controlled for the snapshot |
| Source licensing | Only Traffic shows a licence (Public Domain) | Credit City of Seattle/SDOT; no licence assigned to the derived package | Open |
| Location privacy and misuse | Record-level locations and coordinates in `validated_crashes.csv` | Intended use limited to aggregate hotspot analysis; follow source terms | Open |

## AI-readiness assessment

| Check | Status |
| --- | --- |
| Provenance, dictionary, machine-readable metadata | Yes |
| Unique keys, validated groups, reproducibility (Windows and Linux) | Yes |
| Tableau/Python parity of values | Yes (column layout differs) |
| Label quality (severity) | Partial: 331 inconsistent, 13 blank |
| Traffic exposure for citywide rates | No: 4.77% coverage |
| Independent ground truth | No |

**Ready for:** documented descriptive aggregates, reproducible quality demonstrations, and limited exploratory models with explicit constraints. **Not ready for:** reliable citywide collision risk per vehicle, causal inference about speed or weather, individual-level prediction, or high-stakes automated resource allocation. The project contains no trained or validated predictive model and no external ground truth. Future work would need a historical street inventory, longitudinal exposure data and carefully defined outcome labels.
