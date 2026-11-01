# DAY 6 — 임시 카드 데이터와 확률 엔진

2026-10-31 KST. **로컬 구현·검증 완료. commit / push / 배포하지 않음.**
2026-11-01 DAY 7 실행 흐름 통합 및 중간 배포는 오늘 수행하거나 예약하지 않았다.

## 시작 상태와 선행 검증

- 실제 root: `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`.
- origin `https://github.com/haepul/rythem_game.git`, branch `main`, HEAD `f8b4ecd32e0965b095032f57f350890bbd19781a`.
- 저장소 전체 및 상위 경로에서 적용 AGENTS.md 없음. 기존 DAY 5 수정/미추적 파일을 보존했다. 중복 카드/추첨 모듈은 없었다.
- index/app/style/ui-system/gacha CSS, gacha 전체 모듈, 메뉴 라우터, architecture/day5 및 기존 테스트를 확인했다.
- 상세 안내·지갑·배너·메뉴 선행 테스트 **53개 통과 후** DAY 6을 구현했다. 기존 상세는 확률 미설정 안내였다.
- 판정/점수/LIFE/채보/오디오/리본/노트/결과 저장, 다른 게임 버전은 수정하지 않았다. 지갑 스키마와 지급 정책도 유지했다.

## 프로젝트 테스트 규칙 v1

**프세카 공식 확률이 아니다.** 결제·광고·현금성 보상·실제 캐릭터 정보가 없는 로컬 시험 규칙이다.

| 희귀도 | 가중치 basis points | 희귀도 확률 | 카드 ID | 카드 각각의 확률 |
|---|---:|---:|---|---:|
| R2 | 8000 | 80% | test-card-001 / test-card-002 | 40% |
| R3 | 1500 | 15% | test-card-003 / test-card-004 | 7.5% |
| R4 | 500 | 5% | test-card-005 / test-card-006 | 2.5% |

- 합계 10000. 희귀도 내 카드 균등. 10회는 독립 추첨 10번이며 **보장 없음** (`guarantee:'none'`).
- 카드 데이터는 `id/rarity/placeholderArtKey`뿐이다. placeholderArtKey는 향후 교체할 표시용 토큰이며 카드 ID나 파일 경로로 사용하지 않는다. 오늘 카드 이미지 렌더링은 추가하지 않았다.
- `demo-mint`, `demo-lilac`, `demo-peach` 모두 `project-test-v1`을 참조한다. 같은 풀을 공유하는 배너 목록도 bindings에서 계산한다.
- 비용은 기존 `DRAW_COST=null` 그대로다. 실제 실행 버튼·차감·획득 저장·연출·교환은 없다.

## 엔진과 안내의 공유 계약

`cards.mjs` → `draw-config.mjs` → 순수 `draw-engine.mjs` 및 `details.mjs`.

```js
drawCards(config, 1 /* 또는 10 */, {cards: CARDS, rng})
// [{cardId, rarity, configVersion, schemaVersion}, ...]
```

`rng`는 주입 가능한 함수이며 생략 시 Math.random을 사용한다. 동일 설정과 RNG 시퀀스에서는 동일 결과다. DOM/localStorage/지갑/오디오에 의존하지 않고 입력 객체를 변경하지 않는다. 반환 배열은 메모리에만 존재하며 실제 보유 카드가 아니다.

1. count, RNG 타입, 설정/카탈로그를 먼저 검증한다. 잘못된 설정은 RNG도 호출하지 않는다.
2. 호출자 RNG가 도중 설정을 바꾸더라도 배치가 변하지 않게 필요한 설정/ID를 복사한다.
3. RNG 결과는 숫자이며 유한한 `[0,1)`만 허용한다. 희귀도용 1회, 해당 희귀도 내 카드용 1회를 독립적으로 사용한다.
4. 누적 구간은 `[시작,끝)`. `roll < cumulativeBps / 10000`으로 경계를 비교한다. 0 가중치를 선택하지 않고, 마지막 항목으로 보내는 fallback은 없다.
5. 설정 오류/늦은 RNG 오류는 예외로 실패한다. 중간 결과를 성공으로 반환하지 않는다. 지갑 변경도 없다.

검증은 엄격한 schemaVersion 1, 비어 있지 않은 version, 정확한 필드 구성, 지원 희귀도, 정수 가중치/합계, 빈 목록, 중복 ID/참조/희귀도, 누락 카드, 희귀도 불일치, 보장 `none`만 지원함을 검사한다. 숨은 보장/천장 등 추가 규칙 필드도 거부한다. 양수 가중치의 빈 풀은 오류이며 0 가중치의 빈 풀은 유효하다.

`drawProbabilities()`는 엔진과 같은 `validateDrawConfig()`를 사용한다. 카드 확률은 `numeratorBps / denominator`로 반환하고 표시할 때만 퍼센트로 변환한다. 표시 문자열을 추첨 계산에 재사용하지 않는다. 나누어떨어지지 않는 미래 시험 비율은 소수 4자리 근사임을 표시한다.

선택 배너 → bindings → 설정 → 동일 검증 → 희귀도/카드별 표. UI에 확률 숫자를 별도로 하드코딩하지 않았다. 설정이 없으면 미설정, 잘못되면 설정 오류와 빈 표 대신 오류 문구를 표시한다. 비용 미설정은 확률 준비와 별개로 명시한다.

## 수정 파일

| 파일 | 작업 |
|---|---|
| `gacha/cards.mjs` | 안정적인 임시 카드 6개와 표시 키 |
| `gacha/draw-config.mjs` | 테스트 규칙/배너 매핑/검증/표시용 확률 조회 |
| `gacha/draw-engine.mjs` | RNG 주입, 1·10회 순수 추첨 |
| `gacha/details.mjs` | 기존 상세 확장, 공유 확률 표, 키보드 스크롤/Tab 순환 |
| `gacha/view.mjs` | 선택된 배너 상세 연결, 시험용 detailOptions 주입 |
| `gacha/wallet-view.mjs` | 공통 details import 캐시 식별자만 변경, 지갑 동작 유지 |
| `gacha.css` | 가챠 표/스크롤 영역/고정 닫기 버튼/확대 높이 제한 |
| `app.mjs`, `index.html` | 오늘 변경은 가챠 모듈/CSS 캐시 식별자만; 선행 DAY 5 변경 보존 |
| `tests/test_gacha_draw.mjs` | 신규 44개 검증 |
| `tests/test_gacha_wallet.mjs` | 기존 미설정 상세 시험에 빈 bindings 명시; 지갑 시험 유지 |
| `tests/gacha-draw.html` | 메모리 지갑만 쓰는 미설정/오류/긴 ID/확대 fixture |
| `docs/gacha/day6*`, `architecture.md`, `README.md` | 계약과 검증 기록 |

## 자동 검증

저장소 루트에서 실제 실행:

```powershell
git diff --check
node --check next-stage/app.mjs
Get-ChildItem next-stage/gacha/*.mjs | ForEach-Object { node --check $_.FullName }
node --test tests/test_gacha_draw.mjs tests/test_gacha_wallet.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs
node tests/test_judgment_3d.mjs
```

- 구문·공백 검사 통과. 추첨44 + 지갑/상세37 + 배너9 + 메뉴7 = **97개 통과**.
- 판정선 테스트 PASS: 기하/레이어/효과 OFF/60·120Hz hot path/고정 풀/실제 Engine 점수. 실제 기기 FPS 검사라는 의미는 아니다.
- RNG 0, .8/.95/.5 경계와 정확한 직전 IEEE754 값, 1 직전, 잘못된 RNG의 두 단계, 0 가중치, 잘못된 설정/카탈로그, count, 입력 불변, RNG 중 설정 변경, 19번째 RNG 실패를 검증했다.
- 10회 전부 R2도 정상이며 보장을 추가하지 않는다. 모든 배너의 표와 설정이 일치하고, 시험 가중치 변경 시 안내와 엔진이 함께 변경됨을 검증했다.
- 고정 seed 123456789의 50,000회 표본 분포를 보조 검증했다. 경계/구간 검증이 정확성의 근거이며 표본만으로 정확성을 주장하지 않는다. 결과 수치는 `day6-test-results.txt`에 있다.
- 기존 지갑에 3,000 지급한 뒤 순수 추첨 성공/실패를 호출해 잔액·저장 문자열·메모리 snapshot 불변을 확인했다.

## 브라우저 검증 및 발견한 문제

Windows Codex 인앱 브라우저, 로컬 `/next-stage/?v=20261031-day6-verified#/gacha` 및 `/tests/gacha-draw.html`. [DOM·조작 기록](day6-browser-checks.json).

- 실제 앱에서 세 배너 각각 제목과 희귀도/카드별 확률 9행 확인. `:modal`과 접근성 트리로 모달 배경 차단 확인.
- Escape/닫기 후 상세 버튼 포커스 복귀. 닫기에서 Tab을 누르면 스크롤 가능한 내용 영역으로 이동하고 Shift+Tab으로 닫기로 복귀. 화면 이탈(history back) 시 열린 모달 0, 재진입 후 선택 배너 보존, 설정 모달 왕복 후 열린 dialog 1.
- Cry Baby/MASTER/전체 곡 선택 후 가챠 왕복해 같은 선택 유지.
- 360×800, 390×844, 844×390, 1366×768에서 문서/내용 가로 넘침 없음, 모달 및 닫기 버튼 화면 안, 닫기 높이 44px.
- 긴 카드 ID와 CSS 200% 확대에서 줄바꿈/키보드 스크롤 확인. 최초에는 높이 88dvh가 2배 확대되어 닫기 버튼이 화면 밖으로 나갔다. `max-height:min(88dvh,calc(100% - 24px))`로 수정했다. 수정 후 1366×768에서 모달 y=24~744, 닫기 하단694.4/높이88px, 가로 넘침 없음.
- 효과 OFF/reduced-motion 모사 상태: animation none, backdrop-filter none. 기존 토큰과 최소44px 조작 영역 유지. 새 반복 애니메이션/blur 없음.
- 미설정 및 지원하지 않는 보장 fixture는 수치 표 없이 각각 올바른 안내를 표시했다. 앱/fixture 확인 시 console error0.

**미실행/한계:** 스크린샷 API가 `Unable to capture screenshot`으로 실패하여 이번 캡처는 없다. 따라서 화면 이미지 기반 외관 검증 완료라고 주장하지 않는다. DOM 치수/접근성/실제 조작으로 검증했다. Ctrl+plus 4회도 viewport/DPR이 변하지 않아 브라우저 자체200% 확대는 미검증이며 CSS200% 결과와 구분한다. 실제 휴대폰 터치, Safari/Firefox, OS reduced-motion 설정 전환, FPS/입력 지연 측정은 하지 않았다. GitHub Pages 배포 검증도 하지 않았다. 상대 ES module 경로로 `/next-stage/` 하위 경로에서 실행했다.

## DAY 7 연결 계약 — 아직 구현하지 않음

1. 지금 wallet v1은 `schemaVersion/balance/claimedGrantIds` 이외 필드를 거부한다. 오늘 결과를 wallet에 넣거나 별도 획득 저장 키를 쓰지 않았다. DAY 7에는 비용 정책을 먼저 결정하고, 잔액·확정 결과·요청 receipt를 함께 담을 새 스키마와 명시적인 v1 마이그레이션을 설계해야 한다.
2. 동일 origin 공통 Web Lock 안에서 최신 저장 읽기 → 버전/설정/비용 검증 → requestId 중복 확인 → 결과 준비 → **재화 차감+결과+receipt를 하나의 저장 스냅샷으로 쓰기** → 성공 후 UI/연출 확정. 잔액부터 차감하고 별도 결과 저장을 하는 방식은 금지한다. Web Locks 미지원은 기존처럼 안전하게 쓰기를 제한한다.
3. requestId는 사용자 실행 의도당 한 번만 만들고 재시도에 재사용한다. 배너 ID/설정 버전/count/비용을 요청 내용과 결합한다. 동일 ID·동일 내용의 완료 요청은 저장된 receipt를 반환하며 재추첨·재차감하지 않는다. 같은 ID에 다른 내용은 오류다.
4. 쓰기/용량 오류 시 기존 저장과 잔액을 보존한다. 확정 전 결과를 획득 성공으로 보여주지 않는다. 저장 성공 후 연출 중단/새로고침은 receipt로 복원한다. 저장 전 프로세스 종료에는 확정 receipt가 없다는 점을 구분하고, 미확정 RNG 결과 재시도 정책도 DAY 7에서 명시해야 한다.
5. 마이그레이션 실패, 미래 버전, 이전 탭의 v1 작성기와 충돌, 두 탭 동시 요청, 저장 성공 직후 UI 실패, receipt 보존/한도/복구를 테스트한다. 손상/미지원 데이터를 자동 초기화하지 않고 기록·설정 키는 건드리지 않는다.
6. 반복 QA는 `tests/gacha-draw.html`의 메모리 지갑 또는 별도 테스트 키/저장 어댑터로 한다. 운영 1회 지급 정책을 바꾸거나 운영 잔액을 자동 충전하지 않는다. DAY 7 통합 시험도 시험 전용 저장에서 필요한 잔액/실패를 주입한다.

현재 완료 범위는 **카드 풀·순수 추첨·공유 확률 안내**다. 실제 사용자 추첨 흐름과 차감/결과 저장 및 중간 배포는 DAY 7 과제다.
