# DAY 14 최종 로컬 마감 기록

2026-11-10 KST. **부분 마감: 로컬 구현·문서·실행한 검사는 완료했으나 필수 호환성 검증이 남아 전체 출시 완료는 아니다.** 커밋/푸시/배포하지 않았다.

## 현재 상태와 보존 범위

실제 root `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`, main HEAD `77451317d7d3f7a68a36f54d8de0c932769465cb`, origin `https://github.com/haepul/rythem_game.git`, 단일 worktree. status/log/worktree/file inventory를 확인했다. 적용 AGENTS.md 없음. DAY8~13의 기존 미커밋 파일을 보존했으며 reset/clean/타 worktree 복사는 하지 않았다.

실제 index/app/style/ui-system/gacha CSS와 가챠 저장·추첨·표현·결과·보관함·교환·획득순서·보상 모듈, DAY10~12 문서 및 기존 테스트를 검토했다. DAY13 문서는 없었으므로 실제 남아 있는 로그와 이번 재검증만으로 작성했다. 과거 문서의 브라우저 결과는 이번 실행 결과와 구분했다.

| 기능 | 상태 | 근거 |
|---|---|---|
| 배너/상세/확률·비용 안내 | 구현·검증 | 선택 라일락과 모달 제목 일치, 80/15/5 및40/7.5/2.5%, 비용300/3000 |
| 무료 지급·원자적1/10회 추첨·중복방지 | 구현·검증 | 자동 테스트, 실제 앱10회/격리fixture1회, 두 탭 잔액 갱신 |
| 진입/희귀도 공개/skip/복원 | 구현·검증 | 실제 Next/Space/Escape, 오류·motion fixture10검사 |
| 결과/역사적NEW/재조회 | 구현·검증 | 교환 후 reload해도 동일 카드순서/NEW |
| 보관함/필터/정렬/획득기록 | 구현·검증 |11장5종, R4 filter/disclosure, 빈 필터 안내 |
| 스티커/보너스/교환 | 구현·검증 | draw10→12스티커, 교환1→2스티커/총11장 |
| 실제 캐릭터 표시 레지스트리/이미지 | 미구현(의도된 제외) | 연결 계약만 작성 |
| 실제 브라우저200%/Android/iOS/스크린리더 | 미검증 | 아래 제한 참고 |

실제 캐릭터·공식자산·결제·광고·현금성 보상은 추가하지 않았다. 판정/점수/LIFE/채보/오디오/노트 렌더링 규칙 및 다른 버전 폴더는 수정하지 않았다.

## 결함 수정과 이번 변경

DAY13에서 재현한 세 결함(손상 저장 후 확인 모달 탈출 불가, 확인 갱신 시 포커스 소실, 보관함 갱신 시 펼침 소실)은 각각 `draw-view.mjs`, `inventory-view.mjs`의 최소 DOM/종료 처리 변경으로 해결했다. DAY14에서 같은 결함과 잔액 갱신/연타까지 **9/9** 재검증했다. 저장 계층/확률/비용은 변경하지 않았다. 상세 재현은 [day13.md](day13.md).

이번 이어서 작업의 추가 변경:

- `tests/gacha-play.html`: `isolation=day14` 저장 prefix 추가. 운영 키나 이전 fixture를 초기화하지 않고 동일 production 앱 모듈로 검사한다.
- `tests/test_gacha_integration.mjs`: 250건 이력을 보존하는 quota 실패→동일 요청 재시도→changed:false 회귀 테스트 추가.
- `docs/gacha/day13.md`, `day14.md`, `character-integration.md`: 근거·한계·후속 계약 문서.
- `day14-tests.txt`, `day14-game-tests.txt`, `day14-evidence/`: 실제 실행 로그와 캡처.

가챠 카드·패널의 기존 토큰/형태를 유지했다. 펼침 전에는 5종 보관함을 읽을 수 있었고 이력은 필요할 때만 펼치므로, 검증 없이 카드 밀도를 다시 바꾸지 않았다. CSS 시각 변경은 추가하지 않았다. 기존 가챠 모듈/진입 캐시 query `20261108-day13`과 상대 경로 계약을 유지했다.

## 저장·복구 증거

- 확정 receipt만 연출 입력. 재조회/복원/changed:false는 추가 RNG·차감·쓰기 없음(자동/fixture 검사).
- v1/v2→v3 마이그레이션, 거래 ID 충돌, 동일 요청 재시도, 동시 draw/exchange, 미래 버전·손상 JSON·잠금 미지원은 기존 테스트에서 검증한다.
- schema3 단일 스냅샷은 balance/claimedGrantIds/receipts/exchanges/transactions를 보존한다. 교환은 별도 거래이며 draw 보너스를 주지 않는다.
- 250개 v2 receipt를 가진 fixture(잔액25000)에서 quota 오류를 주입: 원본 저장 문자열·250개 기록·잔액 불변. 같은 요청 재시도 후 원본250건 유지, receipt251건/총260장/잔액22000, 저장1회. 같은 확정 요청 재조회도 저장1회 유지. **실제 디스크 용량을 가득 채운 실험이 아니라 어댑터 오류 주입**이다.
- 실제 두 탭: A10회 확인 중 B1회 확정 → A가2700/300부족으로 갱신하고 확인 비활성화. A취소/reload/마지막결과는 B의1장/2700을 복원한다. 증거 `two-tab.json`, `two-tab-stale-confirm.png`.
- 교환 취소 후 확정: 실제 앱에서 demo-lilac10회, 교환005를 확정하고 보관함11장5종 확인. 두 번째 비용 없음. 기존 과거NEW와 결과순서는 reload 후 동일.
- 손상 데이터 자동 초기화 없음. 복구 테스트는 가챠 전용 키만 바꾸며 게임 기록·설정 키 보존을 검사한다. 운영 데이터는 건드리지 않았다.

## 실제 실행 명령

저장소 root, PowerShell:

```powershell
$t=(Get-ChildItem tests/test_gacha*.mjs).FullName
node --test @t tests/test_menu_navigation.mjs
# 최종226/226, fail0, cancelled0, skipped0
node --test tests/test_gacha_integration.mjs
# 신규 quota 포함6/6
node --test tests/test_ap_combo.mjs tests/test_beat_guides.mjs tests/test_judgment_text.mjs tests/test_ribbon_light.mjs
# 59/59, fail0, skipped0
node tests/test_judgment_3d.mjs
# PASS geometry/layers/static body/OFF/80ms reflection/60-120Hz hot path/fixed pools/engine scores
node --check next-stage/app.mjs
$files=(Get-ChildItem next-stage/gacha/*.mjs).FullName
foreach($f in $files){node --check $f}
#25개 가챠 모듈 통과
node --check tests/gacha-integration.mjs
node --check tests/test_gacha_integration.mjs
git diff --check
# exit0, LF/CRLF 안내만 있음
```

6개 integration 검사는226개 전체에 포함된다. 59개와 judgment3d는 별도다. 반복 실행을 새 테스트 수로 더하지 않았다.

## 브라우저와 접근성

Windows in-app Chromium156, localhost8785. 운영 origin 저장 대신 명시적 `rhythm-next-day14-play-fixture:` prefix 및 기존 전용 fixture key를 사용했다.

실행한 앱 흐름: 곡 선택(Cry Baby MASTER)→일반 플레이 완료→가챠→라일락 배너→상세/확률→지급→1회확인/취소→10회확정→공개 Next→Escape skip→결과→교환선택/취소→다시선택/확정→보관함/R4필터/기록→reload→과거결과→곡 선택. 별도 fixture에서1회 확정/복원도 수행했다.

상세 모달 Tab/Shift+Tab 포커스 순환, Escape닫기, Enter취소, Space공개/교환, 닫기 후 opener복귀를 확인했다. 모달 배경은 native dialog로 차단된다. 실제앱 브라우저 뒤로/앞으로 후에도 가챠 복귀가 동작했다. 조회/교환/추첨 버튼 중 확인한 범위는 위 흐름이며 **모든 오류 상태의 모든 버튼을 수동 전수 검사했다고 주장하지 않는다.**

### 화면 크기

360×800,390×844,844×390,768×1024,1366×768의 실제 크기 iframe에서 보관함·10장 결과를 검사했다. iframe 안의 media query/레이아웃 검사이며 실기기나 네이티브 전체 브라우저 뷰포트 검사와 다르다. 세로 스크롤바 때문에 clientWidth는 각각345/375/829/753/1351이었다. 각 화면의 scrollWidth=clientWidth, 열린 모달 내부에도 가로 넘침 없음. 결과10장 DOM순서 유지, 닫기/복귀 버튼 높이44px. 모바일2열, 데스크톱5열 결과를 캡처 확인했다. 긴 내용은 모달 내부 스크롤이며 아래 동작 버튼은 접근 가능했다. 부모 테스트 페이지가 큰 iframe 때문에 가로 스크롤되는 것은 게임 본문의 넘침으로 계산하지 않았다.

실제 브라우저200% 확대는 **미검증**이다. 이전 시도에서 Windows Chrome의 현재 URL을 도구가 안전하게 식별하지 못해 컴퓨터 조작이 중단되었다. 이번에는 in-app DOM 검증을 복구했지만 native 확대 증거를 확보하지 못했다. CSS zoom은 대체 증거로 사용하지 않았다.

### 중단/모션

`fault-recovery.json`10/10: quota 실패, 같은 요청 재시도, 저장후throw readback, intro/WAAPI오류, motion 시작/intro중/card중 변경, intro/card화면이탈. 해당 입력은 테스트 전용 오류/MediaQueryList 모의이며 실제 OS reduced-motion 변경은 미실행이다. 물리적 탭 숨김/복귀 전수검사도 남아 있다. fixture의 이탈/오래된 callback/취소 테스트와 구분한다.

## 기존 게임 회귀

실제 production 앱 모듈을 사용하는 `gacha-play.html?isolation=day14&fixture=short`. chart fetch만6초/1TAP/120BPM으로 대체한 **짧은 시험 채보**이며 실제 원곡 MASTER 완주가 아니다.

- 가챠 방문 전/후 동일 Cry Baby MASTER·1절 일반 플레이 종료: score0/MISS1/gradeF. `rhythm-next-records`의 곡3기록 유지.
- 카운트다운이 끝난 PLAY에서 일시정지 화면→계속하기→결과 화면 확인. COUNTDOWN에서 pause가 메뉴로 돌아가는 기존 정책은 수정하지 않았다.
- 가챠 왕복/뒤로·앞으로 후 Cry Baby/MASTER/FAVORITES 보존. 새로고침 시 선택곡/필터가 기본값으로 돌아가는 기존 동작은 별도이며 가챠 왕복 보존과 혼동하지 않았다.
- 연습 모드 진입·종료 및 저장 문자열 불변 확인. 연습 모드 별도 pause 조작은 짧은 재생 창을 놓쳐 이번 최종 수동 검사에서는 미검증으로 남긴다.
- 실제 앱 콘솔 error/warn0. `game-storage.txt`에 가챠schema3/교환/게임기록 근거 저장.
- **오디오 청음·싱크 측정, 정밀 타이밍 입력, 실기기 터치는 미실행**이다.

## 성능 판단

DAY13 동일조건 측정은 [day13.md](day13.md)와 원본JSON 참조. 수정전후 p50 8.3→8.3ms, p95 8.6→8.6ms, 최대41.8→58.8ms. 각 약6.7초 단일 표본으로 최대 간격 증가 원인을 특정할 수 없고 성능 개선이라고 주장하지 않는다.20회왕복 warmDOM250→250/listener53→53/timer0/animation0. heap누수/60FPS 보장이 아니다. DAY14는 런타임 렌더링 변경 없이 추가 검증/문서만 수행했으므로 새로운 전후 수치를 꾸미지 않았다. 대량 이력의 실제 모바일 렌더/저장 성능은 후속 검증이다.

## 캡처와 근거

- `day14-evidence/app-results.png`: 실제앱10회 결과/NEW
- `app-inventory.png`: 교환 후 보관함
- `game-pause.png`: 일반 플레이 일시정지
- `inventory-desktop.png`, `results-desktop.png`, `results-mobile.png`: iframe 반응형
- `inventory-sizes.json`, `result-sizes.json`: 5크기 실측
- `regressions.json`: UI9검사
- `fault-recovery.json`: 중단/오류10검사
- `two-tab.json`, `two-tab-stale-confirm.png`: 실제2탭 잔액 변화
- `game-storage.txt`, `final-browser-summary.json`: 앱 흐름과 제한

## 점수 평가 — 주관적, 출시 인증 아님

| 항목 | 점수 | 근거/미검증 감점 |
|---|---:|---|
| UI |25/30|공통패널·라벨·5크기·키보드 확인. native200% 및 전체 오류버튼 전수 미완료|
| 데이터 |24/25|226테스트·두탭·quota250건·원자성·과거NEW. 실제quota환경/장기이력 제한|
| 연출 |17/20|skip·확정receipt·오류fallback·motion모의. 물리적 탭숨김/OS설정 미검증|
| 호환성 |5/10|하위경로/Chromium/iframe 확인. Android/iOS/Safari/Firefox/native확대 미검증|
| 통합 |8/10|일반pause/resume·결과·가챠/교환/보관함왕복. 청음/정밀입력/연습pause 미검증|
| 확장성 |4/5|실제엄격스키마 기반 캐릭터연결 계약. 자산연결은 의도적으로 미구현|
| 합계 |83/100|기능 및 근거 중심의 주관적 로컬 평가. 남은 필수 검증을 통과 처리하지 않음|

## 남은 작업과 배포 전 확인 목록

현재 실행한 검사에서 미해결 중복차감/기록손실/복귀불가 결함은 발견하지 못했다. 다음 항목이 남아 있어 **전체 마감은 부분 완료**다.

1. **P1 검증 차단:** 실제 브라우저200%에서 모달/버튼/스크롤 확인; 조작 도구 URL식별 복구 또는 수동 QA 증거 필요.
2. **P1 검증:** 실제 탭 숨김/복귀, OS reduced-motion 변경, 연습pause/resume 및 모든 오류·복구 버튼 수동 전수.
3. **P2:** Android/iOS 실기기, Safari/Firefox, 스크린리더, 청음/입력지연, 느린기기/긴 이력 저장성능.
4. **P3:** 캐릭터 자산 도입 전에 [character-integration.md](character-integration.md)의 권리/영구ID/표시fallback 계약 검토. 실제 캐릭터 작업은 시작하지 않음.

배포할 때에는 별도 요청을 받은 후: dirty파일과 신규 의존파일 누락 점검 → 전체테스트/구문/diffcheck → 위 필수브라우저 검증 → 기존Pages 경로/캐시쿼리 정합성 → 원격최신 확인/검증된파일만커밋 → force없는push → Actions/공개URL/모듈404/격리공개시험 확인 순서로 진행한다. **오늘은 커밋0/푸시0/배포0, 공개 사이트 변경 없음.**
