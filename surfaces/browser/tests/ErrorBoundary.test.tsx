import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorBoundary } from '../src/components/ErrorBoundary'

describe('ErrorBoundary', () => {
  const GoodChild = () => <div>Nội dung bình thường</div>

  const BadChild = () => {
    throw new Error('Test crash')
  }

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Nội dung bình thường')).toBeInTheDocument()
  })

  it('renders fallback on error', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    )
    expect(screen.getByText(/không thể hiển thị/)).toBeInTheDocument()
    expect(screen.getByText('Thử lại')).toBeInTheDocument()
    expect(screen.getByText('Tải lại trang')).toBeInTheDocument()
    vi.mocked(console.error).mockRestore()
  })

  it('shows error message in fallback', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Test crash')).toBeInTheDocument()
    vi.mocked(console.error).mockRestore()
  })

  it('uses custom name in fallback title', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary name="Dashboard">
        <BadChild />
      </ErrorBoundary>,
    )
    expect(screen.getByText(/Dashboard/)).toBeInTheDocument()
    vi.mocked(console.error).mockRestore()
  })

  it('calls onReset when Thử lại is clicked', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const onReset = vi.fn()
    const user = userEvent.setup()

    render(
      <ErrorBoundary onReset={onReset}>
        <BadChild />
      </ErrorBoundary>,
    )

    await user.click(screen.getByText('Thử lại'))
    expect(onReset).toHaveBeenCalledTimes(1)
    vi.mocked(console.error).mockRestore()
  })

  it('resets error state after Thử lại', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const user = userEvent.setup()

    const { rerender } = render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    )

    expect(screen.getByText(/không thể hiển thị/)).toBeInTheDocument()

    rerender(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    )

    await user.click(screen.getByText('Thử lại'))

    expect(screen.getByText('Nội dung bình thường')).toBeInTheDocument()
    vi.mocked(console.error).mockRestore()
  })

  it('renders alert role in fallback', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    vi.mocked(console.error).mockRestore()
  })
})
