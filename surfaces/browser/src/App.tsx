import React, { useEffect, useState } from 'react';
import { VideoCamera, Users, CalendarBlank, ChartBar, GearSix, ShieldCheck, SignOut } from '@phosphor-icons/react';
import { AnimatePresence } from 'framer-motion';
import { useAuth } from './hooks/useAuth';
import { useToast } from './hooks/useToast';
import { useTheme } from './hooks/useTheme';
import { ToastContainer } from './components/Toast';
import { NavTabs } from './components/NavTabs';
import { PageTransition } from './components/PageTransition';
import { LoginPage } from './components/LoginPage';
import { ErrorBoundary } from './components/ErrorBoundary';
import { MonitorPage } from './components/MonitorPage';
import { RegistryPage } from './components/RegistryPage';
import { HistoryPage } from './components/HistoryPage';
import { AnalyticsPage } from './components/AnalyticsPage';
import { AdminPage } from './components/AdminPage';
import { PersonalSettings, type Density } from './components/PersonalSettings';

const ICON_SM = { size: 14, weight: 'regular' as const };

type OpsTabId = 'monitor' | 'registry' | 'history' | 'analytics';
type TabId = OpsTabId | 'admin';

function App() {
  const { isAuthenticated, isAdmin, logout } = useAuth();
  const { toasts, dismiss: dismissToast } = useToast();
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<TabId>('monitor');
  const [prevOpsTab, setPrevOpsTab] = useState<OpsTabId>('monitor');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [density, setDensity] = useState<Density>(() => (localStorage.getItem('libcounterai-density') as Density) || 'comfortable');
  const [reduceMotion, setReduceMotion] = useState(() => localStorage.getItem('libcounterai-reduce-motion') === 'true');

  useEffect(() => {
    document.documentElement.dataset.density = density;
    localStorage.setItem('libcounterai-density', density);
  }, [density]);

  useEffect(() => {
    document.documentElement.dataset.reduceMotion = String(reduceMotion);
    localStorage.setItem('libcounterai-reduce-motion', String(reduceMotion));
  }, [reduceMotion]);

  const navTabs: { id: OpsTabId; label: string; Icon: React.ComponentType<{ size?: number; weight?: 'regular' }> }[] = [
    { id: 'monitor', label: 'Giám sát', Icon: VideoCamera },
    { id: 'registry', label: 'Thành viên', Icon: Users },
    { id: 'history', label: 'Lịch sử', Icon: CalendarBlank },
    { id: 'analytics', label: 'Thống kê', Icon: ChartBar },
  ];

  const selectOpsTab = (tab: OpsTabId) => {
    setPrevOpsTab(tab);
    setActiveTab(tab);
  };

  const toggleAdmin = () => {
    if (activeTab === 'admin') {
      setActiveTab(prevOpsTab);
      return;
    }
    setPrevOpsTab(activeTab);
    setActiveTab('admin');
  };

  if (!isAuthenticated) {
    return (
      <>
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        <LoginPage />
      </>
    );
  }

  return (
    <>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">L</div>
          <div className="brand-copy">
            <h1 className="brand-name">LibCounterAI</h1>
          </div>
        </div>
        <NavTabs
          tabs={navTabs}
          activeTab={activeTab === 'admin' ? null : activeTab}
          onChange={selectOpsTab}
          iconProps={ICON_SM}
        />
        <div className="system-status">
          {isAdmin && (
            <button
              type="button"
              className={`admin-entry ${activeTab === 'admin' ? 'active' : ''}`}
              data-testid="admin-entry"
              aria-pressed={activeTab === 'admin'}
              aria-label={activeTab === 'admin' ? 'Đóng khu vực quản trị' : 'Mở quản trị hệ thống'}
              title="Quản trị hệ thống"
              onClick={toggleAdmin}
            >
              <ShieldCheck size={16} weight={activeTab === 'admin' ? 'fill' : 'regular'} />
              <span className="admin-entry-label">Quản trị</span>
            </button>
          )}
          <button type="button" className="settings-entry" onClick={() => setSettingsOpen(true)} aria-label="Mở cài đặt cá nhân" title="Cài đặt cá nhân"><GearSix size={16} weight="regular" /></button>
          <button type="button" className="logout-btn" onClick={logout} title="Đăng xuất" data-testid="logout-btn">
            <SignOut {...ICON_SM} />
          </button>
        </div>
      </header>
      <div className="page-transition-stage">
        <AnimatePresence mode="wait" initial={false}>
          {activeTab === 'monitor' && (
            <PageTransition key="monitor" className="page-view" testId="view-monitor">
              <ErrorBoundary name="Giám sát">
                <MonitorPage />
              </ErrorBoundary>
            </PageTransition>
          )}
          {activeTab === 'registry' && (
            <PageTransition key="registry" className="page-view" testId="view-registry">
              <ErrorBoundary name="Thành viên">
                <RegistryPage />
              </ErrorBoundary>
            </PageTransition>
          )}
          {activeTab === 'history' && (
            <PageTransition key="history" className="page-view" testId="view-history">
              <ErrorBoundary name="Lịch sử">
                <HistoryPage />
              </ErrorBoundary>
            </PageTransition>
          )}
          {activeTab === 'analytics' && (
            <PageTransition key="analytics" className="page-view" testId="view-analytics">
              <ErrorBoundary name="Thống kê">
                <AnalyticsPage />
              </ErrorBoundary>
            </PageTransition>
          )}
          {activeTab === 'admin' && (
            <PageTransition key="admin" className="page-view" testId="view-admin">
              <ErrorBoundary name="Quản trị">
                <AdminPage onBack={() => setActiveTab(prevOpsTab)} />
              </ErrorBoundary>
            </PageTransition>
          )}
        </AnimatePresence>
      </div>
      <PersonalSettings open={settingsOpen} theme={theme} density={density} reduceMotion={reduceMotion} onClose={() => setSettingsOpen(false)} onThemeChange={setTheme} onDensityChange={setDensity} onReduceMotionChange={setReduceMotion} />
    </>
  );
}

export default App;
