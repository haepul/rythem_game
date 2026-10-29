# 가챠 DAY 2 — 메뉴와 기본 화면

작업일: 2026-10-27 KST. 로컬 구현만 수행. 이번 변경의 commit / push / 배포 없음.

## 기준과 보존 범위

- Git 루트: `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`
- remote: `https://github.com/haepul/rythem_game.git`, branch: `main`
- 시작 HEAD: `b7b5d1b4a7fd45cf36f8271852d6c6da872205f8`
- 시작 사용자 변경: README 수정, 미추적 `docs/gacha/architecture.md`, `references.md`, `validation-plan.md`. 삭제/초기화하지 않았다.
- 적용할 AGENTS.md와 package.json은 검사에서 발견되지 않았다.
- `Desktop/game`, 원본 사이트, 유리 버전, 판정대·노트·채보·오디오·SCORE/LIFE/COMBO·결과 저장 코드는 변경하지 않았다.
- 앞선 wide-deck 배포는 별도 작업이며 Pages run `40337795340` 성공 및 공개 renderer 응답을 확인했다. DAY 2 화면은 그 공개 버전에 포함되지 않는다.

## 실제 변경 파일

| 파일 | 변경 이유 |
|---|---|
| `next-stage/index.html` | HOME opt-in shell, 별도 GACHA 버튼, library/gacha wrapper와 스타일/module 연결 |
| `next-stage/app.mjs` | 메뉴 adapter, 선택 표시 책임 분리, focus/scroll 복원, catalog 미준비 guard |
| `next-stage/menu-navigation.mjs` | HOME 전용 hash/history, 중복 이벤트 방지, mount/destroy |
| `next-stage/gacha/view.mjs` | 정적 CSS/SVG 카드와 복귀 callback; 저장/추첨 기능 없음 |
| `next-stage/gacha.css` | 민트/라벤더 안내 패널, 44px 조작 영역, 모바일 메뉴 보완 |
| `tests/test_menu_navigation.mjs` | 주입한 host로 실제 route/guard/history 동작 7개 검증 |
| `tests/serve_menu_cases.py` | 실제 catalog를 건드리지 않는 empty/503/20초 delay HTTP fixture |
| `next-stage/README.md`, `docs/gacha/architecture.md`, `validation-plan.md`, 이 보고서·캡처 | DAY 1 기록 보존, 현재 기준 및 사용자 일정 정정 |

## 동작 계약

- 게임 state와 별개로 `menuScreen=library|gacha`. `view=all|favorites|records`와 `[data-view]`는 곡 필터로 유지한다.
- 일반 왕복은 `home()`을 호출하지 않고 기존 library DOM을 숨기거나 표시한다. 검색/정렬/곡/난이도/길이/페이지를 재설정하지 않는다.
- 가챠에서 FAVORITES/RECORDS를 누르면 library로 전환한 뒤 기존 필터 정책을 실행한다. 복귀 버튼은 이전 필터를 유지한다.
- 최초/미지 hash는 replace로 `#/library`, 직접 `#/gacha`는 가챠. pathname/query 보존. 다른 메뉴만 push, 동일 메뉴와 popstate/hashchange 중복은 적용하지 않는다.
- LOADING/COUNTDOWN/PLAY/PAUSED/CLEAR/RESULT에서 이동을 거절하고 hash만 마지막 유효 값으로 replace한다. 게임/오디오 호출 없음.
- 가챠 진입 시 제목 focus. 복귀 시 이전 library 요소와 grid/window scroll 복원, 요소가 제거/disabled이면 검색으로 대체한다. 결과→HOME은 검색 focus.
- HOME 메뉴 변경은 settings/help만 닫는다. PAUSED에서 router adapter를 실행하지 않아 기존 pause 모달과 resume 경로를 유지한다.
- 전환은 기존 `--ui-normal:200ms` opacity/transform. 이전 animation/복원 RAF를 취소하고 완료 callback에 화면 상태를 맡기지 않는다. 효과 OFF/reduced-motion이면 animation을 생략한다.
- history listener와 view listener는 한 번 등록하고 destroy 지원. pagehide의 비-BFCache 이탈에서 해제하고 BFCache 복원에는 기존 연결을 유지한다.
- DAY 3 실제 마운트: `#gacha-screen #gacha-content`. 오늘은 준비 안내와 자체 도형만 있다. 가짜 추첨/상세 버튼·잔액·캐릭터·새 저장 키 없음.

## 자동 검사

실행 명령:

```text
git status --short --branch
git diff --check
node --check next-stage/app.mjs
node --check next-stage/menu-navigation.mjs
node --check next-stage/gacha/view.mjs
node --test tests/test_menu_navigation.mjs
node tests/test_judgment_3d.mjs
```

메뉴 7개 통과: 초기/잘못된 route, 같은 메뉴 반복과 mount 중복, popstate/hashchange 중복,
6개 비-HOME state 거절, 100회 빠른 순차 전환, destroy 이후 이벤트 무시, 게임 HOME replace.
기존 판정선 테스트 통과: geometry/layers/static body/OFF/80ms reflection/60·120Hz hot path/
pool 상한/TAP·FLICK·HOLD·SLIDE 엔진 점수. 이는 테스트 시뮬레이션이며 실제 기기 FPS 측정이 아니다.
문법 검사와 diff whitespace 검사 통과. 누락된 `test_web_next.mjs`는 실행하지 않았다.

## 실제 브라우저 확인

IAB Chromium, HTTP `127.0.0.1:8782/next-stage/`; 별도 실패 fixture는 8783.
브라우저 상태 주입 없이 화면 컨트롤과 URL, DOM 읽기로 확인했다.

| 항목 | 관찰 결과 |
|---|---|
| 곡 선택 왕복 | 숙명, MASTER, 전체 곡, BPM 정렬, 2/3페이지, grid scrollTop=392, 선택 카드 focus가 전후 동일 |
| 검색 | `나` 검색 후 왕복: 검색어·1 TRACKS·검색 focus 유지 |
| 필터 | 가챠→FAVORITES 0곡, 복귀도 FAVORITES 유지; 가챠→RECORDS 기존 기록 1곡 |
| route | 직접 가챠/새로고침/뒤로/앞으로/unknown→library 확인, query 보존 |
| 키보드 | 제목→Tab 복귀 버튼, Enter 복귀, Space 가챠, Shift+Tab 설정; 숨겨진 library 건너뜀 |
| HOME 모달 | settings/help 열린 상태에서 hash 메뉴 이동 시 닫힘, 가챠 제목 focus |
| 빈 catalog | 가챠 정상, 복귀 시 등록된 곡 없음; 시작/연습 disabled |
| 503 catalog | 가챠 정상, 복귀 시 오류 안내; 시작/연습 disabled. fixture의 의도된 503 |
| 20초 지연 | 데이터 0개인 동안 메뉴 왕복 가능·시작/연습 disabled; 완료 후 12개 카드·가챠 active 유지·시작 enabled |
| 효과 OFF | body.reduced 상태에서 가챠 진입/복귀 및 HOME 모달 닫힘 확인. 설정은 ON으로 복원 |
| 일반 플레이 | 나다움 HARD 1절 로딩/게임 진행→18 MISS GAME OVER→곡 선택. 결과 중 가챠 hash 거절 |
| 연습 모드 | READY→실제 진행 시간 00:09, LIFE100; PLAY hash 거절; pause→hash 거절(모달 유지)→resume 00:11; ESC→곡 선택 |
| 반복 전환 | 브라우저 10회 왕복 후 최종 가챠, 관찰한 runtime error 로그 없음 |
| 화면 크기 | 1366×768, 360×800, 390×844, 844×390. 가로 넘침 없이 세로 스크롤로 복귀 접근 |

360px에서 모바일 메뉴 라벨이 나뉘는 문제를 확인하고 아이콘/라벨을 세로 정렬했다.
360px nav 실측 최소 44px, GACHA 58.7×49px, body scrollWidth345 ≤ viewport360.
가로 844px에서도 body scrollWidth829 ≤ viewport844; 제목 Tab으로 아래 복귀 버튼에 접근했다.
PC 기본 패널 여백도 줄여 반환 버튼이 더 일찍 보이도록 수정했다.

## 캡처

- [PC 1366×768](day2-desktop.jpg)
- [모바일 360×800](day2-mobile-360.jpg)
- [모바일 390×844](day2-mobile-390.jpg)
- [모바일 가로 844×390](day2-landscape.jpg)

캡처는 실제 페이지의 full-page 이미지이므로 세로 길이는 viewport보다 길 수 있다.

## 한계와 남은 확인

- Android/iOS 실기기, 물리 터치, 스크린리더, OS reduced-motion 설정 변경은 수행하지 않았다. reduced-motion 연결은 코드 확인, 기존 effects OFF는 브라우저 확인이다.
- 재개 시 화면의 clock/progress 진행은 확인했지만 청음·악곡별 오디오 offset 정밀 동기 검사와 실제 60/120Hz FPS·heap 측정은 수행하지 않았다.
- 중복 이벤트 동작은 단위 테스트와 10회 브라우저 왕복으로 확인했다. 장시간 메모리 누수가 없다는 주장은 하지 않는다.
- 새로운 Pixi 루프, 상시 파티클, blur, 프레임별 텍스처/Canvas 작업은 추가하지 않았다. 메뉴 전환에만 단일 WAAPI animation/복원 RAF가 사용된다.
- 범위 밖 추첨/확률/배너/재화/저장/교환은 다음 단계 작업이다. 사용자 일정은 architecture.md DAY 2 정정을 따른다.
- 로컬 구현 완료. 이 DAY 2 변경은 commit하지 않았고 push/배포하지 않았다.
