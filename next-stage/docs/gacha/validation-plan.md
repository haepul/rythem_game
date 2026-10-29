# DAY 1 검증 기록 및 후속 회귀 계획

기준 날짜 2026-10-26 KST. 기준 HEAD `19bc813daeffe3ea2d1c4a4410b082ddb2176706`.
실행 위치 `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`.
이 문서의 미래 시험은 통과 기록이 아니다. 가챠 실행 코드는 아직 구현하지 않았다.

## 오늘 실행한 확인

| 명령 / 검사 | 결과 |
|---|---|
| Desktop/game에서 git 확인 | Git 저장소 아님. 수정하지 않고 실제 체크아웃 확인 |
| git rev-parse --show-toplevel / git remote -v / git branch --show-current / git rev-parse HEAD | 사용자 저장소 origin, main, 기준 HEAD 일치 |
| git status --short (시작) | 깨끗함 |
| git log -5 --oneline | 아래 5개 확인 |
| rg --files next-stage tests tools | 실행 성공, 실제 파일 목록 조사 |
| rg -n 'data-view\|localStorage\|history\|hashchange' next-stage -g '*.mjs' -g '*.html' | 필터/기존 저장 키 확인. 실제 실행 시 패턴은 정규식 OR의 `|` 사용 |
| history/hashchange/location.hash/pushState/replaceState/popstate 추가 검색 | 기존 runtime에서 일치 없음 |
| AGENTS.md / gacha / package.json 검색 | 적용 규칙 파일·기존 가챠·package.json 발견하지 못함. rg 일치 없음 exit 1은 예상 결과 |
| node --check next-stage/app.mjs | 통과, 실행 기능 테스트가 아닌 구문 검사 |
| git diff --check / git diff --stat | 실행. tracked 변경은 README 링크만; untracked 문서는 아래 별도 검사 |
| 공개 URL 브라우저 AX + 스크린샷 | 30곡·사이드바·설정·선택/난이도/길이/시작 UI 관찰. 버튼 조작·게임 진행·저장소 수정은 하지 않음 |
| 일본판 배너 메뉴 및 2023 연출 스틸 | 실제 이미지 관찰. 영상 재생 없음. 세부 범위는 references.md |

로그:
```text
19bc813 Clarify chart score maximum and harden rank HUD ratios
a96aa6d Publish horizontal score rank HUD and refined combo presentation
11017ac Refine score HUD and publish preserved LIFE improvements
fe58e0b Add luminous note materials and configurable mint ribbons
761d6fd Refine translucent playfield depth and lane edges
```

PowerShell에서 `next-stage/*.md`를 rg 파일 인자로 넘긴 조사 1회가 경로 구문 오류를 냈다.
`rg -n 'test_.*mjs' next-stage -g '*.md'`로 바꿔 실제 문서 참조를 확인했다. 테스트 통과로 치환하지 않았다.

### 누락 파일 — 실행하지 않음

| 문서가 언급하는 경로 | 실제 존재 | 처리 |
|---|---|---|
| tests/test_web_next.mjs | 없음 | 미실행 |
| tests/test_keyboard_bridge.mjs | 없음 | 미실행 |
| tests/test_play_hud.mjs | 없음 | 미실행 |
| tests/test_settings_motion.mjs | 없음 | 미실행 |
| tests/test_transitions_ui.mjs | 없음 | 미실행 |
| tests/test_final_ui.mjs | 없음 | 미실행 |
| tools/export_web_next.py | 없음 | 미실행, 채보 재생성 안 함 |
| tools/export_judgement_fixtures.py | 없음 | 미실행 |

`tests/`와 `tools/` 자체는 있다. 구버전 Python 및 test_browser_input.cjs를 NEXT 회귀 시험으로 대체하지 않았다.
기존 README/과거 보고서의 통과 수치는 오늘 재현한 결과가 아니다. README의 /next/, /web-next/ 설명도 과거 작업 경로다.
이 Git 체크아웃을 로컬 제공할 때는 저장소 루트 HTTP 서버의 `/next-stage/`를 사용해야 한다.

## 오늘의 문서 완료 점검

- [x] 실제 코드의 함수·선택자·기준 위치를 기록했다.
- [x] 메뉴/게임 상태 분리, hash와 dialog 우선순위, 빈 catalog 경계를 명세했다.
- [x] 모든 요청 화면의 와이어프레임과 모듈 의존도·상태도가 있다.
- [x] 카드/배너/receipt/envelope/NEW 계약과 version 일치 정책이 있다.
- [x] 저장 성공 전 성공 연출 금지, 실패/재진입 복구, 다중 탭 쓰기 차단 정책이 있다.
- [x] DAY 2 파일별 최소 범위를 지정했다.
- [x] 변경 범위는 설계 문서 3개와 README 링크뿐이다.
- [x] 실행 코드/CSS/catalog/공식 자산을 추가하거나 변경하지 않았다.
- [x] 사용자 저장소 직접 조작, commit/push/deploy 없음.

새 untracked 파일은 git diff --stat에 안 잡힐 수 있으므로 `git status --short --untracked-files=all`과
별도 Markdown 로컬 링크·끝 공백·코드펜스 짝 검사를 함께 사용한다. Mermaid의 실제 렌더링 검증은 미실행이다.

## 구현 후 실행할 회귀 행렬 — 현재 전부 미실행

| 영역 | 입력/시나리오 | 통과 기준 / 방법 | 단계 |
|---|---|---|---|
| 메뉴 복원 | 곡·MASTER·전체곡·검색·정렬·2페이지·스크롤 후 가챠 왕복 | ID/선택/필터/페이지/스크롤 동일; DOM 및 실제 클릭 비교 | DAY 2 |
| 필터 | 가챠에서 favorites/records 클릭 | library 먼저 표시, 기존 필터 적용, active/aria 단일 선택 | DAY 2 |
| catalog | 지연·실패·빈 배열 | 가챠 이동 가능, detail 참조 예외 없음, 플레이 버튼 비활성 | DAY 2 |
| history | 직접 hash/리로드/back/forward/unknown/동일 메뉴 | 중복 entry·루프 없음, query/path 보존 | DAY 2 |
| 플레이 guard | LOADING/COUNTDOWN/PLAY/PAUSED/CLEAR/RESULT 중 hash 변경 | 가챠 안 열림, 기존 audio clock/state 유지 | DAY 2 |
| dialog | HOME 설정/help 열린 상태 이동, ESC, focus 복귀 | 숨겨진 모달·배경 입력·focus 유실 없음 | DAY 2 |
| 게임 정상/연습 | 동일 곡 일반/연습 시작·pause/resume/retry/home | 판정·HP·sync·기록 정책 기존과 동일; 복구된 원본 회귀 시험과 브라우저 검증 | 통합 |
| 결과 저장 | 정상 clear vs practice/fail | 기존 records 저장 규칙 유지, 가챠 잔액과 무관 | 통합 |
| 키보드/터치 | D/F/J/K/SPACE, 키 반복, pointercancel, 다중 터치 | 가챠에서 게임 입력 소비 안 함, 플레이에서 기존 좌표/시각 유지 | 통합 |
| 확률/순수 추첨 | 고정 RNG, 경계 0/1 직전, 잘못된 RNG·weight | 결정론적 결과·오류, 표시와 실행의 configVersion 일치 | DAY 4 |
| NEW/중복 | 동일 10회 A,A; 기보유 A | 처음 미보유 A만 NEW, 재표시 때 불변, 보유 수 정확 | DAY 4–5 |
| 저장 실패 | setItem quota/security 예외, 파싱 손상, 음수/타입/unknownschema | 성공 UI/메모리 차감 없음, 원본 유지, 게임 키 보존 | DAY 5 |
| 연타 | 확정 double click, 동일 tx 재요청 | receipt 하나·차감 한 번, UI 즉시 잠금 | DAY 5–7 |
| 다중 탭 | lock 대기 중 두 번째 추첨/교환/ack | 최신 snapshot으로 직렬 처리; 미지원은 모든 쓰기 차단 | DAY 5 |
| 중단 복구 | commit 전/후 종료, 연출 중 reload, skip, asset 실패 | commit 전 무반영, 후 원 receipt 결과·무재추첨/무재차감 | DAY 5–9 |
| 확인 실패 | presentedAt 저장 실패 및 재확인 | pending 보존, 같은 결과 다시 표시, 무중복 반영 | DAY 5–9 |
| schema/누락 ID | 이전 버전·unknownID·migration 실패 | 백업·수량/기록 유지, fallback 도형, 알 수 없는 버전 쓰기 차단 | DAY 5 |
| 장기 기록 | 큰 snapshot·한도 근접 | 측정한 상한에서 신규 추첨 중지, 무단 삭제 없음 | DAY 5/13 |
| 교환 | 부족/중복클릭/실패/재진입 | 같은 잠금·snapshot으로 카드와 스티커 일괄 반영 | DAY 11 |
| 효과 접근성 | OS reduce / effects OFF / 중간 설정 변경 | 정적 결과, loop 없음, 결과 내용·확률 동일 | DAY 9/12 |
| 생명주기 | 메뉴 100회 왕복·연출 이탈 | listener/timer/animation 수 누적 없음, teardown 후 실행 0 | DAY 13 |

### 화면·입력 환경 행렬

| 환경 | 크기/조건 | 검증 내용 | 현재 |
|---|---|---|---|
| Windows 브라우저 | 1280×720, 키보드+마우스 | 3영역 배치, 5×2 결과, Tab/Shift+Tab/Enter/ESC, 외곽 focus | 미검증 |
| 좁은 viewport | 360×800, 390×844 | 2×5 결과, 긴 제목/ID, 44px target, 페이지 가로 넘침 0 | 미검증 |
| 가로 viewport | 844×390 | 세로 스크롤·모달 액션 접근·safe area·회전 상태 보존 | 미검증 |
| 확대/보조기술 | 글자 200%, screen reader, forced-colors | 금액/확률 전체 읽기, 결과 1회 알림, 희귀도 비색상 구분 | 미검증 |
| Android 실기기 | Chrome, 터치·저장 제한/잠금 | 실제 touch와 Web Locks, reload/다중 탭, 성능 | 미검증 |
| iOS Safari 실기기 | 세로/가로, safe area, 비공개/저장 제한 | 실제 입력·focus·dialog·lock·복구 | 미검증 |

실제 성능 계획: 동일 장치/곡/설정으로 기존판과 비교하여 메뉴·가챠·플레이 각각 RAF frame time p50/p95,
긴 작업 수, 왕복 전후 메모리/활성 animation 수를 기록한다. 60/120Hz는 각 장치 실제 갱신율을 기록한다.
설계만으로 FPS 수치를 약속하지 않는다. 음악 싱크·실제 FPS·Android/iOS 실기기 검증은 오늘 수행하지 않았다.

## 미해결 위험 / 다음 단계 진입 조건

1. NEXT 회귀 파일과 export 원본이 배포 체크아웃에 없다. 원본 위치·버전·fixture 출처를 확인한 뒤 테스트 복원 범위를 별도로 정한다.
2. catalog 빈 배열에서 현재 renderDetail은 안전하지 않다. DAY 2 메뉴 경계에 최소 guard 계획을 적었으며 오늘 버그 수정을 선행하지 않았다.
3. 기존 renderLibrary가 모든 data-view 표시를 다시 쓰므로 화면별 활성 상태 adapter가 필요하다.
4. 전역 closeDialogs와 설정의 PAUSED→resume 연결을 건드리면 sync 회귀 위험이 있다. 가챠는 HOME에만 허용한다.
5. 확률·비용·보장·보너스·교환·무료 잔액 정책 미정: 해당 정책을 정하지 않은 채 거래 UI를 활성화하지 않는다.
6. Web Locks 미지원 안전한 쓰기 정책을 실기기에서 입증하기 전에는 읽기 전용. DAY 5 gate 실패 시 IndexedDB 검토.
7. 구버전 결과 자료 접근 실패 및 모든 연출 영상 미관찰. 공식 시간·픽셀 재현을 주장하지 않는다.

DAY 2 진입은 [파일별 범위](architecture.md)의 navigation과 안내 화면에 한정한다.
구현·시험 결과가 확보되기 전 이 미래 행렬의 상태를 통과로 변경하지 않는다. 배포는 별도 요청이 필요하다.

## DAY 2 검증 추가 (2026-10-27)

위 DAY 1 결과와 미래 행렬은 당시 기록으로 유지한다. 현재 기준 HEAD는 `b7b5d1b4a7fd45cf36f8271852d6c6da872205f8`이다.
실제 새 메뉴 구현, 7개 행동 테스트, 기존 판정선 회귀, 브라우저 왕복/로딩 실패/모바일 검증은
[DAY 2 상세 결과](day2.md)에 기록했다. 위 빈 catalog 위험은 이번 최소 guard로 해결했다.
`test_web_next.mjs` 등 누락된 과거 테스트를 실행했다고 주장하지 않는다.
