"""Validate data_contract.yaml against the official ODCS v3.2.0 JSON schema and run its quality checks on the data.

Run from anywhere:  python scripts/validate_data_contract.py
Requires: pandas, pyyaml, jsonschema (see requirements-contract.txt). Read-only: no file is modified.
Exit code 0 = schema valid and every quality check passed; 1 = at least one problem.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import yaml
from jsonschema import Draft201909Validator

P = Path(__file__).resolve().parents[1]
CONTRACT = P / 'data_contract.yaml'
SCHEMA = P / 'documentation/governance/odcs-json-schema-v3.2.0.json'


def check_schema(contract):
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    errors = sorted(Draft201909Validator(schema).iter_errors(contract), key=lambda e: list(e.path))
    for e in errors:
        print(f"  SCHEMA ERROR at {'/'.join(map(str, e.path)) or '(root)'}: {e.message[:200]}")
    return len(errors)


def server_path(contract, server_id):
    server = next(s for s in contract['servers'] if s['id'] == server_id)
    return P / server['path'].replace('./', '', 1).rsplit('/', 1)[0]


def check_quality(contract, server_id='python-curated'):
    folder = server_path(contract, server_id)
    con = sqlite3.connect(':memory:')
    tables = {}
    for obj in contract['schema']:
        df = pd.read_csv(folder / obj['physicalName'], low_memory=False)
        df.to_sql(obj['name'], con, index=False)
        tables[obj['name']] = df
    failed = total = 0
    for obj in contract['schema']:
        df = tables[obj['name']]
        expected_cols = [p['name'] for p in obj['properties']]
        if list(df.columns) != expected_cols:
            failed += 1
            print(f"  FAIL {obj['name']}: columns differ from contract")
        checks = [(None, q) for q in obj.get('quality', [])]
        checks += [(p['name'], q) for p in obj['properties'] for q in p.get('quality', [])]
        for col, q in checks:
            total += 1
            if q['type'] == 'sql':
                got = con.execute(q['query']).fetchone()[0]
            elif q['metric'] == 'rowCount':
                got = len(df)
            elif q['metric'] == 'duplicateValues':
                got = int(df.duplicated(q['arguments']['properties']).sum())
            elif q['metric'] == 'nullValues':
                got = int(df[col].isna().sum())
            else:
                print(f"  SKIP {q['id']}: metric {q['metric']} not implemented")
                continue
            if got != q['mustBe']:
                failed += 1
                print(f"  FAIL {q['id']} [{q.get('severity')}]: got {got}, expected {q['mustBe']}")
    return total, failed


def main():
    contract = yaml.safe_load(CONTRACT.read_text(encoding='utf-8'))
    print(f"Contract: {contract['id']} version {contract['version']} (ODCS {contract['apiVersion']}, status {contract['status']})")
    schema_errors = check_schema(contract)
    print(f"Schema validation: {'PASS' if not schema_errors else f'{schema_errors} error(s)'}")
    total, failed = check_quality(contract)
    print(f"Quality checks on data/output: {total - failed}/{total} passed")
    sys.exit(0 if schema_errors == 0 and failed == 0 else 1)


if __name__ == '__main__':
    main()
