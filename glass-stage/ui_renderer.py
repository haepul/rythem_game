"""Original, cached 800x480 rhythm UI. No gameplay clocks or judgments live here."""
import math
import os
import time
from functools import lru_cache
import pygame

CYAN = (25, 212, 197)
MINT = (102, 233, 210)
PINK = (255, 105, 181)
PURPLE = (166, 138, 232)
INK = (65, 68, 92)
MUTED = (113, 120, 145)
WHITE = (248, 250, 255)
NAVY = (52, 52, 84)
LEVELS = {'easy': (57, 177, 128), 'hard': (230, 153, 41), 'master': (151, 104, 215)}
UI_EFFECTS = True
_scene = None
_entered = 0.0
_pause_backdrop = None
_selected = None
_selection_time = 0.0


@lru_cache(maxsize=32)
def font(size):
    return pygame.font.Font(os.path.join(os.path.dirname(__file__), 'ui-font.ttf'), size)


@lru_cache(maxsize=512)
def label_image(label, size, color):
    return font(size).render(str(label), True, color)


def text(surface, label, pos, size=14, color=INK, center=False, width=None):
    image = label_image(str(label), size, tuple(color))
    if width and image.get_width() > width:
        ratio = width / image.get_width()
        image = pygame.transform.smoothscale(image, (width, max(1, round(image.get_height()*ratio))))
    rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
    surface.blit(image, rect)
    return rect


def mix(a, b, t):
    return tuple(round(x+(y-x)*t) for x, y in zip(a, b))


@lru_cache(maxsize=96)
def panel_image(size, color=WHITE, radius=12):
    w, h = size
    image = pygame.Surface((w+8, h+8), pygame.SRCALPHA)
    for offset, alpha in ((6, 10), (3, 20)):
        pygame.draw.rect(image, (35, 38, 77, alpha), (offset, offset, w, h), border_radius=radius)
    pygame.draw.rect(image, color, (0, 0, w, h), border_radius=radius)
    pygame.draw.rect(image, (255, 255, 255, 190), (0, 0, w, h), 1, border_radius=radius)
    return image


def panel(surface, rect, color=WHITE, radius=12):
    surface.blit(panel_image(tuple(rect.size), tuple(color), radius), rect.topleft)


@lru_cache(maxsize=1)
def menu_background():
    image = pygame.Surface((800, 480))
    for y in range(480):
        pygame.draw.line(image, mix((240, 248, 253), (225, 225, 244), y/479), (0, y), (800, y))
    layer = pygame.Surface((800, 480), pygame.SRCALPHA)
    pygame.draw.polygon(layer, (102, 233, 210, 50), [(0,0),(340,0),(0,340)])
    pygame.draw.polygon(layer, (166,138,232,30), [(450,0),(800,0),(800,480),(700,480)])
    for y in range(12,480,16):
        for x in range(12,800,16):
            pygame.draw.circle(layer, (114,131,160,28), (x,y), 1)
    for x,y,r in ((39,382,35),(465,114,19),(731,332,55),(422,448,24)):
        pygame.draw.polygon(layer, (255,255,255,130), [(x,y-r),(x+r,y),(x,y+r),(x-r,y)], 2)
    image.blit(layer,(0,0))
    return image


@lru_cache(maxsize=96)
def button_image(size, accent, active, hover):
    w,h = size
    image = pygame.Surface((w,h+4),pygame.SRCALPHA)
    pygame.draw.rect(image, (71,76,109,65), (0,3,w,h),border_radius=8)
    top = mix(accent,(255,255,255),.23) if active else (255,255,255)
    bottom = accent if active else ((221,248,246) if hover else (232,237,247))
    fill = pygame.Surface((w,h),pygame.SRCALPHA)
    for y in range(h):
        pygame.draw.line(fill,mix(top,bottom,y/max(1,h-1)),(0,y),(w,y))
    mask = pygame.Surface((w,h),pygame.SRCALPHA)
    pygame.draw.rect(mask,(255,255,255),mask.get_rect(),border_radius=8)
    fill.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    image.blit(fill,(0,0))
    pygame.draw.rect(image, accent if active or hover else (190,198,214),(0,0,w,h),1,border_radius=8)
    pygame.draw.line(image,(255,255,255,160),(9,2),(w-10,2))
    return image


def button(surface, rect, label, accent=CYAN, active=False, mouse=(-1,-1), size=14):
    surface.blit(button_image(tuple(rect.size),tuple(accent),active,rect.collidepoint(mouse)),rect.topleft)
    text(surface,label,rect.center,size, (24,65,76) if active and accent==CYAN else WHITE if active else INK,True,rect.width-12)


@lru_cache(maxsize=96)
def jacket(index, accent, size):
    """Independent abstract covers; no downloaded album artwork."""
    image = pygame.Surface((size,size))
    dark = mix(accent,NAVY,.7)
    for y in range(size):
        pygame.draw.line(image,mix(dark,accent,.65*y/max(1,size)),(0,y),(size,y))
    layer=pygame.Surface((size,size),pygame.SRCALPHA)
    for k in range(5):
        x=int(size*(.12+k*.21))
        pygame.draw.line(layer,(255,255,255,24),(x-size//2,0),(x+size//2,size),max(2,size//11))
    cx,cy=size//2,size//2
    if index%3==0:
        for r in (.36,.27,.11):
            pygame.draw.circle(layer,(225,255,251,190),(cx,cy),int(size*r),max(1,size//40))
        pygame.draw.polygon(layer,(*PINK,210),[(cx,cy-int(size*.28)),(cx+int(size*.2),cy+int(size*.18)),(cx-int(size*.2),cy+int(size*.18))])
    elif index%3==1:
        for k in range(3):
            d=int(size*(.34-k*.09))
            pygame.draw.polygon(layer,(255,255,255,210-k*35),[(cx,cy-d),(cx+d,cy),(cx,cy+d),(cx-d,cy)],max(2,size//30))
    else:
        for k in range(9):
            x=int(size*(.17+k*.08)); height=int(size*(.18+.35*abs(math.sin(k*1.3+index))))
            pygame.draw.rect(layer,(220,255,250,205),(x,cy-height//2,max(2,size//30),height),border_radius=2)
    image.blit(layer,(0,0))
    text(image,f'RS / {index+1:02}',(size*.08,size*.08),max(9,size//12),WHITE)
    text(image,'RHYTHM STAGE',(size*.08,size*.86),max(7,size//17),WHITE)
    return image


def title(g, surface, song, rect, size=16, color=INK):
    image=g.wrapped_title_image(song.get('title',song['song']),font(size),rect.width,rect.height,tuple(color))
    surface.blit(image,image.get_rect(center=rect.center))


def volume(g, surface, rect, mouse, click):
    if click and rect.inflate(0,14).collidepoint(mouse):
        g.set_music_volume((mouse[0]-rect.x)/max(1,rect.width))
    text(surface,'VOL',(rect.x-24,rect.centery),10,MUTED,True)
    pygame.draw.rect(surface,(211,218,232),rect,border_radius=5)
    width=round(rect.width*g.music_volume)
    if width: pygame.draw.rect(surface,CYAN,(rect.x,rect.y,width,rect.height),border_radius=5)
    pygame.draw.circle(surface,WHITE,(rect.x+width,rect.centery),6)
    pygame.draw.circle(surface,(41,158,158),(rect.x+width,rect.centery),6,1)
    text(surface,f'{round(g.music_volume*100)}',(rect.right+19,rect.centery),11,INK,True)


def home_controls(g):
    controls={'speed-':pygame.Rect(310,46,38,30),'speed+':pygame.Rect(432,46,38,30),
              'flick':pygame.Rect(480,46,138,30),'prev':pygame.Rect(24,398,38,27),
              'next':pygame.Rect(432,398,38,27),'play':pygame.Rect(635,408,141,39),
              'practice':pygame.Rect(492,408,133,39)}
    if g.sys.platform!='emscripten': controls['editor']=pygame.Rect(24,433,130,26)
    for i,key in enumerate(('easy','hard','master')): controls[key]=pygame.Rect(504+i*87,315,82,31)
    for i,key in enumerate(('verse','full')): controls[key]=pygame.Rect(504+i*131,362,125,28)
    return controls


def draw_home(g, mouse, click):
    global _selected,_selection_time
    controls=home_controls(g)
    pages=max(1,math.ceil(len(g.MAP_LIST)/g.SONGS_PER_PAGE))
    if click:
        for key,rect in controls.items():
            if not rect.collidepoint(mouse): continue
            if key in ('play','practice','editor'): return key
            if key=='speed-': g.adjust_note_speed(-1)
            elif key=='speed+': g.adjust_note_speed(1)
            elif key=='flick': g.set_flick_enabled(not g.flick_enabled)
            elif key in ('easy','hard','master'): g.selected_difficulty=key
            elif key in ('verse','full'): g.selected_length=key
            elif key in ('prev','next'):
                page=max(0,min(pages-1,g.song_page+(-1 if key=='prev' else 1)))
                if page!=g.song_page:
                    g.song_page=page; g.selected_map_idx=page*g.SONGS_PER_PAGE
    cards=[]
    for local,index in enumerate(range(g.song_page*g.SONGS_PER_PAGE,min((g.song_page+1)*g.SONGS_PER_PAGE,len(g.MAP_LIST)))):
        rect=pygame.Rect(24+(local%3)*150,103+(local//3)*145,140,135)
        cards.append((index,rect))
        if click and rect.collidepoint(mouse): g.selected_map_idx=index
    if _selected!=g.selected_map_idx:
        _selected=g.selected_map_idx; _selection_time=time.perf_counter()
    s=g.screen; s.blit(menu_background(),(0,0))
    panel(s,pygame.Rect(12,9,776,75),radius=12)
    pygame.draw.polygon(s,CYAN,[(18,16),(24,16),(24,37),(18,42)])
    text(s,'RHYTHM STAGE',(35,18),21)
    text(s,'MUSIC SELECT',(270,22),13,MUTED)
    text(s,f'{len(g.MAP_LIST):02} SONGS',(691,22),13,(34,149,148))
    text(s,'노트 속도',(248,61),12,MUTED,True)
    button(s,controls['speed-'],'-',mouse=mouse); button(s,controls['speed+'],'+',mouse=mouse)
    text(s,f'{g.NOTE_SPEED_LEVELS[g.note_speed_index]:.2f}×',(389,61),15,INK,True)
    button(s,controls['flick'],'플릭 ON' if g.flick_enabled else '플릭 OFF',PINK,g.flick_enabled,mouse)
    volume(g,s,g.volume_slider_for_state('HOME'),mouse,click)
    text(s,'곡을 선택하세요',(35,59),12,MUTED)
    for index,rect in cards:
        song=g.MAP_LIST[index]; selected=index==g.selected_map_idx
        panel(s,rect)
        art=jacket(index,tuple(song['accent']),92)
        s.blit(art,(rect.x+24,rect.y+7))
        title(g,s,song,pygame.Rect(rect.x+5,rect.y+102,130,28),12)
        if selected:
            pygame.draw.rect(s,CYAN,rect,3,border_radius=12)
            pygame.draw.polygon(s,CYAN,[(rect.right-27,rect.y),(rect.right,rect.y),(rect.right,rect.y+27)])
            pygame.draw.lines(s,WHITE,False,[(rect.right-17,rect.y+7),(rect.right-12,rect.y+12),(rect.right-5,rect.y+5)],2)
        elif rect.collidepoint(mouse): pygame.draw.rect(s,(168,206,213),rect,2,border_radius=12)
    button(s,controls['prev'],'‹',mouse=mouse,size=20); button(s,controls['next'],'›',mouse=mouse,size=20)
    text(s,f'{g.song_page+1} / {pages}',(247,410),14,INK,True)
    for i in range(pages): pygame.draw.circle(s,CYAN if i==g.song_page else (182,188,206),(218+i*14,432),3)
    song=g.MAP_LIST[g.selected_map_idx]
    detail=pygame.Rect(492,103,284,292); panel(s,detail)
    pygame.draw.rect(s,NAVY,(492,103,284,48),border_top_left_radius=12,border_top_right_radius=12)
    text(s,'SELECTED MUSIC',(510,119),12,WHITE)
    text(s,f'#{g.selected_map_idx+1:02}',(739,119),12,MINT)
    s.blit(jacket(g.selected_map_idx,tuple(song['accent']),126),(571,159))
    # The title has its own reserved strip, independent of jacket and settings.
    title(g,s,song,pygame.Rect(504,287,260,25),16)
    for key in ('easy','hard','master'):
        button(s,controls[key],g.DIFFICULTIES[key],LEVELS[key],g.selected_difficulty==key,mouse,12)
    bpm=g.get_saved_bpm(song['audio'],song['bpm'])
    text(s,f'{bpm:g} BPM  ·  {g.format_time(g.song_duration(song,g.selected_length))}',(634,354),11,MUTED,True)
    for key in ('verse','full'): button(s,controls[key],g.LENGTH_LABELS[key],CYAN,g.selected_length==key,mouse,12)
    record=g.player_records.get(g.selected_map_idx,{'grade':'-','fc':False})
    text(s,f"BEST  {record['grade']}"+('  /  FULL COMBO' if record['fc'] else ''),(510,140),10,MINT)
    button(s,controls['play'],'라이브 시작  ›',CYAN,True,mouse,17)
    button(s,controls['practice'],'연습 모드',PURPLE,False,mouse,15)
    if 'editor' in controls: button(s,controls['editor'],'CHART STUDIO',PURPLE,False,mouse,11)
    text(s,'D F J K  ·  플릭: 레인 키 + SPACE / 위로 스와이프',(400,468),11,MUTED,True)
    if g.home_notice and time.time()<g.home_notice_until:
        panel(s,pygame.Rect(172,444,448,18),(225,249,245),6)
        text(s,g.home_notice,(396,453),11,INK,True,432)
    if UI_EFFECTS:
        t=min(1,(time.perf_counter()-_selection_time)/.14)
        pygame.draw.line(s,MINT,(504,105),(504+round(256*t),105),2)


def begin_frame(surface, scene):
    global _scene,_entered,_pause_backdrop
    if scene==_scene: return
    _scene=scene; _entered=time.perf_counter()
    if scene=='PAUSED':
        _pause_backdrop=surface.copy()
        veil=pygame.Surface(surface.get_size(),pygame.SRCALPHA); veil.fill((20,22,46,158))
        _pause_backdrop.blit(veil,(0,0))


@lru_cache(maxsize=1)
def transition_layer():
    layer=pygame.Surface((800,480)); layer.fill((235,244,250)); return layer


def end_frame(surface, scene):
    if not UI_EFFECTS or scene not in ('HOME','RESULT','GAME_OVER','LOADING','ANALYZING'): return
    t=(time.perf_counter()-_entered)/.18
    if t<1:
        layer=transition_layer(); layer.set_alpha(round(65*(1-max(0,t)))); surface.blit(layer,(0,0))


def draw_pause(g,mouse,click):
    s=g.screen; s.blit(_pause_backdrop if _pause_backdrop is not None else g.current_bg_surface,(0,0))
    box=pygame.Rect(220,25,360,435); panel(s,box)
    pygame.draw.rect(s,CYAN,(220,25,360,57),border_top_left_radius=12,border_top_right_radius=12)
    text(s,'PAUSE',(400,54),27,WHITE,True)
    text(s,'연습 모드 · 체력 감소 없음' if g.practice_mode else '잠시 쉬어 가도 괜찮아요',(400,94),12,MUTED,True)
    resume=pygame.Rect(255,112,290,38); retry=pygame.Rect(255,158,140,38); home=pygame.Rect(405,158,140,38)
    flick=pygame.Rect(255,210,290,36); minus=pygame.Rect(428,333,31,32); plus=pygame.Rect(514,333,31,32)
    button(s,resume,'계속하기  ›',CYAN,True,mouse,18)
    button(s,retry,'다시하기',mouse=mouse); button(s,home,'곡 선택으로',mouse=mouse)
    button(s,flick,'플릭 ON' if g.current_flick_enabled else '플릭 OFF',PINK,g.current_flick_enabled,mouse)
    volume(g,s,g.volume_slider_for_state('PAUSED'),mouse,click)
    pygame.draw.line(s,(221,228,240),(255,306),(545,306))
    text(s,'노트 낙하 속도',(265,342),14)
    button(s,minus,'-',mouse=mouse); button(s,plus,'+',mouse=mouse)
    text(s,f'{g.NOTE_SPEED_LEVELS[g.note_speed_index]:g}×',(486,349),14,INK,True)
    text(s,'음악 속도와 판정 타이밍은 유지됩니다',(400,399),12,MUTED,True)
    text(s,'ESC · 계속하기',(400,432),11,(45,157,151),True)
    return resume,retry,home,flick,minus,plus


def draw_hud(g,s,play_time,btn_pause):
    pygame.draw.rect(s,(25,28,51),(0,0,800,63))
    pygame.draw.polygon(s,WHITE,[(14,12),(229,12),(217,48),(14,48)])
    text(s,'SCORE',(25,16),10,MUTED)
    text(s,f'{g.score:07,}',(79,20),23,INK)
    title(g,s,g.current_map,pygame.Rect(242,10,315,22),14,WHITE)
    text(s,f'{g.DIFFICULTIES[g.current_difficulty]}  ·  {g.current_bpm:g} BPM',(400,44),11,MINT,True)
    text(s,'LIFE',(579,13),10,WHITE)
    pygame.draw.rect(s,(68,69,91),(579,31,140,12),border_radius=6)
    color=MINT if g.hp>50 else (255,199,109) if g.hp>25 else PINK
    pygame.draw.rect(s,color,(579,31,round(140*max(0,min(1,g.hp/100))),12),border_radius=6)
    text(s,'PRACTICE' if g.practice_mode else f'{round(g.hp)}',(688,16),10,MINT,True)
    pygame.draw.line(s,(79,80,111),(14,59),(786,59),2)
    progress=max(0,min(1,play_time/max(.01,g.current_map['duration'])))
    pygame.draw.line(s,CYAN,(14,59),(14+round(772*progress),59),2)
    button(s,btn_pause,'',mouse=(-1,-1))
    for dx in (14,26): pygame.draw.rect(s,INK,(btn_pause.x+dx,btn_pause.y+9,5,17),border_radius=1)
    text(s,f'{g.format_time(max(0,play_time))} / {g.format_time(g.current_map["duration"])}',(400,77),10,(180,190,216),True)
    text(s,g.current_chart_source,(400,94),9,(150,163,191),True)
    if g.current_difficulty=='master' and g.current_flick_enabled:
        text(s,'FLICK · 레인 키 + SPACE / 위로 스와이프',(400,462),11,(244,161,202),True)


def draw_result(g,s):
    s.blit(menu_background(),(0,0))
    panel(s,pygame.Rect(24,18,752,77))
    s.blit(jacket(g.current_map_idx,tuple(g.current_map['accent']),59),(36,27))
    text(s,'LIVE RESULT',(112,31),12,(40,160,153))
    title(g,s,g.current_map,pygame.Rect(112,48,490,35),20)
    button(s,pygame.Rect(651,38,110,30),g.DIFFICULTIES[g.current_difficulty],LEVELS[g.current_difficulty],True,size=12)
    panel(s,pygame.Rect(24,151,464,218))
    text(s,'TOTAL SCORE',(44,168),12,MUTED)
    text(s,f'{g.score:,}',(45,190),39,(220,71,146))
    pygame.draw.line(s,(221,227,239),(44,243),(468,243))
    for label,count,y,color in (('PERFECT',g.perfect_count,262,(131,86,174)),('GREAT',g.great_count,294,(40,151,154)),('MISS',g.miss_count,326,(204,85,121))):
        text(s,label,(45,y),15,color); text(s,str(count),(205,y),15)
    accuracy=g.hit_score/g.total_notes if g.total_notes else 0
    text(s,'MAX COMBO',(293,264),12,MUTED); text(s,str(g.max_combo),(293,284),24)
    text(s,f'ACCURACY  {accuracy:.1f}%',(293,330),13,INK)
    panel(s,pygame.Rect(509,151,267,218),NAVY)
    grade,color=g.get_grade(accuracy)
    pygame.draw.polygon(s,(96,97,136),[(642,174),(724,248),(642,331),(560,248)],2)
    pygame.draw.polygon(s,(134,119,172),[(642,184),(714,248),(642,321),(570,248)],1)
    text(s,grade,(642,249),68,MINT,True)
    text(s,'CLEAR RANK',(642,345),12,WHITE,True)
    text(s,'STAGE CLEAR',(400,123),24,INK,True)
    if g.practice_mode: text(s,'PRACTICE · 기록은 저장되지 않습니다',(400,465),12,MUTED,True)
    else: text(s,f'{g.LENGTH_LABELS[g.current_length]} · 수고하셨습니다!',(400,465),12,MUTED,True)


def draw_failure(g,s,mouse):
    s.blit(menu_background(),(0,0)); panel(s,pygame.Rect(172,85,456,310))
    pygame.draw.rect(s,PINK,(172,85,456,49),border_top_left_radius=12,border_top_right_radius=12)
    text(s,'LIVE FAILED',(400,110),24,WHITE,True)
    title(g,s,g.current_map,pygame.Rect(195,151,410,46),20)
    text(s,'체력이 모두 소진되었습니다',(400,222),16,INK,True)
    text(s,f'SCORE  {g.score:,}',(400,264),23,(204,77,136),True)
    retry=pygame.Rect(240,310,140,50); home=pygame.Rect(420,310,140,50)
    button(s,retry,'다시하기',CYAN,True,mouse,17); button(s,home,'곡 선택으로',mouse=mouse,size=17)
    return retry,home


def draw_loading(g,label,detail,progress,error=False,song=None):
    s=g.screen; song=song or g.current_map
    s.blit(menu_background(),(0,0)); panel(s,pygame.Rect(116,69,568,337))
    text(s,'LIVE PREPARATION',(400,96),13,(35,159,154),True)
    title(g,s,song,pygame.Rect(141,124,518,53),25)
    text(s,label,(400,218),18,INK,True,520)
    text(s,detail,(400,257),12,MUTED,True,518)
    pygame.draw.rect(s,(219,228,239),(240,292,320,8),border_radius=4)
    if not error:
        width=round(320*max(0,min(1,progress))) if progress else 70
        x=240 if progress else 240+round(250*(.5+.5*math.sin(time.perf_counter()*2)))
        pygame.draw.rect(s,CYAN,(x,292,width,8),border_radius=4)


def draw_ready(g):
    s=g.screen; s.blit(g.current_bg_surface,(0,0))
    title(g,s,g.current_map,pygame.Rect(40,70,720,60),28,WHITE)
    text(s,f'{g.DIFFICULTIES[g.current_difficulty]} · {g.LENGTH_LABELS[g.current_length]} · {g.current_bpm:g} BPM',(400,150),14,MINT,True)
    elapsed=max(0,time.perf_counter()-g.ready_start_time); beat=g.ready_count_in_duration/4
    count=max(1,4-min(3,int(elapsed/beat))); phase=elapsed%beat/beat
    pygame.draw.circle(s,(97,103,142),(400,262),68,1)
    pygame.draw.arc(s,CYAN,(330,192,140,140),-math.pi/2,-math.pi/2+max(.01,1-phase)*2*math.pi,4)
    text(s,str(count),(400,262),64,WHITE,True)
    text(s,'GET READY',(400,360),25,WHITE,True)
    tip='플릭: 레인 키 + SPACE / 위로 스와이프' if g.current_flick_enabled else '플릭 OFF · 일반 탭으로 연주'
    text(s,tip,(400,404),13,(216,214,239),True)
    text(s,'PRACTICE · NO FAIL' if g.practice_mode else '판정선에 맞춰 연주하세요',(400,433),12,MINT,True)
    text(s,'ESC · 취소',(400,464),11,(177,185,212),True)
