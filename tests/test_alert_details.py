"""Synthetic evidence-only descriptions of internal Tandem event labels."""
from copy import deepcopy
import json
import unittest

from tandem.alert_details import alert_details
from tandem.event_hover import format_messages, message


def details(code, properties=None, labels=None, **extra):
    return {'event_code': code,
            'properties': {} if properties is None else properties,
            'labels': {} if labels is None else labels, **extra}


def point(source):
    return {'time': '2026-10-29T06:52:13', 'value': None, 'unit': '',
            'details': source}


class AlertDetailsTests(unittest.TestCase):
    def test_no_readings_has_literal_description_and_exact_identifier(self):
        lines = alert_details(details(4, {'alertId': 48}))
        self.assertIn('Falta de lecturas del sensor (etiqueta interna)', lines)
        self.assertIn('alertId=48 · aaAlert_CGM_NO_READINGS', lines)
        self.assertIn('Alerta activada · evento 4', lines)
        self.assertEqual(len(lines), 3)

    def test_calibration_error_is_identified_as_an_internal_label(self):
        lines = alert_details(details(369, {'dalertId': 9, 'sensorType': 3}))
        self.assertIn('Error de calibración (etiqueta interna)', lines)
        self.assertIn('dalertId=9 · Alert_CGM_CALIB_ERROR', lines)
        self.assertIn('Sensor: Dexcom G7 · sensorType=3', lines)
        self.assertIn('Alerta activada · evento 369', lines)
        self.assertEqual(len(lines), 4)

    def test_alarm_uses_its_own_namespace_and_keeps_zero_identifiers(self):
        lines = alert_details(details(5, {'alarmId': 2}))
        self.assertIn('Oclusión (etiqueta interna)', lines)
        self.assertIn('alarmId=2 · Alarm_OCCLUSION', lines)
        self.assertIn('Alarma activada · evento 5', lines)
        zero = '\n'.join(alert_details(details(4, {'alertId': 0})))
        self.assertIn('alertId=0 · oaAlert_LIQ_LOW', zero)
        self.assertIn('Sin descripción disponible', zero)

    def test_acknowledgement_distinguishes_user_and_software_without_resolution(self):
        for value, expected in ((0, 'Reconocida por usuario'),
                                (1, 'Reconocida por software')):
            with self.subTest(value=value):
                lines = alert_details(details(371, {'dalertId': 9,
                                                     'sensorType': 1,
                                                     'ackSource': value}))
                self.assertIn(expected + ' · evento 371', lines)
                self.assertIn('Sensor: Dexcom G6 · sensorType=1', lines)
                self.assertEqual(len(lines), 4)
                text = '\n'.join(lines).lower()
                self.assertNotIn('resuelta', text)
                self.assertNotIn('desactivada', text)
                self.assertNotIn('activada ·', text)

    def test_normalized_acknowledgement_label_is_used_when_present(self):
        source = details(371, {'dalertId': 9},
                         {'ackSource': 'Alert Acknowledged by User'})
        self.assertIn('Reconocida por usuario · evento 371', alert_details(source))

    def test_unknown_acknowledgement_keeps_original_value(self):
        lines = alert_details(details(371, {'dalertId': 9, 'ackSource': 99}))
        self.assertIn('Reconocimiento registrado · evento 371 · origen no descrito', lines)
        self.assertIn('ackSource=99 · tipo no descrito', lines)
        self.assertNotIn('Reconocida por usuario', '\n'.join(lines))

    def test_conflicting_acknowledgement_label_does_not_choose_an_actor(self):
        source = details(371, {'dalertId': 9, 'ackSource': 0},
                         {'ackSource': 'Alert Acknowledged by Software'})
        lines = alert_details(source)
        self.assertIn('Reconocimiento registrado · evento 371 · origen no descrito', lines)
        self.assertIn('ackSource=0 · Alert Acknowledged by Software', lines)
        self.assertNotIn('Reconocida por software · evento 371', lines)
        self.assertNotIn('Reconocida por usuario · evento 371', lines)

    def test_unknown_alert_id_and_future_label_have_no_invented_description(self):
        source = details(4, {'alertId': 9876}, {'alertId': 'FUTURE_NEW_ALERT'})
        lines = alert_details(source)
        self.assertEqual(lines[0], 'Sin descripción disponible')
        self.assertIn('alertId=9876 · FUTURE_NEW_ALERT', lines)

    def test_ambiguous_acronyms_are_not_expanded(self):
        for code, field, value, original in ((5, 'alarmId', 4, 'Alarm_OBE'),
                                             (5, 'alarmId', 5, 'Alarm_P2'),
                                             (4, 'alertId', 52, 'aaAlert_TZ_IIDM')):
            with self.subTest(original=original):
                lines = alert_details(details(code, {field: value}))
                self.assertEqual(lines[0], 'Sin descripción disponible')
                self.assertIn(field + '=' + str(value) + ' · ' + original, lines)

    def test_non_integer_or_boolean_enum_is_not_treated_as_a_known_code(self):
        for value in (False, True, '48', 48.0, None):
            with self.subTest(value=value):
                lines = alert_details(details(4, {'alertId': value}))
                self.assertEqual(lines[0], 'Sin descripción disponible')
                self.assertNotIn('aaAlert_CGM_NO_READINGS', '\n'.join(lines))

    def test_disagreement_with_catalogue_remains_explicit_and_unresolved(self):
        source = details(4, {'alertId': 48}, {'alertId': 'Alert_CGM_CALIB_ERROR'})
        lines = alert_details(source)
        self.assertEqual(lines[0], 'Sin descripción disponible · etiquetas no coincidentes')
        self.assertIn('alertId=48 · Alert_CGM_CALIB_ERROR', lines)
        self.assertNotIn('Error de calibración (etiqueta interna)', lines)

    def test_sensor_unknown_or_missing_is_not_assumed_to_be_g6_or_g7(self):
        unknown = alert_details(details(369, {'dalertId': 9, 'sensorType': 77}))
        self.assertIn('Sensor: Sin descripción disponible · sensorType=77', unknown)
        missing = alert_details(details(369, {'dalertId': 9}))
        self.assertIn('Sensor no indicado', missing)
        invalid = alert_details(details(369, {'dalertId': 9, 'sensorType': 0}))
        self.assertIn('Sensor: Tipo no válido (Invalid) · sensorType=0', invalid)

    def test_conflicting_sensor_labels_remain_unresolved(self):
        source = details(369, {'dalertId': 9, 'sensorType': 1},
                         {'sensorType': 'CGM_TYPE_DEXCOM_G7'})
        self.assertIn('Sensor: etiquetas no coincidentes · sensorType=1',
                      alert_details(source))

    def test_technical_form_preserves_all_raw_parameters_and_transitions(self):
        properties = {'alertId': 48, 'param1': 123.4567, 'param2': 0,
                      'faultLocatorData': 9001, 'future': {'nested': [1, False, None]}}
        labels = {'alertId': 'aaAlert_CGM_NO_READINGS', 'future': '<texto & original>'}
        transitions = [{'state': 'unknown_future_state', 'action': 'source_action'}]
        source = details(4, properties, labels, state_transitions=transitions)
        short = '\n'.join(alert_details(source))
        self.assertNotIn('param1', short)
        self.assertNotIn('mg/dL', short)
        self.assertNotIn('U/h', short)
        lines = alert_details(source, technical=True)
        self.assertIn('Datos técnicos · evento 4 · LID_ALERT_ACTIVATED', lines)
        for key, expected in (('properties', properties), ('labels', labels),
                              ('state_transitions', transitions)):
            raw = next(line.partition('=')[2] for line in lines if line.startswith(key + '='))
            self.assertEqual(json.loads(raw), expected)
        self.assertIn('123.4567', '\n'.join(lines))

    def test_missing_and_malformed_properties_are_preserved_in_technical_form(self):
        source = {'event_code': 4, 'properties': None, 'labels': ['unexpected']}
        lines = alert_details(source, technical=True)
        self.assertIn('alertId=no indicado · tipo no descrito', lines)
        self.assertIn('properties=null', lines)
        self.assertIn('labels=["unexpected"]', lines)

    def test_control_change_uses_only_explicit_enums_and_boolean_flags(self):
        source = details(230, {'previousPcm': 1, 'currentPcm': 3,
                               'pumpSuspended': False, 'cgmAvailable': 1,
                               'calculationAvailable': 0,
                               'closedLoopPreferred': 1})
        lines = alert_details(source)
        self.assertIn('Control registrado: Lazo abierto (Open Loop) → Lazo cerrado (Closed Loop)', lines)
        self.assertIn('Cambio de control · evento 230', lines)
        self.assertIn('Indicador pumpSuspended: No', lines)
        self.assertIn('Indicador cgmAvailable: Sí', lines)
        technical = '\n'.join(alert_details(source, technical=True))
        self.assertIn('"calculationAvailable":0', technical)
        self.assertIn('"closedLoopPreferred":1', technical)
        self.assertNotIn('desconexión física', '\n'.join(lines).lower())

    def test_unexplained_control_enum_keeps_pining_and_raw_value(self):
        lines = alert_details(details(230, {'previousPcm': 2, 'currentPcm': 99,
                                           'cgmAvailable': 'false'}))
        self.assertIn('previousPcm=2 · Pining', lines)
        self.assertIn('currentPcm=99 · tipo no descrito', lines)
        self.assertIn('Indicador cgmAvailable: Sin descripción disponible · "false"', lines)

    def test_hover_adds_details_and_retains_time_and_ambiguity(self):
        source = details(4, {'alertId': 48}, label='Alerta',
                         ambiguous=True, alternatives=['fuente A', 'fuente B'])
        title, body = message('event', point(source))
        self.assertEqual(title, 'Alerta')
        self.assertIn('29/10/2026 06:52:13', body)
        self.assertIn('Observación ambigua', body)
        self.assertIn('Valores registrados: fuente A, fuente B', body)
        self.assertIn('Falta de lecturas del sensor (etiqueta interna)', body)

    def test_hover_escapes_original_names_and_values_in_rich_text(self):
        source = details(4, {'alertId': '<raw & value>'},
                         {'alertId': '<source & label>'}, label='<Alerta & original>')
        html, plain = format_messages([('event', point(source))])
        self.assertIn('&lt;Alerta &amp; original&gt;', html)
        self.assertIn('&lt;raw &amp; value&gt;', html)
        self.assertIn('&lt;source &amp; label&gt;', html)
        self.assertNotIn('<source & label>', html)
        self.assertIn('<source & label>', plain)

    def test_inputs_are_unchanged_by_short_technical_and_hover_formatting(self):
        source = details(371, {'dalertId': 9, 'sensorType': 3, 'ackSource': 0,
                               'future': {'values': [0, 1]}},
                         {'dalertId': 'Alert_CGM_CALIB_ERROR'},
                         state_transitions=[{'state': 'source', 'action': 'source'}])
        original = deepcopy(source)
        alert_details(source)
        alert_details(source, technical=True)
        format_messages([('event', point(source))])
        self.assertEqual(source, original)

    def test_other_events_and_invalid_event_codes_are_not_reinterpreted(self):
        for code in (None, True, 4.0, '4', 229, 13, 9876):
            with self.subTest(code=code):
                self.assertEqual(alert_details(details(code, {'alertId': 48})), [])
        self.assertEqual(alert_details(None), [])


if __name__ == '__main__':
    unittest.main()
