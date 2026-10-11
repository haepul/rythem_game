"""Generate offline melody charts for the October 11 MP3 additions."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from auto_chart import generate_auto_chart_levels

SONGS = [
    ('푸르름이 사는 곳 - Tatsuya Kitani.mp3', 'where-our-blue-is', '푸르름이 사는 곳'),
    ('회회기담 - Eve .mp3', 'kaikai-kitan', '회회기담'),
    ('King Gnu - 일도.mp3', 'ichizu', '일도'),
    ('King Gnu - AIZO.mp3', 'aizo', 'AIZO'),
    ('Mili - Camelia [4K].mp3', 'camelia', 'Camelia'),
    ('Mili - Rendezvous [Limbus Company] (1).mp3', 'rendezvous', 'Rendezvous'),
    ('Mili - Salt, Pepper, Birds, and the Thought Police.mp3', 'salt-pepper-birds', 'Salt, Pepper, Birds, and the Thought Police'),
    ('Mili - String Theocracy Library of Ruina theme song.mp3', 'string-theocracy', 'String Theocracy'),
    ('Nightmare-M2U.mp3', 'nightmare', 'Nightmare'),
]

# Choose the musical pulse rather than a half-/third-time autocorrelation peak.
PREFERRED_BPM = {'kaikai-kitan': 185, 'aizo': 190, 'camelia': 126,
                 'salt-pepper-birds': 156, 'nightmare': 190}
# Local-file seconds; lyric section boundaries followed by short release space.
# Instrumental Nightmare uses its first major section.
VERSE_ENDS = {'where-our-blue-is': 81.6, 'kaikai-kitan': 85.9, 'ichizu': 89.6,
              'aizo': 106.4, 'camelia': 157.3, 'rendezvous': 81.5,
              'salt-pepper-birds': 107.8, 'string-theocracy': 58.6, 'nightmare': 69.6}

def main():
    source = Path(sys.argv[1])
    cache_path = ROOT / 'auto_charts.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8'))
    catalog_path = ROOT / 'stable' / 'additional_songs.json'
    catalog = []
    pygame.mixer.init(44100, -16, 2)
    for index, (filename, slug, title) in enumerate(SONGS):
        target = ROOT / 'music' / (slug + '.mp3')
        incoming = source / filename
        changed = incoming.exists() and (not target.exists() or
            hashlib.sha256(incoming.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest())
        if changed:
            shutil.copy2(incoming, target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        preferred = PREFERRED_BPM.get(slug)
        if changed or slug not in cache or cache[slug].get('preferred_bpm') != preferred:
            print('Analyzing ' + title, flush=True)
            result = generate_auto_chart_levels(str(target), preferred)
            result['preferred_bpm'] = preferred
            stat = target.stat()
            result['signature'] = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
            result['source_file'] = filename
            cache[slug] = result
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        entry = cache[slug]
        entry['source_sha256'] = digest
        accents = [(98, 223, 255), (194, 153, 255), (255, 122, 190)]
        catalog.append(dict(title=title, song=title, level=9, bpm=entry['bpm'],
                            offset=entry['offset'], duration=VERSE_ENDS[slug],
                            audio=slug+'.mp3', audio_version=digest[:12], colors=[[18, 14, 40], [25, 38, 66], [6, 10, 23]],
                            accent=accents[index % len(accents)]))
        print(json.dumps({'song': title, 'seconds': entry['duration'], 'bpm': entry['bpm'],
                          'notes': {k: len(v['notes']) for k, v in entry['difficulty_charts'].items()}},
                         ensure_ascii=False), flush=True)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
