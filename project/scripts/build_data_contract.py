"""Generate the ODCS v3.2.0 data contract (data_contract.yaml) from the real outputs and the data dictionary.

Run from anywhere:  python scripts/build_data_contract.py
Then validate:      python scripts/validate_data_contract.py
Requires: pandas, pyyaml (see requirements-contract.txt). Does not modify any data file.
"""
import json
from pathlib import Path
import pandas as pd
import yaml

P = Path(__file__).resolve().parents[1]
OUT = P / 'data_contract.yaml'
dd = pd.read_csv(P / 'documentation/data_dictionary.csv')
qm = json.loads((P / 'data/output/quality_metrics.json').read_text(encoding='utf-8'))

TABLES = {
    'validated_crashes': dict(pk=['INCKEY'], gran='One row per original source collision (INCKEY), 2019-2025.',
        desc='All 53,936 source collisions with normalized date, keys, weather status and analysis-scope status. Excluded records are kept, not deleted.'),
    'road_safety_by_segment_year': dict(pk=['Crash_Road_Key', 'Crash_Year'], gran='One row per street segment and crash year.',
        desc='Recorded collision counts per road segment and year, left-joined to Streets attributes and eligible same-year traffic studies.'),
    'intersection_crashes_by_year': dict(pk=['Intersection_Key', 'Crash_Year'], gran='One row per intersection and crash year.',
        desc='Recorded collision counts per intersection and year.'),
    'intersection_hotspots_with_streets': dict(pk=['Intersection_Key', 'Crash_Year'], gran='One row per intersection and crash year.',
        desc='Intersection-year counts left-joined to street attributes pre-aggregated per intersection (endpoints unioned and aggregated before the join).'),
    'crash_scope_summary': dict(pk=['Road_Analysis_Status'], gran='One row per analysis-scope category.',
        desc='Number of source collisions in each analysis-scope category; reconciles to all source collisions.'),
}
SUMS = {'road_safety_by_segment_year': ('Crash_Count', 23774), 'intersection_crashes_by_year': ('Crash_Count', 17751),
        'intersection_hotspots_with_streets': ('Crash_Count', 17751), 'crash_scope_summary': ('Number_of_Crashes', 53936)}
REQUIRED_ALWAYS = {'INCKEY', 'Crash_Year', 'Crash_Count', 'Road_Analysis_Status', 'Number_of_Crashes', 'Weather_Status',
                   'Total_Injuries', 'Total_Serious_Injuries', 'Total_Fatalities', 'Street_Match_Status',
                   'Traffic_Coverage_Status', 'Intersection_Street_Status', 'Crash_Road_Key', 'Intersection_Key'}
MEASURES = {'Crash_Count', 'Total_Injuries', 'Total_Serious_Injuries', 'Total_Fatalities', 'Number_of_Crashes',
            'Mean_Study_ADT', 'Traffic_Study_Count', 'PERSONCOUNT', 'PEDCOUNT', 'PEDCYLCOUNT', 'VEHCOUNT', 'INJURIES',
            'SERIOUSINJURIES', 'FATALITIES', 'Connected_Segment_Count', 'Connected_Street_Name_Count', 'Distinct_Speed_Limits',
            'Zero_Speed_Limit_Endpoints', 'Missing_Speed_Limit_Endpoints', 'SEGLENGTH'}
ENUMS = {'Road_Analysis_Status', 'Weather_Status', 'Street_Match_Status', 'Traffic_Coverage_Status', 'Speed_Limit_Status',
         'Intersection_Street_Status', 'STATUS', 'ADDRTYPE'}


def logical(dtype, col):
    if col in ('Crash_Date',):
        return 'date'
    return {'int64': 'integer', 'float64': 'number'}.get(str(dtype), 'string')


def prop(table, col, s, pk):
    row = dd[(dd.table == f'output/{table}.csv') & (dd.field == col)]
    meaning = row.meaning.iloc[0] if len(row) else 'Not documented by source'
    unit = row.unit.iloc[0] if len(row) else 'Unknown'
    src = row.definition_source.iloc[0] if len(row) else ''
    lt = logical(s.dtype, col)
    # keys that pandas reads as float because of empty values are integer identifiers
    if lt == 'number' and col.endswith('_Key') or col in ('INTKEY', 'Traffic_Road_Key', 'Street_Road_Key', 'Study_Year', 'Traffic_Study_Count',
                                                      'Connected_Segment_Count', 'Connected_Street_Name_Count', 'Distinct_Speed_Limits',
                                                      'Min_Speed_Limit', 'Max_Speed_Limit'):
        lt = 'integer' if (s.dropna() % 1 == 0).all() else lt
    p = {'id': f'{table}_{col}', 'name': col, 'logicalType': lt, 'physicalType': str(s.dtype), 'description': f'{meaning}. Unit: {unit}.'}
    if src:
        p['customProperties'] = [{'property': 'definitionSource', 'value': src}]
    if col in pk:
        p['primaryKey'] = True
        p['primaryKeyPosition'] = pk.index(col) + 1
    nulls = int(s.isna().sum())
    if col in REQUIRED_ALWAYS and nulls == 0 or col in pk:
        p['required'] = True
    if len(pk) == 1 and col in pk:
        p['unique'] = True
    if col in MEASURES:
        p['semanticType'] = 'measure'
    elif col in pk or col in ENUMS:
        p['semanticType'] = 'dimension'
    if col in ENUMS and s.nunique() <= 12:
        p['examples'] = sorted(s.dropna().astype(str).unique().tolist())
    q = []
    if p.get('required'):
        q.append({'id': f'{table}_{col}_nulls', 'type': 'library', 'metric': 'nullValues', 'mustBe': 0,
                  'dimension': 'completeness', 'severity': 'error', 'description': f'{col} must always be populated.'})
    if col in ('Crash_Count', 'Number_of_Crashes'):
        q.append({'id': f'{table}_{col}_positive', 'type': 'sql', 'dimension': 'conformity', 'severity': 'error',
                  'description': f'{col} is a positive integer.',
                  'query': f'SELECT COUNT(*) FROM {table} WHERE {col} < 1', 'mustBe': 0})
    if q:
        p['quality'] = q
    return p


schema = []
for t, meta in TABLES.items():
    df = pd.read_csv(P / f'data/output/{t}.csv', low_memory=False)
    pk = meta['pk']
    obj = {'id': t, 'name': t, 'physicalName': f'{t}.csv', 'logicalType': 'object', 'physicalType': 'csv file',
           'description': meta['desc'], 'dataGranularityDescription': meta['gran'],
           'properties': [prop(t, c, df[c], pk) for c in df.columns]}
    q = [{'id': f'{t}_rowcount', 'type': 'library', 'metric': 'rowCount', 'mustBe': len(df), 'dimension': 'completeness',
          'severity': 'error', 'description': f'Row count for the archived snapshot downloaded 2026-11-02 ({len(df):,} rows).'}]
    if len(pk) > 1 or pk:
        q.append({'id': f'{t}_grain_unique', 'type': 'library', 'metric': 'duplicateValues', 'mustBe': 0,
                  'arguments': {'properties': pk}, 'dimension': 'uniqueness', 'severity': 'error',
                  'description': f'The grain ({", ".join(pk)}) is unique. Pipeline STOP rule.'})
    if t in SUMS:
        c, v = SUMS[t]
        assert int(df[c].sum()) == v, (t, c, df[c].sum(), v)
        q.append({'id': f'{t}_conservation', 'type': 'sql', 'dimension': 'consistency', 'severity': 'error',
                  'description': f'Crash conservation: SUM({c}) equals {v:,} source crashes in scope. Pipeline STOP rule.',
                  'query': f'SELECT SUM({c}) FROM {t}', 'mustBe': v})
    if t == 'validated_crashes':
        q += [
            {'id': 'validated_crashes_weather_missing', 'type': 'sql', 'dimension': 'completeness', 'severity': 'info',
             'description': 'Monitor: WEATHER missing (12,350 = 22.90% in the snapshot). Kept, not imputed.',
             'query': "SELECT COUNT(*) FROM validated_crashes WHERE Weather_Status = 'Missing'", 'mustBe': 12350},
            {'id': 'validated_crashes_severity_mismatch', 'type': 'sql', 'dimension': 'accuracy', 'severity': 'warning',
             'description': 'Monitor: SEVERITYCODE contradicts casualty counts (331 in the snapshot). Flagged, source values unchanged.',
             'query': ("SELECT COUNT(*) FROM validated_crashes WHERE (SEVERITYCODE = 2 AND INJURIES = 0 AND SERIOUSINJURIES = 0) "
                       "OR (SEVERITYCODE = 3 AND SERIOUSINJURIES = 0) OR (SEVERITYCODE = 4 AND FATALITIES = 0)"), 'mustBe': 331},
        ]
    if t == 'road_safety_by_segment_year':
        q.append({'id': 'segment_traffic_coverage', 'type': 'sql', 'dimension': 'coverage', 'severity': 'info',
                  'description': 'Monitor: segment-years with an eligible same-year traffic study (790 of 16,569 = 4.77%). Not sufficient for rate-based risk.',
                  'query': "SELECT COUNT(*) FROM road_safety_by_segment_year WHERE Traffic_Coverage_Status = 'Eligible Study Available'",
                  'mustBe': 790})
    obj['quality'] = q
    schema.append(obj)

members = [('ram.dileep', 'Nagothi Ram Dileep', 'Derived data owner', 'Approves scope, release conditions, limitations and version.'),
           ('bhavya.sri', 'Jonnala Bhavya Sri', 'Data steward', 'Data dictionary, quality definitions, scope decisions and issue log.'),
           ('aashrith.reddy', 'Pulakanti Aashrith Reddy', 'Pipeline custodian', 'Unchanged raw copies, Python and Tableau code, tests, hashes and reruns.'),
           ('megha.vardhan', 'Nukala Megha Sri Sai Vardhan', 'Quality reviewer', 'Independent Tableau/Python comparison, limitations and documentation checks.')]

contract = {
    'apiVersion': 'v3.2.0',
    'kind': 'DataContract',
    'id': 'seattle-road-safety-curated',
    'name': 'Seattle Road Safety - curated collision hotspot tables',
    'version': '2.0.0',
    'status': 'active',
    'domain': 'transportation-safety',
    'dataProduct': 'seattle_road_safety_hotspots',
    'tenant': 'SRH University Data Management, Group 1',
    'tags': ['seattle', 'sdot', 'road-safety', 'collision-counts', 'fair', 'data-quality'],
    'contractCreatedTs': '2026-11-07T00:00:00Z',
    'description': {
        'purpose': 'Describe recorded collision counts by road segment and intersection (2019-2025) and the data-quality limits that apply to them.',
        'usage': 'Identify recorded collision-count hotspots and data-quality issues for further investigation by transportation analysts and road-safety researchers.',
        'limitations': ('Counts are not exposure-adjusted risk: only 4.77% of segment-years have an eligible same-year traffic study. '
                        'Street attributes come from a current snapshot, not a historical inventory. Study ADT is not full-year exposure. '
                        'No independent ground-truth accuracy check. No production warehouse or AI model. '
                        'Not for causal inference, individual-level prediction or automated resource allocation.'),
        'authoritativeDefinitions': [
            {'type': 'businessDefinition', 'url': 'https://www.seattle.gov/Documents/Departments/SDOT/GIS/Collisions_OD.pdf', 'description': 'SDOT Collisions field documentation'},
            {'type': 'businessDefinition', 'url': 'https://www.seattle.gov/Documents/Departments/SDOT/GIS/Seattle_Streets_OD.pdf', 'description': 'SDOT Seattle Streets field documentation (2018-07-09)'},
        ],
    },
    'servers': [
        {'id': 'python-curated', 'server': 'python-curated', 'type': 'local', 'environment': 'prod', 'format': 'csv',
         'path': './data/output/*.csv', 'description': 'Curated outputs written by pipeline.py (authoritative).'},
        {'id': 'tableau-exports', 'server': 'tableau-exports', 'type': 'local', 'environment': 'validation', 'format': 'csv',
         'path': './data/tableau_output/*.csv', 'description': 'Tableau Prep exports used for independent reconciliation; the first four outputs only.'},
    ],
    'schema': schema,
    'team': {'name': 'SRH University Data Management, Group 1', 'description': 'Student group responsible for the derived data product.',
             'members': [{'username': u, 'name': n, 'role': r, 'description': d, 'dateIn': '2026-11-02'} for u, n, r, d in members]},
    'roles': [
        {'role': 'examiner_read', 'access': 'read', 'description': 'Course examiner: read access to all outputs and evidence.'},
        {'role': 'analyst_read', 'access': 'read', 'description': 'Intended consumers: read curated outputs within the documented limitations.'},
        {'role': 'pipeline_write', 'access': 'write', 'description': 'Only the pipeline custodian regenerates outputs, via pipeline.py.',
         'firstLevelApprovers': 'Pipeline custodian', 'secondLevelApprovers': 'Derived data owner'},
    ],
    'slaProperties': [
        {'property': 'frequency', 'value': 'manual', 'description': 'Manual snapshot refresh; no scheduled updates.'},
        {'property': 'retention', 'value': 'project duration', 'description': 'Kept for the course project; raw snapshots retained unchanged with SHA-256 hashes.'},
    ],
    'authoritativeDefinitions': [
        {'type': 'source', 'url': 'https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::sdot-collisions-all-years', 'description': 'SDOT Collisions All Years (no licence displayed)'},
        {'type': 'source', 'url': 'https://data.seattle.gov/dataset/Seattle-Streets/w3hh-bqt5', 'description': 'Seattle Streets (no licence; no-warranty disclaimer)'},
        {'type': 'source', 'url': 'https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc', 'description': 'Traffic Counts by Study (Public Domain)'},
    ],
    'customProperties': [
        {'property': 'sourceOwner', 'value': 'City of Seattle / Seattle Department of Transportation'},
        {'property': 'snapshotPeriod', 'value': '2019-01-01/2025-12-31'},
        {'property': 'snapshotDownloaded', 'value': '2026-11-02'},
        {'property': 'inputSha256', 'value': qm['input_sha256']},
        {'property': 'classification', 'value': 'public open data; source terms apply; no licence assigned to the derived package'},
        {'property': 'approvalStatus', 'value': 'approved by Group 1 on 2026-11-07',
         'description': 'Approved by the group; derived data owner: Nagothi Ram Dileep.'},
        {'property': 'stopRules', 'value': ['missing_required_columns', 'duplicate_or_invalid_primary_keys', 'negative_or_non_numeric_injury_counts',
                                            'duplicate_group_grain', 'crash_count_non_conservation', 'join_row_count_change'],
         'description': 'Enforced in rules.py and pipeline.py; the pipeline stops before writing any output.'},
        {'property': 'quarantineRules', 'value': ['unparseable_crash_dates']},
        {'property': 'changePolicy', 'value': 'Schema-breaking changes need a new major version, a full test rerun and group approval; source refreshes are tracked by hash and download date.'},
    ],
}
OUT.write_text('# Open Data Contract Standard (ODCS) v3.2.0 - https://bitol-io.github.io/open-data-contract-standard/\n'
               + yaml.safe_dump(contract, sort_keys=False, allow_unicode=True, width=120), encoding='utf-8', newline='\n')
print('written', OUT, 'tables', len(schema), 'properties', sum(len(o['properties']) for o in schema),
      'quality checks', sum(len(o['quality']) for o in schema) + sum(len(p.get('quality', [])) for o in schema for p in o['properties']))
