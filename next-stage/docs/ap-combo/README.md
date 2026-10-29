# PERFECT / AP 유지 콤보 — 2026-10-29

## 구현

- `play-hud.css`: 기존 PERFECT 위치·크기를 유지하고 가로 핑크→흰색→하늘색 그라데이션, 얇은 연보라 윤곽과 작은 그림자를 적용했다. GREAT/MISS 색상은 유지했다.
- `play-hud.mjs`: `isAPMaintained(counts)`가 실제 Engine 누적 통계를 읽는다. PERFECT가 1회 이상이며 다른 판정이 전부 0일 때만 유지 상태다. 누락/잘못된 통계는 일반 상태로 처리한다. 마지막 feedback이나 현재 combo로 AP를 추정하지 않는다.
- AP 콤보만 파스텔 그라데이션과 최대 2개의 CSS 별빛을 표시한다. GREAT/MISS 이후에는 일반 연분홍 숫자로 전환하며 이후 PERFECT로 복구되지 않는다. 곡 재시작의 새 Engine 통계와 기존 HUD.reset을 그대로 사용한다.
- AP 해제 시 숫자는 바로 갱신하며 wrapper opacity만 110ms 전환한다. 별빛과 AP 그라데이션은 즉시 제거한다. 게임 도중 ALL PERFECT 달성 문구는 추가하지 않았다.
- 효과 OFF/reduced-motion에서는 색 구분을 유지하되 별빛·색 이동을 멈춘다. forced-colors 대응 포함. 기존 콤보 3 이상 표시 정책·글꼴·좌표는 유지한다.
- `app.mjs`와 `index.html`: 캐시 버전 갱신. renderer/core/audio/채보/판정선/다이아몬드는 이번 작업에서 수정하지 않았다. 이전 박자선 등 미커밋 변경은 그대로 보존했다.

텍스트는 기존 DOM/CSS 구조를 사용한다. 새 Canvas/Texture/Sprite/BlurFilter 생성은 없다. 그라데이션 위치 이동은 작은 글자 영역만 다시 그리며, 별빛은 opacity/transform을 사용한다. AP 상태와 효과 설정의 DOM 속성은 변경될 때만 쓴다.

## 참고 자료

[개발자 블로그](https://media.colorfulpalette.co.jp/n/nf36e1946d71b)와 제공된 플레이 스크린샷에서 어두운 배경 위 밝은 글자, 외곽선과 파스텔 색상을 참고했다. 현재 게임의 기존 캡처와 새 브라우저 화면을 비교했다. 원본 이미지 리소스는 삽입하지 않았다.

[공식 FAQ](https://pjsekai.sega.jp/faq/index.html)의 실제 로드된 리듬게임 항목에서 AP 유지 중 COMBO에 별도 연출이 적용된다는 설명을 확인했다. 정확한 색상 stop이나 전환 시간은 확인되지 않았으며 이 구현의 110ms/4초 색 이동은 우리 UI 설정이다.

## 테스트

`node --test tests/test_ap_combo.mjs tests/test_judgment_text.mjs tests/test_beat_guides.mjs tests/test_gacha_banners.mjs tests/test_menu_navigation.mjs`: **64 통과**. 기존 `test_judgment_3d.mjs`도 내부 실행되어 PASS. 문법 검사와 git diff 검사 통과.

새 AP 테스트 13개는 실제 Engine 입력을 사용한다. 100 PERFECT, 99 PERFECT+GREAT, 이후 100 PERFECT, MISS 후 새 콤보, 4레인 동시 PERFECT, 동시 GREAT+PERFECT, HOLD/SLIDE 중간 성공·실패, 새 곡/reset, 정지 시점 반복·재개, OFF, 잘못된 통계, 실제 MASTER 누적 결과를 검증한다. GOOD/BAD는 현재 엔진에 없으므로 통계 어댑터의 거부 동작만 시험했다.

동시 혼합 판정에서는 마지막 feedback이 PERFECT여도 누적 GREAT가 1이므로 AP가 해제됨을 확인했다. HOLD/SLIDE 중간 MISS 이후 끝점을 PERFECT로 처리해도 AP는 복구되지 않는다. 테스트 초기 sustain tail 기대값이 실제 기존 커버리지 규칙과 달라 입력 재접촉 시점을 수정했으며 엔진 규칙은 변경하지 않았다.

브라우저에서도 위 11개 장면과 Next GREAT/Restart 컨트롤을 확인했다([결과](browser-checks.json)). 실제 앱은 나다움 HARD 연습 모드 시작·일시정지·재개·결과·재시작을 확인했다. 정지 시 00:31의 일반 상태가 재개 후에도 유지됐고, 재시작 READY에서는 combo 0이었다. AP 유지 상태의 정지/재개는 자동 테스트로 확인했으며 수동 연주 AP 상태로 실기기 검증한 것은 아니다.

## 캡처

- [perfect-gradient.png](perfect-gradient.png)
- [ap-combo.png](ap-combo.png)
- [normal-combo.png](normal-combo.png): GREAT 이후 PERFECT 100회, combo 200에서도 일반 상태.
- [ap-to-normal.png](ap-to-normal.png): 99 PERFECT+GREAT, 110ms 전환의 중간 시점.
- [mobile-combo.png](mobile-combo.png): 844×390 viewport, 브라우저 배율 반올림으로 이미지 폭 843px.
- [effects-off.png](effects-off.png), [master-combo.png](master-combo.png)

PNG는 브라우저 JPEG 캡처를 내용 변경 없이 변환한 것이다. fixture는 실제 Engine 판정을 사용하되 무음·고정 시점이며, 음악을 연주한 화면이라고 주장하지 않는다. PERFECT/AP 캡처에도 미처리 노트를 남겨 곡 도중 상태임을 구분했다.

## 성능 및 남은 검증

변경 없는 HUD 업데이트 1만 회 평균: 수정 전 0.01675ms, 수정 후 0.00941ms. p95는 모두 약 0.1ms, DOM mutation은 모두 0건. 이는 JS 호출 측정이며 GPU 렌더링 시간이 아니다.

첫 240프레임 비교는 94.1→93.2 FPS, 마지막 약한 AP glow 추가 후 재측정은 84.0 FPS였다. 측정 중 다른 게임 탭 실행·뷰포트 변경이 있어 환경이 일정하지 않으며, 성능 향상이나 안정적인 120FPS를 보장하지 않는다. 표시 탭의 추가 기준 측정은 82.3 FPS였으나 사용자가 배포 우선으로 변경하여 최종 쌍 측정을 완료하지 않았다. [원본 측정](performance.json)에 완료된 값만 보관했다.

모바일 가로 및 1600×960 Pixi 버퍼(resolution 2)를 확인했다. 실제 브라우저 DPR은 1~1.25였으므로 **실제 DPR2 기기·물리 터치·모바일 GPU 성능은 미검증**이다. OS reduced-motion 대신 앱 효과 OFF와 fixture reduced 상태를 확인했다.

2026-10-29 사용자의 후속 지시로 배포를 우선 진행한다. 배포 성공 여부는 GitHub Pages 실행 결과 및 공개 URL 검증으로 별도 확인한다.
