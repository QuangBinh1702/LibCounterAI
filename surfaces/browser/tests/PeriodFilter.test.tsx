import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PeriodFilter } from '../src/components/PeriodFilter'

describe('PeriodFilter', () => {
  const baseProps = {
    preset: 'day' as const,
    rangeLabel: '10 Thg 7, 2026',
    onPresetChange: vi.fn(),
    fromDate: '2026-07-10',
    toDate: '2026-07-10',
    onFromChange: vi.fn(),
    onToChange: vi.fn(),
    onApply: vi.fn(),
    applying: false,
  }

  it('renders range label', () => {
    render(<PeriodFilter {...baseProps} />)
    expect(screen.getByText(/10 Thg 7, 2026/)).toBeInTheDocument()
  })

  it('renders preset buttons', () => {
    render(<PeriodFilter {...baseProps} />)
    expect(screen.getByText('Ngày')).toBeInTheDocument()
    expect(screen.getByText('Tuần')).toBeInTheDocument()
    expect(screen.getByText('Tháng')).toBeInTheDocument()
  })

  it('marks active preset', () => {
    render(<PeriodFilter {...baseProps} preset="month" />)
    const buttons = screen.getAllByRole('button')
    const monthBtn = buttons.find((b) => b.textContent === 'Tháng')
    expect(monthBtn?.className).toContain('active')
  })

  it('uses data-testid', () => {
    render(<PeriodFilter {...baseProps} />)
    expect(screen.getByTestId('period-filter')).toBeInTheDocument()
  })

  it('disables apply button when applying', () => {
    render(<PeriodFilter {...baseProps} applying={true} />)
    expect(screen.getByText('Áp dụng').closest('button')).toBeDisabled()
  })
})
