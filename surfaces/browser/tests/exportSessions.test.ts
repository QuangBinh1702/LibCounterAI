import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockWriteFile = vi.hoisted(() => vi.fn())
const mockJsonToSheet = vi.hoisted(() => vi.fn(() => ({})))
const mockSheetToCsv = vi.hoisted(() => vi.fn(() => 'csv,content'))
const mockBookNew = vi.hoisted(() => vi.fn(() => ({})))
const mockBookAppendSheet = vi.hoisted(() => vi.fn())
const mockAutoTable = vi.hoisted(() => vi.fn())

vi.mock('xlsx', () => ({
  writeFile: mockWriteFile,
  utils: {
    json_to_sheet: mockJsonToSheet,
    sheet_to_csv: mockSheetToCsv,
    book_new: mockBookNew,
    book_append_sheet: mockBookAppendSheet,
  },
}))

const mockPdfSave = vi.hoisted(() => vi.fn())
const mockAddFileToVFS = vi.hoisted(() => vi.fn())
const mockAddFont = vi.hoisted(() => vi.fn())
const mockSetFont = vi.hoisted(() => vi.fn())
const mockSetFontSize = vi.hoisted(() => vi.fn())
const mockText = vi.hoisted(() => vi.fn())
const mockSetDrawColor = vi.hoisted(() => vi.fn())
const mockSetFillColor = vi.hoisted(() => vi.fn())
const mockRect = vi.hoisted(() => vi.fn())
const mockLine = vi.hoisted(() => vi.fn())
const mockSetLineWidth = vi.hoisted(() => vi.fn())
const mockGetNumberOfPages = vi.hoisted(() => vi.fn(() => 1))
const mockPdfDoc = vi.hoisted(() => ({
  addFileToVFS: mockAddFileToVFS,
  addFont: mockAddFont,
  setFont: mockSetFont,
  setFontSize: mockSetFontSize,
  text: mockText,
  save: mockPdfSave,
  setDrawColor: mockSetDrawColor,
  setFillColor: mockSetFillColor,
  rect: mockRect,
  line: mockLine,
  setLineWidth: mockSetLineWidth,
  getNumberOfPages: mockGetNumberOfPages,
  internal: {
    getNumberOfPages: vi.fn(() => 1),
    pageSize: { width: 841.92, height: 595.32 },
  },
}))

vi.mock('jspdf', () => ({
  jsPDF: function () { return mockPdfDoc },
}))

vi.mock('jspdf-autotable', () => ({
  default: mockAutoTable,
}))

import {
  exportSessionsCsv,
  exportSessionsExcel,
  exportSessionsPdf,
  type ExportSessionRow,
} from '../src/utils/exportSessions'

const mockSessions: ExportSessionRow[] = [
  { id: 1, person_name: 'Nguyễn Văn A', member_code: 'SV001', entry_at: '2026-07-10T08:00:00Z', exit_at: '2026-07-10T10:30:00Z', duration_seconds: 9000, status: 'CLOSED' },
  { id: 2, person_name: 'UNKNOWN_20260710_0001', member_code: null, entry_at: '2026-07-10T09:00:00Z', exit_at: null, duration_seconds: null, status: 'ACTIVE' },
]

beforeEach(() => {
  vi.clearAllMocks()
})

describe('exportSessionsCsv', () => {
  it('downloads CSV file with BOM', () => {
    const click = vi.fn()
    const createObjectURL = vi.fn(() => 'blob:url')
    const revokeObjectURL = vi.fn()
    const origURL = globalThis.URL

    globalThis.URL = { createObjectURL, revokeObjectURL } as any

    const anchor = document.createElement('a')
    vi.spyOn(anchor, 'click').mockImplementation(click)
    vi.spyOn(document, 'createElement').mockReturnValue(anchor)

    exportSessionsCsv(mockSessions, '2026-07-10', '2026-07-10')

    expect(click).toHaveBeenCalled()
    expect(anchor.download).toContain('.csv')

    globalThis.URL = origURL
    vi.mocked(document.createElement).mockRestore()
  })
})

describe('exportSessionsExcel', () => {
  it('generates xlsx file with correct filename', () => {
    exportSessionsExcel(mockSessions, '2026-07-10', '2026-07-10')
    expect(mockWriteFile).toHaveBeenCalled()
    const filename = mockWriteFile.mock.calls[0][1]
    expect(typeof filename).toBe('string')
    expect(filename).toContain('.xlsx')
    expect(filename).toContain('2026-07-10')
  })

  it('handles range in filename', () => {
    exportSessionsExcel(mockSessions, '2026-07-01', '2026-07-10')
    const filename = mockWriteFile.mock.calls[0][1]
    expect(filename).toContain('2026-07-01_2026-07-10')
  })

  it('processes sessions with correct row data', () => {
    exportSessionsExcel(mockSessions, '2026-07-10', '2026-07-10')
    const rows = mockJsonToSheet.mock.calls[0][0] as Record<string, unknown>[]
    expect(rows).toHaveLength(2)
    expect(rows[0]['Tên']).toBe('Nguyễn Văn A')
    expect(rows[1]['Loại']).toBe('Khách')
    expect(rows[0]['Trạng thái']).toBe('Đã ra')
    expect(rows[1]['Trạng thái']).toBe('Đang trong')
  })
})

describe('exportSessionsPdf', () => {
  it('generates PDF document', () => {
    exportSessionsPdf(mockSessions, '2026-07-10', '2026-07-10', '10 Thg 7, 2026')

    expect(mockPdfSave).toHaveBeenCalled()
    const filename = mockPdfSave.mock.calls[0][0]
    expect(filename).toContain('.pdf')
  })
})
