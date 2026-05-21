// Public API client (chat SSE, scan, manifest, health). Auth-required routes live in userApi.ts.

import type { AlternativeMedicineDTO, ManifestResponse, ScanResponse } from '../types';

export type ChatRole = 'user' | 'assistant' | 'system';
export interface ChatTurn { role: ChatRole; text: string; }
export type ChatEventKind = 'intent' | 'triage' | 'medicines' | 'token' | 'done' | 'error';
export interface ChatEventPayload {
    text?: string;
    message?: string;
    items?: unknown[];
    [key: string]: unknown;
}
export type ChatEventHandler = (kind: ChatEventKind, payload: ChatEventPayload) => void;

export interface ChatProfilePayload {
    age?: number;
    gender?: 'male' | 'female' | 'other';
    isPregnant?: boolean;
    allergies?: string[];
    conditions?: string[];
    medications?: string[];
}

const RAW_BACKEND = import.meta.env.VITE_BACKEND_URL ?? '';
export const API_BASE_URL = RAW_BACKEND.replace(/\/$/, '');

export function isApiConfigured(): boolean {
    return Boolean(API_BASE_URL);
}

function endpoint(path: string): string {
    return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

/**
 * Map an HTTP failure to a Romanian-language user message + a retry hint.
 *
 * - 429 (rate-limited) reads the `Retry-After` header so the UI can show
 *   "încearcă din nou în N secunde" precisely rather than guessing.
 * - 5xx is the "we're broken, our fault" bucket. Worth auto-retrying.
 * - 4xx (other) is the "your request was wrong" bucket. Don't auto-retry.
 *
 * Returned `retryAfterSec` is undefined when retry isn't appropriate.
 */
export interface HttpProblem {
    status: number;
    message: string;
    retryAfterSec?: number;
}

export class ApiError extends Error {
    readonly problem: HttpProblem;
    constructor(problem: HttpProblem) {
        super(problem.message);
        this.problem = problem;
    }
}

function explainStatus(status: number, retryAfterHeader: string | null): HttpProblem {
    if (status === 429) {
        const sec = Number(retryAfterHeader);
        const retryAfterSec = Number.isFinite(sec) && sec > 0 ? sec : 30;
        return {
            status,
            retryAfterSec,
            message: `Prea multe cereri într-un timp scurt. Încearcă din nou în ${retryAfterSec}s.`,
        };
    }
    if (status >= 500) {
        return {
            status,
            retryAfterSec: 2,
            message: 'Serverul are o problemă temporară. Încercăm din nou…',
        };
    }
    if (status === 401 || status === 403) {
        return { status, message: 'Sesiunea ta a expirat. Reîncărcă pagina sau autentifică-te din nou.' };
    }
    if (status === 400) {
        return { status, message: 'Cererea nu a putut fi procesată. Verifică ce ai trimis.' };
    }
    return { status, message: `Eroare neașteptată (${status}). Reîncearcă peste câteva secunde.` };
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
    if (!res.ok) {
        throw new ApiError(explainStatus(res.status, res.headers.get('retry-after')));
    }
    return res.json() as Promise<T>;
}

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

export async function fetchAlternatives(medicineId: string, limit = 5): Promise<AlternativeMedicineDTO[]> {
    const res = await fetch(endpoint(`/medicines/${encodeURIComponent(medicineId)}/alternatives?limit=${limit}`), {
        method: 'GET',
    });
    return jsonOrThrow<AlternativeMedicineDTO[]>(res);
}

export async function submitChatFeedback(requestId: string, helpful: boolean): Promise<void> {
    const res = await fetch(endpoint('/chat/feedback'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId, helpful }),
    });
    if (!res.ok) {
        throw new ApiError(explainStatus(res.status, res.headers.get('retry-after')));
    }
}

export async function scanMedicine(imageDataUrl: string): Promise<ScanResponse> {
    const mimeMatch = imageDataUrl.match(/^data:(image\/(jpeg|png|webp));base64,/);
    const mime_type = mimeMatch ? mimeMatch[1] : 'image/jpeg';
    const res = await fetch(endpoint('/scan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageDataUrl, mime_type }),
    });
    return jsonOrThrow<ScanResponse>(res);
}

export async function streamChat(
    messages: ChatTurn[],
    onEvent: ChatEventHandler,
    signal?: AbortSignal,
    profile?: ChatProfilePayload,
    skipFollowups = false,
): Promise<void> {
    const body: Record<string, unknown> = { messages };
    if (profile && Object.keys(profile).length > 0) body.profile = profile;
    if (skipFollowups) body.skip_followups = true;
    const res = await fetch(endpoint('/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal,
    });
    if (!res.ok) {
        throw new ApiError(explainStatus(res.status, res.headers.get('retry-after')));
    }
    if (!res.body) throw new Error('Răspunsul streamingului este gol.');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

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

