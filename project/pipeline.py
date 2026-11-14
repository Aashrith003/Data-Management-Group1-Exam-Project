"""Seattle Road Safety: the main data pipeline.

Reads the three raw CSV files, cleans and checks them, counts collisions per road
segment and intersection per year, adds street and traffic details, and writes the
results to data/output. Run with: python pipeline.py

The raw files are only read, never changed. Nothing is written until every
quality rule in rules.py has passed.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import pandas as pd
import rules

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'data' / 'output'
Q = ROOT / 'data' / 'quarantine'
LOGS = ROOT / 'logs'
FILES = {
    'crashes': 'CRASHES_2019_2025.csv',
    'streets': 'Seattle_Streets_1_7907262242317696645.csv',
    'traffic': 'Traffic_Counts_by_Study_20261101.csv',
}


def log(message):
    print(message)


def numeric(series):
    return pd.to_numeric(series.astype('string').str.replace(',', '', regex=False).str.strip(), errors='coerce')


def load_raw():
    data = {}
    for key, filename in FILES.items():
        path = RAW / filename
        if not path.exists():
            raise FileNotFoundError(f'Missing input {path}. Copy the original CSV to data/raw first.')
        df = pd.read_csv(path, dtype='string', keep_default_na=True, low_memory=False)
        rules.check_required_columns(df, key)
        data[key] = df
        log(f'Loaded {key}: {len(df):,} rows, {df.shape[1]} fields')
    return data


def clean_crashes(df):
    c = df.copy()
    c['INCKEY'] = rules.check_unique_required_key(c['INCKEY'], 'Crashes.INCKEY')
    c['Crash_Date'] = pd.to_datetime(c['INCDATE'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce').dt.normalize()
    c['Crash_Year'] = c['Crash_Date'].dt.year.astype('Int64')
    c['Crash_Road_Key'] = numeric(c['ADDR_SEGINTKEY']).astype('Int64')
    c['Intersection_Key'] = numeric(c['INTKEY']).astype('Int64')
    for col in ('INJURIES','SERIOUSINJURIES','FATALITIES'):
        c[col] = numeric(c[col])
    rules.check_nonnegative_measures(c, ('INJURIES','SERIOUSINJURIES','FATALITIES'))
    c['Weather_Status'] = 'Recorded'
    c.loc[c['WEATHER'].isna() | c['WEATHER'].astype('string').str.strip().eq('').fillna(False),'Weather_Status'] = 'Missing'
    c.loc[c['WEATHER'].astype('string').str.strip().eq('Unknown').fillna(False),'Weather_Status'] = 'Reported Unknown'
    return c


def clean_streets(df):
    s = df.copy()
    s['Street_Road_Key'] = rules.check_unique_required_key(s['COMPKEY'], 'Streets.COMPKEY')
    s['Street_Road_Key'] = s['Street_Road_Key'].astype('Int64')
    for col in ('INTKEYLO','INTKEYHI'):
        s[col] = numeric(s[col]).astype('Int64')
    s['SPEEDLIMIT'] = numeric(s['SPEEDLIMIT'])
    return s


def clean_traffic(df):
    t=df.copy()
    t['STUDY_ID'] = rules.check_unique_required_key(t['STUDY_ID'],'Traffic.STUDY_ID')
    t['Traffic_Road_Key'] = numeric(t['COMPKEY']).astype('Int64')
    t['ADT_Clean'] = numeric(t['ADT'])
    t['Study_Start_Date'] = pd.to_datetime(t['START_DATE'], format='%Y %b %d %I:%M:%S %p',errors='coerce').dt.normalize()
    t['Study_Year'] = t['Study_Start_Date'].dt.year.astype('Int64')
    t['TRAFFIC_FLOW_DIR_ID'] = numeric(t['TRAFFIC_FLOW_DIR_ID']).astype('Int64')
    t['ACTUAL_DAYS'] = numeric(t['ACTUAL_DAYS'])
    t['INTENDED_DAYS'] = numeric(t['INTENDED_DAYS'])
    t['Study_Duration_Status'] = 'Duration Met'
    t.loc[t['ACTUAL_DAYS'].isna() | t['INTENDED_DAYS'].isna(),'Study_Duration_Status'] = 'Missing Duration'
    t.loc[(t['ACTUAL_DAYS'] < t['INTENDED_DAYS']).fillna(False),'Study_Duration_Status'] = 'Shorter Than Planned'
    return t


def classify_crashes(c):
    """Scope exclusions are valid records; not automatically quarantined."""
    df=c.copy()
    status=pd.Series('Outside - Other',index=df.index,dtype='string')
    unmatched=~df['STATUS'].eq('Matched').fillna(False)
    status.loc[unmatched]='Outside - Unmatched Location'
    matched=~unmatched
    status.loc[matched & df['ADDRTYPE'].eq('A').fillna(False)]='Outside - Alley'
    status.loc[matched & df['ADDRTYPE'].eq('B').fillna(False)]='Outside - Bad Segment Key'
    status.loc[matched & df['ADDRTYPE'].eq('I').fillna(False)]='Outside - Bad Intersection Key'
    b=matched & df['ADDRTYPE'].eq('B').fillna(False) & df['Crash_Road_Key'].gt(0).fillna(False)
    i=matched & df['ADDRTYPE'].eq('I').fillna(False) & df['Intersection_Key'].gt(0).fillna(False)
    status.loc[b]='Included - Road Segment'
    status.loc[i]='Included - Intersection'
    # An unreadable date cannot be assigned to a year-based analysis.
    bad_date = df['Crash_Date'].isna()
    status.loc[bad_date] = 'Quarantined - Invalid Date'
    df['Road_Analysis_Status'] = status
    quarantine = df[bad_date].copy()
    quarantine['reason']='unparseable crash date'
    clean=df[~bad_date].copy()
    blocks=clean[clean['Road_Analysis_Status'].eq('Included - Road Segment')].copy()
    intersections=clean[clean['Road_Analysis_Status'].eq('Included - Intersection')].copy()
    return df,blocks,intersections,quarantine


def aggregate_crashes(df, key):
    result=(df.groupby([key,'Crash_Year'],dropna=False)
              .agg(Crash_Count=('INCKEY','nunique'),
                   Total_Injuries=('INJURIES','sum'),
                   Total_Serious_Injuries=('SERIOUSINJURIES','sum'),
                   Total_Fatalities=('FATALITIES','sum'))
              .reset_index())
    return result


def aggregate_traffic(t):
    eligible=t[t['Study_Year'].between(2019,2025).fillna(False)
               & t['TRAFFIC_FLOW_DIR_ID'].eq(11).fillna(False)
               & t['ADT_Clean'].gt(0).fillna(False)
               & t['Traffic_Road_Key'].notna()].copy()
    agg=(eligible.groupby(['Traffic_Road_Key','Study_Year'],dropna=False)
         .agg(Mean_Study_ADT=('ADT_Clean','mean'),
              Traffic_Study_Count=('STUDY_ID','nunique'))
         .reset_index())
    return eligible,agg


def build_intersection_roads(s):
    """Each segment contributes its low and high endpoint; never join raw edges to crashes."""
    lo=s[['Street_Road_Key','INTKEYLO','ONSTREET','SPEEDLIMIT']].rename(columns={'INTKEYLO':'Intersection_Key'})
    hi=s[['Street_Road_Key','INTKEYHI','ONSTREET','SPEEDLIMIT']].rename(columns={'INTKEYHI':'Intersection_Key'})
    edges=pd.concat([lo,hi],ignore_index=True)
    edges=edges[edges['Intersection_Key'].gt(0).fillna(False)].copy()
    # Count distinct segments and street names, not number of rows.
    summ=edges.groupby('Intersection_Key',dropna=False).agg(
        Connected_Segment_Count=('Street_Road_Key','nunique'),
        Connected_Street_Name_Count=('ONSTREET','nunique'),
        Min_Speed_Limit=('SPEEDLIMIT','min'),
        Max_Speed_Limit=('SPEEDLIMIT','max'),
        Distinct_Speed_Limits=('SPEEDLIMIT','nunique'),
        Zero_Speed_Limit_Endpoints=('SPEEDLIMIT',lambda x:int(x.eq(0).sum())),
        Missing_Speed_Limit_Endpoints=('SPEEDLIMIT',lambda x:int(x.isna().sum())),
    ).reset_index()
    summ['Speed_Limit_Status']='Different Speed Limits'
    summ.loc[summ['Min_Speed_Limit'].isna(),'Speed_Limit_Status']='No Speed Limit Available'
    summ.loc[summ['Min_Speed_Limit'].eq(summ['Max_Speed_Limit']).fillna(False),'Speed_Limit_Status']='Same Recorded Speed Limit'
    summ.loc[summ['Zero_Speed_Limit_Endpoints'].gt(0),'Speed_Limit_Status']='Contains Zero Speed Limit — Review'
    return edges,summ


def enrich_segment(block_agg,s,traffic_agg):
    streets=s[['Street_Road_Key','ONSTREET','SPEEDLIMIT','ARTDESCRIPT','SEGLENGTH']].copy()
    out=block_agg.merge(streets,left_on='Crash_Road_Key',right_on='Street_Road_Key',how='left',validate='many_to_one')
    if len(out)!=len(block_agg): raise rules.QualityGateError('Street join unexpectedly changed row count')
    out=out.merge(traffic_agg,left_on=['Crash_Road_Key','Crash_Year'],right_on=['Traffic_Road_Key','Study_Year'],how='left',validate='one_to_one')
    if len(out)!=len(block_agg): raise rules.QualityGateError('Traffic join unexpectedly changed row count')
    out['Street_Match_Status']='Street Matched'
    out.loc[out['Street_Road_Key'].isna(),'Street_Match_Status']='No Street Match'
    out['Traffic_Coverage_Status']='Eligible Study Available'
    out.loc[out['Mean_Study_ADT'].isna(),'Traffic_Coverage_Status']='No Eligible Same-Year Study'
    return out


def enrich_intersection(inter_agg,intersection_streets):
    out=inter_agg.merge(intersection_streets,on='Intersection_Key',how='left',validate='many_to_one')
    if len(out)!=len(inter_agg): raise rules.QualityGateError('Intersection join changed row count')
    out['Intersection_Street_Status']='Street Reference Available'
    out.loc[out['Connected_Segment_Count'].isna(),'Intersection_Street_Status']='No Matching Street Reference'
    return out


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def run():
    raw=load_raw()
    c=clean_crashes(raw['crashes']);s=clean_streets(raw['streets']);t=clean_traffic(raw['traffic'])
    all_crashes,blocks,intersections,quarantine=classify_crashes(c)
    block_agg=aggregate_crashes(blocks,'Crash_Road_Key')
    inter_agg=aggregate_crashes(intersections,'Intersection_Key')
    valid_studies,traffic_agg=aggregate_traffic(t)
    edges,intersection_streets=build_intersection_roads(s)
    segment=enrich_segment(block_agg,s,traffic_agg)
    inter=enrich_intersection(inter_agg,intersection_streets)
    # Fail before writing outputs if any conservation / uniqueness check is broken.
    rules.verify_group_identity(segment,['Crash_Road_Key','Crash_Year'],len(blocks))
    rules.verify_group_identity(inter,['Intersection_Key','Crash_Year'],len(intersections))
    scope=all_crashes.groupby('Road_Analysis_Status',dropna=False).agg(Number_of_Crashes=('INCKEY','nunique')).reset_index()
    if int(scope['Number_of_Crashes'].sum())!=len(c):raise rules.QualityGateError('Scope categories do not reconcile with source crashes')
    metrics={
        'raw_crashes':len(c),'raw_streets':len(s),'raw_traffic_studies':len(t),
        'segment_crashes':len(blocks),'segment_year_groups':len(segment),
        'segment_join_crash_total':int(segment.Crash_Count.sum()),
        'segment_year_groups_without_street_match':int(segment.Street_Road_Key.isna().sum()),
        'segment_year_groups_with_same_year_traffic':int(segment.Mean_Study_ADT.notna().sum()),
        'intersection_crashes':len(intersections),'intersection_year_groups':len(inter),
        'intersection_join_crash_total':int(inter.Crash_Count.sum()),
        'intersection_year_groups_without_street_match':int(inter.Connected_Segment_Count.isna().sum()),
        'endpoint_rows':len(edges),'distinct_street_endpoint_intersections':len(intersection_streets),
        'eligible_traffic_studies':len(valid_studies),'eligible_traffic_year_groups':len(traffic_agg),
        'quarantined_unparseable_date_crashes':len(quarantine),
        'missing_weather_records':int(c.WEATHER.isna().sum()),
        'zero_street_speed_limit_values':int(s.SPEEDLIMIT.eq(0).sum()),
        'input_sha256':{key:sha256(RAW/filename) for key,filename in FILES.items()},
    }
    OUT.mkdir(parents=True,exist_ok=True);Q.mkdir(parents=True,exist_ok=True);LOGS.mkdir(parents=True,exist_ok=True)
    output_files={
        'validated_crashes.csv':all_crashes,
        'road_safety_by_segment_year.csv':segment,
        'intersection_crashes_by_year.csv':inter_agg,
        'intersection_hotspots_with_streets.csv':inter,
        'crash_scope_summary.csv':scope,
    }
    output_hash={}
    for filename,df in output_files.items():
        path=OUT/filename
        df.sort_values(by=[c for c in ('Crash_Road_Key','Intersection_Key','Crash_Year','INCKEY','Road_Analysis_Status') if c in df.columns],kind='stable').to_csv(path,index=False,float_format='%.6f',date_format='%Y-%m-%d',lineterminator='\n')
        output_hash[filename]=sha256(path)
        log(f'Wrote {filename}: {len(df):,} rows')
    quarantine.to_csv(Q/'quarantine_crashes.csv',index=False,date_format='%Y-%m-%d',lineterminator='\n')
    metrics['output_sha256']=output_hash
    (OUT/'quality_metrics.json').write_text(json.dumps(metrics,indent=2,sort_keys=True),encoding='utf8',newline='\n')
    with open(LOGS/'run_log.jsonl','a',encoding='utf8',newline='\n') as f:
        f.write(json.dumps({'run_utc':datetime.now(timezone.utc).isoformat(),'status':'SUCCESS','metrics':metrics},sort_keys=True)+'\n')
    log('SUCCESS: All crash totals conserved; deterministic files written.')
    return metrics


def main():
    try:run()
    except Exception as exc:
        LOGS.mkdir(parents=True,exist_ok=True)
        with open(LOGS/'run_log.jsonl','a',encoding='utf8',newline='\n') as f:
            f.write(json.dumps({'run_utc':datetime.now(timezone.utc).isoformat(),'status':'FAILED','reason':str(exc)})+'\n')
        print(f'FAILED (no new trusted outputs should be used): {exc}',file=sys.stderr)
        sys.exit(1)


if __name__=='__main__':main()
