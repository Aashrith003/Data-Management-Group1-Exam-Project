import unittest
import pandas as pd
from rules import QualityGateError, check_nonnegative_measures, check_unique_required_key, verify_group_identity
from pipeline import clean_crashes, classify_crashes, enrich_segment

class ExamEvidenceTests(unittest.TestCase):
    def test_negative_injury_stops(self):
        with self.assertRaises(QualityGateError):
            check_nonnegative_measures(pd.DataFrame({'INJURIES': [2,-1]}), ('INJURIES',))

    def test_non_numeric_injury_stops(self):
        with self.assertRaises(QualityGateError):
            check_nonnegative_measures(pd.DataFrame({'INJURIES': [2,'unknown']}), ('INJURIES',))

    def test_valid_zero_injury_passes(self):
        check_nonnegative_measures(pd.DataFrame({'INJURIES': [0,3]}), ('INJURIES',))

    def test_missing_key_stops(self):
        with self.assertRaises(QualityGateError):
            check_unique_required_key(pd.Series(['123',None]),'INCKEY')

    def test_duplicated_output_groups_stop(self):
        with self.assertRaises(QualityGateError):
            verify_group_identity(pd.DataFrame({'key':[1,1],'year':[2024,2024],'Crash_Count':[1,1]}), ['key','year'],2)

    def test_invalid_date_quarantined_but_unmatched_is_scope_excluded(self):
        raw=pd.DataFrame({
           'INCKEY':['1','2','3'],
           'INCDATE':['01/03/2024 12:00:00 AM','not a date','01/04/2024 01:00:00 AM'],
           'STATUS':['Matched','Matched','Unmatched'], 'ADDRTYPE':['B','B','B'],
           'ADDR_SEGINTKEY':['100','100','100'], 'INTKEY':[None,None,None],
           'INJURIES':['0','0','0'], 'SERIOUSINJURIES':['0','0','0'],
           'FATALITIES':['0','0','0'], 'WEATHER':['Clear','Rain','Clear']
        })
        allc,blocks,inters,quarantine=classify_crashes(clean_crashes(raw))
        self.assertEqual(len(quarantine),1)
        self.assertEqual(len(blocks),1)
        self.assertEqual(len(inters),0)
        self.assertEqual((allc.Road_Analysis_Status=='Outside - Unmatched Location').sum(),1)

    def test_street_join_preserves_group_row_count(self):
        block=pd.DataFrame({'Crash_Road_Key':pd.Series([100],dtype='Int64'),'Crash_Year':pd.Series([2023],dtype='Int64'),'Crash_Count':[2]})
        street=pd.DataFrame({'Street_Road_Key':pd.Series([100],dtype='Int64'),'ONSTREET':['TEST ST'],'SPEEDLIMIT':[25],'ARTDESCRIPT':['Local'],'SEGLENGTH':[100]})
        traffic=pd.DataFrame({'Traffic_Road_Key':pd.Series([100],dtype='Int64'),'Study_Year':pd.Series([2023],dtype='Int64'),'Mean_Study_ADT':[1000],'Traffic_Study_Count':[1]})
        self.assertEqual(len(enrich_segment(block,street,traffic)),1)

if __name__=='__main__': unittest.main()
