# Rhythm Stage

GitHub Pages build for the Pygame rhythm game. The page loads `game.tar.gz`; track audio is fetched on demand from `music/` so the full music library is not downloaded on the first page load.

## Song length and playback

- Select **1절** or **전체 곡** beside the play controls. First-verse endpoints
  remain in `MAP_LIST`; full durations and all three charts are in `auto_charts.json`.
- `audio_player.js` fetches and decodes the selected track before the count-in.
  The loading screen supports retry/cancel. The decoded buffer is reused on retry;
  another song replaces it. Web Audio schedules the silent approach and uses the
  same audio clock for the chart. Native Pygame opens its decoder in a worker first.
- Page arrows are drawn shapes, so they do not depend on font Unicode coverage.
- The October 3 MASTER update adds accents at existing melody timestamps for
  other songs. Shoushitsu uses the October 5 melody analysis described below;
  the older upgrade/balance migrations leave this newer chart intact.

## Shoushitsu melody charts

`tools/rebuild_shoushitsu_melody.py` generates all three difficulties from the
user's complete MP3. It detects spectral attacks and a smoothed harmonic pitch
contour, fits the 240 BPM pulse/offset, and snaps only attacks within 14ms of the
sixteenth grid. It never fills silent gaps with evenly spaced notes. Lane choices
follow local pitch motion, hand alternation and repeated-motif penalties. Sustained
phrases become holds/slides; strong isolated attacks can become two-hand accents.
The first 25 seconds stay sparse. The game clips this same chart for verse mode.

The arrangement references [Project Sekai's original Shoushitsu MASTER chart](https://www.youtube.com/watch?v=NbXzQJi5ntU)
for changes between slides, runs and accents. That game's edited audio differs
from this full MP3, so its note timestamps are not copied. Polyphonic pitch
estimates are approximate and are not an isolated vocal transcription.

The offline tool requires NumPy and little-endian mono int16 PCM at 11025Hz:
`python tools/rebuild_shoushitsu_melody.py path/to/shoushitsu.pcm --apply`.
It stores feature/report/candidate files beside the PCM. Delete the derived
`.features.npz` before reusing the same filename for a different source. Runtime
playback needs only the saved `auto_charts.json`, with no analysis dependency.

## Fast-song input and rendering

Browser D/F/J/K edges retain their DOM event times on the audible audio clock;
multiple presses in one Python frame remain distinct. `tap_judgement.py` matches
each edge to the closest eligible tap, with priority for a closer sustain head.
An earlier missed tile no longer captures the next tile's more accurate input.
Output timestamps compensate for the browser audio render buffer where supported.
Text caching, reused lane glow surfaces and a particle cap reduce frame work;
browser frames yield without an additional SDL frame-limit sleep.

## Rebuild the web archive

The browser build uses `webapp/` so the music files stay outside the startup
archive. After changing the game source or charts, copy the matching files from
the repository root into `webapp/`, then run this from the repository root:

```powershell
Copy-Item .\main.py, .\sustain_judgement.py, .\tap_judgement.py, .\auto_chart.py, .\auto_charts.json, .\charts.json, .\font.ttf .\webapp\ -Force
Push-Location .\webapp
python -m pygbag --build --PYBUILD 3.12 --app_name RhythmStage --title "Rhythm Stage" .
Pop-Location
Copy-Item .\webapp\build\web\webapp.tar.gz .\game.tar.gz -Force
```

The archive must remain named `game.tar.gz`, which is what `index.html` loads. Increment the `v=` values in `index.html` whenever replacing the archive or `audio_player.js` so browsers do not keep an older cached build. Keep `audio_player.js` at the site root and each selected `.mp4` or `.mp3` audio file in the repository's `music/` directory for on-demand playback.

## Sustain judgement

`sustain_judgement.py` measures actual held intervals on the song clock. Body
ticks require 85% held time and a continuous contact ending at the tick. Rejoining
never grants elapsed ticks. Slide lane transfers allow 50ms for reconnection but
do not count the gap as held time. The tail accepts release up to 60ms early after
a sustained contact (up to 35ms: PERFECT; 35–60ms: GREAT); holding through the tail
also succeeds. No release action is required. Head, body and tail resolve once.
Ordered input edges include releases and re-presses within one frame. Synthetic
mouse events from touch are ignored, and losing focus pauses and clears input.
