/**
 * Minimal Web Speech API wrapper for Romanian voice input.
 *
 * Returns a stable `start()` / `stop()` pair plus `isListening` + `isSupported`.
 * Each utterance feeds into `onResult` once finalized — no interim transcript
 * streaming (chat micro-copy doesn't benefit from it and it complicates the
 * textarea state). Errors silently end the session and surface via `error`.
 *
 * Triggers only support `'webkitSpeechRecognition'` (Chromium / Edge / Samsung
 * Internet) — Firefox + Safari don't ship the API at the time of writing.
 * `isSupported` lets the Composer hide the button cleanly.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

// The Web Speech API isn't in lib.dom.d.ts. Minimal shape we touch:
interface SpeechRecognitionLike {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    onresult: ((ev: { results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null;
    onerror: ((ev: { error: string }) => void) | null;
    onend: (() => void) | null;
    start: () => void;
    stop: () => void;
}

interface UseSpeechRecognitionOptions {
    lang?: string;
    onResult: (transcript: string) => void;
}

interface UseSpeechRecognitionReturn {
    isSupported: boolean;
    isListening: boolean;
    error: string | null;
    start: () => void;
    stop: () => void;
}

export function useSpeechRecognition(opts: UseSpeechRecognitionOptions): UseSpeechRecognitionReturn {
    const { lang = 'ro-RO', onResult } = opts;
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

    const SpeechRecognitionCtor =
        typeof window !== 'undefined'
            ? (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognitionLike; SpeechRecognition?: new () => SpeechRecognitionLike })
                  .webkitSpeechRecognition ??
              (window as unknown as { SpeechRecognition?: new () => SpeechRecognitionLike }).SpeechRecognition
            : undefined;

    const isSupported = Boolean(SpeechRecognitionCtor);

    const onResultRef = useRef(onResult);
    onResultRef.current = onResult;

    const start = useCallback(() => {
        if (!SpeechRecognitionCtor) return;
        if (recognitionRef.current) return;
        const recog = new SpeechRecognitionCtor();
        recog.continuous = false;
        recog.interimResults = false;
        recog.lang = lang;
        recog.onresult = (ev) => {
            const transcript = ev.results[0]?.[0]?.transcript ?? '';
            if (transcript.trim()) onResultRef.current(transcript.trim());
        };
        recog.onerror = (ev) => {
            setError(ev.error || 'unknown speech error');
            setIsListening(false);
            recognitionRef.current = null;
        };
        recog.onend = () => {
            setIsListening(false);
            recognitionRef.current = null;
        };
        try {
            recog.start();
            recognitionRef.current = recog;
            setError(null);
            setIsListening(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'failed to start recognition');
            setIsListening(false);
            recognitionRef.current = null;
        }
    }, [SpeechRecognitionCtor, lang]);

    const stop = useCallback(() => {
        recognitionRef.current?.stop();
    }, []);

    useEffect(() => () => recognitionRef.current?.stop(), []);

    return { isSupported, isListening, error, start, stop };
}
