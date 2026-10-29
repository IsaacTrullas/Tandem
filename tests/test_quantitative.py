import unittest
from datetime import datetime
import cv2,numpy as np
from tandem.quantitative import fit_calibration,match_ink,separate_layers,temporary_regions,extended_rectangles,match_extended,expected_extended


class Quantitative(unittest.TestCase):
    def test_tick_spacing_calibrates_independent_of_font_offset(self):
        ticks=[{'value':3,'y':745},{'value':2,'y':795},{'value':1,'y':845}]
        result=fit_calibration(ticks,887)
        self.assertAlmostEqual(result['units_per_pixel'],.02)
        self.assertEqual(result['zero_y'],887)
        self.assertGreater(result['uncertainty_units_per_hour'],0)

    def test_inconsistent_scale_is_not_calibrated(self):
        self.assertIsNone(fit_calibration([{'value':3,'y':740},{'value':2,'y':750},{'value':1,'y':845}],887))

    def test_one_tick_needs_drawn_grid_and_independent_readouts(self):
        tick=[{'value':2,'y':845}]
        self.assertIsNone(fit_calibration(tick,887))
        label={'text':'.6','rate':.6,'line_y':873}
        self.assertIsNotNone(fit_calibration(tick,887,[740,790,838],[label]))
        self.assertIsNone(fit_calibration(tick,887,[740,790,838],[dict(label,rate=5)]))

    def test_white_antialias_does_not_merge_two_blue_strokes(self):
        a=np.array([[[0,118,174],[0,145,220],[128,187,214],[200,228,246]]],dtype='uint8')
        dark=match_ink(a,(0,118,174),12);bright=match_ink(a,(0,145,220),12)
        self.assertTrue(dark[0,0]);self.assertFalse(dark[0,1]);self.assertTrue(dark[0,2])
        self.assertTrue(bright[0,1]);self.assertFalse(bright[0,0]);self.assertFalse(bright[0,3])

    def scene(self):
        a=np.ones((974,2432,3),dtype='uint8')*255
        a[861:887,56:2296]=[200,228,246]
        a[859:861,56:2296]=[0,118,174]
        a[820:822,500:550]=[0,145,220]
        a[822:887,500:502]=[0,145,220];a[822:887,548:550]=[0,145,220]
        return a

    def test_nominal_profile_and_variable_bar_are_separate_nonadditive_series(self):
        cal={'zero_y':887,'units_per_pixel':.02,'uncertainty_units_per_hour':.08}
        labels=[{'line_y':859.5,'rate':.6,'box':[60,830,140,858]}]
        layers=separate_layers(self.scene(),(56,2295,633,739),cal,labels)
        profile=next(p for p in layers['basal_setting'] if p[0]==520)
        bar=next(p for p in layers['basal_control_iq'] if p[0]==520)
        self.assertEqual(profile[3],.6);self.assertGreater(bar[3],1)
        self.assertIn('ocr',profile[4]);self.assertIn('digitized',bar[4])

    def test_conflicting_ocr_amount_is_not_propagated_into_profile(self):
        cal={'zero_y':887,'units_per_pixel':.02,'uncertainty_units_per_hour':.08}
        bad=[{'line_y':859.5,'rate':5.6,'box':[60,830,140,858]}]
        point=separate_layers(self.scene(),(56,2295,633,739),cal,bad)['basal_setting'][0]
        self.assertLess(point[3],1);self.assertIn('no_consistent_readout',point[4])

    def test_close_profile_levels_use_height_before_label_distance(self):
        a=np.ones((974,2432,3),dtype='uint8')*255
        a[859:861,56:700]=[0,118,174];a[861:863,700:2296]=[0,118,174]
        cal={'zero_y':887,'units_per_pixel':.02,'uncertainty_units_per_hour':.08}
        labels=[{'line_y':859.5,'rate':.6,'box':[64,830,145,858]},
                {'line_y':861.5,'rate':.54,'box':[702,833,783,861]}]
        points=separate_layers(a,(56,2295,633,739),cal,labels)['basal_setting']
        self.assertEqual(next(p for p in points if p[0]==650)[3],.6)
        self.assertEqual(next(p for p in points if p[0]==1000)[3],.54)

    def test_orange_fill_without_dashes_remains_ambiguous(self):
        a=np.ones((974,2432,3),dtype='uint8')*255;a[800:835,500:550]=[255,240,216]
        r=temporary_regions(a,(56,2295,633,739),887)
        self.assertEqual(r[0]['classification'],'ambiguous_orange_fill_border_unresolved')

    def test_orange_fill_and_two_dashed_edges_are_recognized(self):
        a=np.ones((974,2432,3),dtype='uint8')*255;a[800:835,500:550]=[255,240,216]
        for x in range(500,551,10):
            a[797:800,x:x+5]=[219,150,90];a[835:838,x:x+5]=[219,150,90]
        r=temporary_regions(a,(56,2295,633,739),887)
        self.assertEqual(r[0]['classification'],'temporary_fill_and_dashes')

    def test_dashed_top_and_solid_sides_match_source_legend_style(self):
        a=np.ones((974,2432,3),dtype='uint8')*255;a[800:835,500:550]=[255,240,216]
        for x in range(500,551,10):a[797:800,x:x+5]=[219,150,90]
        a[800:835,497:500]=[219,150,90];a[800:835,550:553]=[219,150,90]
        a[835:838,497:553]=[219,150,90]
        r=temporary_regions(a,(56,2295,633,739),887)
        self.assertEqual(r[0]['classification'],'temporary_fill_and_dashes')

    def extended(self):
        return {'record_id':17,'extended_start_local':'2026-01-01T22:00:00','extended_end_local':'2026-01-02T01:00:00'}

    def test_extended_bolus_is_sliced_across_midnight_without_a_new_event(self):
        row=self.extended()
        self.assertEqual(expected_extended(row,'2026-01-01')[2:],(1320,1440))
        self.assertEqual(expected_extended(row,'2026-01-02')[2:],(0,60))
        self.assertIsNone(expected_extended(row,'2026-01-03'))

    def test_occluded_extended_bar_joins_only_when_both_csv_endpoints_agree(self):
        axis=(0,1440,633,739)
        pieces=[[1320,620,1360,633],[1380,620,1440,633]]
        result=match_extended(pieces,[self.extended()],'2026-01-01',axis)
        self.assertEqual(len(result),1);self.assertEqual(result[0]['row']['record_id'],17)
        self.assertEqual(result[0]['error'],0)
        self.assertEqual(match_extended([[1300,620,1370,633]],[self.extended()],'2026-01-01',axis),[])


if __name__=='__main__':unittest.main()
