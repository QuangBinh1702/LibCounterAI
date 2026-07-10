import { describe, it, expect } from 'vitest'
import { rangeForPreset, formatRangeLabel, periodQuery, periodShortLabel } from '../src/utils/dateRange'

describe('rangeForPreset', () => {
  it('returns same from/to for day preset', () => {
    const r = rangeForPreset('day', new Date(2026, 6, 10))
    expect(r.from).toBe('2026-07-10')
    expect(r.to).toBe('2026-07-10')
  })

  it('returns Monday-start week for week preset (Tue → Mon)', () => {
    const r = rangeForPreset('week', new Date(2026, 6, 14))
    expect(r.from).toBe('2026-07-13')
    expect(r.to).toBe('2026-07-19')
  })

  it('returns Monday-start week for week preset (Sun → previous Mon)', () => {
    const r = rangeForPreset('week', new Date(2026, 6, 12))
    expect(r.from).toBe('2026-07-06')
    expect(r.to).toBe('2026-07-12')
  })

  it('returns full month for month preset', () => {
    const r = rangeForPreset('month', new Date(2026, 6, 10))
    expect(r.from).toBe('2026-07-01')
    expect(r.to).toBe('2026-07-31')
  })
})

describe('periodQuery', () => {
  it('uses date param when from === to', () => {
    expect(periodQuery({ from: '2026-07-10', to: '2026-07-10' })).toBe('date=2026-07-10')
  })

  it('uses from_date/to_date when range differs', () => {
    const q = periodQuery({ from: '2026-07-01', to: '2026-07-07' })
    expect(q).toContain('from_date=2026-07-01')
    expect(q).toContain('to_date=2026-07-07')
  })

  it('encodes URI components', () => {
    const q = periodQuery({ from: '2026-07-01', to: '2026-07-07' })
    expect(q).not.toContain(' ')
  })
})

describe('formatRangeLabel', () => {
  it('returns single date for day preset', () => {
    const label = formatRangeLabel({ from: '2026-07-10', to: '2026-07-10' }, 'day')
    expect(label).toContain('10')
    expect(label).toContain('2026')
  })
})

describe('periodShortLabel', () => {
  it('returns ngày for day', () => expect(periodShortLabel('day')).toBe('ngày'))
  it('returns tuần for week', () => expect(periodShortLabel('week')).toBe('tuần'))
  it('returns tháng for month', () => expect(periodShortLabel('month')).toBe('tháng'))
})
