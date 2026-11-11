import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../components/ui/Button';
import { Input, SearchInput } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Dialog, ConfirmDialog } from '../components/ui/Dialog';
import { ThemeProvider, useTheme } from '../context/ThemeContext';

describe('Design System: Button', () => {
  it('renders correctly with default props', () => {
    render(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).not.toBeDisabled();
  });

  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('shows loading spinner and is disabled when loading', () => {
    const handleClick = vi.fn();
    render(<Button isLoading onClick={handleClick}>Save Changes</Button>);
    const button = screen.getByRole('button', { name: /save changes/i });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
    expect(button.querySelector('svg')).toBeInTheDocument();
  });

  it('applies variant classes correctly', () => {
    const { rerender } = render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-red-600');

    rerender(<Button variant="secondary">Cancel</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-surface');

    rerender(<Button variant="outline">Outline</Button>);
    expect(screen.getByRole('button')).toHaveClass('border');
  });
});

describe('Design System: Input and SearchInput', () => {
  it('renders input with label and helper text', () => {
    render(<Input label="Project Name" helperText="Must be unique" placeholder="Enter name" />);
    expect(screen.getByText('Project Name')).toBeInTheDocument();
    expect(screen.getByText('Must be unique')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter name')).toBeInTheDocument();
  });

  it('displays error message when error prop is provided', () => {
    render(<Input label="Path" error="Directory not found" />);
    expect(screen.getByText('Directory not found')).toBeInTheDocument();
  });

  it('handles typing in SearchInput and triggers onClear', () => {
    const TestSearch = () => {
      const [val, setVal] = useState('test query');
      return <SearchInput value={val} onChange={(e) => setVal(e.target.value)} onClear={() => setVal('')} />;
    };
    render(<TestSearch />);
    const input = screen.getByRole('searchbox');
    expect(input).toHaveValue('test query');

    const clearBtn = screen.getByRole('button', { name: /clear search/i });
    fireEvent.click(clearBtn);
    expect(input).toHaveValue('');
  });
});

describe('Design System: Badge', () => {
  it('renders variants properly', () => {
    const { rerender } = render(<Badge variant="success">Completed</Badge>);
    expect(screen.getByText('Completed')).toHaveClass('text-emerald-400');

    rerender(<Badge variant="danger">Failed</Badge>);
    expect(screen.getByText('Failed')).toHaveClass('text-red-400');

    rerender(<Badge variant="warning">Queued</Badge>);
    expect(screen.getByText('Queued')).toHaveClass('text-amber-400');

    rerender(<Badge variant="info">Running</Badge>);
    expect(screen.getByText('Running')).toHaveClass('text-sky-400');
  });
});

describe('Design System: Card', () => {
  it('renders card content with interactive styling', () => {
    render(<Card interactive data-testid="test-card">Card Body</Card>);
    const card = screen.getByTestId('test-card');
    expect(card).toBeInTheDocument();
    expect(card).toHaveTextContent('Card Body');
    expect(card).toHaveClass('hover:border-border-focus');
  });
});

describe('Design System: Dialog and ConfirmDialog', () => {
  it('renders dialog when isOpen is true', () => {
    const onClose = vi.fn();
    render(
      <Dialog isOpen={true} onClose={onClose} title="Test Modal">
        <p>Modal Content</p>
      </Dialog>
    );
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal Content')).toBeInTheDocument();

    const closeBtn = screen.getByRole('button', { name: /close dialog/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });

  it('does not render when isOpen is false', () => {
    render(
      <Dialog isOpen={false} onClose={vi.fn()} title="Hidden Modal">
        <p>Hidden Content</p>
      </Dialog>
    );
    expect(screen.queryByText('Hidden Modal')).not.toBeInTheDocument();
  });

  it('fires onConfirm on ConfirmDialog action button', () => {
    const handleConfirm = vi.fn();
    const handleClose = vi.fn();
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Project?"
        message="This action cannot be undone."
        confirmText="Confirm Delete"
        variant="danger"
        onConfirm={handleConfirm}
        onClose={handleClose}
      />
    );
    expect(screen.getByText('Delete Project?')).toBeInTheDocument();
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: 'Confirm Delete' });
    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalled();
  });
});

describe('Design System: ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark', 'light');
  });

  const ThemeTestConsumer = () => {
    const { theme, setTheme, resolvedTheme } = useTheme();
    return (
      <div>
        <span data-testid="theme-val">{theme}</span>
        <span data-testid="resolved-val">{resolvedTheme}</span>
        <button onClick={() => setTheme('light')}>Set Light</button>
        <button onClick={() => setTheme('dark')}>Set Dark</button>
        <button onClick={() => setTheme('system')}>Set System</button>
      </div>
    );
  };

  it('persists and toggles themes properly', () => {
    render(
      <ThemeProvider>
        <ThemeTestConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-val')).toHaveTextContent('dark');
    expect(screen.getByTestId('resolved-val')).toHaveTextContent('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    fireEvent.click(screen.getByText('Set Light'));
    expect(screen.getByTestId('theme-val')).toHaveTextContent('light');
    expect(screen.getByTestId('resolved-val')).toHaveTextContent('light');
    expect(document.documentElement.classList.contains('light')).toBe(true);
    expect(localStorage.getItem('zezedit_theme_preference')).toBe('light');

    fireEvent.click(screen.getByText('Set Dark'));
    expect(screen.getByTestId('theme-val')).toHaveTextContent('dark');
    expect(localStorage.getItem('zezedit_theme_preference')).toBe('dark');
  });
});
