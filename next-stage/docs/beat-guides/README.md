# 박자 가이드라인 정밀 개선 — 2026-10-29

로컬 구현 및 검증 완료. 기준 HEAD `b7b5d1b4a7fd45cf36f8271852d6c6da872205f8`. 배포·commit·push하지 않았다. 기존 DAY 2/3 가챠와 DAY 8 판정 텍스트 미커밋 작업은 보존했다. 아래 변경 범위는 이번 박자선 작업만을 뜻한다.

## 기존 구조와 수정 범위

`Stage.draw()`는 `beat=60/bpm`, `start=ceil((now-offset)/beat)`로 박자 시각을 구하고, `p=1-(offset+k*beat-now)/approach`를 `project(-.5,p)`에 전달했다. 선 양끝은 `x`와 `x+w*4`다. 앱은 기존 오디오 시간과 채보 BPM/offset, `.55/settings.speed`를 전달한다. 독립적인 박자 애니메이션 시계는 없다.

180개 채보 JSON에는 BPM/offset/duration/total/notes가 있고 명시적인 박자표·마디 메타데이터는 발견하지 못했다. 따라서 모든 박자에 같은 스타일을 적용하며 매 4번째 박자 강조는 넣지 않았다.

수정 파일:

- `next-stage/renderer.mjs`: 기존 grid 객체를 사용하는 `drawBeatGuides()` 분리, 테마의 저채도 민트 반사색 계산.
- `next-stage/app.mjs`, `next-stage/index.html`: 이번 변경은 renderer/app 캐시 버전만 갱신.
- `tests/test_beat_guides.mjs`: 좌표·시간·레이어·효과 OFF 회귀 테스트.
- `tests/fixtures/beat-guide-before.mjs`: 수정 전 박자선 루프 보존.
- `tests/beat-guides.html`: 동일 음악 시점 비교, 실제 MASTER 장면, BPM/approach/렌더 해상도 및 성능 측정 도구.
- 이 문서와 캡처·측정 JSON, 상위 README 링크.

`core.mjs`의 project 및 판정, audio.js, note-skin/palette, 채보는 Git diff가 없다. renderer의 나머지 노트·판정선·다이아몬드 렌더링은 변경하지 않았다. 이전 작업의 HUD/가챠 수정이 전체 Git diff에 남아 있으므로 이번 박자선 수정과 구분해야 한다.

## 최종 표현

| 요소 | 값 / 동작 |
|---|---|
| 중심선 | 연보라 `#C5C9E9`, 0.55→1.05 논리 px |
| 중심 불투명도 | 화면상 깊이에 따라 0.025→0.14, 양끝 및 밀도 감쇠 적용 |
| 약한 광채 | `#B4A6DF`, 1.6→2.2px, 중심 alpha의 16% |
| 민트 반사 | 기본 `#B1E0DA` 88% + 곡 accent 12%, 중심 alpha의 18% |
| 출현·소멸 | 상단 8px에서 등장, Y=410 직전 16px에서 smoothstep 감쇠 |
| 효과 OFF | 중심선만 유지, 광채·민트 반사 제거 |
| 과밀 처리 | sqrt(4/count) 투명도 감쇠; 극단적 밀도에서 실제 박자 중 최대 32개 표시 |

깊이는 기존 project 결과 `(y-110)/300`을 사용한다. 좌표나 속도는 그대로이고, Y=410에서 alpha만 0이 된다. 60~240 BPM × approach 0.35~1.0초에서는 박자를 생략하지 않는다. 최대 32개 표시 제한도 원래 박자 인덱스만 선택하며 새 박자나 마디를 만들지 않는다.

기존 레이어 순서(트랙 → grid → 판정선/리본 → 노트 → 입력·성공 효과)를 유지했다. 새 레이어, BlurFilter, Canvas, Texture, Sprite를 추가하지 않았다. 효과 ON은 선당 stroke 3회, OFF는 1회이므로 기존보다 Graphics 명령은 증가하지만 상한은 각각 96/32회다.

## 레퍼런스 확인 범위

[Colorful Palette 개발자 글](https://media.colorfulpalette.co.jp/n/nf36e1946d71b)을 읽고, [제공된 SLIDE 스크린샷](https://assets.st-note.com/img/1703212985149-8vMjyxt288.png?width=1200)을 실제 브라우저에서 확인했다. 어두운 바닥보다 밝은 민트 리본·노트가 먼저 보이는 명도 관계를 참고했다. 자료만으로 프세카 내부 BPM 가이드라인 알고리즘이나 박자표를 확인하지 못했으므로 이를 재현했다고 주장하지 않는다. 제공된 [영상](https://www.youtube.com/watch?v=5RbyprQO-3s)은 가져오기에 실패하여 시청하지 못했다.

## 실제 테스트

기존 테스트 존재 확인 후 실행:

- `python -m unittest discover -s tests -p test_note_renderer.py`: **11 통과**. Pygame 쪽 기존 테스트이며 Pixi 화면 검증과 별개다.
- `python -m unittest discover -s tests -p test_chart_layout.py`: **8 통과**.
- `node --test tests/test_beat_guides.mjs`: **17 통과**, 내부에서 기존 `test_judgment_3d.mjs`도 실행되어 PASS. 기존 풀 상한·프레임 자원 생성 회귀 검증 포함.
- `node --test tests/test_beat_guides.mjs tests/test_judgment_text.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs`: **51 통과**, 위 기존 판정선 스크립트 PASS 포함.
- renderer/app Node 문법 검사, `git diff --check` 통과.

| BPM | 0.35초 | 0.55초 | 1.0초 |
|---|---|---|---|
| 60 | 좌표/브라우저 통과 | 좌표/브라우저 통과 | 좌표/브라우저 통과 |
| 120 | 좌표/브라우저 통과 | 좌표/브라우저 통과 | 좌표/브라우저 통과 |
| 180 | 좌표/브라우저 통과 | 좌표/브라우저 통과 | 좌표/브라우저 통과 |
| 240 | 좌표/브라우저 통과 | 좌표/브라우저 통과 | 좌표/브라우저 통과 |

좌표 테스트는 각 조합에 3개 offset과 시작 전·박자 경계·진행 중 10개 음악 시간을 대입하여 수정 전후 양끝 좌표를 완전 비교한다. 60/120Hz 호출 이력의 같은 음악 시점, 반복 정지 시점, 재개 시점도 일치했다. 실제 Engine 기반 Stage 비교에서 grid 외 본체·리본·노트 위치와 Engine 상태가 동일했다.

브라우저는 12개 조합을 실제 Pixi fixture의 컨트롤로 변경하고 렌더 완료 상태를 확인했다([기록](browser-matrix.json)). TAP+FLICK, HOLD+TAP, SLIDE+TAP, 4레인 64노트 밀집 장면, 실제 `21-master-full.json`의 183.00872050058055초 장면을 캡처했다. 선이 리본 아래에 보이되 노트 헤드보다 약하며, 판정선 직전에서 밝기가 줄어드는 것을 확인했다. 효과 OFF에서도 중심선이 남는다.

실제 앱에서 나다움 HARD 1절 연습 모드의 READY → 플레이 → 자연 종료(213 MISS, 연습 기록 미저장 안내) → 재시작을 확인했다. 재시작 후 일시정지 모달에서 00:12, 계속하기 후 00:50으로 진행되는 것을 확인했다. 정지 좌표의 엄밀한 동일성은 위 자동 테스트로 검증했다. 실제 앱/fixture 콘솔 error 조회 결과는 비어 있었다. 오디오 출력의 청감상 박자 오차나 입력 지연을 별도로 측정한 것은 아니다.

## 변경 전후 캡처

기본 비교는 1280×720, 음악 시점 1.33초, approach 1초다. MASTER만 실제 채보의 별도 시점을 사용한다. 모바일은 요청 viewport 844×390(캡처 래스터는 브라우저 배율 반올림으로 843×390)이다. 원본 브라우저 JPEG와 PNG 변환본을 함께 보관했으며 그래픽 내용은 편집하지 않았다.

| 장면 | 캡처 |
|---|---|
| 수정 전 / 후 동일 idle | [before-idle.png](before-idle.png) / [after-idle.png](after-idle.png) |
| 120 / 240 BPM | [after-120bpm.png](after-120bpm.png) / [after-240bpm.png](after-240bpm.png) |
| 고밀도 / 실제 MASTER | [after-dense.png](after-dense.png) / [after-master.png](after-master.png) |
| HOLD / SLIDE | [after-hold.png](after-hold.png) / [after-slide.png](after-slide.png) |
| 모바일 / 효과 OFF | [after-mobile.png](after-mobile.png) / [after-effects-off.png](after-effects-off.png) |

## 성능 비교와 남은 한계

동일 실제 MASTER 고정 장면, 렌더 resolution 1, 20프레임 워밍업 후 각각 240프레임을 측정했다([원본 JSON](performance.json)).

| 측정 | 수정 전 | 수정 후 |
|---|---:|---:|
| Stage.draw CPU 호출 평균 | 1.94ms | 1.82ms |
| Stage.draw p95 | 3.10ms | 2.90ms |
| RAF 프레임 간격 평균 | 9.13ms | 9.34ms |
| RAF 프레임 간격 p95 | 16.7ms | 16.7ms |
| 관측 FPS | 109.5 | 107.1 |

이 한 쌍의 측정에서 큰 저하는 관찰하지 못했다. 평균 차이는 실행 환경 변동 범위일 수 있으므로 성능 향상으로 단정하지 않는다. GPU 완료 시간, 전체 곡 실시간 FPS, 모바일 실기기 성능 측정이 아니다.

1280×720 및 모바일 가로 레이아웃에서 확인했고 Pixi 렌더 버퍼 resolution 1/2(800×480/1600×960)를 확인했다. 테스트 중 브라우저 DPR은 약 1이었으므로 **실제 DPR2 디바이스 검증은 미완료**다. 물리 60/120Hz 디스플레이의 프레임 유지, 실제 터치, 청감 동기화는 별도 기기 검증이 필요하다. 이번 작업에서는 해당 로직을 수정하지 않았다.

로컬 앱: `http://127.0.0.1:8782/next-stage/?check=20261029-beat-guides`

비교 도구: `http://127.0.0.1:8782/tests/beat-guides.html`
