/**
 * Three-card first-launch tour that surfaces (1) what the app is, (2) what
 * it isn't, (3) the 112 escape hatch — in that order. Stored dismissal in
 * localStorage so power-users never see it twice.
 *
 * Doubles as a regulatory hedge: the user is shown 'this is not medical
 * advice' BEFORE their first interaction. The AI Act high-risk transparency
 * obligation is satisfied better by an active step than by a footer line.
 */

import { useState } from 'react';
import { ChevronRight, Pill, Phone, ShieldCheck } from 'lucide-react';
import { TOUR_DONE_KEY } from '../lib/onboarding';

interface Slide {
    icon: typeof Pill;
    accent: string;
    title: string;
    body: string;
}

const SLIDES: Slide[] = [
    {
        icon: Pill,
        accent: 'from-blue-500 to-indigo-600',
        title: 'Asistent pentru farmacia ta',
        body:
            'Spune-mi simptomele sau medicamentul care te interesează. ' +
            'Răspund pe baza nomenclatorului oficial ANMDM (7.555 de medicamente autorizate).',
    },
    {
        icon: ShieldCheck,
        accent: 'from-amber-500 to-orange-600',
        title: 'Sunt un instrument informativ',
        body:
            'Nu sunt medic și nu pot prescrie. Recomandările sunt doar pentru orientare — ' +
            'confirmă întotdeauna cu farmacistul înainte să iei un medicament nou.',
    },
    {
        icon: Phone,
        accent: 'from-red-500 to-rose-600',
        title: 'Urgență? Sună 112',
        body:
            'Dacă ai dureri severe în piept, dificultăți de respirație, semne de AVC, ' +
            'reacție alergică gravă sau orice altă urgență — sună imediat la 112. ' +
            'Aplicația te direcționează automat dacă detectează aceste semne.',
    },
];

export function OnboardingTour({ onDone }: { onDone: () => void }) {
    const [index, setIndex] = useState(0);
    const slide = SLIDES[index];
    const Icon = slide.icon;
    const isLast = index === SLIDES.length - 1;

    const handleNext = () => {
        if (isLast) {
            try { localStorage.setItem(TOUR_DONE_KEY, '1'); } catch { /* private-mode */ }
            onDone();
        } else {
            setIndex(i => i + 1);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/50 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="onboarding-tour-title"
        >
            <div className="bg-white w-full max-w-sm rounded-3xl p-6 shadow-2xl animate-in zoom-in-95 duration-200">
                <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${slide.accent} flex items-center justify-center mb-5 shadow-lg`} aria-hidden="true">
                    <Icon className="text-white" size={32} />
                </div>
                <h2 id="onboarding-tour-title" className="text-xl font-bold text-gray-900 mb-2 leading-tight">{slide.title}</h2>
                <p className="text-sm text-gray-600 leading-relaxed">{slide.body}</p>
                <div className="flex items-center justify-between mt-7">
                    <div className="flex gap-1.5" role="tablist" aria-label={`Pasul ${index + 1} din ${SLIDES.length}`}>
                        {SLIDES.map((_, i) => (
                            <div
                                key={i}
                                role="tab"
                                aria-selected={i === index}
                                className={`h-1.5 rounded-full transition-all ${
                                    i === index ? 'bg-blue-600 w-6' : 'bg-gray-200 w-1.5'
                                }`}
                            />
                        ))}
                    </div>
                    <button
                        onClick={handleNext}
                        className="flex items-center gap-1 bg-blue-600 text-white font-bold text-sm px-5 py-2.5 rounded-2xl shadow-md shadow-blue-100 hover:bg-blue-700 active:scale-95 transition-all"
                    >
                        {isLast ? 'Începe' : 'Următor'}
                        {!isLast && <ChevronRight size={16} />}
                    </button>
                </div>
                {!isLast && (
                    <button
                        onClick={() => {
                            try { localStorage.setItem(TOUR_DONE_KEY, '1'); } catch { /* private-mode */ }
                            onDone();
                        }}
                        className="block w-full text-center text-[11px] font-bold text-gray-400 uppercase tracking-widest mt-4 hover:text-gray-600"
                    >
                        Sari peste introducere
                    </button>
                )}
            </div>
        </div>
    );
}

