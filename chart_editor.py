"""Beat calibration and note chart editor for Rhythm Stage."""
import json
import math
import os
import statistics
import sys
import threading
import time

import pygame
from auto_chart import generate_auto_chart
from beat_analysis import analyze_audio

ROOT = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(ROOT, "music")
CHARTS_PATH = os.path.join(ROOT, "charts.json")
AUTO_CHARTS_PATH = os.path.join(ROOT, "auto_charts.json")
SONGS = [
    ("나다움", "나다움", 165), ("숙명", "숙명", 164), ("이단의 스타", "이단의 스타", 98),
    ("Cry Baby", "Cry Baby", 200), ("Gone Angels", "Gone Angels", 129),
    ("Mixed Nuts", "Mixed Nuts", 150), ("Pretender", "Pretender", 92),
    ("Universe", "Universe", 186), ("괴수의 꽃노래", "괴수의 꽃노래", 151),
    ("라일락", "라일락", 83), ("최종화", "최종화", 100), ("Ray", "Ray", 66),
]
SONG_LEVELS = [1, 2, 3, 4, 5, 6, 7, 10, 8, 8, 9, 8]

# Match the game's low-latency mixer setup so beat calibration is measured
# against the same audio output delay as gameplay.
pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.init()
pygame.mixer.init()
W, H = 1100, 690
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Rhythm Stage · Chart Studio")
clock = pygame.time.Clock()
try:
    font = pygame.font.SysFont("Malgun Gothic", 17)
    small = pygame.font.SysFont("Malgun Gothic", 13)
    title_font = pygame.font.SysFont("Malgun Gothic", 31, bold=True)
except pygame.error:
    font, small, title_font = pygame.font.Font(None, 17), pygame.font.Font(None, 13), pygame.font.Font(None, 31)

BG = (12, 15, 29)
PANEL = (23, 28, 48)
PANEL_ALT = (30, 36, 60)
TEXT = (238, 242, 255)
MUTED = (151, 163, 193)
ACCENT = (112, 139, 255)
LANE_COLORS = [(72, 198, 255), (162, 126, 255), (255, 114, 174), (255, 191, 84)]

def read_database():
    try:
        with open(CHARTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def read_auto_database():
    try:
        with open(AUTO_CHARTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

database = read_database()
song_index = 0
song_data = {}
notes = []
mode = "TAP"
bpm = float(SONGS[0][2])
offset = 0.0
playing = False
position = 0.0
wall_anchor = time.perf_counter()
tap_times = []
open_holds = {}
pending_slide = None
message = "P 재생 · A 오디오 분석 · SPACE 수동 박자 보정 · CTRL+S 저장"
message_until = 0.0
analysis_job = None
auto_chart_confirm_until = 0.0
backup_notes = None
backup_settings = None
preview_auto_chart = False

def announce(text):
    global message, message_until
    message = text
    message_until = time.perf_counter() + 2.5

def load_song(index):
    global song_index, song_data, notes, bpm, offset, position, playing, tap_times, open_holds, pending_slide
    global backup_notes, backup_settings
    if song_data.get("stem"):
        save_chart()
    pygame.mixer.music.stop()
    playing = False
    song_index = index % len(SONGS)
    title, stem, default_bpm = SONGS[song_index]
    saved = database.get(stem, {})
    if not saved.get("notes"):
        automatic = read_auto_database().get(stem)
        audio_path = os.path.join(MUSIC_DIR, stem + ".ogg")
        try:
            stat = os.stat(audio_path)
            signature = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            if isinstance(automatic, dict) and automatic.get("signature") == signature:
                saved = automatic
        except OSError:
            pass
    song_data = {"title": title, "stem": stem, "bpm": float(saved.get("bpm", default_bpm)),
                 "offset": float(saved.get("offset", 0.0))}
    bpm, offset = song_data["bpm"], song_data["offset"]
    notes = list(saved.get("notes", []))
    position = 0.0
    tap_times = []
    open_holds = {}
    pending_slide = None
    backup_notes = None
    backup_settings = None

def save_chart():
    global backup_notes, backup_settings, preview_auto_chart
    database[song_data["stem"]] = {
        "bpm": round(bpm, 3), "offset": round(offset, 4),
        "notes": sorted(notes, key=lambda n: (float(n["beat"]), int(n["lane"])))
    }
    with open(CHARTS_PATH, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    backup_notes = None
    backup_settings = None
    preview_auto_chart = False
    announce(f"저장 완료 · {len(notes)} notes · {bpm:.2f} BPM · offset {offset:+.3f}s")

def undo_auto_preview(save_restored=False):
    global notes, bpm, offset, backup_notes, backup_settings, preview_auto_chart
    if backup_notes is None:
        return False
    notes = backup_notes
    backup_notes = None
    if backup_settings is not None:
        bpm, offset = backup_settings
        song_data["bpm"], song_data["offset"] = bpm, offset
    backup_settings = None
    preview_auto_chart = False
    if save_restored:
        save_chart()
    else:
        announce("자동 채보 이전 상태로 되돌렸습니다.")
    return True

def song_time():
    global position, wall_anchor, playing
    if playing:
        if not pygame.mixer.music.get_busy():
            playing = False
            return position
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms >= 0:
            position = pos_ms / 1000.0
        else:
            position += time.perf_counter() - wall_anchor
            wall_anchor = time.perf_counter()
    return position

def set_playing(value):
    global playing, wall_anchor, position
    if value and not playing:
        _, stem, _ = SONGS[song_index]
        path = os.path.join(MUSIC_DIR, stem + ".ogg")
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(start=position)
            playing = True
            wall_anchor = time.perf_counter()
            announce("재생 중 · SPACE를 박자에 맞춰 눌러 BPM/offset 보정")
        except pygame.error as exc:
            announce(f"오디오를 열지 못했습니다: {exc}")
    elif not value and playing:
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms >= 0:
            position = pos_ms / 1000.0
        pygame.mixer.music.pause()
        playing = False

def _run_audio_analysis(job, path, preferred_bpm, difficulty, make_chart):
    try:
        if make_chart:
            job["result"] = {"mode": "chart", **generate_auto_chart(path, preferred_bpm, difficulty)}
        else:
            bpm_result = analyze_audio(path, preferred_bpm=preferred_bpm)
            job["result"] = {"mode": "bpm", "bpm": bpm_result[0], "offset": bpm_result[1],
                             "confidence": bpm_result[2], "alternatives": bpm_result[3]}
    except Exception as exc:
        job["error"] = str(exc)
    finally:
        job["done"] = True

def begin_analysis(make_chart=False):
    global analysis_job, playing, position, tap_times
    if analysis_job is not None:
        announce("오디오 분석이 이미 진행 중입니다.")
        return
    _, stem, _ = SONGS[song_index]
    path = os.path.join(MUSIC_DIR, stem + ".ogg")
    if not os.path.isfile(path):
        announce(f"음악 파일을 찾을 수 없습니다: {path}")
        return
    pygame.mixer.music.stop()
    playing = False
    position = 0.0
    tap_times = []
    analysis_job = {"done": False, "result": None, "error": None}
    global_message_set("오디오 분석 중 · 곡 길이에 따라 잠시 걸릴 수 있습니다.")
    threading.Thread(
        target=_run_audio_analysis,
        args=(analysis_job, path, float(song_data["bpm"]), SONG_LEVELS[song_index], make_chart),
        daemon=True,
    ).start()

def request_auto_chart():
    global auto_chart_confirm_until
    if analysis_job is not None:
        announce("분석이 끝날 때까지 기다려 주세요.")
        return
    now = time.perf_counter()
    if notes and now > auto_chart_confirm_until:
        auto_chart_confirm_until = now + 6.0
        announce(f"현재 노트 {len(notes)}개를 자동 채보로 교체합니다. 확인하려면 G를 한 번 더 누르세요.")
        return
    auto_chart_confirm_until = 0.0
    begin_analysis(make_chart=True)

def global_message_set(text):
    global message, message_until
    message = text
    message_until = time.perf_counter() + 3600.0

def snapped_beat(at_time):
    step = 0.25
    return max(0.0, round(((at_time - offset) / (60.0 / bpm)) / step) * step)

def add_tap(lane, at_time):
    beat_pos = snapped_beat(at_time)
    notes.append({"type": "TAP", "beat": beat_pos, "lane": lane})
    announce(f"TAP · lane {lane + 1} · beat {beat_pos:g}")

def draw_text(text, x, y, color=TEXT, use_font=font):
    screen.blit(use_font.render(str(text), True, color), (x, y))

def draw_button(rect, label, active=False):
    pygame.draw.rect(screen, (53, 67, 111) if active else PANEL_ALT, rect, border_radius=10)
    pygame.draw.rect(screen, ACCENT if active else (55, 64, 94), rect, 1, border_radius=10)
    img = font.render(label, True, TEXT)
    screen.blit(img, img.get_rect(center=rect.center))

try:
    initial_song_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
except ValueError:
    initial_song_index = 0
load_song(initial_song_index)
running = True
while running:
    dt = clock.tick(60) / 1000.0
    if analysis_job is not None and analysis_job["done"]:
        finished_job = analysis_job
        analysis_job = None
        if finished_job["error"]:
            announce(f"자동 분석 실패: {finished_job['error']}")
        else:
            result = finished_job["result"]
            previous_settings = (bpm, offset)
            bpm, offset = result["bpm"], result["offset"]
            song_data["bpm"], song_data["offset"] = bpm, offset
            if result["mode"] == "chart":
                backup_notes = [dict(note) for note in notes]
                backup_settings = previous_settings
                preview_auto_chart = True
                notes = result["notes"]
                counts = result["type_counts"]
                global_message_set(
                    f"자동 채보 미리보기 · 노트 {len(notes)}개 "
                    f"(TAP {counts['TAP']} / HOLD {counts['HOLD']} / SLIDE {counts['SLIDE']}) · "
                    "Ctrl+S 저장 / Ctrl+Z 되돌리기"
                )
            else:
                save_chart()
                alt_text = ", ".join(f"{value:.1f}" for value in result["alternatives"][:3])
                global_message_set(
                    f"박자 분석 저장 · {bpm:.2f} BPM · offset {offset:+.3f}s · "
                    f"후보 {alt_text} · 귀로 확인해 주세요"
                )
    now = song_time()
    mouse_pos = pygame.mouse.get_pos()
    mouse_click = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if preview_auto_chart:
                undo_auto_preview(save_restored=True)
            else:
                save_chart()
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_click = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if preview_auto_chart:
                    undo_auto_preview(save_restored=True)
                else:
                    save_chart()
                running = False
            elif event.key == pygame.K_UP:
                if analysis_job is None: load_song(song_index - 1)
            elif event.key == pygame.K_DOWN:
                if analysis_job is None: load_song(song_index + 1)
            elif event.key == pygame.K_p:
                if analysis_job is None: set_playing(not playing)
            elif event.key == pygame.K_r:
                if analysis_job is None:
                    pygame.mixer.music.stop()
                    playing = False
                    position = 0.0
                    set_playing(True)
            elif event.key == pygame.K_a:
                begin_analysis()
            elif event.key == pygame.K_g:
                request_auto_chart()
            elif event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                save_chart()
            elif event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
                if not undo_auto_preview():
                    announce("되돌릴 자동 채보가 없습니다.")
            elif event.key == pygame.K_1:
                mode = "TAP"; announce("노트 모드: TAP")
            elif event.key == pygame.K_2:
                mode = "HOLD"; announce("노트 모드: HOLD · 레인 키를 누른 뒤 놓으세요")
            elif event.key == pygame.K_3:
                mode = "SLIDE"; pending_slide = None; announce("노트 모드: SLIDE · 시작 레인과 끝 레인을 차례로 누르세요")
            elif event.key == pygame.K_LEFTBRACKET:
                bpm = max(40, bpm - 1); announce(f"BPM {bpm:.1f}")
            elif event.key == pygame.K_RIGHTBRACKET:
                bpm = min(300, bpm + 1); announce(f"BPM {bpm:.1f}")
            elif event.key in (pygame.K_MINUS, pygame.K_EQUALS):
                offset = max(-2.0, min(2.0, offset + (-0.01 if event.key == pygame.K_MINUS else 0.01)))
                announce(f"offset {offset:+.3f}s")
            elif event.key == pygame.K_SPACE and playing:
                tap_times.append(now)
                tap_times = tap_times[-8:]
                if len(tap_times) >= 4:
                    intervals = [tap_times[i] - tap_times[i - 1] for i in range(1, len(tap_times))]
                    valid = [v for v in intervals if 0.25 <= v <= 1.5]
                    if valid:
                        bpm = max(40, min(240, 60.0 / statistics.median(valid)))
                        phase = tap_times[0] % (60.0 / bpm)
                        offset = phase
                        announce(f"박자 보정됨 · {bpm:.2f} BPM · offset {offset:+.3f}s")
                else:
                    announce(f"박자 탭 {len(tap_times)}/4")
            elif event.key in (pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k) and playing:
                lane = {pygame.K_d: 0, pygame.K_f: 1, pygame.K_j: 2, pygame.K_k: 3}[event.key]
                beat_pos = snapped_beat(now)
                if mode == "TAP":
                    add_tap(lane, now)
                elif mode == "HOLD":
                    open_holds[lane] = beat_pos
                    announce(f"HOLD 시작 · lane {lane + 1}")
                elif mode == "SLIDE":
                    if pending_slide is None:
                        pending_slide = (lane, beat_pos)
                        announce("슬라이드 끝 레인을 눌러 주세요")
                    else:
                        start_lane, start_beat = pending_slide
                        end_beat = max(start_beat + 0.25, beat_pos)
                        notes.append({"type": "SLIDE", "beat": start_beat, "end_beat": end_beat,
                                      "lane": start_lane, "end_lane": lane})
                        pending_slide = None
                        announce(f"SLIDE · {start_lane + 1} → {lane + 1}")
        elif event.type == pygame.KEYUP and event.key in (pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k):
            lane = {pygame.K_d: 0, pygame.K_f: 1, pygame.K_j: 2, pygame.K_k: 3}[event.key]
            if lane in open_holds:
                start_beat = open_holds.pop(lane)
                end_beat = max(start_beat + 0.25, snapped_beat(now))
                notes.append({"type": "HOLD", "beat": start_beat, "end_beat": end_beat, "lane": lane})
                announce(f"HOLD 저장 · {end_beat - start_beat:g} beats")

    if mouse_click:
        if pygame.Rect(28, 218, 236, 44).collidepoint(mouse_pos):
            if analysis_job is None: set_playing(not playing)
        elif pygame.Rect(28, 274, 72, 42).collidepoint(mouse_pos):
            bpm = max(40, bpm - 1)
        elif pygame.Rect(108, 274, 72, 42).collidepoint(mouse_pos):
            bpm = min(300, bpm + 1)
        elif pygame.Rect(188, 274, 76, 42).collidepoint(mouse_pos):
            save_chart()
        elif pygame.Rect(28, 402, 112, 28).collidepoint(mouse_pos):
            begin_analysis()
        elif pygame.Rect(146, 402, 118, 28).collidepoint(mouse_pos):
            request_auto_chart()
        elif pygame.Rect(28, 436, 236, 38).collidepoint(mouse_pos):
            mode = "TAP"
        elif pygame.Rect(28, 482, 236, 38).collidepoint(mouse_pos):
            mode = "HOLD"
        elif pygame.Rect(28, 528, 236, 38).collidepoint(mouse_pos):
            mode = "SLIDE"
        elif pygame.Rect(28, 574, 236, 30).collidepoint(mouse_pos):
            notes = notes[:-1]
            announce("마지막 노트 삭제")

    screen.fill(BG)
    # Studio header
    pygame.draw.rect(screen, (19, 23, 40), (0, 0, W, 94))
    draw_text("RHYTHM STAGE", 32, 17, TEXT, title_font)
    draw_text("CHART STUDIO", 34, 59, ACCENT, small)
    draw_text("곡별 BPM · 박자 오프셋 · 노트 직접 제작", 300, 35, MUTED, font)
    draw_text("CTRL+S 저장     ESC 닫기", 880, 36, MUTED, small)

    # Left control card
    pygame.draw.rect(screen, PANEL, (24, 116, 260, 500), border_radius=16)
    draw_text("곡 선택", 44, 136, MUTED, small)
    draw_text(song_data["title"], 44, 158, TEXT, font)
    draw_text("↑ / ↓ 로 곡 변경", 44, 184, MUTED, small)
    draw_button(pygame.Rect(28, 218, 236, 44), "재생 중 · P로 일시정지" if playing else "▶  곡 재생 / P", playing)
    draw_button(pygame.Rect(28, 274, 72, 42), "BPM −")
    draw_button(pygame.Rect(108, 274, 72, 42), "BPM +")
    draw_button(pygame.Rect(188, 274, 76, 42), "저장")
    draw_text(f"{bpm:.2f} BPM", 44, 329, (134, 207, 255), font)
    draw_text(f"OFFSET {offset:+.3f}s", 44, 356, MUTED, small)
    draw_text(f"AUDIO {format(int(now // 60), '02d')}:{int(now % 60):02d}  ·  {len(notes)} NOTES", 44, 379, MUTED, small)
    draw_button(pygame.Rect(28, 402, 112, 28), "A  BPM 분석", analysis_job is not None)
    draw_button(pygame.Rect(146, 402, 118, 28), "G  자동 채보", analysis_job is not None)
    draw_button(pygame.Rect(28, 436, 236, 38), "1  TAP  ·  한 번 눌러 입력", mode == "TAP")
    draw_button(pygame.Rect(28, 482, 236, 38), "2  HOLD  ·  누르고 유지", mode == "HOLD")
    draw_button(pygame.Rect(28, 528, 236, 38), "3  SLIDE  ·  시작 → 끝 레인", mode == "SLIDE")
    draw_button(pygame.Rect(28, 574, 236, 30), "BACKSPACE  ·  마지막 노트 삭제")

    # Timeline card
    pygame.draw.rect(screen, PANEL, (304, 116, 772, 500), border_radius=16)
    draw_text("4-LANE TIMELINE", 330, 136, TEXT, font)
    draw_text("A: BPM 분석  ·  G: 자동 채보  ·  SPACE: 수동 탭 보정", 330, 164, MUTED, small)
    grid = pygame.Rect(330, 206, 720, 330)
    pygame.draw.rect(screen, (13, 17, 32), grid, border_radius=12)
    beat_sec = 60.0 / bpm
    view_start = max(0.0, now - 2.5)
    view_end = view_start + 12.0
    lane_h = grid.height / 4
    for lane in range(4):
        y = grid.y + lane * lane_h
        pygame.draw.line(screen, (47, 54, 80), (grid.x + 1, int(y)), (grid.right - 1, int(y)), 1)
        draw_text(f"{lane + 1}  {['D', 'F', 'J', 'K'][lane]}", grid.x + 9, int(y + 8), LANE_COLORS[lane], small)
    for beat_num in range(math.floor((view_start - offset) / beat_sec), math.ceil((view_end - offset) / beat_sec) + 1):
        t = offset + beat_num * beat_sec
        x = grid.x + 64 + int((t - view_start) / (view_end - view_start) * (grid.width - 72))
        if grid.x < x < grid.right:
            strong = beat_num % 4 == 0
            pygame.draw.line(screen, (67, 77, 111) if strong else (35, 41, 63), (x, grid.y + 1), (x, grid.bottom - 1), 2 if strong else 1)
    for note in notes:
        start_t = offset + float(note["beat"]) * beat_sec
        if not view_start - 1 <= start_t <= view_end + 1:
            continue
        x1 = grid.x + 64 + int((start_t - view_start) / (view_end - view_start) * (grid.width - 72))
        y = int(grid.y + note["lane"] * lane_h + lane_h / 2)
        col = LANE_COLORS[note["lane"]]
        if note["type"] in {"HOLD", "SLIDE"}:
            end_t = offset + float(note["end_beat"]) * beat_sec
            x2 = grid.x + 64 + int((end_t - view_start) / (view_end - view_start) * (grid.width - 72))
            end_y = y if note["type"] == "HOLD" else int(grid.y + note.get("end_lane", note["lane"]) * lane_h + lane_h / 2)
            pygame.draw.line(screen, col, (x1, y), (x2, end_y), 12)
            pygame.draw.circle(screen, (255, 255, 255), (x2, end_y), 7)
        else:
            pygame.draw.circle(screen, col, (x1, y), 9)
            pygame.draw.circle(screen, (255, 255, 255), (x1, y), 3)
    cursor_x = grid.x + 64 + int((now - view_start) / (view_end - view_start) * (grid.width - 72))
    pygame.draw.line(screen, (255, 255, 255), (cursor_x, grid.y), (cursor_x, grid.bottom), 2)
    draw_text("재생 커서", 330, 551, MUTED, small)
    draw_text("현재 모드: " + mode, 330, 578, ACCENT, font)
    if message and time.perf_counter() < message_until:
        draw_text(message, 590, 579, (178, 235, 201), small)
    else:
        draw_text("D F J K: 현재 위치에 노트 입력", 590, 579, MUTED, small)

    pygame.display.flip()

save_chart()
pygame.quit()
