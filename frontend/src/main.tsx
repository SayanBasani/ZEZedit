import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './components/system/ToastNotificationCenter';
import { ErrorBoundary } from './components/ui/ErrorBoundary';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
