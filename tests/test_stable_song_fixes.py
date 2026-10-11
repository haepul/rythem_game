"""Stable-site duration, replacement-audio and complete-title regressions."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from stable import main as game


class StableSongFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = json.loads((ROOT / 'auto_charts.json').read_text(encoding='utf-8'))
        cls.songs = {song['audio']: song for song in game.additional_songs}

    def test_distinct_verse_and_full_durations(self):
        for filename, verse, full in [('rendezvous.mp3', 81.5, 225.5122),
                                      ('salt-pepper-birds.mp3', 107.8, 244.1346)]:
            song, entry = self.songs[filename], self.cache[Path(filename).stem]
            self.assertEqual(game.song_duration(song, 'verse', entry), verse)
            self.assertAlmostEqual(game.song_duration(song, 'full', entry), full, places=3)
            self.assertGreater(full, verse + 60)
            for difficulty in ('easy', 'hard', 'master'):
                selected = game.chart_entry_for_difficulty(entry, difficulty)
                for duration in (verse, full):
                    notes, _, _ = game.load_authored_chart(filename, 9, duration,
                                                          entry['bpm'], entry['offset'], selected)
                    self.assertTrue(notes)
                    self.assertTrue(all(0 <= n['time'] < duration for n in notes))
                    self.assertTrue(all(n.get('end_time', n['time']) <= duration for n in notes))
                self.assertTrue(any(entry['offset'] + n['beat'] * 60 / entry['bpm'] > verse + 30
                                    for n in selected['notes']))

    def test_replacement_audio_is_used_and_cache_busted(self):
        song = self.songs['rendezvous.mp3']
        path = ROOT / 'music' / song['audio']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(self.cache['rendezvous']['source_sha256'], digest)
        self.assertEqual(song['audio_version'], digest[:12])
        self.assertIn(song['audio'] + '?v=' + digest[:12], game.WEB_AUDIO_FILES)
        self.assertGreater(pygame.mixer.Sound(str(path)).get_length(), 225)

    def test_complete_title_fits_web_font_panels_readably(self):
        song = self.songs['salt-pepper-birds.mp3']
        self.assertEqual(song['song'], 'Salt, Pepper, Birds, and the Thought Police')
        font = pygame.font.Font(str(ROOT / 'font.ttf'), 14)
        for width, height in ((108, 46), (192, 36), (720, 50)):
            image = game.wrapped_title_image(song['song'], font, width, height)
            self.assertLessEqual(image.get_width(), width)
            self.assertLessEqual(image.get_height(), height)
            self.assertGreater(image.get_width(), min(90, width * .8))
            self.assertGreater(image.get_bounding_rect().height, 10)


if __name__ == '__main__':
    unittest.main()
