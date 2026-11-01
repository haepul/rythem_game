# DAY 7 — 무료 시뮬레이션 실행·저장 통합

기준일 2026-11-01 KST. 로컬 시작 HEAD `f8b4ecd32e0965b095032f57f350890bbd19781a`, `main`, origin `https://github.com/haepul/rythem_game.git`. DAY 5/6 미커밋 상세 안내·지갑·확률 엔진을 보존해 확장했다. 적용 대상 및 조상 경로에 AGENTS.md 없음. 원격 fetch 후 시작 HEAD와 origin/main 일치. Pages는 기존 `dynamic/pages/pages-build-deployment` 워크플로를 사용한다.

## 완료 범위와 규칙

- 실제 1회/10회 실행, 확인/취소, 안전한 차감·결과 저장, 단순 임시 ID/희귀도 목록, 마지막 결과 다시 보기, 새로고침 복원.
- 프로젝트 테스트 비용 `project-cost-v1`: 1회 300 / 10회 3,000. `wallet-config.mjs`에서 UI와 서비스가 함께 읽는다. 프세카 공식 규칙이 아니다.
- 기존 `project-test-v1`: R2/R3/R4 = 8,000/1,500/500 basis points. 각 등급 내 두 카드 균등. 10회는 독립 추첨이며 보장 `none` 유지.
- 초기 0, 저장 데이터당 1회 테스트 지급 3,000 유지. 운영 잔액을 반복 지급하거나 자동 충전하지 않는다. 비용과 확률은 서로 다른 버전 정책이다.
- 실제 캐릭터·결제·광고·현금성 가치 없음. 연출/정식 결과 그리드/보관함 필터/교환은 미구현.

## 저장 스키마 및 트랜잭션

기존 키 **`rhythm-next-gacha-wallet-v1` 유지**, 내부 `schemaVersion: 2`:

```js
{
 schemaVersion: 2,
 balance: 2700,
 claimedGrantIds: ['test-crystals-v1'],
 receipts: [{
  request: { requestId, bannerId, count, cost, configVersion,
             policyVersion, configFingerprint },
  results: [{cardId, rarity, configVersion, schemaVersion: 1}],
  balanceBefore: 3000, balanceAfter: 2700, committedAt
 }]
}
```

획득 결과는 receipt의 `results` 안에 함께 저장한다. 별도 인벤토리 키/잔액 키를 만들지 않는다. 마지막 결과는 `receipts.at(-1)`이며 전체 획득 이력은 receipts의 결과들이다. 같은 카드 중복 획득도 별개 결과로 보존한다. receipt ID 중복, 개수/타입/산술/설정 버전 불일치, 음수·비정수·안전 정수 초과를 거부한다. 이후 정책 변경에도 과거 receipt를 읽을 수 있도록 저장 형식 검증과 현재 실행 정책 검증을 분리했다.

유효한 v1은 잔액과 모든 지급 ID를 보존하고 빈 receipts를 추가한다. 조회는 쓰지 않으며 메모리에서 v2로 해석한다. 다음 정상 쓰기 또는 명시적 `store.migrate()`에서 공통 Web Lock 안에 v2를 저장한다. 취소/부족/실패 경로에서는 마이그레이션을 이유로 별도 쓰기를 하지 않는다. 손상/미래 버전은 자동 초기화하지 않는다.

모든 지급·복구·추첨은 동일 origin의 **키 + `:transaction`** exclusive Web Lock을 공유한다:

1. 최신 문자열 읽기 및 검증/v1 해석
2. requestId 중복 확인; 같은 내용은 기존 receipt 반환, 다른 내용은 충돌 오류
3. 최신 배너/설정/비용 재검증, 확인 모달의 fingerprint와 비교
4. 최신 잔액 확인 후 기존 순수 `drawCards()` 호출
5. 차감+결과+receipt+지급 이력 전체를 `setItem` 한 번으로 저장
6. 성공 후에만 메모리/화면 확정

Web Locks 미지원은 조회 전용이며 추첨/지급/초기화를 금지한다. localStorage 자체를 트랜잭션으로 간주하지 않는다. 기존 v1 작성기는 v2를 미지원 버전으로 거부하므로 자동 덮어쓰지 않는다. 다만 예전 탭에서도 사용자가 직접 복구 초기화를 확인하면 데이터는 삭제될 수 있다. 예전 탭은 새로고침하고, 정상 최신 데이터에 복구 초기화를 사용하지 않아야 한다. 외부 코드/사용자 개발자 도구가 공통 잠금을 무시하는 쓰기까지 보호하는 서버 저장소는 아니다.

정상 기록은 임의로 삭제하지 않는다. 용량 초과 시 기록을 잘라내지 않고 오류를 표시한다. 명시적 복구는 해당 가챠 키만 초기화하며 모든 결과/요청 이력도 사라짐을 확인 문구에 표시한다. 곡 기록·설정·즐겨찾기는 접근하지 않는다.

## 실패·재시도·상태

`idle → confirming → committing → result/error`. 하나의 실행 의도에 crypto.randomUUID를 한 번 생성하고 재시도에 유지한다. 확인 모달에서 배너/횟수/비용/버전과 fingerprint를 고정한다. 같은 버전 이름으로 설정 내용만 바뀐 경우도 거부한다. 저장된 요청은 설정이 이후 폐기되어도 그대로 복원한다.

확정 전 취소에는 RNG/차감/쓰기 없음. UI 및 서비스 모두 중복 실행을 막는다. 확정 중 닫기/Escape를 잠그며, 브라우저 뒤로 가기로 화면을 떠날 때는 모달만 닫고 진행 중인 쓰기를 롤백하지 않는다. 재진입은 저장소를 읽는다. 페이지 자체 종료 전 아직 잠금을 얻지 못한 작업은 확정되지 않을 수 있다.

쓰기 예외가 나면 정확한 저장 문자열을 다시 읽는다. 예외 뒤 실제 저장된 경우 기존 receipt를 성공으로 복원하며, 읽기까지 실패하면 `commit-unknown`으로 새 실행 대신 같은 요청 재확인을 안내한다. 저장 성공 후 DOM 구독자 오류가 발생해도 트랜잭션 성공을 실패로 바꾸지 않는다. 결과 표시 실패 때문에 재추첨하지 않는다.

저장 **이전** RNG 결과는 성공으로 노출하지 않는다. 저장이 확실히 실패하고 receipt가 없으면 같은 requestId 재시도에서 결과를 다시 생성할 수 있다. 미확정 결과/확인 중 의도는 프로세스 종료 시 사라지며, 마지막 확정 receipt는 새로고침으로 복원된다. 서버 계정 동기화나 브라우저 데이터 삭제 후 복원은 지원하지 않는다.

## 수정 파일

- `gacha/draw-service.mjs`: 확인 요청, 최신 정책 재검증, idempotency, 단일 저장 업데이트, 상태 및 복원 계약.
- `gacha/draw-view.mjs`: 실행/확인/오류/결과/마지막 결과 UI. 결과 전환 시 닫기 버튼으로 포커스 유지.
- `gacha/wallet-config.mjs`, `wallet.mjs`, `wallet-storage.mjs`: 비용, v2 및 마이그레이션, 공통 잠금, 저장 불확실성 재확인, 구독자 오류 격리.
- `gacha/view.mjs`, `wallet-view.mjs`, `details.mjs`, `gacha.css`: 공통 store 연결, 확률·비용 안내, 복구 문구, 범위 한정 UI.
- `app.mjs`, `index.html`: DAY 5 모달 정리 연결과 release query. 게임 로직 diff 없음. gacha 모듈 전체 동일 `v=20261101-day7` import로 혼합 캐시 방지.
- 선행 DAY 5/6 `cards/draw-config/draw-engine`, 테스트/문서도 이번 첫 통합 배포 의존 파일에 포함한다.
- `tests/test_gacha_flow.mjs`, `tests/gacha-flow.html`, `tests/gacha-play.html`: 통합/브라우저 fixture. 기존 지갑·확률 테스트는 새 비용/스키마의 기대값만 갱신하고 과거 경계·실패 테스트를 유지.

## 실행한 검증

```powershell
git diff --check
node --check next-stage/app.mjs
# next-stage/gacha/*.mjs 각각 node --check
node --test tests/test_gacha_draw.mjs tests/test_gacha_wallet.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs tests/test_gacha_flow.mjs tests/test_ap_combo.mjs tests/test_beat_guides.mjs tests/test_judgment_text.mjs tests/test_ribbon_light.mjs
node tests/test_judgment_3d.mjs
```

**185개 통과**: 새 통합 29 + 기존 가챠/메뉴 97 + 렌더링 관련 59. 별도 판정선 테스트 PASS. [실제 출력](day7-test-results.txt). 구문/공백 검사 통과. 게임 엔진·판정·점수·오디오·채보·노트·LIFE·결과 저장 코드는 변경하지 않았다.

통합 검증은 v1 및 지급 보존, 1/10 개수/비용, 취소·부족·RNG/저장 실패, 빠른 20회 요청, 두 탭 같은/다른 요청, payload 충돌 6종, UI 오류와 재로딩, 저장 이후 예외/확정 불명, 손상·미래·용량, 설정 내용 변경, 과거 receipt 보존, 지급/마이그레이션 경쟁, 미지원 잠금, 복구 후 오류 해제를 포함한다.

### 실제 브라우저

Windows Codex IAB Chromium, localhost 하위 경로에서 [DOM·조작 기록](day7-browser-checks.json).

- 1회 지급, Escape 취소(무차감·포커스 복귀), 1회 3000→2700, 10회 3000→0/결과10개, 같은 결과/요청ID의 새로고침 복원.
- 용량 실패 시 잔액3000/결과0, 같은 요청 재시도 성공. 손상 데이터의 명시적 복구와 미래버전 거부.
- 실제 두 탭: 3000→2700→2400/서로 다른 receipt2개. 확정 중 Escape 잠금. 잠금 지연 중 뒤로 가기로 화면 이탈 → 다시 열어 확정 결과 복원.
- Cry Baby/MASTER/전체 곡 선택의 가챠 왕복 보존, 상세 표의 희귀도/카드 확률과 비용 안내, 실제 곡 일반 game-over 및 연습 진입/일시정지/재개/복귀.
- 기존 기록 저장은 **격리된 실제 앱 + 6초 1노트 시험 채보**로 정상 종료 및 새로고침 후 F 기록 복원을 확인. 실제 곡 완주/성공 점수 검증으로 과장하지 않는다. 운영 채보 파일은 변경하지 않는다.
- 360×800,390×844,844×390,1366×768에서 10개 결과 스크롤/닫기 접근/가로 넘침 없음. 최초 측정은 모달 scale 등장 중 CSS44px이 화면43.34px로 관측된 값도 기록했다. 효과 OFF에서 transform 애니메이션 없음, CSS200% 확대에서 닫기88px/화면내 하단694.4px, 모달24~744px, 가로 넘침 없음.
- 결과 전환에서 포커스가 body로 빠지던 문제를 발견하고 모달 내부 포커스/결과 확인 버튼으로 복구하도록 수정했다. 복구 후 남던 이전 저장 오류도 공통 store 구독으로 해제했다.

`gacha-flow.html`은 별도 `rhythm-next-day7-flow-fixture` 키와 실제 Web Locks를 사용한다. `gacha-play.html`은 index markup과 실제 app 모듈을 사용하되 **모든 localStorage 키에 `rhythm-next-day7-play-fixture:` prefix**를 붙인다. `?fixture=short`에서만 fetch 어댑터가 시험 채보를 반환한다. 기본 fixture는 실제 곡/채보를 사용한다. 운영 저장 데이터를 읽거나 초기화하지 않았다.

### 미실행 및 한계

실기기 모바일/Safari/Firefox, 청음 기반 음악 동기화, FPS/입력 지연 측정은 미실행. CSS200%는 브라우저 자체 zoom 검증과 다르다. 캡처 API가 `Unable to capture screenshot`으로 실패했으므로 DAY 7 스크린샷과 이미지 기반 외관 검증은 없다. 새 효과·렌더 루프 작업은 없으며 저장 처리 비용은 누적 receipt 크기에 따라 늘어난다. 데이터가 용량을 초과하면 쓰기를 차단하고 기록을 보존한다.

## DAY 8 인터페이스

`createDrawService({store,...})`의 `prepare(bannerId,1|10)`이 고정 요청을 만들며 `confirm()`이 위 저장 트랜잭션을 호출한다. `{ok:true,receipt,changed}`의 **확정 receipt만** 연출 입력으로 사용한다. `changed:false`도 이미 확정된 동일 결과이며 재차감/새 RNG를 호출해서는 안 된다. `restore().receipt` 또는 `store.snapshot.wallet.receipts.at(-1)`로 복원한다. 외부 UI가 받은 snapshot과 결과는 복제본이다.

DAY 8 연출 실패/건너뛰기/이탈은 receipt를 지우거나 재실행할 이유가 아니다. 원본 요청 ID를 결과 식별자로 쓰고, 연출 상태를 잔액/확정 결과와 혼동하지 않는다. 반복 QA는 fixture 키/메모리 어댑터를 사용하고 운영 1회 지급 규칙을 바꾸지 않는다.

## 배포 계획과 확인 위치

기존 main/GitHub Pages에 관련 DAY 5~7 변경을 한 번 커밋·푸시한다. 공개 주소는 고정된 `https://haepul.github.io/rythem_game/next-stage/?v=20261022-track`을 유지한다. 이 문서는 커밋 전 로컬 검증 보고이며, 실제 SHA/Actions 결과/공개 파일 해시·격리 브라우저 검증은 배포 후 최종 응답 및 별도 release evidence에 기록한다. 원본 및 다른 게임 버전은 수정하지 않는다.
