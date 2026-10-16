# Rhythm Stage NEXT

Pygame-free browser implementation: semantic HTML/CSS menus, PixiJS 8.17.1 WebGL gameplay and the original Web Audio clock/input bridge. No Python or WebAssembly runtime is loaded by this page. Run an HTTP server from the repository root, then open `/next/` (deployed) or `/web-next/` (source workspace). Audio is resolved from sibling `music/`.

## What changed

- Responsive music library with real search, sorting, favorites and saved-record filtering.
- Independent geometric jacket graphics, a violet selected-song stage, layered white panels, cyan primary actions, per-difficulty colors and restrained CSS transitions.
- Native, resolution-independent text and controls; keyboard focus, accessible names, modal dialogs, reduced-motion support and a narrow-screen layout.
- WebGL track and note rendering, shared head textures, a reusable sprite pool, translucent HOLD/SLIDE ribbons and clear FLICK chevrons. Same 800×480 play coordinates and perspective projection.
- Countdown, normal/practice play, pause/resume/retry/home, volume, speed, flick conversion, failed/clear results, score/combo/accuracy, local records and ALL PERFECT celebration. Tab hiding/blur pauses live play. Practice never saves records.
- Separate `/next/` deployment. Original root, `/glass/`, `/glass-stage/` and the local Pygame sources remain available. The existing original-site ZIP backup is unchanged.

## Data and timing

`tools/export_web_next.py` calls the existing Python chart loader, note collision resolver and sustain-tick generator. It exports all 30 songs × 3 difficulties × 2 length modes, retaining authored BPM, offsets, lanes and timestamps. Songs load charts individually. Audio is downloaded/decoded before countdown and scheduled on the existing audio clock, not on frame time.

`core.mjs` ports the original tap, flick and sustain judges. `audio.js` is an unchanged copy of the prior site's Web Audio implementation, including output timestamp compensation and coalesced touch events. Keyboard controls remain D/F/J/K with SPACE for flicks. Touch positions are mapped to the same logical playfield. Mouse practice is also supported.

## Checks performed

- 34,985 frame/event samples agree with the Python reference judges across 464 generated scenarios. Includes HOLD/SLIDE at 15/30/60/120 Hz, continuous touch slides, key chord ordering and upward swipe rearming.
- Node checks cover nearest TAP, flick reservation, consumed gestures, score/combo, invincible practice, flick-off conversion, perspective endpoints and all 180 chart variants.
- Local browser: 30-song catalog, long-title search/selection, favorite persistence/filter, actual music loading and running play, normal failure/result, pause/settings and home return. Gone Angels MASTER practice completed naturally in 73 seconds and resolved all 278 expected judgments. A restart and actual D/F/J/K input produced a score of 105, confirming the DOM input path reaches scoring.
- 390×844 and 1280×720 DOM geometry checked; narrow-screen horizontal overflow repaired. Capture service returned `Unable to capture screenshot`, so image-based visual verification is not claimed.

Reproduce data/tests from the source workspace:

```text
python tools/export_web_next.py
python tools/export_judgement_fixtures.py
node tests/test_web_next.mjs
```

## Limits

The separate desktop chart editor/audio-analysis tooling stays in Python; this web player consumes its exported charts, matching the prior web player's scope. Old Pygame in-memory records are not automatically imported; new browser records use a separate localStorage namespace. Physical-device touch performance, mobile FPS and audible per-song offset alignment require device testing. GPU rendering does not by itself guarantee a faster frame rate on every machine. WebGL availability is required; initialization failures show a retry/back dialog instead of a blank game.

Reference implementation API: https://pixijs.com/8.x/guides/components/application
Vendored PixiJS: https://cdn.jsdelivr.net/npm/pixi.js@8.17.1/dist/pixi.min.js (MIT notice in `vendor/PIXI-LICENSE.txt`). Nanum Gothic Bold is unmodified and accompanied by `UI-FONT-LICENSE.txt`. Jackets are generated from original SVG geometry; no Project SEKAI graphic assets are bundled.
