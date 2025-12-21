import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'glass' | 'neon';
}

export const Card: React.FC<CardProps> = ({ children, className, variant = 'default' }) => {
  const variants = {
    default: 'glass-card',
    glass: 'ultra-glass rounded-2xl',
    neon: 'glass-card neon-border',
  };

  return <div className={cn(variants[variant], className)}>{children}</div>;
};

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children, className, onClick }) => (
  <div className={cn('p-6 pb-4', className)} onClick={onClick}>{children}</div>
);

interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
}

export const CardTitle: React.FC<CardTitleProps> = ({ children, className }) => (
  <h3 className={cn('text-xl font-bold text-white flex items-center gap-3', className)}>
    {children}
  </h3>
);

interface CardDescriptionProps {
  children: React.ReactNode;
  className?: string;
}

export const CardDescription: React.FC<CardDescriptionProps> = ({ children, className }) => (
  <p className={cn('text-sm text-slate-400 mt-1.5', className)}>{children}</p>
);

interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export const CardContent: React.FC<CardContentProps> = ({ children, className }) => (
  <div className={cn('p-6 pt-0', className)}>{children}</div>
);

interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export const CardFooter: React.FC<CardFooterProps> = ({ children, className }) => (
  <div className={cn('p-6 pt-0 flex items-center gap-3', className)}>{children}</div>
);
