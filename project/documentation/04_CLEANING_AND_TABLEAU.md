# 4. Tableau Prep transformation and cleaning log

The Tableau Prep flow was built by the group and corrected on 7 November 2026 (see *Fixes applied*). The editable flow is `../tableau/Seattle_Road_Safety_Final.tfl`; the packaged deliverable is `../tableau/Seattle_Road_Safety_Final.tflx`. The pre-correction flow is kept in the original working-package ZIP. Its output CSV files in `data/tableau_output/` are compared with Python in `evidence/08_tableau_python_count_reconciliation.csv` and `evidence/09_tableau_speed_status_differences.csv`.

**Flow configuration:** inputs read the three files in `data/raw/`; outputs `O1`, `O2`, `O4` and `O5` write to `data/tableau_output/`; the `.tflx` package embeds the three source CSVs so it opens without the original folders.

## Practical Tableau sequence and evidence needed

1. **Input:** connect the three raw CSV sources; document source row counts (53,936; 23,888; 64,532). Screenshot input profiles.
2. **Cleaning:** parse crash dates and calculate `Crash_Year`; normalize numeric location keys; label unmatched and alley records instead of deleting all source rows. Record each filter's before/after count.
3. **Segment branch:** from included matched block crashes, aggregate by `Crash_Road_Key + Crash_Year`; separately join Streets on `COMPKEY` and same-year traffic studies on `COMPKEY + year` after study filtering/aggregation.
4. **Intersection branch:** from included matched intersection crashes, aggregate by `Intersection_Key + Crash_Year`.
5. **Street endpoint branch:** select `INTKEYLO` and `INTKEYHI`, standardize both to a common `Intersection_Key`, UNION, then aggregate by intersection before joining intersection crashes.
6. **Outputs:** save validated crash detail, segment-year summary, intersection-year summary and enriched intersection summary. Check row counts and crash totals.
7. **Compare with Python:** explain the independent reconciliation in `evidence/08_...csv` and the remaining field-level discrepancies.

## Code-independent cleaning decisions (no silent corrections)

| Problem | Action | Reason |
| --- | --- | --- |
| Date formats | Parse, normalize, derive year | Enables grouping and same-year joins |
| Numeric keys with commas in Traffic studies | Remove formatting, convert to integer | Correctly relate different source systems |
| Unmatched locations | Keep and label in validated detail; exclude from location hotspot aggregation | Cannot safely attach to a location |
| Missing or Unknown weather | Keep and flag; no imputation | Do not invent source observations |
| Zero posted speed limit | Keep original, flag for review | Zero is not assumed a drivable posted speed |
| Multiple study rows per road-year | Filter eligible TOTAL study rows; aggregate before joining | Prevents duplicating crash counts |
| Two street endpoints per segment | Union + aggregate endpoints by intersection | Prevents intersection count multiplication |
| No matching Streets/Traffic | LEFT JOIN and mark coverage status | Missing reference does not invalidate the original crash |

## Verified comparison (Tableau run of 7 November 2026)

**PASS:** All `Crash_Count` values match for **16,569 segment-year**, **10,968 intersection-year** and **10,968 enriched-intersection-year** records, and the totals match (23,774 segment and 17,751 intersection crashes). `validated_crashes.csv` has 53,936 rows in both.

**RESOLVED A - speed status (114 → 0 differences):** Python flags an intersection as `Contains Zero Speed Limit — Review` when any connected street end has a posted speed of 0. The original Tableau formula in `C14` had no such rule and never counted zero-speed ends. Fix: a calculated field `Zero_Speed_Flag = IF [SPEEDLIMIT] = 0 THEN 1 ELSE 0 END` in `C11_Street_Low_Endpoint` and `C12_Street_High_Endpoint`, summed in `A5_Streets_Per_Intersection`, renamed to `Zero_Speed_Limit_Endpoints` in `C14`, and checked first in `Speed_Limit_Status`. The zero-speed counts now match Python for every intersection-year.

**RESOLVED B - `SEGLENGTH` (8 → 0 differences):** the `I2_Raw_Streets` input had typed `SEGLENGTH` as a whole number, so the 91 decimal lengths in the Streets file were read as null; 8 of them belong to segments with crashes (keys 286947, 287003, 287046, 287047, 287198, 626545, 661370, 669325). Changing the type in a later clean step did not help, because the values were already lost at input. Fix: `SEGLENGTH` set to Number (decimal) in the `I2` input step. All lengths now match Python.

**OPEN C - schema differences (no effect on any comparison):**
- The Tableau segment output carries 66 columns against Python's curated 17. Either keep only the needed columns in `C6_Final_Quality_Flags` or explain that the extra columns are pass-through street and traffic attributes.
- The Tableau intersection output contains a duplicate join key, `Intersection_Key-1`, created by `J3`; it can be removed in `C13`.
- Python's `Missing_Speed_Limit_Endpoints` column has no Tableau counterpart.

## Fixes applied

| Step | Change | Effect |
| --- | --- | --- |
| `I1`–`I3` inputs | Reconnected to `data/raw/` | Flow uses the project's own source files |
| `I2_Raw_Streets` | `SEGLENGTH` → Number (decimal) | Decimal segment lengths preserved |
| `C11`, `C12` | New `Zero_Speed_Flag` calculated field | Marks each street end with speed limit 0 |
| `A5_Streets_Per_Intersection` | SUM of `Zero_Speed_Flag` | Zero-speed ends counted per intersection |
| `C14_Intersection_Speed_Quality` | Rename to `Zero_Speed_Limit_Endpoints`; zero-speed rule first in `Speed_Limit_Status` | Same classification as Python |
| `O1`, `O2`, `O4`, `O5` outputs | Write to `data/tableau_output/` | Outputs stored with the project |
| Package | Exported as `Seattle_Road_Safety_Final.tflx` | Self-contained flow with embedded source data |
