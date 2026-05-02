/**
 * API client for the med_assist FastAPI backend (med_assist/api/main.py).
 *
 * Local dev:   set VITE_BACKEND_URL=http://localhost:8000 in .env.local
 * Production:  set VITE_BACKEND_URL=https://your-aws-deploy-url
 *
 * If VITE_BACKEND_URL is unset we fall back to same-origin requests, which
 * is what the production build will use when the static frontend is served
 * by the same gateway as the API.
 */

import type { AdviseRequest, AdviseResponse, ManifestResponse } from '../types';

const RAW_BACKEND = import.meta.env.VITE_BACKEND_URL ?? '';
export const API_BASE_URL = RAW_BACKEND.replace(/\/$/, '');

/** True when an explicit backend URL is configured. */
export function isApiConfigured(): boolean {
    return Boolean(API_BASE_URL);
}

function endpoint(path: string): string {
    return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
    if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${body || res.statusText}`);
    }
    return res.json() as Promise<T>;
}

/**
 * End-to-end triage + recommendation. The single call the chat UI needs.
 */
export async function advise(request: AdviseRequest): Promise<AdviseResponse> {
    const body: AdviseRequest = {
        query: request.query,
        otc_only: request.otc_only ?? true,
        top_k: request.top_k ?? 5,
    };
    const res = await fetch(endpoint('/advise'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return jsonOrThrow<AdviseResponse>(res);
}

/**
 * Backend liveness probe + index metadata. Cheap, used by status indicators.
 */
export async function checkHealth(): Promise<boolean> {
    try {
        const res = await fetch(endpoint('/health'), {
            method: 'GET',
            signal: AbortSignal.timeout(3000),
        });
        return res.ok;
    } catch {
        return false;
    }
}

export async function getManifest(): Promise<ManifestResponse> {
    const res = await fetch(endpoint('/manifest'), { method: 'GET' });
    return jsonOrThrow<ManifestResponse>(res);
}

/**
 * Legacy text-only API used by older components (CameraScanner result page,
 * MedicineCabinet add-flow). Calls /advise and serializes the top medicines
 * back into a markdown blob so existing callers keep working without changes.
 */
export async function searchMedicines(query: string): Promise<string> {
    const decision = await advise({ query, top_k: 5 });
    if (decision.label === 'EMERGENCY') {
        const action = decision.recommended_action_ro || 'Sunați 112 imediat.';
        const flags = decision.red_flags.map(f => `- ${f.description}`).join('\n');
        return `⚠️ URGENȚĂ\n\n${action}\n\nSemnale detectate:\n${flags}`;
    }
    if (!decision.medicines.length) {
        return decision.rationale || 'Nu am găsit medicamente potrivite. Consultați un farmacist.';
    }
    const lines = decision.medicines.map(m => {
        const status = m.rx_status === 'OTC' ? '✅ OTC' : '⚠️ Rx';
        return `**${m.trade_name}** (${m.dci}) — ${status}\n  ${m.category}`;
    });
    return `## Rezultate pentru: ${query}\n\n${lines.join('\n\n')}\n\n*${decision.rationale}*`;
}
