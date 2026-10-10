"""Visual geometry, compositing and clock regressions for the glass renderer."""
import copy
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import main as game
from note_renderer import NoteRenderer, glass_sprite
from sustain_judgement import SustainJudge

PALETTE = {"TAP": ((255, 242, 255), (247, 93, 187)),
           "HOLD": ((255, 250, 196), (45, 218, 222)),
           "SLIDE": ((255, 203, 255), (151, 90, 255))}


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.renderer = NoteRenderer(game.get_perspective_pos)
        self.surface = pygame.Surface((800, 480))

    def test_slide_samples_follow_judgement_path_in_both_directions(self):
        for start, end in ((0, 3), (3, 0), (1, 2)):
            note = dict(type="SLIDE", lane=start, end_lane=end, time=2, end_time=5)
            judge = SustainJudge(note, [2, 5])
            for now in (1.1, 2, 3.7, 4.99):
                points = self.renderer.ribbon_points(note, now, 1.0)
                for when, x, y, half in points:
                    projected = game.get_perspective_pos(judge.position(when), 1-(when-now))
                    self.assertAlmostEqual(x, projected[0])
                    self.assertAlmostEqual(y, projected[1])
                    self.assertGreater(half, 0)
                self.assertTrue(all(a[2] >= b[2] for a, b in zip(points, points[1:])))

    def test_ribbon_clips_actual_time_range_and_never_grows_on_early_press(self):
        note = dict(type="SLIDE", lane=0, end_lane=3, time=1, end_time=2)
        before = self.renderer.ribbon_points(note, .92, 1)
        note["active"] = True
        self.assertEqual(before, self.renderer.ribbon_points(note, .92, 1))
        self.assertAlmostEqual(before[0][0], 1)
        self.assertAlmostEqual(before[-1][0], 1.92)
        self.assertEqual(self.renderer.ribbon_points(note, 2, 1), [])
        self.assertEqual(self.renderer.ribbon_points(note, -1, 1), [])

    def test_rendering_never_changes_notes_or_judgements(self):
        notes = [dict(type=kind, lane=i, time=.3, end_time=.8, end_lane=3-i, hit=False)
                 for i, kind in enumerate(("TAP", "FLICK", "HOLD", "SLIDE"))]
        snapshot = copy.deepcopy(notes)
        for now in (-.3, 0, .4, .8, 1):
            self.renderer.draw(self.surface, notes, now, 1, PALETTE)
        self.assertEqual(notes, snapshot)

    def test_caps_are_drawn_above_overlapping_ribbons_regardless_of_input_order(self):
        tap = dict(type="TAP", lane=1, time=.3)
        hold = dict(type="HOLD", lane=1, time=0, end_time=1)
        outputs = []
        for notes in ([tap, hold], [hold, tap], [tap]):
            self.surface.fill((10, 15, 20))
            self.renderer.draw(self.surface, notes, 0, 1, PALETTE)
            x, y, _ = game.get_perspective_pos(1, .7)
            outputs.append(self.surface.get_at((round(x), round(y))))
        self.assertEqual(outputs[0], outputs[1])
        self.surface.fill((10, 15, 20))
        self.renderer.draw(self.surface, [hold], 0, 1, PALETTE)
        self.renderer.head(self.surface, 1, .7, *PALETTE['TAP'])
        self.assertEqual(outputs[0], self.surface.get_at((round(x), round(y))))
        self.assertNotEqual(outputs[0], outputs[2])  # Ribbon shows through the face.

    def test_paused_song_clock_freezes_flow_and_head_positions(self):
        notes = [dict(type="SLIDE", lane=0, end_lane=3, time=-.2, end_time=.8, active=True)]
        images = []
        for _ in range(2):
            self.surface.fill((0, 0, 0))
            self.renderer.draw(self.surface, notes, .2, 1, PALETTE)
            images.append(pygame.image.tobytes(self.surface, "RGB"))
        self.assertEqual(*images)

    def test_flick_stays_pink_at_all_combo_colors(self):
        images = []
        for combo in (0, 10, 35, 75, 150, 300):
            self.surface.fill((0, 0, 0))
            self.renderer.head(self.surface, 1, .5, *game.combo_gradient_colors(combo), flick=True)
            images.append(pygame.image.tobytes(self.surface, "RGB"))
        self.assertTrue(all(image == images[0] for image in images))

    def test_horizon_flick_arrow_has_bright_pixels_above_the_cap(self):
        self.surface.fill((0, 0, 0))
        self.renderer.head(self.surface, 1, .01, *PALETTE["TAP"], flick=True)
        x, y, _ = game.get_perspective_pos(1, .01)
        pixels = [self.surface.get_at((round(x)+dx, round(y)+dy))
                  for dx in range(-12, 13) for dy in range(-20, -5)]
        self.assertTrue(any(min(pixel[:3]) > 210 for pixel in pixels))

    def test_fast_jacks_keep_separate_visible_centers_near_judgement_line(self):
        self.surface.fill((0, 0, 0))
        notes = [dict(type="TAP", lane=1, time=t) for t in (.05, .113)]
        self.renderer.draw(self.surface, notes, 0, 1, PALETTE)
        for note in notes:
            x, y, _ = game.get_perspective_pos(1, 1-note['time'])
            self.assertGreater(min(self.surface.get_at((round(x), round(y)))[:3]), 150)

    def test_near_head_has_a_broad_visible_face_without_shifting_its_center(self):
        self.surface.fill((0, 0, 0))
        self.renderer.head(self.surface, 1, 1, *PALETTE["TAP"])
        x, y, _ = game.get_perspective_pos(1, 1)
        bright_rows = [row for row in range(round(y)-30, round(y)+30)
                       if max(self.surface.get_at((round(x), row))[:3]) > 150]
        self.assertGreaterEqual(len(bright_rows), 32)
        self.assertLessEqual(len(bright_rows), 36)
        self.assertLessEqual(abs((min(bright_rows)+max(bright_rows))/2-y), 1)

    def test_head_faces_remain_translucent_for_all_note_types(self):
        for flick, tail in ((False, False), (True, False), (False, True)):
            sprite = glass_sprite(160, 34, *PALETTE['TAP'], flick=flick, tail=tail)
            arrow = 45 if flick else 0
            self.assertEqual(sprite.get_at((55, 22 + arrow)).a, 205)

    def test_finished_notes_are_not_rendered_and_cache_is_bounded(self):
        self.surface.fill((0, 0, 0))
        before = pygame.image.tobytes(self.surface, "RGB")
        self.renderer.draw(self.surface, [dict(type="TAP", lane=0, time=.2, hit=True)], 0, 1, PALETTE)
        self.assertEqual(before, pygame.image.tobytes(self.surface, "RGB"))
        self.assertEqual(glass_sprite.cache_info().maxsize, 384)


if __name__ == "__main__":
    unittest.main()
