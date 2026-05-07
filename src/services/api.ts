// Public API client (chat SSE, scan, manifest, health). Auth-required routes live in userApi.ts.

import type { ManifestResponse, ScanResponse } from '../types';

export type ChatRole = 'user' | 'assistant' | 'system';
export interface ChatTurn { role: ChatRole; text: string; }
export type ChatEventKind = 'triage' | 'medicines' | 'token' | 'done' | 'error';
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

async function jsonOrThrow<T>(res: Response): Promise<T> {
    if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${body || res.statusText}`);
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
): Promise<void> {
    const body: Record<string, unknown> = { messages };
    if (profile && Object.keys(profile).length > 0) body.profile = profile;
    const res = await fetch(endpoint('/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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

