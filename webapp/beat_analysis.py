"""Lightweight BPM and beat-phase estimation from an OGG file.

This uses only Pygame's decoder and the Python standard library so the game
does not need NumPy, librosa, or an internet connection.
"""
from array import array
import math
import sys

import pygame


def analyze_audio(path, preferred_bpm=None, min_bpm=55.0, max_bpm=220.0, hop_seconds=0.01):
    """Return an estimated (bpm, offset_seconds, confidence, alternatives).

    The estimate is based on positive changes in short-window signal energy,
    followed by autocorrelation. It works best for songs with a steady tempo;
    half/double-time interpretations are common in music and should be checked
    by listening before saving a chart.
    """
    if not pygame.mixer.get_init():
        raise RuntimeError("오디오 믹서가 초기화되지 않았습니다.")

    sample_rate, sample_format, channels = pygame.mixer.get_init()
    if sample_format != -16:
        raise RuntimeError("자동 분석에는 16-bit 오디오 믹서가 필요합니다.")

    sound = pygame.mixer.Sound(path)
    raw = sound.get_raw()
    del sound

    pcm = array("h")
    pcm.frombytes(raw)
    if sys.byteorder != "little":
        pcm.byteswap()
    if channels < 1 or len(pcm) < channels * sample_rate * 8:
        raise ValueError("곡 파일이 비어 있거나 너무 짧습니다.")

    frame_count = len(pcm) // channels
    hop_frames = max(1, round(sample_rate * hop_seconds))
    frames_per_sample = 4  # Downsample the energy scan to about 11 kHz.
    energies = []
    for first in range(0, frame_count, hop_frames):
        last = min(frame_count, first + hop_frames)
        total = 0.0
        count = 0
        for frame in range(first, last, frames_per_sample):
            sample_index = frame * channels
            if channels == 1:
                mono = pcm[sample_index]
            else:
                mono = (pcm[sample_index] + pcm[sample_index + 1]) * 0.5
            total += mono * mono
            count += 1
        energies.append(math.log1p(math.sqrt(total / max(1, count))))
    del pcm

    if len(energies) < 100:
        raise ValueError("박자를 분석할 만큼 오디오가 길지 않습니다.")

    # Positive energy changes emphasize drum and note onsets over sustained
    # loudness. Subtracting a short local baseline reduces gradual dynamics.
    onset = [0.0] * len(energies)
    for index in range(1, len(energies)):
        begin = max(0, index - 4)
        baseline = sum(energies[begin:index]) / (index - begin)
        onset[index] = max(0.0, energies[index] - baseline)
    mean_onset = sum(onset) / len(onset)
    signal = [value - mean_onset for value in onset]

    min_lag = max(2, int((60.0 / max_bpm) / hop_seconds))
    max_lag = min(len(signal) // 3, int((60.0 / min_bpm) / hop_seconds))
    correlations = {}
    for lag in range(min_lag, max_lag + 1):
        left = signal[lag:]
        right = signal[:-lag]
        numerator = sum(a * b for a, b in zip(left, right))
        left_energy = sum(a * a for a in left)
        right_energy = sum(b * b for b in right)
        correlations[lag] = numerator / math.sqrt(left_energy * right_energy + 1e-12)

    if not correlations:
        raise ValueError("유효한 박자 후보를 찾지 못했습니다.")
    candidate_rows = []
    for lag, score in sorted(correlations.items(), key=lambda pair: pair[1], reverse=True):
        candidate = 60.0 / (lag * hop_seconds)
        if all(abs(candidate - row[0]) >= 2.0 for row in candidate_rows):
            candidate_rows.append((candidate, lag, score))
        if len(candidate_rows) == 8:
            break

    selected_rows = candidate_rows
    # Beat trackers often return half-time or double-time. If the chart already
    # has a BPM hint, use it only to resolve that common octave ambiguity.
    if preferred_bpm and math.isfinite(preferred_bpm) and preferred_bpm > 0:
        near_hint = [row for row in candidate_rows if abs(row[0] / preferred_bpm - 1.0) <= 0.15]
        if near_hint:
            selected_rows = near_hint
    _, peak_lag, selected_score = max(selected_rows, key=lambda row: row[2])
    # Parabolic interpolation improves the tempo resolution between 10 ms bins.
    before = correlations.get(peak_lag - 1, correlations[peak_lag])
    center = correlations[peak_lag]
    after = correlations.get(peak_lag + 1, center)
    denominator = before - 2.0 * center + after
    fraction = 0.5 * (before - after) / denominator if abs(denominator) > 1e-12 else 0.0
    refined_lag = peak_lag + max(-0.5, min(0.5, fraction))
    period_seconds = refined_lag * hop_seconds
    bpm = 60.0 / period_seconds

    # Find the phase that places the beat grid over the strongest repeating
    # onsets. Search at 2.5 ms steps and average across the whole track.
    period_bins = period_seconds / hop_seconds
    phase_step = 0.25
    phase_count = max(1, int(math.ceil(period_bins / phase_step)))
    best_phase = 0.0
    best_phase_score = float("-inf")
    for phase_index in range(phase_count):
        phase = phase_index * phase_step
        cursor = phase
        total, count = 0.0, 0
        while cursor < len(onset):
            nearest = int(round(cursor))
            if 0 <= nearest < len(onset):
                total += onset[nearest]
                count += 1
            cursor += period_bins
        score = total / max(1, count)
        if score > best_phase_score:
            best_phase_score = score
            best_phase = phase

    alternatives = [bpm]
    for row in candidate_rows:
        if abs(row[0] - bpm) >= 2.0:
            alternatives.append(row[0])
        if len(alternatives) == 3:
            break

    return bpm, best_phase * hop_seconds, selected_score, alternatives
