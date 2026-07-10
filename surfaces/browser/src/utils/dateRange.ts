export type PeriodPreset = 'day' | 'week' | 'month';

export interface DateRange {
  from: string;
  to: string;
}

function toIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function startOfLocalDay(date = new Date()): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/** Monday-start week containing `anchor`. */
function startOfWeek(anchor: Date): Date {
  const day = startOfLocalDay(anchor);
  const weekday = day.getDay(); // 0 Sun .. 6 Sat
  const offset = weekday === 0 ? 6 : weekday - 1;
  day.setDate(day.getDate() - offset);
  return day;
}

export function rangeForPreset(preset: PeriodPreset, anchor = new Date()): DateRange {
  const today = startOfLocalDay(anchor);

  if (preset === 'day') {
    const iso = toIsoDate(today);
    return { from: iso, to: iso };
  }

  if (preset === 'week') {
    const from = startOfWeek(today);
    const to = new Date(from);
    to.setDate(from.getDate() + 6);
    return { from: toIsoDate(from), to: toIsoDate(to) };
  }

  const from = new Date(today.getFullYear(), today.getMonth(), 1);
  const to = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  return { from: toIsoDate(from), to: toIsoDate(to) };
}

export function formatRangeLabel(range: DateRange, preset: PeriodPreset): string {
  const from = new Date(`${range.from}T00:00:00`);
  const to = new Date(`${range.to}T00:00:00`);
  const opts: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'short', year: 'numeric' };
  const fromLabel = from.toLocaleDateString('vi-VN', opts);
  const toLabel = to.toLocaleDateString('vi-VN', opts);

  if (preset === 'day' || range.from === range.to) return fromLabel;
  return `${fromLabel} – ${toLabel}`;
}

export function periodQuery(range: DateRange): string {
  if (range.from === range.to) return `date=${encodeURIComponent(range.from)}`;
  return `from_date=${encodeURIComponent(range.from)}&to_date=${encodeURIComponent(range.to)}`;
}

export function periodShortLabel(preset: PeriodPreset): string {
  if (preset === 'day') return 'ngày';
  if (preset === 'week') return 'tuần';
  return 'tháng';
}
