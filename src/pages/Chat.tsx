import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { advise, checkHealth, isApiConfigured } from '../services/api';
import type { AdviseResponse, MedicineDTO, Message, RedFlagDTO } from '../types';

const QUICK_QUERIES: { label: string; query: string; icon: typeof Sparkles }[] = [
    { label: 'durere de cap',     query: 'mă doare capul și am febră',                        icon: Sparkles },
    { label: 'tuse productivă',   query: 'tuse productivă cu secreții',                       icon: Sparkles },
    { label: 'nas înfundat',      query: 'nas înfundat de la răceală',                        icon: Sparkles },
    { label: 'arsuri stomac',     query: 'am arsuri la stomac',                                icon: Sparkles },
    { label: 'alergie',           query: 'alergie cu mâncărime',                               icon: Sparkles },
    { label: 'diaree',            query: 'mă doare burta și am diaree',                        icon: Sparkles },
];

export default function Chat() {
    const navigate = useNavigate();
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isOnline, setIsOnline] = useState<boolean | null>(null);

    useEffect(() => {
        setMessages([{
            id: 'welcome',
            sender: 'ai',
            timestamp: new Date(),
            text: isApiConfigured()
                ? 'Salut. Descrie simptomele tale sau întreabă despre un medicament. Răspund din nomenclatorul ANMDM.'
                : 'Backend not configured. Set VITE_BACKEND_URL in .env.local — see README.',
        }]);
        let cancelled = false;
        checkHealth().then(ok => { if (!cancelled) setIsOnline(ok); });
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const sendMessage = async (queryText?: string) => {
        const text = (queryText ?? inputMessage).trim();
        if (!text || isLoading) return;

        setMessages(prev => [...prev, {
            id: `u-${Date.now()}`,
            sender: 'user',
            timestamp: new Date(),
            text,
        }]);
        setInputMessage('');
        setIsLoading(true);

        try {
            const response = await advise({ query: text, top_k: 5, otc_only: true });
            setIsOnline(true);
            setMessages(prev => [...prev, {
                id: `a-${Date.now()}`,
                sender: 'ai',
                timestamp: new Date(),
                advise: response,
            }]);
        } catch (err: any) {
            setIsOnline(false);
            setMessages(prev => [...prev, {
                id: `a-${Date.now()}`,
                sender: 'ai',
                timestamp: new Date(),
                text: `Backend indisponibil. ${err?.message ?? 'Eroare necunoscută'}.\n\nVerifică VITE_BACKEND_URL și că serverul uvicorn rulează.`,
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleQuickQuery = (query: string) => {
        setInputMessage(query);
        sendMessage(query);
    };

    return (
        // Chat fills the App's <main> content area (which already reserves
        // pb-24 for MobileNavigation), so input sits right above the bottom nav.
        // Background is inherited from App's gradient.
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

                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="flex items-start space-x-3">
                                <div className="w-8 h-8 rounded-xl bg-white border border-gray-100 flex items-center justify-center flex-shrink-0">
                                    <Loader2 className="animate-spin text-blue-500" size={16} />
                                </div>
                                <div className="bg-white border border-gray-100 rounded-2xl px-4 py-3 shadow-sm">
                                    <div className="flex space-x-1">
                                        <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" />
                                        <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.2s]" />
                                        <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.4s]" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {messages.length === 1 && !isLoading && (
                        <div className="pt-6 animate-in fade-in duration-700">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] ml-1">
                                    Acțiuni rapide
                                </h3>
                                <div className="h-[1px] flex-1 bg-gray-100 ml-4" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                {QUICK_QUERIES.map(({ label, query, icon: Icon }) => (
                                    <button
                                        key={label}
                                        onClick={() => handleQuickQuery(query)}
                                        className="text-left p-3 bg-white border border-gray-100 rounded-2xl hover:border-blue-200 hover:shadow-md transition-all active:scale-[0.98]"
                                    >
                                        <div className="flex items-center mb-1">
                                            <Icon className="text-blue-500 mr-2 flex-shrink-0" size={14} />
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
                            disabled={isLoading}
                        />
                        <button
                            onClick={() => sendMessage()}
                            disabled={!inputMessage.trim() || isLoading}
                            className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2 rounded-xl hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md active:scale-90"
                            aria-label="Trimite"
                        >
                            {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                        </button>
                    </div>
                    <div className="flex items-center justify-center mt-2 space-x-1.5">
                        <AlertTriangle className="text-amber-500" size={10} />
                        <p className="text-[9px] text-gray-400 font-bold uppercase tracking-tight">
                            Demo educativ • Nu este sfat medical
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

                <div className="flex-1 min-w-0">
                    {message.advise ? (
                        <AdviseCard advise={message.advise} />
                    ) : (
                        <div className={`rounded-2xl px-4 py-3 shadow-sm ${
                            isUser
                                ? 'bg-gradient-to-br from-blue-600 to-indigo-700 text-white'
                                : 'bg-white border border-gray-100 text-gray-800'
                        }`}>
                            <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">{message.text}</p>
                        </div>
                    )}
                    <div className={`text-[9px] font-bold uppercase tracking-tight text-gray-300 mt-1 ${isUser ? 'text-right pr-1' : 'pl-1'}`}>
                        {time}
                    </div>
                </div>
            </div>
        </div>
    );
}

function AdviseCard({ advise }: { advise: AdviseResponse }) {
    if (advise.label === 'EMERGENCY') {
        return <EmergencyCard advise={advise} />;
    }
    if (advise.label === 'UNCERTAIN') {
        return <UncertainCard advise={advise} />;
    }
    return <OtcSafeCard advise={advise} />;
}

function EmergencyCard({ advise }: { advise: AdviseResponse }) {
    return (
        <div className="rounded-2xl border-2 border-red-300 bg-gradient-to-br from-red-50 to-white shadow-md overflow-hidden">
            <div className="bg-red-600 text-white px-4 py-3 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <AlertTriangle size={20} />
                    <span className="font-bold text-sm uppercase tracking-wider">URGENȚĂ</span>
                </div>
                <span className="text-[10px] font-mono opacity-80">{advise.latency_ms.toFixed(0)} ms</span>
            </div>
            <div className="p-4 space-y-3">
                <p className="text-sm font-bold text-red-900 leading-relaxed">
                    {advise.recommended_action_ro}
                </p>
                {advise.red_flags.map(flag => (
                    <RedFlagBadge key={flag.name} flag={flag} />
                ))}
                <a
                    href="tel:112"
                    className="flex items-center justify-center space-x-2 w-full bg-red-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-red-200 hover:bg-red-700 active:scale-[0.98] transition-all"
                >
                    <Phone size={18} />
                    <span>Sună 112</span>
                </a>
                <p className="text-[10px] text-red-700 italic text-center px-2 leading-relaxed">
                    {advise.rationale}
                </p>
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

function UncertainCard({ advise }: { advise: AdviseResponse }) {
    return (
        <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-white shadow-sm overflow-hidden">
            <div className="bg-amber-100 px-4 py-2.5 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <AlertTriangle size={14} className="text-amber-700" />
                    <span className="font-bold text-xs text-amber-900 uppercase tracking-wider">Nu sunt sigur</span>
                </div>
                <span className="text-[10px] font-mono text-amber-700 opacity-80">{advise.latency_ms.toFixed(0)} ms</span>
            </div>
            <div className="p-4 space-y-3">
                <p className="text-sm text-amber-900 leading-relaxed">
                    {advise.recommended_action_ro || 'Vă rugăm să consultați un farmacist.'}
                </p>
                <p className="text-[11px] text-amber-700 italic">{advise.rationale}</p>
                {advise.medicines.length > 0 && (
                    <div className="pt-2 border-t border-amber-200">
                        <p className="text-[10px] font-bold text-amber-700 uppercase tracking-wider mb-2">
                            Rezultate slabe (referință)
                        </p>
                        <div className="space-y-2">
                            {advise.medicines.slice(0, 3).map(med => (
                                <MedicineRow key={`${med.trade_name}-${med.atc_code}`} med={med} compact />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

function OtcSafeCard({ advise }: { advise: AdviseResponse }) {
    return (
        <div className="space-y-3">
            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-b border-green-100 px-4 py-2.5 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <Sparkles size={14} className="text-green-600" />
                        <span className="font-bold text-xs text-green-900 uppercase tracking-wider">Recomandare OTC</span>
                    </div>
                    <span className="text-[10px] font-mono text-gray-400">{advise.latency_ms.toFixed(0)} ms</span>
                </div>
                <div className="p-3 space-y-2.5">
                    {advise.medicines.map(med => (
                        <MedicineRow key={`${med.trade_name}-${med.atc_code}`} med={med} />
                    ))}
                    <p className="text-[10px] text-gray-400 italic px-1 pt-1">{advise.rationale}</p>
                </div>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start">
                <AlertTriangle size={14} className="text-amber-600 mr-2 mt-0.5 flex-shrink-0" />
                <p className="text-[11px] text-amber-800 leading-relaxed">
                    {advise.recommended_action_ro || 'Consultați farmacistul dacă simptomele persistă.'}
                </p>
            </div>
        </div>
    );
}

function MedicineRow({ med, compact = false }: { med: MedicineDTO; compact?: boolean }) {
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
            {!compact && med.lay_symptoms.length > 0 && (
                <div className="text-[11px] text-gray-600 mt-1.5 leading-relaxed">
                    <span className="text-gray-400">pentru:</span> {med.lay_symptoms.join(', ')}
                </div>
            )}
            {!compact && med.best_chunk_snippet && (
                <p className="text-[11px] text-gray-500 mt-2 leading-snug line-clamp-3 italic">
                    {med.best_chunk_snippet}…
                </p>
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
