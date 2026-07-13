import { Component, type ErrorInfo, type ReactNode } from 'react';
import { WarningCircle, ArrowClockwise, House } from '@phosphor-icons/react';

const ICON = { size: 20, weight: 'fill' as const };

interface Props {
  children: ReactNode;
  name?: string;
  onReset?: () => void;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[ErrorBoundary] ${this.props.name || 'component'}:`, error.message, info.componentStack);
  }

  handleReset = () => {
    this.setState({ error: null });
    this.props.onReset?.();
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary-fallback" role="alert">
          <div className="error-boundary-icon">
            <WarningCircle {...ICON} />
          </div>
          <h2 className="error-boundary-title">
            {this.props.name || 'Trang'} không thể hiển thị
          </h2>
          <p className="error-boundary-message">
            {this.state.error.message || 'Đã xảy ra lỗi không mong muốn.'}
          </p>
          <div className="error-boundary-actions">
            <button type="button" className="btn" onClick={this.handleReset}>
              <ArrowClockwise size={14} weight="bold" />
              Thử lại
            </button>
            <button type="button" className="btn btn-ghost" onClick={this.handleReload}>
              <House size={14} weight="bold" />
              Tải lại trang
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
