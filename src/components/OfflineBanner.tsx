/**
 * Sticky offline indicator. Shows when the browser reports navigator.onLine=false.
 * Doesn't try to *test* backend reachability — that's already covered by
 * checkHealth() in the chat page. This banner is for the 'phone walked out
 * of WiFi range' case where the user would otherwise wonder why nothing
 * responds.
 */

import { WifiOff } from 'lucide-react';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

export function OfflineBanner() {
    const online = useOnlineStatus();
    if (online) return null;
    return (
        <div
            role="status"
            aria-live="polite"
            className="fixed top-0 inset-x-0 z-[60] bg-red-600 text-white text-center py-1.5 text-[11px] font-bold uppercase tracking-widest shadow-md flex items-center justify-center gap-2"
        >
            <WifiOff size={12} />
            Fără conexiune la internet
        </div>
    );
}
