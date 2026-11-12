# 3. Data quality audit and profile (Chapter 2)

All figures are produced from the archived input and `python audit_evidence.py`. See evidence files 01–10. All *six* lecture quality dimensions are addressed; where measurement is impossible, say so.

| Dimension | What was checked | Evidence and result | Consequence |
| --- | --- | --- | --- |
| Completeness | `WEATHER` present | 12,350 / 53,936 missing (**22.90%**); 246 also explicitly `Unknown` (23.35% missing or Unknown combined) | No weather-conditioned risk inference for all crashes; preserve missingness |
| Uniqueness | Keys `INCKEY`, `COMPKEY`, `STUDY_ID` | 0 duplicate IDs and 0 missing IDs in the three snapshots | Stop if future source keys break |
| Validity | Crash dates, numeric injury counts, number format | 0 unparseable crash dates; 0 negative/malformed cells among 161,808 injury cells. Traffic `ADT` is stored as text with thousands separators (e.g. `9,759.57`); a plain numeric parse loses 85% of values, so the pipeline strips commas first | Quarantine invalid dates; STOP on malformed injury measures |
| Consistency | Speed-limit semantics, cross-table joins, severity vs. casualty counts | 140 zero and 20 null street speed values; counts conserved after joins. `SEVERITYCODE` disagrees with casualty counts in 331 crashes (273 "Injury" with 0 injuries, 56 "Serious Injury" with 0 serious injuries, 2 "Fatal" with 0 fatalities) and is blank in 13 (`evidence/13_severity_consistency.csv`) | Flag zero speed rather than using it as a real speed; flag severity mismatches for review, do not recode them |
| Timeliness | Collision year vs. traffic-study year | Only 790 of 16,569 segment-year groups (**4.77%**) have eligible same-year study | A traffic-normalized risk ranking of all locations is not justified |
| Accuracy | Independent ground-truth checks; internal plausibility | No ground truth in the provided files. Internal proxy: the 331 severity mismatches (0.6%) show that some source records contradict themselves | Counts are largely internally consistent, but not externally certified as real-world truth |

### Profiling beyond basic nulls

- **Column profiles:** `evidence/01_raw_column_profile_extended.csv` inventories all 117 raw fields and records missing rates, distinct-value counts, and types.
- **Key dependency:** `INCKEY` is the crash event grain. A unique key means it functionally identifies recorded values within this snapshot, subject to future source changes.
- **Inclusion dependency:** `ADDR_SEGINTKEY` needs an appropriate Streets `COMPKEY`, but valid historical collisions may not match today's street snapshot. See `evidence/07_inclusion_dependency.json`.
- **Domain findings:** `ADDRTYPE` partitions intersection and segment populations; `TRAFFIC_FLOW_DIR_ID=11` means TOTAL according to the portal; zero speed values are special handling candidates.
- **Structural caution:** One raw street segment can connect two intersection endpoints. Union these endpoints and **aggregate by intersection** before joining crash counts, preventing row multiplication.

### Detailed profiling (recomputed from the raw CSVs, 7 November 2026)

| Check | Result | Why it matters |
| --- | --- | --- |
| `WEATHER` domain | 12 categories | Missing and `Unknown` are kept as separate states |
| `SPEEDLIMIT` domain | 10 distinct values (mostly 20, 25, 30 mph); 140 zeros, 20 null | Zero is a placeholder, not a speed |
| Traffic `COMPKEY` | 6,699 distinct keys; 1,217 studies without a key | Studies without a key cannot be linked to a road |
| Traffic join cardinality | 5,298 of 6,699 road keys have more than one study | Joining raw studies would multiply crash rows, so traffic is aggregated first |
| `ADT` zeros | 2,738 studies report ADT = 0 | Excluded from `Mean_Study_ADT` by the `ADT > 0` rule |
| `ADT` outliers (1.5 × IQR) | Q1 = 2,502.46, Q3 = 11,837.18, upper fence 25,839.25; 5,569 values outside | A review list, not proof of error; high-volume roads are plausible |
| Time coverage | Crashes 2019-01-01 to 2025-12-31; traffic studies 1990-01-30 to 2026-10-16 | Year-matching is required before combining |
| Segment inclusion | 8,245 distinct segment keys; 29 (49 crashes) absent from Streets: 99.65% included | Historical keys may not exist in today's street network |
| Intersection inclusion | 4,602 distinct intersection keys; 16 absent from every Streets endpoint | Same snapshot effect on the intersection side |
| Functional dependency | `INTKEY` → `LOCATION`: 0 violations across 5,063 keys | Intersection keys are consistent within this snapshot |

Extended profile files (full column profile, domain distributions, temporal profile, relationship checks) are in `evidence/profiling/`. The intersection-inclusion and `INTKEY` → `LOCATION` figures were recomputed for this document and are not yet written to an evidence file.

### Before → after - explain, do not embellish

| Check | Before | After |
| --- | --- | --- |
| Raw crash rows | 53,936 | 53,936 retained with scope status |
| Analyzable crashes | Unclassified | 41,525 labelled for segment/intersection summaries |
| Missing weather | 12,350 missing | Still 12,350 missing, explicitly labelled (not imputed) |
| Zero speed values | 140 in Streets | Still present but flagged in the Python intersection output |
| Segment-year aggregation | Event-level records | 16,569 segment-year rows, 23,774 crashes conserved |
| Intersection-year aggregation | Event-level records | 10,968 intersection-year rows, 17,751 crashes conserved |
| Date quarantine | Unchecked | 0 invalid date rows in this snapshot; functionality tested synthetically |

**Important distinction:** 'Cleaning' can mean standardizing, flagging, quarantining, or deciding not to use a record in a particular analysis. It does **not** necessarily mean removing records or improving a missing percentage.
