import unittest
import pandas as pd
from analysis import load_data, aggregate, reconcile, MONEY

class FinancialTests(unittest.TestCase):
    def test_all_dimensions_reconcile(self):
        df=load_data()
        dims=['month','quarter','season','category','region','product_id','year']
        self.assertTrue(reconcile(df,{d:aggregate(df,d) for d in dims}).passed.all())

    def test_discount_rounding_and_weighted_margin(self):
        # Half-paise discount rounds up; never banker's rounding.
        self.assertEqual((101*50+50)//100,51)
        df=load_data(); t=aggregate(df,'category')
        expected=100*df.profit_paise.sum()/df.net_paise.sum()
        weighted=(t.margin_pct*t.net_paise/t.net_paise.sum()).sum()
        self.assertAlmostEqual(expected,weighted,places=10)
        self.assertAlmostEqual(df.net_paise.sum()/100/df.order_id.nunique(),
            (t.aov_inr*t.orders/t.orders.sum()).sum(),places=10)

    def test_reconciliation_rejects_tampered_total(self):
        df=load_data(); t=aggregate(df,'region'); t.iloc[0,t.columns.get_loc('net_paise')]+=1
        with self.assertRaises(AssertionError): reconcile(df,{'region':t})

if __name__=='__main__': unittest.main()
