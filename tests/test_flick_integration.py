"""Exercise the Pygame/DOM adapter and actual gameplay loop without devices."""
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as game
from flick_judgement import KeyboardFlickInput, TouchFlickInput, match_flick_intents
from tap_judgement import match_tap_presses


def note(when=1.0, lane=0, kind="FLICK", end=None):
    result = {"type": kind, "time": when, "lane": lane, "hit": False, "active": False}
    if end is not None:
        result["end_time"] = end
    return result


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.stack.enter_context(patch.multiple(game, audio_element=None,
            flick_keyboard=KeyboardFlickInput(), flick_touch=TouchFlickInput(),
            key_lanes_down=set(), active_touches={}))
        self.addCleanup(self.stack.close)

    def test_native_age_and_dom_audio_times_are_equivalent(self):
        native = [(100.94, None, "lane", "down", 2),
                  (101.0, None, "space", "down", None)]
        intents = game.collect_flick_intents(native, 1.1, 101.1)
        self.assertEqual(len(intents), 1)
        self.assertAlmostEqual(intents[0].time, 1.0)
        game.clear_game_inputs()
        dom = [(500, 0.94, "lane", "down", 2),
               (500, 1.0, "space", "down", None)]
        direct = game.collect_flick_intents(dom, 1.1, 501)
        self.assertEqual(len(direct), 1)
        self.assertEqual(direct[0].lanes, intents[0].lanes)
        self.assertAlmostEqual(direct[0].time, intents[0].time)

    def test_delivered_event_order_is_sorted_on_song_clock(self):
        events = [(101, 1.03, "lane", "down", 3),
                  (101, 1.0, "space", "down", None)]
        intent, = game.collect_flick_intents(events, 1.04, 101.04)
        self.assertEqual((intent.time, intent.lanes), (1, {3}))

    def test_pointer_native_and_dom_crossing_times_match(self):
        raw = [(100.96, None, "pointer", "down", ("p", 130, 400)),
               (101.0, None, "pointer", "up", ("p", 130, 380))]
        native, = game.collect_flick_intents(raw, 1.1, 101.1)
        self.assertAlmostEqual(native.time, 0.984)
        self.assertFalse(game.flick_touch.pointers)
        direct, = game.collect_flick_intents([
            (500, 0.96, "pointer", "down", ("p", 130, 400)),
            (500, 1.0, "pointer", "up", ("p", 130, 380))], 1.1, 501)
        self.assertAlmostEqual(direct.time, native.time)
        self.assertEqual(direct.lanes, native.lanes)

    def test_pointer_cancel_cannot_award_final_motion(self):
        self.assertEqual(game.collect_flick_intents([
            (100, 1, "pointer", "down", ("p", 130, 400)),
            (100, 1.04, "pointer", "cancel", ("p", 130, 380))], 1.1, 100), [])
        self.assertFalse(game.flick_touch.pointers)

    def test_touching_hud_or_outside_track_does_not_arm_flick(self):
        for x, y in ((130, 20), (1, 400), (799, 400)):
            events = [(100, 1, "pointer", "down", ("p", x, y)),
                      (100, 1.04, "pointer", "up", ("p", x, y - 20))]
            self.assertEqual(game.collect_flick_intents(events, 1.1, 100), [])

    def test_clear_pause_resume_and_stop_reset_every_input_source(self):
        audio = Mock()
        with patch.object(game, "audio_element", audio):
            for clear in (game.clear_game_inputs, game.pause_music, game.resume_music, game.stop_music):
                game.key_lanes_down.add(1)
                game.active_touches["p"] = 130
                game.flick_keyboard.lane_down(1, 0.9)
                game.flick_keyboard.space_down(1)
                game.flick_touch.begin("p", 130, 400, 1, 0)
                clear()
                self.assertFalse(game.key_lanes_down)
                self.assertFalse(game.active_touches)
                self.assertFalse(game.flick_keyboard.held_lanes)
                self.assertFalse(game.flick_keyboard.space_held)
                self.assertFalse(game.flick_touch.pointers)
            self.assertEqual(audio.clearInput.call_count, 4)

    def test_load_flick_preserves_beat_and_has_no_sustain_fields(self):
        entry = {"bpm": 240, "offset": 0.016, "notes": [
            {"type": "FLICK", "beat": 16.375, "lane": 2},
            {"type": "TAP", "beat": 17, "lane": 0}]}
        loaded, bpm, offset = game.load_authored_chart("unused", 10, 10, 120, 0, entry)
        self.assertEqual((bpm, offset), (240, 0.016))
        self.assertEqual(loaded[0]["type"], "FLICK")
        self.assertAlmostEqual(loaded[0]["time"], 0.016 + 16.375 / 4)
        self.assertNotIn("end_time", loaded[0])
        self.assertEqual(game.prepare_sustain_combo_ticks(loaded, bpm), 2)
        self.assertNotIn("sustain_judge", loaded[0])
        self.assertNotIn("tick_times", loaded[0])

    def test_flick_loader_respects_song_cutoff(self):
        loaded, _, _ = game.load_authored_chart("unused", 10, 2, 120, 0,
            {"bpm": 120, "notes": [{"type": "FLICK", "beat": 4, "lane": 0},
                                      {"type": "FLICK", "beat": 3.5, "lane": 1}]})
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["lane"], 1)

    def test_plain_lane_press_neither_hits_flick_nor_steals_adjacent_tap(self):
        notes = [note(1), note(1.1, kind="TAP")]
        press = [1, 0, False]
        self.assertEqual(match_tap_presses(notes, [press], game.GREAT_TIME), [])
        self.assertTrue(all(not item["hit"] for item in notes))
        self.assertFalse(press[2])

    def test_closer_tap_still_hits_with_flick_in_window(self):
        notes = [note(1), note(1.1, kind="TAP")]
        hits = match_tap_presses(notes, [[1.1, 0, False]], game.GREAT_TIME)
        self.assertEqual(len(hits), 1)
        self.assertIs(hits[0][0], notes[1])
        self.assertFalse(notes[0]["hit"])

    def test_flick_gesture_coexists_with_held_note_on_another_lane(self):
        flick = note(1)
        hold = note(0.8, lane=1, kind="HOLD", end=2)
        notes = [hold, flick]
        game.prepare_sustain_combo_ticks(notes, 120)
        changes = [(0.8, frozenset({1}), {1})]
        head = hold["sustain_judge"].update(0.9, frozenset(), changes)
        self.assertTrue(head)
        self.assertTrue(hold["sustain_judge"].connected)
        intents = game.collect_flick_intents([
            (100, 0.8, "lane", "down", 1),
            (100, 0.99, "lane", "down", 0),
            (100, 1.0, "space", "down", None)], 1.0, 100)
        self.assertEqual(len(match_flick_intents(notes, intents)), 1)
        self.assertTrue(flick["hit"])
        self.assertFalse(hold["hit"])
        self.assertTrue(hold["sustain_judge"].connected)


class _ReplayFinished(Exception):
    pass


class GameplayReplayTests(unittest.TestCase):
    def replay(self, frames, notes, dom=False):
        """Run real event parsing, drawing and scoring; replace only devices/time."""
        current = {"index": -1, "time": 0.0}

        class ReplayAudio:
            ended = False
            pending = []

            @property
            def currentTime(self):
                return current["time"]

            def drainInput(self):
                events, self.pending = self.pending, []
                return json.dumps(events)

            def clearInput(self):
                self.pending = []

            def setInputEnabled(self, enabled):
                self.enabled = enabled

            def pause(self):
                pass

            def play(self):
                pass

        audio = ReplayAudio()

        class ReplayClock:
            def tick(self, *_):
                current["index"] += 1
                when, events = frames[current["index"]]
                current["time"] = when
                if dom:
                    audio.pending = events
                else:
                    for kind, values in events:
                        game.pygame.event.post(game.pygame.event.Event(kind, values))
                return 16

        async def yield_frame(_delay):
            if current["index"] >= len(frames) - 1:
                raise _ReplayFinished()

        game.pygame.event.clear()
        song = dict(game.MAP_LIST[0], duration=10)
        total = game.prepare_sustain_combo_ticks(notes, 120)
        with ExitStack() as stack:
            stack.enter_context(patch.multiple(game,
                state="PLAY", current_map=song, current_map_idx=0,
                current_difficulty="master", current_bpm=120, current_offset=0,
                chart=notes, active_chart_notes=[], next_chart_index=0,
                score=0, combo=0, max_combo=0, hit_score=0, total_notes=total,
                perfect_count=0, great_count=0, miss_count=0, hp=100,
                particles=[], key_lanes_down=set(), active_touches={},
                flick_keyboard=KeyboardFlickInput(), flick_touch=TouchFlickInput(),
                practice_mode=True, audio_element=audio if dom else None, audio_ended_at=None,
                music_scheduled_start=None, auto_analysis_job=None,
                clock=ReplayClock(), last_feedback="", feedback_time=0))
            stack.enter_context(patch.object(game.time, "perf_counter", lambda: 100 + current["time"]))
            stack.enter_context(patch.object(game.pygame.mixer.music, "get_busy", return_value=True))
            stack.enter_context(patch.object(game.pygame.mixer.music, "get_pos", lambda: round(current["time"] * 1000)))
            stack.enter_context(patch.object(game.asyncio, "sleep", yield_frame))
            saver = stack.enter_context(patch.object(game, "save_records"))
            with self.assertRaises(_ReplayFinished):
                asyncio.run(game.main())
            saver.assert_not_called()
            return {"perfect": game.perfect_count, "great": game.great_count,
                    "miss": game.miss_count, "combo": game.combo, "state": game.state}

    @staticmethod
    def down(key):
        return game.pygame.KEYDOWN, {"key": key}

    @staticmethod
    def up(key):
        return game.pygame.KEYUP, {"key": key}

    def test_actual_keyboard_event_route_awards_space_on_selected_lane(self):
        target = note()
        result = self.replay([(0.98, [self.down(game.pygame.K_d)]),
                              (1.0, [self.down(game.pygame.K_SPACE)]),
                              (1.02, [])], [target])
        self.assertEqual(result["perfect"], 1)
        self.assertEqual(result["miss"], 0)
        self.assertTrue(target["hit"])

    def test_actual_plain_lane_press_without_space_misses_flick(self):
        result = self.replay([(1, [self.down(game.pygame.K_d)]), (1.22, [])], [note()])
        self.assertEqual(result["perfect"], 0)
        self.assertEqual(result["miss"], 1)

    def test_actual_reverse_order_across_frames_uses_space_time(self):
        result = self.replay([(0.99, [self.down(game.pygame.K_SPACE)]),
                              (1.02, [self.down(game.pygame.K_d)])], [note()])
        self.assertEqual(result["perfect"], 1)

    def test_reverse_order_late_edge_survives_intermediate_frame(self):
        result = self.replay([(1.14, [self.down(game.pygame.K_SPACE)]),
                              (1.16, []), (1.175, [self.down(game.pygame.K_d)])], [note()])
        self.assertEqual(result["great"], 1)
        self.assertEqual(result["miss"], 0)

    def test_recognition_grace_does_not_widen_actual_hit_window(self):
        result = self.replay([(1.1, [self.down(game.pygame.K_d)]),
                              (1.17, [self.down(game.pygame.K_SPACE)]),
                              (1.22, [])], [note()])
        self.assertEqual(result["great"], 0)
        self.assertEqual(result["perfect"], 0)
        self.assertEqual(result["miss"], 1)

    def test_dom_keyboard_uses_audio_timestamp_instead_of_delivery_frame(self):
        result = self.replay([(1.17, [["key", "down", "KeyD", 0.98],
                                    ["key", "down", "Space", 1.0]])], [note()], dom=True)
        self.assertEqual(result["perfect"], 1)
        self.assertEqual(result["miss"], 0)

    def test_dom_multitouch_upward_motion_handles_two_lanes(self):
        result = self.replay([
            (1.1, [["pointer", "down", 41, 130, 400, 0.98],
                   ["pointer", "down", 42, 670, 400, 0.98],
                   ["pointer", "up", 41, 130, 380, 1.02],
                   ["pointer", "up", 42, 670, 380, 1.02]])],
            [note(lane=0), note(lane=3)], dom=True)
        self.assertEqual(result["perfect"], 2)
        self.assertEqual(result["miss"], 0)
        self.assertEqual(result["combo"], 2)

    def test_actual_flick_preserves_hold_head_and_release_judgement(self):
        notes = [note(0.8, lane=1, kind="HOLD", end=1.3), note(1)]
        result = self.replay([
            (0.8, [self.down(game.pygame.K_f)]),
            (0.98, [self.down(game.pygame.K_d)]),
            (1.0, [self.down(game.pygame.K_SPACE)]),
            (1.1, []),
            (1.3, [self.up(game.pygame.K_f)])], notes)
        self.assertEqual(result["perfect"], 3)
        self.assertEqual(result["miss"], 0)
        self.assertTrue(notes[0]["sustain_judge"].tail_hit)
        self.assertTrue(notes[1]["hit"])

    def test_actual_simultaneous_tap_and_other_lane_flick_both_score(self):
        result = self.replay([
            (0.98, [self.down(game.pygame.K_d)]),
            (1.0, [self.down(game.pygame.K_SPACE), self.down(game.pygame.K_k)])],
            [note(1), note(1, lane=3, kind="TAP")])
        self.assertEqual(result["perfect"], 2)
        self.assertEqual(result["miss"], 0)

    def test_native_touch_motion_and_up_trigger_flick(self):
        finger = 42
        result = self.replay([
            (0.98, [(game.pygame.FINGERDOWN, {"finger_id": finger, "x": 130 / 800, "y": 400 / 480})]),
            (1.02, [(game.pygame.FINGERUP, {"finger_id": finger, "x": 130 / 800, "y": 380 / 480})])], [note()])
        self.assertEqual(result["perfect"], 1)
        self.assertEqual(result["miss"], 0)

    def test_focus_loss_discards_pending_chord(self):
        result = self.replay([(0.98, [self.down(game.pygame.K_d)]),
                              (1, [(game.pygame.WINDOWFOCUSLOST, {})]),
                              (1.02, [self.down(game.pygame.K_SPACE)])], [note()])
        self.assertEqual(result["perfect"], 0)
        self.assertEqual(result["state"], "PAUSED")

    def test_resume_drops_pause_screen_chord_in_same_event_batch(self):
        target = note()
        result = self.replay([
            (0.98, [self.down(game.pygame.K_ESCAPE)]),
            (1.0, [self.down(game.pygame.K_d), self.down(game.pygame.K_SPACE),
                   self.down(game.pygame.K_ESCAPE)])], [target])
        self.assertEqual(result["state"], "PLAY")
        self.assertEqual(result["perfect"], 0)
        self.assertEqual(result["great"], 0)
        self.assertEqual(result["miss"], 0)
        self.assertFalse(target["hit"])

    def test_fresh_chord_after_resume_still_hits(self):
        target = note()
        result = self.replay([
            (0.98, [self.down(game.pygame.K_ESCAPE)]),
            (1.0, [self.down(game.pygame.K_d), self.down(game.pygame.K_SPACE),
                   self.down(game.pygame.K_ESCAPE)]),
            (1.02, [self.up(game.pygame.K_d), self.up(game.pygame.K_SPACE)]),
            (1.04, [self.down(game.pygame.K_d), self.down(game.pygame.K_SPACE)])], [target])
        self.assertEqual(result["state"], "PLAY")
        self.assertEqual(result["perfect"], 1)
        self.assertEqual(result["great"], 0)
        self.assertEqual(result["miss"], 0)
        self.assertTrue(target["hit"])


if __name__ == "__main__":
    unittest.main()
