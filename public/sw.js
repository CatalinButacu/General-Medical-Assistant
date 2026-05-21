/**
 * Minimal service worker for Med Assist.
 *
 * Two jobs:
 *   1. Cache the app shell so the React entry loads when the user is on a
 *      flaky connection or fully offline. /chat and /scan still need the
 *      backend — we don't intercept those.
 *   2. Provide a foundation for future local notifications (cabinet expiry
 *      reminders, see UX14). The notification logic lives here so a single
 *      SW handles both concerns.
 *
 * Bumping CACHE_VERSION forces the install / activate cycle to flush the
 * old cache on the next page load. The Vite-hashed JS/CSS filenames mean
 * we mostly add new entries rather than overwrite old ones, but the shell
 * documents (index.html, the start URL) update in place — version bump
 * keeps those fresh.
 */

const CACHE_VERSION = 'med-assist-v1';
const APP_SHELL_URLS = [
    './',
    './index.html',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_VERSION).then((cache) => cache.addAll(APP_SHELL_URLS))
            .catch(() => { /* Best-effort: first load without network is acceptable to drop. */ })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    if (request.method !== 'GET') return;
    const url = new URL(request.url);

    // Never intercept the backend — /chat, /scan, /manifest, /health, /user/*,
    // /medicines/* all live on a different origin (the HF Space URL). Letting
    // them go straight to fetch() keeps the SSE stream alive.
    if (url.origin !== self.location.origin) return;

    // Network-first for navigations so a fresh deploy is visible immediately;
    // fall back to cached shell when offline.
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(() =>
                caches.match('./index.html').then((cached) => cached ?? Response.error())
            )
        );
        return;
    }

    // Cache-first for hashed static assets — they're immutable so a hit is safe.
    event.respondWith(
        caches.match(request).then((cached) =>
            cached
                ?? fetch(request).then((res) => {
                    if (res.ok && res.type !== 'opaque') {
                        const clone = res.clone();
                        caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone));
                    }
                    return res;
                })
        )
    );
});

// Reserved for UX14: cabinet-expiry reminders posted via postMessage from
// the page. self.registration.showNotification(...) lives here so the
// notification UI stays consistent across foreground / future background
// triggers.
self.addEventListener('message', (event) => {
    if (event.data?.type === 'show-notification') {
        const { title, body, tag } = event.data;
        self.registration.showNotification(title, {
            body,
            tag,
            icon: './icon-192.png',
            badge: './icon-192.png',
        });
    }
});
