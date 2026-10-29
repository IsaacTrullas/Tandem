import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from copy import deepcopy
from tandem.bolus_display import is_food_bolus,FOOD_BOLUS_LABEL
from tandem.plot_symbols import COLORS
from tandem.event_hover import message
from tandem.timeline_widget import TimelineWidget
from test_event_hover_widget import APP,START,point,bundle

class FoodBolusTests(unittest.TestCase):
    def test_positive_associated_grams_from_api_or_csv_only(self):
        for details in ({'carbohydrate_grams':20},{'csv_values':{'carbohydrate_grams':20}}):
            self.assertTrue(is_food_bolus(point(START,1,**details)))
        for value in (None,0,-1,True,'20',float('nan')):
            self.assertFalse(is_food_bolus(point(START,1,carbohydrate_grams=value)))
        self.assertFalse(is_food_bolus(point(START,1,carbohydrate_grams=20,revision_count=2)))
    def test_orange_precedence_retains_bolus_dose_and_source(self):
        w=TimelineWidget('unused.sqlite');w.resize(1200,820);w.show();APP.processEvents()
        try:
            b=bundle();p=point(START+3600,.05,carbohydrate_grams=20,properties={'bolusSource':7})
            b['data']['boluses']=[p];b['data']['carbs']=[point(START+3560,20,'g')];original=deepcopy(p)
            w.current_start=START;w.render(b);w.hover_at(p['x'])
            series=next(item for item in w.plots[1].listDataItems() if item.name()==FOOD_BOLUS_LABEL)
            self.assertEqual(series.opts['symbolBrush'],COLORS['carbs']);self.assertEqual(list(series.yData),[.05])
            self.assertEqual(p,original);self.assertIn(COLORS['carbs'],w.values['bolus'].styleSheet())
            self.assertEqual(message('bolus',p)[0],FOOD_BOLUS_LABEL)
        finally:w.debounce.stop();w.close();w.deleteLater();APP.processEvents()

if __name__=='__main__':unittest.main()
