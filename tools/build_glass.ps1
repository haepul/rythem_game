param([string]$Version = '20261009-glass-v1')
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path $PSScriptRoot -Parent
$webPath = Join-Path $repoPath 'webapp'
$glassPath = Join-Path $repoPath 'glass'
New-Item -ItemType Directory -Path $glassPath -Force | Out-Null
foreach ($name in @('main.py', 'note_renderer.py', 'sustain_judgement.py', 'tap_judgement.py',
    'flick_judgement.py', 'flick_chart.py', 'chart_layout.py', 'auto_chart.py', 'beat_analysis.py',
    'auto_charts.json', 'charts.json', 'font.ttf')) {
    Copy-Item -LiteralPath (Join-Path $repoPath $name) -Destination $webPath -Force
}
$env:PYTHONUTF8 = '1'
Push-Location $webPath
try {
    python -m pygbag --build --PYBUILD 3.12 --app_name RhythmStage --title 'Rhythm Stage Glass' .
    if ($LASTEXITCODE -ne 0) { throw 'PyGBag glass build failed' }
} finally { Pop-Location }
Copy-Item -LiteralPath (Join-Path $webPath 'build\web\webapp.tar.gz') -Destination (Join-Path $glassPath 'game.tar.gz') -Force
# The preview shares existing music/audio assets through the parent base URL.
# Its Python archive stays under glass/; the stable root page/archive stay intact.
$page = [IO.File]::ReadAllText((Join-Path $repoPath 'index.html'))
$page = $page.Replace('<html lang="ko">', '<html lang="ko"><base href="../">')
$page = $page -replace 'game.tar.gz\?v=[^"\s]+', "glass/game.tar.gz?v=$Version"
$page = $page.Replace('<title>game</title>', '<title>Rhythm Stage - Glass Preview</title>')
[IO.File]::WriteAllText((Join-Path $glassPath 'index.html'), $page, [Text.UTF8Encoding]::new($false))
Write-Output "Glass preview built: $glassPath"
