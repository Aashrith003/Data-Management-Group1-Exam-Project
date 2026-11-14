# 2. FAIR scorecard - ORIGINAL source datasets

Course rubric: each dimension receives **0 (missing), 1 (partial), or 2 (good/complete)**. This is a **reasoned, provisional manual assessment**, not an automated internationally certified FAIR score. The assessment concerns the ORIGINAL publicly catalogued datasets, not the group's local publication status.

| Original dataset | F | A | I | R | Total / 8 | Main remaining gap |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| SDOT Collisions All Years | 2 | 2 | 1 | 1 | **6/8** | The subset's field semantics, historical corrections and reuse terms require project-specific documentation |
| Seattle Streets | 2 | 2 | 1 | 1 | **6/8** | Complex GIS codes/units and site-specific reuse/terms require explicit mapping |
| Traffic Counts by Study | 2 | 2 | 1 | 2 | **7/8** | ADT sampling, code values and some field meanings require careful interpretation |

**Combined headline score for the three sources used together: 6/8 (F 2, A 2, I 1, R 1).** When the datasets are integrated, reuse is limited by the weakest source: Collisions and Streets show no explicit licence, so the combined Reusable score is 1 even though Traffic alone scores 2.

### Why the ratings are not zero

- **Findable (2):** Each source has a titled public catalog entry, source URL, identifier, publisher information and searchable keywords.
- **Accessible (2):** Public portal routes exist, downloadable machine-readable data, no account needed for the public datasets as checked at review.
- **Interoperable (1):** CSV and identifiable keys exist, but complex source code domains, inconsistent date formatting, nullable fields, and domain-specific meanings require mapping, especially for integrative use.
- **Reusable (1–2):** Attribution/provenance can be documented; the traffic dataset explicitly lists **Public Domain**. The City of Seattle's open data policy generally supports unrestricted portal reuse subject to identifying sources/modifications, but ArcGIS GIS-portal terms should still be reviewed. Do NOT automatically label all three inputs as CC BY or CC0.

### FAIR improvement in our project package: 3/8 → 5/8

This is a **separate assessment object**: the downloaded CSV bundle plus our documentation, not the City of Seattle portals.

| Principle | Before | After | What changed and what did not |
| --- | ---: | ---: | --- |
| Findable | 0 | 1 | Added a title, keywords and structured metadata. No DOI or catalog registration. |
| Accessible | 1 | 1 | Source URLs documented. Since 12 November 2026 the project is in a public GitHub repository, but that is not a persistent identifier or archive. We therefore kept this score at 1. |
| Interoperable | 1 | 2 | Added `documentation/data_dictionary.csv` (196 raw and output fields, each with its definition source), units from SDOT field documentation, join keys and date-handling notes. 29 raw fields remain undocumented by the sources and are marked as such. |
| Reusable | 1 | 1 | Added provenance, README, code and cleaning logs. No licence has been established for the combined derived package. |
| **Total** | **3/8** | **5/8** | Only documented improvements are scored. |

We added/updated an architecture README, a structured Schema.org `metadata.json`, data inventory, data dictionary, checksums, cleaning/quality logs, reproducibility code and data contract. These **improve technical reuse**. Since 12 November 2026 the code, documentation, source snapshots, Python outputs and Tableau outputs can also be downloaded from our public GitHub repository (https://github.com/Aashrith003/Data-Management-Group1-Exam-Project). This still **does not give a DOI, an archived release or legal permission beyond the sources' terms**, so we did not raise the scores.

### Source evidence (portal metadata checked 7 November 2026)

| Source | Licence shown by the portal | Other evidence |
| --- | --- | --- |
| SDOT Collisions All Years | None displayed on the data.gov catalog entry | Access level "public"; publisher City of Seattle ArcGIS Online; **daily refresh**; contact Transportation_SeattleCityGIS (mapgis.mapgis@seattle.gov); 11 download formats including CSV and GeoJSON |
| Seattle Streets | None; the licence field contains only a disclaimer that the City "makes no representation or warranty as to its accuracy" | Federated from ArcGIS; SDOT field documentation (2018) defines `SEGLENGTH` in feet and `SPEEDLIMIT` in MPH |
| Traffic Counts by Study | **Public Domain** (`PUBLIC_DOMAIN`) | Attribution: SDOT Traffic Counts Group; first published 2023-01-11; live rows updated 2026-11-06 |

All three snapshots were downloaded on 2 November 2026. Because the Collisions and Traffic portals were updated after our download, live record counts will differ from our snapshot. Use the SHA-256 checksums in `data/output/quality_metrics.json` to identify the exact files analysed.

Links:
- Collisions: https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::sdot-collisions-all-years (catalog: https://catalog.data.gov/dataset/sdot-collisions-all-years)
- Seattle Streets: https://data.seattle.gov/dataset/Seattle-Streets/w3hh-bqt5 (field documentation: https://www.seattle.gov/Documents/Departments/SDOT/GIS/Seattle_Streets_OD.pdf)
- Traffic Counts by Study: https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc
- City open data policy (not re-checked on 7 Nov): https://www.seattle.gov/documents/departments/tech/opendata/cos_opendatapolicy.pdf

### Open items for the group

- Reuse statement for our derived outputs, which must respect the source terms above.
- Whether the professor expects one FAIR score per source (6, 6, 7) or the combined score (6/8). Both are documented above.
