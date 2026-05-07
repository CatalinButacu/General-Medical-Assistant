import { cn } from '../../lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    padding?: 'none' | 'sm' | 'md' | 'lg';
    hoverable?: boolean;
}

const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-6',
};

export function Card({ className, padding = 'md', hoverable, children, ...rest }: CardProps) {
    return (
        <div
            className={cn(
                'bg-white rounded-2xl shadow-sm border border-gray-100',
                paddingClasses[padding],
                hoverable && 'hover:shadow-md transition-shadow',
                className,
            )}
            {...rest}
        >
            {children}
        </div>
    );
}

export function CardHeader({ icon, title, action, accent = 'blue' }: {
    icon?: React.ReactNode;
    title: string;
    action?: React.ReactNode;
    accent?: 'blue' | 'red' | 'green' | 'pink' | 'orange' | 'gray';
}) {
    const accentBg: Record<string, string> = {
        blue: 'bg-blue-100', red: 'bg-red-50', green: 'bg-green-50',
        pink: 'bg-pink-100', orange: 'bg-orange-50', gray: 'bg-gray-50',
    };
    return (
        <div className="flex items-center justify-between mb-5">
            <div className="flex items-center">
                {icon && (
                    <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center mr-3', accentBg[accent])}>
                        {icon}
                    </div>
                )}
                <h2 className="text-lg font-bold text-gray-800">{title}</h2>
            </div>
            {action}
        </div>
    );
}
