# DAY 9 — 확정 카드의 희귀도별 공개

2026-11-03 KST. 로컬 구현 및 검증 보고. commit/push/배포 없음.

## 시작 상태와 보호 범위

실제 root `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`, branch `main`, origin `https://github.com/haepul/rythem_game.git`, HEAD `77451317d7d3f7a68a36f54d8de0c932769465cb`. `git ls-remote origin refs/heads/main`도 같은 SHA였다. 조상/대상 경로에 적용 AGENTS.md 없음. 기존 DAY 8 미커밋 변경·캡처를 보존했다.

DAY 8 선행 테스트 154개 및 브라우저 Space skip/새로고침 동일 receipt 복원 후 확장했다. `core.mjs`, `renderer.mjs`, 판정/점수/LIFE/오디오/채보/게임 결과 저장, 추첨 엔진/설정/비용, wallet 저장 스키마·서비스는 변경하지 않았다. `app.mjs`는 가챠 모듈 import 버전 한 줄만 바뀐다. 원본/다른 게임 버전 변경 없음.

## 변경 파일과 이유

| 파일 | 변경 |
|---|---|
| `gacha/reveal-theme.mjs` | 순수 R2/R3/R4 테마 및 380ms 공개 시간 설정 |
| `gacha/card-reveal.mjs` | 전체 연출 완료 책임, 순서 기반 카드 공개, 재사용 DOM/WAAPI |
| `gacha/draw-view.mjs` | 확정 receipt 연결, 기존 모달/최종 목록 재사용, 공개/skip/focus 및 pagehide 정리 |
| `gacha/view.mjs` | 공개 옵션 전달, DAY 9 import |
| `gacha.css` | 가챠 공개 전용 스타일, 짧은 가로 화면과 고정 버튼 영역 |
| `index.html`, `app.mjs` | 변경된 진입 파일 및 CSS revision `20261103-day9` |
| `tests/gacha-flow.html` | 격리 고정 receipt, 오류/OFF/이탈 및 호출 카운터 fixture |
| `tests/gacha-play.html`, `gacha-banners.html`, `gacha-draw.html`, `gacha-wallet.html` | 변경한 가챠 진입 모듈/CSS 캐시 버전 일치 |
| `tests/test_gacha_reveal.mjs` | 31개 공개·통합 회귀 테스트 |
| `docs/gacha/day8.md`, `day9.md`, 캡처/검증 기록 | 선행 사실과 현재 검증 구분, 다음 단계 계약 |

기존 DAY 8 `intro-sequence.mjs`, `intro-view.mjs`, `test_gacha_intro.mjs`도 미커밋 의존 파일이다. 새 모듈의 상대 import는 Pages 하위 경로에서도 해석된다. 수정한 entry/view/draw-view/card-reveal/theme/CSS는 DAY 9 revision, 변경하지 않은 intro 모듈은 DAY 8 revision, 저장/추첨 모듈은 DAY 7 revision을 유지한다.

## 상태와 완료 책임

`createGachaPresentation()`이 intro → card(380ms 전환) → 수동 대기 → 다음 카드/finished를 소유한다. 카드를 읽는 시간에는 타이머가 없고 자동 진행하지 않는다. 전환 중 next는 false를 반환하며 버튼도 잠긴다. 전체 skip과 Escape는 intro/reveal 어느 단계에서도 바로 같은 최종 receipt로 간다.

입력은 저장 완료 receipt의 읽기 전용 복제본이다. `results[index]`만 읽고 정렬/중복 제거/카드 ID·희귀도 변경을 하지 않는다. 저장·차감·샘플링 모듈을 import하지 않는다. 한 실행의 done guard와 실행 객체 동일성, 카드별 token으로 중복 완료 및 이전 카드/실행의 늦은 콜백을 차단한다. 완료 시 타이머와 WAAPI를 취소한다. WAAPI.finished의 취소 rejection은 정상 정리로 처리하고 실제 오류는 기록한 뒤 기존 결과로 보낸다.

`changed:false`, 복원, 마지막 결과 다시 보기는 intro/reveal 모두 실행하지 않는다. hide/destroy는 present:false로 끝내고 UI를 갱신하지 않는다. 화면 재진입은 기존 서비스 restore를 읽는다. visibilitychange/pagehide 및 모션 설정 변경도 같은 정리 경로를 사용한다. 결과 표시 실패를 이유로 confirm을 다시 호출하지 않는다.

공개는 기존 dialog 안에서 진행한다. background는 native dialog로 차단한다. 결과 버튼은 본문 스크롤 밖으로 옮겨 확대/가로 화면에서도 조작할 수 있다. 다음 카드 및 최종 확인으로 포커스를 이동한다. 카드 위치·희귀도·ID는 카드당 한 번 aria-live로 갱신하며 애니메이션 프레임을 읽지 않는다.

## 자체 시각 설정과 비용

| 희귀도 | 형태/색 | 380ms 모션 | 최대 활성 입자 |
|---|---|---|---|
| R2 | 민트 단일 테두리 | 작은 밝기 변화 | 2 |
| R3 | 따뜻한 금색 이중 테두리 | 한 번의 광택 이동 | 4, 좁은 화면 3 |
| R4 | 파스텔 다색 테두리 + 내부 흰 선 | 한 번의 부드러운 확산 | 6, 좁은 화면 3 |
| 알 수 없음 | 중립 회색 점선 | 중립 공개 | 0 |

공식 프세카 규격이 아닌 프로젝트 자체 그래픽이다. 문자 R2/R3/R4와 테두리 형태도 달라 색상만으로 구분하지 않는다. 카드 그림은 외부 자산 없이 자체 마름모 placeholder를 사용하여 누락 이미지 요청이 없다. 실제 캐릭터·공식 리소스·소리 없음. 희귀도 상승을 암시하거나 결과를 바꾸는 효과 없음.

intro는 1450ms, 각 카드 전환은 `REVEAL_TIMING.card=380`. DOM 카드 1개, light 레이어 1개, 입자 6개를 mount 때 생성하고 재사용한다. 카드마다 Animation 객체는 생성/취소하지만 DOM/Pixi/Canvas/Texture를 새로 생성하지 않는다. 최대 동시 WAAPI는 8개, 좁은 화면 5개. 무한 모션·상시 RAF·BlurFilter 없음. **실제 FPS/프레임 시간은 측정하지 않았으므로 성능 수치를 주장하지 않는다.**

## 실행한 자동 검증

저장소 root에서 실행했다.

```powershell
git diff --check
node --check next-stage/app.mjs
node --check next-stage/gacha/draw-view.mjs
node --check next-stage/gacha/view.mjs
node --check next-stage/gacha/intro-sequence.mjs
node --check next-stage/gacha/intro-view.mjs
node --check next-stage/gacha/card-reveal.mjs
node --check next-stage/gacha/reveal-theme.mjs
node --test tests/test_gacha_intro.mjs tests/test_gacha_flow.mjs tests/test_gacha_draw.mjs tests/test_gacha_wallet.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs tests/test_gacha_reveal.mjs
node tests/test_judgment_3d.mjs
```

통합 **185/185 통과**, 실패·skip 0. 이 중 신규 reveal 31개, 선행 intro 28개. [실제 출력](day9-test-results.txt). syntax/diff check 및 별도 judgment_3d PASS. Windows Git의 LF→CRLF 안내는 whitespace 오류가 아니다.

R2/3/4/unknown, 1/10장 원래 순서·중복, next/skip 연타, 마지막 완료 경쟁, 이전 카드와 실행의 늦은 콜백, hide/destroy, OFF/도중 syncMotion, intro·카드·ready 오류, WAAPI 취소·오류, DOM 재사용/모바일 입자 상한을 검증한다. 실제 DAY 7 서비스로 저장한 1/10회 receipt에 정상/skip/오류/hide/OFF를 적용한 뒤 저장 문자열·쓰기 수·RNG 수가 같고 복원/동일 요청 재시도에 재연출이 없음을 검사했다.

## 실제 브라우저 확인

Windows IAB Chromium, `http://127.0.0.1:8785/tests/gacha-flow.html`의 격리 저장 키만 사용. 운영 데이터 초기화 없음.

- 고정 R2/R3/R4 및 10장 receipt를 미리 저장한 fixture. 실제 `confirm`의 중복 요청 복원 결과에 fixture에서만 `changed:true`를 주어 공개를 관찰한다. 운영 모듈에는 이 override가 없다. 고정 모드 RNG를 호출하면 throw한다. 10장 전부 확인 후 writes=0, rolls=0, confirms=1; 중복 카드 두 자리도 그대로 보였다.
- 1회 결과 확인 Enter/Space, 다음 카드 Enter/클릭, 전체 skip 클릭 및 Escape, 정상 10장 → 기존 목록 10개, 확인 버튼 focus를 확인했다.
- 새로고침 → 마지막 결과는 같은 요청 `day9-fixed-ten`의 10장, phases=[], revealed=[], writes/rolls/confirms=0이었다.
- 공개 100ms 후 OFF와 시작 전 OFF는 같은 결과로 이동했다. 카드 공개 오류 주입은 console에 원인을 남기고 같은 receipt/잔액으로 이동했다. 오류 fixture 이외 정상 새 탭 console error는 없었다.
- 공개 도중 메뉴 이탈 → 다시 열기 → 마지막 결과는 같은 receipt. 추가 confirm/RNG/쓰기가 없었다.
- 1366×768, 360×800, 390×844, 844×390에서 캡처/DOM 치수를 확인했다. 최종 모바일 세 규격 본문 가로 넘침 없음, 결과/skip 버튼 44px, 모달 안에 위치. [치수 기록](day9-captures/responsive.json).
- 가로 화면에서 처음 next 버튼이 스크롤에 가려지는 문제를 발견하고 짧은 화면 패딩/헤더/카드 크기를 조절했다. 200% CSS 확대에서는 버튼을 스크롤 밖 고정 영역으로 이동하여 둘 다 접근 가능하게 했다. 확대된 카드 본문은 세로 스크롤로 읽는다. OS/브라우저 자체 zoom과 CSS zoom은 동일 검사가 아니다.
- 격리 실제 앱 `tests/gacha-play.html`: Cry Baby/MASTER 선택 → 가챠 상세 확률 → Escape → 곡 메뉴 복귀 후 선택 유지. 일반 플레이/game over, 일반 재시작 후 일시정지·재개·메뉴 복귀, 연습 모드 진입·일시정지 확인. 실제 청음 동기화나 성공 완주 검증은 아니다.

### 캡처

- [R2](day9-captures/r2-desktop.jpg), [R3](day9-captures/r3-desktop.jpg), [R4](day9-captures/r4-desktop.jpg)
- [360×800](day9-captures/r4-360x800.jpg), [390×844](day9-captures/r4-390x844.jpg), [844×390](day9-captures/r4-844x390.jpg)
- [CSS 200% 확대](day9-captures/zoom-200.jpg), [기존 10개 결과 목록](day9-captures/ten-results.jpg)

### 미실행/제한

실기기 터치, Safari/Firefox, 화면 리더 청취, OS reduced-motion 실제 전환, FPS/프레임 시간/입력 지연/음악 청음 동기화는 미실행이다. IAB의 다른 탭 생성은 document.hidden 이벤트를 발생시키지 않아 실제 탭 숨김·복귀는 브라우저 통과로 표시하지 않는다. hide/destroy/늦은 콜백 및 motion 변경은 자동 테스트로 검증했다. safe-area CSS는 있지만 실제 노치 기기 검증은 없다. 정상 화면에 알려진 기능 차단 문제는 발견하지 않았다.

## DAY 10 결과 화면 계약

`createGachaPresentation({onFinish(receipt,{reason,present,id})})`가 유일한 전체 종료점이다. `present:true`면 read-only receipt를 기존/차기 결과 화면으로 전달하고, false면 표시하지 않고 재진입 시 `restore().receipt`를 읽는다. `receipt.request.requestId`로 결과를 식별하고 `results`의 순서와 중복을 유지한다. cardId/rarity/configVersion/schemaVersion은 저장 값을 그대로 사용한다. balanceBefore/After는 당시 확정 값이며 현재 잔액과 다를 수 있다.

DAY 10은 이 결과를 읽기만 해야 한다. 결과 화면을 열기 위해 confirm/execute/RNG/차감/저장을 호출하지 않는다. `changed:false`와 복원은 공개를 반복하지 않는다. 이번에는 정식 10회 그리드/NEW/보관함/교환을 구현하지 않았다.

## 배포 상태

DAY 7 Actions completed/success와 공개 파일의 커밋 일치는 [기록](day9-deployment-check.json)에서 확인할 수 있다. 이번 DAY 8/9는 **로컬 미커밋 상태**, commit/push/배포하지 않았다. 공개 고정 URL의 내용은 DAY 7이며 이번 공개 연출을 배포했다고 주장하지 않는다.
