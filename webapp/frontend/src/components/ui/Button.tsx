import React from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  ...props
}) => {
  const baseStyles = `
    relative inline-flex items-center justify-center gap-2
    font-semibold rounded-xl
    transition-all duration-300 ease-out
    focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:ring-offset-2 focus:ring-offset-slate-900
    disabled:opacity-50 disabled:cursor-not-allowed
  `;

  const variants = {
    primary: `
      btn-glow text-white
      shadow-lg shadow-purple-500/25
      hover:shadow-xl hover:shadow-purple-500/30
      hover:scale-[1.02]
      active:scale-[0.98]
    `,
    secondary: `
      bg-slate-800/80 text-white
      border border-slate-700/50
      hover:bg-slate-700/80 hover:border-purple-500/30
      hover:shadow-lg hover:shadow-purple-500/10
    `,
    ghost: `
      bg-transparent text-slate-300
      hover:bg-white/5 hover:text-white
    `,
    danger: `
      bg-gradient-to-r from-red-600 to-rose-600 text-white
      shadow-lg shadow-red-500/25
      hover:shadow-xl hover:shadow-red-500/30
      hover:scale-[1.02]
    `,
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      <span className="relative z-10">{children}</span>
    </button>
  );
};

export default Button;
