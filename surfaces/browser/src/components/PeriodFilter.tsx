import { CalendarBlank } from '@phosphor-icons/react';
import type { PeriodPreset } from '../utils/dateRange';

const ICON_SM = { size: 14, weight: 'regular' as const };

const PRESETS: { id: PeriodPreset; label: string }[] = [
  { id: 'day', label: 'Ngày' },
  { id: 'week', label: 'Tuần' },
  { id: 'month', label: 'Tháng' },
];

interface PeriodFilterProps {
  preset: PeriodPreset;
  rangeLabel: string;
  onPresetChange: (preset: PeriodPreset) => void;
  fromDate: string;
  toDate: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  onApply: () => void;
  applying?: boolean;
}

export function PeriodFilter({
  preset,
  rangeLabel,
  onPresetChange,
  fromDate,
  toDate,
  onFromChange,
  onToChange,
  onApply,
  applying = false,
}: PeriodFilterProps) {
  return (
    <div className="period-filter" data-testid="period-filter">
      <div className="period-filter-main">
        <div className="period-presets" role="group" aria-label="Khoảng thời gian">
          {PRESETS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`period-preset ${preset === item.id ? 'is-active' : ''}`}
              aria-pressed={preset === item.id}
              data-testid={`period-${item.id}`}
              onClick={() => onPresetChange(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="period-range-label">
          <CalendarBlank {...ICON_SM} />
          <span>{rangeLabel}</span>
        </div>
      </div>

      <div className="period-custom">
        <label className="period-date-field">
          <span>Từ</span>
          <input
            type="date"
            className="text-input text-input-date"
            value={fromDate}
            onChange={(e) => onFromChange(e.target.value)}
            data-testid="period-from"
          />
        </label>
        <label className="period-date-field">
          <span>Đến</span>
          <input
            type="date"
            className="text-input text-input-date"
            value={toDate}
            min={fromDate}
            onChange={(e) => onToChange(e.target.value)}
            data-testid="period-to"
          />
        </label>
        <button
          type="button"
          className="btn btn-sm"
          onClick={onApply}
          disabled={applying}
          data-testid="period-apply"
        >
          Áp dụng
        </button>
      </div>
    </div>
  );
}
