import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Check, Moon, SlidersHorizontal, Sun, X } from '@phosphor-icons/react';
import type { Theme } from '../hooks/useTheme';

export type Density = 'comfortable' | 'compact';

interface PersonalSettingsProps {
  open: boolean;
  theme: Theme;
  density: Density;
  reduceMotion: boolean;
  onClose: () => void;
  onThemeChange: (theme: Theme) => void;
  onDensityChange: (density: Density) => void;
  onReduceMotionChange: (enabled: boolean) => void;
}

export function PersonalSettings({ open, theme, density, reduceMotion, onClose, onThemeChange, onDensityChange, onReduceMotionChange }: PersonalSettingsProps) {
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="settings-overlay" role="presentation" onMouseDown={onClose}>
      <aside className="settings-drawer" role="dialog" aria-modal="true" aria-labelledby="settings-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="settings-header">
          <div>
            <span className="settings-kicker">Không gian làm việc</span>
            <h2 id="settings-title"><SlidersHorizontal size={18} weight="duotone" /> Cài đặt cá nhân</h2>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Đóng cài đặt"><X size={18} /></button>
        </header>
        <div className="settings-content">
          <section className="settings-section" aria-labelledby="appearance-title">
            <h3 id="appearance-title">Giao diện</h3>
            <p>Những tuỳ chọn này chỉ áp dụng trên trình duyệt hiện tại.</p>
            <div className="settings-choice-grid" role="radiogroup" aria-label="Chế độ giao diện">
              {([{ id: 'light', label: 'Sáng', Icon: Sun }, { id: 'dark', label: 'Tối', Icon: Moon }] as const).map(({ id, label, Icon }) => (
                <button key={id} type="button" role="radio" aria-checked={theme === id} className={`settings-choice ${theme === id ? 'active' : ''}`} onClick={() => onThemeChange(id)}>
                  <span className="settings-choice-leading"><Icon size={17} weight="duotone" /><span>{label}</span></span><span className="settings-choice-check" aria-hidden="true">{theme === id && <Check size={15} weight="bold" />}</span>
                </button>
              ))}
            </div>
          </section>
          <section className="settings-section" aria-labelledby="density-title">
            <h3 id="density-title">Mật độ dữ liệu</h3>
            <p><strong>Thoáng</strong> tăng khoảng cách giữa các hàng để dễ đọc; <strong>Gọn</strong> thu hẹp hàng bảng để xem được nhiều dữ liệu hơn trên một màn hình.</p>
            <div className="settings-choice-grid" role="radiogroup" aria-label="Mật độ dữ liệu">
              {([{ id: 'comfortable', label: 'Thoáng' }, { id: 'compact', label: 'Gọn' }] as const).map(({ id, label }) => (
                <button key={id} type="button" role="radio" aria-checked={density === id} className={`settings-choice ${density === id ? 'active' : ''}`} onClick={() => onDensityChange(id)}>
                  <span>{label}</span><span className="settings-choice-check" aria-hidden="true">{density === id && <Check size={15} weight="bold" />}</span>
                </button>
              ))}
            </div>
          </section>
          <section className="settings-section settings-toggle-row">
            <div><h3>Giảm chuyển động</h3><p>Tắt hoặc rút ngắn hiệu ứng chuyển trang, modal và phản hồi nút; phù hợp khi bạn dễ bị phân tán hoặc nhạy cảm với chuyển động.</p></div>
            <button type="button" role="switch" aria-checked={reduceMotion} className={`preference-switch ${reduceMotion ? 'active' : ''}`} onClick={() => onReduceMotionChange(!reduceMotion)}><span /></button>
          </section>
        </div>
      </aside>
    </div>,
    document.body,
  );
}
