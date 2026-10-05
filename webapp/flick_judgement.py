"""Timestamped, rendering-independent input and judgement for normal flicks.

All times are seconds on the audio song clock. Touch coordinates use the
game's logical 800 x 480 canvas; browser/device pixels must be scaled first.
A flick is a fresh SPACE edge with selected lanes, or one upward touch stroke.
"""

from dataclasses import dataclass, field
import math


PERFECT_WINDOW = 0.070
GREAT_WINDOW = 0.150
KEY_CHORD_GRACE = 0.040
EPSILON = 1e-7
SWIPE_DISTANCE = 12.0
SWIPE_WINDOW = 0.100
SWIPE_MIN_SPEED = 140.0
SWIPE_MAX_SIDE_RATIO = 1.20
REARM_DOWN_DISTANCE = 12.0
REARM_SETTLE_TIME = 0.120
REARM_SETTLE_RADIUS = 4.0


@dataclass
class FlickIntent:
    time: float
    lanes: frozenset
    consumed_lanes: set = field(default_factory=set)

    def __post_init__(self):
        self.time = float(self.time)
        self.lanes = frozenset(lane for lane in self.lanes if lane in range(4))


def flick_grade(delta):
    """Grade a signed timing error, including both exact window boundaries."""
    distance = abs(delta)
    if distance <= PERFECT_WINDOW + EPSILON:
        return "PERFECT"
    if distance <= GREAT_WINDOW + EPSILON:
        return "GREAT"
    return "MISS"


class KeyboardFlickInput:
    """One SPACE press can flick each selected lane exactly once.

    Lane keys may already be held. A lane arriving at most 40 ms after SPACE
    is accepted at the SPACE timestamp to tolerate keyboard chord ordering.
    Holding SPACE does not turn subsequent lane taps into repeated flicks.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.held_lanes = set()
        self.space_held = False
        self.space_time = None
        self.stroke_lanes = set()

    def lane_down(self, lane, when):
        if lane not in range(4) or lane in self.held_lanes:
            return []
        self.held_lanes.add(lane)
        if (self.space_held and self.space_time is not None
                and -EPSILON <= when - self.space_time <= KEY_CHORD_GRACE + EPSILON
                and lane not in self.stroke_lanes):
            self.stroke_lanes.add(lane)
            return [FlickIntent(self.space_time, frozenset((lane,)))]
        return []

    def lane_up(self, lane, when):
        self.held_lanes.discard(lane)
        return []

    def space_down(self, when):
        if self.space_held:
            return []
        self.space_held = True
        self.space_time = float(when)
        self.stroke_lanes = set(self.held_lanes)
        if self.stroke_lanes:
            return [FlickIntent(when, frozenset(self.stroke_lanes))]
        return []

    def space_up(self, when):
        self.space_held = False
        self.space_time = None
        self.stroke_lanes.clear()
        return []


class TouchFlickInput:
    """Independent upward-swipe recognition for every active pointer.

    Detection uses a sliding 100 ms motion window, not render-frame counts.
    A 12 logical-pixel upward stroke must have enough upward speed and a
    reasonable diagonal angle. Its event time is the interpolated distance
    crossing, not the frame in which it was delivered. Continuous movement
    cannot repeat: rearming needs 12 px downward reversal or sampled stillness.
    """

    def __init__(self):
        self.pointers = {}

    def reset(self):
        self.pointers.clear()

    def begin(self, pointer, x, y, when, lane):
        if lane not in range(4) or not all(math.isfinite(v) for v in (x, y, when)):
            self.pointers.pop(pointer, None)
            return []
        self.pointers[pointer] = {
            "lane": lane, "samples": [(float(when), float(x), float(y))],
            "armed": True, "min_y": float(y),
            "settle": (float(when), float(x), float(y)),
        }
        return []

    def end(self, pointer):
        self.pointers.pop(pointer, None)
        return []

    def move(self, pointer, x, y, when, lane=None):
        state = self.pointers.get(pointer)
        if state is None or not all(math.isfinite(v) for v in (x, y, when)):
            return []
        x, y, when = float(x), float(y), float(when)
        samples = state["samples"]
        previous = samples[-1]
        if when < previous[0] - EPSILON:
            return []
        if lane in range(4):
            state["lane"] = lane

        if not state["armed"]:
            state["min_y"] = min(state["min_y"], y)
            settled_at, settle_x, settle_y = state["settle"]
            if math.hypot(x - settle_x, y - settle_y) > REARM_SETTLE_RADIUS:
                state["settle"] = (when, x, y)
                settled = False
            else:
                settled = when - settled_at >= REARM_SETTLE_TIME - EPSILON
            reversed_down = y - state["min_y"] >= REARM_DOWN_DISTANCE - EPSILON
            state["samples"] = [(when, x, y)]
            if reversed_down or settled:
                state["armed"] = True
            return []

        samples.append((when, x, y))
        cutoff = when - SWIPE_WINDOW
        # Keep one point before the window and interpolate its boundary. This
        # makes a 30 Hz stream and a high-rate/coalesced stream agree in time.
        while len(samples) > 2 and samples[1][0] <= cutoff:
            samples.pop(0)
        if len(samples) >= 2 and samples[0][0] < cutoff:
            a, b = samples[0], samples[1]
            if b[0] > a[0] + EPSILON:
                amount = min(1.0, (cutoff - a[0]) / (b[0] - a[0]))
                samples[0] = (cutoff, a[1] + (b[1] - a[1]) * amount,
                              a[2] + (b[2] - a[2]) * amount)
            else:
                samples.pop(0)

        # Search possible recent anchors so a preceding sideways/downward
        # motion cannot suppress a subsequent genuine upward stroke.
        crossings = []
        for start_time, start_x, start_y in samples[:-1]:
            upward = start_y - y
            elapsed = when - start_time
            if upward < SWIPE_DISTANCE - EPSILON or elapsed < -EPSILON:
                continue
            if elapsed > EPSILON and upward / elapsed < SWIPE_MIN_SPEED - EPSILON:
                continue
            if abs(x - start_x) > upward * SWIPE_MAX_SIDE_RATIO + EPSILON:
                continue
            target_y = start_y - SWIPE_DISTANCE
            # Only a new crossing on the newest segment may activate. An
            # already-past threshold cannot fire later after sideways drift.
            before = samples[-2]
            if before[2] < target_y - EPSILON or y > target_y + EPSILON:
                continue
            distance = before[2] - y
            fraction = max(0.0, min(1.0, (before[2] - target_y) / distance)) if distance > EPSILON else 1.0
            crossing_time = before[0] + (when - before[0]) * fraction
            crossing_x = before[1] + (x - before[1]) * fraction
            crossing_elapsed = crossing_time - start_time
            if (crossing_elapsed > EPSILON
                    and SWIPE_DISTANCE / crossing_elapsed < SWIPE_MIN_SPEED - EPSILON):
                continue
            if abs(crossing_x - start_x) > SWIPE_DISTANCE * SWIPE_MAX_SIDE_RATIO + EPSILON:
                continue
            crossings.append(crossing_time)

        if not crossings:
            return []
        state["armed"] = False
        state["min_y"] = y
        state["settle"] = (when, x, y)
        state["samples"] = [(when, x, y)]
        return [FlickIntent(min(crossings), frozenset((state["lane"],)))]


def match_flick_intents(notes, intents, window=GREAT_WINDOW):
    """Resolve closest FLICK only; one note per lane per gesture, permanently.

    Intents are consumed even on a miss. They must never remain queued until a
    future note enters its hit window. Miss expiration remains the caller's
    responsibility, after all input intents for that frame have been applied.
    """
    available = {}
    for note in notes:
        if note["type"] == "FLICK" and not note.get("hit", False):
            available.setdefault(note["lane"], []).append(note)
    hits = []
    for intent in sorted(intents, key=lambda item: item.time):
        for lane in sorted(intent.lanes - intent.consumed_lanes):
            intent.consumed_lanes.add(lane)
            candidates = [note for note in available.get(lane, ())
                          if not note.get("hit", False)
                          and abs(note["time"] - intent.time) <= window + EPSILON]
            if not candidates:
                continue
            note = min(candidates, key=lambda item: (abs(item["time"] - intent.time), item["time"]))
            note["hit"] = True
            hits.append((note, note["time"] - intent.time, intent))
    return hits
