import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chart_layout import note_end, notes_overlap, resolve_note_overlaps


def tap(time, lane, kind="TAP"):
    return {"type": kind, "time": time, "lane": lane}


def hold(start, end, lane):
    return {"type": "HOLD", "time": start, "end_time": end, "lane": lane}


def slide(start, end, first, last):
    return {"type": "SLIDE", "time": start, "end_time": end, "lane": first, "end_lane": last}


class ChartLayoutTests(unittest.TestCase):
    def test_taps_and_flicks_move_away_from_hold_body_and_tail(self):
        notes = [hold(1, 3, 1), tap(2, 1), tap(3.04, 1, "FLICK"), tap(3.3, 1)]
        fixed = resolve_note_overlaps(notes)
        self.assertEqual([n['time'] for n in fixed], [1, 2, 3.04, 3.3])
        self.assertEqual([n['lane'] for n in fixed], [1, 0, 0, 1])
        self.assertEqual(fixed[2]['type'], 'FLICK')

    def test_slide_intermediate_path_is_checked_not_only_endpoints(self):
        path = slide(1, 3, 0, 3)
        self.assertTrue(notes_overlap(path, tap(2, 1)))
        self.assertTrue(notes_overlap(path, tap(2, 2)))
        self.assertFalse(notes_overlap(path, tap(2, 0)))
        fixed = resolve_note_overlaps([path, tap(2, 1)])
        self.assertGreaterEqual(abs(fixed[1]['lane'] - 1.5), .9)

    def test_crossing_slides_and_parallel_slides(self):
        first, second = slide(0, 2, 0, 3), slide(0, 2, 3, 0)
        self.assertTrue(notes_overlap(first, second))
        self.assertFalse(notes_overlap(slide(0, 2, 0, 1), slide(0, 2, 2, 3)))
        fixed = resolve_note_overlaps([first, second])
        self.assertEqual(len(fixed), 2)
        self.assertFalse(notes_overlap(*fixed))
        self.assertTrue(all(n['time'] == 0 for n in fixed))

    def test_adjacent_chord_and_fast_alternating_pattern_remain_intact(self):
        notes = [hold(0, 2, 0), tap(0, 1), tap(.125, 2), tap(.25, 3), tap(.375, 2)]
        self.assertEqual(resolve_note_overlaps(notes), notes)

    def test_fully_occupied_custom_chart_cannot_add_a_fifth_lane(self):
        notes = [hold(0, 2, lane) for lane in range(4)] + [tap(1, 1)]
        self.assertEqual(resolve_note_overlaps(notes), notes[:4])

    def test_deterministic_idempotent_and_source_is_not_mutated(self):
        notes = [hold(0, 2, 0), tap(1, 0), slide(1.2, 2.5, 0, 3)]
        original = copy.deepcopy(notes)
        fixed = resolve_note_overlaps(notes)
        self.assertEqual(resolve_note_overlaps(notes), fixed)
        self.assertEqual(resolve_note_overlaps(fixed), fixed)
        self.assertEqual(notes, original)

    def test_beat_and_second_formats_agree(self):
        for bpm in (76, 165, 240):
            with self.subTest(bpm=bpm):
                seconds = [hold(0, 2, 0), tap(1, 0)]
                beats = [{'type': 'HOLD', 'beat': 0, 'end_beat': 2*bpm/60, 'lane': 0},
                         {'type': 'TAP', 'beat': bpm/60, 'lane': 0}]
                fixed = resolve_note_overlaps(beats, 'beat', 'end_beat', 60/bpm)
                self.assertEqual([n['lane'] for n in fixed],
                                 [n['lane'] for n in resolve_note_overlaps(seconds)])

    def test_entire_catalog_preserves_every_note_and_musical_time(self):
        entries = json.loads((ROOT/'auto_charts.json').read_text(encoding='utf-8'))
        count = 0
        for song, entry in entries.items():
            step = 60/entry['bpm']
            for level, variant in entry['difficulty_charts'].items():
                with self.subTest(song=song, difficulty=level):
                    notes = [{**n, 'source_index': i} for i, n in enumerate(variant['notes'])]
                    fixed = resolve_note_overlaps(notes, 'beat', 'end_beat', step)
                    self.assertEqual(len(fixed), len(notes))
                    for n in fixed:
                        before = notes[n['source_index']]
                        for field in ('type', 'beat', 'end_beat'):
                            self.assertEqual(n.get(field), before.get(field))
                    self.assertEqual(resolve_note_overlaps(fixed, 'beat', 'end_beat', step), fixed)
                    active = []
                    for n in fixed:
                        active = [p for p in active if note_end(p, 'beat', 'end_beat') + .11/step >= n['beat']]
                        self.assertFalse(any(notes_overlap(n, p, 'beat', 'end_beat', step) for p in active))
                        active.append(n)
                    count += 1
        self.assertEqual(count, 63)


if __name__ == '__main__':
    unittest.main()
