# Rhythm Stage NEXT

최근 추가 작업: [PERFECT/AP 콤보](docs/ap-combo/README.md), [박자 가이드라인 전후 캡처·검증](docs/beat-guides/README.md), [가챠 DAY 3 배너 선택·검증](docs/gacha/day3.md), [판정 텍스트 DAY 8 전후 캡처·검증](docs/judgment-text/README.md). 각 보고서는 구현 당시 검증 기록입니다. 2026-10-29 후속 요청으로 GitHub Pages 배포를 진행하며 공개 경로는 `/next-stage/?v=20261022-track`을 유지합니다.

## Gacha DAY 1 design (2026-10-26)

설계 전용 문서: [아키텍처](docs/gacha/architecture.md), [레퍼런스 관찰](docs/gacha/references.md), [실행한 검증과 후속 계획](docs/gacha/validation-plan.md).
DAY 1 당시 가챠는 설계만 존재했습니다. 현재 체크아웃에서 누락된 과거 테스트 및 export 파일은 검증 문서에 구분했습니다.

## Gacha DAY 2 local implementation (2026-10-27)

HOME의 GACHA 메뉴와 정적 안내 화면을 구현했습니다. `/next-stage/#/gacha`에서 확인할 수 있습니다.
곡 목록 DOM과 선택 상태를 보존하며, 추첨·재화·저장은 아직 없습니다.
[실제 변경·브라우저 검증·캡처·남은 제약](docs/gacha/day2.md)을 참고하세요. DAY 2는 커밋·push·배포하지 않았습니다.

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
