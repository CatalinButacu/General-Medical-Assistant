import { cn } from '../../lib/utils';

export type BadgeTone = 'blue' | 'green' | 'red' | 'orange' | 'gray' | 'amber';

const toneClasses: Record<BadgeTone, string> = {
    blue: 'bg-blue-50 text-blue-700 border-blue-100',
    green: 'bg-green-50 text-green-700 border-green-100',
    red: 'bg-red-50 text-red-700 border-red-100',
    orange: 'bg-orange-50 text-orange-700 border-orange-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    gray: 'bg-gray-50 text-gray-600 border-gray-100',
};

export function Badge({ tone = 'gray', children, className }: {
    tone?: BadgeTone;
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <span className={cn(
            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider',
            toneClasses[tone],
            className,
        )}>
            {children}
        </span>
    );
}
