"""Pause settings must change visual scrolling without changing the song clock."""
import os
import unittest
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import main as game
import test_flick_integration as replay_tests


class PauseControlsTests(unittest.TestCase):
    def test_flick_switch_preserves_judged_notes_timing_and_combo(self):
        notes = [{'type': 'FLICK', 'authored_type': 'FLICK', 'hit': True, 'time': 1, 'lane': 0},
                 {'type': 'FLICK', 'authored_type': 'FLICK', 'hit': False, 'time': 2, 'lane': 1},
                 {'type': 'HOLD', 'hit': False, 'time': 3, 'end_time': 4, 'lane': 2}]
        with patch.multiple(game, state='PAUSED', chart=notes, current_flick_enabled=True,
                            flick_enabled=True, combo=42, audio_element=None), patch.object(game, 'set_flick_enabled') as save:
            save.side_effect = lambda value: setattr(game, 'flick_enabled', value)
            game.change_pause_flick()
            self.assertEqual([n['type'] for n in notes], ['FLICK', 'TAP', 'HOLD'])
            self.assertEqual([n['time'] for n in notes], [1, 2, 3])
            self.assertEqual(game.combo, 42)
            game.change_pause_flick()
            self.assertEqual(notes[1]['type'], 'FLICK')

    def test_flick_can_be_restored_after_starting_with_it_off(self):
        source = [{'type': 'FLICK', 'authored_type': 'FLICK', 'hit': False, 'time': 2, 'lane': 1}]
        notes = game.chart_with_flick_setting(source, False)
        with patch.multiple(game, state='PAUSED', chart=notes, current_flick_enabled=False,
                            flick_enabled=False, audio_element=None), patch.object(game, 'set_flick_enabled') as save:
            save.side_effect = lambda value: setattr(game, 'flick_enabled', value)
            game.change_pause_flick()
            self.assertEqual(notes[0]['type'], 'FLICK')
            self.assertEqual(source[0]['type'], 'FLICK')

    def test_fall_speed_only_changes_approach_time(self):
        audio = Mock()
        notes = [{'type': 'TAP', 'time': 4, 'lane': 0, 'hit': False}]
        with patch.multiple(game, state='PAUSED', chart=notes, note_speed_index=2,
                            APPROACH_TIME=game.BASE_APPROACH_TIME, audio_element=audio,
                            current_bpm=165, game_start_time=123, score=1234, combo=42):
            game.adjust_note_speed(1)
            self.assertAlmostEqual(game.APPROACH_TIME, game.BASE_APPROACH_TIME / 1.15)
            self.assertEqual(game.current_bpm, 165)
            self.assertEqual(game.game_start_time, 123)
            self.assertEqual((game.score, game.combo), (1234, 42))
            self.assertEqual(notes[0]['time'], 4)
            self.assertEqual(audio.mock_calls, [])

    def test_scroll_speed_limits(self):
        with patch.multiple(game, note_speed_index=0, APPROACH_TIME=game.BASE_APPROACH_TIME / .75):
            game.adjust_note_speed(-1)
            self.assertEqual(game.note_speed_index, 0)
        with patch.multiple(game, note_speed_index=len(game.NOTE_SPEED_LEVELS)-1,
                            APPROACH_TIME=game.BASE_APPROACH_TIME / 2):
            game.adjust_note_speed(1)
            self.assertEqual(game.APPROACH_TIME, game.BASE_APPROACH_TIME / 2)

    def test_actual_judgement_times_do_not_depend_on_scroll_speed(self):
        replay = replay_tests.GameplayReplayTests()
        for index, speed in enumerate(game.NOTE_SPEED_LEVELS):
            with self.subTest(speed=speed), patch.multiple(game, note_speed_index=index,
                    APPROACH_TIME=game.BASE_APPROACH_TIME/speed):
                target = replay_tests.note(kind='TAP')
                result = replay.replay([(1.06, [replay.down(game.pygame.K_d)])], [target])
                self.assertEqual((result['perfect'], result['miss']), (1, 0))
                target = replay_tests.note(kind='TAP')
                result = replay.replay([(1.17, [replay.down(game.pygame.K_d)]), (1.22, [])], [target])
                self.assertEqual((result['perfect'], result['great'], result['miss']), (0, 0, 1))


if __name__ == '__main__':
    unittest.main()
