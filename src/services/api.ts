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

import type { ManifestResponse, ScanResponse } from '../types';

export type ChatRole = 'user' | 'assistant' | 'system';
export interface ChatTurn { role: ChatRole; text: string; }
export type ChatEventKind = 'triage' | 'medicines' | 'token' | 'done' | 'error';
export type ChatEventHandler = (kind: ChatEventKind, payload: any) => void;

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
 * Identify a medicine from a captured photo. `imageDataUrl` is the
 * full result of `canvas.toDataURL('image/jpeg')` — the backend strips
 * the `data:image/jpeg;base64,` prefix automatically.
 */
export async function scanMedicine(imageDataUrl: string): Promise<ScanResponse> {
    // Detect mime type from the data URL header so PNG uploads still work.
    const mimeMatch = imageDataUrl.match(/^data:(image\/(jpeg|png|webp));base64,/);
    const mime_type = mimeMatch ? mimeMatch[1] : 'image/jpeg';
    const res = await fetch(endpoint('/scan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageDataUrl, mime_type }),
    });
    return jsonOrThrow<ScanResponse>(res);
}

/**
 * Streaming chat. Calls the SSE-format `POST /chat` and invokes onEvent
 * for every parsed event. Resolves when the stream ends cleanly,
 * rejects on transport / parse errors. The signal lets callers cancel
 * (e.g. user navigates away mid-stream).
 */
export async function streamChat(
    messages: ChatTurn[],
    onEvent: ChatEventHandler,
    signal?: AbortSignal,
): Promise<void> {
    const res = await fetch(endpoint('/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
        signal,
    });
    if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${body || res.statusText}`);
    }
    if (!res.body) throw new Error('streaming response has no body');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by a blank line; each event has
        // an `event: <kind>` line and one or more `data: <json>` lines.
        let sep: number;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
            const raw = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            const eventMatch = raw.match(/^event: (\S+)/m);
            const dataMatch = raw.match(/^data: (.+)$/m);
            if (!eventMatch || !dataMatch) continue;
            const kind = eventMatch[1] as ChatEventKind;
            try {
                onEvent(kind, JSON.parse(dataMatch[1]));
            } catch {
                onEvent('error', { message: 'malformed SSE payload' });
            }
        }
    }
}

