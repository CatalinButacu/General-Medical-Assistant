/**
 * Register Med Assist's service worker. Best-effort:
 *   - Only registers in production builds. Dev would clash with Vite HMR.
 *   - Scoped under the deployed base path (`/General-Medical-Assistant/`)
 *     so it never tries to handle requests outside the SPA's own routes.
 *   - Silently no-ops where Service Worker isn't available (Firefox PWA off,
 *     private browsing, http://localhost without secure context, etc.).
 */

export function registerServiceWorker(): void {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
    if (!import.meta.env.PROD) return;

    const base = import.meta.env.BASE_URL ?? '/';
    const swPath = `${base.replace(/\/$/, '')}/sw.js`;
    window.addEventListener('load', () => {
        navigator.serviceWorker.register(swPath, { scope: base }).catch(() => {
            // Registration failed — almost always private mode or http without HTTPS.
            // Not worth surfacing to the user; the app works fine without it.
        });
    });
}
