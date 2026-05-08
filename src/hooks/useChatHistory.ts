/**
 * Owns chat-history state for the signed-in user. Anonymous chats stay ephemeral —
 * if `enabled` is false (no auth), every method is a no-op so callers don't need
 * to branch on auth state.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useUserApi } from './useUserApi';
import {
    userPaths,
    type ChatMessageDTO,
    type ChatSessionDetail,
    type ChatSessionSummary,
} from '../services/userApi';

interface UseChatHistory {
    enabled: boolean;
    sessions: ChatSessionSummary[];
    currentSessionId: string | null;
    refresh: () => Promise<void>;
    /** Persist one message; lazily creates the session on the first call. */
    persistMessage: (role: 'user' | 'assistant', text: string) => Promise<void>;
    loadSession: (id: string) => Promise<ChatMessageDTO[]>;
    deleteSession: (id: string) => Promise<void>;
    startNewSession: () => void;
}

export function useChatHistory(): UseChatHistory {
    const { isAuthenticated } = useAuth0();
    const apiCall = useUserApi();

    const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

    // Tracks an in-flight session creation so two near-simultaneous user messages
    // don't race and create two sessions.
    const creatingRef = useRef<Promise<string> | null>(null);

    const refresh = useCallback(async () => {
        if (!isAuthenticated) return;
        try {
            const list = await apiCall<ChatSessionSummary[]>(userPaths.chats);
            setSessions(list);
        } catch (err) {
            console.warn('chat-history list failed', err);
        }
    }, [apiCall, isAuthenticated]);

    useEffect(() => { void refresh(); }, [refresh]);

    const ensureSession = useCallback(async (): Promise<string> => {
        if (currentSessionId) return currentSessionId;
        if (creatingRef.current) return creatingRef.current;
        const p = (async () => {
            const created = await apiCall<ChatSessionSummary>(userPaths.chats, {
                method: 'POST',
                body: JSON.stringify({}),
            });
            setCurrentSessionId(created.id);
            return created.id;
        })();
        creatingRef.current = p;
        try {
            return await p;
        } finally {
            creatingRef.current = null;
        }
    }, [apiCall, currentSessionId]);

    const persistMessage = useCallback(async (role: 'user' | 'assistant', text: string) => {
        if (!isAuthenticated) return;
        const trimmed = text.trim();
        if (!trimmed) return;
        try {
            const sid = await ensureSession();
            await apiCall(userPaths.chatMessages(sid), {
                method: 'POST',
                body: JSON.stringify({ role, text: trimmed }),
            });
            void refresh();
        } catch (err) {
            // Persistence failure must not break the chat experience.
            console.warn('chat-history persist failed', err);
        }
    }, [apiCall, ensureSession, isAuthenticated, refresh]);

    const loadSession = useCallback(async (id: string): Promise<ChatMessageDTO[]> => {
        const detail = await apiCall<ChatSessionDetail>(userPaths.chat(id));
        setCurrentSessionId(id);
        return detail.messages;
    }, [apiCall]);

    const deleteSession = useCallback(async (id: string) => {
        await apiCall(userPaths.chat(id), { method: 'DELETE' });
        if (id === currentSessionId) setCurrentSessionId(null);
        await refresh();
    }, [apiCall, currentSessionId, refresh]);

    const startNewSession = useCallback(() => {
        setCurrentSessionId(null);
    }, []);

    return {
        enabled: isAuthenticated,
        sessions,
        currentSessionId,
        refresh,
        persistMessage,
        loadSession,
        deleteSession,
        startNewSession,
    };
}
