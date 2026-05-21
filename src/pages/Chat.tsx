import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { LogIn, Sparkles, X } from 'lucide-react';
import { ApiError, checkHealth, isApiConfigured, streamChat } from '../services/api';
import type { ChatProfilePayload, ChatTurn } from '../services/api';
import { toast } from 'sonner';
import { useUserApi } from '../hooks/useUserApi';
import { useChatHistory } from '../hooks/useChatHistory';
import { userPaths, type ProfileDTO } from '../services/userApi';
import type { IntentEvent, MedicineDTO, Message, TriageEvent } from '../types';
import { ChatHeader } from '../components/chat/ChatHeader';
import { HistoryDrawer } from '../components/chat/HistoryDrawer';
import { MessageBubble } from '../components/chat/MessageBubble';
import { Composer } from '../components/chat/Composer';
import { exportConversation } from '../lib/exportConversation';

const QUICK_QUERIES = [
    { label: 'durere de cap',     query: 'mă doare capul și am febră' },
    { label: 'tuse productivă',   query: 'tuse productivă cu secreții' },
    { label: 'nas înfundat',      query: 'nas înfundat de la răceală' },
    { label: 'arsuri stomac',     query: 'am arsuri la stomac' },
    { label: 'alergie',           query: 'alergie cu mâncărime' },
    { label: 'diaree',            query: 'mă doare burta și am diaree' },
];

const HISTORY_TURNS_TO_SEND = 6;

const SAVE_PROMPT_DISMISSED_KEY = 'med_assist_save_prompt_dismissed';

export default function Chat() {
    const navigate = useNavigate();
    const { user, loginWithRedirect } = useAuth0();
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const abortRef = useRef<AbortController | null>(null);
    const profileRef = useRef<ChatProfilePayload | undefined>(undefined);

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isOnline, setIsOnline] = useState<boolean | null>(null);
    const [historyOpen, setHistoryOpen] = useState(false);
    const [savePromptDismissed, setSavePromptDismissed] = useState(() => {
        if (typeof window === 'undefined') return false;
        try { return localStorage.getItem(SAVE_PROMPT_DISMISSED_KEY) === '1'; }
        catch { return false; }
    });

    // Show the 'log in to save this conversation' banner only when the user
    // is anonymous AND has had 2+ real turns AND hasn't dismissed it before.
    // Two-turns gate prevents the banner from flashing on the welcome screen.
    const showSavePrompt = useMemo(() => {
        if (user || savePromptDismissed) return false;
        const realUserTurns = messages.filter(m => m.id !== 'welcome' && m.sender === 'user').length;
        return realUserTurns >= 2;
    }, [user, savePromptDismissed, messages]);

    const dismissSavePrompt = () => {
        setSavePromptDismissed(true);
        try { localStorage.setItem(SAVE_PROMPT_DISMISSED_KEY, '1'); } catch { /* private mode */ }
    };

    const history = useChatHistory();
    const historyRef = useRef(history);
    historyRef.current = history;

    const welcomeMessage: Message = {
        id: 'welcome',
        sender: 'ai',
        timestamp: new Date(),
        text: isApiConfigured()
            ? 'Bună. Descrie-mi simptomele sau medicamentul care te interesează — îți răspund pe baza nomenclatorului ANMDM.'
            : 'Backendul nu este configurat. Setează VITE_BACKEND_URL în .env.local.',
    };

    useEffect(() => {
        setMessages([welcomeMessage]);
        let cancelled = false;
        checkHealth().then(ok => { if (!cancelled) setIsOnline(ok); });
        return () => { cancelled = true; abortRef.current?.abort(); };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const apiCall = useUserApi();
    useEffect(() => {
        if (!user?.sub) {
            profileRef.current = undefined;
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                const p = await apiCall<ProfileDTO>(userPaths.profile);
                if (cancelled) return;
                profileRef.current = {
                    age: p.age ?? undefined,
                    gender: p.gender ?? undefined,
                    isPregnant: p.isPregnant ?? undefined,
                    allergies: p.allergies ?? [],
                    conditions: p.conditions ?? [],
                    medications: p.medications ?? [],
                };
            } catch (err) {
                console.warn('profile load failed', err);
            }
        })();
        return () => { cancelled = true; };
    }, [user?.sub, apiCall]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async (queryText?: string) => {
        const text = (queryText ?? inputMessage).trim();
        if (!text || isStreaming) return;

        const userMsg: Message = {
            id: `u-${Date.now()}`,
            sender: 'user',
            timestamp: new Date(),
            text,
        };
        const aiId = `a-${Date.now()}`;
        const aiMsg: Message = {
            id: aiId,
            sender: 'ai',
            timestamp: new Date(),
            text: '',
            isStreaming: true,
            // Initial phase before any SSE event lands. Lets the bubble surface
            // 'Verific semnele de urgență…' immediately rather than typing-dots silence.
            streamPhase: 'scanning',
        };
        setMessages(prev => [...prev, userMsg, aiMsg]);
        setInputMessage('');
        setIsStreaming(true);
        void historyRef.current.persistMessage('user', text);

        // Build the conversation payload from the freshly-pushed history,
        // dropping the welcome bubble and any in-progress streaming placeholder.
        setMessages(latest => {
            const cleanForSend: ChatTurn[] = latest
                .filter(m => m.id !== 'welcome' && m.id !== aiId && (m.text ?? '').trim())
                .slice(-HISTORY_TURNS_TO_SEND)
                .map(m => ({
                    role: m.sender === 'user' ? 'user' : 'assistant',
                    text: (m.text ?? '').trim(),
                }));

            const controller = new AbortController();
            abortRef.current = controller;

            (async () => {
                try {
                    await streamChat(cleanForSend, (kind, payload) => {
                        setMessages(curr => curr.map(m => {
                            if (m.id !== aiId) return m;
                            switch (kind) {
                                case 'intent':
                                    return {
                                        ...m,
                                        intent: payload as unknown as IntentEvent,
                                        // Intent fired ⇒ red-flag scan didn't short-circuit; we're routing.
                                        streamPhase: 'classifying',
                                    };
                                case 'triage':
                                    return {
                                        ...m,
                                        triage: payload as unknown as TriageEvent,
                                        // Triage carries retrieval signal — searching is done by this point.
                                        streamPhase: (payload?.label === 'EMERGENCY') ? 'done' : 'searching',
                                    };
                                case 'medicines':
                                    return {
                                        ...m,
                                        medicines: (payload?.items ?? []) as unknown as MedicineDTO[],
                                        streamPhase: 'drafting',
                                    };
                                case 'token': {
                                    // Some LLM SDKs (incl. Gemini) sometimes emit cumulative
                                    // chunks where each one repeats everything so far rather
                                    // than just the delta. Detect that and replace instead of
                                    // appending — otherwise the UI would render "hello hello
                                    // world" when the stream sends "hello" then "hello world".
                                    const incoming = (payload?.text ?? '').toString();
                                    const existing = m.text ?? '';
                                    if (!incoming || incoming === existing) return m;
                                    if (incoming.length > existing.length && incoming.startsWith(existing)) {
                                        return { ...m, text: incoming, streamPhase: 'drafting' };
                                    }
                                    return { ...m, text: existing + incoming, streamPhase: 'drafting' };
                                }
                                case 'done': {
                                    const finalText = (m.text ?? '').trim();
                                    if (finalText) void historyRef.current.persistMessage('assistant', finalText);
                                    const citationValid = (payload?.citation_valid ?? null) as boolean | null;
                                    const requestId = (payload?.request_id ?? null) as string | null;
                                    return {
                                        ...m,
                                        isStreaming: false,
                                        streamPhase: 'done',
                                        citationValid,
                                        requestId,
                                    };
                                }
                                case 'error':
                                    return {
                                        ...m,
                                        isStreaming: false,
                                        streamPhase: 'done',
                                        error: (payload?.message as string) ?? 'unknown error',
                                    };
                                default:
                                    return m;
                            }
                        }));
                        if (kind === 'done' || kind === 'error') {
                            setIsOnline(true);
                            setIsStreaming(false);
                        }
                    }, controller.signal, profileRef.current);
                } catch (err) {
                    setIsOnline(false);
                    setIsStreaming(false);
                    // Map the error class to a human-readable Romanian message.
                    // ApiError already carries a localized message + retry hint;
                    // anything else is most likely a network outage on the client.
                    let msg: string;
                    if (err instanceof ApiError) {
                        msg = err.problem.message;
                    } else if (err instanceof Error && err.name === 'AbortError') {
                        msg = 'Conversație întreruptă.';
                    } else if (err instanceof Error) {
                        msg = 'Nu m-am putut conecta la server. Verifică conexiunea și încearcă din nou.';
                    } else {
                        msg = 'Eroare necunoscută. Reîncearcă peste câteva secunde.';
                    }
                    setMessages(curr => curr.map(m =>
                        m.id === aiId ? { ...m, isStreaming: false, streamPhase: 'done', error: msg } : m
                    ));
                }
            })();

            return latest;
        });
    };

    const handleQuickQuery = (q: string) => {
        setInputMessage(q);
        sendMessage(q);
    };

    // Only worth offering the export action after at least one real exchange.
    const realMessageCount = messages.filter(m => m.id !== 'welcome').length;
    const canExport = realMessageCount >= 2 && !isStreaming;

    const handleExport = async () => {
        if (!canExport) return;
        const result = await exportConversation(messages);
        if (result === 'shared') toast.success('Conversație partajată');
        else if (result === 'copied') toast.success('Conversația a fost copiată în clipboard');
        else if (result === 'downloaded') toast.success('Fișierul .md a fost descărcat');
        else if (result === 'unsupported') toast.error('Browserul nu permite această acțiune');
        // 'cancelled' is silent — the user explicitly dismissed the share sheet.
    };

    return (
        <div className="h-full flex flex-col">
            <ChatHeader
                onBack={() => navigate('/')}
                isOnline={isOnline}
                historyEnabled={history.enabled}
                sessionsCount={history.sessions.length}
                isStreaming={isStreaming}
                canExport={canExport}
                onNewSession={() => { history.startNewSession(); setMessages([welcomeMessage]); }}
                onOpenHistory={() => setHistoryOpen(true)}
                onExport={handleExport}
            />

            {historyOpen && (
                <HistoryDrawer
                    sessions={history.sessions}
                    currentId={history.currentSessionId}
                    onClose={() => setHistoryOpen(false)}
                    onPick={async (id) => {
                        try {
                            const msgs = await history.loadSession(id);
                            const loaded: Message[] = msgs.map(m => ({
                                id: m.id,
                                sender: m.role === 'user' ? 'user' : 'ai',
                                timestamp: new Date(m.created_at),
                                text: m.text,
                            }));
                            setMessages(loaded.length > 0 ? loaded : [welcomeMessage]);
                            setHistoryOpen(false);
                        } catch (err) {
                            console.warn('load session failed', err);
                        }
                    }}
                    onDelete={async (id) => {
                        await history.deleteSession(id);
                        if (id === history.currentSessionId) {
                            setMessages([welcomeMessage]);
                        }
                    }}
                />
            )}

            {showSavePrompt && (
                <div className="bg-blue-50 border-b border-blue-100 flex-shrink-0">
                    <div className="max-w-md mx-auto px-4 py-2.5 flex items-center gap-3">
                        <p className="flex-1 text-[11px] text-blue-900 font-medium leading-snug">
                            Conectează-te ca să salvezi această conversație și să o regăsești mai târziu.
                        </p>
                        <button
                            onClick={() => loginWithRedirect()}
                            className="flex items-center gap-1 bg-blue-600 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg shadow-sm shadow-blue-100 hover:bg-blue-700 transition-colors"
                        >
                            <LogIn size={12} />
                            Conectează-mă
                        </button>
                        <button
                            onClick={dismissSavePrompt}
                            className="p-1 text-blue-400 hover:text-blue-700 rounded"
                            aria-label="Închide acest mesaj"
                            title="Închide acest mesaj"
                        >
                            <X size={14} />
                        </button>
                    </div>
                </div>
            )}

            <div className="flex-1 overflow-y-auto">
                <div className="max-w-md mx-auto px-4 py-6 space-y-4">
                    {messages.map(message => (
                        <MessageBubble key={message.id} message={message} setMessages={setMessages} />
                    ))}

                    {messages.length === 1 && !isStreaming && (
                        <div className="pt-6 animate-in fade-in duration-700">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] ml-1">
                                    Acțiuni rapide
                                </h3>
                                <div className="h-[1px] flex-1 bg-gray-100 ml-4" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                {QUICK_QUERIES.map(({ label, query }) => (
                                    <button
                                        key={label}
                                        onClick={() => handleQuickQuery(query)}
                                        className="text-left p-3 bg-white border border-gray-100 rounded-2xl hover:border-blue-200 hover:shadow-md transition-all active:scale-[0.98]"
                                    >
                                        <div className="flex items-center mb-1">
                                            <Sparkles className="text-blue-500 mr-2 flex-shrink-0" size={14} />
                                            <span className="text-xs font-bold text-gray-700 capitalize">{label}</span>
                                        </div>
                                        <p className="text-[10px] text-gray-400 font-medium truncate">{query}</p>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            <Composer
                ref={inputRef}
                value={inputMessage}
                onChange={setInputMessage}
                onSubmit={() => sendMessage()}
                isStreaming={isStreaming}
            />
        </div>
    );
}
