# DAY 7 — 2.5D 판정 플랫폼 검증

## 후속 수정: 넓은 사다리꼴 판정 영역

사용자의 추가 이미지에 맞춰 아래 최초 구현을 다시 수정했다. 최신 치수는 판정 기준 Y410에서
플레이어 방향 Y444까지 **34px 깊이의 어두운 윗면**, Y444~449의 5px 앞면이다.
앞쪽 외곽 X는 기존 project 연장으로 약 13.18~786.82이며 장식이다. 실제 입력/판정 범위는 X38~762, Y410 그대로다.
이전의 밝은 7px 윗면을 넓은 어두운 면과 보라색 외곽으로 대체하고 레인 경계도 이어 그린다.
노트 헤드의 도착 시 Sprite 높이는 62→78px(약 26% 증가); 원거리 높이 36px, 폭, 하단 anchor, 판정 시각은 유지한다.
FLICK 화살표와 HOLD/SLIDE 헤드도 같은 표시 배율을 적용한다. 텍스처 원본은 변경하지 않았다.
입력 반사는 넓어진 면에 맞춰 확장했다. renderer/app의 모듈 URL 버전과 테스트 페이지 import를 갱신해 이전 캐시를 피한다.

최신 캡처: [노트와 넓은 판정 영역](judgment-wide-notes.jpg), [SLIDE/다이아몬드](judgment-wide-slide.jpg), [효과 OFF](judgment-wide-off.jpg).
실제 브라우저에서 위 세 장면 확인, 수정한 test_judgment_3d 및 구문/diff 검사 통과.
아래 최초 구현의 치수·캡처·성능 수치는 이전 단계 기록이며 이 후속 수정의 성능을 재측정한 값은 아니다.
commit/push/배포 없음. 8770/web-next는 수정한 Git 체크아웃과 다른 페이지이므로 8782/next-stage에서 확인한다.

2026-10-26 KST, 기준 HEAD `19bc813`. 배포·commit·push 없음.
기존 미커밋 README 및 docs/gacha 문서는 보존했다.

## 변경

런타임 수정은 `next-stage/renderer.mjs`의 initJudgment/themeJudgment/resetJudgment/drawJudgment에 한정했다.
추가: `tests/test_judgment_3d.mjs`, `tests/judgment-3d.html`, 이 보고서와 실제 캡처.
core/project/노트 텍스처/팔레트/오디오/입력/채보/HUD/app은 Git diff에서 변경 없음.
Stage.init의 기존 렌더링 순서, 다이아몬드 생성 조건/개수/텍스처/풀 및 drawImpacts는 그대로다.

기존 본체는 9px stroke와 삼각 하이라이트라 수평선으로 읽혔다.
새 본체는 정적 Graphics의 세 면으로 분리되며 themeJudgment 때만 구축한다.

| 면 | 좌표·크기 (800×480 논리 좌표) | 색상 |
|---|---|---|
| 윗면 | Y403→410, 깊이 7px, project로 트랙 쪽 너비 계산 | 뒤 #A985F0 → 앞 #D9D4FF |
| 앞면 | Y410→422, 높이 12px, 끝에서 5px 안쪽 | #8C6AE0 → #514194 → #251E51 |
| 좌/우 측면 | X38~43 / 757~762, 5px 사선 캡 | 왼쪽 #7464B4 / 오른쪽 #392C6E |
| 중심선 | X38→762, Y410, 기존 2.2px | 기존 #F7FFFF 유지 |
| 하단 반사 | Y422, 0.8px, 낮은 alpha | #8FE9DC |
| 외곽 glow | 기존 28/22/16/13px 계층 | 기존 테마 색 유지 |

앞면은 화면 아래로만 돌출하는 장식이다. 판정 Y410, X38~762, project 및 입력 영역은 불변이다.
윗면 뒤쪽의 원근 너비는 project의 기존 Y식을 역산해 얻는다. 높이는 전 구간 동일하다.
새 반사 Graphics는 본체와 함께 노트 뒤에 둔다. contacts의 상승 edge를 관측해 레인별 80ms 반사광을 표시한다.
장시간 홀드 시 장식 펄스는 사라지고 기존 입력 위치 표시만 유지한다. 가짜 판정 이벤트를 만들지 않는다.
효과 OFF에서는 glow/다이아몬드/장식 반사는 끄고 본체·중심선·최소 입력 표시를 유지한다.

렌더링 순서: track → grid → judgeGlow(외곽/본체/새 반사/기존 ambient 및 laneLights)
→ ribbon → heads → judgeHighlight → inputHighlight → fx → diamondBurst.
새 Canvas/Texture/필터/3D 엔진은 추가하지 않았다. 추가 리소스는 재사용 Graphics 하나와 4개 press 시간 배열이다.

## 참고 관찰

- [개발사 기사](https://media.colorfulpalette.co.jp/n/nf36e1946d71b): 2023-12-24 게시.譜面 의도 설명을 텍스트로 확인. 판정선 메시 구현의 근거는 아님.
- [기본 이미지](https://assets.st-note.com/img/1702892059947-osEl2Btoos.png?width=1200): 실제 브라우저 이미지 관찰. 얇고 밝은 경계, 어두운 내부 영역, 트랙 연결이 깊이를 구분한다.
- [SLIDE 이미지](https://assets.st-note.com/img/1703212985149-8vMjyxt288.png?width=1200): 실제 관찰. 리본과 다이아몬드의 빛이 경계보다 앞에 읽힌다.
- [입력 참고](https://assets.st-note.com/production/uploads/images/36680972/picture_pc_a78f61a0107ee052ebc1a5f31bc81ad8.jpg?fit=bounds&height=2000&quality=85&width=2000): 실제 관찰. 판정 부근 국소적인 광량 증가와 어두운 면의 대비를 참고했다.
- [영상 1](https://www.youtube.com/watch?v=5RbyprQO-3s), [영상 2](https://www.youtube.com/watch?v=TabBrIDHalk): 웹 접근 실패. 실제 재생·시간 측정 미실행.

공식 내부 구현이 3D인지 확인하지 않았다. 위 치수/색상은 사용자 제안을 바탕으로 한 독립 구현이며 공식 측정값이 아니다. 참고 자산 복사 없음.

## 실제 캡처

브라우저의 원본 캡처 형식이 JPEG여서 .jpg로 저장했다. PNG로 확장자만 바꾸지 않았다.
before는 HEAD renderer를 임시 별도 모듈로 로드한 동일 테스트 장면/1280×720/DPR1이고,
after는 수정 renderer다. 기준 임시 파일/임시 import 분기는 비교 후 삭제했다.

| 비교 | 캡처 |
|---|---|
| 변경 전 | [before](judgment-3d-before.jpg) |
| 변경 후 | [after](judgment-3d-after.jpg) |
| 확대 | [closeup](judgment-3d-closeup.jpg) |
| TAP / FLICK | [TAP](judgment-3d-tap.jpg), [FLICK](judgment-3d-flick.jpg) |
| 유지·이동 | [HOLD](judgment-3d-hold.jpg), [SLIDE](judgment-3d-slide.jpg) |
| 실제 Engine 성공 이벤트 | [PERFECT](judgment-3d-diamond.jpg), [GREAT](judgment-3d-great.jpg), [4레인](judgment-3d-four.jpg) |
| 밀집 | [합성 스트레스](judgment-3d-dense.jpg), [실제 MASTER](judgment-3d-master.jpg) |
| OFF / 밝은 배경 | [OFF](judgment-3d-effects-off.jpg), [bright](judgment-3d-bright.jpg) |
| 크기 | [1366×768](judgment-3d-1366.jpg), [844×390](judgment-3d-mobile.jpg), [800×360](judgment-3d-800.jpg) |
| 실제 게임 재개 후 | [gameplay](judgment-3d-gameplay.jpg) |

앞면·윗면의 명암 분리, 끝의 bevel, TAP/FLICK/HOLD 헤드 비가림, SLIDE 연결과 다이아몬드 전경 표시를 이미지로 확인했다.
4레인 성공은 Engine.step에 실제 키 이벤트를 넣는 고정 시각 테스트이며 실제 사용자의 동시 키 입력 검증과 구분한다.
MASTER 스냅샷은 푸르름이 사는 곳 `data/21-master-full.json`, 183.009초 부근의 실제 채보다.
전체 30곡 MASTER-full에서 0.55초 구간의 시작 노트 개수를 조사해 9개인 구간을 선택했다. 이는 실제 무음 렌더링 검증이며 전체곡 플레이가 아니다.
실제 앱에서는 나다움 HARD 연습 모드 로딩, 진행, 일시정지, 계속하기, 재개 후 진행 표시를 확인했다. 관찰한 console error는 0개였다.

## 자동 검사

| 실행 | 결과 / 한계 |
|---|---|
| node tests/test_judgment_3d.mjs | 통과. 프로젝트 실제 Stage + 기록용 Pixi double로 좌표·면·레이어·정적 본체·효과 OFF·80ms 반사·60/120Hz 호출·풀 상한·할당 확인. 실제 Engine TAP/FLICK/HOLD/SLIDE 및 PERFECT/GREAT/MISS 점수 확인 |
| node --check next-stage/renderer.mjs | 통과 |
| node --test tests/test_browser_input.cjs | 기존 13개 통과. 루트 audio_player.js 테스트로 NEXT 전용 시험이라고 주장하지 않음 |
| python -m unittest discover -s tests -p test_flick_judgement.py | 기존 Python 판정 29개 통과 |
| python -m unittest discover -s tests -p test_note_renderer.py | 기존 Python/glass 렌더링 11개 통과; Pixi GPU 시험은 아님 |
| git diff --check | 통과. 기존 README의 Git LF/CRLF 안내만 있음 |
| 보호 파일 diff | core/app/audio/note-skin/note-palette/play-hud/data 변경 없음 |

새 시험은 노트 Sprite pool 워밍업 이후 Canvas/Texture/Sprite 할당 증가 0을 확인했다.
기존 지연 생성되는 노트 헤드 pool까지 처음부터 할당 0이라고 주장하지 않는다.
다이아몬드 burst 32 / halo 4 / ambient 8 상한 유지. GPU 렌더링 자체는 실제 브라우저 캡처로 별도 확인했다.
기존 NEXT test_web_next.mjs 등 누락 파일은 실행/통과했다고 보고하지 않는다.

## 성능 비교

동일 notes 고정 장면, 동일 1280×720/DPR1, 같은 브라우저에서 워밍업 20회 후 240프레임.
Stage.draw+app.render 호출의 performance.now 소요 시간이며 GPU 완료 시간은 아니다.

| 측정 | HEAD 전 | 수정 후 |
|---|---:|---:|
| render CPU p50 | 3.2ms | 2.2ms |
| render CPU p95 | 6.5ms | 3.6ms |
| RAF 간격 p50 | 8.3ms | 8.3ms |
| RAF 간격 p95 | 8.7ms | 9.0ms |

이 표본에서 눈에 띄는 프레임 저하는 관찰하지 않았다. 브라우저/GPU 부하 변동이 있으므로 빨라졌다는 결론은 내리지 않는다.
RAF는 약 120Hz 관찰이며 60Hz 실제 디스플레이 시험은 하지 않았다. 60/120Hz 호출의 시간 기반 효과는 자동 검사로 확인했다.
실제 곡 장시간 FPS, GPU 타이밍, 입력 지연 수치 및 실기기 성능은 미측정이다.

## 한계와 재현

- 요청한 네 viewport 크기는 실제 DOM 크기를 확인해 검사했다. DPR은 약 1이었다. 도구가 DPR 지정 API를 제공하지 않아 **844×390 및 800×360 DPR2 검증은 미완료**다.
- 밝은/어두운 테스트 배경은 대비용 CSS 배경이다. 실제 밝은/어두운 MV를 재생한 검증은 아니다.
- 실제 음악 재개·곡 진행은 확인했으나 청취 기반 오디오 싱크 측정은 하지 않았다.
- 자동 시험의 Graphics double은 실제 GPU anti-aliasing과 메모리 사용을 측정하지 않는다.
- 판정 성공 시 별도 윗면 반사 이벤트를 추가하지 않았다. 기존 성공 fx/diamond 레이어는 그대로 유지하고 새 반사는 contacts에만 반응한다.

로컬 저장소 루트에서 `python -m http.server 8782 --bind 127.0.0.1` 후
`/tests/judgment-3d.html`로 고정 장면을, `/next-stage/`로 실제 게임을 확인한다.
기존 사용자가 열어 둔 8770/web-next는 이번 수정 대상 체크아웃이 아니다.
