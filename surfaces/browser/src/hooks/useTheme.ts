import { useCallback, useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'libcounterai-theme';

function getPreferredTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(STORAGE_KEY, theme);
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof document === 'undefined') return 'dark';
    return (document.documentElement.dataset.theme as Theme) || getPreferredTheme();
  });

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, setTheme, toggleTheme };
}

export function readThemeColors() {
  const style = getComputedStyle(document.documentElement);
  const pick = (name: string) => style.getPropertyValue(name).trim();
  return {
    accent: pick('--accent'),
    entry: pick('--semantic-entry'),
    exit: pick('--semantic-exit'),
    labelBg: pick('--canvas-label-bg'),
    labelFg: pick('--canvas-label-fg'),
    entryFill: pick('--semantic-entry-fill'),
    exitFill: pick('--semantic-exit-fill'),
  };
}
