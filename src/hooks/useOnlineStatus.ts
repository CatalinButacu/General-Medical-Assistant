/**
 * Lightweight wrapper around `navigator.onLine` + the online/offline events.
 * `navigator.onLine` reports whether the device has *any* network, not
 * whether the backend is reachable — that's the job of api.checkHealth().
 * The hook is used by the AppOfflineBanner to surface 'no network' at the
 * page level so individual fetches don't have to each render their own
 * red bubble.
 */

import { useEffect, useState } from 'react';

export function useOnlineStatus(): boolean {
    const [online, setOnline] = useState(
        typeof navigator !== 'undefined' ? navigator.onLine : true,
    );

    useEffect(() => {
        const on = () => setOnline(true);
        const off = () => setOnline(false);
        window.addEventListener('online', on);
        window.addEventListener('offline', off);
        return () => {
            window.removeEventListener('online', on);
            window.removeEventListener('offline', off);
        };
    }, []);

    return online;
}
