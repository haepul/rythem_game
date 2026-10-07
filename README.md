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

## Ordinary flicks (MASTER only)

All 21 MASTER charts include ordinary flick notes. EASY and HARD keep their
existing note types. `flick_chart.py` converts a small subset of existing MASTER
taps at phrase endings and accents; the music-attack timestamps, lanes and total
note count remain unchanged. It avoids dense runs, simultaneous chords and
nearby sustains, and leaves Shoushitsu's first 25 seconds unchanged. Reapply this
idempotent pass with `python tools/add_master_flicks.py --apply` after rebuilding
the saved charts.

- **Computer:** hold the matching lane key (**D / F / J / K**) and freshly press
  **SPACE** at the flick's beat. Holding the lane key early is allowed. For a
  near-simultaneous chord, a lane key arriving within **40ms after SPACE** also
  counts, using the SPACE press time. Holding SPACE or operating-system key
  repeats cannot trigger more flicks; release SPACE before the next gesture.
- **Phone:** touch the note's lane and swipe **upward** at its beat. A stationary
  touch or ordinary tap cannot clear a flick. Each finger is tracked separately.
  Upward movement is this game's requested control scheme; directional flick
  notes have not been added.
- **Timing:** PERFECT is within **±70ms** and GREAT within **±150ms** of the
  unchanged note timestamp. On computer the action time is the fresh SPACE
  edge. On phone it is the interpolated instant the upward gesture crosses its
  movement threshold, rather than the render frame that receives the event.
- **Swipe detection:** move at least **12 logical pixels** upward within a
  **100ms** motion window, at an upward speed of at least **140 logical px/s**.
  Coordinates are scaled to the game's **800 × 480** canvas, so this is not a
  physical-screen-pixel requirement. A continuous swipe resolves once; another
  flick needs a new gesture, with a fresh touch or a rearmed stroke.

The [official Project Sekai FAQ](https://pjsekai.sega.jp/faq/index.html) distinguishes
early/late flick timing from directional errors. It is the behavioral reference;
the timing windows, keyboard grace and swipe thresholds above are this game's
design values, not claimed to be Project Sekai's internal values.

## Fast-song input and rendering

The song selection header has a **플릭 ON/OFF** switch. OFF converts flicks to
ordinary taps at the same time and lane for that play; saved charts remain intact.
The setting applies when starting a song and persists in browser localStorage
or desktop `settings.json`. Turning ON restores the original MASTER flicks.

ESC or the pause button also opens volume, flick ON/OFF and note fall speed
controls (0.75–2×). The speed setting changes only the visual approach time;
music speed, pitch, BPM and every note's judgement time remain unchanged.
Faster scrolling spaces consecutive notes farther apart along the track.
Changing flick while paused converts only unresolved flicks to/from taps;
already judged notes, score, combo and song position are retained.

Browser D/F/J/K edges retain their DOM event times on the audible audio clock;
multiple presses in one Python frame remain distinct. `tap_judgement.py` matches
each edge to the closest eligible tap, with priority for a closer sustain head.
An earlier missed tile no longer captures the next tile's more accurate input.
Output timestamps compensate for the browser audio render buffer where supported.
Text caching, reused lane glow surfaces and a particle cap reduce frame work;
browser frames yield without an additional SDL frame-limit sleep.

## ALL PERFECT and sustain spacing

Completing every judgement, including hold/slide heads, body ticks and tails,
shows a glowing ALL PERFECT announcement once after the song finishes. It stays
visible for 1.25 seconds, fades out over 0.85 seconds, then opens the results.
During gameplay the normal combo display is used. A GREAT, MISS, empty chart or
partially judged chart cannot earn AP. Practice can show the announcement but
continues to leave records alone.

`chart_layout.py` checks full hold/slide paths, including crossings between slide
endpoints and clearance around sustain tails. Saved charts are repaired on load,
and newly generated charts pass through the same lane allocation before flick
selection. Musical times stay fixed. All 63 current difficulty charts retain
their 28,063 notes and original note types; 485 note placements are corrected.
Overfilled custom charts may simplify an impossible sustain or omit an onset
when all four lanes are occupied.

## Rebuild the web archive

The browser build uses `webapp/` so the music files stay outside the startup
archive. After changing the game source or charts, copy the matching files from
the repository root into `webapp/`, then run this from the repository root:

```powershell
Copy-Item .\main.py, .\sustain_judgement.py, .\tap_judgement.py, .\flick_judgement.py, .\flick_chart.py, .\chart_layout.py, .\auto_chart.py, .\auto_charts.json, .\charts.json, .\font.ttf .\webapp\ -Force
Push-Location .\webapp
python -m pygbag --build --PYBUILD 3.12 --app_name RhythmStage --title "Rhythm Stage" .
Pop-Location
Copy-Item .\webapp\build\web\webapp.tar.gz .\game.tar.gz -Force
```

The archive must remain named `game.tar.gz`, which is what `index.html` loads. Increment the `v=` values in `index.html` whenever replacing the archive or `audio_player.js` so browsers do not keep an older cached build. Keep `audio_player.js` at the site root and each selected `.mp4` or `.mp3` audio file in the repository's `music/` directory for on-demand playback.

## Automated checks

From the repository root, run the Python judgement/chart tests and the browser
input contract tests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/test_browser_input.cjs
```

The Python checks cover flick windows, ordered keyboard chords, swipe motion and
MASTER chart preservation. The Node checks exercise the JavaScript input bridge
with simulated DOM events. These checks do not establish real-phone touch or
speaker/Bluetooth latency; device playtesting is a separate check.

## Sustain judgement

`sustain_judgement.py` measures actual held intervals on the song clock. Body
ticks require 85% held time and a continuous contact ending at the tick. Rejoining
never grants elapsed ticks. Slide lane transfers allow 50ms for reconnection but
do not count the gap as held time. The tail accepts release up to 60ms early after
a sustained contact (up to 35ms: PERFECT; 35–60ms: GREAT); holding through the tail
also succeeds. No release action is required. Head, body and tail resolve once.
Ordered input edges include releases and re-presses within one frame. Synthetic
mouse events from touch are ignored, and losing focus pauses and clears input.
