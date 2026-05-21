/**
 * Heuristic suggested-reply chips for followup questions.
 *
 * The LLM follows the followup.ro.j2 priority list (a→f: trigger, location,
 * duration, severity, associated symptoms, profile). This file recognizes
 * each pattern from the model's actual phrasing and returns a short list of
 * tappable canned answers — the user gets a 3-tap reply instead of a typed
 * one, but free-text typing still works.
 *
 * Deterministic + cheap. Not all followup questions match — when none do,
 * the function returns null and the UI shows nothing.
 *
 * Romanian text is diacritic-folded before matching so 'de cât timp' and
 * 'de cat timp' both hit.
 */

function fold(s: string): string {
    return s
        .toLowerCase()
        .normalize('NFKD')
        .replace(/[̀-ͯ]/g, '');
}

interface SuggestedReplySet {
    /** Short word shown on the chip. */
    label: string;
    /** Full sentence sent as the next user turn. */
    reply: string;
}

const TIME_REPLIES: SuggestedReplySet[] = [
    { label: 'Acum câteva ore', reply: 'A apărut acum câteva ore.' },
    { label: 'O zi', reply: 'De aproximativ o zi.' },
    { label: 'Câteva zile', reply: 'De câteva zile.' },
    { label: '> 1 săptămână', reply: 'De mai mult de o săptămână.' },
];

const TRIGGER_REPLIES: SuggestedReplySet[] = [
    { label: 'Mâncare', reply: 'Am mâncat ceva nou recent.' },
    { label: 'Medicament', reply: 'Am început un medicament nou.' },
    { label: 'Polen / animal', reply: 'Am fost expus la polen sau părul animalelor.' },
    { label: 'Nu știu', reply: 'Nu știu ce a declanșat.' },
];

const LOCATION_REPLIES: SuggestedReplySet[] = [
    { label: 'Cap', reply: 'Mă doare capul.' },
    { label: 'Stomac', reply: 'Mă doare stomacul.' },
    { label: 'Gât', reply: 'Mă doare gâtul.' },
    { label: 'Spate', reply: 'Mă doare spatele.' },
];

const SEVERITY_REPLIES: SuggestedReplySet[] = [
    { label: 'Ușoară', reply: 'Durerea este ușoară, nu mă oprește din activități.' },
    { label: 'Moderată', reply: 'Durerea este moderată, mă deranjează dar pot funcționa.' },
    { label: 'Severă', reply: 'Durerea este severă, mă oprește din activități zilnice.' },
];

const YES_NO_REPLIES: SuggestedReplySet[] = [
    { label: 'Da', reply: 'Da.' },
    { label: 'Nu', reply: 'Nu.' },
    { label: 'Nu sunt sigur', reply: 'Nu sunt sigur.' },
];

export function suggestReplies(questionText: string | undefined): SuggestedReplySet[] | null {
    if (!questionText) return null;
    const t = fold(questionText);
    if (!t.includes('?')) return null; // only suggest when the LLM is actually asking

    // Order matters: more specific patterns first so e.g. 'unde te doare'
    // wins over the generic 'doare' substring in a severity question.
    if (/\bde c(a|â)t timp\b|\bde c(a|â)nd\b|\bcat de demult\b|\bcat timp\b/.test(t)) {
        return TIME_REPLIES;
    }
    if (/declansa|provoca|trigger|ce ai m(a|â)ncat|c(a|â)nd a (ap(a|â)rut|inceput)/.test(t)) {
        return TRIGGER_REPLIES;
    }
    if (/\bunde\b.*(doare|durere)|locali[zs]/.test(t)) {
        return LOCATION_REPLIES;
    }
    if (/severitate|intens|de la 1 la 10|c(a|â)t de tare|c(a|â)t de puternic/.test(t)) {
        return SEVERITY_REPLIES;
    }
    // 'Ai și' + symptom list is yes/no by intent.
    if (/^(ai )(și|si)\b|alte simptome|al(a|â)turi|asociat/.test(t)) {
        return YES_NO_REPLIES;
    }
    return null;
}
