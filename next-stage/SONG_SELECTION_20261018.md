# Song selection redesign — 2026-10-18

Scope: NEXT song selection only. Files: song-select.css, index.html, app.mjs. No deployed files changed during this phase.

Reference: actual song-selection screenshot inspected earlier in this task at https://cdn-ak.f.st-hatena.com/images/fotolife/y/yashihei/20231230/20231230155754.png from https://yashihei.hatenablog.com/entry/2023/12/30/181813 . Square jackets, compact consistent gaps, outlined selection and violet side detail informed the layout. Bright mint/white/pastel colors remain Rhythm Stage's own theme. No reference artwork copied.

Implemented a 4/3/2-column responsive jacket grid, 16px desktop gaps, uniform 2px card borders, bright cyan selection with white highlight, check badge, restrained unselected art, fine-pointer hover scale, reduced-motion-aware selection transition, static dot/diagonal patterns. All selectors are scoped to #home or the new pagination component. Shared tokens remain in ui-system.css.

Pagination uses 12 songs with previous/next boundaries, preserved selected song, and reset on search/sort/filter changes. The selection click updates existing card states instead of rebuilding the grid, preserving keyboard focus. Search, favorites, records, sort, difficulty, full/verse and practice controls remain. Song card title is two lines; detail and accessible name retain the whole title. Existing PNG/fallback covers remain.

Browser checks:
- Desktop 1280x800 screenshot reviewed against reference; adjusted desktop list height after first capture to keep pagination visible.
- Page 3 has six tracks, Next disabled, selection ID 27 matches Salt, Pepper, Birds, and the Thought Police and covers/27.png; focused card stays 27.
- Search Salt resets to page 1/1; empty query result disables both page controls and displays empty message.
- BPM ascending places ID 26 first; Enter selects Rendezvous with correct title/state.
- Mobile 390x844: document width 375 (scrollbar excluded), no horizontal overflow, long title retained in detail.
- Captures: ../song-select-desktop.png and ../song-select-mobile.png.
- node --check web-next/app.mjs; keyboard bridge test passed; existing 34985 judgment samples/180 charts/30 songs test passed.
- core.mjs, audio.js, renderer.mjs and catalog hashes equal prior deployed copy.

Limits: no physical touch device or mobile FPS measurement. Existing original/glass sites are untouched. Public deployment remains the prior version; this phase is available in the local preview.
