import asyncio  # 상단에 추가
import pygame
from auto_chart import generate_auto_chart, generate_auto_chart_levels
import time
import random
import sys
import math
import os
import json
import base64
import subprocess
import threading
from functools import lru_cache
from tap_judgement import match_tap_presses
from flick_judgement import KeyboardFlickInput, TouchFlickInput, match_flick_intents
from sustain_judgement import SustainJudge, TouchContact, HEAD_WINDOW, MIN_CONTINUOUS_HOLD, TAIL_EARLY_WINDOW
from chart_layout import resolve_note_overlaps
from note_renderer import NoteRenderer


# ---------------------------------------------------------
# 1. 초기 설정 및 폰트
# ---------------------------------------------------------
# Keep the audio output buffer small so the audible beat stays close to the
# gameplay clock (the default SDL_mixer buffer can add a noticeable delay).
pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.init()
pygame.font.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 480
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Rhythm Stage")
clock = pygame.time.Clock()
pressed_glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
GAME_DIR = os.path.dirname(os.path.abspath(__file__))

def load_korean_font(size, bold=False):
    # Use a clean native UI font on Windows; retain the bundled font in the web build.
    if sys.platform == "emscripten":
        return pygame.font.Font(os.path.join(GAME_DIR, "font.ttf"), size)
    return pygame.font.SysFont("Malgun Gothic", size, bold=bold)

# 폰트 사이즈 전체적으로 축소 (UI 잘림 방지)
font_combo_num = load_korean_font(58, bold=True)
font_combo_sub = load_korean_font(16, bold=True)
font_large = load_korean_font(32, bold=True)
font_med = load_korean_font(20, bold=True)
font_small = load_korean_font(14, bold=True)

# ---------------------------------------------------------
# 2. 3D 퍼스펙티브(원근감) 트랙 설정
# ---------------------------------------------------------
TRACK_TOP_Y = 110        
TRACK_BOTTOM_Y = 410     
JUDGE_Y = TRACK_BOTTOM_Y

TRACK_TOP_W = 286       
TRACK_BOTTOM_W = 724    
CENTER_X = SCREEN_WIDTH // 2

def get_perspective_pos(lane, progress):
    p_clamped = max(0.0, progress)
    p_curved = math.pow(p_clamped, 1.55)
    y = TRACK_TOP_Y + (TRACK_BOTTOM_Y - TRACK_TOP_Y) * p_curved
    current_track_w = TRACK_TOP_W + (TRACK_BOTTOM_W - TRACK_TOP_W) * p_curved
    lane_w = current_track_w / 4.0
    track_left = CENTER_X - (current_track_w / 2.0)
    x_center = track_left + (lane + 0.5) * lane_w
    return x_center, y, lane_w


note_renderer = NoteRenderer(get_perspective_pos, (SCREEN_WIDTH, SCREEN_HEIGHT))

def generate_bg_surface(colors, accent):
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    c_top, c_mid, c_bot = colors
    base_rows = []
    for y in range(0, SCREEN_HEIGHT, 4):
        ratio = y / max(1, SCREEN_HEIGHT - 1)
        if ratio < 0.5:
            r1 = ratio * 2
            base = tuple(int(c_top[i] * (1 - r1) + c_mid[i] * r1) for i in range(3))
        else:
            r2 = (ratio - 0.5) * 2
            base = tuple(int(c_mid[i] * (1 - r2) + c_bot[i] * r2) for i in range(3))
        base_rows.append(base)

    # Blend two broad accent glows into the dark base for a layered 2D gradient.
    for y_index, y in enumerate(range(0, SCREEN_HEIGHT, 4)):
        base = base_rows[y_index]
        for x in range(0, SCREEN_WIDTH, 4):
            glow_right = max(0.0, 1.0 - math.hypot((x - SCREEN_WIDTH * 0.78) / 430.0,
                                                  (y - SCREEN_HEIGHT * 0.20) / 300.0))
            glow_left = max(0.0, 1.0 - math.hypot((x - SCREEN_WIDTH * 0.16) / 360.0,
                                                 (y - SCREEN_HEIGHT * 0.82) / 280.0))
            blend = min(0.30, glow_right * 0.21 + glow_left * 0.12)
            color = tuple(int(base[i] * (1.0 - blend) + accent[i] * blend) for i in range(3))
            pygame.draw.rect(surf, color, (x, y, 4, 4))
        
    for _ in range(20):
        rx = random.randint(0, SCREEN_WIDTH)
        ry = random.randint(0, SCREEN_HEIGHT)
        pygame.draw.circle(surf, accent, (rx, ry), random.randint(1, 2))
    return surf

default_bg_surface = generate_bg_surface(((18, 10, 40), (10, 20, 50), (5, 5, 15)), (0, 180, 255))
current_bg_surface = default_bg_surface

# ---------------------------------------------------------
# 3. 유틸리티 & 그래디언트 렌더러
# ---------------------------------------------------------
def interpolate_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )

def combo_gradient_colors(combo_count):
    """Return a smoothly shifting note gradient tied to the active combo."""
    stops = (
        (0,   (255, 242, 255), (247, 93, 187)),
        (10,  (203, 252, 255), (34, 194, 255)),
        (35,  (225, 214, 255), (119, 91, 255)),
        (75,  (255, 210, 235), (255, 69, 173)),
        (150, (255, 247, 190), (255, 150, 38)),
        (300, (255, 255, 255), (75, 236, 211)),
    )
    if combo_count <= stops[0][0]:
        return stops[0][1], stops[0][2]
    for first, second in zip(stops, stops[1:]):
        if combo_count <= second[0]:
            phase = (combo_count - first[0]) / (second[0] - first[0])
            return interpolate_color(first[1], second[1], phase), interpolate_color(first[2], second[2], phase)
    return stops[-1][1], stops[-1][2]

@lru_cache(maxsize=384)
def cached_text(font, text, color):
    return font.render(text, True, color)


def draw_styled_text(surface, text, font, center_x, center_y, text_color, shadow_color=(0, 0, 0), scale=1.0):
    base_img = cached_text(font, text, tuple(text_color))
    shadow_img = cached_text(font, text, tuple(shadow_color))
    if scale != 1.0:
        w = max(1, int(base_img.get_width() * scale))
        h = max(1, int(base_img.get_height() * scale))
        base_img = pygame.transform.smoothscale(base_img, (w, h))
        shadow_img = pygame.transform.smoothscale(shadow_img, (w, h))
    rect = base_img.get_rect(center=(center_x, center_y))
    shadow_rect = shadow_img.get_rect(center=(center_x + 2, center_y + 2))
    surface.blit(shadow_img, shadow_rect)
    surface.blit(base_img, rect)


def is_all_perfect(total, perfect, great, miss):
    """Count every sustain head, body tick and tail; empty charts cannot earn AP."""
    return total > 0 and perfect == total and great == 0 and miss == 0


def prism_color(position):
    palette = ((111, 242, 255), (171, 150, 255), (255, 137, 212),
               (255, 231, 147), (134, 255, 220))
    position = (position % 1.0) * len(palette)
    index = int(position)
    return interpolate_color(palette[index], palette[(index + 1) % len(palette)], position - index)


@lru_cache(maxsize=96)
def prismatic_text_image(font, text, frame):
    mask = cached_text(font, text, (255, 255, 255))
    width, height = mask.get_size()
    image = pygame.Surface((width, height), pygame.SRCALPHA)
    for x in range(0, width, 3):
        pygame.draw.rect(image, (*prism_color(x / max(1, width) + frame / 60.0), 255),
                         (x, 0, 3, height))
    image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return image


def draw_prismatic_text(surface, text, font, center_x, center_y, scale=1.0):
    now = time.perf_counter()
    image = prismatic_text_image(font, text, int(now * 20) % 60)
    if scale != 1.0:
        image = pygame.transform.smoothscale(image, (max(1, int(image.get_width() * scale)),
                                                    max(1, int(image.get_height() * scale))))
    rect = image.get_rect(center=(center_x, center_y))
    glow = image.copy()
    glow.set_alpha(int(40 + 15 * math.sin(now * 3)))
    for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-2, -2), (2, -2), (-2, 2), (2, 2)):
        surface.blit(glow, rect.move(dx, dy))
    surface.blit(image, rect)

def draw_gradient_note(surface, lane, p_top, p_bot, color_top, color_bot, width_scale=0.44, steps=8):
    """Compatibility entry point: cap thickness no longer encodes a time span."""
    note_renderer.head(surface, lane, (p_top + p_bot) / 2, color_top, color_bot, width_scale)


def draw_flick_note(surface, lane, progress):
    """Pink glass and contrast-backed chevrons remain independent of combo tint."""
    note_renderer.head(surface, lane, progress, (255, 206, 234), (249, 65, 143), flick=True)

# ---------------------------------------------------------
# 4. 곡 데이터 (난이도 이름 적용) 및 로컬 기록 저장소
# ---------------------------------------------------------
MAP_LIST = [
    {"title": "나다움", "song": "나다움", "level": 1, "bpm": 165, "offset": 0.0, "duration": 91.0, "audio": "나다움.mp4", "colors": ((15, 35, 25), (10, 50, 40), (5, 20, 15)), "accent": (100, 255, 180)},
    {"title": "숙명", "song": "숙명", "level": 2, "bpm": 164, "offset": 0.0, "duration": 87.0, "audio": "숙명.mp4", "colors": ((25, 20, 40), (40, 30, 60), (10, 10, 25)), "accent": (180, 150, 255)},
    {"title": "이단의 스타", "song": "이단의 스타", "level": 3, "bpm": 98, "offset": 0.0, "duration": 92.0, "audio": "이단의 스타.mp4", "colors": ((50, 15, 25), (60, 25, 20), (20, 5, 10)), "accent": (255, 120, 80)},
    {"title": "Cry Baby", "song": "Cry Baby", "level": 4, "bpm": 200, "offset": 0.0, "duration": 95.0, "audio": "Cry Baby.mp4", "colors": ((10, 15, 35), (15, 25, 55), (5, 5, 15)), "accent": (80, 160, 255)},
    {"title": "Gone Angels", "song": "Gone Angels", "level": 5, "bpm": 129.146, "offset": 0.319, "duration": 73.0, "audio": "Gone Angels.mp4", "colors": ((22, 12, 38), (48, 24, 64), (12, 8, 25)), "accent": (207, 145, 255)},
    {"title": "Mixed Nuts", "song": "Mixed Nuts", "level": 6, "bpm": 150, "offset": 0.0, "duration": 96.0, "audio": "Mixed Nuts.mp4", "colors": ((10, 25, 40), (15, 40, 60), (5, 15, 25)), "accent": (100, 200, 255)},
    {"title": "Pretender", "song": "Pretender", "level": 7, "bpm": 92, "offset": 0.0, "duration": 138.0, "audio": "Pretender.mp4", "colors": ((30, 30, 10), (50, 50, 15), (15, 15, 5)), "accent": (255, 230, 50)},
    {"title": "Universe", "song": "Universe", "level": 10, "bpm": 186, "offset": 0.0, "duration": 128.0, "audio": "Universe.mp4", "colors": ((45, 10, 10), (65, 15, 15), (20, 5, 5)), "accent": (255, 60, 60)},
    {"title": "괴수의 꽃노래", "song": "괴수의 꽃노래", "level": 8, "bpm": 150, "offset": 0.0, "duration": 76.0, "audio": "괴수의 꽃노래.mp4", "colors": ((34, 12, 42), (76, 20, 48), (16, 8, 24)), "accent": (255, 122, 190)},
    {"title": "라일락", "song": "라일락", "level": 8, "bpm": 138, "offset": 0.0, "duration": 96.0, "audio": "라일락.mp4", "colors": ((28, 20, 52), (58, 34, 84), (13, 10, 35)), "accent": (194, 153, 255)},
    {"title": "최종화", "song": "최종화", "level": 9, "bpm": 130, "offset": 0.0, "duration": 98.0, "audio": "최종화.mp4", "colors": ((34, 28, 12), (82, 56, 22), (20, 12, 8)), "accent": (255, 208, 118)},
    {"title": "Ray", "song": "Ray", "level": 8, "bpm": 130, "offset": 0.0, "duration": 108.0, "audio": "Ray.mp4", "colors": ((10, 34, 50), (20, 60, 84), (5, 15, 33)), "accent": (98, 223, 255)},
    {"title": "White Noise", "song": "White Noise", "level": 9, "bpm": 143, "offset": 0.0, "duration": 100.0, "audio": "white-noise.mp3", "colors": ((14, 37, 45), (22, 78, 83), (7, 20, 36)), "accent": (100, 228, 239)},
    {"title": "괴물 Cover", "song": "괴물 Cover", "level": 9, "bpm": 170, "offset": 0.0, "duration": 76.0, "audio": "monster-cover.mp3", "colors": ((38, 24, 18), (83, 43, 25), (27, 14, 26)), "accent": (255, 153, 92)},
    {"title": "별자리가 될 수 있다면", "song": "별자리가 될 수 있다면", "level": 7, "bpm": 123, "offset": 0.0, "duration": 108.0, "audio": "seiza-ni-naretara.mp3", "colors": ((21, 30, 66), (45, 52, 120), (14, 21, 53)), "accent": (158, 181, 255)},
    {"title": "봄꿈", "song": "봄꿈", "level": 7, "bpm": 76, "offset": 0.0, "duration": 87.0, "audio": "springdream.mp3", "colors": ((47, 26, 46), (91, 45, 78), (27, 14, 35)), "accent": (255, 151, 201)},
    {"title": "사무라이 하트", "song": "사무라이 하트", "level": 8, "bpm": 113, "offset": 0.0, "duration": 89.0, "audio": "samurai-heart.mp3", "colors": ((27, 28, 37), (66, 50, 68), (17, 18, 33)), "accent": (255, 151, 183)},
    {"title": "소실", "song": "소실", "level": 33, "bpm": 240, "offset": 0.0, "duration": 139.0, "audio": "hatsune-miku-no-shoushitsu.mp3", "colors": ((21, 27, 67), (53, 34, 118), (14, 19, 50)), "accent": (136, 174, 255)},
    {"title": "여로", "song": "여로", "level": 8, "bpm": 123, "offset": 0.0, "duration": 94.0, "audio": "yeoro.mp3", "colors": ((14, 37, 59), (21, 76, 105), (8, 21, 43)), "accent": (89, 216, 255)},
    {"title": "I Wanna Be...", "song": "I Wanna Be...", "level": 9, "bpm": 126, "offset": 0.0, "duration": 94.0, "audio": "i-wanna-be.mp3", "colors": ((40, 19, 49), (85, 30, 72), (26, 10, 35)), "accent": (255, 118, 207)},
    {"title": "SPLASH FREE", "song": "SPLASH FREE", "level": 7, "bpm": 128.5, "offset": 0.0, "duration": 94.0, "audio": "splash-free.mp3", "colors": ((12, 36, 53), (17, 86, 114), (6, 24, 40)), "accent": (79, 215, 247)},
]

# ASCII-only, percent-encoded filenames avoid Unicode corruption when PyGBag
# converts Python strings into browser DOM URLs.
WEB_AUDIO_FILES = (
    "%EB%82%98%EB%8B%A4%EC%9B%80.mp4",
    "%EC%88%99%EB%AA%85.mp4",
    "%EC%9D%B4%EB%8B%A8%EC%9D%98%20%EC%8A%A4%ED%83%80.mp4",
    "Cry%20Baby.mp4",
    "Gone%20Angels.mp4",
    "Mixed%20Nuts.mp4",
    "Pretender.mp4",
    "Universe.mp4",
    "%EA%B4%B4%EC%88%98%EC%9D%98%20%EA%BD%83%EB%85%B8%EB%9E%98.mp4",
    "%EB%9D%BC%EC%9D%BC%EB%9D%BD.mp4",
    "%EC%B5%9C%EC%A2%85%ED%99%94.mp4",
    "Ray.mp4",
    "white-noise.mp3",
    "monster-cover.mp3",
    "seiza-ni-naretara.mp3",
    "springdream.mp3",
    "samurai-heart.mp3",
    "hatsune-miku-no-shoushitsu.mp3",
    "yeoro.mp3",
    "i-wanna-be.mp3",
    "splash-free.mp3",
)

SONGS_PER_PAGE = 12
FADE_OUT_SECONDS = 1.35

DIFFICULTIES = {"easy": "EASY", "hard": "HARD", "master": "MASTER"}

# 성취도를 위한 로컬 기록 딕셔너리
RECORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records_v2.json")

def load_records():
    records = {i: {"grade": "-", "fc": False} for i in range(len(MAP_LIST))}
    try:
        with open(RECORDS_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        for key, value in saved.items():
            idx = int(key)
            if idx in records and value.get("grade") in {"S", "A", "B", "C", "F", "-"}:
                records[idx] = {"grade": value["grade"], "fc": bool(value.get("fc", False))}
    except (OSError, ValueError, TypeError):
        pass
    return records

def save_records(records):
    try:
        with open(RECORDS_PATH, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in records.items()}, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

player_records = load_records()
CHARTS_PATH = os.path.join(GAME_DIR, "charts.json")
AUTO_CHARTS_PATH = os.path.join(GAME_DIR, "auto_charts.json")
_chart_meta_cache = {"mtime": None, "entries": {}}
_auto_chart_meta_cache = {"mtime": None, "entries": {}}

def song_audio_path(audio_name):
    name = os.path.basename(audio_name)
    stem, extension = os.path.splitext(name)
    audio_extension = ".mp3" if extension.lower() == ".mp3" else ".ogg"
    return os.path.join(GAME_DIR, "music", stem + audio_extension)

def audio_signature(path):
    stat = os.stat(path)
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}

def _read_json_entries(path, cache):
    try:
        mtime = os.path.getmtime(path)
        if mtime != cache["mtime"]:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cache["entries"] = data if isinstance(data, dict) else {}
            cache["mtime"] = mtime
        return cache["entries"]
    except (OSError, ValueError, TypeError):
        return {}

def get_manual_chart_entry(audio_name):
    stem = os.path.splitext(os.path.basename(audio_name))[0]
    return _read_json_entries(CHARTS_PATH, _chart_meta_cache).get(stem, {})

def get_auto_chart_entry(audio_name):
    stem = os.path.splitext(os.path.basename(audio_name))[0]
    entry = _read_json_entries(AUTO_CHARTS_PATH, _auto_chart_meta_cache).get(stem)
    if not isinstance(entry, dict):
        return None
    # Browser builds load their analyzed charts as immutable packaged data and
    # stream music from the Pages site, so the desktop OGG signature is absent.
    if sys.platform == "emscripten":
        return entry
    try:
        if entry.get("signature") != audio_signature(song_audio_path(audio_name)):
            return None
    except OSError:
        return None
    return entry

def chart_entry_for_difficulty(entry, difficulty):
    """Expose the selected tier while keeping the common BPM/phase metadata."""
    if not isinstance(entry, dict):
        return {}
    variants = entry.get("difficulty_charts", {})
    if isinstance(variants, dict) and isinstance(variants.get(difficulty), dict):
        return {**entry, **variants[difficulty]}
    # Older saves contain a single hand-authored chart. Keep them playable;
    # freshly analyzed songs carry all three variants in difficulty_charts.
    return entry

def save_auto_chart_entry(audio_name, entry, signature):
    global _auto_chart_meta_cache
    stem = os.path.splitext(os.path.basename(audio_name))[0]
    entries = dict(_read_json_entries(AUTO_CHARTS_PATH, _auto_chart_meta_cache))
    entries[stem] = {**entry, "signature": signature}
    temp_path = AUTO_CHARTS_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(temp_path, AUTO_CHARTS_PATH)
    _auto_chart_meta_cache = {"mtime": os.path.getmtime(AUTO_CHARTS_PATH), "entries": entries}

def get_saved_bpm(audio_name, default_bpm):
    """Show the BPM saved in Chart Studio, refreshing after an editor save."""
    automatic = get_auto_chart_entry(audio_name)
    if automatic:
        try:
            return float(automatic.get("bpm", default_bpm))
        except (TypeError, ValueError):
            pass
    manual = get_manual_chart_entry(audio_name)
    if isinstance(manual, dict) and manual.get("notes"):
        try:
            return float(manual.get("bpm", default_bpm))
        except (TypeError, ValueError):
            pass
    try:
        return float(manual.get("bpm", default_bpm)) if isinstance(manual, dict) else float(default_bpm)
    except (TypeError, ValueError):
        return float(default_bpm)

def load_authored_chart(audio_name, level, duration, default_bpm, default_offset, entry_override=None):
    """Load saved or audio-generated notes, clipping sustain tails to the song."""
    entry = entry_override if isinstance(entry_override, dict) else get_manual_chart_entry(audio_name)
    if not isinstance(entry, dict):
        entry = {}

    try:
        bpm = max(40.0, min(300.0, float(entry.get("bpm", default_bpm))))
        offset = max(-2.0, min(2.0, float(entry.get("offset", default_offset))))
        if not math.isfinite(bpm) or not math.isfinite(offset):
            raise ValueError("BPM and offset must be finite numbers")
    except (TypeError, ValueError):
        bpm, offset = float(default_bpm), float(default_offset)
    authored_notes = entry.get("notes", [])
    if not isinstance(authored_notes, list):
        authored_notes = []
    notes = []
    for item in authored_notes:
        try:
            kind = item.get("type", "TAP").upper()
            lane = int(item["lane"])
            start_beat = float(item["beat"])
            if kind not in {"TAP", "FLICK", "HOLD", "SLIDE"} or lane not in range(4):
                continue
            if not math.isfinite(start_beat):
                continue
            note = {"type": kind, "time": offset + start_beat * 60.0 / bpm,
                    "lane": lane, "hit": False, "active": False}
            if kind == "HOLD":
                end_time = offset + float(item["end_beat"]) * 60.0 / bpm
                if not math.isfinite(end_time): continue
                note["end_time"] = min(duration, end_time)
                if note["end_time"] <= note["time"]: continue
            elif kind == "SLIDE":
                end_time = offset + float(item["end_beat"]) * 60.0 / bpm
                if not math.isfinite(end_time): continue
                note["end_time"] = min(duration, end_time)
                note["end_lane"] = int(item["end_lane"])
                if note["end_time"] <= note["time"] or note["end_lane"] not in range(4): continue
            if -0.2 <= note["time"] < duration:
                notes.append(note)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    if not notes:
        return [], bpm, offset
    return resolve_note_overlaps(notes), bpm, offset

def generate_chart(level, duration, bpm, offset=0.0):
    notes = []
    rng = random.Random(2024 + level * 7919 + duration * 17 + bpm)
    beat = 60.0 / bpm
    subdivision = 1.0 if level <= 2 else 0.5 if level <= 6 else 0.25
    step = beat * subdivision
    # Start on a true beat line; the old fixed 2-second start shifted every song off-beat.
    chart_origin = offset
    current_time = chart_origin + beat * 4
    slot = 0
    previous_lane = rng.randrange(4)
    while current_time < duration:
        # Lower levels leave more musical breathing room; density rises with difficulty.
        chance = min(0.92, (0.42 + level * 0.11) * subdivision)
        if slot % 8 == 7:
            chance *= 0.55
        if rng.random() > chance:
            current_time += step
            slot += 1
            continue
        lane = (previous_lane + rng.choice([-2, -1, 1, 2])) % 4
        if slot % 4 == 0:
            lane = (slot // 4 + level) % 4
        previous_lane = lane
        note_type = rng.choices(["TAP", "HOLD", "SLIDE"], weights=[max(2, 12 - level), max(1, level * 0.22), max(1, level * 0.18)])[0]
        if note_type != "TAP" and current_time + beat * 4 >= duration:
            note_type = "TAP"
        if note_type == "TAP":
            notes.append({"type": "TAP", "time": current_time, "lane": lane, "hit": False})
            current_time += step
        elif note_type == "HOLD":
            hold_len = beat * rng.choice([2, 3, 4])
            notes.append({"type": "HOLD", "time": current_time, "end_time": current_time + hold_len, "lane": lane, "hit": False, "active": False})
            current_time += hold_len
        elif note_type == "SLIDE":
            end_lane = rng.choice([l for l in range(4) if l != lane])
            slide_len = beat * rng.choice([2, 3, 4])
            notes.append({"type": "SLIDE", "time": current_time, "end_time": current_time + slide_len, "lane": lane, "end_lane": end_lane, "hit": False, "active": False})
            current_time += slide_len
    slot = round((current_time - chart_origin) / step)
    return notes

# ---------------------------------------------------------
# 5. 게임 상태 & 변수
# ---------------------------------------------------------
state = "HOME"
current_map, current_map_idx = None, -1
selected_map_idx = 0
song_page = 0
selected_length = "verse"
current_length = "verse"
LENGTH_LABELS = {"verse": "1절", "full": "전체 곡"}
selected_difficulty = "hard"
current_difficulty = "hard"
SETTINGS_PATH = os.path.join(GAME_DIR, "settings.json")
SETTINGS_STORAGE_KEY = "rhythm-stage-settings-v1"


def load_flick_setting():
    try:
        if sys.platform == "emscripten":
            import platform as browser_platform
            raw = browser_platform.window.localStorage.getItem(SETTINGS_STORAGE_KEY)
            saved = json.loads(str(raw)) if raw else {}
        else:
            with open(SETTINGS_PATH, encoding="utf-8") as stream:
                saved = json.load(stream)
        value = saved.get("flick_enabled", True)
        return value if isinstance(value, bool) else True
    except Exception:
        return True


def set_flick_enabled(enabled):
    global flick_enabled
    flick_enabled = bool(enabled)
    saved = json.dumps({"flick_enabled": flick_enabled})
    try:
        if sys.platform == "emscripten":
            import platform as browser_platform
            browser_platform.window.localStorage.setItem(SETTINGS_STORAGE_KEY, saved)
        else:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as stream:
                stream.write(saved)
    except Exception:
        # Storage can be unavailable in a private browser; this session still works.
        pass


def chart_with_flick_setting(notes, enabled):
    return [{**note, "type": "TAP" if note["type"] == "FLICK" and not enabled else note["type"]}
            for note in notes]


def change_pause_flick():
    global current_flick_enabled
    if state != "PAUSED":
        return
    set_flick_enabled(not current_flick_enabled)
    current_flick_enabled = flick_enabled
    for note in chart:
        if not note["hit"] and note.get("authored_type") == "FLICK":
            note["type"] = "FLICK" if current_flick_enabled else "TAP"
    clear_game_inputs()


flick_enabled = load_flick_setting()
current_flick_enabled = True
practice_mode = False
current_bpm = 120.0
current_offset = 0.0
current_chart_source = "AUTO CHART"
home_notice = ""
home_notice_until = 0.0
chart = []
score = 0
combo, max_combo, total_notes, hit_score = 0, 0, 0, 0
hp = 100.0 
particles = []
audio_element = None
music_volume = 0.8
music_fade_gain = 1.0
auto_analysis_job = None
audio_ended_at = None
ready_start_time = 0.0
clear_started_at = None
clear_backdrop = None
AP_HOLD_SECONDS = 1.25
AP_FADE_SECONDS = 0.85
clear_award_surface = pygame.Surface((SCREEN_WIDTH, 160), pygame.SRCALPHA)
ready_count_in_duration = 2.0
music_scheduled_start = None
music_load_job = None
music_load_lock = threading.Lock() if sys.platform != "emscripten" else None
active_chart_notes = []
next_chart_index = 0

# 판정 횟수 카운터
perfect_count, great_count, miss_count = 0, 0, 0

BASE_APPROACH_TIME = 0.55
NOTE_SPEED_LEVELS = (0.75, 0.9, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0)
note_speed_index = 2
APPROACH_TIME = BASE_APPROACH_TIME / NOTE_SPEED_LEVELS[note_speed_index]
PERFECT_TIME = 0.07
GREAT_TIME = 0.15

active_touches = {}
key_lanes_down = set()
KEY_TO_LANE = {pygame.K_d: 0, pygame.K_f: 1, pygame.K_j: 2, pygame.K_k: 3}
CODE_TO_LANE = {"KeyD": 0, "KeyF": 1, "KeyJ": 2, "KeyK": 3}
flick_keyboard = KeyboardFlickInput()
flick_touch = TouchFlickInput()


def touch_lane(x):
    left = CENTER_X - TRACK_BOTTOM_W / 2
    if left <= x <= left + TRACK_BOTTOM_W:
        return min(3, max(0, int((x-left) / (TRACK_BOTTOM_W/4))))
    return None


def clear_game_inputs():
    key_lanes_down.clear()
    active_touches.clear()
    flick_keyboard.reset()
    flick_touch.reset()
    if audio_element is not None:
        audio_element.clearInput()


def collect_flick_intents(events, play_time, sample_wall_time):
    """Translate native/DOM edges to one song clock before recognizing gestures."""
    timed = [(direct if direct is not None else play_time-max(0, sample_wall_time-wall),
              kind, action, payload) for wall, direct, kind, action, payload in events]
    intents = []
    for when, kind, action, payload in sorted(timed, key=lambda row: row[0]):
        if kind == "lane":
            method = flick_keyboard.lane_down if action == "down" else flick_keyboard.lane_up
            intents.extend(method(payload, when))
        elif kind == "space":
            method = flick_keyboard.space_down if action == "down" else flick_keyboard.space_up
            intents.extend(method(when))
        elif kind == "pointer":
            pointer, x, y = payload
            lane = touch_lane(x)
            if action == "down":
                if lane is not None and y >= TRACK_TOP_Y:
                    intents.extend(flick_touch.begin(pointer, x, y, when, lane))
            elif action in ("move", "up"):
                intents.extend(flick_touch.move(pointer, x, y, when, lane))
            if action in ("up", "cancel"):
                flick_touch.end(pointer)
    return intents
combo_scale = 1.0
feedback_scale = 1.0
last_feedback = ""
last_feedback_color = (255, 255, 255)
feedback_time = 0
pause_start_time = 0

def get_grade(accuracy):
    if accuracy >= 95: return "S", (255, 215, 0)
    if accuracy >= 85: return "A", (0, 255, 120)
    if accuracy >= 75: return "B", (0, 200, 255)
    if accuracy >= 60: return "C", (255, 160, 0)
    return "F", (255, 60, 60)

def spawn_particles(x, y, color, count=16, power=1.0):
    for _ in range(min(count, max(0, 180 - len(particles)))):
        vx = random.uniform(-8 * power, 8 * power)
        vy = random.uniform(-10 * power, -2 * power)
        size = random.uniform(3, 9)
        particles.append([x, y, vx, vy, size, color])

def format_time(seconds):
    secs = max(0, int(seconds))
    return f"{secs // 60:02d}:{secs % 60:02d}"

def prepare_sustain_combo_ticks(notes, bpm):
    """Give holds/slides beat-synced sustain ticks for combo and accuracy."""
    interval = 30.0 / max(40.0, min(300.0, float(bpm)))  # two combo ticks per beat
    total = 0
    for note in notes:
        note["ticks_awarded"] = 0
        if note["type"] in {"HOLD", "SLIDE"}:
            note["active"] = False
            duration = max(0.0, note["end_time"] - note["time"])
            note["tick_interval"] = interval
            ticks = [note["time"]]
            tick_number = 1
            while tick_number * interval < duration - TAIL_EARLY_WINDOW - 1e-9:
                # The accepted head/tail windows must not overlap body ticks.
                if tick_number * interval >= HEAD_WINDOW + MIN_CONTINUOUS_HOLD:
                    ticks.append(note["time"] + tick_number * interval)
                tick_number += 1
            if duration > 1e-9:
                ticks.append(note["end_time"])
            note["tick_times"] = ticks
            note["tick_total"] = len(ticks)
            note["sustain_judge"] = SustainJudge(note, ticks)
            total += note["tick_total"]
        else:
            total += 1
    return total

def award_sustain_tick(note, grade="PERFECT"):
    global score, hit_score, combo, max_combo, hp, perfect_count, great_count
    global last_feedback, last_feedback_color, feedback_time, feedback_scale, combo_scale
    if note["ticks_awarded"] >= note["tick_total"]:
        return
    combo += 1
    max_combo = max(max_combo, combo)
    combo_scale = max(combo_scale, 1.18)
    note["ticks_awarded"] += 1
    if grade == "GREAT":
        score += 100 + combo * 5
        hit_score += 70
        great_count += 1
        hp = min(100.0, hp + 1.0)
        last_feedback, last_feedback_color = "GREAT", (0, 255, 255)
    else:
        score += 200 + combo * 10
        hit_score += 100
        perfect_count += 1
        hp = min(100.0, hp + 1.5)
        last_feedback, last_feedback_color = "PERFECT", (255, 215, 0)
    feedback_time = time.time()
    feedback_scale = 1.15

def apply_sustain_grades(note, grades):
    """Resolve every head, body and tail once; missed time cannot be reclaimed."""
    global miss_count, combo, hp, last_feedback, last_feedback_color
    global feedback_time, feedback_scale
    for grade in grades:
        if grade != "MISS":
            award_sustain_tick(note, grade)
            continue
        note["ticks_awarded"] += 1
        miss_count += 1
        combo = 0
        if not practice_mode:
            hp = max(0.0, hp - 0.8)
        last_feedback, last_feedback_color = "MISS", (255, 60, 60)
        feedback_time, feedback_scale = time.time(), 1.15


def physical_lanes():
    lanes = set(key_lanes_down)
    left = CENTER_X - TRACK_BOTTOM_W / 2
    for touch_x in active_touches.values():
        if left <= touch_x <= left + TRACK_BOTTOM_W:
            lanes.add(min(3, max(0, int((touch_x - left) // (TRACK_BOTTOM_W / 4)))))
    return lanes


def sustain_contacts():
    """Keep finger motion continuous without changing tap/flick lane selection."""
    contacts = set(key_lanes_down)
    left = CENTER_X - TRACK_BOTTOM_W / 2
    width = TRACK_BOTTOM_W / 4
    for pointer, x in active_touches.items():
        lane = touch_lane(x)
        if lane is None:
            continue
        if isinstance(pointer, tuple) and pointer[0] in ("pointer", "finger"):
            contacts.add(TouchContact(pointer, (x - left) / width - 0.5, lane))
        else:
            contacts.add(lane)
    return frozenset(contacts)


def update_sustain(note, play_time, initial_lanes, changes, triggered_lanes):
    judge = note["sustain_judge"]
    available = {lane for _, _, fresh in changes for lane in fresh}
    apply_sustain_grades(note, judge.update(play_time, initial_lanes, changes))
    note["active"] = judge.connected
    note["hit"] = judge.finished
    remaining = {lane for _, _, fresh in changes for lane in fresh}
    triggered_lanes.difference_update(available - remaining)
    return judge


def apply_music_volume():
    volume = max(0.0, min(1.0, music_volume * music_fade_gain))
    try:
        if audio_element is not None:
            audio_element.volume = volume
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(volume)
    except Exception:
        pass

def set_music_volume(value):
    global music_volume
    music_volume = max(0.0, min(1.0, float(value)))
    apply_music_volume()

def draw_volume_control(surface, slider_rect, mouse_pos, mouse_click, label="VOL"):
    if mouse_click and slider_rect.inflate(0, 14).collidepoint(mouse_pos):
        set_music_volume((mouse_pos[0] - slider_rect.x) / max(1, slider_rect.width))
    draw_styled_text(surface, label, font_small, slider_rect.x - 22, slider_rect.centery, (155, 172, 212))
    pygame.draw.rect(surface, (38, 47, 72), slider_rect, border_radius=5)
    fill_width = int(slider_rect.width * music_volume)
    if fill_width > 0:
        pygame.draw.rect(surface, (112, 196, 255), (slider_rect.x, slider_rect.y, fill_width, slider_rect.height), border_radius=5)
    pygame.draw.rect(surface, (220, 233, 255), slider_rect, width=1, border_radius=5)
    knob_x = slider_rect.x + fill_width
    pygame.draw.circle(surface, (250, 252, 255), (knob_x, slider_rect.centery), 6)
    draw_styled_text(surface, f"{round(music_volume * 100):d}%", font_small, slider_rect.right + 23, slider_rect.centery, (218, 228, 248))

def volume_slider_for_state(scene):
    if scene == "HOME":
        return pygame.Rect(657, 54, 93, 9)
    if scene == "PAUSED":
        return pygame.Rect(CENTER_X - 20, 270, 145, 10)
    return None

def set_home_notice(message):
    global home_notice, home_notice_until
    home_notice = message
    home_notice_until = time.time() + 5.0

def adjust_note_speed(direction):
    global note_speed_index, APPROACH_TIME
    next_index = max(0, min(len(NOTE_SPEED_LEVELS) - 1, note_speed_index + direction))
    if next_index == note_speed_index:
        return
    note_speed_index = next_index
    speed = NOTE_SPEED_LEVELS[note_speed_index]
    APPROACH_TIME = BASE_APPROACH_TIME / speed
    set_home_notice(f"노트 낙하 속도: {speed:.2f}×")

def draw_button(surface, rect, label, accent=(112, 139, 255), active=False):
    fill = tuple(min(255, int(c * 1.22)) for c in accent) if active else (28, 34, 56)
    pygame.draw.rect(surface, fill, rect, border_radius=11)
    pygame.draw.rect(surface, accent, rect, width=2 if active else 1, border_radius=11)
    draw_styled_text(surface, label, font_small, rect.centerx, rect.centery, (245, 247, 255))

def draw_album_art(surface, rect, accent, index):
    pygame.draw.rect(surface, (18, 22, 39), rect, border_radius=14)
    art = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, max(50, int(rect.height * 0.48)))
    pygame.draw.rect(surface, (13, 17, 32), art, border_radius=10)
    cx, cy = art.center
    pulse = (index % 5) * 5
    pygame.draw.circle(surface, tuple(min(255, c + pulse) for c in accent), (cx, cy), max(14, art.height // 3), 2)
    pygame.draw.circle(surface, tuple(int(c * 0.55) for c in accent), (cx, cy), max(7, art.height // 5), 5)
    bars = [0.25, 0.48, 0.78, 0.56, 0.34, 0.68, 0.42]
    for j, ratio in enumerate(bars):
        x = art.x + 12 + j * ((art.width - 24) // len(bars))
        height = max(5, int((art.height - 18) * ratio))
        pygame.draw.rect(surface, accent, (x, art.bottom - 9 - height, 5, height), border_radius=3)
    pygame.draw.rect(surface, accent, rect, width=2, border_radius=14)

def song_duration(song, mode, entry=None):
    if mode == "verse":
        return song["duration"]
    entry = entry or get_auto_chart_entry(song["audio"]) or {}
    duration = float(entry.get("duration", song["duration"]))
    return duration if math.isfinite(duration) and duration > 0 else song["duration"]


def draw_home(mouse_pos, mouse_click):
    global selected_map_idx, selected_difficulty, selected_length, song_page
    screen.blit(default_bg_surface, (0, 0))
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (64, 77, 174, 32), (680, 80), 260)
    pygame.draw.circle(overlay, (34, 170, 181, 18), (50, 440), 220)
    screen.blit(overlay, (0, 0))

    pygame.draw.rect(screen, (12, 16, 31), (0, 0, SCREEN_WIDTH, 82))
    pygame.draw.line(screen, (63, 72, 105), (24, 81), (SCREEN_WIDTH - 24, 81), 1)
    draw_styled_text(screen, "RHYTHM", font_large, 105, 29, (240, 244, 255))
    draw_styled_text(screen, "STAGE", font_small, 47, 57, (121, 152, 255))
    draw_styled_text(screen, "SONG LIBRARY", font_small, 524, 31, (155, 172, 212))
    draw_styled_text(screen, f"{len(MAP_LIST):02d} TRACKS", font_small, 733, 31, (113, 220, 207))
    draw_volume_control(screen, volume_slider_for_state("HOME"), mouse_pos, mouse_click)
    speed_left = pygame.Rect(310, 46, 38, 30)
    speed_value = pygame.Rect(352, 46, 76, 30)
    speed_right = pygame.Rect(432, 46, 38, 30)
    draw_styled_text(screen, "NOTE SPEED", font_small, 260, 60, (155, 172, 212))
    for rect, label in ((speed_left, "-"), (speed_right, "+")):
        hovered = rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (47, 57, 86) if hovered else (25, 31, 52), rect, border_radius=7)
        pygame.draw.rect(screen, (102, 119, 166), rect, 1, border_radius=7)
        draw_styled_text(screen, label, font_med, rect.centerx, rect.centery - 1, (237, 242, 255))
    pygame.draw.rect(screen, (19, 25, 44), speed_value, border_radius=7)
    pygame.draw.rect(screen, (86, 103, 150), speed_value, 1, border_radius=7)
    speed = NOTE_SPEED_LEVELS[note_speed_index]
    draw_styled_text(screen, f"{speed:.2f}×", font_small, speed_value.centerx, speed_value.centery, (121, 220, 207))
    flick_button = pygame.Rect(480, 46, 138, 30)
    pygame.draw.rect(screen, (74, 31, 66) if flick_enabled else (25, 31, 52), flick_button, border_radius=7)
    pygame.draw.rect(screen, (244, 124, 188) if flick_enabled else (102, 119, 166), flick_button, 1, border_radius=7)
    draw_styled_text(screen, "플릭  ON" if flick_enabled else "플릭  OFF", font_small,
                     flick_button.centerx, flick_button.centery, (255, 185, 220) if flick_enabled else (171, 181, 209))

    hero = pygame.Rect(24, 101, 212, 286)
    pygame.draw.rect(screen, (17, 22, 41), hero, border_radius=18)
    pygame.draw.rect(screen, (45, 54, 83), hero, width=1, border_radius=18)
    selected = MAP_LIST[selected_map_idx]
    art_rect = pygame.Rect(hero.x + 13, hero.y + 13, hero.width - 26, 106)
    draw_album_art(screen, art_rect, selected["accent"], selected_map_idx)
    draw_styled_text(screen, "FEATURED CHART", font_small, hero.centerx, hero.y + 139, (142, 156, 194))
    title_font = font_med if len(selected["song"]) < 17 else font_small
    draw_styled_text(screen, selected["song"], title_font, hero.centerx, hero.y + 164, (248, 249, 255))
    selected_bpm = get_saved_bpm(selected["audio"], selected["bpm"])
    draw_styled_text(screen, f"{DIFFICULTIES[selected_difficulty]}   ·   {selected_bpm:g} BPM", font_small, hero.centerx, hero.y + 194, selected["accent"])
    draw_styled_text(screen, f"{format_time(song_duration(selected, selected_length))}   ·   4 LANES", font_small, hero.centerx, hero.y + 218, (171, 181, 209))
    draw_styled_text(screen, "SELECT CHART LEVEL", font_small, hero.centerx, hero.y + 238, (142, 156, 194))
    difficulty_buttons = {}
    button_y = hero.y + 250
    button_x = hero.x + 13
    for index, difficulty in enumerate(("easy", "hard", "master")):
        rect = pygame.Rect(button_x + index * 62, button_y, 58, 25)
        difficulty_buttons[difficulty] = rect
        active = difficulty == selected_difficulty
        fill = selected["accent"] if active else (25, 31, 52)
        ink = (14, 18, 33) if active else (184, 195, 222)
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, (235, 240, 255) if active else (61, 72, 104), rect, 1, border_radius=8)
        draw_styled_text(screen, DIFFICULTIES[difficulty], font_small, rect.centerx, rect.centery, ink)

    length_buttons = {}
    for index, mode in enumerate(("verse", "full")):
        rect = pygame.Rect(24 + index * 99, 409, 94, 38)
        length_buttons[mode] = rect
        active = mode == selected_length
        pygame.draw.rect(screen, (53, 73, 105) if active else (22, 28, 47), rect, border_radius=9)
        pygame.draw.rect(screen, selected["accent"] if active else (60, 72, 99), rect, 2 if active else 1, border_radius=9)
        draw_styled_text(screen, LENGTH_LABELS[mode], font_small, rect.centerx, rect.centery,
                         (241, 247, 255) if active else (158, 173, 201))

    grid_x, grid_y = 252, 102
    card_w, card_h, gap_x, gap_y = 126, 87, 7, 8
    page_count = max(1, (len(MAP_LIST) + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE)
    previous_page_button = pygame.Rect(650, 386, 39, 18)
    next_page_button = pygame.Rect(739, 386, 39, 18)
    if mouse_click and previous_page_button.collidepoint(mouse_pos) and song_page > 0:
        song_page -= 1
        selected_map_idx = song_page * SONGS_PER_PAGE
        return None
    if mouse_click and next_page_button.collidepoint(mouse_pos) and song_page + 1 < page_count:
        song_page += 1
        selected_map_idx = song_page * SONGS_PER_PAGE
        return None

    first_song = song_page * SONGS_PER_PAGE
    for i in range(first_song, min(first_song + SONGS_PER_PAGE, len(MAP_LIST))):
        song = MAP_LIST[i]
        local_index = i - first_song
        col, row = local_index % 4, local_index // 4
        rect = pygame.Rect(grid_x + col * (card_w + gap_x), grid_y + row * (card_h + gap_y), card_w, card_h)
        hovered = rect.collidepoint(mouse_pos)
        if mouse_click and hovered:
            selected_map_idx = i
            selected = song
        draw_album_art(screen, rect, song["accent"], i)
        pygame.draw.rect(screen, (22, 27, 46), (rect.x + 5, rect.bottom - 32, rect.width - 10, 24), border_radius=6)
        compact_title = song["song"]
        if font_small.size(compact_title)[0] > rect.width - 20:
            while compact_title and font_small.size(compact_title + "…")[0] > rect.width - 20:
                compact_title = compact_title[:-1]
            compact_title += "…"
        draw_styled_text(screen, compact_title, font_small, rect.centerx, rect.bottom - 20, (245, 247, 255))
        if i == selected_map_idx:
            pygame.draw.rect(screen, (241, 244, 255), rect, width=2, border_radius=14)

    if page_count > 1:
        for rect, label, enabled in (
            (previous_page_button, -1, song_page > 0),
            (next_page_button, 1, song_page + 1 < page_count),
        ):
            pygame.draw.rect(screen, (33, 43, 69) if enabled else (23, 28, 44), rect, border_radius=6)
            pygame.draw.rect(screen, (87, 109, 158) if enabled else (48, 55, 77), rect, 1, border_radius=6)
            # Draw chevrons directly: independent of bundled font glyph coverage.
            cx, cy = rect.center
            pygame.draw.lines(screen, (236, 242, 255) if enabled else (98, 105, 126), False,
                              [(cx - label * 3, cy - 5), (cx + label * 3, cy),
                               (cx - label * 3, cy + 5)], 2)
        draw_styled_text(screen, f"{song_page + 1} / {page_count}", font_small, 714, 395, (171, 181, 209))

    # Controls are deliberately separated from song cards, like a web player action bar.
    if sys.platform == "emscripten":
        play_button = pygame.Rect(255, 406, 128, 44)
        practice_button = pygame.Rect(394, 406, 150, 44)
        editor_button = None
    else:
        play_button = pygame.Rect(226, 406, 128, 44)
        practice_button = pygame.Rect(365, 406, 150, 44)
        editor_button = pygame.Rect(526, 406, 166, 44)
    draw_button(screen, play_button, "PLAY CHART", selected["accent"], True)
    draw_button(screen, practice_button, "PRACTICE", (69, 197, 161))
    if editor_button is not None:
        draw_button(screen, editor_button, "CHART STUDIO", (154, 135, 255))
    draw_styled_text(screen, "D F J K  ·  플릭: 레인 키 + SPACE / 위로 스와이프  ·  볼륨 - / +", font_small, SCREEN_WIDTH // 2, 466, (174, 180, 205))
    if home_notice and time.time() < home_notice_until:
        notice_box = pygame.Rect(253, 386, 390, 18)
        pygame.draw.rect(screen, (25, 39, 58), notice_box, border_radius=8)
        pygame.draw.rect(screen, (91, 129, 184), notice_box, 1, border_radius=8)
        draw_styled_text(screen, home_notice, font_small, notice_box.centerx, notice_box.centery, (218, 235, 255))

    if mouse_click:
        if flick_button.collidepoint(mouse_pos):
            set_flick_enabled(not flick_enabled)
            return None
        if speed_left.collidepoint(mouse_pos):
            adjust_note_speed(-1)
            return None
        if speed_right.collidepoint(mouse_pos):
            adjust_note_speed(1)
            return None
        for mode, rect in length_buttons.items():
            if rect.collidepoint(mouse_pos):
                selected_length = mode
                return None
        for difficulty, rect in difficulty_buttons.items():
            if rect.collidepoint(mouse_pos):
                selected_difficulty = difficulty
                return None
        if play_button.collidepoint(mouse_pos): return "play"
        if practice_button.collidepoint(mouse_pos): return "practice"
        if editor_button is not None and editor_button.collidepoint(mouse_pos): return "editor"
    return None

def _analyze_for_game(job, audio_path, difficulty):
    try:
        # Tempo establishes the time scale; melody attacks and pitch movement
        # decide which moments become notes in each difficulty tier.
        job["result"] = generate_auto_chart_levels(audio_path, preferred_bpm=None)
        job["signature"] = audio_signature(audio_path)
        variants = job["result"].get("difficulty_charts", {})
        if any(not variants.get(name, {}).get("notes") for name in DIFFICULTIES):
            raise ValueError("멜로디 노트를 찾지 못했습니다. 오디오 파일을 확인해 주세요.")
    except Exception as exc:
        job["error"] = str(exc)
    finally:
        job["done"] = True

def request_game_start(m_idx, practice=False, difficulty=None):
    global auto_analysis_job, state
    difficulty = difficulty or selected_difficulty
    song = MAP_LIST[m_idx]
    automatic = get_auto_chart_entry(song["audio"])
    if automatic and (automatic.get("notes") or automatic.get("difficulty_charts")):
        start_game(m_idx, practice=practice, chart_entry=automatic,
                   chart_source="MELODY CHART", difficulty=difficulty)
        return
    manual = get_manual_chart_entry(song["audio"])
    if isinstance(manual, dict) and manual.get("notes"):
        start_game(m_idx, practice=practice, chart_entry=manual,
                   chart_source="SAVED CHART", difficulty=difficulty)
        return
    if auto_analysis_job is not None:
        if auto_analysis_job.get("map_idx") == m_idx:
            auto_analysis_job["practice"] = practice
            auto_analysis_job["difficulty"] = difficulty
            auto_analysis_job["pending"] = True
        else:
            set_home_notice("다른 곡을 분석 중입니다. 잠시 후 다시 눌러 주세요.")
        return
    audio_path = song_audio_path(song["audio"])
    if not os.path.isfile(audio_path):
        set_home_notice(f"오디오 파일이 없습니다: {os.path.basename(audio_path)}")
        return
    if sys.platform == "emscripten":
        set_home_notice("이 곡의 웹 차트 데이터가 없습니다. 배포 파일을 확인해 주세요.")
        return
    stop_music()
    auto_analysis_job = {"done": False, "result": None, "error": None,
                         "map_idx": m_idx, "practice": practice, "difficulty": difficulty,
                         "pending": True}
    state = "ANALYZING"
    threading.Thread(target=_analyze_for_game, args=(auto_analysis_job, audio_path, difficulty), daemon=True).start()

def draw_analysis_screen():
    screen.blit(default_bg_surface, (0, 0))
    song = MAP_LIST[auto_analysis_job["map_idx"]] if auto_analysis_job else MAP_LIST[selected_map_idx]
    center = (CENTER_X, 206)
    pulse = 0.5 + 0.5 * math.sin(time.perf_counter() * 3.4)
    pygame.draw.circle(screen, (34, 42, 76), center, 56, 2)
    pygame.draw.arc(screen, song["accent"], pygame.Rect(center[0] - 56, center[1] - 56, 112, 112),
                    time.perf_counter() % (math.pi * 2), time.perf_counter() % (math.pi * 2) + 2.2 + pulse, 5)
    draw_styled_text(screen, "AUDIO → MELODY DETECTION → AUTO CHART", font_small, CENTER_X, 90, (177, 191, 223))
    draw_styled_text(screen, song["song"], font_large, CENTER_X, 142, (248, 249, 255))
    draw_styled_text(screen, "음의 시작과 높낮이를 읽어 3단계 차트를 만들고 있어요", font_med, CENTER_X, 284, (214, 222, 245))
    draw_styled_text(screen, "첫 분석은 잠시 걸릴 수 있습니다 · ESC를 누르면 취소됩니다", font_small, CENTER_X, 323, (137, 151, 184))
    draw_styled_text(screen, f"선택 난이도  {DIFFICULTIES.get(auto_analysis_job.get('difficulty', 'hard'), 'HARD')}  ·  BPM도 함께 분석합니다", font_small, CENTER_X, 350, song["accent"])
    progress_w = 300
    pygame.draw.rect(screen, (22, 28, 49), (CENTER_X - progress_w // 2, 390, progress_w, 7), border_radius=4)
    sweep = int(progress_w * (0.25 + pulse * 0.3))
    pygame.draw.rect(screen, song["accent"], (CENTER_X - progress_w // 2, 390, sweep, 7), border_radius=4)

def start_game(m_idx, practice=False, chart_entry=None, chart_source="SAVED CHART", difficulty=None):
    global current_map, current_map_idx, chart, total_notes, score, combo, max_combo, hit_score, hp
    global perfect_count, great_count, miss_count, game_start_time, current_bg_surface, state, audio_ended_at
    global practice_mode, current_bpm, current_offset, current_chart_source, current_difficulty
    global ready_start_time, ready_count_in_duration, music_scheduled_start, current_length
    global active_chart_notes, next_chart_index
    global current_flick_enabled
    global clear_started_at, clear_backdrop

    clear_started_at, clear_backdrop = None, None
    
    current_map_idx = m_idx
    current_map = dict(MAP_LIST[m_idx])
    current_length = selected_length
    current_map["duration"] = song_duration(current_map, current_length, chart_entry)
    current_difficulty = difficulty or selected_difficulty
    chart_entry = chart_entry_for_difficulty(chart_entry, current_difficulty)
    chart, current_bpm, current_offset = load_authored_chart(
        current_map["audio"], current_map["level"], current_map["duration"],
        current_map["bpm"], current_map["offset"], entry_override=chart_entry)
    current_flick_enabled = flick_enabled
    for note in chart:
        if note["type"] == "FLICK":
            note["authored_type"] = "FLICK"
    chart = chart_with_flick_setting(chart, current_flick_enabled)
    if not chart:
        state = "HOME"
        set_home_notice("자동채보가 아직 준비되지 않았습니다. 다시 시작해 주세요.")
        return
    practice_mode = practice
    current_chart_source = chart_source
    total_notes = prepare_sustain_combo_ticks(chart, current_bpm)
    score, combo, max_combo, hit_score = 0, 0, 0, 0
    perfect_count, great_count, miss_count = 0, 0, 0
    hp = 100.0
    particles.clear()
    current_bg_surface = generate_bg_surface(current_map["colors"], current_map["accent"])
    stop_music()
    ready_start_time = time.perf_counter()
    ready_count_in_duration = min(4.5, max(1.0, 240.0 / max(40.0, current_bpm)))
    audio_ended_at = None
    music_scheduled_start = None
    active_chart_notes = []
    next_chart_index = 0
    prepare_music(current_map["audio"])
    state = "LOADING"
    active_touches.clear()
    key_lanes_down.clear()

def draw_ready_screen():
    """Show a beat-paced count-in without drawing or advancing chart notes."""
    screen.blit(current_bg_surface, (0, 0))
    elapsed = max(0.0, time.perf_counter() - ready_start_time)
    beat_length = ready_count_in_duration / 4.0
    count = max(1, 4 - min(3, int(elapsed / beat_length)))
    beat_phase = (elapsed % beat_length) / beat_length
    pulse = 0.5 + 0.5 * math.sin(beat_phase * math.pi)
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((3, 6, 18, 148))
    screen.blit(overlay, (0, 0))
    draw_styled_text(screen, current_map["song"], font_large, CENTER_X, 112, (246, 248, 255))
    draw_styled_text(screen, f"{DIFFICULTIES[current_difficulty]}  ·  {LENGTH_LABELS[current_length]}  ·  {current_bpm:.1f} BPM", font_small, CENTER_X, 150, current_map["accent"])
    ring = pygame.Rect(CENTER_X - 74, 188, 148, 148)
    pygame.draw.circle(screen, (31, 40, 67), ring.center, 70, 2)
    pygame.draw.arc(screen, current_map["accent"], ring,
                    -math.pi / 2, -math.pi / 2 + max(0.1, pulse * math.pi * 1.7), 5)
    draw_styled_text(screen, str(count), font_combo_num, CENTER_X, ring.centery, (249, 250, 255), scale=1.0 + pulse * 0.06)
    draw_styled_text(screen, "GET READY", font_med, CENTER_X, 365, (220, 229, 248))
    ready_tip = ("분홍 화살표: 레인 키를 누른 채 SPACE / 터치는 위로" if current_flick_enabled
                 else "플릭 OFF · 모든 플릭을 같은 박자의 일반 탭으로 연주합니다") if current_difficulty == "master" else "음악 준비 완료 · 판정선에 맞춰 연주하세요"
    draw_styled_text(screen, ready_tip, font_small, CENTER_X, 396, (231, 163, 204) if current_difficulty == "master" else (151, 166, 199))
    if practice_mode:
        draw_styled_text(screen, "PRACTICE · NO FAIL", font_small, CENTER_X, 431, (120, 228, 195))
    draw_styled_text(screen, "ESC  ·  취소", font_small, CENTER_X, 462, (112, 126, 158))

def begin_play():
    global game_start_time, audio_ended_at, state, music_scheduled_start
    if current_map is None:
        state = "HOME"
        return
    clear_game_inputs()
    # Give the first notes a short silent approach so the playfield is empty
    # when gameplay opens. The song begins exactly when the chart reaches t=0.
    lead_in = max(0.45, APPROACH_TIME * 2.0)
    game_start_time = time.perf_counter() + lead_in
    music_scheduled_start = game_start_time
    if audio_element is not None:
        audio_element.volume = music_volume
        if not audio_element.play(lead_in):
            state = "LOADING"
            return
    audio_ended_at = None
    state = "PLAY"
    if audio_element is not None:
        audio_element.setInputEnabled(True)

def finish_auto_analysis():
    global auto_analysis_job, state
    job = auto_analysis_job
    auto_analysis_job = None
    if not job:
        return
    if job.get("error"):
        if job.get("pending"):
            set_home_notice(f"자동채보 실패: {job['error']}")
            state = "HOME"
        return
    song = MAP_LIST[job["map_idx"]]
    result = job["result"]
    cache_entry = {key: result[key] for key in (
        "bpm", "offset", "confidence", "alternatives", "notes", "type_counts",
        "difficulty_charts", "duration", "onset_count", "selected_count") if key in result}
    try:
        save_auto_chart_entry(song["audio"], cache_entry, job["signature"])
    except OSError as exc:
        print(f"자동채보 캐시를 저장하지 못했습니다: {exc}")
    if job.get("pending"):
        start_game(job["map_idx"], practice=job["practice"], chart_entry=cache_entry,
                   chart_source="MELODY CHART", difficulty=job.get("difficulty", selected_difficulty))
        counts = result.get("type_counts", {})
        set_home_notice(f"자동채보 완료 · {result['bpm']:.2f} BPM · 노트 {len(result['notes'])}개")

def _load_native_music(job, path):
    # SDL's streaming decoder is opened before the count-in, never on frame zero.
    try:
        with music_load_lock:
            if job is not music_load_job:
                return
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
        job["done"] = True
    except Exception as exc:
        job["error"] = str(exc)
        job["done"] = True


def prepare_music(path):
    global audio_element, music_load_job, music_fade_gain
    music_fade_gain = 1.0
    music_load_job = {"done": False, "error": ""}
    if sys.platform == "emscripten":
        try:
            import platform as browser_platform
            audio_element = browser_platform.window.rhythmAudio
            audio_element.prepare("music/" + WEB_AUDIO_FILES[current_map_idx])
        except Exception as exc:
            music_load_job.update(done=True, error=str(exc))
    else:
        threading.Thread(target=_load_native_music,
                         args=(music_load_job, song_audio_path(path)), daemon=True).start()


def draw_loading_screen(mouse_pos, mouse_click):
    global state, ready_start_time, chart, total_notes
    screen.blit(current_bg_surface, (0, 0))
    ready = False
    error = music_load_job.get("error", "") if music_load_job else ""
    progress = 0.0
    unlocked = True
    if audio_element is not None and not error:
        status = str(audio_element.status)
        error = str(audio_element.error) if status == "error" else ""
        ready = status == "ready"
        progress = float(audio_element.progress)
        unlocked = bool(audio_element.unlocked)
    elif music_load_job and not error:
        ready = music_load_job["done"]
    draw_styled_text(screen, current_map["song"], font_large, CENTER_X, 125, (248, 249, 255))
    label = "곡을 준비하는 중" if not error else "곡을 불러오지 못했습니다"
    if ready and not unlocked:
        label = "화면을 눌러 음악을 시작해 주세요"
    draw_styled_text(screen, label, font_med, CENTER_X, 210, (224, 234, 252))
    detail = "다운로드와 오디오 준비가 끝나면 카운트다운을 시작합니다"
    if error:
        detail = error[:65]
    draw_styled_text(screen, detail, font_small, CENTER_X, 250, (154, 177, 212))
    pygame.draw.rect(screen, (24, 31, 53), (240, 292, 320, 8), border_radius=4)
    if not error:
        width = int(320 * progress) if progress else int(60 + 30 * math.sin(time.perf_counter() * 3))
        pygame.draw.rect(screen, current_map["accent"], (240, 292, width, 8), border_radius=4)
    back = pygame.Rect(245, 345, 145, 45)
    retry = pygame.Rect(410, 345, 145, 45)
    draw_button(screen, back, "메뉴로", (85, 105, 150))
    if error:
        draw_button(screen, retry, "다시 시도", current_map["accent"])
    if mouse_click and back.collidepoint(mouse_pos):
        if audio_element is not None:
            audio_element.cancel()
        stop_music()
        state = "HOME"
        return
    if mouse_click and error and retry.collidepoint(mouse_pos):
        prepare_music(current_map["audio"])
        return
    if ready and unlocked and not error:
        if audio_element is not None:
            # Encoded container lengths may differ slightly from analysis PCM.
            actual_duration = float(audio_element.duration)
            if 0 < actual_duration < current_map["duration"]:
                current_map["duration"] = actual_duration
                chart = [note for note in chart if note["time"] < actual_duration]
                for note in chart:
                    if "end_time" in note:
                        note["end_time"] = min(note["end_time"], actual_duration)
                total_notes = prepare_sustain_combo_ticks(chart, current_bpm)
        ready_start_time = time.perf_counter()
        state = "READY"


def start_music(path):
    global music_fade_gain
    music_fade_gain = 1.0
    # Web playback was already scheduled on the audio clock in begin_play().
    if audio_element is not None:
        return True
    try:
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play()
        return True
    except pygame.error as exc:
        set_home_notice(f"음악 재생 실패: {exc}")
        return False


def pause_music():
    global audio_element
    clear_game_inputs()
    if audio_element is not None:
        audio_element.setInputEnabled(False)
    try:
        if audio_element is not None: audio_element.pause()
        else: pygame.mixer.music.pause()
    except Exception:
        pass

def resume_music():
    clear_game_inputs()
    try:
        if audio_element is not None:
            audio_element.play()
            audio_element.setInputEnabled(True)
        else: pygame.mixer.music.unpause()
    except Exception:
        pass

def stop_music():
    clear_game_inputs()
    if audio_element is not None:
        audio_element.setInputEnabled(False)
    try:
        if audio_element is not None: audio_element.pause()
        pygame.mixer.music.stop()
    except Exception:
        pass


def finish_song():
    """Record the completed run once, then show its optional clear animation."""
    global state, clear_started_at, clear_backdrop
    stop_music()
    accuracy = hit_score / total_notes if total_notes > 0 else 0
    grade_str, _ = get_grade(accuracy)
    if not practice_mode:
        prev = player_records[current_map_idx]["grade"]
        ranks = ["S", "A", "B", "C", "F", "-"]
        if ranks.index(grade_str) < ranks.index(prev):
            player_records[current_map_idx]["grade"] = grade_str
        if total_notes > 0 and miss_count == 0 and perfect_count + great_count == total_notes:
            player_records[current_map_idx]["fc"] = True
        save_records(player_records)
    clear_started_at, clear_backdrop = None, None
    if is_all_perfect(total_notes, perfect_count, great_count, miss_count):
        clear_started_at = time.perf_counter()
        clear_backdrop = current_bg_surface.copy()
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        veil.fill((8, 12, 25))
        veil.set_alpha(90)
        clear_backdrop.blit(veil, (0, 0))
        state = "CLEAR"
    else:
        state = "RESULT"


def draw_clear_celebration(surface):
    """Show AP once after song completion, then fade it into the results."""
    global state, clear_started_at, clear_backdrop
    elapsed = time.perf_counter() - clear_started_at if clear_started_at is not None else float("inf")
    if elapsed >= AP_HOLD_SECONDS + AP_FADE_SECONDS:
        state = "RESULT"
        clear_started_at, clear_backdrop = None, None
        draw_result_summary(surface)
        return
    surface.blit(clear_backdrop, (0, 0))
    remaining = 1.0 - max(0.0, elapsed - AP_HOLD_SECONDS) / AP_FADE_SECONDS
    alpha = round(255 * remaining * remaining * (3.0 - 2.0 * remaining))
    clear_award_surface.fill((0, 0, 0, 0))
    draw_prismatic_text(clear_award_surface, "ALL PERFECT", font_large, CENTER_X, 80, scale=1.45)
    for index in range(6):
        angle = elapsed * .6 + index * math.tau / 6
        x, y = CENTER_X + math.cos(angle) * 225, 80 + math.sin(angle) * 33
        tint = prism_color(index / 6 + elapsed / 3)
        radius = 2 + int((1 + math.sin(elapsed * 3 + index)) * 1.5)
        pygame.draw.line(clear_award_surface, tint, (x-radius, y), (x+radius, y), 2)
        pygame.draw.line(clear_award_surface, tint, (x, y-radius), (x, y+radius), 2)
    clear_award_surface.set_alpha(alpha)
    surface.blit(clear_award_surface, (0, SCREEN_HEIGHT // 2 - 80))


def draw_result_summary(surface):
    surface.blit(current_bg_surface, (0, 0))
    accuracy = hit_score / total_notes if total_notes > 0 else 0
    grade_str, grade_color = get_grade(accuracy)
    draw_styled_text(surface, current_map["song"], font_large, CENTER_X, 38, (255, 255, 255))
    draw_styled_text(surface, f"STAGE CLEAR!  ·  {LENGTH_LABELS[current_length]}  ·  {DIFFICULTIES[current_difficulty]}",
                     font_med, CENTER_X, 75, current_map["accent"])

    if is_all_perfect(total_notes, perfect_count, great_count, miss_count):
        draw_prismatic_text(surface, "ALL PERFECT", font_large, CENTER_X, 122)
    elif total_notes > 0 and miss_count == 0 and perfect_count + great_count == total_notes:
        draw_styled_text(surface, "FULL COMBO!", font_large, CENTER_X, 122,
                         (255, 215, 0), (120, 65, 20))
    if practice_mode:
        draw_styled_text(surface, "PRACTICE · RECORD NOT SAVED", font_small, CENTER_X, 159, (120, 228, 195))
    draw_styled_text(surface, f"GRADE: {grade_str}", font_large, CENTER_X, 198, grade_color)
    draw_styled_text(surface, f"최종 점수: {score:,}", font_med, CENTER_X, 238, (220, 220, 220))
    for label, count, y, color in (("PERFECT", perfect_count, 283, (255, 215, 0)),
                                   ("GREAT", great_count, 313, (0, 255, 255)),
                                   ("MISS", miss_count, 343, (255, 60, 60))):
        draw_styled_text(surface, f"{label} : {count}", font_med, CENTER_X - 105, y, color)
    draw_styled_text(surface, f"최대 콤보: {max_combo}", font_med, CENTER_X + 110, 298, (220, 220, 220))
    draw_styled_text(surface, f"정확도: {accuracy:.1f}%", font_med, CENTER_X + 110, 328, (220, 220, 220))

# ---------------------------------------------------------
# 6. 비동기 메인 루프 (Web/pygbag 전용)
# ---------------------------------------------------------
async def main():
    global state, current_map, current_map_idx, chart, score, combo, max_combo, total_notes, hit_score, hp, particles, key_lanes_down
    global perfect_count, great_count, miss_count, active_touches, combo_scale, feedback_scale
    global last_feedback, last_feedback_color, feedback_time, pause_start_time, game_start_time, current_bg_surface, audio_ended_at
    global music_fade_gain, music_scheduled_start, next_chart_index, active_chart_notes

    # 웹 로딩 시 폰트 파일이 비동기 준비될 수 있도록 0.1초 양보 대기
    await asyncio.sleep(0.1)

    running = True
    game_start_time = 0
    btn_pause = pygame.Rect(740, 15, 45, 35)

    while running:
        # Pygbag already yields to the browser scheduler; an SDL sleep blocks input.
        dt = clock.tick(0 if sys.platform == "emscripten" else 120) / 1000.0
        if auto_analysis_job is not None and auto_analysis_job.get("done"):
            finish_auto_analysis()
        mouse_click = False
        triggered_lanes = set()
        mouse_pos = pygame.mouse.get_pos()
        initial_lanes = sustain_contacts()
        event_contacts = initial_lanes
        event_lanes = physical_lanes()
        input_changes = []
        raw_tap_presses = []
        raw_flick_events = []
        web_key_input = audio_element is not None
        web_pointer_input = web_key_input and state == "PLAY"
        if web_key_input:
            # DOM timestamps preserve keyboard and every finger's motion even
            # when multiple events arrive during one slow Python frame.
            for event_data in json.loads(str(audio_element.drainInput())):
                if state != "PLAY":
                    continue
                received_at = time.perf_counter()
                kind, action = event_data[:2]
                song_time = float(event_data[-1])
                if kind == "key":
                    code = event_data[2]
                    if code == "Space":
                        raw_flick_events.append((received_at, song_time, "space", action, None))
                    elif code in CODE_TO_LANE:
                        lane = CODE_TO_LANE[code]
                        raw_flick_events.append((received_at, song_time, "lane", action, lane))
                        if action == "down":
                            if lane not in key_lanes_down:
                                triggered_lanes.add(lane)
                                raw_tap_presses.append((received_at, lane, song_time))
                            key_lanes_down.add(lane)
                        else:
                            key_lanes_down.discard(lane)
                else:
                    pointer, x, y = event_data[2:5]
                    pointer = ("pointer", pointer)
                    raw_flick_events.append((received_at, song_time, "pointer", action, (pointer, x, y)))
                    if action == "down":
                        mouse_click, mouse_pos = True, (x, y)
                        if y >= TRACK_TOP_Y:
                            active_touches[pointer] = x
                            lane = touch_lane(x)
                            if lane is not None:
                                triggered_lanes.add(lane)
                                raw_tap_presses.append((received_at, lane, song_time))
                    elif action == "move" and pointer in active_touches:
                        active_touches[pointer] = x
                    elif action in ("up", "cancel"):
                        active_touches.pop(pointer, None)
                lanes_now = physical_lanes()
                contacts_now = sustain_contacts()
                if contacts_now != event_contacts:
                    input_changes.append((received_at, contacts_now, lanes_now - event_lanes, song_time))
                    event_contacts = contacts_now
                    event_lanes = lanes_now

        for event in pygame.event.get():
            if web_pointer_input and event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                continue
            # Touch-generated mouse events duplicate the same finger and can
            # otherwise leave a phantom held lane after FINGERUP.
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and getattr(event, "touch", False):
                continue
            received_at = time.perf_counter()
            timestamp = getattr(event, "timestamp", None)
            if timestamp is not None:
                age_ms = (pygame.time.get_ticks() - int(timestamp)) % (2 ** 32)
                if age_ms <= 250:
                    received_at -= age_ms / 1000.0
            if web_key_input and event.type in (pygame.KEYDOWN, pygame.KEYUP) and (event.key in KEY_TO_LANE or event.key == pygame.K_SPACE):
                continue
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                key_lanes_down.clear()
                active_touches.clear()
                if state == "PLAY":
                    state = "PAUSED"
                    pause_start_time = time.perf_counter()
                    pause_music()
            elif event.type == pygame.KEYDOWN:
                if event.key in KEY_TO_LANE:
                    lane = KEY_TO_LANE[event.key]
                    raw_flick_events.append((received_at, None, "lane", "down", lane))
                    if lane not in key_lanes_down:
                        triggered_lanes.add(lane)
                        raw_tap_presses.append((received_at, lane, None))
                    key_lanes_down.add(lane)
                elif event.key == pygame.K_SPACE:
                    raw_flick_events.append((received_at, None, "space", "down", None))
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    set_music_volume(music_volume - 0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                    set_music_volume(music_volume + 0.05)
                if event.key == pygame.K_ESCAPE and state in ["LOADING", "READY", "PLAY", "PAUSED", "ANALYZING"]:
                    if state == "ANALYZING":
                        if auto_analysis_job is not None:
                            auto_analysis_job["pending"] = False
                        state = "HOME"
                        set_home_notice("분석은 계속 진행되며 결과는 다음 플레이에 사용됩니다.")
                    elif state in ("READY", "LOADING"):
                        if audio_element is not None:
                            audio_element.cancel()
                        stop_music()
                        state = "HOME"
                        set_home_notice("게임 시작을 취소했습니다.")
                    elif state == "PLAY":
                        state = "PAUSED"
                        pause_start_time = time.perf_counter()
                        pause_music()
                    elif state == "PAUSED":
                        state = "PLAY"
                        # Discard input made on the pause screen, including
                        # key chords delivered before this ESC in the same batch.
                        raw_tap_presses.clear()
                        raw_flick_events.clear()
                        input_changes.clear()
                        initial_lanes = set()
                        event_contacts = frozenset()
                        event_lanes = set()
                        paused_for = time.perf_counter() - pause_start_time
                        game_start_time += paused_for
                        if music_scheduled_start is not None:
                            music_scheduled_start += paused_for
                        if music_scheduled_start is None or audio_element is not None:
                            resume_music()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_click = True
                active_touches[event.button] = event.pos[0]
                raw_flick_events.append((received_at, None, "pointer", "down", ("mouse", *event.pos)))
                if state == "PLAY":
                    track_left = CENTER_X - TRACK_BOTTOM_W / 2
                    if track_left <= event.pos[0] <= track_left + TRACK_BOTTOM_W:
                        lane = min(3, max(0, int((event.pos[0] - track_left) // (TRACK_BOTTOM_W / 4))))
                        triggered_lanes.add(lane)
                        raw_tap_presses.append((received_at, lane, None))
            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:
                    active_touches[1] = event.pos[0]
                    raw_flick_events.append((received_at, None, "pointer", "move", ("mouse", *event.pos)))
                    slider = volume_slider_for_state(state)
                    if slider is not None and slider.inflate(0, 22).collidepoint(event.pos):
                        set_music_volume((event.pos[0] - slider.x) / max(1, slider.width))
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    raw_flick_events.append((received_at, None, "pointer", "up", ("mouse", *event.pos)))
                if event.button in active_touches:
                    del active_touches[event.button]
            elif event.type == pygame.FINGERDOWN:
                touch_x = int(event.x * SCREEN_WIDTH)
                touch_y = int(event.y * SCREEN_HEIGHT)
                raw_flick_events.append((received_at, None, "pointer", "down", (("finger", event.finger_id), touch_x, touch_y)))
                active_touches[("finger", event.finger_id)] = touch_x
                if state == "PLAY":
                    track_left = CENTER_X - TRACK_BOTTOM_W / 2
                    if track_left <= touch_x <= track_left + TRACK_BOTTOM_W:
                        lane = min(3, max(0, int((touch_x - track_left) // (TRACK_BOTTOM_W / 4))))
                        triggered_lanes.add(lane)
                        raw_tap_presses.append((received_at, lane, None))
                else:
                    mouse_click = True
                    mouse_pos = (touch_x, touch_y)
            elif event.type == pygame.FINGERMOTION:
                active_touches[("finger", event.finger_id)] = int(event.x * SCREEN_WIDTH)
                raw_flick_events.append((received_at, None, "pointer", "move", (("finger", event.finger_id), event.x*SCREEN_WIDTH, event.y*SCREEN_HEIGHT)))
            elif event.type == pygame.FINGERUP:
                active_touches.pop(("finger", event.finger_id), None)
                raw_flick_events.append((received_at, None, "pointer", "up", (("finger", event.finger_id), event.x*SCREEN_WIDTH, event.y*SCREEN_HEIGHT)))
            elif event.type == pygame.KEYUP:
                if event.key in KEY_TO_LANE:
                    key_lanes_down.discard(KEY_TO_LANE[event.key])
                    raw_flick_events.append((received_at, None, "lane", "up", KEY_TO_LANE[event.key]))
                elif event.key == pygame.K_SPACE:
                    raw_flick_events.append((received_at, None, "space", "up", None))

            lanes_now = physical_lanes()
            contacts_now = sustain_contacts()
            if contacts_now != event_contacts:
                input_changes.append((received_at, contacts_now, lanes_now - event_lanes, None))
                event_contacts = contacts_now
                event_lanes = lanes_now

        pressed_lanes = physical_lanes() if state == "PLAY" else set()

        combo_scale = max(1.0, combo_scale - dt * 2.5)
        feedback_scale = max(1.0, feedback_scale - dt * 3.0)

        # ==========================================
        # SCENE: HOME
        # ==========================================
        if state == "HOME":
            action = draw_home(mouse_pos, mouse_click)
            if action == "play":
                request_game_start(selected_map_idx, difficulty=selected_difficulty)
            elif action == "practice":
                request_game_start(selected_map_idx, practice=True, difficulty=selected_difficulty)
            elif action == "editor":
                stop_music()
                if sys.platform == "emscripten":
                    set_home_notice("차트 스튜디오는 데스크톱에서 py main.py 로 실행해 주세요.")
                else:
                    try:
                        editor_path = os.path.join(GAME_DIR, "chart_editor.py")
                        if not os.path.isfile(editor_path):
                            raise FileNotFoundError(f"편집기 파일이 없습니다: {editor_path}")
                        subprocess.Popen([sys.executable, editor_path, str(selected_map_idx)], cwd=GAME_DIR)
                        set_home_notice("차트 스튜디오를 별도 창으로 열었습니다. 보이지 않으면 Alt+Tab을 눌러 보세요.")
                    except OSError as exc:
                        print(f"차트 편집기를 실행할 수 없습니다: {exc}")
                        set_home_notice(f"차트 스튜디오 실행 실패: {exc}")

        # ==========================================
        # SCENE: PLAY
        # ==========================================
        elif state == "ANALYZING":
            draw_analysis_screen()

        # ==========================================
        # SCENE: PLAY
        # ==========================================
        elif state == "LOADING":
            draw_loading_screen(mouse_pos, mouse_click)

        elif state == "READY":
            draw_ready_screen()
            if time.perf_counter() - ready_start_time >= ready_count_in_duration:
                begin_play()

        # ==========================================
        # SCENE: PLAY
        # ==========================================
        elif state == "PLAY":
            now = time.perf_counter()
            if music_scheduled_start is not None and now >= music_scheduled_start:
                if not start_music(current_map["audio"]):
                    state = "HOME"
                    continue
                game_start_time = time.perf_counter()
                music_scheduled_start = None
            play_time = time.perf_counter() - game_start_time
            try:
                if audio_element is not None:
                    # A suspended audio context freezes the notes with the sound.
                    play_time = float(audio_element.currentTime)
                    if audio_element.ended:
                        play_time = max(current_map["duration"], play_time)
                elif music_scheduled_start is not None:
                    pass  # Negative pre-roll time; an idle mixer is not song end.
                elif pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    mixer_time = pygame.mixer.music.get_pos()
                    if mixer_time >= 0:
                        play_time = mixer_time / 1000.0
                    audio_ended_at = None
                elif pygame.mixer.get_init():
                    elapsed_from_start = time.perf_counter() - game_start_time
                    if audio_ended_at is None and elapsed_from_start < 0.75:
                        # Avoid mistaking the first mixer startup frames for song end.
                        play_time = elapsed_from_start
                    else:
                        if audio_ended_at is None:
                            audio_ended_at = time.perf_counter()
                        play_time = current_map["duration"] + (time.perf_counter() - audio_ended_at)
            except Exception:
                pass
            now = time.perf_counter()
            if audio_ended_at is None:
                if play_time >= current_map["duration"]:
                    music_fade_gain = 0.0
                    apply_music_volume()
                    stop_music()
                    audio_ended_at = now
                    play_time = current_map["duration"]
                else:
                    seconds_left = current_map["duration"] - play_time
                    music_fade_gain = min(1.0, max(0.0, seconds_left / FADE_OUT_SECONDS))
                    apply_music_volume()
            else:
                play_time = current_map["duration"] + (now - audio_ended_at)
            sample_wall_time = time.perf_counter()
            sustain_changes = [(direct if direct is not None else play_time - max(0.0, sample_wall_time - when), lanes, fresh)
                               for when, lanes, fresh, direct in input_changes]
            sustain_changes.sort(key=lambda change: change[0])
            tap_presses = [[direct if direct is not None else play_time - max(0.0, sample_wall_time - when), lane, False]
                           for when, lane, direct in raw_tap_presses]
            flick_intents = collect_flick_intents(raw_flick_events, play_time, sample_wall_time)
            screen.blit(current_bg_surface, (0, 0))

            top_l, top_r = CENTER_X - TRACK_TOP_W / 2, CENTER_X + TRACK_TOP_W / 2
            bot_l, bot_r = CENTER_X - TRACK_BOTTOM_W / 2, CENTER_X + TRACK_BOTTOM_W / 2

            for beam in range(-4, 5):
                edge_x = CENTER_X + beam * 100
                pygame.draw.line(screen, (24, 23, 53), (CENTER_X + beam * 18, TRACK_TOP_Y - 8), (edge_x, SCREEN_HEIGHT), 1)
            
            track_poly = [(top_l, TRACK_TOP_Y), (top_r, TRACK_TOP_Y), (bot_r, TRACK_BOTTOM_Y), (bot_l, TRACK_BOTTOM_Y)]
            pygame.draw.polygon(screen, (17, 18, 42), track_poly)
            pygame.draw.polygon(screen, (102, 90, 153), track_poly, 2)
            beat_phase = ((play_time - current_offset) * current_bpm / 60.0) % 1.0
            beat_seconds = 60.0 / max(1.0, current_bpm)
            for beat_ahead in range(1, 6):
                seconds_to_beat = (beat_ahead - beat_phase) * beat_seconds
                grid_progress = 1.0 - seconds_to_beat / APPROACH_TIME
                if 0.04 < grid_progress < 0.98:
                    left_x, grid_y, _ = get_perspective_pos(-0.5, grid_progress)
                    right_x, _, _ = get_perspective_pos(3.5, grid_progress)
                    grid_color = (75, 72, 111) if beat_ahead > 1 else (109, 94, 152)
                    pygame.draw.line(screen, grid_color, (left_x, grid_y), (right_x, grid_y), 1 if beat_ahead > 1 else 2)
            
            pressed_glow = pressed_glow_surface
            pressed_glow.fill((0, 0, 0, 0))
            for lane in set(pressed_lanes):
                x1_l, y1, _ = get_perspective_pos(lane - 0.5, 0.0)
                x1_r, y1, _ = get_perspective_pos(lane + 0.5, 0.0)
                x2_l, y2, _ = get_perspective_pos(lane - 0.5, 1.0)
                x2_r, y2, _ = get_perspective_pos(lane + 0.5, 1.0)
                pygame.draw.polygon(pressed_glow, (*current_map["accent"], 26), [(x1_l, y1), (x1_r, y1), (x2_r, y2), (x2_l, y2)])
            screen.blit(pressed_glow, (0, 0))

            for i in range(5):
                lane_ratio = i / 4.0
                x_top, x_bot = top_l + TRACK_TOP_W * lane_ratio, bot_l + TRACK_BOTTOM_W * lane_ratio
                pygame.draw.line(screen, (87, 83, 130), (x_top, TRACK_TOP_Y), (x_bot, TRACK_BOTTOM_Y), 2)
                if i in (0, 4):
                    pygame.draw.line(screen, (180, 137, 255), (x_top, TRACK_TOP_Y), (x_bot, TRACK_BOTTOM_Y), 2)

            beat_glow = 0.35 + 0.65 * (1.0 - beat_phase) ** 4
            judge_color = tuple(int(c * beat_glow) for c in current_map["accent"])
            pygame.draw.line(screen, tuple(int(c * 0.35) for c in judge_color), (bot_l - 12, JUDGE_Y), (bot_r + 12, JUDGE_Y), 14)
            pygame.draw.line(screen, judge_color, (bot_l - 12, JUDGE_Y), (bot_r + 12, JUDGE_Y), 5)
            pygame.draw.line(screen, (245, 248, 255), (bot_l - 8, JUDGE_Y), (bot_r + 8, JUDGE_Y), 1)

            for lane in range(4):
                cx, cy, cw = get_perspective_pos(lane, 1.0)
                pad_w, pad_h = int(cw * 0.42), 28
                pad_rect = pygame.Rect(int(cx - pad_w), int(cy - pad_h / 2), pad_w * 2, pad_h)
                pygame.draw.rect(screen, (8, 10, 25), pad_rect.move(0, 4), border_radius=10)
                pad_fill = current_map["accent"] if lane in pressed_lanes else (31, 29, 62)
                pygame.draw.rect(screen, pad_fill, pad_rect, border_radius=9)
                pygame.draw.rect(screen, (250, 247, 255) if lane in pressed_lanes else (139, 126, 190), pad_rect, 2, border_radius=9)
                pygame.draw.line(screen, (255, 255, 255), (pad_rect.x + 12, pad_rect.y + 3), (pad_rect.right - 12, pad_rect.y + 3), 1)
                key_color = (14, 20, 36) if lane in pressed_lanes else (198, 213, 242)
                draw_styled_text(screen, ("D", "F", "J", "K")[lane], font_small, cx, cy, key_color)

            combo_top, combo_bottom = combo_gradient_colors(combo)
            combo_mix = min(1.0, combo / 12.0)
            TAP_TOP = interpolate_color((255, 242, 255), combo_top, combo_mix)
            TAP_BOT = interpolate_color((247, 93, 187), combo_bottom, combo_mix)
            HOLD_TOP = interpolate_color((255, 250, 196), combo_top, combo_mix * 0.8)
            HOLD_BOT = interpolate_color((45, 218, 222), combo_bottom, combo_mix * 0.8)
            SLIDE_TOP = interpolate_color((255, 203, 255), combo_top, combo_mix * 0.9)
            SLIDE_BOT = interpolate_color((151, 90, 255), combo_bottom, combo_mix * 0.9)

            # Only visit approaching notes and unfinished sustains, even in full songs.
            while next_chart_index < len(chart) and chart[next_chart_index]["time"] <= play_time + APPROACH_TIME * 1.25:
                active_chart_notes.append(chart[next_chart_index])
                next_chart_index += 1
            active_chart_notes = [note for note in active_chart_notes if not note["hit"]]
            tap_hits = match_tap_presses(active_chart_notes, tap_presses, GREAT_TIME)
            tap_results = [(press[0], note, delta) for note, delta, press in tap_hits]
            flick_hits = match_flick_intents(active_chart_notes, flick_intents, GREAT_TIME)
            tap_results.extend((intent.time, note, delta) for note, delta, intent in flick_hits)
            for note, _, press in tap_hits:
                for when, _, fresh in sustain_changes:
                    if when == press[0]:
                        fresh.discard(note["lane"])
            for note in active_chart_notes:
                # Keep a flick pending briefly for a reverse-order key chord or
                # an interpolated touch crossing delivered in the next frame.
                # Actual gesture matching still uses the strict +/-150ms window.
                expiry = GREAT_TIME + (0.050 if note["type"] == "FLICK" else 0.0)
                if note["type"] in ("TAP", "FLICK") and not note["hit"] and play_time - note["time"] > expiry:
                    note["hit"] = True
                    tap_results.append((note["time"] + GREAT_TIME, note, None))
            for _, note, delta in sorted(tap_results, key=lambda item: item[0]):
                if delta is None:
                    combo = 0
                    miss_count += 1
                    if not practice_mode:
                        hp -= 18.0
                    last_feedback, last_feedback_color = "MISS", (255, 60, 60)
                    feedback_scale, feedback_time = 1.2, time.time()
                    continue
                combo += 1
                max_combo = max(max_combo, combo)
                combo_scale, feedback_scale = 1.35, 1.4
                hit_x, hit_y, _ = get_perspective_pos(note["lane"], 1.0)
                spawn_particles(hit_x, hit_y, (255, 112, 189) if note["type"] == "FLICK" else TAP_TOP, count=14 if note["type"] == "FLICK" else 10)
                if abs(delta) <= PERFECT_TIME + 1e-7:
                    score += 200 + combo * 10
                    hit_score += 100
                    perfect_count += 1
                    hp = min(100.0, hp + 2.0)
                    last_feedback, last_feedback_color = "PERFECT", (255, 215, 0)
                else:
                    score += 100 + combo * 5
                    hit_score += 70
                    great_count += 1
                    hp = min(100.0, hp + 1.0)
                    last_feedback, last_feedback_color = "GREAT", (0, 255, 255)
                feedback_time = time.time()
            note_renderer.draw(screen, active_chart_notes, play_time, APPROACH_TIME, {
                "TAP": (TAP_TOP, TAP_BOT), "HOLD": (HOLD_TOP, HOLD_BOT),
                "SLIDE": (SLIDE_TOP, SLIDE_BOT),
            })
            for note in active_chart_notes:
                if note["hit"]: continue
                if note["type"] == "HOLD":
                    judge = update_sustain(note, play_time, initial_lanes, sustain_changes, triggered_lanes)
                    if judge.contact and note["active"]:
                        hit_x, hit_y, _ = get_perspective_pos(note["lane"], 1.0)
                        spawn_particles(hit_x, hit_y, HOLD_TOP, count=3)
                    if judge.finished and judge.tail_hit:
                        combo_scale, feedback_scale = 1.35, 1.4
                        hit_x, hit_y, _ = get_perspective_pos(note["lane"], 1.0)
                        spawn_particles(hit_x, hit_y, (255, 255, 255), count=25, power=1.4)

                elif note["type"] == "SLIDE":
                    judge = update_sustain(note, play_time, initial_lanes, sustain_changes, triggered_lanes)
                    if judge.contact and note["active"]:
                        hit_x, hit_y, _ = get_perspective_pos(judge.position(play_time), 1.0)
                        spawn_particles(hit_x, hit_y, SLIDE_TOP, count=2)
                    if judge.finished and judge.tail_hit:
                        combo_scale, feedback_scale = 1.35, 1.4
                        hit_x, hit_y, _ = get_perspective_pos(note["end_lane"], 1.0)
                        spawn_particles(hit_x, hit_y, (255, 255, 255), count=25, power=1.5)

            if hp <= 0 and not practice_mode:
                state = "GAME_OVER"
                stop_music()

            effect_step = min(3.0, dt * 60.0)
            for p in particles[:]:
                p[0] += p[2] * effect_step; p[1] += p[3] * effect_step
                p[3] += 0.45 * effect_step; p[4] -= 0.14 * effect_step
                if p[4] > 0: pygame.draw.circle(screen, p[5], (int(p[0]), int(p[1])), int(p[4]))
                else: particles.remove(p)

            max_combo = max(max_combo, combo)
            draw_styled_text(screen, f"점수: {score:,}", font_med, 90, 20, (255, 255, 255))
            
            display_play_time = max(0.0, play_time)
            prog_ratio = min(1.0, max(0.0, display_play_time / current_map["duration"]))
            bar_w, bar_h = 240, 8
            bar_x, bar_y = CENTER_X - bar_w // 2, 35
            time_str = f"{format_time(display_play_time)} / {format_time(current_map['duration'])}"
            title_str = f"{current_map['song']}  /  {DIFFICULTIES[current_difficulty]}  ·  {current_chart_source}"
            
            pygame.draw.rect(screen, (10, 14, 32), (0, 0, SCREEN_WIDTH, 58))
            draw_styled_text(screen, title_str, font_small, CENTER_X, 15, (200, 240, 255))
            draw_styled_text(screen, "LIFE", font_small, 30, 43, (211, 220, 242))
            pygame.draw.rect(screen, (39, 28, 44), (55, 37, 113, 12), border_radius=5)
            hp_ratio = max(0.0, min(1.0, hp / 100.0))
            hp_color = (70, 232, 166) if hp > 50 else (255, 195, 77) if hp > 25 else (255, 82, 110)
            if hp_ratio > 0:
                pygame.draw.rect(screen, hp_color, (55, 37, int(113 * hp_ratio), 12), border_radius=5)
            pygame.draw.rect(screen, (226, 234, 252), (55, 37, 113, 12), width=1, border_radius=5)
            pygame.draw.rect(screen, (20, 25, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            if prog_ratio > 0:
                pygame.draw.rect(screen, (0, 230, 255), (bar_x, bar_y, int(bar_w * prog_ratio), bar_h), border_radius=4)
            pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)
            draw_styled_text(screen, time_str, font_small, CENTER_X + 165, 38, (200, 200, 200))
            draw_styled_text(screen, f"{current_bpm:.2f} BPM", font_small, CENTER_X - 185, 38, current_map["accent"])
            if practice_mode:
                draw_styled_text(screen, "PRACTICE", font_small, 674, 43, (120, 228, 195))
            if current_difficulty == "master" and current_flick_enabled:
                draw_styled_text(screen, "FLICK  ·  레인 키 + SPACE  /  위로 스와이프", font_small, CENTER_X, 459, (244, 161, 202))

            pygame.draw.rect(screen, (30, 40, 70), btn_pause, border_radius=8)
            pygame.draw.rect(screen, (0, 220, 255), btn_pause, width=2, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), (btn_pause.x + 14, btn_pause.y + 9, 5, 17))
            pygame.draw.rect(screen, (255, 255, 255), (btn_pause.x + 26, btn_pause.y + 9, 5, 17))

            if mouse_click and btn_pause.collidepoint(mouse_pos):
                state = "PAUSED"
                pause_start_time = time.perf_counter()
                pause_music()

            if combo >= 3:
                combo_color = interpolate_color(combo_top, combo_bottom, 0.48)
                draw_styled_text(screen, f"{combo}", font_combo_num, CENTER_X, 150, combo_color, scale=combo_scale)
                draw_styled_text(screen, "COMBO", font_combo_sub, CENTER_X, 190, (255, 255, 255))

            if time.time() - feedback_time < 0.45:
                draw_styled_text(screen, last_feedback, font_large, CENTER_X, 270, last_feedback_color, scale=feedback_scale)

            if play_time > current_map["duration"] + 0.35:
                finish_song()

        # ==========================================
        # SCENE: PAUSED
        # ==========================================
        elif state == "PAUSED":
            dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            dim_surf.set_alpha(150)
            dim_surf.fill((0, 0, 0))
            screen.blit(dim_surf, (0, 0))
            
            box = pygame.Rect(CENTER_X - 180, 25, 360, 435)
            pygame.draw.rect(screen, (20, 25, 45), box, border_radius=16)
            pygame.draw.rect(screen, (0, 200, 255), box, width=2, border_radius=16)
            
            draw_styled_text(screen, "PAUSED", font_large, CENTER_X, 60, (255, 255, 255))
            if practice_mode:
                draw_styled_text(screen, "PRACTICE · NO LIFE LOSS", font_small, CENTER_X, 91, (120, 228, 195))
            
            btn_resume, btn_retry, btn_home = pygame.Rect(CENTER_X - 145, 112, 290, 38), pygame.Rect(CENTER_X - 145, 158, 140, 38), pygame.Rect(CENTER_X + 5, 158, 140, 38)
            
            pygame.draw.rect(screen, (0, 180, 220), btn_resume, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 150), btn_retry, border_radius=8)
            pygame.draw.rect(screen, (220, 60, 80), btn_home, border_radius=8)
            
            draw_styled_text(screen, "계속하기", font_med, btn_resume.centerx, btn_resume.centery, (255, 255, 255))
            draw_styled_text(screen, "다시하기", font_med, btn_retry.centerx, btn_retry.centery, (255, 255, 255))
            draw_styled_text(screen, "메뉴로", font_med, btn_home.centerx, btn_home.centery, (255, 255, 255))
            draw_volume_control(screen, volume_slider_for_state("PAUSED"), mouse_pos, mouse_click)
            flick_button = pygame.Rect(CENTER_X - 145, 210, 290, 36)
            draw_button(screen, flick_button, "플릭 ON" if current_flick_enabled else "플릭 OFF", (235, 102, 173) if current_flick_enabled else (101, 119, 159))
            speed_minus = pygame.Rect(CENTER_X + 28, 333, 31, 32)
            speed_plus = pygame.Rect(CENTER_X + 114, 333, 31, 32)
            draw_styled_text(screen, "노트 낙하 속도", font_small, CENTER_X - 64, 349, (196, 210, 239))
            draw_button(screen, speed_minus, "-", (93, 138, 183))
            draw_button(screen, speed_plus, "+", (93, 138, 183))
            draw_styled_text(screen, f"{NOTE_SPEED_LEVELS[note_speed_index]:g}×", font_small, CENTER_X + 86, 349, (137, 233, 219))
            draw_styled_text(screen, "노트가 내려오는 속도만 조절합니다", font_small, CENTER_X, 398, (153, 171, 204))
            draw_styled_text(screen, "음악 속도 · 박자 · 판정 타이밍 유지", font_small, CENTER_X, 423, (153, 171, 204))
            
            if mouse_click:
                if flick_button.collidepoint(mouse_pos):
                    change_pause_flick()
                elif speed_minus.collidepoint(mouse_pos):
                    adjust_note_speed(-1)
                elif speed_plus.collidepoint(mouse_pos):
                    adjust_note_speed(1)
                if btn_resume.collidepoint(mouse_pos):
                    state = "PLAY"
                    paused_for = time.perf_counter() - pause_start_time
                    game_start_time += paused_for
                    if music_scheduled_start is not None:
                        music_scheduled_start += paused_for
                    if music_scheduled_start is None or audio_element is not None:
                        resume_music()
                elif btn_retry.collidepoint(mouse_pos):
                    request_game_start(current_map_idx, practice=practice_mode, difficulty=current_difficulty)
                elif btn_home.collidepoint(mouse_pos):
                    state = "HOME"
                    stop_music()

        # ==========================================
        # SCENE: GAME OVER
        # ==========================================
        elif state == "GAME_OVER":
            screen.blit(current_bg_surface, (0, 0))
            dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            dim_surf.set_alpha(200)
            dim_surf.fill((20, 0, 0))
            screen.blit(dim_surf, (0, 0))
            
            draw_styled_text(screen, "GAME OVER", font_large, CENTER_X, 120, (255, 50, 50))
            draw_styled_text(screen, "체력이 모두 소진되었습니다!", font_med, CENTER_X, 180, (220, 220, 220))
            draw_styled_text(screen, f"진행 점수: {score:,}", font_med, CENTER_X, 230, (255, 255, 255))
            
            btn_retry, btn_home = pygame.Rect(CENTER_X - 160, 310, 140, 50), pygame.Rect(CENTER_X + 20, 310, 140, 50)
            
            pygame.draw.rect(screen, (0, 180, 220), btn_retry, border_radius=10)
            pygame.draw.rect(screen, (220, 60, 80), btn_home, border_radius=10)
            
            draw_styled_text(screen, "다시하기", font_med, btn_retry.centerx, btn_retry.centery, (255, 255, 255))
            draw_styled_text(screen, "메뉴로", font_med, btn_home.centerx, btn_home.centery, (255, 255, 255))
            
            if mouse_click:
                if btn_retry.collidepoint(mouse_pos): request_game_start(current_map_idx, difficulty=current_difficulty)
                elif btn_home.collidepoint(mouse_pos):
                    state = "HOME"
                    stop_music()

        # ==========================================
        # SCENE: CLEAR / RESULT
        # ==========================================
        elif state == "CLEAR":
            draw_clear_celebration(screen)

        elif state == "RESULT":
            draw_result_summary(screen)
            
            btn_home = pygame.Rect(CENTER_X - 170, 391, 150, 55)
            btn_retry = pygame.Rect(CENTER_X + 20, 391, 150, 55)
            
            pygame.draw.rect(screen, (0, 180, 220), btn_home, border_radius=12)
            pygame.draw.rect(screen, (255, 0, 100), btn_retry, border_radius=12)
            
            draw_styled_text(screen, "메뉴로", font_med, btn_home.centerx, btn_home.centery, (255, 255, 255))
            draw_styled_text(screen, "다시하기", font_med, btn_retry.centerx, btn_retry.centery, (255, 255, 255))
            
            if mouse_click:
                if btn_home.collidepoint(mouse_pos):
                    state = "HOME"
                    stop_music()
                elif btn_retry.collidepoint(mouse_pos):
                    request_game_start(current_map_idx, practice=practice_mode, difficulty=current_difficulty)

        if audio_element is not None:
            audio_element.setInputEnabled(state == "PLAY")
        if state != "PLAY":
            flick_keyboard.reset()
            flick_touch.reset()
        pygame.display.flip()
        
        # [핵심] 웹 브라우저 상의 비동기 양보
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

# 프로그램 실행 포인트
if __name__ == "__main__":
    asyncio.run(main())
