# Mobile PWA Runbook

Operational procedures for the service worker and Web Push stack introduced in Sprint 17.

---

## 1. Service Worker (`public/sw.js`)

### Deploying a new SW version

1. Bump `SW_VERSION` at the top of `public/sw.js` (e.g. `"v1"` → `"v2"`). This is the only correct way to invalidate runtime caches. Do **not** change cache names individually — the activate handler only cleans up caches whose name suffix doesn't match the current version.
2. Verify locally: `npm run build && npm run start`, open DevTools → Application → Service Workers, confirm the new SW installs.
3. Ship via the normal `deploy.yml` pipeline.

### What clients see after deploy

- Next page load: browser fetches `/sw.js` (response has `Cache-Control: public, max-age=0, must-revalidate`), detects a new install.
- The new SW enters `waiting` state.
- `ServiceWorkerUpdateToast` detects `registration.waiting` and shows a Sonner toast: "새 버전이 준비됐어요. 새로고침하면 최신 앱으로 업데이트됩니다."
- Clicking 새로고침 posts `SKIP_WAITING`, the SW activates and `controllerchange` fires → `location.reload()`.

### Rolling back the SW

- Revert the SW commit. The previous `SW_VERSION` ships. Clients follow the same waiting/toast flow — no manual unregister needed.
- Nuclear option (corrupted SW served to many users): keep the URL `/sw.js` but serve a kill-switch SW:
  ```js
  self.addEventListener("install", () => self.skipWaiting());
  self.addEventListener("activate", async () => {
    await self.registration.unregister();
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => caches.delete(k)));
    const clients = await self.clients.matchAll();
    clients.forEach((c) => c.navigate(c.url));
  });
  ```

### Debugging cache issues

- Chrome: DevTools → Application → Cache Storage lists `wealth-api-v1`, `wealth-static-v1`, `wealth-images-v1`, `wealth-pages-v1`.
- Network tab shows `(from ServiceWorker)` for served-from-cache responses.
- Force refresh without SW: DevTools → Application → Service Workers → "Bypass for network".

### What is never cached

- `/api/v1/auth/*` (login, refresh, sessions)
- `/api/v1/prices/stream` (SSE)
- `/api/v1/push/*`
- All non-GET requests

Any regression that caches these will break refresh-token rotation — add matchers to `isBypass(url)` only.

---

## 2. Web Push (VAPID)

### Generating VAPID keys

```bash
cd backend && source venv/bin/activate
python - <<'PY'
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print("PRIVATE:", v.private_pem().decode())
print("PUBLIC :", v.public_pem().decode())
PY
```

Paste the URL-safe base64 outputs into `backend/.env`:

```
VAPID_PUBLIC_KEY=BH...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:admin@joonwon.dev
```

Restart the backend. `GET /api/v1/push/public-key` must return `{enabled: true, ...}`.

### Rotating VAPID keys

⚠️ Rotating invalidates every existing subscription — clients must re-subscribe with the new public key.

1. Generate new key pair as above.
2. Put the new keys into `.env` and restart backend.
3. `TRUNCATE push_subscriptions RESTART IDENTITY;` (or let 410/404 prune happen naturally over ~a week).
4. Users re-subscribe on next visit via the settings toggle.

### Push send failures

- `push_sender.send_push` logs each non-2xx with `status=<code>`. Expected codes:
  - **201 / 200** — delivered.
  - **410 Gone / 404** — subscription expired → auto-deleted.
  - **403** — invalid VAPID claim. Check `VAPID_SUBJECT` is a valid `mailto:` / `https://` URL.
  - **413** — payload too large (>4 KB encrypted). Trim the notification body.

### iOS limitation

- Push works **only** when the user has installed the PWA via "홈 화면에 추가". The settings UI surfaces this; `InstallBanner` + `IosInstallGuide` nudge users toward installing.
- iOS 16.4+ required.

---

## 3. Offline persistence

### TanStack Query persister

- Storage: `localStorage["wealth-query-cache"]`, throttled at 1s.
- TTL: 24h (older snapshots discarded on hydrate).
- Persisted query key prefixes: `portfolios`, `portfolios-with-prices`, `holdings`, `analytics`.
- To expand: edit `PERSIST_QUERY_PREFIXES` in `components/QueryProvider.tsx`.

### Clearing offline data

- In-app: the SW kill-switch above also clears `localStorage` if you add `localStorage.clear()`.
- User-side: settings → 알림 → unsubscribe + browser clear site data.

---

## 4. Install prompt lifecycle

- `beforeinstallprompt` captured by `useInstallPrompt`. `InstallBanner` shows on visit 2+ if not dismissed and not already installed.
- 30-day dismissal cooldown stored in `localStorage["install-banner-dismissed-at"]`.
- If a user rejects the native prompt, the OS-level cooldown kicks in too — we won't see `beforeinstallprompt` again for weeks. The iOS guide modal has no such cooldown.

---

## 5. Related files

- `public/sw.js`
- `src/app/manifest.ts`
- `src/app/layout.tsx` (viewport + apple-web-app metadata)
- `src/components/ServiceWorkerUpdateToast.tsx`
- `src/components/QueryProvider.tsx`
- `src/hooks/useInstallPrompt.ts`, `useWebPush.ts`
- `backend/app/api/push.py`, `services/push_sender.py`, `models/push_subscription.py`
