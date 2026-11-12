"""Describe every column of the three raw files and save it as data/output/raw_column_profile.csv.
Run: python profile.py
"""
from pathlib import Path
import pandas as pd
from pipeline import RAW, OUT, FILES


def dtype_label(s):
    """Text columns are 'object' in pandas 2 and 'str' in pandas 3; report one label so the profile is version-independent."""
    name = str(s.dtype)
    return 'str' if name in ('object', 'string', 'str') else name


def main():
    rows=[]
    for dataset,filename in FILES.items():
        df=pd.read_csv(RAW/filename,low_memory=False)
        for col in df.columns:
            s=df[col]
            rows.append({'dataset':dataset,'field':col,'imported_dtype':dtype_label(s),
                         'row_count':len(df),'missing_count':int(s.isna().sum()),
                         'missing_pct':round(s.isna().mean()*100,2),
                         'distinct_nonnull':int(s.nunique(dropna=True)),
                         'top_or_example':str(s.mode(dropna=True).iloc[0])[:100] if s.notna().any() else ''})
    OUT.mkdir(parents=True,exist_ok=True)
    dest=OUT/'raw_column_profile.csv'
    pd.DataFrame(rows).to_csv(dest,index=False,lineterminator='\n')
    print('Wrote',dest, 'fields profiled',len(rows))

if __name__=='__main__':main()
