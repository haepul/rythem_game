# HOLD / SLIDE ribbon activation — 2026-10-30

## Scope and reference
Baseline: `3d1180b53bd9bea4d91d127ba8ab29411663b1d0`. Only ribbon rendering and module cache pointers change in the release. Existing local DAY 5 gacha work is retained but excluded from this commit/deployment.

Inspected the [Colorful Palette article](https://media.colorfulpalette.co.jp/n/nf36e1946d71b) and its [actual slide screenshot](https://assets.st-note.com/img/1703212985149-8vMjyxt288.png?width=1200). Observed pale mint translucent paths, brighter connected regions and distinct heads. No official assets are included. The linked YouTube video could not be retrieved (cache miss); video playback was not verified. No claims about the official renderer implementation.

## Analysis and implementation
- Previous `drawRibbon()` used binary `n.active` opacity, one tint for all strips, constant-width strokes and a detached horizontal travelling bar. At 10% opacity the edge became too faint.
- `Stage.drawRibbon()` now delegates to `ribbon-light.mjs`; all other Stage methods are unchanged. Exact 25 times, judge.position(), project(), body width .38 and endpoints are preserved.
- Renderer-owned WeakMap stores a 60 ms smoothstep activation/release envelope from real `n.active`. Nothing is written into engine notes. Audio `now` is the only animation clock. Repeated paused time gives identical output; a backward clock resets the presentation safely.
- Existing mint palette supplies separate translucent body, core, thin central highlight and soft outer glow. Edges taper with projected width and keep a visibility floor at low opacity. Existing longOpacity still multiplies body and decorative light.
- One small tapered light patch follows the existing samples; no detached crossbar. It stops before endpoint heads. A small mint ellipse and 2 px stroke connect only the current local ribbon width at Y=410, with fade near the tail.
- Existing ribbon layer remains behind ALL note heads, judgment highlights and diamond pools. No new layer, texture, canvas or Sprite. Graphics and Float64Array are reused; WeakMap state allocates once per rendered note.
- Effects OFF/reduced motion keep the body/edge and snap brightness; outer glow, travelling patch and local connection reflection are omitted. The app already combines the effects setting and reduced-motion preference.

## Validation
Automated commands (run at repository root):
```powershell
node --check next-stage/app.mjs
node --check next-stage/renderer.mjs
node --check next-stage/ribbon-light.mjs
node --test tests/test_ribbon_light.mjs tests/test_ap_combo.mjs tests/test_beat_guides.mjs tests/test_judgment_text.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs
node tests/test_judgment_3d.mjs
git diff --check
```
New ribbon tests: 11 passed, including exact previous/current sample equality, straight/reverse slides, .1/.7/1 opacity, real Engine touch and key contact/release/rejoin/tail, engine purity, paused time, 60/120 Hz envelope, effect OFF, fixed diamond pools and no new warmed Canvas/Texture/Sprite allocations. Existing judgment deck/AP/beat/judgment text/navigation/banner regressions also passed.

Browser fixture: `/tests/ribbon-visual.html`. It uses the real Engine with deterministic synthetic charts/input, real Stage/head textures, existing PlayHUD and an actual MASTER chart. It is silent; it is NOT a full-song audio-sync test. `tests/fixtures/ribbon-before.mjs` freezes the exact baseline method for identical-scene comparisons.

Verified in desktop IAB:
- 1280×720 render resolution 1; 844×390 render resolution 2 (1600×960 backing canvas). Browser devicePixelRatio remained 1; this is not a physical DPR2 phone test.
- Passive/active/released HOLD, tail head, straight/right/left SLIDE (both directions also in dense scene), overlapping TAP/FLICK, four simultaneous longs plus dense taps, actual MASTER, opacity 10/70/100%, effects OFF and reduced-motion UI fixture.
- Keyboard key down/up registered 2 events with peakContacts=1. Pointer-only hold registered 3 events with peakContacts=1. Pausing the fixture clock preserved displayed now; resume uses the same engine. Engine-level tests verify unchanged ribbon command output at paused time.
- Tail and heads remain visible; low-opacity edges remain readable; transparent overlap does not cover TAP/FLICK. Existing diamonds are above the ribbon by unchanged layer order and pass the existing pool tests.

## Measured performance
240 measured frames after 20 warm-up frames; IAB, 1280×720, render resolution 1. `performance.json` retains all runs including the initial implementation and repeated baseline; measurements vary with browser scheduling, so these are local observations, not an FPS guarantee.

| Scene | Baseline render mean / p95 | Final render mean / p95 | Baseline / final RAF FPS |
|---|---:|---:|---:|
| Four active longs + 16 TAPs | 4.47 / 8.30 ms | 4.97 / 8.20 ms | 96.6 / 94.5 |
| Actual MASTER scene | 2.20 / 3.70 ms | 1.72 / 2.80 ms | 95.4 / 102.9 |

The dense synthetic scene costs about 0.50 ms more in the repeated comparison. Initial multi-segment light patches cost more; replaced with a single patch before final captures. RAF timing is not a physical refresh-rate measurement. Actual 120 Hz hardware and mobile GPU performance are untested; the 60/120 Hz *animation duration* is covered by deterministic tests.

## Captures
PNG conversions of actual browser screenshots. Compare the same named before/after scene and time:
- [Before HOLD](before-hold.png), [after HOLD](after-hold.png)
- [Before active HOLD](before-hold-active.png), [after active HOLD](after-hold-active.png), [release](after-hold-release.png), [tail](after-hold-tail.png)
- [Before SLIDE](before-slide.png), [after SLIDE](after-slide.png)
- [Before active SLIDE](before-slide-active.png), [after active SLIDE](after-slide-active.png), [tail](after-slide-tail.png), [straight](after-slide-straight.png)
- [Dense](after-dense.png), [mobile](after-mobile.png), [effects OFF](after-effects-off.png)
- [10% opacity](after-opacity10.png), [100% opacity](after-opacity100.png), [reduced motion](after-reduced-motion.png)

## Delivery and remaining limits
Deployment is authorized by the user's latest explicit request, overriding the attachment's earlier prohibition. Public entry remains https://haepul.github.io/rythem_game/next-stage/?v=20261022-track . App/renderer internal query versions are updated for caches. Original site, glass-stage and other versions are not modified. DAY 5 gacha wallet remains local.

Not verified: physical touch device, native DPR2 browser, hardware 120 Hz, full-song manual sustained input/audio timing, YouTube playback. No engine/audio/chart changes were made. The exact deployed-file hashes and GitHub Pages run are reported separately after upload.
