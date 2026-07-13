import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExportMenu } from '../src/components/ExportMenu'

describe('ExportMenu', () => {
  it('renders export trigger button', () => {
    render(<ExportMenu onExport={vi.fn()} />)
    expect(screen.getByTestId('export-menu')).toBeInTheDocument()
    expect(screen.getByText('Xuất file')).toBeInTheDocument()
  })

  it('is disabled when disabled prop is true', () => {
    render(<ExportMenu onExport={vi.fn()} disabled={true} />)
    expect(screen.getByTestId('export-menu')).toBeDisabled()
  })

  it('opens dropdown on trigger click', async () => {
    const user = userEvent.setup()
    render(<ExportMenu onExport={vi.fn()} />)
    await user.click(screen.getByTestId('export-menu'))
    expect(screen.getByText('Excel (.xlsx)')).toBeInTheDocument()
    expect(screen.getByText('PDF')).toBeInTheDocument()
    expect(screen.getByText('CSV')).toBeInTheDocument()
  })

  it('calls onExport with csv format', async () => {
    const onExport = vi.fn()
    const user = userEvent.setup()
    render(<ExportMenu onExport={onExport} />)
    await user.click(screen.getByTestId('export-menu'))
    await user.click(screen.getByTestId('export-csv'))
    expect(onExport).toHaveBeenCalledWith('csv')
  })

  it('calls onExport with excel format', async () => {
    const onExport = vi.fn()
    const user = userEvent.setup()
    render(<ExportMenu onExport={onExport} />)
    await user.click(screen.getByTestId('export-menu'))
    await user.click(screen.getByText('Excel (.xlsx)'))
    expect(onExport).toHaveBeenCalledWith('excel')
  })

  it('calls onExport with pdf format', async () => {
    const onExport = vi.fn()
    const user = userEvent.setup()
    render(<ExportMenu onExport={onExport} />)
    await user.click(screen.getByTestId('export-menu'))
    await user.click(screen.getByText('PDF'))
    expect(onExport).toHaveBeenCalledWith('pdf')
  })

  it('closes dropdown after choosing format', async () => {
    const user = userEvent.setup()
    render(<ExportMenu onExport={vi.fn()} />)
    await user.click(screen.getByTestId('export-menu'))
    expect(screen.getByText('Excel (.xlsx)')).toBeInTheDocument()
    await user.click(screen.getByText('CSV'))
    expect(screen.queryByText('Excel (.xlsx)')).not.toBeInTheDocument()
  })

  it('sets aria-expanded correctly', async () => {
    const user = userEvent.setup()
    render(<ExportMenu onExport={vi.fn()} />)
    const trigger = screen.getByTestId('export-menu')
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
  })

  it('closes on Escape key', async () => {
    const user = userEvent.setup()
    render(<ExportMenu onExport={vi.fn()} />)
    await user.click(screen.getByTestId('export-menu'))
    expect(screen.getByText('Excel (.xlsx)')).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByText('Excel (.xlsx)')).not.toBeInTheDocument()
  })

  it('closes on outside click', async () => {
    const user = userEvent.setup()
    render(<ExportMenu onExport={vi.fn()} />)
    await user.click(screen.getByTestId('export-menu'))
    expect(screen.getByText('Excel (.xlsx)')).toBeInTheDocument()
    await user.click(document.body)
    expect(screen.queryByText('Excel (.xlsx)')).not.toBeInTheDocument()
  })
})
