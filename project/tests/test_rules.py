"""Run from project root with: python -m unittest discover -s tests"""
import unittest
import pandas as pd
from rules import QualityGateError, check_unique_required_key, verify_group_identity

class ValidationTests(unittest.TestCase):
    def test_duplicate_street_key_causes_stop(self):
        with self.assertRaises(QualityGateError):
            check_unique_required_key(pd.Series(['123', '123']), 'Streets.COMPKEY')
    def test_wrong_crash_total_causes_stop(self):
        df=pd.DataFrame({'key':[1,2],'year':[2024,2024],'Crash_Count':[3,1]})
        with self.assertRaises(QualityGateError):
            verify_group_identity(df,['key','year'],5)
    def test_conserved_crash_total_passes(self):
        df=pd.DataFrame({'key':[1,2],'year':[2024,2024],'Crash_Count':[3,1]})
        verify_group_identity(df,['key','year'],4)

if __name__=='__main__':unittest.main()
