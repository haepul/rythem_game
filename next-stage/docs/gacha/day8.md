# DAY 8 — 저장 완료 결과의 진입 연출

기준일 2026-11-02 KST. 2026-11-03에 미완료 검증·문서를 이어 작성하고 DAY 9와 통합했다. 과거에 실행하지 않은 검사를 DAY 8 당시 통과한 것으로 소급하지 않는다.

## 구현 및 경계

- `intro-sequence.mjs`: DOM/저장/RNG와 독립된 entering → gathering → revealing → finished 시퀀스. 프로젝트 시간은 350/650/450ms, 총 1450ms. 공식 게임 타이밍이 아니다.
- `intro-view.mjs`: 자체 SVG 마름모·원, 재사용 입자 6개(480px 이하에서는 4개). 유한 WAAPI opacity/transform 모션만 사용한다. 소리, 이미지 다운로드, Pixi Application, RAF 루프, BlurFilter 없음.
- `draw-view.mjs`와 `view.mjs`: 성공한 `confirm()`의 확정 receipt 연결. `changed:true`만 연출하고 재시도 `changed:false`, 복원, 마지막 결과 보기는 바로 기존 결과 목록으로 간다.
- 읽기 전용 복제 receipt, 실행 세대와 종료 guard, 타이머/WAAPI 취소, 취소 rejection 흡수. 정상/skip/오류는 같은 결과를 전달한다. 이탈 시 `present:false`로 끝내고 DOM·포커스를 건드리지 않는다.
- 기존 native dialog의 배경 차단/닫기/Escape를 재사용한다. 효과 OFF 및 reduced-motion에서 즉시 결과, 실행 중 설정 변경도 반영. visibilitychange와 pagehide에서 정리한다.
- DAY 9 통합 후 전체 완료 책임은 `card-reveal.mjs`의 `createGachaPresentation()`으로 이동했다. intro 단독 완료는 최종 결과를 직접 표시하지 않고 카드 공개로 연결한다. 전체 skip/오류/OFF는 카드 공개도 생략한다.

## 실제 확인

- DAY 9 시작 전 기존 가챠/메뉴 + intro 테스트 154개 통과. `test_gacha_intro.mjs` 28개는 정상 타임라인, 각 단계 skip, 늦은 콜백, hide/destroy, OFF, 오류 및 실제 서비스 1/10회 후 RNG·쓰기·잔액 불변을 검증한다.
- 격리 `tests/gacha-flow.html`에서 1회 실제 저장 후 Space skip → 같은 요청 ID/카드/잔액을 새로고침으로 복원. 복원 후 writes=0, rolls=0, confirms=0, phases=[]를 관측했다.
- 초기 연출 화면은 [실제 캡처](day8-captures/intro.jpg). 최종 통합 브라우저/반응형/오류 검증은 [DAY 9 보고](day9.md)에 기록했다.
- 숨김 후 정리는 자동 테스트로 검증했다. IAB에서 다른 탭을 만드는 것만으로 실제 document.hidden 이벤트가 발생하지 않아 실제 OS 탭 숨김/복귀는 통과로 주장하지 않는다. 실기기, OS 모션 설정 전환, FPS/청음 검사는 미실행이다.

## 선행 배포와 로컬 상태

로컬/원격 main HEAD `77451317d7d3f7a68a36f54d8de0c932769465cb`. DAY 7 [Pages run 41265412432](https://github.com/haepul/rythem_game/actions/runs/41265412432)의 completed/success와 해당 SHA를 API로 확인했다. 2026-11-03 공개 index.html/draw-service.mjs HTTP 200 및 커밋 파일과의 바이트 일치를 재확인했다([기록](day9-deployment-check.json)). DAY 8/9의 성공적인 배포를 의미하지 않는다. DAY 8/9는 commit/push/배포하지 않았다.
