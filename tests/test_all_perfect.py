import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import main as game
import test_flick_integration as replay_tests


class AllPerfectTests(unittest.TestCase):
    def test_completion_requires_every_judgement_and_no_great_or_miss(self):
        self.assertTrue(game.is_all_perfect(100, 100, 0, 0))
        for counts in ((0, 0, 0, 0), (100, 99, 0, 0), (100, 99, 1, 0),
                       (100, 99, 0, 1), (100, 100, 1, 0), (100, 101, 0, 0)):
            with self.subTest(counts=counts):
                self.assertFalse(game.is_all_perfect(*counts))

    def test_live_ap_starts_after_first_perfect_and_stops_at_great(self):
        self.assertFalse(game.is_all_perfect(100, 0, 0, 0, completed=False))
        self.assertTrue(game.is_all_perfect(100, 3, 0, 0, completed=False))
        self.assertFalse(game.is_all_perfect(100, 3, 1, 0, completed=False))
        self.assertFalse(game.is_all_perfect(100, 3, 0, 1, completed=False))

    def test_hold_head_body_and_tail_all_count_toward_ap(self):
        replay = replay_tests.GameplayReplayTests()
        target = replay_tests.note(1, 0, 'HOLD', end=2)
        result = replay.replay([(1, [replay.down(game.pygame.K_d)]), (2.03, [])], [target])
        self.assertGreater(target['tick_total'], 2)
        self.assertTrue(game.is_all_perfect(target['tick_total'], result['perfect'], result['great'], result['miss']))

    def test_early_hold_release_and_missed_body_cannot_earn_ap(self):
        replay = replay_tests.GameplayReplayTests()
        for frames in ([(1, [replay.down(game.pygame.K_d)]), (1.95, [replay.up(game.pygame.K_d)]), (2.08, [])],
                       [(1, [replay.down(game.pygame.K_d)]), (1.3, [replay.up(game.pygame.K_d)]),
                        (1.7, [replay.down(game.pygame.K_d)]), (2.08, [])]):
            target = replay_tests.note(1, 0, 'HOLD', end=2)
            result = replay.replay(frames, [target])
            self.assertFalse(game.is_all_perfect(target['tick_total'], result['perfect'], result['great'], result['miss']))

    def test_loaded_chart_is_separated_before_sustain_ticks_are_created(self):
        entry = {'bpm': 120, 'notes': [{'type': 'HOLD', 'beat': 2, 'end_beat': 6, 'lane': 1},
                                     {'type': 'TAP', 'beat': 4, 'lane': 1}]}
        notes, bpm, _ = game.load_authored_chart('unused', 5, 10, 120, 0, entry)
        self.assertEqual([n['time'] for n in notes], [1, 2])
        self.assertNotEqual(notes[0]['lane'], notes[1]['lane'])
        game.prepare_sustain_combo_ticks(notes, bpm)
        self.assertEqual(notes[0]['sustain_judge'].lane, notes[0]['lane'])


if __name__ == '__main__':
    unittest.main()
