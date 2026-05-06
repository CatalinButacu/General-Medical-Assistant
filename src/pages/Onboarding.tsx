import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { doc, getDoc, serverTimestamp, setDoc } from 'firebase/firestore';
import { ArrowLeft, ArrowRight, Check, Heart, Plus, Save, Shield, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';
import { db } from '../config/firebase';
import type { HealthProfile } from '../types';

type Gender = 'male' | 'female' | 'other';

interface DraftProfile {
    name: string;
    age: number | '';
    gender: Gender | '';
    isPregnant: boolean;
    allergies: string[];
    conditions: string[];
    medications: string[];
}

const TOTAL_STEPS = 3;

export default function Onboarding() {
    const navigate = useNavigate();
    const { user, isAuthenticated, isLoading } = useAuth0();
    const [step, setStep] = useState(0);
    const [draft, setDraft] = useState<DraftProfile>({
        name: '',
        age: '',
        gender: '',
        isPregnant: false,
        allergies: [],
        conditions: [],
        medications: [],
    });
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        if (!isLoading && !isAuthenticated) navigate('/', { replace: true });
    }, [isAuthenticated, isLoading, navigate]);

    useEffect(() => {
        if (!user?.sub) return;
        let cancelled = false;
        (async () => {
            try {
                const snap = await getDoc(doc(db, 'health_profiles', user.sub!));
                if (cancelled) return;
                if (snap.exists()) {
                    const p = snap.data() as HealthProfile;
                    setDraft({
                        name: p.name || (user.name ?? ''),
                        age: typeof p.age === 'number' ? p.age : '',
                        gender: p.gender ?? '',
                        isPregnant: Boolean(p.isPregnant),
                        allergies: p.allergies ?? [],
                        conditions: p.conditions ?? [],
                        medications: p.medications ?? [],
                    });
                } else if (user.name) {
                    setDraft(prev => ({ ...prev, name: user.name as string }));
                }
            } catch (err) {
                console.warn('onboarding preload failed', err);
            }
        })();
        return () => { cancelled = true; };
    }, [user]);

    const next = () => setStep(s => Math.min(s + 1, TOTAL_STEPS - 1));
    const back = () => setStep(s => Math.max(s - 1, 0));

    const persist = async (markOnboarded: boolean) => {
        if (!user?.sub) return;
        setIsSaving(true);
        const payload: HealthProfile & { updatedAt: unknown } = {
            id: user.sub,
            name: draft.name || (user.name ?? 'User'),
            age: typeof draft.age === 'number' ? draft.age : undefined,
            gender: draft.gender || undefined,
            isPregnant: draft.gender === 'female' ? draft.isPregnant : undefined,
            allergies: draft.allergies,
            conditions: draft.conditions,
            medications: draft.medications,
            onboarded: markOnboarded,
            updatedAt: serverTimestamp(),
        };
        try {
            await setDoc(doc(db, 'health_profiles', user.sub), payload, { merge: true });
            toast.success(markOnboarded ? 'Profil salvat' : 'Salvat — poți completa mai târziu');
            navigate('/', { replace: true });
        } catch (err) {
            console.error('onboarding save failed', err);
            toast.error('Eșec salvare. Reîncearcă.');
        } finally {
            setIsSaving(false);
        }
    };

    const canAdvanceFromStep0 = useMemo(() => Boolean(draft.name.trim() && draft.gender), [draft.name, draft.gender]);

    return (
        <div className="min-h-full bg-gradient-to-br from-blue-50 to-indigo-100 pb-32">
            <div className="bg-white shadow-sm border-b">
                <div className="max-w-md mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center">
                        <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mr-3">
                            <Heart className="text-white" size={20} />
                        </div>
                        <div>
                            <h1 className="text-base font-bold text-gray-800 leading-none">Bun venit</h1>
                            <p className="text-[10px] text-gray-500 uppercase tracking-wider font-bold mt-1">Pasul {step + 1} / {TOTAL_STEPS}</p>
                        </div>
                    </div>
                    <button onClick={() => persist(false)} disabled={isSaving} className="text-xs text-gray-400 hover:text-gray-700 font-semibold">
                        Sari peste
                    </button>
                </div>
            </div>

            <div className="max-w-md mx-auto px-4 pt-6">
                <div className="flex gap-2 mb-8">
                    {Array.from({ length: TOTAL_STEPS }, (_, i) => (
                        <div key={i} className={`flex-1 h-1.5 rounded-full transition-colors ${i <= step ? 'bg-blue-600' : 'bg-blue-100'}`} />
                    ))}
                </div>

                {step === 0 && <StepBasics draft={draft} setDraft={setDraft} />}
                {step === 1 && <StepAllergies draft={draft} setDraft={setDraft} />}
                {step === 2 && <StepConditions draft={draft} setDraft={setDraft} />}
            </div>

            <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 shadow-lg">
                <div className="max-w-md mx-auto px-4 py-4 flex gap-3">
                    {step > 0 && (
                        <button onClick={back} disabled={isSaving} className="flex items-center gap-2 px-5 py-3 bg-gray-100 text-gray-700 rounded-2xl font-bold hover:bg-gray-200 transition-colors active:scale-[0.98]">
                            <ArrowLeft size={16} /> Înapoi
                        </button>
                    )}
                    {step < TOTAL_STEPS - 1 ? (
                        <button onClick={next} disabled={step === 0 && !canAdvanceFromStep0} className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white py-3 rounded-2xl font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed">
                            Continuă <ArrowRight size={16} />
                        </button>
                    ) : (
                        <button onClick={() => persist(true)} disabled={isSaving} className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-700 text-white py-3 rounded-2xl font-bold shadow-lg shadow-blue-200 hover:opacity-95 transition-all active:scale-[0.98] disabled:opacity-60">
                            <Save size={16} /> {isSaving ? 'Salvez…' : 'Salvează profil'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

function StepBasics({ draft, setDraft }: { draft: DraftProfile; setDraft: React.Dispatch<React.SetStateAction<DraftProfile>> }) {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2">Salut! Hai să te cunoaștem.</h2>
                <p className="text-sm text-gray-600 leading-relaxed">
                    Câteva detalii de bază ne ajută să-ți oferim recomandări mai sigure și să nu mai întrebăm de fiecare dată.
                </p>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 space-y-5">
                <Field label="Nume">
                    <input
                        type="text"
                        value={draft.name}
                        onChange={e => setDraft(p => ({ ...p, name: e.target.value }))}
                        placeholder="Numele tău"
                        className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium"
                    />
                </Field>
                <Field label="Vârstă">
                    <input
                        type="number"
                        min={0}
                        max={120}
                        value={draft.age === '' ? '' : String(draft.age)}
                        onChange={e => {
                            const v = e.target.value;
                            setDraft(p => ({ ...p, age: v === '' ? '' : Math.max(0, Math.min(120, parseInt(v, 10) || 0)) }));
                        }}
                        placeholder="ex: 30"
                        className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium"
                    />
                </Field>
                <Field label="Gen">
                    <div className="grid grid-cols-3 gap-2">
                        {(['male', 'female', 'other'] as Gender[]).map(g => (
                            <button
                                key={g}
                                onClick={() => setDraft(p => ({ ...p, gender: g, isPregnant: g === 'female' ? p.isPregnant : false }))}
                                className={`py-3 rounded-2xl font-semibold text-sm transition-all active:scale-[0.97] ${draft.gender === g ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}`}
                            >
                                {g === 'male' ? 'Masculin' : g === 'female' ? 'Feminin' : 'Altul'}
                            </button>
                        ))}
                    </div>
                </Field>

                {draft.gender === 'female' && (
                    <Field label="Sarcină">
                        <button
                            onClick={() => setDraft(p => ({ ...p, isPregnant: !p.isPregnant }))}
                            className={`w-full flex items-center justify-between p-3.5 rounded-2xl font-medium transition-all active:scale-[0.99] ${draft.isPregnant ? 'bg-pink-50 border-2 border-pink-300 text-pink-800' : 'bg-gray-50 border-2 border-transparent text-gray-700 hover:bg-gray-100'}`}
                        >
                            <span className="text-sm">Sunt însărcinată</span>
                            <span className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${draft.isPregnant ? 'bg-pink-500 border-pink-500' : 'border-gray-300'}`}>
                                {draft.isPregnant && <Check size={12} className="text-white" />}
                            </span>
                        </button>
                    </Field>
                )}
            </div>
        </div>
    );
}

function StepAllergies({ draft, setDraft }: { draft: DraftProfile; setDraft: React.Dispatch<React.SetStateAction<DraftProfile>> }) {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2 flex items-center gap-2">
                    <Shield className="text-red-500" size={24} /> Alergii
                </h2>
                <p className="text-sm text-gray-600 leading-relaxed">
                    Adaugă substanțele sau medicamentele la care ai avut reacții. Recomandările vor evita aceste opțiuni.
                </p>
            </div>

            <TagEditor
                placeholder="ex: penicilină, ibuprofen, polen…"
                items={draft.allergies}
                onChange={items => setDraft(p => ({ ...p, allergies: items }))}
                accent="red"
            />
        </div>
    );
}

function StepConditions({ draft, setDraft }: { draft: DraftProfile; setDraft: React.Dispatch<React.SetStateAction<DraftProfile>> }) {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2 flex items-center gap-2">
                    <Sparkles className="text-blue-500" size={24} /> Condiții și medicamente
                </h2>
                <p className="text-sm text-gray-600 leading-relaxed">
                    Condiții cronice și ce iei deja zilnic. Ne ajută să evităm contraindicații și interacțiuni.
                </p>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 space-y-2">
                <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Condiții cronice</div>
                <TagEditor
                    placeholder="ex: hipertensiune, diabet, gastrită…"
                    items={draft.conditions}
                    onChange={items => setDraft(p => ({ ...p, conditions: items }))}
                    accent="blue"
                    compact
                />
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 space-y-2">
                <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Medicamente curente</div>
                <TagEditor
                    placeholder="ex: lisinopril, metformină…"
                    items={draft.medications}
                    onChange={items => setDraft(p => ({ ...p, medications: items }))}
                    accent="green"
                    compact
                />
            </div>
        </div>
    );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="space-y-1.5">
            <label className="text-xs font-bold text-gray-400 uppercase ml-1 tracking-wider">{label}</label>
            {children}
        </div>
    );
}

const ACCENT_CLASSES: Record<'red' | 'blue' | 'green', { pill: string; pillText: string; remove: string }> = {
    red: { pill: 'bg-red-50 border-red-200', pillText: 'text-red-800', remove: 'text-red-400 hover:text-red-700' },
    blue: { pill: 'bg-blue-50 border-blue-200', pillText: 'text-blue-800', remove: 'text-blue-400 hover:text-blue-700' },
    green: { pill: 'bg-green-50 border-green-200', pillText: 'text-green-800', remove: 'text-green-400 hover:text-green-700' },
};

function TagEditor({
    placeholder,
    items,
    onChange,
    accent,
    compact,
}: {
    placeholder: string;
    items: string[];
    onChange: (items: string[]) => void;
    accent: 'red' | 'blue' | 'green';
    compact?: boolean;
}) {
    const [draft, setDraftValue] = useState('');
    const accentCls = ACCENT_CLASSES[accent];

    const add = () => {
        const v = draft.trim();
        if (!v) return;
        if (items.some(i => i.toLowerCase() === v.toLowerCase())) {
            setDraftValue('');
            return;
        }
        onChange([...items, v]);
        setDraftValue('');
    };

    const remove = (idx: number) => {
        onChange(items.filter((_, i) => i !== idx));
    };

    return (
        <div className={compact ? '' : 'bg-white rounded-2xl p-5 shadow-sm border border-gray-100 space-y-3'}>
            <div className="flex gap-2">
                <input
                    type="text"
                    value={draft}
                    onChange={e => setDraftValue(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
                    placeholder={placeholder}
                    className="flex-1 p-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 text-sm font-medium"
                />
                <button onClick={add} className="px-4 bg-blue-600 text-white rounded-2xl font-bold hover:bg-blue-700 transition-colors active:scale-[0.97]">
                    <Plus size={18} />
                </button>
            </div>
            {items.length > 0 ? (
                <div className="flex flex-wrap gap-2 pt-2">
                    {items.map((item, idx) => (
                        <div key={`${item}-${idx}`} className={`inline-flex items-center gap-1.5 px-3 py-1.5 ${accentCls.pill} ${accentCls.pillText} border rounded-full text-xs font-semibold`}>
                            <span>{item}</span>
                            <button onClick={() => remove(idx)} className={`${accentCls.remove} transition-colors`} aria-label={`Șterge ${item}`}>
                                <X size={12} />
                            </button>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-[11px] text-gray-400 italic pt-2">Niciuna adăugată — este OK, poți adăuga mai târziu.</p>
            )}
        </div>
    );
}
