"""Time-based hold/slide judgement independent of rendering and score effects."""

from dataclasses import dataclass

HEAD_WINDOW = 0.23
HEAD_PERFECT = 0.07
SLIDE_TOLERANCE = 0.78
TOUCH_SLIDE_TOLERANCE = 0.90
SLIDE_TRANSFER_GRACE = 0.08
MIN_COVERAGE = 0.85
MIN_CONTINUOUS_HOLD = 0.06
TAIL_EARLY_WINDOW = 0.06
TAIL_PERFECT = 0.035
EPSILON = 1e-7


@dataclass(frozen=True)
class TouchContact:
    """Continuous position measured in lane widths; integer centers are lanes."""

    pointer: object
    position: float
    lane: int


def contact_position(contact):
    return contact.position if isinstance(contact, TouchContact) else contact


def contact_tolerance(contact):
    return TOUCH_SLIDE_TOLERANCE if isinstance(contact, TouchContact) else SLIDE_TOLERANCE


class SustainJudge:
    def __init__(self, note, tick_times):
        self.start = note["time"]
        self.end = note["end_time"]
        self.lane = note["lane"]
        self.end_lane = note.get("end_lane", self.lane)
        self.slide = note["type"] == "SLIDE"
        self.ticks = tick_times
        self.head_done = False
        self.head_contact_time = self.start
        self.next_tick = 1
        self.connected = False
        self.finished = False
        self.tail_hit = False
        self.sample_time = None
        self.lanes = frozenset()
        self.runs = []
        self.contact = False
        self.gap_since = None

    def position(self, when):
        ratio = max(0.0, min(1.0, (when - self.start) / max(EPSILON, self.end - self.start)))
        return self.lane + (self.end_lane - self.lane) * ratio

    def matches(self, lanes, when):
        if not self.slide:
            return any((lane.lane if isinstance(lane, TouchContact) else lane) == self.lane
                       for lane in lanes)
        position = self.position(when)
        return any(abs(contact_position(lane) - position) <= contact_tolerance(lane)
                   for lane in lanes)

    def _lose_contact(self, when):
        self.contact = False
        if self.gap_since is None:
            self.gap_since = when
        if not self.slide or when - self.gap_since > SLIDE_TRANSFER_GRACE + EPSILON:
            self.connected = False

    def _record_contact(self, first, last):
        if not self.connected or last <= first:
            return
        if self.contact and self.runs and abs(self.runs[-1][1] - first) < EPSILON:
            self.runs[-1][1] = last
        else:
            self.runs.append([first, last])
        self.contact = True
        self.gap_since = None

    def _contact_intervals(self, first, last, lanes):
        if not self.slide or self.lane == self.end_lane:
            return [(first, last)] if self.matches(lanes, first) else []
        # Intersect the moving path with each held lane, including between frames.
        velocity = (self.end_lane - self.lane) / (self.end - self.start)
        spans = []
        for lane in lanes:
            position, tolerance = contact_position(lane), contact_tolerance(lane)
            a = self.start + (position - tolerance - self.lane) / velocity
            b = self.start + (position + tolerance - self.lane) / velocity
            lo, hi = max(first, min(a, b)), min(last, max(a, b))
            if hi > lo:
                spans.append((lo, hi))
        merged = []
        for lo, hi in sorted(spans):
            if merged and lo <= merged[-1][1] + EPSILON:
                merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
            else:
                merged.append((lo, hi))
        return merged

    def _advance_contact(self, first, last):
        first, last = max(first, self.start), min(last, self.end)
        if last <= first:
            return
        cursor = first
        for lo, hi in self._contact_intervals(first, last, self.lanes):
            if lo > cursor + EPSILON:
                self._lose_contact(cursor)
                self._lose_contact(lo)
            self._record_contact(lo, hi)
            cursor = hi
        if cursor < last - EPSILON:
            self._lose_contact(cursor)
            self._lose_contact(last)

    def _set_lanes(self, lanes, when):
        self.lanes = frozenset(lanes)
        if not self.matches(self.lanes, when):
            # Preserve a zero-duration up/down edge as a new run as well.
            self._lose_contact(when)
        elif self.gap_since is not None:
            grace = SLIDE_TRANSFER_GRACE if self.slide else 0.0
            if when - self.gap_since > grace + EPSILON:
                self.connected = False

    def _coverage(self, first, last):
        if last <= first + EPSILON:
            return 1.0
        covered = sum(max(0.0, min(last, b) - max(first, a)) for a, b in self.runs)
        return min(1.0, covered / (last - first))

    def _body_hit(self, previous, tick):
        previous = max(previous, self.head_contact_time)
        streak = min(MIN_CONTINUOUS_HOLD, (tick - previous) * MIN_COVERAGE)
        continuous = any(a <= tick - streak + EPSILON and b >= tick - EPSILON
                         for a, b in self.runs)
        return continuous and self._coverage(previous, tick) >= MIN_COVERAGE - EPSILON

    def _tail_grade(self, previous):
        previous = max(previous, self.head_contact_time)
        for first, last in reversed(self.runs):
            release = min(last, self.end)
            early = self.end - release
            if early > TAIL_EARLY_WINDOW + EPSILON:
                break
            required = min(0.08, (self.end - self.start) * MIN_COVERAGE)
            if release - first < required - EPSILON:
                continue
            if self._coverage(previous, release) < MIN_COVERAGE - EPSILON:
                continue
            return "PERFECT" if early <= TAIL_PERFECT + EPSILON else "GREAT"
        return "MISS"

    def update(self, now, initial_lanes, changes):
        """Consume (song_time, held_lanes, fresh_press_lanes) changes in order.

        Each head/body/tail emits one grade. A rejoin only starts a new contact
        interval; it never awards time before that press.
        """
        if self.finished:
            return []
        grades = []
        if self.sample_time is None:
            self.sample_time = min(now, changes[0][0]) if changes else now
        cursor = self.sample_time
        self._set_lanes(initial_lanes, cursor)
        for when, lanes, fresh in changes:
            when = max(cursor, min(now, when))
            self._advance_contact(cursor, when)
            self._set_lanes(lanes, when)
            if fresh and self.start - HEAD_WINDOW <= when < self.end and self.matches(fresh, when):
                joining = not self.connected
                hitting_head = not self.head_done and abs(when - self.start) <= HEAD_WINDOW
                if joining or hitting_head:
                    lane = min((lane for lane in fresh if self.matches((lane,), when)),
                               key=lambda lane: abs(lane - self.position(when)))
                    fresh.discard(lane)
                if not self.connected:
                    self.connected = True
                    self.contact = False
                    self.gap_since = None
                if hitting_head:
                    grades.append("PERFECT" if abs(when - self.start) <= HEAD_PERFECT else "GREAT")
                    self.head_contact_time = max(self.start, when)
                    self.head_done = True
            cursor = when
        self._advance_contact(cursor, now)
        self.sample_time = now
        if not self.head_done and (now > self.start + HEAD_WINDOW or now >= self.end):
            self.head_done = True
            grades.append("MISS")
        # Keep head/body results ordered even when the head's late window spans a tick.
        if self.head_done:
            while self.next_tick < len(self.ticks) and self.ticks[self.next_tick] <= now + EPSILON:
                tick = self.ticks[self.next_tick]
                previous = self.ticks[self.next_tick - 1]
                if self.next_tick == len(self.ticks) - 1:
                    grade = self._tail_grade(previous)
                    self.tail_hit = grade != "MISS"
                else:
                    grade = "PERFECT" if self._body_hit(previous, tick) else "MISS"
                grades.append(grade)
                self.next_tick += 1
        if now >= self.end:
            self.finished = True
            self.connected = False
        return grades
