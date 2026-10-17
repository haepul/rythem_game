# Rhythm Stage UI system v1

## Scope and architecture

Native HTML, CSS and ES modules remain unchanged as the stack. PixiJS owns the game canvas. `app.mjs` owns menu state and event wiring; `core.mjs`, `audio.js`, chart JSON and `renderer.mjs` are outside this change. `style.css` retains screen geometry and legacy screen-specific decoration. Load `ui-system.css` after it: shared component skins and semantic tokens are authoritative there. The legacy selectors are compatibility adapters, not a second theme to maintain. Gradually migrate screen-only literals when those screens are explicitly redesigned.

## Reference observations

Inspected the actual 1200×788 song-selection screenshot linked from https://yashihei.hatenablog.com/entry/2023/12/30/181813 (image https://cdn-ak.f.st-hatena.com/images/fotolife/y/yashihei/20231230/20231230155754.png).

- Square jackets, a prominent double selection outline, translucent violet surfaces, mint accents and compact rounded white controls.
- Jacket tiles are approximately 140px across in that source image; selection adds an exterior outline rather than altering art dimensions. Our square SVG jackets and existing grid geometry remain intact.
- Bold, compact labels create hierarchy. Exact font family, colors and animation duration cannot be reliably measured from this screenshot; our values are independent design choices.
- Official gameplay page https://colorfulstage.com/aboutgame/gameplay/ was read for context, not treated as a measured menu specification. No external image, logo, character or proprietary font was copied into the project.

## Tokens

`--ui-cyan/mint/soft/purple/pink` define accents. `--ui-text/muted/border/selected/focus` define semantic contrast. `--ui-surface/glass/accent` are gradient recipes. Mint is decoration; dark teal is used for small selected text and focus rings.

`--ui-space-1..6`: 4, 8, 12, 16, 24, 32px. `--ui-text-xs..xl`: 11, 13, 16, 20, 24px. Radius: 6/10/18px and pill. Shadows: control/panel/modal plus a separate inset highlight. Motion: 120/200/320ms and one easing curve. All can be overridden on a containing element for a future theme. Existing Stage font uses the bundled OFL font; no external font request. SVG strokes and the independent check mark scale at high DPR.

## Component contracts

| Component | Markup / state | Existing adoption |
|---|---|---|
| Button | native button `.ui-button`, optional `.ui-button--accent`; native `disabled` | `.primary`, `.secondary` compatibility selectors |
| Song card | native button `.ui-card` or `.song-card`, `aria-pressed` | current generated cards; existing `.selected` check decoration |
| Glass panel | `.ui-panel` | selected-song and result panels; layout preserved |
| Modal | native `dialog.ui-modal`, `aria-labelledby`, `.modal-heading`, form method=dialog | settings, help, loading; use showModal()/close(), retain native focus trap/Escape |
| Segmented tabs | `.ui-tabs` containing buttons with `aria-pressed` in a labelled group | song length; native Tab/Space/Enter; deliberately not ARIA tablist without tabpanels |
| Toggle button | button `.ui-toggle` + `aria-pressed` | available for future shared boolean controls |
| Switch | labelled input checkbox `.ui-switch` role=switch | flick and effects |
| Slider | labelled input range `.ui-slider` with min/max/value and output | volume; native keyboard/pointer behavior |
| Icon | svg `.ui-icon`, viewBox 0 0 24 24, aria-hidden when button has a label | settings and close controls |

Selected states use outlines, backgrounds and a check, not color alone. Navigation now exposes `aria-pressed` as well as the visual class. Do not remove native focus outlines; search has a focus-within ring. Reduced-motion respects both OS preference and existing game setting. Forced-colors supplies a visible selected outline. Glass uses alpha gradients without adding animated blur per card; only modal backdrop uses blur. CSS is static, with no per-frame JS added.

## Validation

- `node --check web-next/app.mjs`
- `node tests/test_keyboard_bridge.mjs`: all lane keys, SPACE, repeat suppression, blur releases, pause/resume gating.
- `node tests/test_web_next.mjs`: 34985 judgment samples, 180 chart variants and 30 songs.
- Only menu markup, navigation ARIA and CSS changed. Existing root/glass deployments and game modules were not modified.
- Browser checked at desktop 1280×720 and mobile 390×844: no horizontal overflow (375px document width), modal within viewport, volume arrow key changed 80→81→80, effects toggled with Space, Escape closed the modal, full-song selection updated aria-pressed and the actual chart summary. Desktop screenshot saved at `../design-system-20261017.png`.
- SHA256 compared core.mjs, audio.js, renderer.mjs and catalog with the previous deployment staging copy; all unchanged. New CSS is approximately 7 KB with no new runtime dependency or animation loop. Mobile GPU/frame-rate measurements were not performed.

This phase does not redesign screen layouts, replace all legacy screen-specific literals or claim pixel equivalence with Project SEKAI. No new gameplay functions or decorative nonfunctional buttons were added.
