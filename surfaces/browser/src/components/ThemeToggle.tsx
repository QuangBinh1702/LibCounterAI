import { Moon, Sun } from '@phosphor-icons/react';
import type { Theme } from '../hooks/useTheme';

interface ThemeToggleProps {
  theme: Theme;
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      className={`theme-switch ${isDark ? 'is-dark' : 'is-light'}`}
      onClick={onToggle}
      aria-label={isDark ? 'Giao diện tối. Bật để chuyển sang sáng' : 'Giao diện sáng. Bật để chuyển sang tối'}
      title={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
    >
      <span className="theme-switch-track">
        <span className="theme-switch-thumb" aria-hidden="true" />
        <span className="theme-switch-option theme-switch-sun" aria-hidden="true">
          <Sun size={15} weight="fill" />
        </span>
        <span className="theme-switch-option theme-switch-moon" aria-hidden="true">
          <Moon size={15} weight="fill" />
        </span>
      </span>
    </button>
  );
}
