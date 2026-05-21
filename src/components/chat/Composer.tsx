import { forwardRef } from 'react';
import { AlertTriangle, Loader2, Send } from 'lucide-react';

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
                        placeholder="Descrie simptomele…"
                        className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 text-sm resize-none transition-all placeholder:text-gray-400"
                        disabled={isStreaming}
                    />
                    <button
                        onClick={onSubmit}
                        disabled={!value.trim() || isStreaming}
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
    );
});
