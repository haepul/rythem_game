"""One-time 2026-10-03 chart upgrade; preserve measured timestamps and signatures."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
import auto_chart as ac

path = ROOT / 'auto_charts.json'
entries = json.loads(path.read_text(encoding='utf-8'))
SPECIAL = 'hatsune-miku-no-shoushitsu'
REVISION = '20261003-master-25s'

def save_variant(entry, name, notes):
    entry['difficulty_charts'][name] = {
        'notes': notes, 'selected_count': len(notes),
        'type_counts': {kind: sum(n['type'] == kind for n in notes) for kind in ('TAP', 'HOLD', 'SLIDE')},
    }

for key, entry in entries.items():
    if key == SPECIAL or entry.get('master_revision') == REVISION:
        continue
    old = entry['difficulty_charts']['master']['notes']
    upgraded = ac.intensify_master(old, entry['bpm'])
    save_variant(entry, 'master', upgraded)
    entry['master_revision'] = REVISION
    print(f'{key}: MASTER {len(old)} -> {len(upgraded)}', flush=True)

entry = entries[SPECIAL]
if not entry.get('melody_revision') and entry.get('master_revision') != REVISION:
    pygame.mixer.init(44100, -16, 2)
    samples, rate = ac._downsample_mono(str(ROOT / 'music' / (SPECIAL + '.mp3')))
    hop = 256 / rate
    print('Analyzing complete Shoushitsu audio...', flush=True)
    flux, energy, pitch, salience = ac._spectral_flux(samples, rate, 512, 256)
    onsets = ac._find_onsets(flux, hop, pitch, salience)
    bpm, offset = entry['bpm'], entry.get('offset', 0)
    duration = len(samples) / rate
    step = 60 / bpm / 4
    selected = ac._select_quantized_onsets(onsets, bpm, offset, hop, 9, duration - 0.35)
    old_master = entry['difficulty_charts']['master']['notes']
    # Sparse opening on the saved melody attacks, one tap per second at most.
    intro = []
    last_time = -10
    for note in old_master:
        seconds = offset + note['beat'] * 60 / bpm
        if seconds >= 25:
            break
        if seconds >= 1 and seconds - last_time >= 1:
            intro.append({'type': 'TAP', 'beat': note['beat'], 'lane': (len(intro) * 3) % 4})
            last_time = seconds
    # Dense runs begin at the user's 25s phrase boundary. Only bridge short
    # gaps between detected attacks; long musical rests remain empty.
    slots = {round(note['beat'] * 4) for note in selected
             if 25 <= offset + note['beat'] * 60 / bpm < duration - 0.35}
    slots.update(round(note['beat'] * 4) for note in old_master
                 if 25 <= offset + note['beat'] * 60 / bpm < 139)
    ordered = sorted(slots)
    energy_floor = sorted(energy)[int(len(energy) * 0.12)]
    for first, second in zip(ordered, ordered[1:]):
        if (second - first) * step > 0.32:
            continue
        for slot in range(first + 1, second):
            frame = min(len(energy) - 1, round((offset + slot * step) / hop))
            if energy[frame] > energy_floor:
                slots.add(slot)
    patterns = ((0, 2, 1, 3), (3, 1, 2, 0), (0, 1, 3, 2), (2, 0, 3, 1))
    rapid = []
    previous = -1
    for index, slot in enumerate(sorted(slots)):
        lane = patterns[(index // 32) % len(patterns)][index % 4]
        if lane == previous:
            lane = (lane + 2) % 4
        rapid.append({'type': 'TAP', 'beat': slot / 4, 'lane': lane})
        previous = lane
    save_variant(entry, 'master', intro + rapid)
    # Replace the previously overscaled tail (>1000 seconds) with actual audio
    # events from the full song; leave the established first-verse Hard intact.
    hard = [n for n in entry['difficulty_charts']['hard']['notes']
            if offset + n['beat'] * 60 / bpm < 139]
    tail = [n for n in rapid if offset + n['beat'] * 60 / bpm >= 139]
    hard.extend(n for index, n in enumerate(tail) if index % 5 in (0, 2))
    save_variant(entry, 'hard', hard)
    entry.update(duration=duration, master_revision=REVISION)
    for field in ('notes', 'selected_count', 'type_counts'):
        entry[field] = entry['difficulty_charts']['hard'][field]
    print(f'Shoushitsu: intro={len(intro)}, rapid={len(rapid)}, full duration={duration:.3f}', flush=True)
    pygame.mixer.quit()

path.write_text(json.dumps(entries, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('Saved upgraded full-song chart cache.', flush=True)
