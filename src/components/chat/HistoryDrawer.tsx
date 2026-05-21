import { useState } from 'react';
import { Trash2, X } from 'lucide-react';
import type { ChatSessionSummary } from '../../services/userApi';

export function HistoryDrawer({
    sessions,
    currentId,
    onClose,
    onPick,
    onDelete,
}: {
    sessions: ChatSessionSummary[];
    currentId: string | null;
    onClose: () => void;
    onPick: (id: string) => void;
    onDelete: (id: string) => Promise<void>;
}) {
    const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

    return (
        <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-labelledby="history-drawer-title">
            <button
                type="button"
                aria-label="Închide istoricul"
                className="absolute inset-0 bg-black/40 animate-in fade-in duration-200"
                onClick={onClose}
            />
            <aside className="relative ml-auto w-[85%] max-w-sm h-full bg-white shadow-2xl animate-in slide-in-from-right duration-200 flex flex-col">
                <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                    <h2 id="history-drawer-title" className="text-sm font-bold text-gray-800">Istoric conversații</h2>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-full hover:bg-gray-100 text-gray-500"
                        aria-label="Închide"
                    >
                        <X size={18} />
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto">
                    {sessions.length === 0 ? (
                        <p className="px-4 py-8 text-center text-xs text-gray-400">
                            Nicio conversație salvată încă.
                        </p>
                    ) : (
                        <ul className="divide-y divide-gray-100">
                            {sessions.map(s => {
                                const isCurrent = s.id === currentId;
                                const isPendingDelete = pendingDeleteId === s.id;
                                const updated = new Date(s.updated_at).toLocaleString([], {
                                    month: 'short', day: 'numeric',
                                    hour: '2-digit', minute: '2-digit',
                                });
                                return (
                                    <li
                                        key={s.id}
                                        className={`px-4 py-3 flex items-start gap-3 cursor-pointer transition-colors ${
                                            isCurrent ? 'bg-blue-50/60' : 'hover:bg-gray-50'
                                        }`}
                                        onClick={() => !isPendingDelete && onPick(s.id)}
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-semibold text-gray-800 truncate">
                                                {s.title ?? 'Conversație fără titlu'}
                                            </p>
                                            <p className="text-[11px] text-gray-400 mt-0.5">
                                                {s.message_count} mesaje · {updated}
                                            </p>
                                        </div>
                                        {isPendingDelete ? (
                                            <div className="flex items-center gap-1 flex-shrink-0">
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); setPendingDeleteId(null); }}
                                                    className="text-[10px] font-bold text-gray-500 px-2 py-1 rounded hover:bg-gray-100"
                                                >
                                                    anulează
                                                </button>
                                                <button
                                                    onClick={async (e) => {
                                                        e.stopPropagation();
                                                        await onDelete(s.id);
                                                        setPendingDeleteId(null);
                                                    }}
                                                    className="text-[10px] font-bold text-white bg-red-600 hover:bg-red-700 px-2 py-1 rounded"
                                                >
                                                    șterge
                                                </button>
                                            </div>
                                        ) : (
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setPendingDeleteId(s.id); }}
                                                className="p-1.5 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 flex-shrink-0"
                                                aria-label="Șterge"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        )}
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </div>
            </aside>
        </div>
    );
}
