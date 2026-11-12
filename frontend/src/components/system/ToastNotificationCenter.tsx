import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number; // ms, default 4000
  action?: ToastAction;
  createdAt: number;
}

export type ToastInput = Omit<ToastItem, 'id' | 'createdAt'>;

interface ToastContextValue {
  toasts: ToastItem[];
  addToast: (input: ToastInput) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
  success: (message: string, options?: Partial<ToastInput>) => string;
  error: (message: string, options?: Partial<ToastInput>) => string;
  warning: (message: string, options?: Partial<ToastInput>) => string;
  info: (message: string, options?: Partial<ToastInput>) => string;
}

const defaultToastValue: ToastContextValue = {
  toasts: [],
  addToast: () => '',
  removeToast: () => {},
  clearAll: () => {},
  success: () => '',
  error: () => '',
  warning: () => '',
  info: () => '',
};

const ToastContext = createContext<ToastContextValue>(defaultToastValue);

export const useToast = (): ToastContextValue => {
  return useContext(ToastContext);
};

interface ToastProviderProps {
  children: React.ReactNode;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  const addToast = useCallback((input: ToastInput): string => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const newToast: ToastItem = {
      ...input,
      id,
      duration: input.duration ?? 4000,
      createdAt: Date.now(),
    };
    setToasts((prev) => [newToast, ...prev].slice(0, 6)); // Keep max 6 active toasts
    return id;
  }, []);

  const success = useCallback(
    (message: string, options?: Partial<ToastInput>) =>
      addToast({ type: 'success', message, ...options }),
    [addToast]
  );

  const error = useCallback(
    (message: string, options?: Partial<ToastInput>) =>
      addToast({ type: 'error', message, ...options }),
    [addToast]
  );

  const warning = useCallback(
    (message: string, options?: Partial<ToastInput>) =>
      addToast({ type: 'warning', message, ...options }),
    [addToast]
  );

  const info = useCallback(
    (message: string, options?: Partial<ToastInput>) =>
      addToast({ type: 'info', message, ...options }),
    [addToast]
  );

  const value: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    clearAll,
    success,
    error,
    warning,
    info,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  );
};

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <aside
      aria-label="Notification Center"
      className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 pointer-events-none max-w-sm w-full px-4 sm:px-0"
    >
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} onDismiss={() => onDismiss(toast.id)} />
      ))}
    </aside>
  );
};

interface ToastCardProps {
  toast: ToastItem;
  onDismiss: () => void;
}

const ToastCard: React.FC<ToastCardProps> = ({ toast, onDismiss }) => {
  const [isPaused, setIsPaused] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (toast.duration === 0 || isPaused) return;

    timerRef.current = setTimeout(() => {
      onDismiss();
    }, toast.duration);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [toast.duration, isPaused, onDismiss]);

  const typeConfig = {
    success: {
      border: 'border-emerald-600/40',
      bg: 'bg-neutral-900/95',
      accent: 'text-emerald-400',
      icon: CheckCircle2,
    },
    error: {
      border: 'border-rose-600/40',
      bg: 'bg-neutral-900/95',
      accent: 'text-rose-400',
      icon: AlertCircle,
    },
    warning: {
      border: 'border-amber-600/40',
      bg: 'bg-neutral-900/95',
      accent: 'text-amber-400',
      icon: AlertTriangle,
    },
    info: {
      border: 'border-sky-600/40',
      bg: 'bg-neutral-900/95',
      accent: 'text-sky-400',
      icon: Info,
    },
  }[toast.type];

  const Icon = typeConfig.icon;

  return (
    <div
      role="alert"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      className={`pointer-events-auto flex items-start space-x-3 rounded-lg border p-3.5 shadow-xl backdrop-blur-md transition-all duration-200 ${typeConfig.border} ${typeConfig.bg}`}
    >
      <Icon className={`h-4 w-4 shrink-0 mt-0.5 ${typeConfig.accent}`} />

      <div className="flex-1 min-w-0 pr-1">
        {toast.title && (
          <p className="text-xs font-semibold text-neutral-100 leading-snug truncate">
            {toast.title}
          </p>
        )}
        <p className="text-xs text-neutral-300 leading-snug break-words mt-0.5">
          {toast.message}
        </p>
        {toast.action && (
          <button
            onClick={() => {
              toast.action?.onClick();
              onDismiss();
            }}
            className="mt-2 text-[11px] font-medium text-amber-400 hover:text-amber-300 underline underline-offset-2"
          >
            {toast.action.label}
          </button>
        )}
      </div>

      <button
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="shrink-0 text-neutral-400 hover:text-neutral-200 p-0.5 rounded transition"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};
