"""Synthetic tests for guide selection and collision-free time annotation."""
from copy import deepcopy
from datetime import datetime
import unittest

from tandem.event_guides import collect_event_times, place_event_labels

EPOCH = datetime(1970, 1, 1)


def wall(stamp):
    return (datetime.fromisoformat(stamp) - EPOCH).total_seconds()


def point(stamp, **details):
    return {'x': wall(stamp), 'details': details, 'time': stamp,
            'raw_json': 'Synthetic source must not be retained in guide records'}


def event(stamp, priority=2, labels=('Bolo',)):
    return {'x': wall(stamp), 'labels': labels, 'priority': priority}


def measure(text):
    return len(text) * 6


class EventGuideTests(unittest.TestCase):
    def test_coincident_events_share_one_guide_and_keep_labels_and_priority(self):
        stamp = '2026-10-29T15:02:49'
        data = {'boluses': [point(stamp), point(stamp)],
                'carbs': [point(stamp)],
                'events': [point(stamp, event_code=5, label='Alarma')],
                'clock_changes': [point('2026-10-29T08:00:00', event_code=13,
                                         label='Cambio de hora')]}
        result = collect_event_times(data)
        self.assertEqual(len(result), 2)
        self.assertLess(result[0]['x'], result[1]['x'])
        self.assertEqual(result[1]['x'], wall(stamp))
        self.assertEqual(result[1]['labels'], ('Bolo', 'Carbohidratos', 'Alarma'))
        self.assertEqual(result[1]['priority'], 5)

    def test_continuous_samples_do_not_generate_event_guides(self):
        data = {'glucose': [point('2026-10-29T01:00:00', kind='cgm'),
                            point('2026-10-29T02:00:00', kind='bg')],
                'basal': [point('2026-10-29T03:00:00')],
                'iob': [point('2026-10-29T04:00:00')]}
        guides = collect_event_times(data)
        self.assertEqual(len(guides), 1)
        self.assertEqual(guides[0]['x'], wall('2026-10-29T02:00:00'))
        self.assertEqual(guides[0]['labels'], ('Glucemia introducida',))

    def test_non_numeric_and_non_finite_positions_are_ignored(self):
        data = {'boluses': [{'x': x} for x in
                            (None, '2026-10-29', float('nan'), float('inf'),
                             float('-inf'))]}
        self.assertEqual(collect_event_times(data), ())

    def test_boolean_is_not_a_timestamp(self):
        self.assertEqual(collect_event_times({'boluses': [{'x': True}, {'x': False}]}), ())

    def test_collection_preserves_input_and_does_not_retain_full_source_records(self):
        source = {'events': [point('2026-10-29T12:00:00', label='Cambio de modo',
                                    event_code=229, properties={'mode': 2})]}
        before = deepcopy(source)
        guides = collect_event_times(source)
        self.assertEqual(source, before)
        self.assertIsInstance(guides, tuple)
        self.assertEqual(set(guides[0]), {'x', 'labels', 'priority'})
        self.assertIsInstance(guides[0]['labels'], tuple)

    def test_daily_labels_keep_exact_coordinate_and_display_hours_and_minutes(self):
        source = event('2026-10-29T15:02:49')
        start, end = wall('2026-10-29T00:00:00'), wall('2026-10-30T00:00:00')
        result = place_event_labels([source], start, end, 1200, measure)
        self.assertEqual(result[0]['x'], source['x'])
        self.assertEqual(result[0]['text'], '15:02')
        self.assertAlmostEqual(result[0]['center'], (source['x'] - start) * 1200 / 86400)

    def test_close_zoom_shows_source_seconds_without_rounding_to_scale_ticks(self):
        source = event('2026-10-29T15:02:49')
        result = place_event_labels([source], wall('2026-10-29T14:30:00'),
                                    wall('2026-10-29T15:30:00'), 1200, measure)
        self.assertEqual(result[0]['text'], '15:02:49')
        self.assertEqual(result[0]['x'], source['x'])

    def test_exactly_three_hour_preset_distinguishes_events_in_the_same_minute(self):
        source = [event('2026-10-29T13:39:01'), event('2026-10-29T13:39:46')]
        result = place_event_labels(source, wall('2026-10-29T12:00:00'),
                                    wall('2026-10-29T15:00:00'), 1200, measure)
        self.assertEqual([r['text'] for r in result], ['13:39:01', '13:39:46'])
        self.assertEqual([r['x'] for r in result], [e['x'] for e in source])

    def test_multiday_labels_disambiguate_same_hour_on_different_dates(self):
        source = [event('2026-10-29T12:00:00'), event('2026-10-30T12:00:00')]
        result = place_event_labels(source, wall('2026-10-29T00:00:00'),
                                    wall('2026-10-31T00:00:00'), 1200, measure)
        self.assertEqual([r['text'] for r in result], ['29/10 12:00', '30/10 12:00'])

    def test_thirty_hour_zoom_also_distinguishes_repeated_clock_hours(self):
        source = [event('2026-10-29T10:00:00'), event('2026-10-30T10:00:00')]
        result = place_event_labels(source, wall('2026-10-29T06:00:00'),
                                    wall('2026-10-30T12:00:00'), 1200, measure)
        self.assertEqual([r['text'] for r in result], ['29/10 10:00', '30/10 10:00'])

    def test_dense_labels_do_not_overlap_and_zoom_reveals_more(self):
        start = wall('2026-10-29T00:00:00')
        source = [{'x': start + 12 * 3600 + i * 60, 'labels': ('Bolo',),
                   'priority': 2} for i in range(40)]
        before = deepcopy(source)
        daily = place_event_labels(source, start, start + 86400, 800, measure)
        zoomed = place_event_labels(source, start + 11.9 * 3600,
                                    start + 12.9 * 3600, 800, measure)
        self.assertGreater(len(zoomed), len(daily))
        self.assertLess(len(daily), len(source))
        self.assertEqual(source, before)
        for result in (daily, zoomed):
            for row in (0, 1):
                labels = sorted((label for label in result if label['row'] == row),
                                key=lambda label: label['left'])
                for first, second in zip(labels, labels[1:]):
                    self.assertGreaterEqual(second['left'] - first['right'], 6 - 1e-8)

    def test_important_event_survives_collision_with_lower_priority_event(self):
        start = wall('2026-10-29T00:00:00')
        source = [event('2026-10-29T12:00:00', 2),
                  event('2026-10-29T12:00:01', 5, ('Alarma',))]
        result = place_event_labels(source, start, start + 86400, 500, measure, rows=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['labels'], ('Alarma',))
        self.assertEqual(result[0]['x'], source[1]['x'])

    def test_edge_and_outside_labels_are_not_shifted_or_drawn_beyond_axis(self):
        start = wall('2026-10-29T00:00:00')
        source = [{'x': start + offset, 'labels': ('Evento',), 'priority': 2}
                  for offset in (-1, 0, 43200, 86400, 86401)]
        guides_before = deepcopy(source)
        result = place_event_labels(source, start, start + 86400, 500, measure)
        self.assertEqual([r['x'] for r in result], [start + 43200])
        self.assertEqual(source, guides_before)
        self.assertTrue(all(0 <= r['left'] <= r['right'] <= 500 for r in result))

    def test_empty_or_invalid_view_geometry_has_no_labels(self):
        e = [event('2026-10-29T12:00:00')]
        self.assertEqual(place_event_labels([], 0, 1, 100, measure), [])
        for start, end, width in ((1, 1, 100), (2, 1, 100), (0, 1, 0), (0, 1, -1)):
            self.assertEqual(place_event_labels(e, start, end, width, measure), [])


if __name__ == '__main__':
    unittest.main()
