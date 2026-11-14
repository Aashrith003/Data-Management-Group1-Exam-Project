"""Recreate the detailed profiling evidence in evidence/profiling/ (10 files).

Run from the project folder, after pipeline.py:
    python scripts/generate_detailed_profile.py

It reads the three raw files and data/output/road_safety_by_segment_year.csv.
It does not change the raw files, the pipeline outputs or the Tableau flow.
Files 07 and 08 contain a few sentences whose numbers were written for this
snapshot (for example "53,936 raw events"); the other values are calculated.
"""
from pathlib import Path
import hashlib
import json
import pandas as pd

FILE_INFO = {
    'crashes': ('CRASHES_2019_2025.csv', 'INCKEY'),
    'streets': ('Seattle_Streets_1_7907262242317696645.csv', 'COMPKEY'),
    'traffic': ('Traffic_Counts_by_Study_20261101.csv', 'STUDY_ID'),
}


def number(series):
    return pd.to_numeric(series.astype('string').str.replace(',', '', regex=False).str.strip(), errors='coerce')


def percentage(top, bottom):
    return round(100 * int(top) / int(bottom), 2) if bottom else None


def ranked_counts(series):
    """Value counts sorted by count (highest first); ties keep the order in which values first appear in the file."""
    first_seen = {v: i for i, v in reversed(list(enumerate(series.tolist())))}
    counts = series.value_counts(dropna=False)
    order = sorted(range(len(counts)), key=lambda i: (-int(counts.iloc[i]), first_seen.get(counts.index[i], len(first_seen))))
    return counts.iloc[order]


PROJECT = Path(__file__).resolve().parents[1]


def analyze(project_root=None, output_dir=None):
    root = Path(project_root) if project_root else PROJECT
    raw = root / 'data' / 'raw'
    output = Path(output_dir) if output_dir else root / 'evidence' / 'profiling'
    output.mkdir(parents=True, exist_ok=True)

    data = {name:pd.read_csv(raw / fname, dtype='string', low_memory=False)
            for name, (fname, key) in FILE_INFO.items()}
    c, s, t = data['crashes'], data['streets'], data['traffic']
    dt = pd.to_datetime(c['INCDATE'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
    traffic_dt = pd.to_datetime(t['START_DATE'], format='%Y %b %d %I:%M:%S %p', errors='coerce')
    speed = number(s['SPEEDLIMIT'])
    injuries = {f:number(c[f]) for f in ('INJURIES','SERIOUSINJURIES','FATALITIES')}
    adt = number(t['ADT'])

    # Full 117-field inventory, preserving blanks as missing.
    rows = []
    for source, frame in data.items():
        for f in frame.columns:
            values = frame[f]
            rows.append({'source':source, 'field':f, 'rows':len(frame),
                         'null_count':int(values.isna().sum()), 'null_pct':percentage(values.isna().sum(), len(frame)),
                         'distinct_nonnull':int(values.nunique(dropna=True)),
                         'top_value':str(ranked_counts(values.dropna()).index[0]) if values.notna().any() else '',
                         'top_value_n':int(ranked_counts(values.dropna()).iloc[0]) if values.notna().any() else 0,
                         'import_type':'string (to preserve original source values)'})
    pd.DataFrame(rows).to_csv(output / '01_full_column_profile.csv',index=False,lineterminator='\n')

    top_keys={}
    inventory=[]
    for source, (fname, key) in FILE_INFO.items():
        frame=data[source]
        k = number(frame[key]); duplicates=int(k.duplicated().sum()); nulls=int(k.isna().sum())
        top_keys[source]={'rows':len(frame),'duplicates':duplicates,'missing':nulls}
        inventory.append({'source':source,'file':fname,'rows':len(frame),'fields':len(frame.columns),
                          'key':key,'null_keys':nulls,'duplicate_keys':duplicates,
                          'source_sha256':hashlib.sha256((raw/fname).read_bytes()).hexdigest()})
    pd.DataFrame(inventory).to_csv(output/'02_source_inventory.csv',index=False,lineterminator='\n')

    missing_weather=int(c['WEATHER'].isna().sum())
    unknown_weather=int(c['WEATHER'].eq('Unknown').fillna(False).sum())
    zero_speed=int(speed.eq(0).sum()); null_speed=int(speed.isna().sum())
    invalid_dates=int(dt.isna().sum())
    invalid_traffic_start=int(traffic_dt.isna().sum())
    invalid_injury=int(sum((vals.isna() | vals.lt(0)).sum() for vals in injuries.values()))
    matched=int(c.STATUS.eq('Matched').sum())
    included_block=int((c.STATUS.eq('Matched') & c.ADDRTYPE.eq('B')).sum())
    included_inter=int((c.STATUS.eq('Matched') & c.ADDRTYPE.eq('I')).sum())
    included=included_block+included_inter
    # Inclusion dependency at the distinct segment key level, not event row level.
    street_keys=set(number(s.COMPKEY).dropna().astype('int64'))
    matched_block_keys=set(number(c.loc[c.STATUS.eq('Matched') & c.ADDRTYPE.eq('B'),'ADDR_SEGINTKEY']).dropna().astype('int64'))
    missing_block_keys=matched_block_keys-street_keys
    # Cardinality check: traffic records cannot be directly one-to-one joined to street records.
    study_per_segment=t.dropna(subset=['COMPKEY']).groupby('COMPKEY',dropna=True)['STUDY_ID'].nunique()
    multiple_study_compkeys=int((study_per_segment>1).sum())
    q1=float(adt.quantile(.25));q3=float(adt.quantile(.75));iqr=q3-q1
    hi=q3+1.5*iqr;lo=q1-1.5*iqr
    potential_adt_outliers=int(((adt<lo)|(adt>hi)).sum())
    zero_adt=int(adt.eq(0).sum())

    out_segs=root/'data'/'output'/'road_safety_by_segment_year.csv'
    use_outputs=out_segs.exists()
    coverage=None; segment_year_groups=None; traffic_covered=None
    if use_outputs:
        segs=pd.read_csv(out_segs,low_memory=False)
        traffic_covered=int(segs['Mean_Study_ADT'].notna().sum())
        segment_year_groups=len(segs)
        coverage=percentage(traffic_covered, segment_year_groups)

    kpis={
        'snapshot_source':'three local CSV snapshots, not a live portal',
        'raw_crash_rows':len(c),'raw_street_rows':len(s),'raw_traffic_study_rows':len(t),
        'raw_fields_total':sum(len(v.columns) for v in data.values()),
        'missing_weather_rows':missing_weather, 'missing_weather_pct':percentage(missing_weather,len(c)),
        'reported_unknown_weather_rows':unknown_weather,
        'usable_recorded_weather_rows':len(c)-missing_weather-unknown_weather,
        'missing_or_unknown_weather_pct':percentage(missing_weather+unknown_weather,len(c)),
        'unique_crash_keys':len(c)-top_keys['crashes']['duplicates'],
        'unique_street_keys':len(s)-top_keys['streets']['duplicates'],
        'unique_study_keys':len(t)-top_keys['traffic']['duplicates'],
        'invalid_crash_dates':invalid_dates,
        'invalid_traffic_start_dates':invalid_traffic_start,
        'invalid_injury_cells':invalid_injury,
        'zero_street_speed_rows':zero_speed,'null_street_speed_rows':null_speed,
        'speed_nonzero_nonnull_pct':percentage(len(s)-zero_speed-null_speed,len(s)),
        'source_matched_crashes':matched,
        'included_segment_crashes':included_block,
        'included_intersection_crashes':included_inter,
        'included_crashes_total':included,'included_crashes_pct':percentage(included,len(c)),
        'outside_analysis_crashes':len(c)-included,
        'source_matched_segment_distinct_keys':len(matched_block_keys),
        'segment_keys_not_in_streets_snapshot':len(missing_block_keys),
        'segment_key_inclusion_pct':percentage(len(matched_block_keys)-len(missing_block_keys),len(matched_block_keys)),
        'traffic_compkeys_with_multiple_studies':multiple_study_compkeys,
        'traffic_compkeys_total':len(study_per_segment),
        'adt_zero_rows':zero_adt,'adt_q1':q1,'adt_q3':q3,'adt_upper_iqr_fence':hi,
        'adt_iqr_flagged_rows':potential_adt_outliers,
        'segment_year_groups':segment_year_groups,
        'segment_year_same_year_study_groups':traffic_covered,
        'segment_year_study_coverage_pct':coverage,
    }
    (output/'03_quality_metrics.json').write_text(json.dumps(kpis,indent=2),encoding='utf-8',newline='\n')

    # Quality dimensions: accuracy remains explicitly unverified.
    scores=[
        ('Completeness','WEATHER populated in crash source',len(c)-missing_weather,len(c),missing_weather,'A missing value is not filled in.'),
        ('Uniqueness','No duplicate INCKEY in crashes',len(c)-top_keys['crashes']['duplicates'],len(c),top_keys['crashes']['duplicates'],'The crash key identifies events in this snapshot.'),
        ('Validity','Crash dates parse in expected format',len(c)-invalid_dates,len(c),invalid_dates,'Future invalid rows must be quarantined.'),
        ('Validity','3 injury measures numeric and >=0',3*len(c)-invalid_injury,3*len(c),invalid_injury,'The three injury columns were checked at cell level.'),
        ('Consistency','Street speed nonzero and populated',len(s)-zero_speed-null_speed,len(s),zero_speed+null_speed,'Zero values and null values are retained but flagged.'),
        ('Timeliness','Segment-year with same-year study',traffic_covered,segment_year_groups,(segment_year_groups-traffic_covered) if traffic_covered is not None else None,'Study coverage does not establish annual exposure.'),
        ('Accuracy','Independent police/field verification',None,None,None,'No independent ground truth in these source files.'),
    ]
    pd.DataFrame([{'dimension':dim,'rule':rule,'pass_n':pass_n,'total_n':total_n,'flag_n':flag_n,
                   'pass_pct':percentage(pass_n,total_n) if pass_n is not None and total_n else None,'interpretation':note}
                  for dim,rule,pass_n,total_n,flag_n,note in scores]).to_csv(output/'04_quality_dimension_audit.csv',index=False,lineterminator='\n')

    selected=[('crashes','INCKEY','event identifier'),('crashes','INCDATE','reported crash date/time'),
              ('crashes','WEATHER','recorded weather'),('crashes','ADDRTYPE','address category'),
              ('crashes','STATUS','location-matching status'),('crashes','INJURIES','injury count'),
              ('streets','COMPKEY','street segment identifier'),('streets','SPEEDLIMIT','speed limit value'),
              ('streets','SEGLENGTH','segment length'),('traffic','STUDY_ID','study identifier'),
              ('traffic','COMPKEY','link to street segment'),('traffic','START_DATE','study start'),
              ('traffic','ADT','average daily traffic value')]
    focused=[]
    for source,field,meaning in selected:
        ser=data[source][field]; nonnull=ser.dropna()
        focused.append({'dataset':source,'column':field,'meaning':meaning,'rows':len(ser),
                        'null_count':int(ser.isna().sum()),'null_pct':percentage(ser.isna().sum(),len(ser)),
                        'distinct_nonnull':int(ser.nunique()),
                        'top_value':str(ranked_counts(nonnull).index[0]) if len(nonnull) else '',
                        'top_value_count':int(ranked_counts(nonnull).iloc[0]) if len(nonnull) else 0})
    pd.DataFrame(focused).to_csv(output/'05_critical_column_profile.csv',index=False,lineterminator='\n')

    structure=[
        {'check':'FD - street record','measure':'COMPKEY -> ONSTREET (current Streets snapshot)','result':'PASS in snapshot','evidence':f"{len(s):,} distinct COMPKEY values among {len(s):,} rows",'why_it_matters':'Street attributes should come from the keyed Streets table, not the collision text.'},
        {'check':'FD - intersection text','measure':'INTKEY -> LOCATION (crash source)','result':'PASS in snapshot' if int((c.dropna(subset=['INTKEY']).groupby('INTKEY').LOCATION.nunique()>1).sum())==0 else 'REVIEW',
         'evidence':'No differing non-null LOCATION strings found for the same non-null INTKEY','why_it_matters':'Intersection names are descriptive; INTKEY is the grouping key.'},
        {'check':'Inclusion dependency','measure':'Matched block crash ADDR_SEGINTKEY ∈ Streets.COMPKEY','result':'PARTIAL',
         'evidence':f"{len(missing_block_keys):,} of {len(matched_block_keys):,} distinct crash segment keys absent from Streets snapshot",'why_it_matters':'Historical collisions and current Streets may not cover identical snapshots.'},
        {'check':'Cardinality','measure':'Traffic.COMPKEY -> many STUDY_ID','result':'ONE-TO-MANY',
         'evidence':f"{multiple_study_compkeys:,} of {len(study_per_segment):,} traffic segment keys have multiple studies",'why_it_matters':'Pre-aggregate/choose eligible study records before joining crash group counts.'},
        {'check':'IQR screening','measure':'Traffic.ADT outside [Q1-1.5 IQR, Q3+1.5 IQR]','result':'REVIEW CANDIDATES',
         'evidence':f"{potential_adt_outliers:,}/{len(t):,} ADT values flagged; upper fence {hi:,.2f}", 'why_it_matters':'High traffic is plausible; do not automatically delete outliers.'},
        {'check':'Domain review','measure':'Traffic.ADT = 0','result':'REVIEW CANDIDATES',
         'evidence':f"{zero_adt:,} zero ADT rows",'why_it_matters':'Zero values should be documented before inclusion in derived averages.'}
    ]
    pd.DataFrame(structure).to_csv(output/'06_relationship_checks.csv',index=False,lineterminator='\n')

    before_after=[
        ('Raw crash records','53,936 raw events','53,936 retained with scope labels','No source rows deleted'),
        ('Analysis inclusion','Not classified for this analysis','41,525 included; 12,411 outside','Scope rather than data loss'),
        ('Crash weather','12,350 missing','12,350 missing, explicitly identified','No invented weather values'),
        ('Street speed','140 zero + 20 null','140 zero + 20 null flagged','Do not claim true speed is corrected'),
        ('Crash date parse','0 invalid of 53,936','0 invalid; validation rule present','Synthetic tests prove failure handling'),
        ('Traffic coverage',f"{traffic_covered:,} of {segment_year_groups:,} with study" if use_outputs else 'Not assessed',
         f'{coverage:.2f}% coverage disclosed' if use_outputs else 'Not assessed','Cannot claim traffic-adjusted citywide risk'),
    ]
    pd.DataFrame(before_after,columns=['item','before_raw_or_undocumented','after_handling','claim_limit']).to_csv(output/'07_before_after_evidence.csv',index=False,lineterminator='\n')

    plans=[
        (1,'Prevent fan-out joins','Multiple traffic studies can share a street key','Keep crash counts at location-year grain; summarize traffic separately','Compare crash totals before and after every join'),
        (2,'Separate analysis scope','12,411 events are outside selected matched segment/intersection scope','Keep all records with explicit included/excluded reason','53,936 = 41,525 + 12,411'),
        (3,'Date-match traffic cautiously',f"Only {coverage:.2f}% of segment-year groups have eligible study" if coverage is not None else 'Study coverage not available',
         'Flag unavailable study evidence; avoid risk-per-vehicle rankings','Study coverage KPI and null preservation'),
        (4,'Treat weather as incomplete','12,350 missing and 246 Unknown','Retain original values and create weather-status flag','Weather missing rate remains 22.90%'),
        (5,'Flag questionable speed','140 zeros and 20 nulls in Streets','Treat zero as unknown for speed-based interpretation; do not overwrite raw CSV','Zero/null speed counts disclosed'),
    ]
    pd.DataFrame(plans,columns=['priority','issue','evidence','decision','proof_or_expected_check']).to_csv(output/'08_ranked_quality_plan.csv',index=False,lineterminator='\n')

    # Domain distributions support the lecture's pattern/domain checks. Null is a category of evidence, not a value to impute.
    domain_rows=[]
    for source, field in [('crashes','WEATHER'),('crashes','ADDRTYPE'),('crashes','STATUS'),
                          ('crashes','ROADCOND'),('streets','SPEEDLIMIT'),('traffic','TRAFFIC_FLOW_DIR_ID')]:
        frame=data[source]
        series=frame[field].fillna('<NULL>')
        for value, freq in ranked_counts(series).items():
            domain_rows.append({'source':source,'field':field,'value':value,'count':int(freq),
                                'pct_of_source_rows':percentage(freq,len(frame))})
    pd.DataFrame(domain_rows).to_csv(output/'09_domain_distributions.csv',index=False,lineterminator='\n')
    date_coverage={
      'crash_date_earliest':str(dt.min().date()),'crash_date_latest':str(dt.max().date()),
      'traffic_start_earliest':str(traffic_dt.min().date()),'traffic_start_latest':str(traffic_dt.max().date()),
      'crash_date_parse_failures':invalid_dates,'traffic_start_parse_failures':invalid_traffic_start,
      'note':'These are observed date minima/maxima in the local snapshots, not a promise of portal-wide temporal coverage.'}
    (output/'10_temporal_profile.json').write_text(json.dumps(date_coverage,indent=2),encoding='utf-8',newline='\n')

    print(json.dumps(kpis,indent=2))
    return kpis

if __name__ == '__main__':
    analyze()
