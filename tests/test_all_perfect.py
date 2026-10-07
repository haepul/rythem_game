import os
import unittest
from unittest.mock import patch

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

    def test_perfect_gameplay_uses_normal_combo_even_after_last_note(self):
        replay = replay_tests.GameplayReplayTests()
        notes = [replay_tests.note(1 + i*.3, i, 'TAP') for i in range(3)]
        frames = [(1 + i*.3, [replay.down(key)])
                  for i, key in enumerate((game.pygame.K_d, game.pygame.K_f, game.pygame.K_j))]
        with patch.object(game, 'draw_prismatic_text') as award:
            result = replay.replay(frames, notes)
        self.assertEqual((result['perfect'], result['combo'], result['state']), (3, 3, 'PLAY'))
        award.assert_not_called()

    def test_completed_ap_holds_fades_and_enters_results_once(self):
        with patch.multiple(game, practice_mode=True, state='PLAY', total_notes=100,
                            perfect_count=100, great_count=0, miss_count=0, hit_score=10000,
                            clear_started_at=None, clear_backdrop=None), \
                patch.object(game, 'stop_music'), patch.object(game, 'save_records') as save, \
                patch.object(game.time, 'perf_counter', return_value=100) as clock, \
                patch.object(game, 'draw_result_summary') as results:
            game.finish_song()
            self.assertEqual(game.state, 'CLEAR')
            game.draw_clear_celebration(game.screen)
            self.assertEqual(game.clear_award_surface.get_alpha(), 255)
            clock.return_value = 100 + game.AP_HOLD_SECONDS + game.AP_FADE_SECONDS / 2
            game.draw_clear_celebration(game.screen)
            self.assertAlmostEqual(game.clear_award_surface.get_alpha(), 128, delta=1)
            self.assertEqual(game.state, 'CLEAR')
            clock.return_value = 100 + game.AP_HOLD_SECONDS + game.AP_FADE_SECONDS + .01
            game.draw_clear_celebration(game.screen)
            self.assertEqual(game.state, 'RESULT')
            self.assertIsNone(game.clear_started_at)
            self.assertIsNone(game.clear_backdrop)
            results.assert_called_once()
            save.assert_not_called()

    def test_non_ap_completion_skips_announcement_and_clears_old_animation(self):
        for perfect, great, miss in ((99, 1, 0), (99, 0, 1), (99, 0, 0)):
            with self.subTest(counts=(perfect, great, miss)), \
                    patch.multiple(game, practice_mode=True, state='PLAY', total_notes=100,
                                   perfect_count=perfect, great_count=great, miss_count=miss, hit_score=9900,
                                   clear_started_at=50, clear_backdrop=game.screen.copy()), \
                    patch.object(game, 'stop_music'):
                game.finish_song()
                self.assertEqual(game.state, 'RESULT')
                self.assertIsNone(game.clear_started_at)
                self.assertIsNone(game.clear_backdrop)

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
