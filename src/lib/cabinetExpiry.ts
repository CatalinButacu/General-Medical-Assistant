/**
 * Cabinet-expiry notifications.
 *
 * Limit of the deployment (free HF Space + GitHub Pages): no scheduled
 * server cron. So we use the next-best thing — local notifications fired
 * on app open via the registered service worker. The user has to launch
 * the app for them to fire, but most do daily anyway.
 *
 * Behaviour:
 *  - Run after the MedicineCabinet page loads (so we have the list of items).
 *  - For each item where 0 <= daysUntil <= EXPIRY_WARN_DAYS, fire a
 *    notification — unless one for that same (id, daysUntil) was already
 *    fired today (deduped via localStorage).
 *  - Permission is requested ONCE on first cabinet load, in a polite
 *    user-gesture context (button click), not implicitly.
 *
 * A future enhancement would be a real Web Push setup with a backend cron;
 * that needs VAPID keys + a subscription table and is out of scope here.
 */

const PERMISSION_ASKED_KEY = 'med_assist_notif_permission_asked';
const NOTIF_DEDUPE_KEY = 'med_assist_notif_dedupe';
const EXPIRY_WARN_DAYS = 30;

interface DedupeRecord {
    [itemKey: string]: string; // YYYY-MM-DD of last fire
}

function todayISO(): string {
    return new Date().toISOString().slice(0, 10);
}

function loadDedupe(): DedupeRecord {
    try {
        const raw = localStorage.getItem(NOTIF_DEDUPE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function saveDedupe(d: DedupeRecord): void {
    try { localStorage.setItem(NOTIF_DEDUPE_KEY, JSON.stringify(d)); } catch { /* private mode */ }
}

export function hasAskedForPermission(): boolean {
    try { return localStorage.getItem(PERMISSION_ASKED_KEY) === '1'; }
    catch { return true; }
}

export async function requestNotificationPermission(): Promise<NotificationPermission | 'unsupported'> {
    if (typeof Notification === 'undefined') return 'unsupported';
    try { localStorage.setItem(PERMISSION_ASKED_KEY, '1'); } catch { /* private mode */ }
    if (Notification.permission === 'granted' || Notification.permission === 'denied') {
        return Notification.permission;
    }
    return Notification.requestPermission();
}

interface CabinetItemForNotif {
    id: string;
    name: string;
    daysUntilExpiration?: number;
    isExpired?: boolean;
}

export async function fireExpiryNotifications(items: CabinetItemForNotif[]): Promise<number> {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return 0;
    const reg = await navigator.serviceWorker?.getRegistration();
    if (!reg) return 0;

    const dedupe = loadDedupe();
    const today = todayISO();
    let fired = 0;

    for (const item of items) {
        const days = item.daysUntilExpiration;
        if (days === undefined) continue;
        if (item.isExpired) {
            const key = `expired:${item.id}`;
            if (dedupe[key] === today) continue;
            reg.showNotification('Medicament expirat', {
                body: `${item.name} a expirat. Verifică-l în cabinet.`,
                tag: key,
                icon: './icon-192.png',
            });
            dedupe[key] = today;
            fired += 1;
            continue;
        }
        if (days <= EXPIRY_WARN_DAYS) {
            // Bucket the warning by 5-day windows so we don't fire one notification
            // per day for the same item — only when the bucket changes.
            const bucket = Math.floor(days / 5) * 5;
            const key = `expiring:${item.id}:${bucket}`;
            if (dedupe[key] === today) continue;
            reg.showNotification('Medicament expiră curând', {
                body: `${item.name} expiră în ${days} ${days === 1 ? 'zi' : 'zile'}.`,
                tag: key,
                icon: './icon-192.png',
            });
            dedupe[key] = today;
            fired += 1;
        }
    }

    saveDedupe(dedupe);
    return fired;
}
