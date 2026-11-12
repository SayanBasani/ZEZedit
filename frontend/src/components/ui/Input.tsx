import React from 'react';
import { Search } from 'lucide-react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, rightIcon, className = '', id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-text-secondary">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 pointer-events-none text-text-muted flex items-center">
              {leftIcon}
            </div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={`w-full bg-canvas-subtle border ${
              error ? 'border-red-500 focus:ring-red-500' : 'border-border focus:border-brand'
            } rounded-lg text-xs text-text-primary placeholder:text-text-muted px-3 py-2 transition focus:outline-none focus:ring-1 ${
              leftIcon ? 'pl-9' : ''
            } ${rightIcon ? 'pr-9' : ''} ${className}`}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 pointer-events-none text-text-muted flex items-center">
              {rightIcon}
            </div>
          )}
        </div>
        {error && <p className="text-[11px] text-red-500 font-medium">{error}</p>}
        {!error && helperText && <p className="text-[11px] text-text-muted">{helperText}</p>}
      </div>
    );
  }
);
Input.displayName = 'Input';

export interface SearchInputProps extends InputProps {
  onClear?: () => void;
}

export const SearchInput: React.FC<SearchInputProps> = ({ value, onClear, ...props }) => {
  return (
    <Input
      leftIcon={<Search className="w-3.5 h-3.5" />}
      type="search"
      placeholder="Search..."
      value={value}
      rightIcon={
        value && onClear ? (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              onClear();
            }}
            aria-label="Clear search"
            className="pointer-events-auto text-text-muted hover:text-text-primary p-0.5"
          >
            ×
          </button>
        ) : undefined
      }
      {...props}
    />
  );
};

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, helperText, className = '', id, children, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1">
        {label && (
          <label htmlFor={selectId} className="block text-xs font-medium text-text-secondary">
            {label}
          </label>
        )}
        <select
          id={selectId}
          ref={ref}
          className={`w-full bg-surface border ${
            error ? 'border-red-500 focus:ring-red-500' : 'border-border focus:border-brand'
          } rounded-lg text-xs text-text-primary px-3 py-2 transition focus:outline-none focus:ring-1 appearance-none cursor-pointer ${className}`}
          {...props}
        >
          {children}
        </select>
        {error && <p className="text-[11px] text-red-500 font-medium">{error}</p>}
        {!error && helperText && <p className="text-[11px] text-text-muted">{helperText}</p>}
      </div>
    );
  }
);
Select.displayName = 'Select';
