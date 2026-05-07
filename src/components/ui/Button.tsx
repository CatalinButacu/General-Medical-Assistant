import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant;
    size?: ButtonSize;
    fullWidth?: boolean;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-100 disabled:bg-blue-300 disabled:shadow-none',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-40',
    ghost: 'bg-transparent text-gray-600 hover:bg-gray-50 disabled:opacity-40',
    danger: 'bg-red-600 text-white hover:bg-red-700 shadow-lg shadow-red-100 disabled:bg-red-300 disabled:shadow-none',
    success: 'bg-green-600 text-white hover:bg-green-700 shadow-lg shadow-green-100 disabled:bg-green-300 disabled:shadow-none',
};

const sizeClasses: Record<ButtonSize, string> = {
    sm: 'px-3 py-2 text-xs rounded-xl',
    md: 'px-5 py-3 text-sm rounded-2xl',
    lg: 'px-6 py-4 text-base rounded-2xl',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
    { className, variant = 'primary', size = 'md', fullWidth, leftIcon, rightIcon, children, ...rest },
    ref,
) {
    return (
        <button
            ref={ref}
            className={cn(
                'inline-flex items-center justify-center gap-2 font-bold transition-all active:scale-[0.98] disabled:cursor-not-allowed',
                variantClasses[variant],
                sizeClasses[size],
                fullWidth && 'w-full',
                className,
            )}
            {...rest}
        >
            {leftIcon}
            {children}
            {rightIcon}
        </button>
    );
});
