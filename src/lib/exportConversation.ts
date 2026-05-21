/**
 * Serialize a chat session to plain markdown that a pharmacist can read
 * without the app. Uses the native Web Share API on mobile, falls back to
 * clipboard + .md download on desktop.
 *
 * Deliberately strips the streaming-only fields (intent pill, phase pill,
 * citation badge) — the export is for the human reading it later, not
 * forensic debugging. The audit_log table is the place for that.
 */

import type { Message } from '../types';

function formatTimestamp(ts: Date): string {
    const d = new Date(ts);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ` +
        `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function conversationToMarkdown(messages: Message[]): string {
    const lines: string[] = [];
    const first = messages.find(m => m.id !== 'welcome');
    const headerDate = first ? formatTimestamp(first.timestamp) : formatTimestamp(new Date());
    lines.push('# Conversație Med Assist');
    lines.push(`*Generat: ${headerDate}*`);
    lines.push('');
    lines.push('> Document educativ generat de un proiect-pilot. Nu constituie sfat medical. ' +
        'Pentru orice decizie privind tratamentul, consultă farmacistul sau medicul.');
    lines.push('');

    for (const m of messages) {
        if (m.id === 'welcome') continue;
        const stamp = formatTimestamp(m.timestamp);
        const speaker = m.sender === 'user' ? '**Utilizator**' : '**Asistent**';
        lines.push(`### ${speaker} · ${stamp}`);
        if (m.error) {
            lines.push('');
            lines.push(`> Eroare: ${m.error}`);
            lines.push('');
            continue;
        }
        if (m.triage?.label === 'EMERGENCY') {
            lines.push('');
            lines.push('**⚠ URGENȚĂ DETECTATĂ**');
            lines.push('');
            lines.push(m.triage.recommended_action_ro);
            if (m.triage.red_flags.length > 0) {
                lines.push('');
                lines.push('Reguli detectate:');
                for (const rf of m.triage.red_flags) {
                    lines.push(`- ${rf.description} (severitate: ${rf.severity})`);
                }
            }
            lines.push('');
            continue;
        }
        if (m.text) {
            lines.push('');
            lines.push(m.text.trim());
            lines.push('');
        }
        if (m.medicines && m.medicines.length > 0) {
            lines.push('');
            lines.push('**Medicamente sugerate:**');
            lines.push('');
            for (const med of m.medicines) {
                const rx = med.rx_status === 'OTC' ? 'fără rețetă' : med.rx_status;
                lines.push(`- **${med.trade_name}** — ${med.dci} · ${med.form.toLowerCase()} ${med.concentration} · ATC ${med.atc_code} · ${rx}`);
                if (med.prospect_url) lines.push(`  - Prospect: ${med.prospect_url}`);
                if (med.rcp_url) lines.push(`  - RCP: ${med.rcp_url}`);
            }
            lines.push('');
        }
        if (m.citationValid === false) {
            lines.push('');
            lines.push('> ⚠ Acest răspuns nu citează o sursă concretă din nomenclator.');
            lines.push('');
        }
    }
    lines.push('---');
    lines.push('*Sursa medicamentelor: Nomenclatorul ANMDM. Pentru urgențe medicale: 112.*');
    return lines.join('\n');
}

/**
 * Trigger a share/download for the conversation. Returns a status the UI
 * can toast — distinguishes share-via-native-sheet, copied-to-clipboard,
 * and downloaded-as-file. AbortError (user cancelled the share sheet)
 * is swallowed as "cancelled".
 */
export type ExportResult = 'shared' | 'copied' | 'downloaded' | 'cancelled' | 'unsupported';

export async function exportConversation(messages: Message[]): Promise<ExportResult> {
    const markdown = conversationToMarkdown(messages);
    const filename = `med-assist-conversatie-${new Date().toISOString().slice(0, 10)}.md`;

    // 1) Native share sheet — best mobile UX. Falls through if the user
    // dismisses the sheet (AbortError) or the API doesn't support files.
    const nav = navigator as Navigator & {
        canShare?: (data: ShareData) => boolean;
        share?: (data: ShareData) => Promise<void>;
    };
    if (typeof nav.share === 'function') {
        try {
            await nav.share({
                title: 'Conversație Med Assist',
                text: markdown,
            });
            return 'shared';
        } catch (err) {
            if (err instanceof Error && err.name === 'AbortError') return 'cancelled';
            // fall through to other strategies
        }
    }

    // 2) Clipboard — desktop default.
    if (navigator.clipboard?.writeText) {
        try {
            await navigator.clipboard.writeText(markdown);
            return 'copied';
        } catch {
            // fall through
        }
    }

    // 3) Last resort: synthesize a .md download.
    try {
        const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        return 'downloaded';
    } catch {
        return 'unsupported';
    }
}
