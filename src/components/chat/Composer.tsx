import { forwardRef } from 'react';
import { AlertTriangle, Loader2, Mic, Send } from 'lucide-react';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';

interface ComposerProps {
    value: string;
    onChange: (v: string) => void;
    onSubmit: () => void;
    isStreaming: boolean;
}

export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(function Composer(
    { value, onChange, onSubmit, isStreaming },
    ref,
) {
    // Romanian voice input — diacritics are annoying to type on mobile and
    // medical terms are even worse. Browser-native Web Speech API; the hook
    // gracefully hides the button on browsers without webkitSpeechRecognition.
    const speech = useSpeechRecognition({
        lang: 'ro-RO',
        onResult: (transcript) => {
            // Append to whatever the user already typed, joining with a space.
            // Final-result-only mode → no interim transcript flicker in the textarea.
            onChange((value ? `${value.trim()} ${transcript}` : transcript).trim());
        },
    });

    const onMicClick = () => {
        if (speech.isListening) speech.stop();
        else speech.start();
    };

    return (
        <footer className="bg-white border-t border-gray-100 flex-shrink-0">
            <div className="max-w-md mx-auto px-4 py-3">
                <div className="relative">
                    <textarea
                        ref={ref}
                        rows={1}
                        value={value}
                        onChange={e => onChange(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                onSubmit();
                            }
                        }}
                        placeholder={speech.isListening ? 'Ascult…' : 'Descrie simptomele…'}
                        aria-label="Mesaj către asistent"
                        className={`w-full ${speech.isSupported ? 'pl-12' : 'pl-4'} pr-12 py-3 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 text-sm resize-none transition-all placeholder:text-gray-400`}
                        disabled={isStreaming}
                    />
                    {speech.isSupported && (
                        <button
                            type="button"
                            onClick={onMicClick}
                            disabled={isStreaming}
                            className={`absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-xl transition-all active:scale-90 ${
                                speech.isListening
                                    ? 'bg-red-500 text-white shadow-md animate-pulse'
                                    : 'text-gray-400 hover:text-blue-600 hover:bg-gray-100'
                            }`}
                            aria-label={speech.isListening ? 'Oprește înregistrarea' : 'Vorbește în loc să tastezi'}
                            title={speech.isListening ? 'Oprește înregistrarea' : 'Vorbește în loc să tastezi'}
                        >
                            <Mic size={18} />
                        </button>
                    )}
                    <button
                        onClick={onSubmit}
                        disabled={!value.trim() || isStreaming}
                        className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2 rounded-xl hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md active:scale-90"
                        aria-label="Trimite"
                    >
                        {isStreaming ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                    </button>
                </div>
                {speech.error && !speech.isListening && (
                    <p className="text-[10px] text-red-500 mt-1.5 ml-1 font-semibold">
                        Voce indisponibilă: {speech.error}
                    </p>
                )}
                <div className="flex items-center justify-center mt-2 space-x-1.5">
                    <AlertTriangle className="text-amber-500" size={10} />
                    <p className="text-[9px] text-gray-400 font-bold uppercase tracking-tight">
                        Proiect educativ • Confirmă orice recomandare cu farmacistul
                    </p>
                </div>
            </div>
        </footer>
    );
});
