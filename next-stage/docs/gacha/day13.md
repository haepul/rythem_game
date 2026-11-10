# DAY 13 통합 검증 및 결함 수정

검사 시작 2026-11-08 KST, DAY14에서 2026-11-10 재검증/기록 정리. HEAD `77451317d7d3f7a68a36f54d8de0c932769465cb`, main, origin `https://github.com/haepul/rythem_game.git`, 단일 worktree. 적용 AGENTS.md는 발견되지 않았다. DAY8~12 미커밋 작업을 보존했다.

## 실제 범위

배너·상세 확률·무료 지급·1/10회 추첨·원자적 저장·연출/skip·결과/NEW·보관함 필터/정렬/이력·스티커/보너스·교환은 구현되어 있다. DAY11/12를 새로 구현하지 않았다. 실제 캐릭터와 결제/광고/현금성 보상은 범위 밖이며 추가하지 않았다. 실기기·청음·스크린리더 검사는 미실행이다.

## 재현 결함과 수정

| 재현 | 영향 | 최소 수정 | 재검증 |
|---|---|---|---|
| 추첨 확인창을 연 뒤 저장 JSON 손상, 취소 | 모달이 복구 버튼을 가려 복귀 불가 | draw-view: busy/확정 receipt는 보호하되 실패한 cancel에서도 닫기 허용, 미확정 intent 보존 | 손상 바이트 불변 + 닫기 통과 |
| 확인 버튼에 포커스 후 store.refresh/다른 탭 잔액 갱신 | DOM 교체로 포커스 상실 | 같은 intent의 확인 DOM 재사용, 텍스트/disabled만 갱신 | 잔액 감소 시 포커스 유지/부족 차단 |
| 보관함 획득 기록을 펼친 뒤 refresh/교환 | disclosure 접힘/키보드 포커스 상실 | inventory-view: 카드 ID별 행 재사용, 변경 이력만 갱신 | 펼침·포커스 유지, 보유10→11 |

증거: `day13-evidence/regressions-before.json`의 3개 실패를 수정했다. 초기 수정 후 6개 검사 통과, 확장된 최종 9개 브라우저 검사 결과는 `day14-evidence/regressions.json`이다. 버튼 연타 시험은 synthetic pointer/click이며 실기기 터치가 아니다.

## 명령 및 결과

```powershell
$t=(Get-ChildItem tests/test_gacha*.mjs).FullName
node --test @t tests/test_menu_navigation.mjs
# 기준 220/220, 신규 integration 5개 포함 후 225/225, 실패/skip 0
node --test tests/test_ap_combo.mjs tests/test_beat_guides.mjs tests/test_judgment_text.mjs tests/test_ribbon_light.mjs
# 59/59, 실패/skip 0
node tests/test_judgment_3d.mjs
# PASS geometry/layers/OFF/reflection/hot path/pools/TAP-FLICK-HOLD-SLIDE engine scores
node --check next-stage/app.mjs
# gacha/*.mjs 및 신규 integration 모듈도 구문 검사
git diff --check
# 통과, 일부 LF/CRLF 안내만 존재
```

통합 테스트는 read 실패 취소, draw/exchange 동시 잠금, 20회 복원 불변, 복구의 다른 저장 키 보존, 20회 중단 시 오래된 callback 무시를 추가했다. `gacha-integration.html/.mjs`는 명시적 fixture key만 사용한다. RNG/쓰기 계수, DOM/timer/listener 계측은 시험 파일에만 있고 앱 진입점에서 로드하지 않는다.

`fault-recovery.json`: 저장 전 quota 실패, 같은 요청 재시도, 저장 후 throw readback, intro/WAAPI 오류, reduced-motion 시작/도중, intro/card 화면 이탈의 10개 검사 통과. 오류 주입은 실제 브라우저에서 실행한 fixture이며 OS 설정/물리적 탭 숨김을 대신 검증했다고 주장하지 않는다.

## 동일 조건 성능 비교

Windows, Intel Core 3 100U, in-app Chromium156, 1280×720, DPR1.25. 각 1회 약6.7초, 기본10장 연출 + 시험 자동 Next80ms. 렌더 간 RAF 간격이며 GPU/입력지연 측정이 아니다.

| 측정 | 수정 전 | 수정 후 |
|---|---:|---:|
| 관찰 길이(ms) |6722.5|6742.5|
| RAF 표본 |756|752|
| 중앙값(ms) |8.3|8.3|
| p95(ms) |8.6|8.6|
| 최대(ms) |41.8|58.8|
| 관찰된 long task |0|0|
| warm-up 후20회 왕복 DOM |250→250|250→250|
| 계측 listener |53→53|53→53|
| 안정화 후 animation/timer |0/0|0/0|

표본이 짧고 최대 간격은 증가했다. 성능 향상/항상60FPS/메모리 누수 없음으로 일반화하지 않는다. 계측 wrapper도 비용이 있고 heap을 측정하지 않았다. 원본 JSON은 `day13-evidence/performance-before.json`, `performance-after.json`에 있다.

## 남은 검증 및 인계

5개 iframe 크기·최종 앱 흐름은 DAY14 증거에 기록한다. 실제 브라우저200% 확대와 실기기, 물리적 탭 숨김, 청음/싱크, 장시간/대량 이력 성능은 미검증이다. 외형 전체 완료로 간주하지 않는다. import/cache query는 `20261108-day13`로 일관되게 맞췄다. 원본 게임/다른 버전 및 판정 규칙은 변경하지 않았다. 커밋·푸시·배포 없음.
