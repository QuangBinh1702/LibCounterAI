import { useState, useEffect } from 'react';
import { ChartBar } from '@phosphor-icons/react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { SkeletonRows } from './Skeleton';
import { PeriodFilter } from './PeriodFilter';
import { ExportMenu, type ExportFormat } from './ExportMenu';
import { TrafficChart } from './TrafficChart';
import {
  formatRangeLabel, periodQuery, periodShortLabel,
  rangeForPreset, type PeriodPreset,
} from '../utils/dateRange';
import { exportSessionsCsv, exportSessionsExcel, exportSessionsPdf } from '../utils/exportSessions';

const ICON = { size: 16, weight: 'regular' as const };

interface OccupancyStats {
  current_occupancy: number;
  total_entries_today: number;
  total_exits_today: number;
  known_visitors_today: number;
  unknown_visitors_today: number;
  total_sessions_today: number;
}

interface HourlyStat {
  hour: number;
  entry: number;
  exit: number;
}

interface VisitSession {
  id: number;
  person_name: string;
  member_code: string | null;
  entry_at: string | null;
  exit_at: string | null;
  duration_seconds: number | null;
  status: string;
}

export function AnalyticsPage() {
  const { apiFetch } = useAuth();
  const { show: showToast } = useToast();

  const initialRange = rangeForPreset('day');
  const [periodPreset, setPeriodPreset] = useState<PeriodPreset>('day');
  const [rangeFrom, setRangeFrom] = useState(initialRange.from);
  const [rangeTo, setRangeTo] = useState(initialRange.to);
  const [draftFrom, setDraftFrom] = useState(initialRange.from);
  const [draftTo, setDraftTo] = useState(initialRange.to);
  const [loading, setLoading] = useState(false);
  const [occupancy, setOccupancy] = useState<OccupancyStats>({
    current_occupancy: 0, total_entries_today: 0, total_exits_today: 0,
    known_visitors_today: 0, unknown_visitors_today: 0, total_sessions_today: 0,
  });
  const [hourlyStats, setHourlyStats] = useState<HourlyStat[]>([]);

  const reportQuery = () => periodQuery({ from: rangeFrom, to: rangeTo });
  const activeRangeLabel = formatRangeLabel({ from: rangeFrom, to: rangeTo }, periodPreset);

  useEffect(() => { loadAnalytics(); }, [rangeFrom, rangeTo]);

  const applyPeriodPreset = (preset: PeriodPreset) => {
    const next = rangeForPreset(preset);
    setPeriodPreset(preset);
    setDraftFrom(next.from);
    setDraftTo(next.to);
    setRangeFrom(next.from);
    setRangeTo(next.to);
  };

  const applyCustomRange = () => {
    if (!draftFrom || !draftTo) {
      showToast('Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc.', 'error');
      return;
    }
    if (draftFrom > draftTo) {
      showToast('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.', 'error');
      return;
    }
    setPeriodPreset(draftFrom === draftTo ? 'day' : 'week');
    setRangeFrom(draftFrom);
    setRangeTo(draftTo);
  };

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const q = reportQuery();
      const resOcc = apiFetch(`/api/stats/occupancy?${q}`);
      const resHourly = apiFetch(`/api/stats/hourly?${q}`);
      const [occResult, hourlyResult] = await Promise.all([resOcc, resHourly]);
      if (occResult.ok && hourlyResult.ok) {
        setOccupancy(await occResult.json());
        const hourly = await hourlyResult.json();
        const byHour = new Map<number, HourlyStat>(
          (Array.isArray(hourly) ? hourly : []).map((s: HourlyStat) => [s.hour, s]),
        );
        setHourlyStats(
          Array.from({ length: 24 }, (_, hour) => byHour.get(hour) ?? { hour, entry: 0, exit: 0 }),
        );
      } else {
        showToast('Không tải được dữ liệu thống kê.', 'error');
      }
    } catch (err) {
      console.error('Failed to load analytics:', err);
      showToast('Không tải được dữ liệu thống kê.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const parseSessionResponse = (data: unknown): VisitSession[] => {
    if (Array.isArray(data)) return data;
    if (data && typeof data === 'object' && 'items' in data && Array.isArray((data as { items: VisitSession[] }).items)) {
      return (data as { items: VisitSession[] }).items;
    }
    return [];
  };

  const handleExport = async (format: ExportFormat) => {
    try {
      const res = await apiFetch(`/api/sessions?${reportQuery()}`);
      let rows: VisitSession[] = [];
      if (res.ok) rows = parseSessionResponse(await res.json());
      if (rows.length === 0) {
        showToast('Không có dữ liệu phiên trong khoảng đã lọc để xuất.', 'error');
        return;
      }
      if (format === 'csv') exportSessionsCsv(rows, rangeFrom, rangeTo);
      else if (format === 'excel') exportSessionsExcel(rows, rangeFrom, rangeTo);
      else exportSessionsPdf(rows, rangeFrom, rangeTo, activeRangeLabel);
      showToast(`Đã xuất báo cáo ${format.toUpperCase()} theo ${periodShortLabel(periodPreset)}.`, 'success');
    } catch (err) {
      console.error('Export failed:', err);
      showToast('Xuất file thất bại.', 'error');
    }
  };

  return (
    <div className="page-stack page-view">
      <div className="section-toolbar analytics-toolbar">
        <h2 className="panel-title"><ChartBar {...ICON} /> Thống kê lưu lượng</h2>
        <div className="toolbar-actions">
          <ExportMenu onExport={handleExport} />
        </div>
      </div>
      <PeriodFilter
        preset={periodPreset}
        rangeLabel={activeRangeLabel}
        onPresetChange={applyPeriodPreset}
        fromDate={draftFrom}
        toDate={draftTo}
        onFromChange={setDraftFrom}
        onToChange={setDraftTo}
        onApply={applyCustomRange}
        applying={loading}
      />
      {loading ? (
        <><SkeletonRows rows={3} /><SkeletonRows rows={6} /></>
      ) : (
        <>
          <div className="stats-primary-grid" data-testid="analytics-cards">
            <div className="stat-card">
              <div className="stat-card-label">Đang trong thư viện</div>
              <div className="stat-card-value occupancy">{occupancy.current_occupancy}</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-label">Lượt vào</div>
              <div className="stat-card-value entry">{occupancy.total_entries_today}</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-label">Lượt ra</div>
              <div className="stat-card-value exit">{occupancy.total_exits_today}</div>
            </div>
          </div>
          <div className="stat-card-meta">
            Khoảng <strong>{activeRangeLabel}</strong>
            {' · '}Đã biết <strong>{occupancy.known_visitors_today}</strong>
            {' · '}Khách <strong>{occupancy.unknown_visitors_today}</strong>
            {' · '}Tổng phiên <strong>{occupancy.total_sessions_today}</strong>
          </div>
          <section className="panel traffic-panel">
            <TrafficChart stats={hourlyStats} rangeLabel={activeRangeLabel} />
          </section>
        </>
      )}
    </div>
  );
}
