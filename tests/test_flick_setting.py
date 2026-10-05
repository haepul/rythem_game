import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import main as game


class FlickSettingTests(unittest.TestCase):
    def test_off_keeps_timing_geometry_and_source_for_on(self):
        notes = [{'type': 'FLICK', 'time': 1.25, 'lane': 2, 'hit': False},
                 {'type': 'HOLD', 'time': 2, 'lane': 0, 'end_time': 3}]
        disabled = game.chart_with_flick_setting(notes, False)
        self.assertEqual(disabled[0], {**notes[0], 'type': 'TAP'})
        self.assertEqual(disabled[1], notes[1])
        self.assertEqual(game.chart_with_flick_setting(notes, True), notes)
        self.assertEqual(notes[0]['type'], 'FLICK')

    def test_setting_survives_reload_and_bad_save_defaults_on(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'settings.json')
            with patch.object(game, 'SETTINGS_PATH', path), patch.object(game, 'flick_enabled', True):
                self.assertTrue(game.load_flick_setting())
                game.set_flick_enabled(False)
                self.assertFalse(game.load_flick_setting())
                game.set_flick_enabled(True)
                self.assertTrue(game.load_flick_setting())
                Path(path).write_text(json.dumps({'flick_enabled': 'false'}))
                self.assertTrue(game.load_flick_setting())

    def test_home_button_changes_saved_selection(self):
        with patch.object(game, 'flick_enabled', True), patch.object(game, 'set_flick_enabled') as setter:
            game.draw_home((549, 60), True)
            setter.assert_called_once_with(False)


if __name__ == '__main__':
    unittest.main()
