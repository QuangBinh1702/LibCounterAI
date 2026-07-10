import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VideoCamera, Users } from '@phosphor-icons/react'
import { NavTabs } from '../src/components/NavTabs'

const tabs = [
  { id: 'monitor' as const, label: 'Giám sát', Icon: VideoCamera },
  { id: 'registry' as const, label: 'Thành viên', Icon: Users },
]

describe('NavTabs', () => {
  it('renders all tabs', () => {
    render(<NavTabs tabs={tabs} activeTab="monitor" onChange={vi.fn()} iconProps={{ size: 14, weight: 'regular' }} />)
    expect(screen.getByText('Giám sát')).toBeInTheDocument()
    expect(screen.getByText('Thành viên')).toBeInTheDocument()
  })

  it('marks active tab', () => {
    render(<NavTabs tabs={tabs} activeTab="registry" onChange={vi.fn()} iconProps={{ size: 14, weight: 'regular' }} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons[1].className).toContain('active')
  })

  it('allows no active tab when admin view is open', () => {
    render(<NavTabs tabs={tabs} activeTab={null} onChange={vi.fn()} iconProps={{ size: 14, weight: 'regular' }} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons.every((btn) => !btn.className.includes('active'))).toBe(true)
  })

  it('calls onChange with tab id', () => {
    const onChange = vi.fn()
    render(<NavTabs tabs={tabs} activeTab="monitor" onChange={onChange} iconProps={{ size: 14, weight: 'regular' }} />)
    screen.getByText('Thành viên').click()
    expect(onChange).toHaveBeenCalledWith('registry')
  })

  it('uses data-testid attribute', () => {
    render(<NavTabs tabs={tabs} activeTab="monitor" onChange={vi.fn()} iconProps={{ size: 14, weight: 'regular' }} />)
    expect(screen.getByTestId('nav-tabs')).toBeInTheDocument()
  })
})
