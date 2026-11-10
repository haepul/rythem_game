# DAY 10 — 확정 추첨 결과 화면

작업 기준일: 2026-11-04 KST. **로컬 구현·검증 완료. commit/push/배포 없음.**

## 시작 상태와 보호 범위

- 실제 root: `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`
- origin: `https://github.com/haepul/rythem_game.git`, branch: `main`
- HEAD: `77451317d7d3f7a68a36f54d8de0c932769465cb`
- DAY 8/9 소스·문서·캡처·fixture 미커밋 변경이 이미 있었다. 이를 보존하여 이어 구현했다. 적용 범위의 AGENTS.md는 발견되지 않았다.
- 선행 intro/reveal/flow/draw/wallet/banner/navigation 테스트 **185/185**를 먼저 실행해 통과를 확인했다.
- 확률·비용·보장·지급 정책, 저장 키와 schemaVersion, 게임 판정·점수·LIFE·오디오·노트·채보·게임 기록 저장은 변경하지 않았다. 다른 게임 버전도 수정하지 않았다.

## 이번 변경 파일

| 파일 | 이유 |
| --- | --- |
| `gacha/result-model.mjs` | 확정 receipt와 이전 획득 이력으로 순수하고 불변인 결과 모델 생성 |
| `gacha/result-view.mjs` | 재사용 가능한 비대화형 카드, NEW, 배너/횟수/재화 요약 |
| `gacha/draw-view.mjs` | 기존 공통 종료점에 결과 화면 연결, 열린 결과 고정, 안전한 복귀 버튼 |
| `gacha/view.mjs` | 기존 onReturn 라우팅 콜백 전달, 변경 모듈 캐시 버전 |
| `gacha.css` | 가챠에만 적용되는 1장/10장·모바일·짧은 화면 스타일 |
| `app.mjs`, `index.html` | 변경된 가챠 모듈/CSS의 `20261104-day10` 버전 참조만 갱신 |
| `tests/test_gacha_results.mjs` | NEW/순서/불변성/저장 격리/DOM 재사용 테스트 15개 |
| `tests/gacha-flow.html` | 이전 소유 기록, 후속 기록, changed:false, 긴 폐기 ID 격리 fixture |
| `tests/gacha-{banners,draw,play,wallet}.html` | 가챠 모듈/CSS 캐시 참조 일치 |
| `docs/gacha/day10.md`, `day10-test-results.txt`, `day10-captures/` | 현재 실행한 검증과 캡처 기록 |

DAY 8/9의 intro/reveal 모듈을 재사용했다. HEAD와의 전체 diff에는 그 선행 변경도 포함되어 있으므로 모두 DAY 10 신규 구현이라고 해석하면 안 된다.

## 결과 모델과 NEW 계약

```js
buildResultModel(receipt, {history, historyComplete})
// -> frozen {
//   requestId, bannerId, count, cost, balanceBefore, balanceAfter,
//   newStatus: 'known' | 'unknown',
//   cards: [{key, index, cardId, rarity, isNew: true | false | null}]
// }
```

NEW의 의미는 **“이 추첨 당시 처음 획득한 카드”**다. history 배열에서 대상 requestId 앞에 저장된 receipt만 순회하고, 대상 results도 순서대로 처리한다. 처음 보는 ID만 true이고, 같은 10회 안에서 두 번째로 나온 ID는 false다. committedAt이나 현재 전체 보유 집합으로 정렬·재계산하지 않는다. 동일 timestamp도 저장 순서를 따른다.

카드를 ID로 합치지 않는다. DOM 식별은 `JSON.stringify([requestId,index])`를 사용한다. 저장된 cardId/rarity를 그대로 복사하므로 현재 카탈로그에서 사라진 ID도 표시된다. 모델과 입력 receipt/history는 변경하지 않으며 출력은 재귀적으로 freeze한다.

### 이력이 완전하다는 근거와 한계

현재 DAY 7 서비스의 성공 경로는 같은 잠금 아래 최신 지갑에 `receipts:[...old.receipts,nextReceipt]`를 한 번 저장한다. 일반 동작에서 receipt를 잘라내거나 삭제하는 경로가 없다. v1은 추첨 도입 전 지갑이며 v2 마이그레이션의 빈 receipts는 정상적으로 획득 이력이 없는 상태다. 명시적 가챠 복구는 전체 가챠 저장을 초기화하며 이전 receipt를 일부만 유지하지 않는다.

따라서 현재 앱에서는 오류 없는 schema2 지갑을 validateWallet로 검증한 뒤 historyComplete를 전달한다. 순수 함수의 기본값은 false다. 대상 receipt 누락/내용 불일치, 잘못된 이력, 중복 requestId, 명시적으로 불완전한 이력은 isNew=null로 반환한다. 화면에는 “획득 이력을 확인할 수 없어 NEW 여부를 표시하지 않습니다.”를 표시하며 카드는 유지한다.

현재 스키마에는 외부 수동 편집으로 유효한 receipt 일부만 삭제했는지 증명할 수 있는 연속 번호/이력 완전성 표식이 없다. 그런 데이터가 정상 스키마 모양이면 완전성을 판별할 수 없다. 이 한계를 숨기기 위해 스키마를 변경하지 않았다. 향후 일부 이력 가져오기나 교환 획득을 추가할 때는 historyComplete를 임의로 true로 넘기지 말고 획득 출처와 확정 순서가 통합된 이력이 필요하다.

## UI와 수명

- 기존 `createGachaPresentation`의 단일 onFinish를 사용한다. 정상 공개/skip/OFF/오류 fallback 모두 같은 확정 receipt로 결과를 표시한다.
- confirm 성공 직후 receipt를 복사하고 당시 NEW 모델을 고정한다. 결과 표시 모듈은 draw/RNG/차감/저장을 호출하지 않는다.
- changed:false, 마지막 결과 다시 보기, 새로고침 복원은 즉시 결과를 보여주며 연출을 반복하지 않는다.
- 결과 DOM은 한 번 만든 뷰를 재사용한다. 같은 결과에서 저장소 구독이 갱신되면 현재 잔액 텍스트만 바꾼다. 다른 탭의 후속 receipt가 현재 열린 결과/NEW/포커스/스크롤을 교체하지 않는다.
- 확인은 기존 모달 닫기 정책으로 가챠에 복귀한다. 곡 선택은 모달과 연출을 정리한 뒤 기존 `onReturn` → 메뉴 라우팅을 호출한다. 게임 `home()` 정리를 추가 호출하지 않는다.
- 결과 진입 시 확인 버튼에 포커스, 요약만 aria-live로 한 번 알림. 카드는 li이며 버튼/탭 정지점이 아니다. NEW는 문자 배지와 `NEW · 처음 획득` 접근성 이름을 제공한다.
- 1장은 가운데 큰 카드, 10장은 충분한 컨테이너 폭에서 5×2, 좁은 화면에서는 2열이다. 짧은 가로 화면은 하단 동작 버튼을 나란히 놓는다. 본문과 필요한 경우 모달을 스크롤할 수 있다.
- R2 민트 단일선, R3 금색 이중선, R4 파스텔 테두리와 문자 라벨을 사용한다. DAY 9 자체 테마/기하학을 재사용하며 공식 리소스는 사용하지 않는다.
- 요청 ID/내부 설정 버전은 결과 주요 화면에서 제거했다. 확인 모달의 요청 검토 정보는 기존 정책대로 유지한다.

## 실제 실행한 자동 검증

저장소 root에서 실행:

```text
node --test tests/test_gacha_intro.mjs tests/test_gacha_reveal.mjs tests/test_gacha_flow.mjs tests/test_gacha_draw.mjs tests/test_gacha_wallet.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs
node --test tests/test_gacha_results.mjs
node --test tests/test_gacha_intro.mjs tests/test_gacha_reveal.mjs tests/test_gacha_flow.mjs tests/test_gacha_draw.mjs tests/test_gacha_wallet.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs tests/test_gacha_results.mjs
node tests/test_judgment_3d.mjs
git diff --check
node --check next-stage/app.mjs
node --check next-stage/gacha/view.mjs
node --check next-stage/gacha/draw-view.mjs
node --check next-stage/gacha/result-model.mjs
node --check next-stage/gacha/result-view.mjs
node --check tests/test_gacha_results.mjs
```

결과: 선행 **185/185**, 신규 **15/15**, 합산 **200/200**, judgment_3d PASS, 구문/공백 검사 PASS. [실행 로그](day10-test-results.txt).

신규 테스트는 첫 획득/기존 보유/동일 10회 중복, 과거 결과 재열기와 JSON 복원/이후 추첨, 같은 timestamp, 누락·불완전·충돌 이력, 폐기 ID, 1/10장 순서와 입력 불변을 검증한다. 실제 draw service와 메모리 저장소로 저장 후 모델을 반복 생성해 RNG/쓰기 횟수/저장 문자열/잔액이 유지됨도 검사한다. 잔액만 바뀔 때 카드 DOM과 요약 알림을 재생성하지 않는 테스트를 포함한다.

## 실제 브라우저 검증

Windows IAB Chromium, 로컬 `http://127.0.0.1:8785/tests/gacha-flow.html` 및 `tests/gacha-play.html`. 고정 결과는 fixture 키 `rhythm-next-day7-flow-fixture`, 실제 앱은 `rhythm-next-day7-play-fixture:` 접두어로 격리했다. 사용자 운영 기록은 초기화하지 않았다.

- 이전 R2 획득 + 고정 10장: 순서대로 10번 공개 후 결과 10장. NEW는 최초 R3/R4 두 위치만 표시. writes=0, rolls=0, confirms=1. 이 경로는 미리 저장한 receipt에 fixture에서만 changed:true를 주어 공개한다.
- 같은 receipt의 정상 종료/ESC skip/효과 OFF/새로고침 결과 카드·NEW 배열이 일치했다. 새로고침 후 마지막 결과는 writes/rolls/confirms=0, phases/revealed=[]였다.
- changed:false 재시도: confirms=1, writes=0, rolls=0, phases/revealed=[]로 즉시 결과를 표시했다.
- 두 번째 탭에서 후속 R4 receipt를 저장했을 때 첫 탭의 10장/NEW가 유지되었다. 실제 결과 영역 scrollTop=95.2와 포커스도 유지되고 현재 잔액만 3,000→2,700으로 변경되었다.
- Enter/Space, Escape 닫기·skip, 확인, 곡 선택 버튼을 동작시켰다. 모바일에서는 마지막 9/10번 카드와 재화 요약까지 스크롤했다.
- 1366×768, 360×800, 390×844, 844×390에서 본문 가로 넘침 없음, 10장 유지, 버튼 최소44px/화면 내 접근 확인. 세로→가로 전환도 수행했다.
- CSS 200% 확대를 1366×768과 844×390에서 확인했다. 처음 짧은 화면에서 모달이 화면 밖으로 나가는 문제를 발견해 높이를 viewport 단위 대신 가용 비율로 제한하고 가로 버튼 배치/스크롤을 수정했다. CSS 확대는 OS/브라우저 자체 확대 검사와 동일하지 않다.
- 폐기된 긴 ID를 360×800에서 줄바꿈하여 표시했다.
- 격리 실제 앱에서 테스트 지급→1회 실제 저장→공개→결과→새 곡 선택 버튼을 사용했다. Cry Baby/MASTER 선택 유지, 열린 dialog=0을 확인했다. 일반 플레이·일시정지 진입과 Game Over, 연습 플레이·일시정지·재개·곡 메뉴 복귀를 확인했다. 재진입 후 마지막 가챠 결과와 NEW도 유지됐다.
- 정상 결과 fixture에서 확인한 console error는 0건이다. 카드 전체가 읽히는 시각 검증이며 화면 리더로 실제 낭독을 듣지는 않았다.

[브라우저 DOM 증거](day10-captures/browser-evidence.json)

### 캡처

- [PC 10장 및 재화 요약](day10-captures/ten-desktop.jpg)
- [가운데 단일 카드](day10-captures/single-desktop.jpg)
- [360×800](day10-captures/ten-360x800.jpg), [390×844](day10-captures/ten-390x844.jpg)
- [모바일 마지막 카드/요약](day10-captures/ten-mobile-bottom.jpg), [844×390](day10-captures/ten-844x390.jpg)
- [PC CSS 200%](day10-captures/zoom-200.jpg), [짧은 화면 CSS 200%](day10-captures/landscape-zoom.jpg)
- [긴 폐기 ID](day10-captures/long-retired-id.jpg)

## 성능과 미실행 항목

최대10장의 결과 DOM을 결과 진입에만 구성한다. 현재 잔액 업데이트는 텍스트만 변경한다. 매 프레임 작업, Canvas/Texture/Pixi Application, 반복 파티클, blur를 추가하지 않았다. NEW 계산은 저장된 이력 크기에 비례하므로 장기간 방대한 이력의 성능은 별도 측정이 필요하다.

실기기 터치/노치 safe-area, Safari/Firefox, 실제 스크린리더, OS reduced-motion 전환, OS/브라우저 자체200% 확대, FPS·프레임 시간·입력 지연·청음 동기화는 미실행이다. 실제 탭 숨김 복귀는 이번 브라우저 검증에 포함하지 않았다. hide/destroy/reduced-motion의 수명 계약은 선행 자동 테스트가 통과했다. 일반 게임의 성공 완주/새 게임 기록 저장을 이번에 별도로 검증한 것으로 주장하지 않는다.

## DAY 11 재사용 계약

- `createResultCard(doc,card)`는 비대화형 li를 생성하며 테마는 `revealTheme(rarity)`로 읽는다. 보관함은 자신의 순서/수량 모델을 준비하고 이 표현을 재사용할 수 있다. 결과 화면의 requestId+index 위치 식별을 cardId 집계로 바꾸면 안 된다.
- `buildResultModel`은 역사적 NEW 계산 전용이다. 보관함의 현재 보유량/필터/정렬은 별도 순수 모델로 구현한다. 결과의 과거 NEW를 현재 보유 집합으로 재계산하지 않는다.
- 현재 획득의 유일한 출처는 확정 receipts의 results다. 향후 교환 등 새 획득 출처를 추가하면 전체 확정 순서와 출처를 포함하는 획득 이력 계약이 필요하다. 부분 이력에서는 NEW를 unknown으로 유지한다.
- receipt/지갑/설정은 결과 표현 계층에 읽기 전용으로 전달한다. 보관함 진입/닫기/다시 보기 때문에 confirm, RNG, 차감, 저장을 호출하지 않는다.

## 릴리스 상태

DAY 10은 로컬 변경이며 기존 DAY 8/9 미커밋 작업과 함께 남아 있다. 자동 commit/push/배포를 수행하지 않았다. 공개 사이트에 DAY 10 결과 화면이 반영됐다고 주장하지 않는다.
