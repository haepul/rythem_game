"""Keep rapid presses distinct and match the nearest note on the pressed lane."""


def match_tap_presses(notes, presses, window):
    """Return (note, signed_delta, event_token) in chronological input order.

    Every press is [song_time, lane, consumed]. Expired earlier notes cannot
    capture a press intended for a closer note. Misses are resolved afterward.
    """
    hits = []
    available = {}
    for note in notes:
        if note['type'] == 'TAP' and not note['hit']:
            available.setdefault(note['lane'], []).append(note)
    for press in sorted(presses, key=lambda event: event[0]):
        when, lane, consumed = press
        if consumed:
            continue
        candidates = [note for note in available.get(lane, ())
                      if not note['hit'] and abs(note['time'] - when) <= window]
        if not candidates:
            continue
        note = min(candidates, key=lambda item: (abs(item['time'] - when), item['time']))
        # An eligible sustain head closer to this press gets first refusal.
        sustain_heads = [item for item in notes if item['type'] in ('HOLD', 'SLIDE') and not item['hit']
                         and not item['sustain_judge'].head_done
                         and when < item['end_time']
                         and item['sustain_judge'].matches((lane,), when)
                         and abs(item['time'] - when) < abs(note['time'] - when)]
        # A lane press/touch-down on a flick arms its gesture; it must not steal
        # an adjacent ordinary tile while waiting for SPACE or upward movement.
        flick_heads = [item for item in notes if item['type'] == 'FLICK' and not item['hit']
                       and item['lane'] == lane and abs(item['time'] - when) <= window
                       and abs(item['time'] - when) <= abs(note['time'] - when)]
        if sustain_heads or flick_heads:
            continue
        note['hit'] = True
        press[2] = True
        hits.append((note, note['time'] - when, press))
    return hits
