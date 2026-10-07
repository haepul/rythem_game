"""Keep authored timing while separating notes from occupied sustain paths."""

SUSTAINS = {"HOLD", "SLIDE"}
TIME_CLEARANCE = 0.055
LANE_CLEARANCE = 0.90  # A slide ribbon and a tap together span 0.86 lanes.
EPSILON = 1e-7


def note_end(note, time_key="time", end_key="end_time"):
    return note.get(end_key, note[time_key]) if note["type"] in SUSTAINS else note[time_key]


def lane_at(note, when, time_key="time", end_key="end_time"):
    if note["type"] != "SLIDE":
        return note["lane"]
    start, end = note[time_key], note[end_key]
    fraction = max(0.0, min(1.0, (when - start) / max(EPSILON, end - start)))
    return note["lane"] + (note["end_lane"] - note["lane"]) * fraction


def notes_overlap(first, second, time_key="time", end_key="end_time", seconds_per_unit=1.0):
    """Intersect complete linear paths, including crossings between endpoints."""
    start_a, start_b = first[time_key], second[time_key]
    if first["type"] not in SUSTAINS and second["type"] not in SUSTAINS:
        # Preserve fast alternating patterns; prevent duplicate/unplayable jacks.
        return (first["lane"] == second["lane"] and
                abs(start_a - start_b) * seconds_per_unit < TIME_CLEARANCE - EPSILON)
    end_a, end_b = note_end(first, time_key, end_key), note_end(second, time_key, end_key)
    padding = TIME_CLEARANCE / seconds_per_unit
    lo, hi = max(start_a, start_b) - padding, min(end_a, end_b) + padding
    if hi < lo - EPSILON:
        return False
    # Clamping at heads/tails introduces breakpoints. Between them relative
    # lane position is linear, so endpoints and zero crossings are sufficient.
    points = sorted({lo, hi, *(t for t in (start_a, end_a, start_b, end_b) if lo < t < hi)})
    distances = [lane_at(first, t, time_key, end_key) - lane_at(second, t, time_key, end_key)
                 for t in points]
    return (any(abs(distance) < LANE_CLEARANCE - EPSILON for distance in distances) or
            any(a * b < 0 for a, b in zip(distances, distances[1:])))


def _placements(note):
    """Prefer the original lane/path, then the smallest spatial adjustment."""
    if note["type"] == "SLIDE":
        paths = [(lane, end) for lane in range(4) for end in range(4) if lane != end]
        original_delta = note["end_lane"] - note["lane"]
        paths.sort(key=lambda pair: (
            abs(pair[0] - note["lane"]) + abs(pair[1] - note["end_lane"]),
            abs((pair[1] - pair[0]) - original_delta), pair))
        for lane, end in paths:
            yield {**note, "lane": lane, "end_lane": end}
    else:
        for lane in sorted(range(4), key=lambda lane: (abs(lane - note["lane"]), lane)):
            yield {**note, "lane": lane}


def resolve_note_overlaps(notes, time_key="time", end_key="end_time", seconds_per_unit=1.0):
    """Return copies with collision-free lanes; never move an onset in time.

    A sustain reserves its full path until its tail. In an overfilled custom
    chart, simplify an impossible slide to a hold, then a sustain to a tap.
    Only omit a note when all four lanes are occupied even for its onset.
    """
    output, active = [], []
    padding = 2 * TIME_CLEARANCE / seconds_per_unit
    ordered = sorted(notes, key=lambda note: (note[time_key], note["type"] not in SUSTAINS))
    for note in ordered:
        active = [other for other in active
                  if note_end(other, time_key, end_key) + padding >= note[time_key]]

        def fits(candidate):
            return not any(notes_overlap(candidate, other, time_key, end_key, seconds_per_unit)
                           for other in active)

        placed = next((candidate for candidate in _placements(note) if fits(candidate)), None)
        if placed is None and note["type"] == "SLIDE":
            hold = {key: value for key, value in note.items() if key != "end_lane"}
            hold["type"] = "HOLD"
            placed = next((candidate for candidate in _placements(hold) if fits(candidate)), None)
        if placed is None and note["type"] in SUSTAINS:
            tap = {key: value for key, value in note.items() if key not in {end_key, "end_lane"}}
            tap["type"] = "TAP"
            placed = next((candidate for candidate in _placements(tap) if fits(candidate)), None)
        if placed is not None:
            output.append(placed)
            active.append(placed)
    return output
