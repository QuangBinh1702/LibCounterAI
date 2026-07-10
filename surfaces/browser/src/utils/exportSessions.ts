import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { robotoBase64 } from './robotoBase64';

export interface ExportSessionRow {
  id: number;
  person_name: string;
  member_code: string | null;
  entry_at: string | null;
  exit_at: string | null;
  duration_seconds: number | null;
  status: string;
}

function identityType(name: string): string {
  return name.startsWith('UNKNOWN_') ? 'Khách' : 'Đã biết';
}

function formatWhen(value: string | null): string {
  return value ? new Date(value).toLocaleString('vi-VN') : '';
}

function rowsForExport(sessions: ExportSessionRow[]) {
  return sessions.map((s) => ({
    'Phiên': s.id,
    'Tên': s.person_name || '',
    'Mã thẻ': s.member_code || '',
    'Loại': identityType(s.person_name || ''),
    'Giờ vào': formatWhen(s.entry_at),
    'Giờ ra': formatWhen(s.exit_at),
    'Thời lượng (s)': s.duration_seconds ?? '',
    'Trạng thái': s.status === 'ACTIVE' ? 'Đang trong' : 'Đã ra',
  }));
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function stamp(rangeFrom: string, rangeTo: string): string {
  if (rangeFrom === rangeTo) return rangeFrom;
  return `${rangeFrom}_${rangeTo}`;
}

export function exportSessionsCsv(sessions: ExportSessionRow[], rangeFrom: string, rangeTo: string) {
  const rows = rowsForExport(sessions);
  const sheet = XLSX.utils.json_to_sheet(rows);
  const csvContent = XLSX.utils.sheet_to_csv(sheet);
  // BOM makes Excel detect the UTF-8 encoding and preserve Vietnamese accents.
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(blob, `libcounterai_sessions_${stamp(rangeFrom, rangeTo)}.csv`);
}

export function exportSessionsExcel(sessions: ExportSessionRow[], rangeFrom: string, rangeTo: string) {
  const rows = rowsForExport(sessions);
  const sheet = XLSX.utils.json_to_sheet(rows);
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, sheet, 'Sessions');
  XLSX.writeFile(book, `libcounterai_sessions_${stamp(rangeFrom, rangeTo)}.xlsx`);
}

function registerFont(doc: jsPDF) {
  doc.addFileToVFS('Roboto-Regular.ttf', robotoBase64);
  doc.addFont('Roboto-Regular.ttf', 'Roboto', 'normal');
  doc.setFont('Roboto');
}

export function exportSessionsPdf(
  sessions: ExportSessionRow[],
  rangeFrom: string,
  rangeTo: string,
  rangeLabel: string,
) {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
  registerFont(doc);

  doc.setFontSize(14);
  doc.text('LibCounterAI - Lịch sử ra/vào', 40, 36);
  doc.setFontSize(10);
  doc.text(`Khoảng: ${rangeLabel}`, 40, 54);

  const body = sessions.map((s) => [
    String(s.id),
    s.person_name || '',
    s.member_code || 'N/A',
    identityType(s.person_name || ''),
    formatWhen(s.entry_at) || 'N/A',
    formatWhen(s.exit_at) || 'N/A',
    s.duration_seconds !== null ? String(s.duration_seconds) : 'N/A',
    s.status === 'ACTIVE' ? 'Đang trong' : 'Đã ra',
  ]);

  autoTable(doc, {
    startY: 68,
    head: [['Phiên', 'Tên', 'Mã thẻ', 'Loại', 'Giờ vào', 'Giờ ra', 'Thời lượng (s)', 'Trạng thái']],
    body,
    // Only Roboto-Regular is embedded. autoTable defaults headers to bold,
    // which makes jsPDF fall back to a different font encoding for accented
    // Vietnamese glyphs. Keep every table cell on the registered font/style.
    styles: { fontSize: 8, cellPadding: 4, font: 'Roboto', fontStyle: 'normal' },
    headStyles: { fillColor: [79, 70, 229], font: 'Roboto', fontStyle: 'normal' },
  });

  doc.save(`libcounterai_sessions_${stamp(rangeFrom, rangeTo)}.pdf`);
}
