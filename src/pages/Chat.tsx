import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import {
    AlertTriangle,
    Bot,
    ExternalLink,
    Loader2,
    Phone,
    Send,
    Sparkles,
    User as UserIcon,
    Wifi,
    WifiOff,
    X,
    Zap,
} from 'lucide-react';
import { checkHealth, isApiConfigured, streamChat } from '../services/api';
import type { ChatProfilePayload, ChatTurn } from '../services/api';
import { useUserApi } from '../hooks/useUserApi';
import { userPaths, type ProfileDTO } from '../services/userApi';
import type { MedicineDTO, Message, RedFlagDTO, TriageEvent } from '../types';

const QUICK_QUERIES = [
    { label: 'durere de cap',     query: 'mă doare capul și am febră' },
    { label: 'tuse productivă',   query: 'tuse productivă cu secreții' },
    { label: 'nas înfundat',      query: 'nas înfundat de la răceală' },
    { label: 'arsuri stomac',     query: 'am arsuri la stomac' },
    { label: 'alergie',           query: 'alergie cu mâncărime' },
    { label: 'diaree',            query: 'mă doare burta și am diaree' },
];

const HISTORY_TURNS_TO_SEND = 6;

export default function Chat() {
    const navigate = useNavigate();
    const { user } = useAuth0();
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const abortRef = useRef<AbortController | null>(null);
    const profileRef = useRef<ChatProfilePayload | undefined>(undefined);

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isOnline, setIsOnline] = useState<boolean | null>(null);

    useEffect(() => {
        setMessages([{
            id: 'welcome',
            sender: 'ai',
            timestamp: new Date(),
            text: isApiConfigured()
                ? 'Salut. Spune-mi ce simptome ai sau ce medicament cauți. Răspund din nomenclatorul ANMDM.'
                : 'Backend not configured. Set VITE_BACKEND_URL in .env.local.',
        }]);
        let cancelled = false;
        checkHealth().then(ok => { if (!cancelled) setIsOnline(ok); });
        return () => { cancelled = true; abortRef.current?.abort(); };
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
        };
        setMessages(prev => [...prev, userMsg, aiMsg]);
        setInputMessage('');
        setIsStreaming(true);

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
                                case 'triage':
                                    return { ...m, triage: payload as TriageEvent };
                                case 'medicines':
                                    return { ...m, medicines: (payload?.items ?? []) as MedicineDTO[] };
                                case 'token': {
                                    // Some LLM SDKs (incl. Gemini) sometimes emit
                                    // cumulative chunks where each one includes
                                    // everything so far rather than just the delta.
                                    // Detect that and replace instead of appending,
                                    // so we don't render "hello hello world" when
                                    // the stream sends "hello" then "hello world".
                                    const incoming = (payload?.text ?? '').toString();
                                    const existing = m.text ?? '';
                                    if (!incoming || incoming === existing) return m;
                                    if (incoming.length > existing.length && incoming.startsWith(existing)) {
                                        return { ...m, text: incoming };
                                    }
                                    return { ...m, text: existing + incoming };
                                }
                                case 'done':
                                    return { ...m, isStreaming: false };
                                case 'error':
                                    return { ...m, isStreaming: false, error: payload?.message ?? 'unknown error' };
                                default:
                                    return m;
                            }
                        }));
                        if (kind === 'done' || kind === 'error') {
                            setIsOnline(true);
                            setIsStreaming(false);
                        }
                    }, controller.signal, profileRef.current);
                } catch (err: any) {
                    setIsOnline(false);
                    setIsStreaming(false);
                    setMessages(curr => curr.map(m =>
                        m.id === aiId ? { ...m, isStreaming: false, error: err?.message ?? 'unknown' } : m
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

    return (
        <div className="h-full flex flex-col">
            <header className="bg-white border-b border-gray-100 shadow-sm flex-shrink-0">
                <div className="max-w-md mx-auto px-4 py-3 flex items-center justify-between">
                    <button
                        onClick={() => navigate('/')}
                        className="p-2 -ml-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800"
                        aria-label="Înapoi"
                    >
                        <X size={20} />
                    </button>
                    <div className="flex items-center space-x-3">
                        <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-lg shadow-blue-100">
                            <Bot className="text-white" size={18} />
                        </div>
                        <div>
                            <h1 className="text-base font-bold text-gray-800 leading-none">Asistent Medical</h1>
                            <div className="flex items-center mt-1.5">
                                {isOnline === null ? (
                                    <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex items-center">
                                        <Loader2 className="w-2.5 h-2.5 mr-1 animate-spin" /> Conectare…
                                    </span>
                                ) : isOnline ? (
                                    <span className="text-[9px] font-bold text-green-600 uppercase tracking-widest flex items-center bg-green-50 px-1.5 py-0.5 rounded-full">
                                        <Wifi className="w-2.5 h-2.5 mr-1" /> Online
                                    </span>
                                ) : (
                                    <span className="text-[9px] font-bold text-red-600 uppercase tracking-widest flex items-center bg-red-50 px-1.5 py-0.5 rounded-full">
                                        <WifiOff className="w-2.5 h-2.5 mr-1" /> Offline
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="w-9 h-9" />
                </div>
            </header>

            <div className="flex-1 overflow-y-auto">
                <div className="max-w-md mx-auto px-4 py-6 space-y-4">
                    {messages.map(message => (
                        <MessageBubble key={message.id} message={message} />
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

            <footer className="bg-white border-t border-gray-100 flex-shrink-0">
                <div className="max-w-md mx-auto px-4 py-3">
                    <div className="relative">
                        <textarea
                            ref={inputRef}
                            rows={1}
                            value={inputMessage}
                            onChange={e => setInputMessage(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    sendMessage();
                                }
                            }}
                            placeholder="Descrie simptomele…"
                            className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 text-sm resize-none transition-all placeholder:text-gray-400"
                            disabled={isStreaming}
                        />
                        <button
                            onClick={() => sendMessage()}
                            disabled={!inputMessage.trim() || isStreaming}
                            className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2 rounded-xl hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md active:scale-90"
                            aria-label="Trimite"
                        >
                            {isStreaming ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                        </button>
                    </div>
                    <div className="flex items-center justify-center mt-2 space-x-1.5">
                        <AlertTriangle className="text-amber-500" size={10} />
                        <p className="text-[9px] text-gray-400 font-bold uppercase tracking-tight">
                            Demo educativ • Verifică recomandările cu farmacistul
                        </p>
                    </div>
                </div>
            </footer>
        </div>
    );
}

function MessageBubble({ message }: { message: Message }) {
    const isUser = message.sender === 'user';
    const time = new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    return (
        <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
            <div className={`flex items-start space-x-3 max-w-[92%] ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm ${
                    isUser ? 'bg-blue-600' : 'bg-white border border-gray-100'
                }`}>
                    {isUser
                        ? <UserIcon className="text-white" size={16} />
                        : <Bot className="text-blue-600" size={16} />
                    }
                </div>

                <div className="flex-1 min-w-0 space-y-2">
                    {isUser ? (
                        <div className="rounded-2xl px-4 py-3 shadow-sm bg-gradient-to-br from-blue-600 to-indigo-700 text-white">
                            <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">{message.text}</p>
                        </div>
                    ) : (
                        <AssistantMessage message={message} />
                    )}
                    <div className={`text-[9px] font-bold uppercase tracking-tight text-gray-300 ${isUser ? 'text-right pr-1' : 'pl-1'}`}>
                        {time}
                    </div>
                </div>
            </div>
        </div>
    );
}

function AssistantMessage({ message }: { message: Message }) {
    const triage = message.triage;

    // Emergency short-circuits the whole layout — no LLM text, no medicine grid.
    if (triage?.label === 'EMERGENCY') {
        return <EmergencyCard triage={triage} />;
    }

    return (
        <>
            {/* The LLM text bubble. Always visible (even if just a typing indicator). */}
            <TextBubble
                text={message.text}
                isStreaming={!!message.isStreaming}
                error={message.error}
            />
            {triage?.label === 'UNCERTAIN' && triage.recommended_action_ro && (
                <UncertainAction triage={triage} />
            )}
            {message.medicines && message.medicines.length > 0 && (
                <MedicineGrid medicines={message.medicines} />
            )}
        </>
    );
}

function TextBubble({ text, isStreaming, error }: { text?: string; isStreaming: boolean; error?: string }) {
    if (error) {
        return (
            <div className="rounded-2xl px-4 py-3 shadow-sm bg-red-50 border border-red-200 text-red-800 text-sm">
                {error}
            </div>
        );
    }
    if (!text && isStreaming) {
        return (
            <div className="rounded-2xl px-4 py-3 shadow-sm bg-white border border-gray-100">
                <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" />
                    <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.2s]" />
                    <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
            </div>
        );
    }
    return (
        <div className="rounded-2xl px-4 py-3 shadow-sm bg-white border border-gray-100 text-gray-800">
            <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">
                {text}
                {isStreaming && <span className="inline-block w-1 h-4 ml-0.5 bg-blue-500 align-middle animate-pulse" />}
            </p>
        </div>
    );
}

function EmergencyCard({ triage }: { triage: TriageEvent }) {
    return (
        <div className="rounded-2xl border-2 border-red-300 bg-gradient-to-br from-red-50 to-white shadow-md overflow-hidden">
            <div className="bg-red-600 text-white px-4 py-3 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <AlertTriangle size={20} />
                    <span className="font-bold text-sm uppercase tracking-wider">URGENȚĂ</span>
                </div>
            </div>
            <div className="p-4 space-y-3">
                <p className="text-sm font-bold text-red-900 leading-relaxed">{triage.recommended_action_ro}</p>
                {triage.red_flags.map(flag => (
                    <RedFlagBadge key={flag.name} flag={flag} />
                ))}
                <a
                    href="tel:112"
                    className="flex items-center justify-center space-x-2 w-full bg-red-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-red-200 hover:bg-red-700 active:scale-[0.98] transition-all"
                >
                    <Phone size={18} />
                    <span>Sună 112</span>
                </a>
                <p className="text-[10px] text-red-700 italic text-center px-2 leading-relaxed">{triage.rationale}</p>
            </div>
        </div>
    );
}

function RedFlagBadge({ flag }: { flag: RedFlagDTO }) {
    return (
        <div className="bg-white border border-red-200 rounded-xl px-3 py-2 text-xs">
            <div className="flex items-start">
                <Zap size={12} className="text-red-600 mr-1.5 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                    <p className="font-semibold text-red-900">{flag.description}</p>
                    <p className="text-[10px] text-red-600 mt-0.5 font-mono truncate">
                        {flag.severity} · «{flag.matched_pattern}»
                    </p>
                </div>
            </div>
        </div>
    );
}

function UncertainAction({ triage }: { triage: TriageEvent }) {
    return (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start">
            <AlertTriangle size={14} className="text-amber-600 mr-2 mt-0.5 flex-shrink-0" />
            <p className="text-[11px] text-amber-800 leading-relaxed">{triage.recommended_action_ro}</p>
        </div>
    );
}

function MedicineGrid({ medicines }: { medicines: MedicineDTO[] }) {
    return (
        <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-b border-green-100 px-4 py-2 flex items-center">
                <Sparkles size={12} className="text-green-600 mr-2" />
                <span className="font-bold text-[11px] text-green-900 uppercase tracking-wider">
                    Medicamente · {medicines.length}
                </span>
            </div>
            <div className="p-3 space-y-2.5">
                {medicines.map(med => (
                    <MedicineRow key={`${med.trade_name}-${med.atc_code}`} med={med} />
                ))}
            </div>
        </div>
    );
}

function MedicineRow({ med }: { med: MedicineDTO }) {
    const rxBadgeColor = med.rx_status === 'OTC'
        ? 'bg-green-100 text-green-700'
        : med.rx_status === 'MIXED'
            ? 'bg-amber-100 text-amber-700'
            : 'bg-red-100 text-red-700';
    return (
        <div className="rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:border-blue-200 hover:shadow-sm transition-all p-3">
            <div className="flex items-start justify-between gap-2 mb-1">
                <div className="font-bold text-sm text-gray-800 leading-tight">{med.trade_name}</div>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${rxBadgeColor} flex-shrink-0`}>
                    {med.rx_status}
                </span>
            </div>
            <div className="text-[11px] text-gray-500 font-medium">
                {med.dci} · <span className="font-mono">{med.atc_code}</span> · {med.form.toLowerCase()} {med.concentration}
            </div>
            {med.category && (
                <div className="text-[11px] text-blue-600 font-semibold mt-1">{med.category}</div>
            )}
            {med.lay_symptoms.length > 0 && (
                <div className="text-[11px] text-gray-600 mt-1.5 leading-relaxed">
                    <span className="text-gray-400">pentru:</span> {med.lay_symptoms.join(', ')}
                </div>
            )}
            <div className="flex items-center gap-3 mt-2">
                {med.prospect_url && (
                    <a
                        href={med.prospect_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 text-[10px] font-semibold text-blue-600 hover:text-blue-800"
                    >
                        <ExternalLink size={10} />
                        <span>prospect</span>
                    </a>
                )}
                {med.rcp_url && (
                    <a
                        href={med.rcp_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 text-[10px] font-semibold text-gray-500 hover:text-blue-700"
                    >
                        <ExternalLink size={10} />
                        <span>RCP</span>
                    </a>
                )}
                <span className="ml-auto text-[10px] font-mono text-gray-300">{med.score.toFixed(3)}</span>
            </div>
        </div>
    );
}
