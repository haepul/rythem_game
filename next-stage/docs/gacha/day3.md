# 가챠 DAY 3 — 임시 배너 선택 (2026-10-28 KST)

로컬 구현. **commit / push / 배포 없음.** 원본 사이트·유리 버전은 수정하지 않았다.

## 실제 기준

- Git root: `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`
- origin: `https://github.com/haepul/rythem_game.git`, branch `main`
- HEAD: `b7b5d1b4a7fd45cf36f8271852d6c6da872205f8`
- 상위 디렉터리 및 저장소에 적용할 AGENTS.md를 찾지 못했다.
- DAY 2의 README/app/index, gacha/view/CSS, menu-navigation, docs와 테스트가 미커밋 상태였다. 진행 중인 DAY 8 play-hud, 판정 span/cache 연결, fixture도 존재했다. reset/clean 없이 보존했다.
- DAY 2 메뉴 테스트 7개와 실제 가챠→곡 선택 왕복을 먼저 확인한 후 구현했다. 기존 라우터를 재사용했다.

## 변경 파일과 데이터 계약

| 파일 | 역할 |
|---|---|
| `gacha/banners.mjs` | 배너 3개, 독립 자산 레지스트리, 허용 테마, 데이터 검증 |
| `gacha/banner-selection.mjs` | selectedBannerId, 선택 no-op, 취소/세대 번호, 이미지 로드 수명 |
| `gacha/view.mjs` | 한 번 마운트하는 목록·큰 비주얼·복귀 버튼; 안전한 textContent 갱신 |
| `gacha/assets/mint.svg`, `lilac.svg`, `peach.svg` | 직접 작성한 마름모/원/삼각형 SVG |
| `gacha.css` | 가챠 범위의 2열 PC / 가로 목록 모바일 배치, 선택·focus·확대 대응 |
| `app.mjs` | 기존 adapter에 setVisible/syncMotion 및 BFCache 수명 연결, view import 버전 |
| `index.html` | app/gacha CSS 캐시 버전만 DAY 3 갱신; 기존 HUD 연결 유지 |
| `tests/test_gacha_banners.mjs`, `tests/gacha-banners.html` | 상태/비동기 회귀 및 운영 데이터를 바꾸지 않는 오류 fixture |
| `README.md`, `docs/gacha/architecture.md`, 이 문서/캡처 | 실제 구현과 후속 연결 명시 |

오늘 정의는 DAY 1 BannerDefinition의 **표시 부분**이다. `id, title, subtitle, previewLabel, artKey, themeKey`를 사용한다. DAY 1 후보 `placeholderArtKey`는 표시 자산 키 `artKey`로 구체화했다. `configVersion/pool/costs/guaranteeRule/bonusRule/exchangeRule`은 아직 구현하지 않았으며 가짜 값을 넣지 않았다.

DAY 4 연결점은 `view.selectedBannerId`이며 안정적인 ID는 `demo-mint`, `demo-lilac`, `demo-peach`다. 세부 화면은 이 ID로 정의를 조회하면 된다. 제목이나 배열 인덱스를 키로 사용하지 않는다. 자산은 `new URL(..., import.meta.url)`로 해석하여 GitHub Pages 하위 경로에서도 현재 모듈 위치를 따른다.

## 상태·접근성·모션

- selectedBannerId가 유일한 선택 상태. 첫 유효 배너로 초기화하며 가챠 왕복에는 유지, 새로고침에는 첫 배너로 돌아간다. localStorage 추가 없음.
- 같은 ID/미지 ID/숨김 상태의 선택은 no-op. 제목·설명·비주얼·aria-pressed를 한 번의 선택 처리에서 갱신한다.
- 목록은 native button + aria-pressed. 민트 윤곽과 `✓ 선택됨` 텍스트를 함께 사용하며 색상만으로 구분하지 않는다. Enter/Space 기본 동작과 포커스 보존, 단일 aria-live 안내를 사용한다.
- 배너 선택은 #/gacha 내부 상태로 history를 쓰지 않는다. 기존 HOME guard, 곡 필터 [data-view], 선택 복원은 그대로다.
- 이전 이미지 요청은 AbortController로 취소하며 generation이 다르면 뒤늦은 성공/실패가 화면을 바꾸지 못한다. 숨김 시 이미지 작업과 WAAPI를 취소, 재진입 시 마지막 선택을 정적으로 복원한다. thumbnail 실패도 숨김 중에는 DOM을 변경하지 않는다.
- 전환은 `--ui-normal`(기본 200ms)의 opacity + translateY(4px)만 사용. 자동 재생·상시 RAF·Pixi·blur 없음. 효과 OFF 및 OS reduced-motion은 visualEffects와 CSS 토큰으로 연결되며 현재 모션을 취소한다. animationend에 상태 확정을 의존하지 않는다.
- 이미지 실패는 기본 도형을 유지한다. 빈/잘못된 데이터에서도 복귀 버튼이 남는다. 중복 ID와 필수 필드 누락은 validation errors로 확인할 수 있다.

## 그래픽 근거

민트 마름모, 라벤더 원, 살구 삼각형은 이번 작업에서 직접 만든 SVG다. 외부 이미지·로고·캐릭터·음원·스크립트·SVG 외부 참조를 사용하지 않았다. 제목은 이미지가 아닌 DOM이다.

DAY 2/공통 디자인 시스템의 밝은 패널, 민트 선택 테두리, 작은 기하 장식을 계승했다. 16:9와 200ms는 우리 레이아웃/모션 선택이며 프세카의 공식 규격이라고 주장하지 않는다. 이번 배너 단계에서 새 외부 자료를 실측하거나 공식 가챠를 관찰했다고 주장하지 않는다.

## 실행 검증

실행 위치는 위 Git root다.

```text
git status --short --branch
git diff --check
node --check next-stage/app.mjs
node --check next-stage/gacha/view.mjs
node --check next-stage/gacha/banners.mjs
node --check next-stage/gacha/banner-selection.mjs
node --test tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs tests/test_judgment_text.mjs
node tests/test_judgment_3d.mjs
```

구문/공백 검사 통과. 배너 9개 + 메뉴 7개 + 판정 텍스트 18개 = **34개 통과**. 기존 판정선 geometry/layers/static body/OFF/80ms/60·120Hz simulation/pools/4종 노트 점수 테스트도 통과했다. 이는 실제 기기의 FPS 측정은 아니다.

배너 테스트는 ID·필드·실제 SVG 파일, 동일/미지 ID no-op, A→B→C의 역순 완료, 숨김/재진입/destroy 뒤 늦은 응답, 이미지 실패·누락, 빈 목록, 동기 loader 오류를 검증한다.

`git diff --name-only`에서 core.mjs/audio.js/renderer.mjs/data/note-skin.mjs/note-palette.mjs 변경 없음. DAY 8 HUD 변경은 별도 [판정 텍스트 보고서](../judgment-text/README.md)에 기록했다.

## 실제 브라우저

로컬 서버 `http://127.0.0.1:8782/next-stage/` (같은 체크아웃의 기존 서버 재사용), IAB Chromium.

| 항목 | 관찰 |
|---|---|
| 세 배너 | title/hero src/feature ID/선택 버튼 ID 일치, 선택은 정확히 1개 |
| 키보드 | Enter로 라일락, Space로 피치 선택. 포커스 유지. 마지막 버튼 Tab→복귀 버튼, Enter→곡 선택 |
| 왕복 상태 | 나다움 MASTER 전체곡, 검색 `나`, BPM 정렬, grid scroll 0이 전후 동일. 마지막 배너 선택도 유지 |
| 이력 | 배너 3개 선택 후 한 번의 뒤로가기로 이전 문서 진입. 배너별 이력이 생기지 않음. 다시 앞으로/메뉴 왕복·뒤로 복귀 확인 |
| 모바일 | 360×800 / 390×844 / 844×390. 본문 scrollWidth 345/375/829 ≤ viewport. 배너 목록만 가로 스크롤, 버튼 230×96px |
| PC | 1366×768에서 좌측 목록/우측 큰 비주얼. 본문 세로 스크롤로 복귀 버튼 접근 |
| 효과 OFF | 실제 설정에서 body.reduced 및 --ui-normal:0ms, 선택 표시 즉시 반영. ON으로 복원 |
| 오류 fixture | 실제 missing image 요청 후 fallback=true, hero image 0, 선택 제목 유지. 빈 목록과 이미지 실패 모두 복귀 작동 |
| 긴 제목 | 별도 fixture의 긴 한국어 제목 + root font 200%, 360px에서 줄바꿈. 본문 폭345, 제목43.2px; 세로 스크롤로 복귀 가능 |
| 일반 게임 | 나다움 HARD 1절 다운로드→일반 시작→무입력 18 MISS GAME OVER→곡 선택 복귀 |
| 연습 게임 | READY→진행/LIFE100→일시정지→00:39에서 재개, ESC 재정지 및 메뉴 복귀 |

오류 fixture 초기에는 선택한 시험 데이터를 view에 전달하지 않아 항상 기본 배너가 표시되었다. 옵션 전달을 수정하고 실패/빈 목록/긴 제목을 재검증했다. 초기 캐시로 구 DAY 2 view가 로드되는 현상도 app/view/CSS 버전 및 fixture import를 맞춰 해소했다. 이 두 문제를 통과 결과로 숨기지 않았다.

## 캡처

[PC](day3-desktop.jpg) · [360×800](day3-360.jpg) · [390×844](day3-390.jpg) · [844×390](day3-844.jpg) · [긴 제목/200%](day3-long-200percent.jpg)

모두 실제 브라우저 full-page 캡처이므로 이미지 세로 길이는 viewport와 다르다.

## 남은 확인 / 제외 범위

Android/iOS 실기기, 물리 터치, 스크린리더, 실제 OS reduced-motion 전환, 청음/음악 offset, GPU FPS·heap 측정은 미실행이다. 200%는 fixture의 root font 확대이며 브라우저 OS 전체 확대와 구별한다. BFCache cancel/restore는 구현했지만 브라우저가 실제 BFCache를 사용했는지는 계측하지 않았다. 페이지/큰 스크롤 상태의 상세 반복 회귀는 DAY 2 결과와 코드 보존에 기대며 오늘은 위 표의 상태만 재검증했다.

추첨·확률·재화·보관함·교환·결제·실제 캐릭터는 추가하지 않았다. 로컬만 변경했으며 commit/push/배포는 하지 않았다.
