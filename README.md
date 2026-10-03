# Rhythm Stage

GitHub Pages build for the Pygame rhythm game. The page loads `game.tar.gz`; track audio is fetched on demand from `music/` so the full music library is not downloaded on the first page load.

## Rebuild the web archive

The browser build uses `webapp/` so the music files stay outside the startup
archive. After changing the game source or charts, copy the matching files from
the repository root into `webapp/`, then run this from the repository root:

```powershell
Copy-Item .\main.py, .\auto_chart.py, .\auto_charts.json, .\charts.json, .\font.ttf .\webapp\ -Force
Push-Location .\webapp
python -m pygbag --build --PYBUILD 3.12 --app_name RhythmStage --title "Rhythm Stage" .
Pop-Location
Copy-Item .\webapp\build\web\webapp.tar.gz .\game.tar.gz -Force
```

The archive must remain named `game.tar.gz`, which is what `index.html` loads. Increment the `v=` value in `index.html` whenever replacing the archive so browsers do not keep an older cached build. Keep each selected `.mp4` or `.mp3` audio file in the repository's `music/` directory for on-demand GitHub Pages streaming.
