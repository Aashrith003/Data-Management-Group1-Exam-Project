"""Produce examination evidence without modifying raw files or trusted pipeline outputs.
Run: python audit_evidence.py
The audit includes counts, profiling, source/target consistency, and limitations.
"""
from __future__ import annotations
from pathlib import Path
import json
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT/'data'/'raw'
OUT = ROOT/'data'/'output'
TABLEAU = ROOT/'data'/'tableau_output'
EVIDENCE = ROOT/'evidence'
FILES = {
    'crashes': ('CRASHES_2019_2025.csv','INCKEY'),
    'streets': ('Seattle_Streets_1_7907262242317696645.csv','COMPKEY'),
    'traffic': ('Traffic_Counts_by_Study_20261101.csv','STUDY_ID'),
}

def num(s):
    return pd.to_numeric(s.astype('string').str.replace(',','',regex=False).str.strip(),errors='coerce')

def pct(n,d):
    return round(100*n/d,2) if d else None

def write_csv(name,items):
    pd.DataFrame(items).to_csv(EVIDENCE/name,index=False,lineterminator='\n')

def main():
    EVIDENCE.mkdir(exist_ok=True,parents=True)
    d={k:pd.read_csv(RAW/f,dtype='string',low_memory=False) for k,(f,_) in FILES.items()}
    metrics=json.loads((OUT/'quality_metrics.json').read_text())
    records=[]
    dataset_checks=[]
    for key,df in d.items():
        file_name,pk=FILES[key]
        digest=hashlib.sha256((RAW/file_name).read_bytes()).hexdigest()
        dataset_checks.append({'dataset':key,'filename':file_name,'row_count':len(df),'column_count':len(df.columns),'primary_key':pk,'missing_key':int(df[pk].isna().sum()),'duplicate_key':int(num(df[pk]).duplicated().sum()),'source_sha256':digest})
        for column in df.columns:
            s=df[column]
            records.append({'dataset':key,'column':column,'rows':len(df),'missing':int(s.isna().sum()),'missing_pct':pct(int(s.isna().sum()),len(df)),'distinct_nonnull':int(s.nunique(dropna=True)),'dtype_imported':'string'})
    write_csv('01_raw_column_profile_extended.csv',records)
    write_csv('02_source_inventory.csv',dataset_checks)
    c,s,t = d['crashes'],d['streets'],d['traffic']
    dates=pd.to_datetime(c.INCDATE,format='%m/%d/%Y %I:%M:%S %p',errors='coerce')
    studydates=pd.to_datetime(t.START_DATE,format='%Y %b %d %I:%M:%S %p',errors='coerce')
    cr_inj={col:num(c[col]) for col in ('INJURIES','SERIOUSINJURIES','FATALITIES')}
    sl=num(s.SPEEDLIMIT)
    valid_segment=pd.read_csv(OUT/'road_safety_by_segment_year.csv',low_memory=False)
    valid_inter=pd.read_csv(OUT/'intersection_hotspots_with_streets.csv',low_memory=False)
    validated=pd.read_csv(OUT/'validated_crashes.csv',low_memory=False)
    nullweather=int(c.WEATHER.isna().sum()); zerospeed=int(sl.eq(0).sum()); speed_missing=int(sl.isna().sum())
    any_injury_invalid=sum(int((x.lt(0)|x.isna()).sum()) for x in cr_inj.values())
    bad_dates=int(dates.isna().sum()); bad_studydates=int(studydates.isna().sum())
    traffic_covered=int(valid_segment.Mean_Study_ADT.notna().sum()); nsegment=len(valid_segment)
    basic={
      'raw_crashes':len(c),'raw_streets':len(s),'raw_traffic':len(t),
      'missing_weather_records':nullweather,'missing_weather_pct':pct(nullweather,len(c)),
      'reported_unknown_weather':int(c.WEATHER.eq('Unknown').fillna(False).sum()),
      'zero_speed_records':zerospeed,'null_speed_records':speed_missing,
      'crashes_invalid_dates':bad_dates,'traffic_invalid_start_dates':bad_studydates,
      'invalid_injury_cell_count':any_injury_invalid,
      'segment_crashes':int(metrics['segment_crashes']),'intersection_crashes':int(metrics['intersection_crashes']),
      'excluded_crashes':len(c)-int(metrics['segment_crashes'])-int(metrics['intersection_crashes']),
      'included_crashes':int(metrics['segment_crashes'])+int(metrics['intersection_crashes']),
      'included_pct':pct(int(metrics['segment_crashes'])+int(metrics['intersection_crashes']),len(c)),
      'segments_with_eligible_study':traffic_covered,'segment_year_groups':nsegment,'same_year_traffic_coverage_pct':pct(traffic_covered,nsegment),
      'segment_groups_without_street_ref':int(valid_segment.Street_Road_Key.isna().sum()),
      'intersection_groups_without_street_ref':int(valid_inter.Connected_Segment_Count.isna().sum()),
      'all_raw_source_keys_unique':all(x['duplicate_key']==0 and x['missing_key']==0 for x in dataset_checks),
      'segment_count_conserved':int(valid_segment.Crash_Count.sum())==int(metrics['segment_crashes']),
      'intersection_count_conserved':int(valid_inter.Crash_Count.sum())==int(metrics['intersection_crashes']),
      'scope_count_conserved':len(validated)==len(c),
      'analysis_max_year':int(dates.dt.year.max()),'analysis_min_year':int(dates.dt.year.min())
    }
    (EVIDENCE/'03_quality_kpis.json').write_text(json.dumps(basic,indent=2),encoding='utf8',newline='\n')
    checks=[
      ['Completeness','Crash weather present',len(c)-nullweather,len(c),nullweather,'Missing weather remains missing; no imputation'],
      ['Uniqueness','Crash keys unique',len(c)-int(num(c.INCKEY).duplicated().sum()),len(c),int(num(c.INCKEY).duplicated().sum()),'Stop on repeated INCKEY'],
      ['Uniqueness','Street keys unique',len(s)-int(num(s.COMPKEY).duplicated().sum()),len(s),int(num(s.COMPKEY).duplicated().sum()),'Stop on repeated COMPKEY'],
      ['Uniqueness','Traffic study keys unique',len(t)-int(num(t.STUDY_ID).duplicated().sum()),len(t),int(num(t.STUDY_ID).duplicated().sum()),'Stop on repeated STUDY_ID'],
      ['Validity','Parseable crash date',len(c)-bad_dates,len(c),bad_dates,'Quarantine unparseable crash dates'],
      ['Validity','Injury fields nonnegative and numeric',3*len(c)-any_injury_invalid,3*len(c),any_injury_invalid,'Stop on impossible or malformed injury values'],
      ['Consistency','Street speed limit is not zero',len(s)-zerospeed,len(s),zerospeed,'Flag zero placeholders; do not assume zero speed'],
      ['Consistency','Segment-year output with same-year traffic evidence',traffic_covered,nsegment,nsegment-traffic_covered,'Low coverage: do not claim exposure-adjusted risk'],
      ['Consistency','Segment group joins conserve crashes',int(valid_segment.Crash_Count.sum()),int(metrics['segment_crashes']),abs(int(valid_segment.Crash_Count.sum())-int(metrics['segment_crashes'])),'Check group counts before and after joins'],
      ['Consistency','Intersection group joins conserve crashes',int(valid_inter.Crash_Count.sum()),int(metrics['intersection_crashes']),abs(int(valid_inter.Crash_Count.sum())-int(metrics['intersection_crashes'])),'Check group counts before and after joins'],
      ['Timeliness','Same-year traffic evidence for segment-years',traffic_covered,nsegment,nsegment-traffic_covered,'Traffic studies vary in year and period; not representative of full year'],
      ['Accuracy','Ground-truth crash/location verification',None,None,None,'Not externally verified against police reports or field measurements'],
    ]
    write_csv('04_quality_dimension_scorecard.csv',[{'dimension':a,'measure':b,'passing':c,'denominator':e,'flagged':f,'pass_pct':pct(c,e) if c is not None and e else None,'policy_or_caveat':g} for a,b,c,e,f,g in checks])
    yearly=dates.dt.year.value_counts(dropna=False).sort_index()
    write_csv('05_crashes_by_year.csv',[{'year':str(k),'crash_count':int(v)} for k,v in yearly.items()])
    scope=pd.read_csv(OUT/'crash_scope_summary.csv')
    scope.to_csv(EVIDENCE/'06_scope_reconciliation.csv',index=False,lineterminator='\n')
    # Intersection endpoints: joining raw edges would multiply collision rows; aggregate per intersection first.
    street_keys=set(num(s.COMPKEY).dropna().astype('int64').tolist())
    crash_segment_keys=set(num(c.loc[c.ADDRTYPE.eq('B')&c.STATUS.eq('Matched'),'ADDR_SEGINTKEY']).dropna().astype('int64').tolist())
    inclusion={
      'distinct_matched_block_crash_segment_keys':len(crash_segment_keys),
      'distinct_matched_block_segment_keys_not_in_streets_snapshot':len(crash_segment_keys-street_keys),
      'referential_inclusion_pct':pct(len(crash_segment_keys&street_keys),len(crash_segment_keys)),
      'caution':'Street snapshot and historic crash dates differ; missing matches do not necessarily prove bad crash source data.'
    }
    (EVIDENCE/'07_inclusion_dependency.json').write_text(json.dumps(inclusion,indent=2),encoding='utf8',newline='\n')
    # Cross-field consistency: does the severity code agree with the recorded casualty counts?
    # Flags rows for review only; nothing is changed or removed.
    sev=num(c.SEVERITYCODE); inj,ser,fat=cr_inj['INJURIES'],cr_inj['SERIOUSINJURIES'],cr_inj['FATALITIES']
    severity_rules=[
      ('Missing','SEVERITYCODE is blank',sev.isna(),len(c)),
      ('1 = Property Damage Only','any INJURIES, SERIOUSINJURIES or FATALITIES > 0',sev.eq(1)&(inj.gt(0)|ser.gt(0)|fat.gt(0)),int(sev.eq(1).sum())),
      ('2 = Injury','INJURIES and SERIOUSINJURIES both 0',sev.eq(2)&inj.eq(0)&ser.eq(0),int(sev.eq(2).sum())),
      ('3 = Serious Injury','SERIOUSINJURIES = 0',sev.eq(3)&ser.eq(0),int(sev.eq(3).sum())),
      ('4 = Fatal','FATALITIES = 0',sev.eq(4)&fat.eq(0),int(sev.eq(4).sum())),
    ]
    write_csv('13_severity_consistency.csv',[{'severity_code':a,'inconsistent_if':b,'flagged_rows':int(m.fillna(False).sum()),'rows_with_code':n,'action':'Flag for review; source values kept unchanged'} for a,b,m,n in severity_rules])
    tableau_diff=[]
    for name,keys in [('road_safety_by_segment_year.csv',['Crash_Road_Key','Crash_Year']),('intersection_crashes_by_year.csv',['Intersection_Key','Crash_Year']),('intersection_hotspots_with_streets.csv',['Intersection_Key','Crash_Year'])]:
        p=OUT/name; q=TABLEAU/name
        if not q.exists(): continue
        a=pd.read_csv(p,low_memory=False);b=pd.read_csv(q,low_memory=False)
        common=set(a.columns)&set(b.columns)
        row={'file':name,'python_rows':len(a),'tableau_rows':len(b),'python_cols':len(a.columns),'tableau_cols':len(b.columns),'common_columns':len(common)}
        if not set(keys).issubset(common):row['check']='Key field(s) absent';tableau_diff.append(row);continue
        a=a[keys+['Crash_Count']].copy();b=b[keys+['Crash_Count']].copy()
        # Coerce numeric join key types; both outputs derive same source identifiers.
        for col in keys+['Crash_Count']:
            a[col]=pd.to_numeric(a[col],errors='coerce'); b[col]=pd.to_numeric(b[col],errors='coerce')
        m=a.merge(b,on=keys,how='outer',suffixes=('_python','_tableau'),indicator=True)
        wrong=m[(m._merge!='both') | (m.Crash_Count_python!=m.Crash_Count_tableau)]
        row['missing_or_different_crash_counts']=len(wrong)
        row['count_sum_python']=int(a.Crash_Count.sum());row['count_sum_tableau']=int(b.Crash_Count.sum())
        row['check']='PASS' if len(wrong)==0 else 'REVIEW'
        tableau_diff.append(row)
        if len(wrong): wrong.head(100).to_csv(EVIDENCE/(name.replace('.csv','_count_differences.csv')),index=False,lineterminator='\n')
    write_csv('08_tableau_python_count_reconciliation.csv',tableau_diff)
    if 'Speed_Limit_Status' in valid_inter and 'Speed_Limit_Status' in pd.read_csv(TABLEAU/'intersection_hotspots_with_streets.csv',nrows=0).columns:
        p=valid_inter[['Intersection_Key','Crash_Year','Speed_Limit_Status','Zero_Speed_Limit_Endpoints','Min_Speed_Limit','Max_Speed_Limit']]
        q=pd.read_csv(TABLEAU/'intersection_hotspots_with_streets.csv',low_memory=False)[['Intersection_Key','Crash_Year','Speed_Limit_Status']]
        m=p.merge(q,on=['Intersection_Key','Crash_Year'],suffixes=('_python','_tableau'),validate='one_to_one')
        m[m.Speed_Limit_Status_python.fillna('')!=m.Speed_Limit_Status_tableau.fillna('')].to_csv(EVIDENCE/'09_tableau_speed_status_differences.csv',index=False,lineterminator='\n')
    # Field dictionary with source flags. Exact descriptions for important analysis output columns.
    definitions={
      'INCKEY':'Collision event identifier (crashes source key)',
      'INCDATE':'Original reported crash date/time string',
      'STATUS':'Source location matching status, not a successful join to Streets',
      'ADDRTYPE':'Source address category (I=intersection; B=block/segment; A=alley)',
      'ADDR_SEGINTKEY':'Source segment or intersection location key',
      'COMPKEY':'Street segment identifier used for cross-source joins',
      'STUDY_ID':'Traffic study identifier',
      'Crash_Date':'Normalized crash date',
      'Crash_Year':'Calendar year of crash',
      'Road_Analysis_Status':'Scope/inclusion classification and reason',
      'Crash_Road_Key':'Crash segment key derived from ADDR_SEGINTKEY',
      'Intersection_Key':'Intersection identifier from INTKEY',
      'Crash_Count':'Number of distinct crash records in location-year group',
      'Total_Injuries':'Sum of recorded INJURIES in group',
      'Total_Serious_Injuries':'Sum of recorded SERIOUSINJURIES in group',
      'Total_Fatalities':'Sum of recorded FATALITIES in group',
      'Mean_Study_ADT':'Arithmetic mean ADT of eligible same-year TOTAL traffic studies; not full-year exposure',
      'Traffic_Study_Count':'Number of eligible studies contributing to mean',
      'Street_Match_Status':'Whether street segment key matched the Streets snapshot',
      'Traffic_Coverage_Status':'Whether an eligible same-year traffic study is available',
      'Connected_Segment_Count':'Distinct street segments connected to the intersection',
      'Connected_Street_Name_Count':'Distinct named streets connected to the intersection',
      'Min_Speed_Limit':'Minimum recorded endpoint speed value; includes zero source placeholders',
      'Max_Speed_Limit':'Maximum recorded endpoint speed value',
      'Zero_Speed_Limit_Endpoints':'Number of intersection endpoint rows with a zero speed limit',
      'Speed_Limit_Status':'Flag class for recorded speed limits, prioritizing zero placeholders',
      'WEATHER':'Original recorded weather category; may be missing or Unknown',
      'Weather_Status':'Recorded / Missing / Reported Unknown',
      'ONSTREET':'Street name from Streets snapshot',
      'SPEEDLIMIT':'Recorded posted street speed limit in miles per hour (SDOT field documentation); 0 flagged as questionable',
      'SEGLENGTH':'Street segment length in feet (SDOT field documentation); may have decimals',
      'ADT':'Average daily traffic during the study, vehicles per day; not a full-year average',
      'TRAFFIC_FLOW_DIR_ID':'Study flow direction; code 11 = TOTAL',
      'START_DATE':'Original study start time',
      'ACTUAL_DAYS':'Actual study duration in days',
      'INTENDED_DAYS':'Planned study duration in days'
    }
    dd=[]
    for file in ['validated_crashes.csv','road_safety_by_segment_year.csv','intersection_hotspots_with_streets.csv']:
        frame=pd.read_csv(OUT/file,low_memory=False)  # whole file, so column types are not guessed from a few rows
        for col in frame.columns:
            dd.append({'output_file':file,'field':col,'dtype_in_csv':str(frame[col].dtype),'meaning':definitions.get(col,'Source field retained for traceability; consult Seattle original schema'),'nullable_or_caveat': 'May be null; verify against source and domain rules' if col not in ('INCKEY','Crash_Count','Crash_Year','Road_Analysis_Status') else 'Expected populated for its output rows'})
    write_csv('10_output_data_dictionary.csv',dd)
    print(json.dumps(basic,indent=2))
    print('Tableau comparison:',tableau_diff)
    print('Generated',len(list(EVIDENCE.glob('*'))),'evidence files')

if __name__=='__main__': main()
