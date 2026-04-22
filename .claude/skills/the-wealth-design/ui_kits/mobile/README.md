# Mobile UI Kit

iOS 느낌의 모바일 앱 UI kit (390×780px 프레임).

## 파일

| 파일 | 용도 |
|---|---|
| `index.html` | 조립된 홈 화면 |
| `styles.css` | 모바일 전용 스타일 |
| `Hero.jsx` | 최상단 평가금액 히어로 카드 |
| `HoldingList.jsx` | 보유 종목 리스트 (iOS 그룹형 리스트 스타일) |
| `TabBar.jsx` | 하단 5-탭 내비게이션 (홈/포트폴리오/관심/알림/내 정보) |

## 주의

- 상단 `safe-area`, 하단 `home indicator` 영역은 padding 으로 근사.
- 바닥 탭바는 `backdrop-blur` 를 예외적으로 사용 (iOS 감성).
- 리스트 카드는 `rounded-2xl` (16px) — 데스크톱보다 한 단계 크게.
