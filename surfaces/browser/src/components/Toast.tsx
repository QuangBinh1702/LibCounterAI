import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle, XCircle, Info, X } from '@phosphor-icons/react';
import type { ToastItem } from '../hooks/useToast';
import { useEffect, useState } from 'react';

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

const iconMap: Record<string, React.ReactNode> = {
  success: <CheckCircle size={20} weight="fill" />,
  error: <XCircle size={20} weight="fill" />,
  info: <Info size={20} weight="fill" />,
};

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: string) => void }) {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    const duration = toast.duration ?? 3800;
    const start = performance.now();
    let animId: number;
    function tick(now: number) {
      const elapsed = now - start;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);
      if (remaining > 0) animId = requestAnimationFrame(tick);
    }
    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, [toast.id, toast.duration]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      className={`toast toast-${toast.type}`}
    >
      <div className="toast-accent" />
      <div className="toast-body">
        <div className="toast-content">
          <span className="toast-icon">{iconMap[toast.type]}</span>
          <span className="toast-message">{toast.message}</span>
        </div>
        <button
          type="button"
          className="toast-dismiss"
          onClick={() => onDismiss(toast.id)}
          aria-label="Đóng thông báo"
        >
          <X size={14} weight="bold" />
        </button>
      </div>
      <div className="toast-progress-track">
        <div className="toast-progress-bar" style={{ width: `${progress}%` }} />
      </div>
    </motion.div>
  );
}
