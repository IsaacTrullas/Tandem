"""Synthetic tooltip formatting tests; no Qt application or database required."""
from copy import deepcopy
from datetime import datetime
import unittest

from tandem.event_hover import format_messages, message, quantity, timestamp


STAMP = '2026-10-29T13:54:15'
DISPLAY_STAMP = '29/10/2026 13:54:15'
EPOCH = datetime(1970, 1, 1)


def wall(stamp):
    return (datetime.fromisoformat(stamp) - EPOCH).total_seconds()


def point(value=None, unit='', **details):
    return {'value': value, 'unit': unit, 'time': STAMP,
            'x': wall(STAMP), 'details': details}


class EventHoverTests(unittest.TestCase):
    def test_zero_decimal_comma_and_original_units(self):
        for value, unit, expected in ((0, 'U', '0 U'), (0.0, 'g', '0 g'),
                                      (.158, 'U', '0,158 U'),
                                      (.4, 'U/h', '0,4 U/h'),
                                      (110, 'mg/dL', '110 mg/dL')):
            with self.subTest(value=value, unit=unit):
                self.assertEqual(quantity(value, unit), expected)

    def test_missing_boolean_and_non_finite_values_are_not_numeric_observations(self):
        for value in (None, False, True, float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value):
                self.assertIsNone(quantity(value, 'U'))
        self.assertEqual(quantity('Sueño'), 'Sueño')

    def test_none_omits_value_while_zero_remains_in_message(self):
        title, body = message('bolus', point(0, 'U'))
        self.assertEqual(title, 'Bolo')
        self.assertEqual(body, ['0 U', DISPLAY_STAMP])
        title, body = message('event', point(label='Desconexión'))
        self.assertEqual(title, 'Desconexión')
        self.assertEqual(body, [DISPLAY_STAMP])

    def test_source_time_keeps_date_and_seconds(self):
        self.assertEqual(timestamp(STAMP), DISPLAY_STAMP)
        self.assertEqual(timestamp(wall(STAMP)), DISPLAY_STAMP)
        self.assertEqual(timestamp(None), 'Hora no disponible')
        self.assertEqual(timestamp('Hora original no interpretable'),
                         'Hora original no interpretable')

    def test_marked_bolus_name_depends_on_recorded_dose(self):
        title, body = message('bolus', point(.05, 'U'))
        self.assertEqual(title, 'Bolo de 0,05 U')
        self.assertEqual(body, ['0,05 U', DISPLAY_STAMP])
        self.assertEqual(message('bolus', point(.0501, 'U'))[0], 'Bolo')
        self.assertEqual(message('bolus', point(.05, 'U', ambiguous=True))[0], 'Bolo')

    def test_manual_glucose_and_iob_have_specific_names(self):
        self.assertEqual(message('glucose', point(94, 'mg/dL', kind='bg'))[0],
                         'Glucemia introducida')
        self.assertEqual(message('glucose', point(94, 'mg/dL', kind='cgm'))[0],
                         'Glucosa del sensor')
        self.assertEqual(message('iob', point(.158, 'U')),
                         ('Insulina activa observada', ['0,158 U', DISPLAY_STAMP]))

    def test_mode_change_event_229_decodes_its_recorded_value_including_zero(self):
        for code, label in ((0, 'Estándar'), (1, 'Sueño'),
                            (2, 'Ejercicio'), (3, 'Comida próxima')):
            with self.subTest(code=code):
                source = point(event_code=229, label='Cambio de modo',
                               properties={'currentUserMode': code})
                self.assertEqual(message('event', source),
                                 ('Cambio de modo', [label, DISPLAY_STAMP]))
        unknown = point(event_code=229, label='Cambio de modo',
                        properties={'currentUserMode': 99})
        self.assertEqual(message('event', unknown)[1], [DISPLAY_STAMP])

    def test_carbohydrate_time_is_labeled_as_bolus_request_not_meal(self):
        source = point(15, 'g', timestamp_meaning='bolus_request_not_actual_meal_time',
                       completed_at='2026-10-29T14:00:00')
        self.assertEqual(message('carbs', source),
                         ('Carbohidratos', ['15 g', DISPLAY_STAMP,
                                            'Hora de solicitud del bolo']))
        self.assertNotIn('14:00:00', '\n'.join(message('carbs', source)[1]))

    def test_mode_band_uses_observation_time_and_does_not_claim_clipped_end(self):
        source = {'observed_start': wall('2026-10-29T10:55:00'),
                  'start': wall('2026-10-29T12:24:00'),
                  'end': wall('2026-10-29T15:24:00'),
                  'label': 'Ejercicio', 'clipped_start': True,
                  'clipped_end': True, 'confirmed_end': False}
        title, body = message('mode', source)
        self.assertEqual(title, 'Modo · Ejercicio')
        self.assertEqual(body, ['Observado · 29/10/2026 10:55:00',
                                'Sin fin confirmado en este tramo'])
        self.assertNotIn('15:24:00', '\n'.join(body))
        self.assertNotIn('12:24:00', '\n'.join(body))

    def test_confirmed_mode_end_and_uncertainty_remain_explicit(self):
        source = {'observed_start': wall('2026-10-29T10:55:00'),
                  'end': wall('2026-10-29T15:48:00'),
                  'label': 'Ejercicio', 'confirmed_end': True}
        self.assertIn('Fin registrado · 29/10/2026 15:48:00', message('mode', source)[1])
        source.update(label='Modo no confirmado', confirmed_end=False, uncertain=True)
        self.assertIn('Modo no confirmado · revisar evidencia', message('mode', source)[1])

    def test_ambiguous_observation_does_not_assert_a_single_dose(self):
        source = point(.05, 'U', ambiguous=True, alternatives=['0.05', '0.1'])
        title, body = message('bolus', source)
        self.assertEqual(title, 'Bolo')
        self.assertIn('Observación ambigua', body)
        self.assertIn('Valores registrados: 0.05, 0.1', body)
        self.assertNotIn('0,05 U', body)

    def test_revision_metadata_remains_visible_and_prevents_marked_title(self):
        for details in ({'revision_count': 2}, {'revision_ids': [10, 11]}):
            with self.subTest(details=details):
                title, body = message('bolus', point(.05, 'U', **details))
                self.assertEqual(title, 'Bolo')
                self.assertIn('Varias revisiones de la observación', body)

    def test_source_conflict_lists_each_source_value_without_summing(self):
        source = point(.05, 'U', source_conflict={'api_delivered_units': .05,
                                                  'csv_delivered_units': 0})
        _, body = message('bolus', source)
        self.assertIn('Diferencia entre fuentes', body)
        self.assertIn('API · 0,05 U', body)
        self.assertIn('CSV · 0 U', body)

    def test_high_low_keep_qualifier_without_inventing_numeric_value(self):
        for qualifier, expected in (('high', 'ALTA · sin valor numérico'),
                                    ('low', 'BAJA · sin valor numérico')):
            with self.subTest(qualifier=qualifier):
                self.assertEqual(message('glucose', point(qualifier=qualifier))[1],
                                 [expected, DISPLAY_STAMP])

    def test_html_escapes_source_text_but_plain_accessibility_text_is_literal(self):
        source = point('<script> & "texto"', '<unidad>',
                       label='<Alarma & aviso>')
        html, plain = format_messages([('event', source)])
        self.assertIn('&lt;Alarma &amp; aviso&gt;', html)
        self.assertIn('&lt;script&gt; &amp; &quot;texto&quot; &lt;unidad&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('<Alarma & aviso>', plain)
        self.assertIn('<script> & "texto" <unidad>', plain)

    def test_coincident_messages_remain_separate_and_limit_has_accurate_remainder(self):
        entries = [('bolus', point(.1, 'U')), ('bolus', point(.2, 'U'))]
        html, plain = format_messages(entries)
        self.assertEqual(plain.count('Bolo'), 2)
        self.assertIn('0,1 U', plain)
        self.assertIn('0,2 U', plain)
        self.assertNotIn('0,3 U', plain)
        self.assertEqual(html.count('<b>Bolo</b>'), 2)
        more = entries + [('carbs', point(15, 'g')) for _ in range(5)]
        html, plain = format_messages(more, limit=2)
        self.assertIn('5 observaciones más · acerca el gráfico', plain)
        self.assertNotIn('15 g', plain)
        self.assertEqual(html.count('<b>'), 2)
        self.assertEqual(format_messages([]), ('', ''))

    def test_formatting_does_not_mutate_source_observations(self):
        entries = [('bolus', point(.05, 'U', revision_ids=[1],
                                   source_conflict={'api_delivered_units': .05,
                                                    'csv_delivered_units': .1})),
                   ('carbs', point(15, 'g'))]
        before = deepcopy(entries)
        format_messages(entries)
        self.assertEqual(entries, before)


if __name__ == '__main__':
    unittest.main()
