import React, { useState, useEffect } from 'react';
import { CalendarBlank } from '@phosphor-icons/react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { SkeletonRows } from './Skeleton';
import { PeriodFilter } from './PeriodFilter';
import { ExportMenu, type ExportFormat } from './ExportMenu';
import {
  formatRangeLabel, periodQuery, periodShortLabel,
  rangeForPreset, type PeriodPreset,
} from '../utils/dateRange';
import { exportSessionsCsv, exportSessionsExcel, exportSessionsPdf } from '../utils/exportSessions';

const ICON = { size: 16, weight: 'regular' as const };

interface VisitSession {
  id: number;
  person_name: string;
  member_code: string | null;
  entry_at: string | null;
  exit_at: string | null;
  duration_seconds: number | null;
  status: string;
}

export function HistoryPage() {
  const { apiFetch } = useAuth();
  const { show: showToast } = useToast();

  const [sessions, setSessions] = useState<VisitSession[]>([]);
  const [loading, setLoading] = useState(false);
  const initialRange = rangeForPreset('day');
  const [periodPreset, setPeriodPreset] = useState<PeriodPreset>('day');
  const [rangeFrom, setRangeFrom] = useState(initialRange.from);
  const [rangeTo, setRangeTo] = useState(initialRange.to);
  const [draftFrom, setDraftFrom] = useState(initialRange.from);
  const [draftTo, setDraftTo] = useState(initialRange.to);

  const reportQuery = () => periodQuery({ from: rangeFrom, to: rangeTo });
  const activeRangeLabel = formatRangeLabel({ from: rangeFrom, to: rangeTo }, periodPreset);

  useEffect(() => { loadFilteredSessions(); }, [rangeFrom, rangeTo]);

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

  const parseSessionResponse = (data: unknown): VisitSession[] => {
    if (Array.isArray(data)) return data;
    if (data && typeof data === 'object' && 'items' in data && Array.isArray((data as { items: VisitSession[] }).items)) {
      return (data as { items: VisitSession[] }).items;
    }
    return [];
  };

  const loadFilteredSessions = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/sessions?${reportQuery()}`);
      if (res.ok) setSessions(parseSessionResponse(await res.json()));
      else showToast('Không lọc được dữ liệu theo khoảng đã chọn.', 'error');
    } catch (err) {
      console.error('Failed to load filtered sessions:', err);
      showToast('Không tải được lịch sử phiên.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: ExportFormat) => {
    try {
      let rows = sessions;
      const res = await apiFetch(`/api/sessions?${reportQuery()}`);
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
      <section className="panel panel-grow">
        <div className="section-toolbar">
          <h2 className="panel-title"><CalendarBlank {...ICON} /> Lịch sử ra/vào</h2>
          <div className="toolbar-actions">
            <ExportMenu onExport={handleExport} disabled={loading} />
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
          <SkeletonRows rows={8} />
        ) : (
          <div className="table-wrapper">
            <table className="data-table" data-testid="sessions-table">
              <thead>
                <tr>
                  <th>Phiên</th>
                  <th>Tên</th>
                  <th>Mã thẻ</th>
                  <th>Giờ vào</th>
                  <th>Giờ ra</th>
                  <th>Thời lượng</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {sessions.length === 0 ? (
                  <tr>
                    <td colSpan={7}>
                      <div className="empty-state">
                        <div className="empty-state-title">Chưa có phiên nào</div>
                        Không có dữ liệu trong khoảng {activeRangeLabel}.
                      </div>
                    </td>
                  </tr>
                ) : (
                  sessions.map((s) => (
                    <tr key={s.id}>
                      <td className="mono">{s.id}</td>
                      <td className="cell-strong">{s.person_name}</td>
                      <td className="mono muted">{s.member_code || 'N/A'}</td>
                      <td>{s.entry_at ? new Date(s.entry_at).toLocaleString('vi-VN') : 'N/A'}</td>
                      <td>{s.exit_at ? new Date(s.exit_at).toLocaleString('vi-VN') : 'N/A'}</td>
                      <td className="mono">{s.duration_seconds !== null ? `${s.duration_seconds}s` : 'N/A'}</td>
                      <td>
                        <span className={`badge ${s.status === 'ACTIVE' ? 'warning' : 'success'}`}>
                          {s.status === 'ACTIVE' ? 'Đang trong' : 'Đã ra'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
