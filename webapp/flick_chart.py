"""Place ordinary MASTER flicks on existing musical attacks.

This pass never creates a note or changes its time/lane. It selects accents and
phrase endings from an already analyzed chart. It is deliberately conservative:
a flick gesture needs space before the next attack, even on very fast songs.
"""
from bisect import bisect_left, bisect_right
from collections import Counter
from copy import deepcopy
import math

MASTER_FLICK_REVISION = "20261005-master-flick-v1"
MIN_FLICK_GAP = 0.85
MIN_PREVIOUS_GAP = 0.105
MIN_NEXT_GAP = 0.180
MIN_LANE_GAP = 0.240
SUSTAIN_CLEARANCE = 0.120
MAX_FLICK_SHARE = 0.055
EPSILON = 1e-7


def _candidates(notes, bpm, offset, song_key):
    beat_seconds = 60.0 / bpm
    timed = [(offset + float(note["beat"]) * beat_seconds, index, note)
             for index, note in enumerate(notes)]
    ordered = sorted(timed, key=lambda row: (row[0], row[1]))
    times = [row[0] for row in ordered]
    lane_times = {lane: [] for lane in range(4)}
    sustains = []
    for when, _, note in ordered:
        lane_times.setdefault(int(note["lane"]), []).append(when)
        if note["type"] in ("HOLD", "SLIDE"):
            end = offset + float(note["end_beat"]) * beat_seconds
            sustains.append((when - SUSTAIN_CLEARANCE, end + SUSTAIN_CLEARANCE))
    candidates = []
    for position, (when, index, note) in enumerate(ordered):
        if note["type"] != "TAP":
            continue
        if song_key == "hatsune-miku-no-shoushitsu" and when < 25.0:
            continue
        previous_gap = when - times[position - 1] if position else 2.0 * beat_seconds
        next_gap = times[position + 1] - when if position + 1 < len(times) else 2.0 * beat_seconds
        # Chords automatically fail these gaps. Keep each new flick a single
        # gesture so SPACE never has to distinguish two near-simultaneous ones.
        if previous_gap + EPSILON < MIN_PREVIOUS_GAP or next_gap + EPSILON < MIN_NEXT_GAP:
            continue
        nearby = lane_times[int(note["lane"])]
        first = bisect_right(nearby, when - MIN_LANE_GAP + EPSILON)
        last = bisect_left(nearby, when + MIN_LANE_GAP - EPSILON)
        if last - first != 1:
            continue
        # Even an unrelated slide can occupy a second finger or cross this lane.
        # There are ample free attacks, so prefer them over ambiguous gestures.
        if any(start - EPSILON <= when <= end + EPSILON for start, end in sustains):
            continue
        beat = float(note["beat"])
        whole_distance = abs(beat - round(beat))
        half_distance = abs(beat * 2.0 - round(beat * 2.0)) / 2.0
        accent = max(0.0, 1.0 - whole_distance / 0.08)
        half_accent = max(0.0, 1.0 - half_distance / 0.04)
        # Gaps after an attack are evidence of a phrase ending. Quarter-note
        # accents add weight, but an off-grid analyzed onset stays off-grid.
        phrase_end = min(2.5, next_gap / beat_seconds)
        phrase_contrast = min(2.0, next_gap / max(previous_gap, 0.05))
        local_count = (bisect_right(times, when + 0.5)
                       - bisect_left(times, when - 0.5))
        score = (1.8 * phrase_end + 0.55 * phrase_contrast
                 + 1.25 * accent + 0.35 * half_accent
                 - 0.12 * max(0, local_count - 4))
        # Sections distribute gestures across the track; they never determine
        # timestamps. Every selected beat still comes from an existing attack.
        section = math.floor(beat / 16.0)
        candidates.append((score, when, index, section))
    return candidates


def add_master_flicks(notes, bpm, offset=0.0, song_key=""):
    """Return copied notes with a modest subset of TAPs changed to FLICK.

    Call only for MASTER. Existing flicks are kept and count toward the quota,
    making repeat calls idempotent. All other fields and list order are intact.
    """
    bpm, offset = float(bpm), float(offset)
    if not math.isfinite(bpm) or bpm <= 0.0 or not math.isfinite(offset):
        raise ValueError("Flick placement requires a positive finite BPM and finite offset")
    result = deepcopy(notes)
    attacks = sum(note["type"] in ("TAP", "FLICK") for note in result)
    if not attacks:
        return result
    target = max(1, min(80, int(attacks * MAX_FLICK_SHARE + 0.5)))
    selected = sorted(offset + float(note["beat"]) * 60.0 / bpm
                      for note in result if note["type"] == "FLICK")
    if len(selected) >= target:
        return result
    section_counts = Counter(math.floor(float(note["beat"]) / 16.0)
                             for note in result if note["type"] == "FLICK")
    candidates = _candidates(result, bpm, offset, song_key)
    grouped = {}
    for candidate in sorted(candidates, key=lambda row: (-row[0], row[1], row[2])):
        grouped.setdefault(candidate[3], []).append(candidate)
    # Give each section its strongest eligible attack before selecting a second
    # one. The rankings depend on rhythmic context, not note ordinal patterns.
    ranked = []
    for rank in range(2):
        rows = [items[rank] for items in grouped.values() if len(items) > rank]
        ranked.extend(sorted(rows, key=lambda row: (-row[0], row[1], row[2])))
    # A section's first two can be too close together; retain lower-ranked
    # alternatives so the spacing rule does not discard the entire phrase.
    ranked.extend(sorted((row for rows in grouped.values() for row in rows[2:]),
                         key=lambda row: (-row[0], row[1], row[2])))
    for _, when, index, section in ranked:
        if len(selected) >= target:
            break
        if section_counts[section] >= 2:
            continue
        if any(abs(when - previous) + EPSILON < MIN_FLICK_GAP for previous in selected):
            continue
        result[index]["type"] = "FLICK"
        selected.append(when)
        section_counts[section] += 1
    return result
