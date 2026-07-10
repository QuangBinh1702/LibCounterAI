import { useEffect, useRef, useState } from 'react';
import {
  CaretDown,
  DownloadSimple,
  FileCsv,
  FilePdf,
  FileXls,
} from '@phosphor-icons/react';

const ICON_SM = { size: 14, weight: 'regular' as const };

export type ExportFormat = 'csv' | 'excel' | 'pdf';

interface ExportMenuProps {
  onExport: (format: ExportFormat) => void;
  disabled?: boolean;
}

export function ExportMenu({ onExport, disabled = false }: ExportMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const choose = (format: ExportFormat) => {
    setOpen(false);
    onExport(format);
  };

  return (
    <div className={`export-menu ${open ? 'is-open' : ''}`} ref={rootRef}>
      <button
        type="button"
        className="btn btn-sm export-trigger"
        data-testid="export-menu"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
      >
        <DownloadSimple {...ICON_SM} />
        Xuất file
        <CaretDown size={12} weight="bold" className="export-caret" />
      </button>

      {open && (
        <div className="export-dropdown" role="menu" aria-label="Xuất định dạng">
          <div className="export-dropdown-title">Xuất định dạng</div>
          <button type="button" role="menuitem" className="export-option" onClick={() => choose('excel')}>
            <FileXls {...ICON_SM} />
            Excel (.xlsx)
          </button>
          <button type="button" role="menuitem" className="export-option" onClick={() => choose('pdf')}>
            <FilePdf {...ICON_SM} />
            PDF
          </button>
          <button
            type="button"
            role="menuitem"
            className="export-option"
            data-testid="export-csv"
            onClick={() => choose('csv')}
          >
            <FileCsv {...ICON_SM} />
            CSV
          </button>
        </div>
      )}
    </div>
  );
}
