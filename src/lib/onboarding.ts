// Non-component helpers for the first-launch tour. Lives next to the
// component but in a separate file so Vite's Fast Refresh stays happy
// (one component per module, no co-exported runtime helpers).

export const TOUR_DONE_KEY = 'med_assist_onboarding_seen';

export function shouldShowOnboarding(): boolean {
    if (typeof window === 'undefined') return false;
    try { return localStorage.getItem(TOUR_DONE_KEY) !== '1'; }
    catch { return false; }
}
