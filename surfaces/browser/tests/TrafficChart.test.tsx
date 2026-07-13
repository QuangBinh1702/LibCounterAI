import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TrafficChart } from '../src/components/TrafficChart'

const sampleStats = [
  { hour: 8, entry: 10, exit: 2 },
  { hour: 9, entry: 25, exit: 5 },
  { hour: 10, entry: 15, exit: 8 },
  { hour: 11, entry: 5, exit: 20 },
]

describe('TrafficChart', () => {
  it('renders title and range label', () => {
    render(<TrafficChart stats={[]} rangeLabel="10 Thg 7, 2026" />)
    expect(screen.getByText('Lưu lượng theo giờ')).toBeInTheDocument()
    expect(screen.getByText('10 Thg 7, 2026')).toBeInTheDocument()
  })

  it('renders legend items', () => {
    render(<TrafficChart stats={sampleStats} rangeLabel="test" />)
    expect(screen.getByText('Vào')).toBeInTheDocument()
    expect(screen.getByText('Ra')).toBeInTheDocument()
  })

  it('computes total entry correctly', () => {
    render(<TrafficChart stats={sampleStats} rangeLabel="test" />)
    expect(screen.getByText('55')).toBeInTheDocument()
  })

  it('computes total exit correctly', () => {
    render(<TrafficChart stats={sampleStats} rangeLabel="test" />)
    expect(screen.getByText('35')).toBeInTheDocument()
  })

  it('identifies peak hour in signal section', () => {
    render(<TrafficChart stats={sampleStats} rangeLabel="test" />)
    const peakLabel = screen.getByText('Cao điểm')
    const signalSection = peakLabel.parentElement!
    expect(signalSection.textContent).toContain('09:00')
    expect(signalSection.textContent).toContain('30')
  })

  it('shows empty state when no data', () => {
    render(<TrafficChart stats={[]} rangeLabel="test" />)
    expect(screen.getByText('Chưa có dữ liệu lưu lượng trong khoảng đã chọn.')).toBeInTheDocument()
  })

  it('shows dash for peak when no data', () => {
    render(<TrafficChart stats={[]} rangeLabel="test" />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('shows no-data message for peak when no data', () => {
    render(<TrafficChart stats={[]} rangeLabel="test" />)
    expect(screen.getByText('Chưa có dữ liệu')).toBeInTheDocument()
  })

  it('renders bars with correct aria-labels', () => {
    render(<TrafficChart stats={sampleStats} rangeLabel="test" />)
    const plot = screen.getByRole('img', { name: /lưu lượng theo giờ/i })
    expect(plot).toBeInTheDocument()
  })

  it('shows single-hour entry/exit totals', () => {
    render(<TrafficChart stats={[{ hour: 14, entry: 3, exit: 1 }]} rangeLabel="test" />)
    expect(screen.getAllByText('3').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('1')).toBeInTheDocument()
  })
})
