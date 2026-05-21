import { useEffect } from 'react';
import {
    AlertTriangle,
    Bot,
    CheckCircle2,
    ExternalLink,
    Phone,
    Pill,
    ShieldAlert,
    Sparkles,
    User as UserIcon,
    Zap,
} from 'lucide-react';
import type { IntentEvent, MedicineDTO, Message, RedFlagDTO, TriageEvent } from '../../types';

export function MessageBubble({ message }: { message: Message }) {
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

    if (triage?.label === 'EMERGENCY') {
        return <EmergencyCard triage={triage} />;
    }

    return (
        <>
            {message.intent && <IntentPill intent={message.intent} />}
            <TextBubble
                text={message.text}
                isStreaming={!!message.isStreaming}
                error={message.error}
                phase={message.streamPhase}
            />
            {/* Citation badge appears only after streaming finishes AND when
                the concept applies (not on followups, not on emergencies). */}
            {!message.isStreaming && message.citationValid !== undefined && message.citationValid !== null && (
                <CitationBadge valid={message.citationValid} />
            )}
            {triage?.label === 'UNCERTAIN' && triage.recommended_action_ro && (
                <UncertainAction triage={triage} />
            )}
            {message.medicines && message.medicines.length > 0 && (
                <MedicineGrid medicines={message.medicines} />
            )}
        </>
    );
}

function CitationBadge({ valid }: { valid: boolean }) {
    if (valid) {
        return (
            <div className="inline-flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 rounded-full px-2.5 py-1 text-[10px] font-semibold text-emerald-700">
                <CheckCircle2 size={10} />
                <span>Răspuns fundamentat pe nomenclatorul ANMDM</span>
            </div>
        );
    }
    return (
        <div className="inline-flex items-center gap-1.5 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1 text-[10px] font-semibold text-amber-800">
            <ShieldAlert size={10} />
            <span>Nu am identificat o sursă concretă pentru această recomandare</span>
        </div>
    );
}

// Stream-phase pill copy. Lives next to the bubble so it stays in sync with
// the phase tags Chat.tsx assigns as each SSE event lands.
const PHASE_LABEL: Record<NonNullable<Message['streamPhase']>, string | null> = {
    scanning: 'Verific semnele de urgență…',
    classifying: 'Aleg fluxul potrivit…',
    searching: 'Caut în nomenclatorul ANMDM…',
    drafting: 'Compun răspunsul…',
    done: null,
};

function IntentPill({ intent }: { intent: IntentEvent }) {
    // Symptom triage is the default — surfacing it as a pill would be noisy.
    if (intent.label !== 'MEDICINE_LOOKUP') return null;
    return (
        <div className="inline-flex items-center gap-1.5 bg-blue-50 border border-blue-200 rounded-full px-2.5 py-1 text-[10px] font-semibold text-blue-700">
            <Pill size={10} />
            <span>Explicare medicament{intent.medicine_trade_name ? `: ${intent.medicine_trade_name}` : ''}</span>
        </div>
    );
}

function TextBubble({
    text,
    isStreaming,
    error,
    phase,
}: {
    text?: string;
    isStreaming: boolean;
    error?: string;
    phase?: Message['streamPhase'];
}) {
    if (error) {
        return (
            <div className="rounded-2xl px-4 py-3 shadow-sm bg-red-50 border border-red-200 text-red-800 text-sm">
                {error}
            </div>
        );
    }
    const phaseLabel = phase && PHASE_LABEL[phase];
    if (!text && isStreaming) {
        return (
            <div className="rounded-2xl px-4 py-3 shadow-sm bg-white border border-gray-100">
                <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                        <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" />
                        <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.2s]" />
                        <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.4s]" />
                    </div>
                    {phaseLabel && (
                        <span className="text-[11px] text-gray-500 font-medium animate-in fade-in duration-300">
                            {phaseLabel}
                        </span>
                    )}
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
    // Haptic alert on mount: a short SOS-like pattern. Browser API, mobile-only
    // effect on most devices. Silently no-ops where unsupported (desktop, iOS
    // outside PWA). Critical for users glancing at a phone during an episode.
    useEffect(() => {
        if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
            try {
                navigator.vibrate([300, 120, 300, 120, 300]);
            } catch {
                // Some browsers throw if vibration is disallowed by user-engagement gesture rules.
            }
        }
    }, []);

    return (
        <div className="rounded-2xl border-2 border-red-300 bg-gradient-to-br from-red-50 to-white shadow-md overflow-hidden">
            <div className="bg-red-600 text-white px-4 py-3 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <AlertTriangle size={20} />
                    <span className="font-bold text-sm uppercase tracking-wider">Urgență medicală</span>
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
