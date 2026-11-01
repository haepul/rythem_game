# DAY 5 — 상세 안내 선행 보완 / 무료 재화와 저장 기반

2026-10-30 KST. **로컬 구현·검증 완료. commit / push / 배포하지 않음.**
11월 1일 점검 이후의 중간 배포는 오늘 실행하거나 예약하지 않았다.

## 실제 시작 상태

- Git root: `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`.
- origin: `https://github.com/haepul/rythem_game.git`, `main`.
- 실제 HEAD: `3d1180b53bd9bea4d91d127ba8ab29411663b1d0`. 시작 status는 깨끗했다.
- 저장소/상위 경로에 적용되는 AGENTS.md 없음. Desktop/game은 Git 저장소가 아니며 가챠/지갑 후보 파일 검색에서도 새 구현을 찾지 못했다. 그곳은 수정하지 않았다.
- DAY 1~3 문서, app/index/style/ui-system/gacha, 배너 선택, 메뉴 라우터, 기존 테스트와 저장 호출을 조사했다. 상세 모달과 지갑은 없었다. 설계 문서의 초기 무료 잔액/지급 정책은 미정이었다.
- 기존 저장은 `rhythm-next-settings`, `rhythm-next-favorites`, `rhythm-next-records`. 일반 `save()`는 성공 반환이 없어 이번 모듈에서 재사용하지 않는다. 새 키 충돌 검색에서 기존 사용 없음.
- 기존 사이트·유리 버전·web-next 복사본, 엔진/판정/차트/노트/오디오/점수/LIFE/결과 저장은 수정하지 않았다.

## 선행 DAY 4 — 완료

`details.mjs`가 selectedBannerId로 제목·설명·희귀도 준비 안내·제공 확률 미설정·추첨 규칙 준비 상태를 조회한다. 수치 확률, 실제 캐릭터, 희귀도 배정, 가짜 추첨 버튼은 없다.

공통 `.ui-modal`을 쓰는 native dialog: 선택한 배너 제목으로 레이블, 44px 닫기 버튼, native 포커스 가둠, Escape/닫기 후 opener 복귀. 화면 이탈/해제 시 닫고 이전 opener를 버린다. 설정/도움말 진입도 가챠 모달을 정리한다. 헤더 색/테두리/배경은 기존 토큰을 쓰고 backdrop blur는 없다.

**지갑 UI 구현 전** 실제 앱에서 라일락/피치 상세, Escape 포커스 복귀, 닫기→설정, 열린 모달 상태에서 히스토리로 library 복귀(open dialog 0), 재진입 시 피치 선택 보존을 확인했다. 이후 재화 UI를 연결했다.

## DAY 5 — 완료

| 파일 | 변경 |
|---|---|
| `gacha/details.mjs` | 상세 데이터 조회 및 native modal 수명 |
| `gacha/wallet-config.mjs` | 독립 테스트 정책, 저장 키, 미설정 비용 |
| `gacha/wallet.mjs` | 순수 검증/파싱/지급/실행 가능 여부 |
| `gacha/wallet-storage.mjs` | 주입 저장 어댑터, 잠금, 1회 지급, 오류/복구, 탭 간 갱신 |
| `gacha/wallet-view.mjs` | 잔액·지급·오류·복구 확인 UI, aria-live, busy |
| `gacha/view.mjs` | 기존 선택 상태에 상세/지갑 연결, 이탈 시 정리 |
| `gacha.css` | 가챠 한정 반응형 패널·모달·44px 버튼 |
| `app.mjs` | 가챠 import 버전 및 설정/도움말 진입 시 모달 정리만 |
| `index.html` | app/gacha CSS 캐시 식별자만 갱신 |
| `tests/test_gacha_wallet.mjs` | 37개 순수/저장/경쟁/오류 테스트 |
| `tests/gacha-wallet.html` | 운영 키와 분리한 브라우저 오류·다중 탭 fixture |
| `README.md`, `docs/gacha/architecture.md`, 이 문서 및 캡처 | 현재 완료 범위와 계약 |

### 정책과 저장 스키마

프로젝트용 임시 테스트 규칙이며 **프세카 공식 규칙이 아니다**.
초기 잔액 0, `테스트 재화 받기`로 3,000, grant ID `test-crystals-v1`은 저장 데이터당 한 번. 날짜/광고/결제/유료 재화/게임 보상 연동 없음. 추첨 비용은 `null`(미설정), 실제 추첨·차감·결과 생성 없음.

키: `rhythm-next-gacha-wallet-v1`

```json
{"schemaVersion":1,"balance":3000,"claimedGrantIds":["test-crystals-v1"]}
```

잔액은 0 이상의 안전한 정수. grant IDs는 중복 없는 비어 있지 않은 문자열 배열. 필드/버전/타입을 엄격히 검사한다. 읽기만으로 저장하거나 지급하지 않는다. 지급 여부와 잔액을 하나의 JSON에 쓰고, **setItem 성공 후에만** 메모리·UI를 확정한다. 일반 app 저장 함수는 사용하지 않는다.

`getItem/setItem`은 동기 Web Storage 계약을 따르는 주입 어댑터다. SecurityError, 용량 초과/쓰기 실패, JSON 오류, 잘못된 타입/음수/소수/안전 정수 초과/중복 ID/알 수 없는 버전은 오류로 처리한다. 손상 시 잔액을 0이라고 가장하지 않고 `확인 불가`로 표시하며 원본을 보존한다. 저장 실패 직후 대기 중인 focus/storage 갱신이 오류를 지우지 않도록 보완했다.

복구는 `가챠 데이터만 초기화…` → 별도 확인창 → 명시적 확인이 필요하다. 재화와 지급 내역을 초기 상태로 저장하며 다른 키를 삭제하지 않는다. 초기화한 새 데이터는 다시 1회 지급받을 수 있다는 점을 확인창에 명시했다. 미래 버전의 같은 객체에 포함된 가챠 정보도 지워질 수 있음을 안내한다. 확인 전후 원본 문자열이 달라졌으면 복구를 거부하여 다른 탭의 최신 기록을 덮지 않는다. 읽기 불가 상태에서는 복구도 쓰지 않는다.

### 다중 탭 / 안전한 제한

`navigator.locks.request('rhythm-next-gacha-wallet-v1:transaction', {mode:'exclusive'}, ...)` 안에서 **다시 읽기 → 검증 → 중복 확인 → 단일 객체 쓰기**를 수행한다. UI의 빠른 연속 요청은 동기 busy 플래그로 막는다. 다른 탭의 storage 이벤트, focus, 메뉴 재진입 시 갱신하며 구독/이벤트는 destroy에서 해제한다.

Web Locks는 동일 origin의 협력하는 탭/worker 간 잠금을 제공하며 secure context가 필요하다. `storage` 이벤트는 원래 저장한 창이 아닌 다른 창에 전달된다. [MDN Web Locks](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API), [MDN storage event](https://developer.mozilla.org/en-US/docs/Web/API/Window/storage_event).

잠금 미지원이면 조회만 하고 지급·복구 쓰기를 제한하며 이유를 표시한다. localStorage만으로 CAS/트랜잭션을 흉내 내지 않는다. Pages 경로가 달라도 동일 origin이면 저장소를 공유하므로 키/잠금 이름을 통일해야 한다. 다른 origin·브라우저 프로필·다른 기기는 독립 데이터다. 개발자 도구로 직접 수정하거나 잠금을 무시하는 외부 코드는 방어하지 못한다. 서버 계정/영구 저장/부정행위 방지가 아닌 무료 로컬 시뮬레이션이다. 브라우저 데이터 삭제·명시적 초기화 후 재지급은 새 데이터로 취급한다.

### 실행 가능 여부와 DAY 7 계약

`drawEligibility()`는 busy / storage-unavailable / cost-unset / invalid-cost / insufficient-balance / ready를 구분한다. 비용은 양의 안전한 정수여야 한다. 비용과 동일한 잔액은 ready, 비용-1은 부족이다. 운영 비용은 미설정이며 이 검사만으로 추첨 기능을 만들지 않았다.

DAY 7에는 **차감과 확정 결과, 중복 방지 operation ID를 동일 트랜잭션의 단일 스냅샷으로 확정**해야 한다. 지금 키의 잔액부터 빼고 별도 결과 키에 쓰는 순서는 금지한다. 잠금 안에서 최신 잔액/규칙 버전 검증 → 결과/receipt 포함 새 스냅샷 → 한 번의 저장 → 메모리 확정 → 연출 순서다. 실패 시 이전 스냅샷을 유지하고 재시도 ID로 중복 차감을 방지한다. 필요한 스키마 변경은 명시적 버전 마이그레이션과 중단/재시도 시험을 수반해야 한다. 현재 엄격한 v1 리더는 새 형식을 자동으로 덮지 않는다. 오늘은 이 계약만 기록했다.

## 실행한 자동 검사

저장소 루트에서 실행:

```powershell
git diff --check
node --check next-stage/app.mjs
node --check next-stage/gacha/view.mjs
Get-ChildItem next-stage/gacha/*.mjs | ForEach-Object { node --check $_.FullName }
node --test tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs tests/test_gacha_wallet.mjs
node tests/test_judgment_3d.mjs
node --test tests/test_ap_combo.mjs tests/test_beat_guides.mjs tests/test_judgment_text.mjs
```

- 구문/공백 통과. Git의 LF→CRLF 안내는 whitespace 오류가 아니다.
- 배너9 + 메뉴7 + 지갑/상세37 = **53개 통과**.
- AP13 + 박자 가이드17 + 판정 텍스트18 = **48개 통과**. 합계 **101개**.
- 판정선 직접 실행 PASS: geometry/layers/static body/OFF/80ms reflection/60·120Hz hot path/fixed pools/TAP·FLICK·HOLD·SLIDE engine scores. 이는 실제 기기 FPS 측정이 아니다.
- 지갑 검증: 지급·중복·20회 경쟁·새 인스턴스 복원·저장 전 UI 미확정·저장 실패 후 재시도·다중 저장소 인스턴스 잠금·손상/미래 버전 원본 보존·복구 경합·기존 3개 키 보존·정수/비용 경계·잠금 미지원·구독/해제·대기 중 refresh.

## 실제 브라우저 검증

Windows Codex 인앱 브라우저, 로컬 `http://127.0.0.1:8784/next-stage/#/gacha` 및 `/tests/gacha-wallet.html`. 다른 로컬 포트/공개 사이트 데이터는 건드리지 않았다. fixture는 `rhythm-next-test-wallet-day5`만 사용하며 운영 지갑을 손상시키지 않는다.

| 검증 | 실제 결과 |
|---|---|
| 앱 지급 / 새로고침 | 0→3,000, 지급 완료 버튼 비활성, 새로고침 후3,000·완료 복원 |
| 빠른 요청 | fixture20회: granted1, busy19, 잔액3,000 |
| 실제 두 탭 경쟁 | 같은 race ID, 한 탭 granted / 다른 탭 duplicate, 양쪽3,000 |
| 저장 공간 오류 주입 | 잔액0 유지, 용량 부족 문구, 지급 재시도 가능 |
| 손상 데이터 복구 | 확인 불가/오류 → 명시적 확인 → 잔액0, 완료 안내 |
| 미래 버전 | 미지원 안내와 원본 보호, 자동 지급 안 함 |
| 읽기 실패 / 잠금 미지원 | 각각 명확한 문구, 미지원 시 지급 비활성 |
| 선택 보존 | Cry Baby / MASTER / 전체 곡 선택 → 가챠 → 복귀 후 동일. 피치 배너도 왕복 유지 |
| 모달 | Escape/닫기/포커스 복귀, history 이탈 정리, 설정 후 상세 정상, 동시 열린 dialog1 |
| 360×800 | 문서 가로 폭345(스크롤바 제외), 재화 패널316.8px, 지급 버튼44px; 가로 넘침 없음 |
| 390×844 | 상세 모달 폭 약337px, 화면 안 배치, 내부 내용/닫기 표시 |
| 844×390 | 모달560×약306px, 화면 안 배치; 페이지 세로 스크롤 가능 |
| 1366×768 | 지갑 우측 배치, 전체 화면 캡처 |
| CSS200% | fixture zoom2, 가로 넘침 없음, 조작 요소 유지 |
| 실제 효과OFF / reduced 모사 | 실제 앱 효과OFF와 fixture reduced 상태에서 modal animation-name:none, backdrop-filter:none |
| 오류 로그 | 확인 시 앱/fixture console error0 |

네이티브 줌 단축키는 이 브라우저에서 200% 줌을 적용하지 않았으므로 통과로 세지 않았다. 기존 +/- 게임 단축키로 바뀐 테스트 origin의 볼륨은80으로 복원했고, 효과 설정도 ON으로 돌렸다. 초기 back 시험은 히스토리가 없는 첫 페이지에서 about:blank로 이동했으므로 library→gacha 이력을 만든 뒤 재검증했다. `전체 곡` 버튼 이름은 곡 필터와 중복되어 data-length로 좁혀 검증했다. 이는 제품 실행 오류와 구분한다.

## 실제 캡처

- [데스크톱 전체 화면](day5-captures/wallet-desktop.jpg)
- [360px 지갑](day5-captures/wallet-360.jpg)
- [390px 상세 모달](day5-captures/details-390.jpg)
- [844px 가로 모달](day5-captures/details-844.jpg)
- [효과 OFF 모달](day5-captures/details-effects-off.jpg)
- [저장 실패 안내](day5-captures/wallet-storage-error.jpg)
- [CSS 200% 확대](day5-captures/wallet-css-200.jpg)

## 성능 및 미검증 범위

재화 DOM/저장은 메뉴 이벤트·버튼·storage/focus 시에만 갱신한다. 새 RAF·캔버스·텍스처·파티클·blur는 없다. 순수 로직/한 번의 작은 JSON 저장과 기존 DOM 재사용으로 구성했다. 실제 FPS, 입력 지연, 메모리/CPU 수치는 측정하지 않았으며 성능 향상 수치도 주장하지 않는다.

실제 Android/iOS 터치 하드웨어, Safari/Firefox, 브라우저 자체200% 줌, OS reduced-motion 설정 전환, 별도 DPR2 기기는 미검증이다. 위 크기는 브라우저 viewport 검사다. 실제 디스크 고갈 대신 QuotaExceededError 주입으로 오류 처리를 확인했다. 공개 Pages 배포/접속 재검증은 수행하지 않았다.

선행 상세 안내와 오늘의 무료 재화 저장 기반은 모두 로컬 완료. 확률·비용·추첨·차감·결과 생성은 의도적으로 미구현이다.
