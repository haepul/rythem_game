"""Render reproducible skin scenes and measure the desktop drawing budget."""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import main as game
from note_renderer import glass_body, glass_sprite, ribbon_palette


def palettes(combo):
    top, bottom = game.combo_gradient_colors(combo)
    amount = min(1, combo / 12)
    return {
        "TAP": (game.interpolate_color((255, 242, 255), top, amount), game.interpolate_color((247, 93, 187), bottom, amount)),
        "HOLD": (game.interpolate_color((255, 250, 196), top, amount*.8), game.interpolate_color((45, 218, 222), bottom, amount*.8)),
        "SLIDE": (game.interpolate_color((255, 203, 255), top, amount*.9), game.interpolate_color((151, 90, 255), bottom, amount*.9)),
    }


def note(kind, lane, when, end=None, end_lane=None, active=False):
    item = {"type": kind, "lane": lane, "time": when, "hit": False, "active": active}
    if end is not None:
        item["end_time"] = end
    if end_lane is not None:
        item["end_lane"] = end_lane
    return item


def scene(notes, now, approach, combo, title):
    canvas = game.default_bg_surface.copy()
    project = game.get_perspective_pos
    for lane in range(5):
        a, b = project(lane-.5, 0), project(lane-.5, 1)
        pygame.draw.aaline(canvas, (77, 79, 113), a[:2], b[:2])
    pygame.draw.line(canvas, (162, 161, 207), (38, 410), (762, 410), 2)
    game.note_renderer.draw(canvas, notes, now, approach, palettes(combo))
    game.draw_styled_text(canvas, title, game.font_med, 400, 35, (236, 239, 255))
    game.draw_styled_text(canvas, f"COMBO {combo}  /  GLASS PREVIEW", game.font_small, 400, 63, (164, 192, 218))
    return canvas


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    # Deliberate overlapping custom patterns are used even though the chart
    # layout repair normally avoids them: every cap must stay above ribbons.
    examples = [
        ("types", [note("TAP", 0, .12), note("TAP", 0, .39), note("TAP", 0, .67),
                   note("FLICK", 1, .16), note("FLICK", 1, .47), note("FLICK", 1, .76),
                   note("HOLD", 2, .10, .72), note("SLIDE", 3, .05, .76, 2)], 0, 1, 0, "TAP   /   FLICK   /   HOLD   /   SLIDE"),
        ("dense", [note("TAP", 0, i*.063) for i in range(1, 14)] +
                  [note("FLICK", 1, i*.18) for i in range(1, 5)] +
                  [note("HOLD", 2, -.2, .85, active=True), note("SLIDE", 3, -.12, .88, 1, True),
                   note("TAP", 2, .31), note("TAP", 2, .49)], 0, 1, 150, "FAST JACKS + OVERLAP / 63 ms spacing"),
        ("active", [note("HOLD", 0, -.3, .55, active=True), note("SLIDE", 1, -.3, .7, 3, True),
                    note("FLICK", 3, .28), note("TAP", 1, .6)], 0, 1, 300, "ACTIVE RIBBONS / precise moving endpoints"),
        ("horizon", [note("FLICK", lane, .99) for lane in range(4)] +
                    [note("TAP", lane, .87) for lane in range(4)] +
                    [note("FLICK", lane, .58) for lane in range(4)] +
                    [note("TAP", lane, .20) for lane in range(4)], 0, 1, 75, "HORIZON + NEAR / flick contrast"),
    ]
    contact = pygame.Surface((1600, 960))
    for i, (name, *args) in enumerate(examples):
        canvas = scene(*args)
        pygame.image.save(canvas, output / (name + ".png"))
        contact.blit(canvas, ((i % 2)*800, (i // 2)*480))
    pygame.image.save(contact, output / "contact-sheet.png")
    # Warm scrolling workload: 32 taps/flicks plus four crossing long notes.
    stress = [note("FLICK" if i % 5 == 0 else "TAP", i % 4, i*.028) for i in range(32)]
    stress += [note("SLIDE" if i % 2 else "HOLD", i, -.3, 1.2, 3-i, True) for i in range(4)]
    target = pygame.Surface((800, 480))
    times = []
    glass_sprite.cache_clear()
    glass_body.cache_clear()
    for i in range(360):
        now = (i % 120) / 240
        start = time.perf_counter()
        game.note_renderer.draw(target, stress, now, 1, palettes(150))
        times.append((time.perf_counter() - start)*1000)
    stats = {"frames": len(times), "notes": len(stress), "cold_frame_ms": round(times[0], 3),
             "median_ms": round(statistics.median(times[120:]), 3),
             "p95_ms": round(sorted(times[120:])[int(240*.95)], 3),
             "head_cache": glass_sprite.cache_info()._asdict(),
             "gradient_cache": glass_body.cache_info()._asdict(),
             "palette_cache": ribbon_palette.cache_info()._asdict(),
             "scope": "Desktop SDL dummy, renderer only; not browser or phone FPS"}
    (output / "performance.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
