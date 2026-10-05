"""Offline NumPy chart builder: audio attacks + harmonic contour, no tile loops.

Input: little-endian 16-bit mono PCM at 11025Hz, decoded from the user's MP3.
The production game only needs the generated JSON, not NumPy or this tool.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flick_chart import add_master_flicks
KEY = 'hatsune-miku-no-shoushitsu'
REVISION = '20261005-melody-contour'
RATE, HOP = 11025, 110


def smooth(values, width):
    pad = width // 2
    return np.convolve(np.pad(values, (pad, pad), mode='edge'), np.ones(width) / width, 'valid')


def features(pcm):
    y = np.fromfile(pcm, dtype='<i2').astype(np.float32) / 32768
    times = np.arange(0, len(y), HOP) / RATE
    pitch_midi = np.arange(52, 92.5, 0.5)
    frequency = 440 * 2 ** ((pitch_midi - 69) / 12)
    pitch_scores = np.zeros((len(times), len(pitch_midi)), np.float32)
    lead = np.zeros(len(times), np.float32)
    broad = lead.copy()
    rms = lead.copy()
    previous = None
    # Centered frames preserve source timestamps; the short window resolves attacks.
    for size in (512, 2048):
        padded = np.pad(y, (size // 2, size // 2), mode='reflect')
        windows = np.lib.stride_tricks.sliding_window_view(padded, size)[::HOP][:len(times)]
        hann = np.hanning(size).astype(np.float32)
        bins = np.fft.rfftfreq(size, 1 / RATE)
        for first in range(0, len(times), 256):
            frames = windows[first:first + 256]
            mag = np.abs(np.fft.rfft(frames * hann, axis=1)).astype(np.float32)
            if size == 512:
                logmag = np.log1p(mag * 15)
                prev = logmag[:1] if previous is None else previous[None, :]
                growth = np.maximum(0, np.diff(np.concatenate((prev, logmag)), axis=0))
                lead[first:first + len(frames)] = np.mean(growth[:, (bins >= 220) & (bins <= 2600)], axis=1)
                broad[first:first + len(frames)] = np.mean(growth[:, (bins >= 60) & (bins <= 4800)], axis=1)
                rms[first:first + len(frames)] = np.sqrt(np.mean(frames ** 2, axis=1))
                previous = logmag[-1]
            else:
                # Whiten the spectrum so broad percussion does not dominate pitch.
                prefix = np.cumsum(np.pad(mag, ((0, 0), (6, 6)), mode='edge'), axis=1)
                local = (prefix[:, 12:] - prefix[:, :-12]) / 12
                whitened = np.maximum(0, np.log1p(mag / (local + 1e-5)) - 0.35)
                scores = np.zeros((len(frames), len(frequency)), np.float32)
                for harmonic, weight in ((1, 1), (2, .65), (3, .42), (4, .25)):
                    indexes = np.clip(np.rint(frequency * harmonic * size / RATE).astype(int), 1, len(bins)-2)
                    peaks = np.maximum.reduce([whitened[:, indexes + shift] for shift in (-1, 0, 1)])
                    peaks *= frequency * harmonic < RATE / 2
                    scores += weight * peaks
                # Retain magnitude evidence; silence must not produce a pitch event.
                indexes = np.rint(frequency * size / RATE).astype(int)
                scores += .18 * np.log1p(mag[:, indexes] * 10)
                scores = (scores - np.mean(scores, axis=1, keepdims=True)) / (np.std(scores, axis=1, keepdims=True) + 1e-5)
                pitch_scores[first:first + len(frames)] = scores
    # Viterbi contour: discourage frame-to-frame octave jumps, allow real phrase moves.
    distance = np.abs(pitch_midi[:, None] - pitch_midi[None, :])
    transition = .16 * np.minimum(distance, 12) + .3 * (distance >= 11)
    back = np.zeros(pitch_scores.shape, np.uint8)
    score = pitch_scores[0]
    for i in range(1, len(times)):
        options = score[:, None] - transition
        back[i] = np.argmax(options, axis=0)
        score = pitch_scores[i] + np.max(options, axis=0)
        score -= np.max(score)
    path = np.zeros(len(times), int)
    path[-1] = np.argmax(score)
    for i in range(len(times) - 1, 0, -1):
        path[i - 1] = back[i, path[i]]
    pitch = pitch_midi[path]
    pitch = np.median(np.lib.stride_tricks.sliding_window_view(np.pad(pitch, (2, 2), mode='edge'), 5), axis=1)
    confidence = pitch_scores[np.arange(len(times)), path]
    return dict(times=times, pitch=pitch, confidence=confidence, lead=lead, broad=broad, rms=rms,
                duration=np.array(len(y) / RATE))


def detect(data):
    times, pitch, rms = data['times'], data['pitch'], data['rms']
    attack = smooth(data['lead'], 3) * .8 + smooth(data['broad'], 3) * .2
    local = smooth(attack, 81)
    scale = np.sqrt(np.maximum(1e-7, smooth(attack ** 2, 81) - local ** 2))
    novelty = (attack - local) / (scale + .005)
    pitch_delta = np.abs(pitch - np.roll(pitch, 4))
    audible = rms > max(.006, float(np.quantile(rms, .15)) * .35)
    peaks = []
    for i in range(5, len(times) - 6):
        attack_peak = novelty[i] >= .12 and attack[i] >= attack[i-1] and attack[i] > attack[i+1]
        pitch_peak = (pitch_delta[i] >= 1 and pitch_delta[i] > pitch_delta[i-1]
                      and data['confidence'][i] >= .8 and novelty[i] > -.4)
        if not audible[i] or not (attack_peak or pitch_peak):
            continue
        # Refine to the onset's leading edge, not the late peak of the FFT window.
        start = i
        floor = local[i] + max(0, attack[i] - local[i]) * .48
        while start > i - 3 and attack[start - 1] >= floor:
            start -= 1
        seconds = float(times[start])
        value = float(max(0, novelty[i]) + min(4, pitch_delta[i]) * .18 + .4 * max(0, data['confidence'][i]))
        peaks.append({'seconds': seconds, 'strength': value, 'pitch': float(np.median(pitch[i:i+6])),
                      'motion': float(pitch[i] - pitch[i-4]), 'frame': i})
    # Suppress duplicate peaks from one attack without filling any missing beats.
    picked = []
    occupied = np.zeros(len(times), bool)
    for event in sorted(peaks, key=lambda e: -e['strength']):
        i = event['frame']
        if not occupied[i]:
            picked.append(event)
            occupied[max(0, i - 5):i + 6] = True
    return sorted(picked, key=lambda e: e['seconds'])


def pulse_fit(events):
    # The referenced song is 240 BPM. Fit a narrow range to detect encode drift,
    # using attacks across the complete file instead of one integer FFT lag.
    use = [e for e in events if 25 < e['seconds'] < 270 and e['strength'] > 1.0]
    t = np.array([e['seconds'] for e in use])
    w = np.array([min(3, e['strength']) for e in use])
    rows = []
    for bpm in np.arange(239.5, 240.501, .005):
        step = 60 / bpm / 2
        vector = np.sum(w * np.exp(2j * np.pi * t / step)) / np.sum(w)
        phase = (np.angle(vector) / (2 * np.pi) % 1) * step
        rows.append((float(abs(vector)), float(bpm), float(phase)))
    strength, bpm, phase = max(rows)
    # Retain the exact musical BPM when the optimum differs only by rounding.
    if abs(bpm - 240) < .025:
        bpm = 240.0
        strength, _, phase = min(rows, key=lambda row: abs(row[1] - bpm))
    return round(bpm, 3), phase, strength


def select(events, difficulty, bpm, offset):
    minimum = {'easy': 1.55, 'hard': .14, 'master': .085}[difficulty]
    cap = {'easy': 1, 'hard': 5, 'master': 9}[difficulty]
    selected = []
    # One-second groups preserve changes in activity without periodic deletions.
    groups = {}
    for event in events:
        groups.setdefault(int(event['seconds']), []).append(event)
    for second, group in groups.items():
        intro = second < 25
        group_cap = 1 if intro else cap
        for event in sorted(group, key=lambda e: -e['strength']):
            if sum(int(e['seconds']) == second for e in selected) >= group_cap:
                break
            gap = max(.72, minimum) if intro else minimum
            if all(abs(event['seconds'] - prev['seconds']) >= gap for prev in selected[-24:]):
                selected.append(dict(event))
        selected.sort(key=lambda e: e['seconds'])
    # Only small corrections to measured attacks; no forced grid for off-grid melody.
    step = 60 / bpm / 4
    for event in selected:
        grid = offset + round((event['seconds'] - offset) / step) * step
        event['time'] = grid if abs(grid - event['seconds']) <= .014 else event['seconds']
    selected.sort(key=lambda e: e['time'])
    return selected


def arrange(events, data, difficulty, bpm, offset):
    notes, history = [], []
    if difficulty != 'easy':
        # Follow sustained/rising/falling pitch phrases even if the backing drums
        # continue to fire attacks underneath them.
        phrases = []
        cursor, last_sustain = 0, -100.0
        while cursor < len(events):
            current = dict(events[cursor])
            group = events[cursor:cursor+4]
            if (len(group) == 4 and current['time'] >= 25 and current['time'] - last_sustain >= 1.3
                    and .28 <= group[-1]['time'] - current['time'] <= .65):
                contour = np.array([event['pitch'] for event in group])
                delta = np.diff(contour)
                stable = float(np.ptp(contour)) <= 1.5
                directed = (3 <= abs(contour[-1]-contour[0]) <= 9
                            and max(np.sum(delta >= 0), np.sum(delta <= 0)) == 3
                            and np.max(np.abs(delta)) <= 5)
                if stable or directed:
                    current['phrase_end'] = group[-1]['time']
                    current['phrase_pitch'] = group[-1]['pitch']
                    current['phrase_type'] = 'HOLD' if stable else 'SLIDE'
                    last_sustain = current['time']
                    phrases.append(current)
                    cursor += 4
                    continue
            phrases.append(current)
            cursor += 1
        events = phrases
    lane_last = [-100.0] * 4
    previous_pitch, last_chord = None, -100.0
    for i, event in enumerate(events):
        when, pitch = event['time'], event['pitch']
        phrase = [e['pitch'] for e in events[max(0, i-12):i+13] if abs(e['time']-when) < 3]
        low, high = np.quantile(phrase or [pitch], [.15, .85])
        preferred = float(np.clip((pitch-low) / max(4, high-low) * 3, 0, 3))
        previous = history[-1] if history else None
        gap = when - events[i-1]['time'] if i else 99
        direction = 0 if previous_pitch is None else np.sign(pitch - previous_pitch)
        costs = []
        for lane in range(4):
            cost = abs(lane - preferred) * .65
            if when - lane_last[lane] < .16:
                cost += 10
            if previous is not None:
                if gap < .18 and (lane < 2) == (previous < 2):
                    cost += 2.8
                if direction and np.sign(lane - previous) != direction and gap >= .18:
                    cost += .85
                if lane == previous:
                    cost += 1.4
            # Penalize repeated lane motifs, not repeated musical timestamps.
            candidate = history + [lane]
            for width in (2, 3, 4):
                if len(candidate) >= width * 3 and candidate[-width:] == candidate[-2*width:-width] == candidate[-3*width:-2*width]:
                    cost += 4.5
            cost += history[-12:].count(lane) * .08
            costs.append(cost)
        lane = min(range(4), key=lambda n: (costs[n], n))
        note = {'type': 'TAP', 'beat': round((when-offset)*bpm/60, 6), 'lane': lane}
        following = events[i+1]['time'] if i+1 < len(events) else when
        free = following - when
        if 'phrase_end' in event:
            note['type'] = event['phrase_type']
            note['end_beat'] = round((event['phrase_end']-offset)*bpm/60, 6)
            if note['type'] == 'SLIDE':
                direction = 1 if event['phrase_pitch'] > pitch else -1
                target = lane + direction
                note['end_lane'] = target if 0 <= target <= 3 else lane - direction
        elif difficulty != 'easy' and when >= 25 and .38 <= free <= 1.6:
            end = min(when + .75, following - .08)
            mask = (data['times'] >= when + .06) & (data['times'] <= end)
            contour = data['pitch'][mask]
            energy = data['rms'][mask]
            if len(contour) >= 8 and float(np.mean(energy)) > .035:
                change = float(np.median(contour[-4:]) - np.median(contour[:4]))
                stability = float(np.mean(np.abs(contour - np.median(contour)) < 1.5))
                if stability >= .68 or abs(change) >= 3:
                    note['type'] = 'SLIDE' if abs(change) >= 3 else 'HOLD'
                    note['end_beat'] = round((end-offset)*bpm/60, 6)
                    if note['type'] == 'SLIDE':
                        target = lane + (1 if change > 0 else -1)
                        note['end_lane'] = target if 0 <= target <= 3 else lane - (1 if change > 0 else -1)
        notes.append(note)
        if note['type'] == 'TAP':
            lane_last[lane] = when
        else:
            end_time = offset + note['end_beat'] * 60 / bpm
            for occupied in range(min(lane, note.get('end_lane', lane)), max(lane, note.get('end_lane', lane))+1):
                lane_last[occupied] = end_time
        history.append(lane)
        previous_pitch = pitch
        # Strong isolated attacks get rare two-hand accents, never a sustained stream.
        if (difficulty == 'master' and when >= 25 and note['type'] == 'TAP'
                and event['strength'] >= 3.0 and when-last_chord >= 2.0 and gap >= .11 and free >= .11):
            choices = [n for n in range(4) if (n < 2) != (lane < 2) and when-lane_last[n] >= .20]
            if choices:
                chord_lane = min(choices, key=lambda n: history[-12:].count(n))
                notes.append({**note, 'lane': chord_lane})
                lane_last[chord_lane] = when
                last_chord = when
    return sorted(notes, key=lambda n: (n['beat'], n['lane']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pcm', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    cache = args.pcm.with_suffix('.features.npz')
    if cache.exists():
        data = dict(np.load(cache))
    else:
        print('Extracting onset and harmonic-contour features...', flush=True)
        data = features(args.pcm)
        np.savez_compressed(cache, **data)
    events = detect(data)
    events = [e for e in events if .8 <= e['seconds'] < float(data['duration'])-.35]
    bpm, offset, pulse_strength = pulse_fit(events)
    charts = {}
    for difficulty in ('easy', 'hard', 'master'):
        chosen = select(events, difficulty, bpm, offset)
        notes = arrange(chosen, data, difficulty, bpm, offset)
        if difficulty == 'master':
            notes = add_master_flicks(notes, bpm, offset, song_key=KEY)
        charts[difficulty] = {'notes': notes, 'type_counts': dict(Counter(n['type'] for n in notes)), 'selected_count': len(chosen)}
    report = {'revision': REVISION, 'duration': float(data['duration']), 'bpm': bpm,
              'offset': round(offset, 6), 'pulse_concentration': round(pulse_strength, 4),
              'detected_attacks': len(events), 'counts': {k: len(v['notes']) for k,v in charts.items()},
              'types': {k: v['type_counts'] for k,v in charts.items()},
              'master_per_10_seconds': [sum(t <= offset+n['beat']*60/bpm < t+10 for n in charts['master']['notes']) for t in range(0, 290, 10)],
              'reference': 'https://www.youtube.com/watch?v=NbXzQJi5ntU',
              'method': 'Measured attacks, harmonic pitch candidates, local contour, ergonomic lane costs; no gap filling.',
              'limitation': 'Polyphonic pitch is an estimate, not an isolated vocal transcription.',
              'audio_sha256': hashlib.sha256((ROOT/'music'/f'{KEY}.mp3').read_bytes()).hexdigest()}
    old = json.loads((ROOT/'auto_charts.json').read_text(encoding='utf-8'))[KEY]['difficulty_charts']['master']['notes']
    def motif_share(notes):
        lanes = [n['lane'] for n in notes if n['type'] == 'TAP']
        motifs = Counter(tuple(lanes[i:i+4]) for i in range(len(lanes)-3))
        return round(max(motifs.values(), default=0) / max(1, len(lanes)-3), 4)
    report['most_common_four_lane_motif_share'] = {'before': motif_share(old), 'after': motif_share(charts['master']['notes'])}
    args.pcm.with_suffix('.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    args.pcm.with_suffix('.candidate.json').write_text(json.dumps(charts, separators=(',', ':')), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.apply:
        path = ROOT / 'auto_charts.json'
        entries = json.loads(path.read_text(encoding='utf-8'))
        entry = entries[KEY]
        entry.update(bpm=bpm, offset=round(offset, 6), difficulty_charts=charts,
                     duration=float(data['duration']), onset_count=len(events),
                     melody_revision=REVISION, analysis=report)
        for field in ('notes', 'type_counts', 'selected_count'):
            entry[field] = charts['hard'][field]
        path.write_text(json.dumps(entries, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        print('Saved all three Shoushitsu tiers.')


if __name__ == '__main__':
    main()
