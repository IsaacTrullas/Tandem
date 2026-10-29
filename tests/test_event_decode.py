import copy
from datetime import datetime
import math
import unittest

from tandem.event_decode import decode, EVENT_CODES, KINDS


def event(code, **properties):
    return {'eventCode':code, 'sequenceGroup':0, 'sequenceNumber':23,
            'deviceAssignmentId':'synthetic-pump',
            'pumpDateTime':'2026-10-25T02:30:00',
            'estimatedDateTime':'2026-10-25T02:30:00Z',
            'eventProperties':properties}


class EventDecodeTests(unittest.TestCase):
    def test_all_catalogued_codes_have_a_kind(self):
        self.assertEqual({int(x) for x in EVENT_CODES},set(KINDS))

    def test_unknown_properties_are_preserved_without_mutation(self):
        raw=event(9876, future={'nested':[1,2]})
        original=copy.deepcopy(raw)
        got=decode(raw)
        self.assertEqual(got['decode_status'],'unknown')
        self.assertEqual(got['kind'],'unknown')
        self.assertEqual(got['values']['properties'],raw['eventProperties'])
        got['values']['properties']['future']['nested'].append(3)
        self.assertEqual(raw,original)

    def test_clock_is_not_converted_or_replaced_by_estimated_time(self):
        raw=event(13,timePrior=3600000,timeAfter=0)
        got=decode(raw)
        self.assertEqual(got['local_timestamp'],'2026-10-25T02:30:00')
        raw.pop('pumpDateTime')
        self.assertIsNone(decode(raw)['local_timestamp'])
        self.assertEqual(decode(raw)['decode_status'],'partial')
        raw['pumpDateTime']='2026-10-25T02:30:00Z'
        self.assertIsNone(decode(raw)['local_timestamp'])

    def test_cgm_zero_status_and_high_marker_are_distinct(self):
        exact=decode(event(399,glucoseValueStatus=0,currentGlucoseDisplayValue=156))
        high=decode(event(399,glucoseValueStatus=1,currentGlucoseDisplayValue=0))
        self.assertEqual((exact['value'],exact['unit']),(156,'mg/dL'))
        self.assertIsNone(high['value'])
        self.assertEqual(high['values']['glucose_qualifier'],'high')
        self.assertIsNone(decode(event(399,currentGlucoseDisplayValue=156))['value'])

    def test_sample_timestamp_preserves_backfill_and_log_time(self):
        # Synthetic reading is logged five minutes after its sensor time.
        sample='2026-10-25T02:25:00'
        seconds=int((datetime.fromisoformat(sample)-datetime(2008,1,1)).total_seconds())
        raw=event(399,glucoseValueStatus=0,currentGlucoseDisplayValue=156,egvTimeStamp=seconds)
        got=decode(raw)
        self.assertEqual(got['local_timestamp'],'2026-10-25T02:30:00')
        self.assertEqual(got['values']['measurement_local_timestamp'],sample)
        self.assertEqual(got['values']['timestamp_source'],'egvTimeStamp_seconds_since_2008_naive')
        self.assertNotIn('Z',got['values']['measurement_local_timestamp'])
        for invalid in (-1,4294967296,True,'593000000',593000000.5,None):
            raw['eventProperties']['egvTimeStamp']=invalid
            got=decode(raw)
            self.assertIsNone(got['values']['measurement_local_timestamp'])
            self.assertEqual(got['decode_status'],'partial')

    def test_milliunits_rate_is_not_an_insulin_dose(self):
        got=decode(event(279,commandedRate=600,profileBasalRate=540,algorithmRate=700,tempRate=0))
        self.assertAlmostEqual(got['value'],.6)
        self.assertEqual(got['unit'],'U/h')
        self.assertEqual(got['values']['measures']['profileBasalRate']['value'],.54)
        self.assertEqual(got['values']['properties']['commandedRate'],600)

    def test_bolus_start_and_completion_never_summed(self):
        start=decode(event(280,bolusId=7,bolusDeliveryStatus=1,requestedNow=3500,deliveredTotal=0))
        end=decode(event(280,bolusId=7,bolusDeliveryStatus=0,requestedNow=3500,deliveredTotal=3250))
        self.assertEqual(start['kind'],'bolus_started')
        self.assertIsNone(start['value'])
        self.assertEqual(end['kind'],'bolus_completed')
        self.assertEqual((end['value'],end['unit']),(3.25,'U'))

    def test_component_completion_remains_component(self):
        got=decode(event(21,insulinDelivered=1.5,insulinRequested=2,completionStatus=0))
        self.assertEqual(got['value'],1.5)
        self.assertEqual(got['kind'],'bolus_extended_completed')
        self.assertEqual(got['values']['labels']['completionStatus'],'User Aborted')

    def test_mode_switch_has_both_boundaries_without_durations(self):
        got=decode(event(229,previousUserMode=2,currentUserMode=1,requestedAction=4))
        self.assertEqual(got['values']['state_transitions'],[
            {'state':'exercise','action':'end'}, {'state':'sleep','action':'start'}])
        unchanged=decode(event(229,previousUserMode=0,currentUserMode=0,requestedAction=1))
        self.assertEqual(unchanged['values']['state_transitions'],[])
        unresolved=decode(event(229,previousUserMode=2,currentUserMode=99,requestedAction=4))
        self.assertEqual(unresolved['values']['state_transitions'],[])
        self.assertEqual(unresolved['decode_status'],'partial')

    def test_carb_request_is_not_a_meal_event(self):
        got=decode(event(64,carbAmount=42,carbRatio=12000,bolusId=9))
        self.assertEqual(got['kind'],'bolus_request')
        self.assertIsNone(got['value'])
        self.assertEqual(got['values']['measures']['carbAmount']['value'],42)
        self.assertEqual(got['values']['measures']['carbRatio']['value'],12)

    def test_boolean_nan_and_text_are_not_doses(self):
        for bad in (True,math.nan,math.inf,'3.5',None):
            self.assertIsNone(decode(event(20,insulinDelivered=bad))['value'])

    def test_suspend_is_not_physical_disconnect(self):
        got=decode(event(11,suspendReason=0))
        self.assertEqual(got['kind'],'suspend')
        self.assertEqual(got['values']['state_transitions'],[{'state':'suspended','action':'start'}])

    def test_malformed_is_retained_as_unresolved(self):
        self.assertEqual(decode([])['decode_status'],'malformed')
        raw=event(20);raw['eventProperties']=None
        self.assertIsNone(decode(raw)['values']['properties'])
        self.assertEqual(decode(raw)['decode_status'],'partial')

    def test_additional_classifications_do_not_invent_doses_or_states(self):
        kinds={8:'alarm_acknowledged',27:'alert_acknowledged',34:'charging_started',
               35:'charging_stopped',219:'cgm_scanner_state',434:'notification_annunciation'}
        for code,kind in kinds.items():
            got=decode(event(code,futureField=42))
            self.assertEqual(got['kind'],kind)
            self.assertEqual(got['decode_status'],'classified')
            self.assertIsNone(got['value'])
            self.assertNotIn('state_transitions',got['values'])
            self.assertEqual(got['values']['properties'],{'futureField':42})
            if code in (34,35,219,434):
                self.assertEqual(got['values']['classification_status'],'provisional_reference')
        for unverified in (9,22,23,52):
            got=decode(event(unverified,screenLockEnabled=1))
            self.assertEqual(got['kind'],'unknown')
            self.assertEqual(got['decode_status'],'unknown')


if __name__=='__main__':unittest.main()
