import { Bot, History, Loader2, Plus, Share2, Wifi, WifiOff, X } from 'lucide-react';

interface ChatHeaderProps {
    onBack: () => void;
    isOnline: boolean | null;
    historyEnabled: boolean;
    sessionsCount: number;
    isStreaming: boolean;
    canExport: boolean;
    onNewSession: () => void;
    onOpenHistory: () => void;
    onExport: () => void;
}

export function ChatHeader({
    onBack,
    isOnline,
    historyEnabled,
    sessionsCount,
    isStreaming,
    canExport,
    onNewSession,
    onOpenHistory,
    onExport,
}: ChatHeaderProps) {
    return (
        <header className="bg-white border-b border-gray-100 shadow-sm flex-shrink-0">
            <div className="max-w-md mx-auto px-4 py-3 flex items-center justify-between">
                <button
                    onClick={onBack}
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
                        <h1 className="text-base font-bold text-gray-800 leading-none">Asistent farmacist</h1>
                        <div className="flex items-center mt-1.5">
                            {isOnline === null ? (
                                <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex items-center">
                                    <Loader2 className="w-2.5 h-2.5 mr-1 animate-spin" /> Mă conectez…
                                </span>
                            ) : isOnline ? (
                                <span className="text-[9px] font-bold text-green-600 uppercase tracking-widest flex items-center bg-green-50 px-1.5 py-0.5 rounded-full">
                                    <Wifi className="w-2.5 h-2.5 mr-1" /> Disponibil
                                </span>
                            ) : (
                                <span className="text-[9px] font-bold text-red-600 uppercase tracking-widest flex items-center bg-red-50 px-1.5 py-0.5 rounded-full">
                                    <WifiOff className="w-2.5 h-2.5 mr-1" /> Indisponibil
                                </span>
                            )}
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-1">
                    {canExport && (
                        <button
                            onClick={onExport}
                            className="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800"
                            aria-label="Descarcă sau partajează conversația"
                            title="Descarcă sau partajează"
                            disabled={isStreaming}
                        >
                            <Share2 size={18} />
                        </button>
                    )}
                    {historyEnabled ? (
                        <>
                            <button
                                onClick={onNewSession}
                                className="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800"
                                aria-label="Conversație nouă"
                                title="Conversație nouă"
                                disabled={isStreaming}
                            >
                                <Plus size={18} />
                            </button>
                            <button
                                onClick={onOpenHistory}
                                className="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800 relative"
                                aria-label="Istoric conversații"
                                title="Istoric"
                            >
                                <History size={18} />
                                {sessionsCount > 0 && (
                                    <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-blue-500 rounded-full" />
                                )}
                            </button>
                        </>
                    ) : (
                        !canExport && <div className="w-9 h-9" />
                    )}
                </div>
            </div>
        </header>
    );
}
