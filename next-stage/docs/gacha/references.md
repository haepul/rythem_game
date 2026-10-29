# DAY 1 출처와 관찰 범위

확인일: 2026-10-26 KST. 공식 규칙, 지역·시기별 화면, 우리 구현 제안을 구분한다.
아래 이미지·폰트·음원·로고를 저장소 자산으로 복사하지 않았다. 영상 실제 재생은 하지 않았다.
문서에 적은 비율·모션·색상은 별도 표시가 없는 한 [아키텍처](architecture.md)의 프로젝트 제안이며 공식 수치가 아니다.

## 공식 글로벌 자료 — 텍스트 확인

| 출처 | 지역 / 게시 시기 | 확인 내용과 적용 | 미확인 |
|---|---|---|---|
| [라인업·확률 FAQ 654](https://sega.helpshift.com/hc/en/12-hatsune-miku-colorful-stage/faq/654-where-can-i-check-the-gacha-lineup-and-drop-rates/) | 영어 글로벌. 절대 게시일 미확인; 상대 업데이트 일수만 노출 | 배너의 상세에서 확률을 확인하는 흐름. 우리 UI도 확인창 전에 동일 버전의 상세·확률 제공 | 내부 난수 구현, 현재 전체 배너 정책, 픽셀·색상 |
| [중단 후 획득 FAQ 653](https://sega.helpshift.com/hc/en/12-hatsune-miku-colorful-stage/faq/653-i-lost-my-crystals-when-the-game-crashed-while-i-was-pulling-in-the-gacha-what-should-i-do/) | 영어 글로벌. 절대 게시일 미확인 | 중단 시 획득 목록 확인 안내. 우리 설계에서는 확정 결과와 연출을 분리하고 receipt 복구 제공 | 공식 서버 트랜잭션·저장 순서. 우리 snapshot 설계가 공식 구현이라는 의미 아님 |
| [보너스 FAQ 652](https://sega.helpshift.com/hc/en/12-hatsune-miku-colorful-stage/faq/652-what-is-a-gacha-bonus/) | 영어 글로벌. 절대 게시일 미확인 | 배너 종류·재화 종류에 따라 보너스 조건이 다름. 배너별 규칙/버전 분리 필요 | 일본판과 동등성, 미래 변경. 유료 요소 및 수치는 우리 무료 모델에 가져오지 않음 |
| [v3.0.0 안내](https://www.colorfulstage.com/news/detail/000573.html) | 글로벌, 2024-09-30 | 메뉴 UI 및 가챠 3D 연출 개편을 텍스트로 확인. 구버전/신버전 자료를 혼합해 하나의 공식 규격으로 취급하지 않음 | 실제 연출 동영상·타이밍·모든 화면 이미지 |

위 FAQ의 기능 설명으로 확률·비용·보장·교환 숫자를 확정하지 않는다. DAY 1에서는 구조만 설계했다.

## 일본판 메뉴 — 텍스트와 이미지 관찰

[개인 플레이 기록](https://ameblo.jp/kokokororosekai2020/entry-12951846879.html)
페이지 표기 게시 시각: **2025-12-31 13:12:36** (사이트 표기 시간대 자체는 미확인), 본문에 1월 4일 추가 기록이 있다.
일본판 플레이 화면이지만 비공식 개인 블로그이며 규칙의 권위 있는 출처로 쓰지 않는다.

실제로 연 이미지: [800×556 배너 메뉴](https://stat.ameba.jp/user_images/20251231/12/kokokororosekai2020/99/0b/j/o2560177815735873678.jpg?caw=800).
브라우저 스크린샷에서 왼쪽 세로 배너 목록, 선택된 민트 배경, 큰 중앙 비주얼, 상단 잔액/교환,
하단 상세와 추첨 버튼들을 관찰했다. 이 계층을 우리 셸 안의 배너 목록/비주얼/액션으로 재구성한다.
원작의 여러 유료 버튼, 캐릭터, 로고, 배너 홍보 문구는 가져오지 않는다.
공식 비율·폰트·색상값을 샘플링하지 않았고 현재 한국/글로벌판과 동일하다고 주장하지 않는다.

## 일본판 2023 개발 중 연출 — 정지 이미지 관찰

[3주년 선행 플레이 기사](https://news.denfaminicogamer.jp/kikakuthetower/230929x)
페이지 게시일 **2023-09-30 00:00**. URL의 230929를 게시일로 쓰지 않는다.
일본판 미디어 사전 체험 자료이며 기사 캡션이 가챠 연출임을 명시한다.

실제로 연 이미지: [1202×674 연출 스틸](https://news.denfaminicogamer.jp/wp-content/uploads/2023/09/image_019-2.jpg).
화면에 개발 중 표시가 있다. 파스텔 보라/청록 공간, 중앙 광원, 삼각형 윤곽, 하단 진행 안내,
오른쪽 위 건너뛰기 아이콘을 관찰했다. 우리 연출에는 캐릭터 없이 독립 도형·중앙 집중·명시적 skip만 적용한다.
정지 화면에서 지속 시간·가속 곡선·희귀도별 연출·확률을 추정하지 않는다. 영상 재생 및 프레임 측정은 미실행이다.

## 구버전 결과 참고 — 접근 실패

[2022 결과 후보](https://nagatsukiririnagames.hatenablog.jp/entry/2022/07/21/142439)
URL에 2022-07-21이 있으나 이번 웹 접근은 Internal Error로 실패했다.
본문·게시일·결과 스크린샷은 확인하지 못했다. 일본판 구버전 참고라는 분류는 사용자 지정에 따른다.
따라서 5×2 결과 배열은 이 페이지를 확인한 결론이 아니라 사용자 요구 및 우리 초기안이다.
후속 결과 화면 작업 때 재확인하되 접근이 안 되면 독립 설계를 유지한다.

## 기존 프로젝트와 비교

[현재 공개 메뉴](https://haepul.github.io/rythem_game/next-stage/?v=20261022-track)를 실제 브라우저에서 열고 접근성 트리와 스크린샷을 관찰했다.
왼쪽 LIBRARY/FAVORITES/RECORDS, 상단 설정, 밝은 패널, 민트 선택 카드, 우측 곡 상세, 30곡/3페이지 표시를 확인했다.
새 가챠 영역은 이 셸 안에서 보여야 한다. 공개 화면 관찰은 로컬 소스와 배포 파일의 바이트 일치 검증은 아니다.
사용자가 열어 둔 `/web-next/`는 이번 Git 저장소의 검증 대상 경로로 간주하지 않았다.

## 기술 근거

- [MDN Web Locks](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API): 같은 origin의 협력하는 writer를 직렬화할 수 있다. 실제 지원 여부와 실패는 런타임에서 검사한다. 미지원 때 임의 lease 대신 쓰기 차단을 선택했다.
- [MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage): origin별 지속 저장이며 정책에 의해 접근이 거절될 수 있다. 브라우저 데이터 삭제·비공개 세션의 영구 보존을 보장하지 않는다.

기술 자료는 2026-10-26 열람. 대상 Android/iOS 실기기 지원은 아직 측정하지 않았다.
모든 적용 제안과 미확인 범위는 [검증 계획](validation-plan.md)에서 단계별로 확인한다.
