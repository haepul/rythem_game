"""Original glass/ribbon skin. Read-only rendering on the existing song clock."""
import math
from functools import lru_cache

import pygame


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def color_key(color):
    # Small colour buckets keep combo changes from creating unlimited textures.
    return tuple(min(255, round(c / 12) * 12) for c in color)


@lru_cache(maxsize=96)
def ribbon_palette(start, end):
    return tuple(mix(start, end, i / 32) for i in range(33))


@lru_cache(maxsize=128)
def glass_body(height, top, bottom, tail=False):
    """Share a canonical gradient across every perspective width."""
    width = 160
    scale, pad = 2, 5
    size = (width + pad * 2, height + pad * 2)
    image = pygame.Surface((size[0] * scale, size[1] * scale), pygame.SRCALPHA)
    x, y, w, h = pad * scale, pad * scale, width * scale, height * scale
    radius = max(2, h // 4)
    rect = pygame.Rect(x, y, w, h)
    for spread, alpha in ((4, 8), (2, 16)):
        pygame.draw.rect(image, (*bottom, alpha), rect.inflate(spread * 2, spread * 2),
                         border_radius=radius + spread)
    pygame.draw.rect(image, (9, 12, 30, 245), rect, border_radius=radius)
    # A bright centre, darker bevel and restrained coloured ends separate jacks.
    for row in range(2, h - 2):
        v = (row - 2) / max(1, h - 5)
        base = mix(top, bottom, v)
        base = mix(base, (255, 255, 255), .36 * math.sin(v * math.pi))
        inset = 3 + max(0, radius - min(row, h - 1 - row))
        band = max(4, math.ceil((w - inset * 2) / 16))
        for col in range(inset, w - inset, band):
            central = max(0, 1 - abs(col / w - .5) * 2)
            tint = mix(bottom, base, .60 + central * .40)
            pygame.draw.rect(image, (*tint, 245), (x + col, y + row, min(band, w - inset - col), 1))
    pygame.draw.rect(image, (*mix(top, (255, 255, 255), .60), 235),
                     rect.inflate(-2, -2), 1, border_radius=radius)
    pygame.draw.line(image, (255, 255, 255, 245), (x + radius, y + 3), (x + w - radius, y + 3), 2)
    pygame.draw.line(image, (*bottom, 240), (x + radius, y + h - 3), (x + w - radius, y + h - 3), 2)
    if tail:
        # A small terminal diamond identifies the independent release-end cap.
        cx, cy = x + w / 2, y + h / 2
        r = max(3, h * .28)
        pygame.draw.polygon(image, (33, 30, 65, 220), [(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)])
        pygame.draw.polygon(image, (255, 255, 255, 250), [(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)], 2)
    return pygame.transform.smoothscale(image, size)


@lru_cache(maxsize=384)
def glass_sprite(width, height, top, bottom, flick=False, tail=False):
    """Cache final sizes; resizing a shared gradient avoids a cold drawing burst."""
    body = pygame.transform.smoothscale(glass_body(height, top, bottom, tail), (width + 10, height + 10))
    if not flick:
        return body
    arrow_h = max(12, round(width * .17))
    size = (width + 10, height + 10 + arrow_h)
    scale = 2
    image = pygame.Surface((size[0] * scale, size[1] * scale), pygame.SRCALPHA)
    x, y, w = 10, (5 + arrow_h) * scale, width * scale
    if flick:
        cx = x + w / 2
        half = max(12, w * .145)
        rise = arrow_h * scale * .47
        for lift in (.12, .55):
            baseline = y - arrow_h * scale * lift
            pts = [(cx-half, baseline), (cx, baseline-rise), (cx+half, baseline)]
            stroke = max(4, round(height * .60))
            pygame.draw.lines(image, (62, 12, 49, 255), False, pts, stroke + 4)
            pygame.draw.lines(image, (255, 250, 255, 255), False, pts, stroke)
    result = pygame.transform.smoothscale(image, size)
    result.blit(body, (0, arrow_h))
    return result


class NoteRenderer:
    def __init__(self, project, size=(800, 480)):
        self.project = project
        self.ribbon_layer = pygame.Surface(size, pygame.SRCALPHA)

    def head(self, surface, lane, progress, top, bottom, width_scale=.40, flick=False, tail=False):
        if not 0 <= progress <= 1.15:
            return
        x, y, lane_width = self.project(lane, progress)
        width = max(18, round(lane_width * width_scale) * 2)
        # Thickness is visual, not a time interval: 6px at the horizon, 11px at the line.
        height = max(5, round(4 + lane_width * .038))
        if flick:
            top, bottom = (255, 206, 234), (249, 65, 143)
        sprite = glass_sprite(width, height, color_key(top), color_key(bottom), flick, tail)
        arrow_h = max(12, round(width * .17)) if flick else 0
        surface.blit(sprite, (round(x - sprite.get_width() / 2), round(y - height / 2 - 5 - arrow_h)))

    @staticmethod
    def lane_at(note, when):
        if note["type"] == "HOLD":
            return note["lane"]
        duration = max(1e-9, note["end_time"] - note["time"])
        ratio = max(0.0, min(1.0, (when - note["time"]) / duration))
        return note["lane"] + (note.get("end_lane", note["lane"]) - note["lane"]) * ratio

    def ribbon_points(self, note, now, approach):
        first = max(note["time"], now)
        last = min(note["end_time"], now + approach)
        if last <= first:
            return []
        p_first, p_last = 1 - (first - now) / approach, 1 - (last - now) / approach
        # Uniform time samples preserve the exact judge path. Perspective turns
        # it into a smooth screen-space curve without inventing a lane easing.
        y_first = self.project(0, p_first)[1]
        y_last = self.project(0, p_last)[1]
        segments = min(64, max(2, math.ceil(abs(y_first - y_last) / 7)))
        points = []
        for i in range(segments + 1):
            when = first + (last - first) * i / segments
            progress = 1 - (when - now) / approach
            x, y, width = self.project(self.lane_at(note, when), progress)
            points.append((when, x, y, width * .29))
        return points

    def ribbon(self, note, now, approach, colors):
        points = self.ribbon_points(note, now, approach)
        if not points:
            return
        layer = self.ribbon_layer
        palette = ribbon_palette(color_key(colors[0]), color_key(colors[1]))
        duration = max(1e-9, note["end_time"] - note["time"])
        active = bool(note.get("active"))
        for first, last in zip(points, points[1:]):
            when, x, y, half = first
            end, nx, ny, nhalf = last
            ratio = ((when + end) / 2 - note["time"]) / duration
            tint = palette[max(0, min(32, round(ratio * 32)))]
            quad = [(x-half, y), (x+half, y), (nx+nhalf, ny), (nx-nhalf, ny)]
            pygame.draw.polygon(layer, (*tint, 102 if active else 75), quad)
            inner = [(x-half*.52, y), (x+half*.52, y), (nx+nhalf*.52, ny), (nx-nhalf*.52, ny)]
            pygame.draw.polygon(layer, (*mix(tint, (255, 255, 255), .30), 65 if active else 42), inner)
            edge = mix(tint, (255, 255, 255), .62)
            for side in (-1, 1):
                a, b = (x+side*half, y), (nx+side*nhalf, ny)
                pygame.draw.line(layer, (*tint, 30), a, b, 5)
                pygame.draw.aaline(layer, (*edge, 210), a, b)
        # Small travelling highlights follow the same timed path. No wall clock
        # is used, so pausing freezes both the ribbon and its animation.
        if active or note["type"] == "SLIDE":
            first, last = points[0][0], points[-1][0]
            spacing = .30
            phase = (now * .38) % spacing
            marker = math.ceil((first - phase) / spacing) * spacing + phase
            while marker < last:
                p = 1 - (marker - now) / approach
                x, y, width = self.project(self.lane_at(note, marker), p)
                half = width * .13
                pygame.draw.aalines(layer, (255, 255, 255, 135 if active else 65), False,
                                   [(x-half, y-2), (x, y+1), (x+half, y-2)])
                marker += spacing

    def draw(self, surface, notes, now, approach, palettes):
        """Paint every ribbon first, then caps from far to near; never mutate notes."""
        visible = [note for note in notes if not note.get("hit")]
        self.ribbon_layer.fill((0, 0, 0, 0))
        caps = []
        for note in visible:
            kind = note["type"]
            if kind in ("HOLD", "SLIDE"):
                self.ribbon(note, now, approach, palettes[kind])
                if now <= note["end_time"]:
                    head_time = max(note["time"], now)
                    caps.append((1-(head_time-now)/approach, self.lane_at(note, head_time), kind, False))
                    caps.append((1-(note["end_time"]-now)/approach, self.lane_at(note, note["end_time"]), kind, True))
            else:
                caps.append((1-(note["time"]-now)/approach, note["lane"], kind, False))
        surface.blit(self.ribbon_layer, (0, 0))
        for progress, lane, kind, tail in sorted(caps, key=lambda cap: cap[0]):
            colors = palettes.get(kind, ((255, 206, 234), (249, 65, 143)))
            self.head(surface, lane, progress, *colors, flick=kind == "FLICK", tail=tail)
