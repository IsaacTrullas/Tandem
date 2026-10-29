import copy
import unittest
from tandem.mode_segments import derive_mode_segments


def bundle(start=0,end=86400,observed_end=80000,modes=None,clocks=None,ambiguous=None):
    return {'view_start':start,'view_width':end-start,'cache_start':start-300,'cache_end':end+300,
      'data':{'glucose':[{'x':max(start,0)},{'x':observed_end}], 'events':[]},
      'context':{'timelines':{'mode':modes or []},'clock_changes':clocks or [],
                 'ambiguous_clock_ranges':ambiguous or [],'observed_iob':[]}}


def mode(x,value,identity=1):return {'x':x,'value':value,'source':'API · evento229','id':identity}


class ModeSegmentTests(unittest.TestCase):
    def test_sleep_predecessor_and_exercise_visible_with_explicit_normal_gaps(self):
        b=bundle(modes=[mode(-100,'sleep'),mode(21600,'normal',2),mode(36000,'exercise',3),mode(39600,'normal',4)])
        segments=derive_mode_segments(b)
        self.assertEqual([(s['mode'],s['start'],s['end']) for s in segments],
          [('sleep',0,21600),('normal',21600,36000),('exercise',36000,39600),('normal',39600,80000)])
        self.assertTrue(segments[0]['clipped_start']);self.assertTrue(segments[0]['confirmed_end'])
        self.assertTrue(segments[-1]['clipped_end'])

    def test_latest_mode_never_extends_to_unobserved_rest_of_day(self):
        segments=derive_mode_segments(bundle(observed_end=28800,modes=[mode(0,'sleep'),mode(27000,'exercise',2)]))
        self.assertEqual(segments[-1]['end'],28800);self.assertLess(segments[-1]['end'],86400)
        self.assertFalse(segments[-1]['confirmed_end'])

    def test_clock_before_window_invalidates_older_mode(self):
        segments=derive_mode_segments(bundle(start=100,end=1000,observed_end=900,modes=[mode(0,'sleep')],clocks=[{'x':50}]))
        self.assertEqual(len(segments),1);self.assertEqual(segments[0]['mode'],'unknown')
        self.assertEqual(segments[0]['reason'],'clock_barrier')

    def test_clock_break_requires_new_observation_before_mode_returns(self):
        b=bundle(end=1000,observed_end=900,modes=[mode(0,'sleep'),mode(500,'exercise',2)],clocks=[{'x':300}])
        self.assertEqual([(s['mode'],s['start'],s['end']) for s in derive_mode_segments(b)],
          [('sleep',0,300),('unknown',300,500),('exercise',500,900)])

    def test_repeated_clock_interval_is_ambiguous_even_with_mode_events_inside(self):
        b=bundle(end=1000,observed_end=900,modes=[mode(0,'sleep'),mode(400,'exercise',2)],ambiguous=[(300,600)])
        segments=derive_mode_segments(b)
        ambiguous=[s for s in segments if s['uncertain']]
        self.assertTrue(ambiguous);self.assertTrue(all(s['mode']=='unknown' for s in ambiguous))
        self.assertTrue(all(300<=s['start']<s['end']<=600 for s in ambiguous))

    def test_conflicting_modes_at_one_wall_time_are_not_silently_chosen(self):
        b=bundle(end=1000,observed_end=900,modes=[mode(0,'sleep'),mode(300,'sleep',2),mode(300,'exercise',3),mode(600,'normal',4)])
        segment=next(s for s in derive_mode_segments(b) if s['start']==300)
        self.assertEqual(segment['mode'],'unknown');self.assertEqual(segment['reason'],'ambiguous_same_wall_time')

    def test_no_mode_or_no_available_data_does_not_invent_bands(self):
        self.assertEqual(derive_mode_segments(bundle()),[])
        b=bundle(modes=[mode(0,'sleep')]);b['data']={};self.assertEqual(derive_mode_segments(b),[])

    def test_inputs_unchanged_and_all_segments_strictly_bounded(self):
        b=bundle(start=100,end=200,observed_end=190,modes=[mode(0,'sleep'),mode(150,'normal',2)])
        original=copy.deepcopy(b);segments=derive_mode_segments(b)
        self.assertEqual(b,original)
        self.assertTrue(all(100<=s['start']<s['end']<=190 for s in segments))


if __name__=='__main__':unittest.main()
