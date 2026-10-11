param([string]$Version = '20261011-song-fixes-v3')
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path $PSScriptRoot -Parent
$stablePath = Join-Path $repoPath 'stable'
$packagePath = Join-Path $stablePath 'package'
New-Item -ItemType Directory -Path $packagePath -Force | Out-Null
foreach ($name in @('main.py', 'additional_songs.json')) {
    Copy-Item -LiteralPath (Join-Path $stablePath $name) -Destination $packagePath -Force
}
foreach ($name in @('sustain_judgement.py', 'tap_judgement.py', 'flick_judgement.py',
    'flick_chart.py', 'chart_layout.py', 'auto_chart.py', 'auto_charts.json',
    'beat_analysis.py', 'charts.json', 'font.ttf')) {
    Copy-Item -LiteralPath (Join-Path $repoPath $name) -Destination $packagePath -Force
}
$env:PYTHONUTF8 = '1'
Push-Location $packagePath
try {
    python -m pygbag --build --PYBUILD 3.12 --app_name RhythmStage --title 'Rhythm Stage' .
    if ($LASTEXITCODE -ne 0) { throw 'Stable build failed' }
} finally { Pop-Location }
Copy-Item -LiteralPath (Join-Path $packagePath 'build/web/package.tar.gz') -Destination (Join-Path $repoPath 'game.tar.gz') -Force
$indexPath = Join-Path $repoPath 'index.html'
$page = [IO.File]::ReadAllText($indexPath)
$page = $page -replace 'game.tar.gz\?v=[^"\s]+', "game.tar.gz?v=$Version"
[IO.File]::WriteAllText($indexPath, $page, [Text.UTF8Encoding]::new($false))
Write-Output "Stable site built: $Version"
