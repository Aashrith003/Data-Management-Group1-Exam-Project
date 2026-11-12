# 5. Reproducible Python pipeline (Chapter 3)

**Implementation:** `pipeline.py` loads immutable raw snapshots; `rules.py` contains quality gates; `profile.py` profiles original columns; `audit_evidence.py` independently audits and compares outputs; `tests/` contains unit tests. The source follows **load → clean → validate → classify → aggregate → enrich → output**.

## Executed validation evidence

- **10 of 10 unit tests passed**, covering uniqueness, conservation, missing keys, nonnegative injury metrics, invalid-date quarantine, preserving scope exclusions, and preserving join cardinality.
- **Two consecutive executions produced identical hashes** for all five published pipeline CSV outputs, verified in `evidence/12_repeat_run_verification.json`. The immutable input hashes also matched. Log timestamps are naturally different.
- `evidence/08_tableau_python_count_reconciliation.csv` shows the keyed per-group crash count matches for the three comparable aggregate outputs; after the Tableau corrections of 7 November 2026, speed-status flags and segment lengths also match (`evidence/09_...` is empty).
- Source keys (`INCKEY`,`COMPKEY`,`STUDY_ID`) have no missing/duplicate values in the current input snapshots.

## Cross-platform verification (Windows, 7 November 2026)

The pipeline was re-run twice on Windows 11 (Python 3.11.0, pandas 2.3.3) in a separate copy of the project, so the published outputs were not overwritten.

- **Repeatable:** both runs produced identical output hashes, and all input hashes and row/count metrics matched `data/output/quality_metrics.json`.
- **Line endings found and fixed:** before the fix, the Windows output hashes differed from the recorded ones although the content was identical, because pandas writes Windows line endings (CRLF) on Windows. `pipeline.py`, `profile.py` and `audit_evidence.py` now always write Unix line endings (LF). After the fix, the Windows outputs, `quality_metrics.json` and the quarantine file are **byte-identical to the recorded files**, so the published hashes can be checked on any operating system.
- **pandas version:** `requirements.txt` allows pandas 2.x and 3.x. pandas 2 labels text columns `object` and pandas 3 labels them `str`, which changed the type column of `raw_column_profile.csv`. `profile.py` now reports `str` for both, so the profile content no longer depends on the pandas version. The pipeline outputs were unaffected.
- **Tests:** 10 of 10 passed on the corrected code.

## STOP vs QUARANTINE vs ANALYSIS SCOPE

- **STOP:** Missing required columns, malformed/duplicate source keys, nonnumeric/negative injury measures, non-unique aggregated groups, join multiplication or loss, or failure to conserve crash totals. These indicate an unsafe trusted output.
- **QUARANTINE:** Invalid crash dates cannot be grouped by year. Current snapshot has **zero** such rows, but the synthetic unit test proves the behavior.
- **ANALYTICAL EXCLUSION:** Unmatched-location and alley records are still valid source events; retained in `validated_crashes.csv` with a reason, not discarded or called corrupt.

## Windows run instructions

```powershell
cd Seattle_Road_Safety_Exam
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python profile.py
python -m unittest discover -s tests -v
python pipeline.py
python audit_evidence.py
python pipeline.py
```

This adds logs but does not edit raw files. Compare `data/output/quality_metrics.json` output hashes across runs; also see the already executed evidence in `evidence/`.

## Limits to reproducibility claims

The tests prove defined invariants, not the objective correctness of each collision record. The Tableau and Python outputs agree on crash counts, speed-status flags and segment lengths, but not on column layout (see `documentation/04_CLEANING_AND_TABLEAU.md`). Exact versions are not pinned in `requirements.txt`; the verification above records the versions used. The GitHub repository link is still to be added once the repository is published.
