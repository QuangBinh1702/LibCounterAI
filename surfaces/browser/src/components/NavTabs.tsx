import { useEffect, useState, type ComponentType } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

type TabId = 'monitor' | 'registry' | 'history' | 'analytics';

type TabIcon = ComponentType<{ size?: number; weight?: 'regular' }>;

export interface NavTabItem {
  id: TabId;
  label: string;
  Icon: TabIcon;
}

interface NavTabsProps {
  tabs: NavTabItem[];
  activeTab: TabId;
  onChange: (tab: TabId) => void;
  iconProps?: { size: number; weight: 'regular' };
}

const GLIDER_SPRING = { type: 'spring' as const, stiffness: 300, damping: 30, mass: 0.8 };

export function NavTabs({ tabs, activeTab, onChange, iconProps = { size: 14, weight: 'regular' } }: NavTabsProps) {
  const reduceMotion = useReducedMotion();
  const [isCompactNav, setIsCompactNav] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 820px)');
    const update = () => setIsCompactNav(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  const showGlider = !reduceMotion && !isCompactNav;

  return (
    <nav className="nav-tabs" aria-label="Điều hướng chính">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            type="button"
            aria-current={isActive ? 'page' : undefined}
            data-testid={`nav-${tab.id}`}
            className={`tab-btn ${isActive ? 'active' : ''} ${isCompactNav ? 'tab-btn--compact' : ''}`}
            onClick={() => onChange(tab.id)}
          >
            {isActive && showGlider && (
              <motion.span
                layoutId="nav-tab-glider"
                className="nav-tabs-glider"
                aria-hidden="true"
                transition={GLIDER_SPRING}
              />
            )}
            <span className="tab-btn-content">
              <tab.Icon {...iconProps} />
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
