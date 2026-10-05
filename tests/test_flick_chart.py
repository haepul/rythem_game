import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flick_chart import (MIN_FLICK_GAP, MIN_PREVIOUS_GAP, MIN_NEXT_GAP,
                         MIN_LANE_GAP, SUSTAIN_CLEARANCE, add_master_flicks)
from tools.add_master_flicks import migrate_cache


class MasterFlickChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT / "auto_charts.json").read_text(encoding="utf-8"))
        # Exercise the migration from TAPs even when the checked-in cache is
        # already migrated. The existing onset times and geometry stay intact.
        for entry in cls.original.values():
            for note in entry["difficulty_charts"]["master"]["notes"]:
                if note["type"] == "FLICK":
                    note["type"] = "TAP"
        cls.migrated = migrate_cache(cls.original)

    def test_every_song_has_master_flicks_and_easy_hard_unchanged(self):
        self.assertEqual(len(self.original), 21)
        for song, before in self.original.items():
            with self.subTest(song=song):
                after = self.migrated[song]
                for difficulty in ("easy", "hard"):
                    self.assertEqual(before["difficulty_charts"][difficulty],
                                     after["difficulty_charts"][difficulty])
                # The legacy flat chart is the HARD alias, not MASTER.
                for key in ("notes", "type_counts", "selected_count"):
                    self.assertEqual(before.get(key), after.get(key))
                master = after["difficulty_charts"]["master"]
                count = sum(note["type"] == "FLICK" for note in master["notes"])
                self.assertGreater(count, 0)
                self.assertEqual(master["type_counts"]["FLICK"], count)

    def test_all_timestamps_lanes_endpoints_and_metadata_are_preserved(self):
        for song, before in self.original.items():
            with self.subTest(song=song):
                after = self.migrated[song]
                for key in ("bpm", "offset", "duration", "signature", "analysis"):
                    self.assertEqual(before.get(key), after.get(key))
                old = before["difficulty_charts"]["master"]["notes"]
                new = after["difficulty_charts"]["master"]["notes"]
                self.assertEqual(len(old), len(new))
                for initial, updated in zip(old, new):
                    expected = dict(initial)
                    if updated["type"] == "FLICK":
                        self.assertEqual(initial["type"], "TAP")
                        expected["type"] = "FLICK"
                    self.assertEqual(expected, updated)

    def test_deterministic_idempotent_and_does_not_mutate_input(self):
        snapshot = copy.deepcopy(self.original)
        self.assertEqual(migrate_cache(self.original), self.migrated)
        self.assertEqual(self.original, snapshot)
        self.assertEqual(migrate_cache(self.migrated), self.migrated)

    def test_flicks_have_gesture_clearance_and_no_conflicting_chords(self):
        for song, entry in self.migrated.items():
            step = 60.0 / entry["bpm"]
            offset = entry.get("offset", 0.0)
            notes = entry["difficulty_charts"]["master"]["notes"]
            timed = sorted([(offset + note["beat"] * step, i, note)
                            for i, note in enumerate(notes)])
            flick_times = []
            for position, (when, index, note) in enumerate(timed):
                if note["type"] != "FLICK":
                    continue
                with self.subTest(song=song, beat=note["beat"]):
                    flick_times.append(when)
                    if position:
                        self.assertGreaterEqual(when - timed[position - 1][0] + 1e-7, MIN_PREVIOUS_GAP)
                    if position + 1 < len(timed):
                        self.assertGreaterEqual(timed[position + 1][0] - when + 1e-7, MIN_NEXT_GAP)
                    if song == "hatsune-miku-no-shoushitsu":
                        self.assertGreaterEqual(when, 25.0)
                    for other_time, other_index, other in timed:
                        if other_index == index:
                            continue
                        if other["lane"] == note["lane"]:
                            self.assertGreaterEqual(abs(when - other_time) + 1e-7, MIN_LANE_GAP)
                        if other["type"] in ("HOLD", "SLIDE"):
                            end = offset + other["end_beat"] * step
                            self.assertFalse(other_time - SUSTAIN_CLEARANCE - 1e-7 <= when
                                             <= end + SUSTAIN_CLEARANCE + 1e-7)
            for left, right in zip(flick_times, flick_times[1:]):
                self.assertGreaterEqual(right - left + 1e-7, MIN_FLICK_GAP)

    def test_dense_sixteenth_stream_is_not_converted(self):
        notes = [{"type": "TAP", "beat": i * 0.25, "lane": i % 4} for i in range(80)]
        self.assertEqual(add_master_flicks(notes, 240), notes)

    def test_existing_flicks_are_kept(self):
        notes = [{"type": "FLICK", "beat": 2.0, "lane": 1}]
        self.assertEqual(add_master_flicks(notes, 120), notes)
        self.assertIsNot(add_master_flicks(notes, 120), notes)

    def test_non_grid_attack_is_not_quantized(self):
        notes = [{"type": "TAP", "beat": 1.173459, "lane": 2}]
        result = add_master_flicks(notes, 123, 0.027)
        self.assertEqual(result, [{"type": "FLICK", "beat": 1.173459, "lane": 2}])

    def test_invalid_clock_is_rejected(self):
        for bpm in (0, -1, float("nan"), float("inf")):
            with self.subTest(bpm=bpm), self.assertRaises(ValueError):
                add_master_flicks([], bpm)


if __name__ == "__main__":
    unittest.main()
