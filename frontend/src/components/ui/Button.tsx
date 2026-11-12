import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none';

  const sizeStyles = {
    sm: 'px-2.5 py-1.5 text-xs gap-1.5',
    md: 'px-3.5 py-2 text-xs gap-2',
    lg: 'px-4 py-2.5 text-sm gap-2.5',
  }[size];

  const variantStyles = {
    primary:
      'bg-text-primary text-canvas hover:opacity-90 active:opacity-80 shadow-xs focus:ring-border-focus border border-transparent',
    secondary:
      'bg-surface hover:bg-surface-hover text-text-primary border border-border focus:ring-border-focus',
    outline:
      'bg-transparent hover:bg-surface border border-border text-text-primary focus:ring-border-focus',
    danger:
      'bg-red-600 hover:bg-red-500 text-white shadow-xs focus:ring-red-500 border border-transparent',
    ghost:
      'bg-transparent hover:bg-surface text-text-secondary hover:text-text-primary border border-transparent focus:ring-border-focus',
  }[variant];

  return (
    <button
      disabled={disabled || isLoading}
      className={`${baseStyles} ${sizeStyles} ${variantStyles} ${className}`}
      {...props}
    >
      {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" /> : leftIcon}
      {children}
      {!isLoading && rightIcon}
    </button>
  );
};
