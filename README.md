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
- The October 3 MASTER update adds accents at existing melody timestamps.
  Shoushitsu MASTER has a sparse first 25 seconds and dense sixteenth-note runs
  afterward. `tools/upgrade_master_charts.py` is the revision-guarded data migration;
  it also replaces the invalid Shoushitsu HARD tail with full-song audio events.

## Rebuild the web archive

The browser build uses `webapp/` so the music files stay outside the startup
archive. After changing the game source or charts, copy the matching files from
the repository root into `webapp/`, then run this from the repository root:

```powershell
Copy-Item .\main.py, .\sustain_judgement.py, .\auto_chart.py, .\auto_charts.json, .\charts.json, .\font.ttf .\webapp\ -Force
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
