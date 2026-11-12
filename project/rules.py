"""Quality rules for the Seattle Road Safety pipeline.

Each rule raises QualityGateError when the data is unsafe, which stops the whole
run before any output is written. Written with plain pandas, so no extra
validation library is needed.
"""
from __future__ import annotations
import pandas as pd

REQUIRED = {
    'crashes': {'INCKEY', 'STATUS', 'ADDRTYPE', 'INCDATE', 'ADDR_SEGINTKEY',
                'INTKEY', 'INJURIES', 'SERIOUSINJURIES', 'FATALITIES', 'WEATHER'},
    'streets': {'COMPKEY', 'ONSTREET', 'SPEEDLIMIT', 'INTKEYLO', 'INTKEYHI'},
    'traffic': {'STUDY_ID', 'COMPKEY', 'START_DATE', 'TRAFFIC_FLOW_DIR_ID',
                'ADT', 'ACTUAL_DAYS', 'INTENDED_DAYS'},
}


class QualityGateError(ValueError):
    """An error serious enough to stop the entire published output."""


def check_required_columns(df: pd.DataFrame, name: str):
    missing = REQUIRED[name] - set(df.columns)
    if missing:
        raise QualityGateError(f'{name}: required columns missing: {sorted(missing)}')


def check_unique_required_key(series: pd.Series, name: str):
    numeric = pd.to_numeric(series.astype('string').str.replace(',', '', regex=False), errors='coerce')
    if numeric.isna().any():
        raise QualityGateError(f'{name}: {int(numeric.isna().sum())} missing or malformed IDs')
    if numeric.duplicated().any():
        raise QualityGateError(f'{name}: {int(numeric.duplicated().sum())} duplicate IDs')
    return numeric.astype('int64')


def verify_group_identity(df: pd.DataFrame, columns: list[str], source_count: int,
                          count_column: str = 'Crash_Count'):
    if df.duplicated(columns).any():
        raise QualityGateError(f'Nonunique output location/year groups: {columns}')
    actual = int(df[count_column].sum())
    if actual != source_count:
        raise QualityGateError(f'Crash conservation failed: {actual} vs {source_count}')


def check_nonnegative_measures(df: pd.DataFrame, columns: tuple[str, ...]):
    """Fail closed on invalid numeric severity counts; never silently turn malformed counts into zero."""
    for col in columns:
        nums = pd.to_numeric(df[col], errors='coerce')
        invalid = nums.isna() | (nums < 0)
        if invalid.any():
            raise QualityGateError(f'{col}: {int(invalid.sum())} missing/malformed/negative counts')
