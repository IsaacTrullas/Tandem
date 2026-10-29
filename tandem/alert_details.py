"""Literal presentation of locally catalogued event labels, without advice.

The enum names come from event_codes.json (tconnectsync, MIT). Spanish phrases
below translate only explicit words in those internal labels; they do not
identify a cause, a physical disconnection, a remedy, or a resolved condition.
Unspecified parameter units are never inferred.
"""
from __future__ import annotations

import json

from .event_decode import EVENT_CODES


ALERT_FIELDS = {4: 'alertId', 5: 'alarmId', 369: 'dalertId', 371: 'dalertId'}
SUPPORTED_CODES = frozenset((*ALERT_FIELDS, 230))
DESCRIPTIONS = {
    'aaAlert_CGM_NO_READINGS': 'Falta de lecturas del sensor',
    'Alert_CGM_CALIB_ERROR': 'Error de calibración',
    'Alert_CGM_CALIBRATION_REQUEST': 'Solicitud de calibración',
    'Alert_CGM_CALIB_REQUIRED': 'Calibración requerida',
    'Alert_CGM_SENSOR_FAILED': 'Fallo del sensor',
    'Alert_CGM_SENSOR_EXPIRING': 'Sensor próximo a caducar',
    'Alert_CGM_SENSOR_EXPIRED': 'Sensor caducado',
    'Alert_CGM_SENSOR_EXPIRING_SOON': 'Sensor próximo a caducar',
    'Alert_CGM_TRANSMITTER_ERROR': 'Error del transmisor',
    'Alert_CGM_CONNECTION_ERROR': 'Error de conexión del sensor',
    'Alert_CGM_CHECK_SENSOR': 'Etiqueta de comprobación del sensor',
    'aaAlert_SENSOR': 'Alerta del sensor',
    'oaAlert_CONTROLLER_CONNECTION_LOST': 'Conexión con el controlador perdida',
    'Alarm_OCCLUSION': 'Oclusión',
    'Alarm_STUCK_BUTTON': 'Botón atascado',
    'aaAlert_STUCK_BUTTON': 'Botón atascado',
    'Alarm_NO_CARTRIDGE_DETECTED': 'Cartucho no detectado',
    'Alarm_GENERIC': 'Alarma genérica',
}
SENSORS = {'CGM_TYPE_DEXCOM_G6': 'Dexcom G6',
           'CGM_TYPE_DEXCOM_G7': 'Dexcom G7',
           'Invalid': 'Tipo no válido (Invalid)'}
ACKNOWLEDGEMENTS = {'Alert Acknowledged by User': 'Reconocida por usuario',
                    'Alert Acknowledged by Software': 'Reconocida por software'}
CONTROL_MODES = {'No Control': 'Sin control (No Control)',
                 'Open Loop': 'Lazo abierto (Open Loop)',
                 'Closed Loop': 'Lazo cerrado (Closed Loop)'}


def _raw(value):
    """Keep technical values and spelling separate from normalized quantities."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _enum(code, field, properties, labels):
    raw = properties.get(field)
    field_spec = EVENT_CODES.get(str(code), {}).get('fields', {}).get(field, {})
    catalogued = (field_spec.get('enum', {}).get(str(raw))
                  if isinstance(raw, int) and not isinstance(raw, bool) else None)
    provided = labels.get(field)
    provided = provided if isinstance(provided, str) and provided else None
    conflict = provided is not None and catalogued is not None and provided != catalogued
    return raw, provided or catalogued, conflict


def _identifier(field, properties, label):
    value = _raw(properties[field]) if field in properties else 'no indicado'
    return field + '=' + value + (' · ' + label if label else ' · tipo no descrito')


def _sensor(code, properties, labels):
    if 'sensorType' not in properties and 'sensorType' not in labels:
        return 'Sensor no indicado'
    raw, label, conflict = _enum(code, 'sensorType', properties, labels)
    if conflict:
        return 'Sensor: etiquetas no coincidentes · sensorType=' + _raw(raw)
    name = SENSORS.get(label, 'Sin descripción disponible')
    original = (' · ' + label) if label and label not in SENSORS else ''
    original_value = _raw(raw) if 'sensorType' in properties else 'no indicado'
    return 'Sensor: ' + name + ' · sensorType=' + original_value + original


def _alert_lines(code, properties, labels):
    field = ALERT_FIELDS[code]
    _, label, conflict = _enum(code, field, properties, labels)
    description = DESCRIPTIONS.get(label)
    if conflict:
        heading = 'Sin descripción disponible · etiquetas no coincidentes'
    elif description:
        heading = description + ' (etiqueta interna)'
    else:
        heading = 'Sin descripción disponible'
    lines = [heading, _identifier(field, properties, label)]
    if code == 371:
        raw_ack, ack_label, ack_conflict = _enum(code, 'ackSource', properties, labels)
        acknowledgement = (ACKNOWLEDGEMENTS.get(ack_label)
                           if not ack_conflict else None)
        if acknowledgement:
            lines.append(acknowledgement + ' · evento 371')
        else:
            lines.append('Reconocimiento registrado · evento 371 · origen no descrito')
            if 'ackSource' in properties or ack_label:
                lines.append(_identifier('ackSource', properties, ack_label))
    else:
        lines.append(('Alarma activada' if code == 5 else 'Alerta activada')
                     + ' · evento ' + str(code))
    if code in (369, 371):
        lines.append(_sensor(code, properties, labels))
    return lines


def _control_lines(properties, labels):
    modes = []
    for field in ('previousPcm', 'currentPcm'):
        _, label, conflict = _enum(230, field, properties, labels)
        name = CONTROL_MODES.get(label) if not conflict else None
        modes.append(name or 'Sin descripción disponible')
    lines = ['Control registrado: ' + modes[0] + ' → ' + modes[1],
             'Cambio de control · evento 230']
    # These are source flags at the event time, not claims of physical
    # connection/disconnection or of the cause of a control transition.
    for field in ('pumpSuspended', 'cgmAvailable'):
        if field not in properties:
            continue
        value = properties[field]
        if isinstance(value, bool):
            text = 'Sí' if value else 'No'
        elif isinstance(value, int) and value in (0, 1):
            text = 'Sí' if value else 'No'
        else:
            text = 'Sin descripción disponible · ' + _raw(value)
        lines.append('Indicador ' + field + ': ' + text)
    # Keep unresolved enum spellings visible in the short message as well.
    for field in ('previousPcm', 'currentPcm'):
        _, label, conflict = _enum(230, field, properties, labels)
        if label not in CONTROL_MODES or conflict:
            lines.append(_identifier(field, properties, label))
    return lines


def alert_details(details, technical=False):
    """Return plain lines for supported normalized event ``details``.

    The short form identifies the internal alert type, recorded phase, sensor
    and acknowledgement. ``technical=True`` appends the exact catalogue event
    name and *complete* original properties/labels/transitions as compact JSON.
    Neither form mutates inputs or infers units, causes or a resolved alert.
    All lines must be HTML-escaped by the display layer when used as rich text.
    """
    if not isinstance(details, dict):
        return []
    code = details.get('event_code')
    if isinstance(code, bool) or not isinstance(code, int) or code not in SUPPORTED_CODES:
        return []
    raw_properties = details.get('properties', {})
    raw_labels = details.get('labels', {})
    properties = raw_properties if isinstance(raw_properties, dict) else {}
    labels = raw_labels if isinstance(raw_labels, dict) else {}
    lines = (_control_lines(properties, labels) if code == 230
             else _alert_lines(code, properties, labels))
    if technical:
        lines.append('Datos técnicos · evento ' + str(code) + ' · '
                     + EVENT_CODES[str(code)]['name'])
        lines.append('properties=' + _raw(raw_properties))
        lines.append('labels=' + _raw(raw_labels))
        if 'state_transitions' in details:
            lines.append('state_transitions=' + _raw(details['state_transitions']))
    return lines
