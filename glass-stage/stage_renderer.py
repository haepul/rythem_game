"""Cached four-lane stage. All geometry is derived from the note projection."""
from functools import lru_cache
import math
import pygame

# Disable decoration without changing projection, timing or input handling.
STAGE_EFFECTS = True
INPUT_EFFECTS = True
BEAT_GRID = True


def blend(a, b, t):
    return tuple(round(x+(y-x)*t) for x,y in zip(a,b))


@lru_cache(maxsize=8)
def background_texture(size, colors, accent, effects=True):
    # Low-resolution smooth light fields are generated once, never per frame.
    w,h=size
    small=pygame.Surface((100,60))
    for y in range(60):
        v=y/59
        base=blend(colors[0],colors[1],v*2) if v<.5 else blend(colors[1],colors[2],(v-.5)*2)
        base=blend((7,10,25),base,.32)
        for x in range(100):
            u=x/99
            glow=(math.exp(-(((u-.18)/.30)**2+((v-.34)/.42)**2))* .12
                  +math.exp(-(((u-.85)/.35)**2+((v-.12)/.38)**2))*.13) if effects else 0
            small.set_at((x,y),blend(base,accent,glow))
    out=pygame.transform.smoothscale(small,size)
    if effects:
        # Deterministic stars stay outside the note corridor; no falling particles.
        for i in range(30):
            x=(i*137+19)%w; y=70+(i*71)%(h-85)
            if abs(x-w/2) > 125+(y-70)*.73:
                c=blend((20,27,49),accent,.22+(i%4)*.06)
                pygame.draw.circle(out,c,(x,y),1)
        layer=pygame.Surface(size,pygame.SRCALPHA)
        for side in (-1,1):
            for i in range(3):
                x=w/2+side*(230+i*48); y=145+i*73
                pygame.draw.polygon(layer,(*accent,16),[(x,y-17),(x+12,y),(x,y+17),(x-12,y)],1)
        out.blit(layer,(0,0))
    return out.convert()


def rail_points(project, lane, p, half_width):
    x,y,_=project(lane,p)
    return (x-half_width,y),(x+half_width,y)


@lru_cache(maxsize=4)
def composed_stage(background, accent, project, effects=True):
    out=background.copy()
    w,h=out.get_size()
    _,top,_=project(-.5,0); left,bottom,_=project(-.5,1); right,_,_=project(3.5,1)
    # Soft shadow and a shallow front fascia detach the track from the floor.
    if effects:
        shadow=pygame.Surface((w,44),pygame.SRCALPHA)
        for row in range(44):
            a=round(75*math.exp(-((row-12)/13)**2))
            pygame.draw.line(shadow,(0,0,9,a),(left-12,row),(right+12,row))
        out.blit(shadow,(0,round(bottom)))
    pygame.draw.polygon(out,(9,12,25),[(left,bottom),(right,bottom),(right-7,bottom+9),(left+7,bottom+9)])
    # Row positions use the inverse of the unchanged progress ** 1.55 mapping.
    road=pygame.Surface((w,h),pygame.SRCALPHA)
    for y in range(round(top),round(bottom)+1):
        depth=(y-top)/(bottom-top)
        progress=depth**(1/1.55)
        for lane in range(4):
            x1,_,_=project(lane-.5,progress); x2,_,_=project(lane+.5,progress)
            base=blend((7,10,23),(23,29,48),depth)
            color=blend(base,accent,(.025 if lane%2 else .055)*depth)
            pygame.draw.line(road,(*color,246),(math.ceil(x1),y),(math.floor(x2),y))
    out.blit(road,(0,0))
    # Tapered neon rails and subdued lane separators share the note geometry.
    rails=pygame.Surface((w,h),pygame.SRCALPHA)
    for boundary in range(5):
        outer=boundary in (0,4)
        for step in range(48):
            a,b=step/48,(step+1)/48
            thickness=(.40+.60*b) if outer else (.18+.35*b)
            l1,r1=rail_points(project,boundary-.5,a,thickness)
            l2,r2=rail_points(project,boundary-.5,b,thickness)
            if effects and outer:
                g1,g2=rail_points(project,boundary-.5,a,thickness+2)
                g3,g4=rail_points(project,boundary-.5,b,thickness+2)
                pygame.draw.polygon(rails,(*accent,16),[g1,g2,g4,g3])
            color=blend(accent,(205,228,255),.55) if outer else (164,176,210)
            pygame.draw.polygon(rails,(*color,round((105+60*b) if outer else (20+22*b))),[l1,r1,r2,l2])
    out.blit(rails,(0,0))
    return out.convert()


@lru_cache(maxsize=24)
def input_lane_texture(size, accent, project, lane):
    layer=pygame.Surface(size,pygame.SRCALPHA)
    # Local rise fades out before the distant stage, with no bright full lane.
    for i in range(28):
        a=.52+i*.48/28; b=.52+(i+1)*.48/28
        pts=[project(lane-.5,a)[:2],project(lane+.5,a)[:2],
             project(lane+.5,b)[:2],project(lane-.5,b)[:2]]
        pygame.draw.polygon(layer,(*accent,round(30*((b-.52)/.48)**2)),pts)
    bounds=layer.get_bounding_rect()
    return layer.subsurface(bounds).copy(), bounds.topleft


@lru_cache(maxsize=32)
def judge_texture(width, accent, phase_bucket, effects=True):
    image=pygame.Surface((width+1,21),pygame.SRCALPHA)
    pulse=1-phase_bucket/15
    if effects:
        for spread,alpha in ((9,6),(6,12),(3,28),(1,95)):
            pygame.draw.line(image,(*accent,round(alpha*(.88+.12*pulse**3))),
                             (0,10),(width,10),spread*2+1)
    # Core never pulses or disappears under receptor decorations.
    pygame.draw.line(image,(242,248,255,250),(0,10),(width,10),1)
    return image


def draw_stage(surface, background, accent, project, now):
    surface.blit(composed_stage(background,tuple(accent),project,STAGE_EFFECTS),(0,0))


def draw_track_feedback(surface, layer, accent, project, now, bpm, offset, approach, pressed):
    """A few projected lines plus cached strips; no per-frame pixel loops."""
    accent=tuple(accent)
    phase=((now-offset)*bpm/60)%1
    layer.fill((0,0,0,0))
    if BEAT_GRID:
        beat_seconds=60/max(1,bpm)
        for ahead in range(1,6):
            p=1-(ahead-phase)*beat_seconds/approach
            if .04<p<.98:
                x,y,_=project(-.5,p); xr,_,_=project(3.5,p)
                depth=p**1.55
                pygame.draw.line(layer,(161,184,225,round(10+37*depth)),(x,y),(xr,y),1)
    surface.blit(layer,(0,0))
    active=sorted(set(lane for lane in pressed if lane in range(4)))
    if INPUT_EFFECTS:
        for lane in active:
            glow, position = input_lane_texture(surface.get_size(),accent,project,lane)
            surface.blit(glow,position)
    left,y,_=project(-.5,1); right,_,_=project(3.5,1)
    strip=judge_texture(round(right-left),accent,min(15,int(phase*16)),STAGE_EFFECTS)
    surface.blit(strip,(round(left),round(y)-10))
    if INPUT_EFFECTS:
        for lane in active:
            x1,_,_=project(lane-.5,1); x2,_,_=project(lane+.5,1)
            pygame.draw.line(surface,blend(accent,(255,255,255),.6),(x1+3,y+2),(x2-3,y+2),2)
