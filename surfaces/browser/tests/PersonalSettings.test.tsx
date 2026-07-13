import { describe, it, expect, vi } from 'vitest'
import { render as rtlRender, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PersonalSettings } from '../src/components/PersonalSettings'
import { AuthProvider } from '../src/hooks/useAuth'
import { ToastProvider } from '../src/hooks/useToast'

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ToastProvider>{children}</ToastProvider>
    </AuthProvider>
  )
}

function render(ui: React.ReactElement, options = {}) {
  return rtlRender(ui, { wrapper: Wrapper, ...options })
}

describe('PersonalSettings', () => {
  const baseProps = {
    open: true,
    theme: 'light' as const,
    density: 'comfortable' as const,
    reduceMotion: false,
    onClose: vi.fn(),
    onThemeChange: vi.fn(),
    onDensityChange: vi.fn(),
    onReduceMotionChange: vi.fn(),
  }

  it('renders nothing when closed', () => {
    render(<PersonalSettings {...baseProps} open={false} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('renders dialog when open', () => {
    render(<PersonalSettings {...baseProps} />)
    expect(screen.getByText('Cài đặt cá nhân')).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('renders theme options', () => {
    render(<PersonalSettings {...baseProps} />)
    expect(screen.getByText('Sáng')).toBeInTheDocument()
    expect(screen.getByText('Tối')).toBeInTheDocument()
  })

  it('renders density options', () => {
    render(<PersonalSettings {...baseProps} />)
    expect(screen.getAllByText('Thoáng').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Gọn').length).toBeGreaterThanOrEqual(1)
  })

  it('renders reduce motion toggle', () => {
    render(<PersonalSettings {...baseProps} />)
    expect(screen.getByText('Giảm chuyển động')).toBeInTheDocument()
  })

  it('marks active theme as aria-checked', () => {
    render(<PersonalSettings {...baseProps} theme="dark" />)
    const buttons = screen.getAllByRole('radio')
    const darkBtn = buttons.find((b) => b.textContent?.includes('Tối'))
    expect(darkBtn).toHaveAttribute('aria-checked', 'true')
    const lightBtn = buttons.find((b) => b.textContent?.includes('Sáng'))
    expect(lightBtn).toHaveAttribute('aria-checked', 'false')
  })

  it('calls onThemeChange when theme is clicked', async () => {
    const onThemeChange = vi.fn()
    const user = userEvent.setup()
    render(<PersonalSettings {...baseProps} onThemeChange={onThemeChange} />)
    const buttons = screen.getAllByRole('radio')
    const darkBtn = buttons.find((b) => b.textContent?.includes('Tối'))
    await user.click(darkBtn!)
    expect(onThemeChange).toHaveBeenCalledWith('dark')
  })

  it('marks active density as aria-checked', () => {
    render(<PersonalSettings {...baseProps} density="compact" />)
    const buttons = screen.getAllByRole('radio')
    const compactBtn = buttons.find((b) => b.textContent?.includes('Gọn'))
    expect(compactBtn).toHaveAttribute('aria-checked', 'true')
  })

  it('calls onDensityChange when density is clicked', async () => {
    const onDensityChange = vi.fn()
    const user = userEvent.setup()
    render(<PersonalSettings {...baseProps} onDensityChange={onDensityChange} />)
    const buttons = screen.getAllByRole('radio')
    const compactBtn = buttons.find((b) => b.textContent?.includes('Gọn'))
    await user.click(compactBtn!)
    expect(onDensityChange).toHaveBeenCalledWith('compact')
  })

  it('calls onReduceMotionChange when toggle is clicked', async () => {
    const onReduceMotionChange = vi.fn()
    const user = userEvent.setup()
    render(<PersonalSettings {...baseProps} onReduceMotionChange={onReduceMotionChange} />)
    await user.click(screen.getByRole('switch'))
    expect(onReduceMotionChange).toHaveBeenCalledWith(true)
  })

  it('marks reduce motion switch as active', () => {
    render(<PersonalSettings {...baseProps} reduceMotion={true} />)
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true')
  })

  it('calls onClose when X is clicked', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<PersonalSettings {...baseProps} onClose={onClose} />)
    await user.click(screen.getByLabelText('Đóng cài đặt'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose on Escape key', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<PersonalSettings {...baseProps} onClose={onClose} />)
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not close on inside click', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<PersonalSettings {...baseProps} onClose={onClose} />)
    await user.click(screen.getByText('Sáng'))
    expect(onClose).not.toHaveBeenCalled()
  })
})
