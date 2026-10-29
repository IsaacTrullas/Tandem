"""Synthetic presentation tests for highlighting a recorded dose of 0.05 U."""
from copy import deepcopy
import math
import unittest

from tandem.bolus_display import is_005_bolus, MARKED_BOLUS_LABEL
from tandem.event_guides import collect_event_times


def bolus(value=.05, unit='U', x=3600, **details):
    return {'x': x, 'value': value, 'unit': unit, 'details': details,
            'time': '2026-10-29T01:00:00', 'id': 'synthetic-bolus'}


class BolusDisplayTests(unittest.TestCase):
    def test_exact_recorded_dose_and_binary_float_noise_are_recognized(self):
        for value in (.05, math.nextafter(.05, 0),
                      math.nextafter(.05, 1), .05 - 5e-13, .05 + 5e-13):
            with self.subTest(value=value):
                self.assertTrue(is_005_bolus(bolus(value)))

    def test_distinct_doses_are_not_rounded_into_the_marked_category(self):
        for value in (.049, .051, .005, .0501, 0, -.05, 1):
            with self.subTest(value=value):
                self.assertFalse(is_005_bolus(bolus(value)))

    def test_values_outside_the_absolute_noise_tolerance_are_rejected(self):
        for value in (.05 - 2e-12, .05 + 2e-12):
            with self.subTest(value=value):
                self.assertFalse(is_005_bolus(bolus(value)))

    def test_missing_non_numeric_boolean_and_non_finite_values_are_rejected(self):
        for value in (None, False, True, '0.05', '0,05',
                      float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value):
                self.assertFalse(is_005_bolus(bolus(value)))
        missing = bolus()
        del missing['value']
        self.assertFalse(is_005_bolus(missing))
        self.assertFalse(is_005_bolus(None))
        self.assertFalse(is_005_bolus({}))

    def test_explicit_insulin_units_are_required(self):
        for unit in (None, '', 'u', 'U/h', 'mg/dL', 'g', 'units'):
            with self.subTest(unit=unit):
                self.assertFalse(is_005_bolus(bolus(unit=unit)))
        missing = bolus()
        del missing['unit']
        self.assertFalse(is_005_bolus(missing))

    def test_explicitly_ambiguous_dose_is_not_highlighted(self):
        self.assertFalse(is_005_bolus(bolus(ambiguous=True)))
        self.assertTrue(is_005_bolus(bolus(ambiguous=False)))

    def test_source_revision_ambiguity_uses_the_same_conservative_rule(self):
        for details in ({'revision_count': 2}, {'revision_ids': [1, 2]}):
            with self.subTest(details=details):
                self.assertFalse(is_005_bolus(bolus(**details)))
        self.assertTrue(is_005_bolus(bolus(revision_count=1, revision_ids=[1])))

    def test_classification_does_not_change_source_or_metadata(self):
        source = bolus(properties={'recordedDose': .05}, revision_ids=[1])
        original = deepcopy(source)
        self.assertTrue(is_005_bolus(source))
        self.assertEqual(source, original)

    def test_event_guides_use_the_dose_label_and_keep_other_boluses_generic(self):
        source = {'boluses': [bolus(), bolus(.5, x=7200),
                              bolus(ambiguous=True, x=10800)]}
        guides = collect_event_times(source)
        self.assertEqual(MARKED_BOLUS_LABEL, 'Bolo de 0,05 U')
        self.assertEqual([g['labels'] for g in guides],
                         [(MARKED_BOLUS_LABEL,), ('Bolo',), ('Bolo',)])
        self.assertEqual([g['x'] for g in guides], [3600, 7200, 10800])

    def test_coincident_bolus_and_carbohydrate_share_one_guide_without_duplicates(self):
        source = {'boluses': [bolus(), bolus()],
                  'carbs': [{'x': 3600, 'value': 15, 'unit': 'g', 'details': {}},
                            {'x': 3600, 'value': 15, 'unit': 'g', 'details': {}}]}
        original = deepcopy(source)
        guides = collect_event_times(source)
        self.assertEqual(guides, ({'x': 3600,
                                   'labels': (MARKED_BOLUS_LABEL, 'Carbohidratos'),
                                   'priority': 4},))
        self.assertEqual(source, original)


if __name__ == '__main__':
    unittest.main()
