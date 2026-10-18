# Song detail and launch UI

Changed only index.html (stylesheet link and accurate per-song record label) and added song-detail.css. Existing app.mjs selection, playback, score and chart logic are unchanged from the previous selection phase.

Reference inspected: https://cdn-ak.f.st-hatena.com/images/fotolife/y/yashihei/20231230/20231230155754.png — prominent jacket, title then colored difficulty choices then primary confirmation. Adapted to the requested bright white translucent surface and three supported difficulties. No external artwork or proprietary typeface copied.

Jacket enlarged to 184px in a 220px display area; white frame, subtle geometry and lavender/mint backing. EASY green, HARD pink, MASTER violet; selected state has a dark double-weight edge, raised shadow and underline as well as color. Main action has cyan gradient, touch press compression and reduced-motion support. The existing song-change animation remains. Full title, BPM, duration, combo total and per-song best record remain bound to existing data. No fabricated per-difficulty record or difficulty rating.

At narrow widths the detail switches to a single readable card, 154px jacket and full-width actions. Minimum difficulty targets 44px, main action 54px or larger. No changes to song list styles or other screens. NEXT has no existing browser chart-editor entry; the separate desktop editor is preserved and no dummy editor action added.

Checks: EASY verse displays 62 combo; MASTER full displays 993 combo and 05:09; HARD verse returns 213 combo and 01:31. Actual normal launch reached the unchanged no-input failure result for 나다움/HARD/1절. Practice launch displayed PRACTICE and life 100. Keyboard bridge and existing 34985 Python/JS judgment sample tests passed. core.mjs, audio.js, renderer.mjs and catalog hashes match the deployed baseline.

Local preview only; original and glass deployments unchanged. Physical touchscreen and subjective audio alignment were not evaluated.
