# Rhythm Stage UI v4

## Reference and implementation

The four supplied references were visually inspected before editing; approximate layout measurements, image identities and the distinction between observation and our own animation choices are in [UI_REFERENCE_ANALYSIS.md](UI_REFERENCE_ANALYSIS.md). No reference assets were copied into the game.

`ui_renderer.py` now owns reusable typography, gradient buttons, panel shadows, procedural square jackets, menu patterns and scene rendering. `main.py` delegates `draw_home`, `draw_analysis_screen`, `draw_ready_screen`, `draw_result_summary`, volume and button rendering; its existing action handlers, audio loading transitions and gameplay logic remain in place. PLAY, PAUSED, GAME_OVER and RESULT use the new renderer.

- HOME: three-column, two-row jacket grid; cyan selection frame and check; separate right detail panel; independent EASY/HARD/MASTER colors; length, speed, flick, volume, practice, play and desktop chart-studio controls. All 30 songs remain available across five pages.
- PLAY: dark stage retained, slanted white score panel, separate song/difficulty, life, elapsed time, source and progress. Fixed old score being covered by the header background.
- PAUSED: stable dimmed stage capture, white panel, cyan header/resume, existing flick/volume/speed controls. Fixed repeated dimming on every frame.
- RESULT: jacket/title strip, large pink score, judgment counts, combo and accuracy, original rank diamond, retained FULL COMBO/ALL PERFECT and practice state. Failed/loading/analysis/count-in screens follow the same visual language.
- Shared Nanum Gothic Bold font on desktop and web, distributed unmodified with `UI-FONT-LICENSE.txt`. Source: [Google Fonts](https://github.com/google/fonts/tree/main/ofl/nanumgothic).
- Independently chosen 180 ms menu fades and 140 ms selection accent. Set `ui_renderer.UI_EFFECTS = False` to disable them. Gameplay rendering is not faded or delayed.

## Preservation and performance

800×480, perspective, note renderers, input mappings, chart times and song catalog are preserved. AST comparison confirms `get_perspective_pos`, `start_game`, `begin_play`, `finish_song`, `update_sustain` and `request_game_start` are unchanged. Existing judge modules are not edited.

Background, panels, button gradients, jackets, fonts and labels use bounded caches. No per-frame pixel gradients or full-screen Surface allocation is introduced in normal menu rendering. Pause captures one Surface on entry. First visits build cached images; memory is traded for stable subsequent frames.

600 warm desktop SDL-dummy menu frames: median 0.47 ms, p95 1.19 ms. This measures drawing only, not browser/mobile FPS or audio latency. PyGBag archive grows from 1,040,397 to 1,824,740 bytes, primarily due to the new font; playback streams existing audio as before.

## Verification

- Existing 98 note/judgment/flick/pause/chart/catalog/track regression tests passed.
- Seven new functional UI tests passed: all 30 cards and page boundaries, all difficulty/length/action controls, web hiding of desktop-only studio, existing settings handler calls, non-overlapping hit rectangles, stable repeated pause frames, bounded titles and visible updating score.
- Eight scene captures inspected: home, longest-title selection, four note types with HUD, pause, result, failed, loading, ready. Reproduce with `python tools/render_ui_preview.py`; images and draw timing are in `render-ui-v4/`.
- PyGBag 0.9.3 / Python 3.12 build succeeds. Separate `/glass-stage/` destination only; original root and `/glass/` artifact SHA-256 hashes match the saved baseline.

## Limits

This is an independently drawn adaptation, not a pixel-identical recreation. Character art, original jackets, currency, rewards and unsupported filters are intentionally absent. Screenshot references cannot establish motion timings. Physical touchscreen performance, mobile FPS and per-song audible sync were not measured by these rendering tests. The separate desktop chart editor retains its own editing layout and launch behavior.
