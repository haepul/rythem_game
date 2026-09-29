"""Audio-driven onset, beat-grid, and starter-chart generation for Rhythm Stage."""
from array import array
import math
import sys

import pygame


def _downsample_mono(path, factor=4):
    if not pygame.mixer.get_init():
        raise RuntimeError("오디오 믹서가 초기화되지 않았습니다.")
    sample_rate, sample_format, channels = pygame.mixer.get_init()
    if sample_format != -16:
        raise RuntimeError("분석에는 16-bit 오디오 믹서가 필요합니다.")

    sound = pygame.mixer.Sound(path)
    raw = sound.get_raw()
    del sound
    pcm = array("h")
    pcm.frombytes(raw)
    if sys.byteorder != "little":
        pcm.byteswap()

    frames = len(pcm) // channels
    usable_frames = frames - (frames % factor)
    mono = array("h")
    for first in range(0, usable_frames, factor):
        total = 0
        for frame in range(first, first + factor):
            index = frame * channels
            if channels == 1:
                total += pcm[index]
            else:
                total += (pcm[index] + pcm[index + 1]) // 2
        mono.append(total // factor)
    del pcm
    return mono, sample_rate // factor


def _fft(real, imag, bit_reversed):
    size = len(real)
    reordered_real = [real[index] for index in bit_reversed]
    reordered_imag = [imag[index] for index in bit_reversed]
    block_size = 2
    while block_size <= size:
        half = block_size // 2
        angle = -2.0 * math.pi / block_size
        step_real, step_imag = math.cos(angle), math.sin(angle)
        for block in range(0, size, block_size):
            weight_real, weight_imag = 1.0, 0.0
            for offset in range(half):
                even = block + offset
                odd = even + half
                odd_real = reordered_real[odd] * weight_real - reordered_imag[odd] * weight_imag
                odd_imag = reordered_real[odd] * weight_imag + reordered_imag[odd] * weight_real
                even_real, even_imag = reordered_real[even], reordered_imag[even]
                reordered_real[even] = even_real + odd_real
                reordered_imag[even] = even_imag + odd_imag
                reordered_real[odd] = even_real - odd_real
                reordered_imag[odd] = even_imag - odd_imag
                next_real = weight_real * step_real - weight_imag * step_imag
                weight_imag = weight_real * step_imag + weight_imag * step_real
                weight_real = next_real
        block_size *= 2
    return reordered_real, reordered_imag


def _spectral_flux(samples, frame_size=512, hop_size=256):
    if len(samples) < frame_size:
        raise ValueError("분석할 수 있는 오디오 길이가 부족합니다.")
    half = frame_size // 2
    window = [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (frame_size - 1)) for i in range(frame_size)]
    bits = int(math.log2(frame_size))
    bit_reversed = []
    for value in range(frame_size):
        result, source = 0, value
        for _ in range(bits):
            result = (result << 1) | (source & 1)
            source >>= 1
        bit_reversed.append(result)

    previous = [0.0] * (half + 1)
    flux, frame_energy = [], []
    for start in range(0, len(samples) - frame_size + 1, hop_size):
        real = [samples[start + i] * window[i] for i in range(frame_size)]
        imag = [0.0] * frame_size
        fft_real, fft_imag = _fft(real, imag, bit_reversed)
        current = [0.0] * (half + 1)
        energy = 0.0
        for band in range(2, min(190, half + 1)):
            magnitude = math.log1p(math.hypot(fft_real[band], fft_imag[band]))
            current[band] = magnitude
            energy += magnitude
        if flux:
            novelty = 0.0
            for band in range(2, min(190, half + 1)):
                novelty += max(0.0, current[band] - previous[band]) / math.sqrt(band)
            flux.append(novelty)
        else:
            flux.append(0.0)
        frame_energy.append(energy)
        previous = current
    return flux, frame_energy


def _tempo_and_phase(flux, hop_seconds, preferred_bpm):
    mean = sum(flux) / len(flux)
    signal = [value - mean for value in flux]
    min_lag = max(2, int((60.0 / 220.0) / hop_seconds))
    max_lag = min(len(signal) // 3, int((60.0 / 55.0) / hop_seconds))
    correlations = {}
    for lag in range(min_lag, max_lag + 1):
        left, right = signal[lag:], signal[:-lag]
        numerator = sum(a * b for a, b in zip(left, right))
        norm = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right) + 1e-12)
        correlations[lag] = numerator / norm

    rows = []
    for lag, score in sorted(correlations.items(), key=lambda pair: pair[1], reverse=True):
        candidate = 60.0 / (lag * hop_seconds)
        if all(abs(candidate - row[0]) >= 2.0 for row in rows):
            rows.append((candidate, lag, score))
        if len(rows) >= 8:
            break
    if not rows:
        raise ValueError("안정적인 BPM 후보를 찾지 못했습니다.")

    selected = rows
    if preferred_bpm and math.isfinite(preferred_bpm) and preferred_bpm > 0:
        near = [row for row in rows if abs(row[0] / preferred_bpm - 1.0) <= 0.15]
        if near:
            selected = near
    _, peak, confidence = max(selected, key=lambda row: row[2])
    before = correlations.get(peak - 1, correlations[peak])
    center = correlations[peak]
    after = correlations.get(peak + 1, center)
    denominator = before - 2.0 * center + after
    fraction = 0.5 * (before - after) / denominator if abs(denominator) > 1e-12 else 0.0
    refined_lag = peak + max(-0.5, min(0.5, fraction))
    period_frames = refined_lag
    period_seconds = period_frames * hop_seconds

    phase_step = 0.25
    phase_count = max(1, int(math.ceil(period_frames / phase_step)))
    best_phase, best_score = 0.0, float("-inf")
    for phase_index in range(phase_count):
        phase = phase_index * phase_step
        cursor = phase
        total, count = 0.0, 0
        while cursor < len(flux):
            nearest = int(round(cursor))
            local_peak = max(flux[max(0, nearest - 1):min(len(flux), nearest + 2)])
            total += local_peak
            count += 1
            cursor += period_frames
        score = total / max(1, count)
        if score > best_score:
            best_phase, best_score = phase, score

    alternatives = [60.0 / (lag * hop_seconds) for _, lag, _ in rows[:3]]
    return 60.0 / period_seconds, best_phase * hop_seconds, confidence, alternatives, period_frames


def _find_onsets(flux, hop_seconds):
    count = len(flux)
    prefix = [0.0] * (count + 1)
    squares = [0.0] * (count + 1)
    for i, value in enumerate(flux):
        prefix[i + 1] = prefix[i] + value
        squares[i + 1] = squares[i] + value * value
    radius = max(3, round(0.45 / hop_seconds))
    floor = sorted(flux)[int(0.55 * (count - 1))]
    raw = []
    for i in range(2, count - 2):
        if not (flux[i] >= flux[i - 1] and flux[i] > flux[i + 1]):
            continue
        lo, hi = max(0, i - radius), min(count, i + radius + 1)
        n = hi - lo
        average = (prefix[hi] - prefix[lo]) / n
        variance = max(0.0, (squares[hi] - squares[lo]) / n - average * average)
        threshold = max(floor * 1.25, average + 0.8 * math.sqrt(variance))
        if flux[i] > threshold:
            strength = (flux[i] - average) / (math.sqrt(variance) + 1e-9)
            raw.append((i, strength, flux[i]))

    # Remove duplicate detections around a single transient, keeping the
    # strongest peak in each short refractory window.
    gap = max(2, round(0.065 / hop_seconds))
    selected = []
    for item in sorted(raw, key=lambda x: x[2], reverse=True):
        if all(abs(item[0] - prev[0]) >= gap for prev in selected):
            selected.append(item)
    return sorted(selected)


def _select_quantized_onsets(onsets, bpm, offset, hop_seconds, level):
    beat_seconds = 60.0 / bpm
    by_slot = {}
    for frame, strength, peak in onsets:
        seconds = frame * hop_seconds
        beat = (seconds - offset) / beat_seconds
        if beat < 0:
            continue
        slot = round(beat * 4.0)
        quantized = slot / 4.0
        if abs(beat - quantized) > 0.16:
            continue
        previous = by_slot.get(slot)
        if previous is None or strength > previous["strength"]:
            by_slot[slot] = {"beat": quantized, "strength": strength, "frame": frame, "peak": peak}

    if not by_slot:
        return []
    per_bar = 2 if level <= 2 else 3 if level <= 5 else 4 if level <= 8 else 5
    bars = {}
    for item in by_slot.values():
        bar = int(item["beat"] // 4)
        bars.setdefault(bar, []).append(item)
    chosen = []
    for bar_items in bars.values():
        bar_items.sort(key=lambda item: item["strength"] + (0.3 if item["beat"] % 4.0 < 0.25 else 0.0), reverse=True)
        chosen.extend(bar_items[:per_bar])
    return sorted(chosen, key=lambda item: item["beat"])


def _make_note_events(selected, frame_energy, bpm, hop_seconds, level):
    if not selected:
        return []
    beat_seconds = 60.0 / bpm
    strengths = sorted(item["strength"] for item in selected)
    strong_cutoff = strengths[int(0.72 * (len(strengths) - 1))]
    events = []
    i = 0
    while i < len(selected):
        item = selected[i]
        next_item = selected[i + 1] if i + 1 < len(selected) else None
        next_beat = next_item["beat"] if next_item else item["beat"] + 4.0
        gap_beats = next_beat - item["beat"]

        if level >= 3 and item["strength"] >= strong_cutoff and gap_beats >= 1.25:
            frame = item["frame"]
            duration_frames = max(1, round(0.7 * beat_seconds / hop_seconds))
            end = min(len(frame_energy), frame + duration_frames)
            start_energy = max(1e-9, frame_energy[min(frame, len(frame_energy) - 1)])
            sustain = sum(frame_energy[frame:end]) / max(1, end - frame) / start_energy
            if sustain >= 0.52:
                hold_beats = min(2.0, gap_beats - 0.25)
                hold_beats = max(1.0, round(hold_beats * 4.0) / 4.0)
                events.append({"type": "HOLD", "beat": item["beat"], "end_beat": item["beat"] + hold_beats,
                               "strength": item["strength"]})
                i += 1
                continue
        events.append({"type": "TAP", "beat": item["beat"], "strength": item["strength"]})
        i += 1

    # Turn a small portion of close, related attacks into a short slide phrase.
    if level >= 5:
        converted = []
        index = 0
        while index < len(events):
            current = events[index]
            following = events[index + 1] if index + 1 < len(events) else None
            gap = following["beat"] - current["beat"] if following else 0.0
            phrase_slot = int(round(current["beat"] * 4.0))
            if (following and current["type"] == following["type"] == "TAP"
                    and 0.5 <= gap <= 1.0 and phrase_slot % 7 == level % 7):
                converted.append({"type": "SLIDE", "beat": current["beat"], "end_beat": following["beat"],
                                  "strength": (current["strength"] + following["strength"]) * 0.5})
                index += 2
            else:
                converted.append(current)
                index += 1
        events = converted
    return events


def _optimize_lanes(events, level):
    if not events:
        return []
    beam = [(0.0, -1, (0, 0, 0, 0), ())]
    beam_width = 32
    for index, note in enumerate(events):
        next_beam = []
        beat_phase = note["beat"] % 4.0
        strong = note["strength"]
        for cost, previous_lane, counts, path in beam:
            for lane in range(4):
                preference = 0.0
                if beat_phase < 0.25:
                    preference += 0.0 if lane in (0, 3) else 0.55
                elif abs(beat_phase - 2.0) < 0.25:
                    preference += 0.0 if lane in (1, 2) else 0.25
                else:
                    preferred = (int(note["beat"] * 2 + level) % 4)
                    preference += abs(lane - preferred) * 0.14
                # Make prominent attacks more likely to land on the outer lanes.
                if strong > 1.0:
                    preference += 0.15 if lane in (1, 2) else 0.0
                transition = 0.0
                if previous_lane >= 0:
                    distance = abs(lane - previous_lane)
                    gap = note["beat"] - events[index - 1]["beat"]
                    transition += distance * 0.28
                    if distance == 0:
                        transition += 2.2 if gap < 0.75 else 0.8 if gap < 1.5 else 0.2
                    if distance == 3:
                        transition += 0.45
                balance = counts[lane] * 0.12
                new_counts = tuple(value + (1 if slot == lane else 0) for slot, value in enumerate(counts))
                tie_break = ((index * 17 + lane * 11) % 7) * 0.001
                next_beam.append((cost + preference + transition + balance + tie_break,
                                  lane, new_counts, path + (lane,)))
        next_beam.sort(key=lambda row: row[0])
        beam = next_beam[:beam_width]

    lanes = list(min(beam, key=lambda row: row[0])[3])
    output = []
    lane_counts = [lanes.count(lane) for lane in range(4)]
    for i, (event, lane) in enumerate(zip(events, lanes)):
        note = {"type": event["type"], "beat": round(event["beat"], 4), "lane": lane}
        if event["type"] == "HOLD":
            note["end_beat"] = round(event["end_beat"], 4)
        elif event["type"] == "SLIDE":
            next_lane = lanes[i + 1] if i + 1 < len(lanes) else None
            options = [candidate for candidate in range(4) if candidate != lane]
            if next_lane in options:
                end_lane = next_lane
            else:
                end_lane = min(options, key=lambda candidate: (lane_counts[candidate], abs(candidate - lane), candidate))
            note["end_beat"] = round(event["end_beat"], 4)
            note["end_lane"] = end_lane
        output.append(note)
    return output


def generate_auto_chart(path, preferred_bpm=120.0, level=5):
    """Run STFT -> spectral flux -> onset -> beat grid -> starter chart."""
    samples, sample_rate = _downsample_mono(path)
    frame_size, hop_size = 512, 256
    hop_seconds = hop_size / sample_rate
    flux, frame_energy = _spectral_flux(samples, frame_size, hop_size)
    bpm, offset, confidence, alternatives, _ = _tempo_and_phase(flux, hop_seconds, preferred_bpm)
    onsets = _find_onsets(flux, hop_seconds)
    selected = _select_quantized_onsets(onsets, bpm, offset, hop_seconds, level)
    events = _make_note_events(selected, frame_energy, bpm, hop_seconds, level)
    notes = _optimize_lanes(events, level)
    counts = {kind: sum(note["type"] == kind for note in notes) for kind in ("TAP", "HOLD", "SLIDE")}
    return {
        "bpm": bpm,
        "offset": offset,
        "confidence": confidence,
        "alternatives": alternatives,
        "onset_count": len(onsets),
        "selected_count": len(selected),
        "notes": notes,
        "type_counts": counts,
    }
