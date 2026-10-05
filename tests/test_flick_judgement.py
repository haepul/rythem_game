import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flick_judgement import (
    FlickIntent, KeyboardFlickInput, TouchFlickInput, flick_grade,
    match_flick_intents,
)


def note(when=1.0, lane=0, kind="FLICK"):
    return {"time": when, "lane": lane, "type": kind, "hit": False}


class FlickMatcherTests(unittest.TestCase):
    def test_grade_boundaries(self):
        for delta in (-0.07, 0, 0.07, 1.07 - 1):
            self.assertEqual(flick_grade(delta), "PERFECT")
        for delta in (-0.15, -0.07001, 0.07001, 0.15, 1.15 - 1):
            self.assertEqual(flick_grade(delta), "GREAT")
        for delta in (-0.15001, 0.15001, math.inf, math.nan):
            self.assertEqual(flick_grade(delta), "MISS")

    def test_early_late_window(self):
        for when, accepted in ((0.84999, False), (0.85, True), (1.15, True), (1.15001, False)):
            target = note()
            hits = match_flick_intents([target], [FlickIntent(when, {0})])
            self.assertEqual(bool(hits), accepted)
            self.assertEqual(target["hit"], accepted)

    def test_wrong_lane_and_ordinary_notes_are_never_hit(self):
        targets = [note(lane=1), note(kind="TAP"), note(kind="HOLD"), note(kind="SLIDE")]
        self.assertEqual(match_flick_intents(targets, [FlickIntent(1, {0})]), [])
        self.assertTrue(all(not target["hit"] for target in targets))

    def test_closest_note_wins_and_tie_prefers_earlier(self):
        targets = [note(0.90), note(1.02)]
        self.assertIs(match_flick_intents(targets, [FlickIntent(1, {0})])[0][0], targets[1])
        targets = [note(0.875), note(1.125)]
        self.assertIs(match_flick_intents(targets, [FlickIntent(1, {0})])[0][0], targets[0])

    def test_gesture_consumed_once_per_lane_even_if_replayed(self):
        targets = [note(1), note(1.1), note(1, lane=1)]
        intent = FlickIntent(1, {0, 1})
        self.assertEqual(len(match_flick_intents(targets, [intent])), 2)
        self.assertEqual(match_flick_intents(targets, [intent]), [])
        self.assertFalse(targets[1]["hit"])

    def test_missed_gesture_cannot_be_buffered_for_future_note(self):
        intent = FlickIntent(1, {0})
        self.assertEqual(match_flick_intents([], [intent]), [])
        self.assertEqual(match_flick_intents([note()], [intent]), [])

    def test_two_fresh_gestures_hit_two_notes_in_one_frame(self):
        targets = [note(1), note(1.12)]
        gestures = [FlickIntent(1.12, {0}), FlickIntent(1, {0})]
        hits = match_flick_intents(targets, gestures)
        self.assertEqual([target["time"] for target, _, _ in hits], [1, 1.12])


class KeyboardFlickTests(unittest.TestCase):
    def setUp(self):
        self.keys = KeyboardFlickInput()

    def test_held_lane_then_space(self):
        self.assertEqual(self.keys.lane_down(2, 0.8), [])
        intent, = self.keys.space_down(1)
        self.assertEqual((intent.time, intent.lanes), (1, {2}))

    def test_selected_lanes_flick_together(self):
        self.keys.lane_down(0, 0.8)
        self.keys.lane_down(3, 0.9)
        intent, = self.keys.space_down(1)
        self.assertEqual(intent.lanes, {0, 3})

    def test_space_before_lane_uses_space_time_only_within_40ms(self):
        self.assertEqual(self.keys.space_down(1), [])
        intent, = self.keys.lane_down(1, 1.04)
        self.assertEqual(intent.time, 1)
        self.assertEqual(self.keys.lane_down(2, 1.04001), [])

    def test_auto_repeat_and_lane_repress_do_not_retrigger(self):
        self.keys.lane_down(0, 0.9)
        self.assertEqual(len(self.keys.space_down(1)), 1)
        self.assertEqual(self.keys.space_down(1.01), [])
        self.assertEqual(self.keys.lane_down(0, 1.01), [])
        self.keys.lane_up(0, 1.02)
        self.assertEqual(self.keys.lane_down(0, 1.03), [])
        self.keys.lane_up(0, 1.2)
        self.assertEqual(self.keys.lane_down(0, 1.3), [])

    def test_space_release_required_for_next_stroke(self):
        self.keys.lane_down(0, 0.9)
        self.keys.space_down(1)
        self.keys.space_up(1.05)
        self.assertEqual(len(self.keys.space_down(1.1)), 1)

    def test_released_space_cannot_accept_late_lane(self):
        self.keys.space_down(1)
        self.keys.space_up(1.01)
        self.assertEqual(self.keys.lane_down(0, 1.02), [])

    def test_pause_focus_reset_clears_chord_and_held_lanes(self):
        self.keys.lane_down(1, 0.9)
        self.keys.space_down(1)
        self.keys.reset()
        self.assertEqual(self.keys.space_down(1.01), [])
        self.keys.space_up(1.02)
        self.assertEqual(self.keys.lane_down(1, 1.03), [])
        self.assertEqual(len(self.keys.space_down(1.04)), 1)


class TouchFlickTests(unittest.TestCase):
    def setUp(self):
        self.touch = TouchFlickInput()
        self.touch.begin("a", 100, 400, 1, 0)

    def test_interpolated_activation_time(self):
        intent, = self.touch.move("a", 100, 380, 1.04)
        self.assertAlmostEqual(intent.time, 1.024)
        self.assertEqual(intent.lanes, {0})

    def test_touchdown_or_jitter_is_not_a_flick(self):
        self.assertEqual(self.touch.move("a", 102, 395, 1.02), [])
        self.assertEqual(self.touch.move("a", 100, 402, 1.04), [])
        self.assertEqual(self.touch.move("a", 100, 394, 1.06), [])

    def test_downward_sideways_and_slow_drift_rejected(self):
        for dx, dy, elapsed in ((0, 30, 0.04), (50, -14, 0.04), (0, -12, 0.2)):
            with self.subTest(dx=dx, dy=dy):
                self.touch.begin("a", 100, 400, 1, 0)
                self.assertEqual(self.touch.move("a", 100 + dx, 400 + dy, 1 + elapsed), [])
        self.touch.begin("a", 100, 400, 1, 0)
        for step in range(1, 60):
            self.assertEqual(self.touch.move("a", 100, 400 - step * 2, 1 + step * 0.025), [])

    def test_moderate_upward_diagonal_accepted(self):
        self.assertEqual(len(self.touch.move("a", 112, 384, 1.04)), 1)

    def test_frame_rates_and_batched_samples_share_activation_time(self):
        # Samples may be delivered together in a later render frame. Only
        # their original audio timestamps determine the judgement event.
        for hz in (30, 60, 100, 240):
            self.touch.begin("a", 100, 400, 1, 0)
            gestures = []
            for step in range(1, int(hz * 0.2) + 1):
                elapsed = step / hz
                gestures.extend(self.touch.move("a", 100, 400 - 300 * elapsed, 1 + elapsed))
            self.assertEqual(len(gestures), 1)
            self.assertAlmostEqual(gestures[0].time, 1.04)

    def test_continuous_long_stroke_does_not_repeat(self):
        count = 0
        for step in range(1, 101):
            count += len(self.touch.move("a", 100, 400 - step * 5, 1 + step * 0.01))
        self.assertEqual(count, 1)

    def test_downward_reversal_rearms_second_upward_flick(self):
        self.assertEqual(len(self.touch.move("a", 100, 380, 1.04)), 1)
        self.assertEqual(self.touch.move("a", 100, 392, 1.08), [])
        self.assertEqual(len(self.touch.move("a", 100, 370, 1.12)), 1)

    def test_sampled_settling_rearms_without_fake_repeat(self):
        self.assertEqual(len(self.touch.move("a", 100, 380, 1.04)), 1)
        self.assertEqual(self.touch.move("a", 101, 379, 1.10), [])
        self.assertEqual(self.touch.move("a", 100, 380, 1.16), [])
        self.assertEqual(len(self.touch.move("a", 100, 360, 1.20)), 1)

    def test_gap_alone_cannot_rearm_a_continuing_stroke(self):
        self.touch.move("a", 100, 380, 1.04)
        self.assertEqual(self.touch.move("a", 100, 300, 1.5), [])

    def test_multitouch_tracks_each_pointer_independently(self):
        self.touch.begin("b", 700, 400, 1, 3)
        first, = self.touch.move("a", 100, 380, 1.04)
        second, = self.touch.move("b", 700, 376, 1.048)
        self.assertEqual(first.lanes, {0})
        self.assertEqual(second.lanes, {3})
        self.assertAlmostEqual(first.time, second.time)

    def test_release_new_touch_and_cancel(self):
        self.touch.move("a", 100, 380, 1.04)
        self.touch.end("a")
        self.assertEqual(self.touch.move("a", 100, 350, 1.08), [])
        self.touch.begin("a", 100, 400, 1.1, 0)
        self.assertEqual(len(self.touch.move("a", 100, 380, 1.14)), 1)
        self.touch.reset()
        self.assertEqual(self.touch.move("a", 100, 350, 1.18), [])

    def test_unknown_out_of_order_and_non_finite_samples_ignored(self):
        self.assertEqual(self.touch.move("missing", 100, 380, 1.04), [])
        self.assertEqual(self.touch.move("a", 100, 380, 0.99), [])
        self.assertEqual(self.touch.move("a", math.nan, 380, 1.04), [])
        self.assertEqual(len(self.touch.move("a", 100, 380, 1.04)), 1)

    def test_motion_on_release_can_be_delivered_before_end(self):
        gesture = self.touch.move("a", 100, 370, 1.06)
        self.touch.end("a")
        self.assertEqual(len(gesture), 1)
        self.assertAlmostEqual(gesture[0].time, 1.024)

    def test_judgement_uses_crossing_not_late_frame_arrival(self):
        self.touch.begin("a", 100, 400, 1.1, 0)
        gestures = self.touch.move("a", 100, 380, 1.1 + 1 / 15)
        self.assertEqual(len(gestures), 1)
        self.assertAlmostEqual(gestures[0].time, 1.14)
        hits = match_flick_intents([note(1)], gestures)
        self.assertEqual(len(hits), 1)
        self.assertEqual(flick_grade(hits[0][1]), "GREAT")

    def test_early_touchdown_is_allowed_when_upward_stroke_is_on_time(self):
        self.touch.begin("a", 100, 400, 0.2, 0)
        self.assertEqual(self.touch.move("a", 100, 400, 0.96), [])
        gestures = self.touch.move("a", 100, 380, 1.0)
        hits = match_flick_intents([note(1)], gestures)
        self.assertEqual(len(hits), 1)
        self.assertEqual(flick_grade(hits[0][1]), "PERFECT")


if __name__ == "__main__":
    unittest.main()
