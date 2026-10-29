"""Conservative local interpretation of Tandem's BFF event envelopes.

Code/field metadata is attributed in event_codes.json (tconnectsync, MIT).
All quantities here are observations, not additive insulin/meal records.
No timezone is inferred from the server's estimatedDateTime field.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
import math
from pathlib import Path

VERSION = '1.1'
CATALOGUE = json.loads(Path(__file__).with_name('event_codes.json').read_text(encoding='utf-8'))
EVENT_CODES = CATALOGUE['events']

KINDS = {
    3:'basal_rate', 4:'alert', 5:'alarm', 6:'malfunction', 8:'alarm_acknowledged',
    11:'suspend', 12:'resume', 13:'clock_change', 14:'clock_change',
    16:'bg', 20:'bolus_completed', 21:'bolus_extended_completed',
    26:'alert_cleared', 27:'alert_acknowledged', 28:'alarm_cleared', 33:'cartridge_fill',
    34:'charging_started', 35:'charging_stopped',
    36:'usb_connected', 37:'usb_disconnected', 48:'carb_entry',
    53:'storage_mode', 55:'bolus_started', 57:'settings', 59:'bolus_extended_started',
    60:'log_corruption', 61:'cannula_fill', 63:'tubing_fill',
    64:'bolus_request', 65:'bolus_request_options', 66:'bolus_request_amounts',
    69:'settings', 81:'basal_daily_summary', 90:'new_day',
    99:'device_initialization', 140:'basal_algorithm_status',
    171:'cgm_alert', 172:'cgm_alert_cleared', 191:'device_version',
    203:'device_update_status', 212:'cgm_session_start', 213:'cgm_session_join',
    214:'cgm_session_stop', 219:'cgm_scanner_state', 229:'mode_change', 230:'control_mode_change',
    256:'cgm', 279:'basal_rate', 280:'bolus_delivery', 307:'device_version',
    313:'daily_status', 369:'cgm_alert', 370:'cgm_alert_cleared',
    371:'cgm_alert_acknowledged', 372:'cgm', 394:'cgm_session_join',
    399:'cgm', 404:'cgm_session_start', 405:'cgm_session_stop',
    406:'cgm_session_join', 434:'notification_annunciation', 447:'cgm_session_stop', 460:'cgm_alert',
    461:'cgm_alert_cleared', 477:'cgm_session_join', 480:'cgm',
    486:'cgm_session_stop', 558:'sync_dose_started', 559:'sync_dose_completed',
    562:'daily_status', 563:'daily_status', 564:'temporary_adjustment_end',
    565:'temporary_adjustment_start', 566:'schedule_settings',
}
MODES = {0:'normal', 1:'sleep', 2:'exercise', 3:'eating_soon'}


def _number(value):
    if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
        return value
    return None


def _integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _local_time(value):
    if not isinstance(value, str) or 'T' not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    # Preserve the exact spelling, precision and clock. An offset is unexpected
    # in this particular field; retain it in the raw envelope for review.
    return value if parsed.tzinfo is None else None


def decode(event: dict) -> dict:
    """Return source-derived meaning while keeping all properties untouched.

    ``values.measures`` holds explicit normalized units; ``value`` is a
    single selected scalar, never a sum. ``state_transitions`` carries both
    boundaries when one mode replaces another. Missing/future values remain
    unresolved. The caller must store the complete source envelope as well.
    """
    if not isinstance(event, dict):
        return {'kind':'unknown', 'local_timestamp':None, 'values':{},
                'unit':None, 'value':None, 'decode_status':'malformed'}
    code = _integer(event.get('eventCode'))
    spec = EVENT_CODES.get(str(code))
    source_props = event.get('eventProperties')
    props = source_props if isinstance(source_props, dict) else {}
    timestamp = _local_time(event.get('pumpDateTime'))
    result = {'kind':KINDS.get(code, 'unknown'), 'local_timestamp':timestamp,
              'values':{'properties':deepcopy(source_props), 'decoder_version':VERSION},
              'unit':None, 'value':None, 'decode_status':'decoded' if spec else 'unknown'}
    details = result['values']
    issues = []
    if timestamp is None: issues.append('missing_or_invalid_local_timestamp')
    if not isinstance(source_props, dict): issues.append('missing_or_invalid_properties')
    if not spec:
        details['issues'] = issues
        return result
    details['event_name'] = spec['name']
    if spec.get('classification_status'):
        details['classification_status'] = spec['classification_status']
        details['classification_source'] = spec['source']
        result['decode_status'] = 'classified'
        if code == 219:
            details['quantity_meaning'] = 'scanner_state_not_physical_disconnect_or_control_iq_availability'
        elif code == 434:
            details['quantity_meaning'] = 'notification_annunciation_not_a_separate_alarm_activation'
    details['labels'] = {}
    details['source_field_units'] = {key:field['source_unit'] for key,field in spec['fields'].items()
                                     if 'source_unit' in field and key in props}
    details['unrecognized_fields'] = sorted(set(props)-set(spec['fields']))
    for key, field in spec['fields'].items():
        raw = props.get(key)
        if 'enum' in field and _integer(raw) is not None:
            label = field['enum'].get(str(raw))
            if label is not None: details['labels'][key] = label
        if 'bitmask' in field:
            # BFF sends bit positions in an array. Do not reinterpret arbitrary
            # numeric values as arrays or vice versa.
            if isinstance(raw, list) and all(_integer(x) is not None for x in raw):
                details['labels'][key] = [field['bitmask'].get(str(x), 'unknown_bit_'+str(x)) for x in raw]
    measures = details['measures'] = {}

    def measure(field, unit, factor=1, primary=False, name=None):
        value = _number(props.get(field))
        if value is None:
            if primary: issues.append('missing_or_invalid_'+field)
            return
        value *= factor
        measures[name or field] = {'value':value, 'unit':unit, 'source_field':field, 'factor':factor}
        if primary: result.update(value=value, unit=unit)

    if code in (256,372,399,480):
        sample_seconds = _integer(props.get('egvTimeStamp'))
        if sample_seconds is not None and 0 <= sample_seconds <= 0xFFFFFFFF:
            details['measurement_local_timestamp'] = (datetime(2008,1,1) + timedelta(seconds=sample_seconds)).isoformat()
            details['timestamp_source'] = 'egvTimeStamp_seconds_since_2008_naive'
        else:
            details['measurement_local_timestamp'] = None
            details['timestamp_source'] = 'unresolved'
            issues.append('missing_or_invalid_egvTimeStamp')
        status = _integer(props.get('glucoseValueStatus'))
        details['glucose_qualifier'] = {0:'numeric',1:'high',2:'low'}.get(status, 'unresolved')
        if status == 0: measure('currentGlucoseDisplayValue', 'mg/dL', primary=True)
        elif status not in (1,2): issues.append('unresolved_glucose_status')
        # A high/low marker uses a source zero; that is not a zero mg/dL reading.
    elif code == 16:
        measure('bg','mg/dL',primary=True)
    elif code == 3:
        measure('commandedBasalRate','U/h',primary=True)
        measure('baseBasalRate','U/h')
        measure('maxBasalRate','U/h')
    elif code == 279:
        for field in ('commandedRate','profileBasalRate','algorithmRate','tempRate'):
            measure(field,'U/h',0.001,field=='commandedRate')
        details['quantity_meaning'] = 'commanded_rate_not_delivered_dose'
    elif code in (20,21):
        measure('insulinDelivered','U',primary=True)
        measure('insulinRequested','U')
        details['quantity_meaning'] = 'component_delivery_not_additive_across_event_types'
    elif code == 280:
        status = _integer(props.get('bolusDeliveryStatus'))
        result['kind'] = {0:'bolus_completed',1:'bolus_started'}.get(status,'bolus_delivery')
        for field in ('requestedNow','requestedLater','correction','deliveredTotal'):
            measure(field,'U',0.001,status==0 and field=='deliveredTotal')
        details['quantity_meaning'] = 'cumulative_bolus_delivery_not_additive'
        if status not in (0,1): issues.append('unresolved_bolus_delivery_status')
    elif code in (55,59):
        measure('bolusSize' if code==55 else 'bolexSize','U')
        details['quantity_meaning'] = 'requested_activation_not_delivery'
    elif code == 64:
        measure('carbAmount','g')
        measure('bg','mg/dL')
        measure('carbRatio','g/U',0.001)
        details['quantity_meaning'] = 'bolus_request_inputs_not_a_separate_meal'
    elif code == 66:
        for field in ('foodBolusSize','correctionBolusSize','totalBolusSize'): measure(field,'U')
    elif code == 81:
        measure('dailyTotalBasal','U',primary=True)
        details['quantity_meaning'] = 'daily_summary_not_additive_with_deliveries'
    elif code in (33,61,63):
        measure('insulinVolume' if code==33 else 'primeSize','U',primary=True)
        details['quantity_meaning'] = 'fill_or_prime_not_therapy_dose'
    elif code in (558,559):
        measure('syncDoseSizeRequested' if code==558 else 'syncDoseSizeDelivered','U',primary=code==559)
        measure('currentBasalRate','U/h',0.001)
        details['quantity_meaning'] = 'sync_dose_not_additive_with_other_delivery_events'
    elif code == 229:
        before = MODES.get(_integer(props.get('previousUserMode')))
        after = MODES.get(_integer(props.get('currentUserMode')))
        details.update(mode_before=before, mode_after=after, state_transitions=[])
        if before is None or after is None:
            issues.append('unresolved_mode')
        elif before != after:
            if before != 'normal': details['state_transitions'].append({'state':before,'action':'end'})
            if after != 'normal': details['state_transitions'].append({'state':after,'action':'start'})
        # requestedAction alone does not establish the resulting state.
    elif code in (11,12):
        details['state_transitions'] = [{'state':'suspended','action':'start' if code==11 else 'end'}]
    elif code in (13,14):
        details['quantity_meaning'] = 'clock_change_raw_before_after_retained'
    if issues:
        details['issues'] = issues
        result['decode_status'] = 'partial'
    return result
