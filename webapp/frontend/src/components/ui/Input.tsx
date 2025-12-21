import React from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input: React.FC<InputProps> = ({ label, error, className, ...props }) => {
  return (
    <div className="space-y-2">
      {label && (
        <label className="text-sm font-semibold text-slate-300">{label}</label>
      )}
      <input
        className={cn(
          'w-full h-11 px-4 rounded-xl',
          'input-glass text-white placeholder-slate-500',
          'focus:outline-none focus:ring-2 focus:ring-purple-500/50',
          error && 'border-red-500/50 focus:ring-red-500/50',
          className
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
};

export default Input;
