# Rhythm Stage

GitHub Pages build for the Pygame rhythm game. The page loads `game.tar.gz`; track audio is fetched on demand from `music/` so the full music library is not downloaded on the first page load.

## Rebuild the web archive

With Python 3.12 and Pygbag 0.9.3 installed, run from this directory:

```powershell
python -m pygbag --build --PYBUILD 3.12 --app_name RhythmStage --title "Rhythm Stage" .
$archive = Get-ChildItem .\build\web\*.tar.gz | Select-Object -First 1
Copy-Item $archive.FullName .\game.tar.gz -Force
```

The archive must remain named `game.tar.gz`, which is what `index.html` loads. Increment the `v=` value in `index.html` whenever replacing the archive so browsers do not keep an older cached build. Keep `music/*.mp4` at the repository root for GitHub Pages audio streaming.
