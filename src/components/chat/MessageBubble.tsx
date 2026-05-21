import { useEffect, useState } from 'react';
import {
    AlertTriangle,
    Bot,
    CheckCircle2,
    Columns,
    ExternalLink,
    Loader2,
    Phone,
    Pill,
    Rows,
    Shuffle,
    ShieldAlert,
    Sparkles,
    ThumbsDown,
    ThumbsUp,
    User as UserIcon,
    Zap,
} from 'lucide-react';
import { fetchAlternatives, submitChatFeedback } from '../../services/api';
import { suggestReplies } from '../../lib/suggestedReplies';
import type { AlternativeMedicineDTO, IntentEvent, MedicineDTO, Message, RedFlagDTO, TriageEvent } from '../../types';

// Setter type matches React's setMessages signature in Chat.tsx — exported
// so the FeedbackButtons callback can update the bubble's optimistic state
// without re-wiring through more props.
type SetMessages = (updater: (prev: Message[]) => Message[]) => void;

// Fixed list of post-recommend follow-up chips. Deliberately short and generic
// so they apply to most OTC recommendations / medicine explanations without
// needing per-medicine logic.
const FOLLOWUP_CHIPS: { label: string; query: string }[] = [
    { label: 'Cât timp?', query: 'Cât timp ar trebui să iau acest medicament?' },
    { label: 'Cu altceva?', query: 'Pot să-l combin cu alte medicamente?' },
    { label: 'Efecte adverse?', query: 'Care sunt efectele adverse posibile?' },
    { label: 'Alternative?', query: 'Există alternative dacă acesta nu funcționează?' },
];

export function MessageBubble({
    message,
    setMessages,
    onSendFollowup,
}: {
    message: Message;
    setMessages?: SetMessages;
    onSendFollowup?: (text: string) => void;
}) {
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
                        <AssistantMessage message={message} setMessages={setMessages} onSendFollowup={onSendFollowup} />
                    )}
                    <div className={`text-[9px] font-bold uppercase tracking-tight text-gray-300 ${isUser ? 'text-right pr-1' : 'pl-1'}`}>
                        {time}
                    </div>
                </div>
            </div>
        </div>
    );
}

function AssistantMessage({
    message,
    setMessages,
    onSendFollowup,
}: {
    message: Message;
    setMessages?: SetMessages;
    onSendFollowup?: (text: string) => void;
}) {
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
            {/* Explain branch with a single resolved medicine — let users
                surface 'other options in the same ATC class' without retyping. */}
            {!message.isStreaming
                && message.intent?.label === 'MEDICINE_LOOKUP'
                && message.medicines?.length === 1
                && message.medicines[0].medicine_id && (
                    <AlternativesPanel medicineId={message.medicines[0].medicine_id} />
                )}
            {/* Follow-up question chips — only on recommend/explain phases
                (same gating as the feedback thumbs / citation badge), and only
                when the parent provides a send callback. */}
            {!message.isStreaming
                && onSendFollowup
                && message.citationValid !== undefined
                && message.citationValid !== null && (
                    <FollowupChips onSelect={onSendFollowup} />
                )}
            {/* Suggested-reply chips during the followup phase. Pattern-matched
                on the LLM's question text so the user can tap a canned answer
                rather than type. */}
            {!message.isStreaming
                && onSendFollowup
                && triage?.label === 'FOLLOWUP'
                && message.text && (
                    <SuggestedReplies questionText={message.text} onSelect={onSendFollowup} />
                )}
            {/* Feedback thumbs only on recommend/explain (citation_valid not null
                = backend produced a grounded reply; followups & emergencies skip). */}
            {!message.isStreaming
                && message.requestId
                && message.citationValid !== undefined
                && message.citationValid !== null
                && setMessages && (
                    <FeedbackButtons message={message} setMessages={setMessages} />
                )}
        </>
    );
}

function FollowupChips({ onSelect }: { onSelect: (text: string) => void }) {
    return (
        <div className="flex flex-wrap gap-1.5">
            {FOLLOWUP_CHIPS.map(chip => (
                <button
                    key={chip.label}
                    onClick={() => onSelect(chip.query)}
                    className="text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-100 rounded-full px-3 py-1 hover:bg-blue-100 active:scale-95 transition-all"
                >
                    {chip.label}
                </button>
            ))}
        </div>
    );
}

function SuggestedReplies({
    questionText,
    onSelect,
}: {
    questionText: string;
    onSelect: (text: string) => void;
}) {
    const chips = suggestReplies(questionText);
    if (!chips || chips.length === 0) return null;
    return (
        <div className="flex flex-wrap gap-1.5">
            {chips.map(chip => (
                <button
                    key={chip.label}
                    onClick={() => onSelect(chip.reply)}
                    className="text-[11px] font-semibold bg-gray-50 text-gray-700 border border-gray-200 rounded-full px-3 py-1 hover:bg-gray-100 hover:border-gray-300 active:scale-95 transition-all"
                >
                    {chip.label}
                </button>
            ))}
        </div>
    );
}

function FeedbackButtons({ message, setMessages }: { message: Message; setMessages: SetMessages }) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const submitted = message.feedbackHelpful !== undefined;

    const submit = async (helpful: boolean) => {
        if (busy || !message.requestId) return;
        // Optimistic — flip the local state immediately so the user sees the
        // selection lock in. Revert if the network call fails.
        setBusy(true);
        setError(null);
        setMessages(curr => curr.map(m => (m.id === message.id ? { ...m, feedbackHelpful: helpful } : m)));
        try {
            await submitChatFeedback(message.requestId, helpful);
        } catch {
            setError('Nu am putut salva feedback-ul.');
            setMessages(curr => curr.map(m => (m.id === message.id ? { ...m, feedbackHelpful: undefined } : m)));
        } finally {
            setBusy(false);
        }
    };

    if (submitted) {
        return (
            <p className="text-[10px] text-gray-400 font-semibold italic">
                Mulțumesc pentru feedback{message.feedbackHelpful ? ' 👍' : ' 👎'}
            </p>
        );
    }

    return (
        <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">A fost util?</span>
            <button
                onClick={() => submit(true)}
                disabled={busy}
                aria-label="A fost util"
                className="p-1.5 rounded-lg text-gray-400 hover:text-green-600 hover:bg-green-50 disabled:opacity-40 transition-colors"
            >
                <ThumbsUp size={12} />
            </button>
            <button
                onClick={() => submit(false)}
                disabled={busy}
                aria-label="Nu a fost util"
                className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-40 transition-colors"
            >
                <ThumbsDown size={12} />
            </button>
            {error && <span className="text-[10px] text-red-500 font-semibold">{error}</span>}
        </div>
    );
}

function AlternativesPanel({ medicineId }: { medicineId: string }) {
    const [items, setItems] = useState<AlternativeMedicineDTO[] | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [open, setOpen] = useState(false);

    const load = async () => {
        if (loading) return;
        if (items !== null) {
            setOpen(o => !o);
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const data = await fetchAlternatives(medicineId, 5);
            setItems(data);
            setOpen(true);
        } catch {
            setError('Nu am putut încărca alternativele acum.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="mt-2">
            <button
                onClick={load}
                disabled={loading}
                className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-blue-700 hover:text-blue-900 disabled:opacity-50"
            >
                {loading
                    ? <><Loader2 size={12} className="animate-spin" /> Caut alternative…</>
                    : <><Shuffle size={12} /> {open && items?.length ? 'Ascunde alternative' : 'Vezi alternative (aceeași clasă ATC)'}</>}
            </button>
            {error && (
                <p className="mt-1 text-[10px] text-red-600 font-medium">{error}</p>
            )}
            {open && items && items.length === 0 && (
                <p className="mt-1 text-[10px] text-gray-400 italic">
                    Niciun alt medicament OTC în aceeași clasă terapeutică.
                </p>
            )}
            {open && items && items.length > 0 && (
                <ul className="mt-2 space-y-1.5">
                    {items.map(alt => (
                        <li
                            key={alt.medicine_id}
                            className="text-[11px] text-gray-700 bg-gray-50 border border-gray-100 rounded-lg px-3 py-2"
                        >
                            <span className="font-bold text-gray-800">{alt.trade_name}</span>
                            <span className="text-gray-400"> · </span>
                            <span>{alt.dci}</span>
                            <span className="text-gray-400"> · </span>
                            <span className="font-mono text-[10px]">{alt.atc_code}</span>
                            <span className="text-gray-400"> · </span>
                            <span className="capitalize">{alt.form.toLowerCase()} {alt.concentration}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
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
            <div
                className="rounded-2xl px-4 py-3 shadow-sm bg-white border border-gray-100"
                role="status"
                aria-live="polite"
                aria-label={phaseLabel ?? 'Asistentul scrie un răspuns'}
            >
                <div className="flex items-center space-x-2">
                    <div className="flex space-x-1" aria-hidden="true">
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
        <div
            className="rounded-2xl px-4 py-3 shadow-sm bg-white border border-gray-100 text-gray-800"
            aria-live={isStreaming ? 'polite' : undefined}
        >
            <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">
                {text}
                {isStreaming && <span className="inline-block w-1 h-4 ml-0.5 bg-blue-500 align-middle animate-pulse" aria-hidden="true" />}
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
        <div
            role="alert"
            aria-live="assertive"
            className="rounded-2xl border-2 border-red-300 bg-gradient-to-br from-red-50 to-white shadow-md overflow-hidden"
        >
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
    // Compare view only earns its keep when there are 2-3 options to weigh.
    // Single medicine → stack mode is the only useful view.
    const canCompare = medicines.length >= 2 && medicines.length <= 3;
    const [mode, setMode] = useState<'stack' | 'compare'>('stack');

    return (
        <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-b border-green-100 px-4 py-2 flex items-center justify-between">
                <div className="flex items-center">
                    <Sparkles size={12} className="text-green-600 mr-2" />
                    <span className="font-bold text-[11px] text-green-900 uppercase tracking-wider">
                        Medicamente · {medicines.length}
                    </span>
                </div>
                {canCompare && (
                    <button
                        onClick={() => setMode(m => (m === 'stack' ? 'compare' : 'stack'))}
                        className="inline-flex items-center gap-1 text-[10px] font-bold text-green-700 hover:text-green-900 uppercase tracking-wider"
                        aria-label={mode === 'stack' ? 'Comutează la comparație alăturată' : 'Comutează la listă'}
                    >
                        {mode === 'stack'
                            ? <><Columns size={11} /> Compară</>
                            : <><Rows size={11} /> Listă</>}
                    </button>
                )}
            </div>
            {mode === 'stack' ? (
                <div className="p-3 space-y-2.5">
                    {medicines.map(med => (
                        <MedicineRow key={`${med.trade_name}-${med.atc_code}`} med={med} />
                    ))}
                </div>
            ) : (
                <MedicineCompareTable medicines={medicines} />
            )}
        </div>
    );
}

function MedicineCompareTable({ medicines }: { medicines: MedicineDTO[] }) {
    // Side-by-side comparison for 2-3 OTC options. Renders as a horizontally
    // scrollable column-per-medicine grid on mobile (no awkward 4-line wraps)
    // and as a clean 2-3 column table on tablet+.
    const rxBadge = (status: MedicineDTO['rx_status']) =>
        status === 'OTC' ? 'bg-green-100 text-green-700'
            : status === 'MIXED' ? 'bg-amber-100 text-amber-700'
                : 'bg-red-100 text-red-700';
    return (
        <div className="overflow-x-auto">
            <div
                className="grid p-3 gap-2"
                style={{ gridTemplateColumns: `repeat(${medicines.length}, minmax(0, 1fr))` }}
            >
                {medicines.map(med => (
                    <div key={`${med.trade_name}-${med.atc_code}`} className="rounded-xl border border-gray-100 bg-gray-50/40 p-3 min-w-0">
                        <div className="flex items-start justify-between gap-1 mb-1.5">
                            <div className="font-bold text-[12px] text-gray-800 leading-tight break-words">{med.trade_name}</div>
                            <span className={`text-[8px] font-bold px-1 py-0.5 rounded uppercase tracking-wider ${rxBadge(med.rx_status)} flex-shrink-0`}>
                                {med.rx_status}
                            </span>
                        </div>
                        <div className="text-[10px] text-gray-500 mb-2 leading-tight break-words">{med.dci}</div>
                        <dl className="space-y-1.5 text-[10px]">
                            <div>
                                <dt className="text-gray-400 font-bold uppercase tracking-wider text-[8px]">ATC</dt>
                                <dd className="font-mono text-gray-700">{med.atc_code}</dd>
                            </div>
                            <div>
                                <dt className="text-gray-400 font-bold uppercase tracking-wider text-[8px]">Formă</dt>
                                <dd className="text-gray-700 capitalize">{med.form.toLowerCase()}</dd>
                            </div>
                            <div>
                                <dt className="text-gray-400 font-bold uppercase tracking-wider text-[8px]">Concentrație</dt>
                                <dd className="text-gray-700">{med.concentration || '—'}</dd>
                            </div>
                            {med.category && (
                                <div>
                                    <dt className="text-gray-400 font-bold uppercase tracking-wider text-[8px]">Categorie</dt>
                                    <dd className="text-blue-700 font-semibold">{med.category}</dd>
                                </div>
                            )}
                            {med.lay_symptoms.length > 0 && (
                                <div>
                                    <dt className="text-gray-400 font-bold uppercase tracking-wider text-[8px]">Pentru</dt>
                                    <dd className="text-gray-600">{med.lay_symptoms.slice(0, 3).join(', ')}</dd>
                                </div>
                            )}
                        </dl>
                        <div className="flex flex-col gap-1 mt-2 pt-2 border-t border-gray-100">
                            {med.prospect_url && (
                                <a
                                    href={med.prospect_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-1 text-[9px] font-semibold text-blue-600 hover:text-blue-800"
                                >
                                    <ExternalLink size={9} />
                                    <span>prospect</span>
                                </a>
                            )}
                            {med.rcp_url && (
                                <a
                                    href={med.rcp_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-1 text-[9px] font-semibold text-gray-500 hover:text-blue-700"
                                >
                                    <ExternalLink size={9} />
                                    <span>RCP</span>
                                </a>
                            )}
                        </div>
                    </div>
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
