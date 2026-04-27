# Brand Assets

The Wealth 브랜드 자산 패키지의 용도와 적용 위치 정리.
모든 마스터는 `frontend/public/brand/` 에 보관하며, PNG는 `npm run build:icons` 로 재생성한다.

## SVG 마스터 인덱스

| 파일 | viewBox | 용도 |
|------|---------|------|
| `logo-mark.svg` | 24×24 | 사이드바/헤더의 다이아몬드 마크 단독 |
| `logo-lockup.svg` | 240×40 | 마크 + "THE WEALTH" 워드마크 (라이트 배경) |
| `logo-lockup-dark.svg` | 240×40 | 다크 배경용 lockup — `prefers-color-scheme: dark` 또는 `next-themes` 의 `resolvedTheme === "dark"` 시 자동 스왑 |
| `favicon.svg` | 32×32 | 브라우저 탭 favicon — `app/icon.svg` 로 복사되어 Next App Router 가 자동 등록 |
| `app-icon-master.svg` | 1024×1024 | PWA / iOS / Android 기본 솔리드 브랜드 아이콘 |
| `app-icon-dark.svg` | 1024×1024 | iOS 18 다크 변형 (모바일 네이티브 도입 시 사용) |
| `app-icon-light.svg` | 1024×1024 | iOS 18 라이트 틴티드 변형 |
| `app-icon-mono.svg` | 1024×1024 | 알림/시계/잠금화면용 모노크롬 |
| `app-icon-neon.svg` | 1024×1024 | 단타 모드 / Pro 알트 아이콘 (네온 #00ff00) |
| `app-icon-android-fg.svg` | 432×432 | Android 어댑티브 아이콘 foreground 레이어 |
| `app-icon-android-bg.svg` | 432×432 | Android 어댑티브 아이콘 background 레이어 |

> 모바일 네이티브(iOS/Android) 코드는 현재 저장소에 존재하지 않는다.
> Capacitor/Expo/네이티브 wrapper 도입 시 위 자산들을 그대로 활용한다.

## 컴포넌트 / 코드 적용

### `BrandLogo` (`frontend/src/components/BrandLogo.tsx`)

```tsx
<BrandLogo variant="mark" size={20} priority />
<BrandLogo variant="lockup" size={28} />
```

- `variant="mark"` — 정사각형 마크 (기본 24px)
- `variant="lockup"` — 마크+워드마크 (기본 높이 28px, 6:1 비율)
- `useTheme()` 의 `resolvedTheme` 으로 lockup의 라이트/다크 자동 스왑
- `aria-label="The Wealth"` 자동 부여

현재 사용처: `Sidebar.tsx`.

### Next App Router 컨벤션 자동 등록

| 파일 | 역할 |
|------|------|
| `frontend/src/app/icon.svg` | `<link rel="icon">` 자동 생성 |
| `frontend/src/app/favicon.ico` | 32+16 멀티사이즈 ICO |
| `frontend/src/app/apple-icon.png` | 180×180 Apple touch icon |
| `frontend/src/app/manifest.ts` | `/manifest.webmanifest` 라우트 — PWA 설치 메타 |

수동으로 metadata.icons 를 명시할 필요 없다 — App Router 가 위 파일을 감지해 `<head>` 에 자동 주입한다.

## PNG 생성 파이프라인

`frontend/scripts/build-icons.mjs` 한 파일에 모든 변환이 묶여 있다.

```bash
cd frontend
npm run build:icons
```

생성물:

| 출력 경로 | 사이즈 | 마스터 | 비고 |
|-----------|--------|--------|------|
| `src/app/favicon.ico` | 32+16 | `favicon.svg` | png-to-ico 로 multi-size ICO |
| `src/app/icon.svg` | 32×32 | `favicon.svg` | 그대로 복사 |
| `src/app/apple-icon.png` | 180×180 | `app-icon-master.svg` | iOS 홈스크린 |
| `public/brand/icon-192.png` | 192×192 | `app-icon-master.svg` | PWA 표준 |
| `public/brand/icon-512.png` | 512×512 | `app-icon-master.svg` | PWA 표준 |
| `public/brand/icon-mask.png` | 512×512 | `app-icon-master.svg` | maskable, 80% safe zone, `#1574d2` 배경 |
| `public/icon-192.png` | 192×192 | `app-icon-master.svg` | 레거시 호환 (구 absolute path) |
| `public/icon-512.png` | 512×512 | `app-icon-master.svg` | 레거시 호환 |
| `public/apple-touch-icon.png` | 180×180 | `app-icon-master.svg` | 레거시 호환 |

**규칙:**
- 변환 결과 PNG/ICO 는 git 에 커밋한다 (CI 에서 매번 빌드하지 않는다).
- 마스터 SVG 변경 시 반드시 `npm run build:icons` 를 다시 돌리고 변경된 PNG 를 함께 커밋한다.
- 생성 도구: `sharp` (devDependency), `png-to-ico` (devDependency).

## 브랜드 컬러

| 토큰 | 값 | 용도 |
|------|----|------|
| Primary | `#1574d2` | manifest `theme_color`, maskable icon 배경 |
| Accent (밝은 톤) | `#1e90ff` | 마크 fill, lockup 그라디언트 |
| Accent (그라디언트 끝점) | `#2da4ff` | app-icon-master 백그라운드 그라디언트 |

> **주의**: 한국 증시 가격 표시 색상(`상승=red`, `하락=blue`)은 도메인 컨벤션이며 브랜드 컬러와 별개로 그대로 유지한다.

## 향후 작업

다음은 인프라/플랫폼 도입 시점에서 추가 작업이 필요하다 — 자산은 이미 준비되어 있다.

- **iOS 네이티브**: `Assets.xcassets/AppIcon.appiconset/` 구성, `Contents.json` `appearances` 에 `dark`/`tinted` 등록
- **Android 네이티브**: `mipmap-*` 어댑티브 아이콘, `res/values/themes.xml` monochrome 등록
- **iOS 알트 아이콘 (단타 모드)**: `Info.plist` `CFBundleAlternateIcons` 에 `pro` (= `app-icon-neon.svg`) 등록 후 `setAlternateIconName('pro')` 호출
