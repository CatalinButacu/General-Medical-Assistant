import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

const inputBase = 'w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium text-gray-800 placeholder:text-gray-400';

interface FormFieldProps {
    label?: string;
    hint?: string;
    error?: string;
    children: React.ReactNode;
}

export function FormField({ label, hint, error, children }: FormFieldProps) {
    return (
        <div className="space-y-1.5">
            {label && <label className="text-[10px] font-bold text-gray-400 uppercase ml-1 tracking-widest">{label}</label>}
            {children}
            {error
                ? <p className="text-[11px] text-red-600 font-semibold ml-1">{error}</p>
                : hint
                    ? <p className="text-[10px] text-gray-400 ml-1">{hint}</p>
                    : null}
        </div>
    );
}

export const TextInput = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function TextInput(
    { className, ...rest },
    ref,
) {
    return <input ref={ref} className={cn(inputBase, className)} {...rest} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
    { className, ...rest },
    ref,
) {
    return <textarea ref={ref} className={cn(inputBase, 'resize-none', className)} {...rest} />;
});

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(function Select(
    { className, children, ...rest },
    ref,
) {
    return (
        <select ref={ref} className={cn(inputBase, 'appearance-none', className)} {...rest}>
            {children}
        </select>
    );
});
