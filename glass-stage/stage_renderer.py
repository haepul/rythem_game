"""Procedural stage scenery; no external artwork or game-clock changes."""
from functools import lru_cache
import pygame


@lru_cache(maxsize=24)
def stage_overlay(size, accent, top_y, bottom_y, top_w, bottom_w):
    w, h = size
    cx = w / 2
    layer = pygame.Surface(size, pygame.SRCALPHA)
    # A central abstract light installation remains visible through the road.
    for inset in range(0, 65, 16):
        rect = pygame.Rect(cx-112+inset, 80+inset, 224-2*inset, 220-2*inset)
        pygame.draw.rect(layer, (*accent, 36), rect, 2)
    # Receding gallery panels and spotlights, drawn once per song palette.
    for x, y, pw, ph in ((52, 154, 106, 80), (176, 120, 82, 61),
                          (w-158, 154, 106, 80), (w-258, 120, 82, 61)):
        pygame.draw.rect(layer, (12, 19, 44, 180), (x-5, y-5, pw+10, ph+10))
        pygame.draw.rect(layer, (*accent, 54), (x, y, pw, ph))
        pygame.draw.rect(layer, (198, 212, 255, 65), (x, y, pw, ph), 2)
        pygame.draw.polygon(layer, (*accent, 45), [(x,y+ph), (x+pw*.65,y+ph*.25), (x+pw,y+ph)])
    for side in (-1, 1):
        source = (cx + side*w*.39, 56)
        pygame.draw.polygon(layer, (*accent, 24), [source, (cx+side*80,h), (cx+side*310,h)])
        pygame.draw.polygon(layer, (216, 231, 255, 14), [source, (cx+side*140,h), (cx+side*235,h)])
        for i in range(9):
            x = cx + side*(185 + (i*47)%170)
            y = 230 + (i*37)%200
            r = 6 + i%3*4
            pygame.draw.polygon(layer, (*accent, 55), [(x,y-r),(x+r,y+r),(x-r,y+r)], 1 if i%2 else 0)
    # A translucent road lets the backdrop show through without competing
    # with notes. Row gradients and rails are cached, not rebuilt per frame.
    for y in range(top_y, h):
        p = (y-top_y)/(bottom_y-top_y)
        half = (top_w+(bottom_w-top_w)*p)/2
        # Composite, rather than overwrite, the gallery's alpha.
        road_color = (9, 12, 31, round(105+65*min(1,p)))
        road_y = y-top_y
        if road_y == 0:
            road = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.line(road, road_color, (cx-half,y), (cx+half,y))
    layer.blit(road, (0, 0))
    for i in range(5):
        a = (cx-top_w/2+top_w*i/4, top_y)
        b = (cx-bottom_w/2+bottom_w*i/4, bottom_y)
        pygame.draw.line(layer, (216, 198, 255, 140 if i in (0,4) else 38), a,b,2 if i in (0,4) else 1)
    return layer


def draw_stage(surface, background, accent, project, now):
    surface.blit(background, (0, 0))
    left, top, _ = project(-.5, 0)
    right, _, _ = project(3.5, 0)
    bl, bottom, _ = project(-.5, 1)
    br, _, _ = project(3.5, 1)
    surface.blit(stage_overlay(surface.get_size(), tuple(accent), round(top),
                              round(bottom), right-left, br-bl), (0,0))
