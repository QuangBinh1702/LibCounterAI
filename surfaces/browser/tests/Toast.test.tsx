import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ToastContainer } from '../src/components/Toast'

describe('ToastContainer', () => {
  it('renders empty stack when toasts is empty', () => {
    const { container } = render(<ToastContainer toasts={[]} onDismiss={vi.fn()} />)
    expect(container.querySelector('.toast-stack')).toBeInTheDocument()
    expect(container.querySelectorAll('.toast').length).toBe(0)
  })

  it('renders toast with message', () => {
    const toasts = [{ id: '1', message: 'Hello', type: 'success' as const }]
    render(<ToastContainer toasts={toasts} onDismiss={vi.fn()} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders multiple toasts', () => {
    const toasts = [
      { id: '1', message: 'First', type: 'success' as const },
      { id: '2', message: 'Second', type: 'error' as const },
    ]
    render(<ToastContainer toasts={toasts} onDismiss={vi.fn()} />)
    expect(screen.getByText('First')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()
  })

  it('renders different types', () => {
    const toasts = [
      { id: '1', message: 'Success', type: 'success' as const },
      { id: '2', message: 'Error', type: 'error' as const },
      { id: '3', message: 'Info', type: 'info' as const },
    ]
    render(<ToastContainer toasts={toasts} onDismiss={vi.fn()} />)
    expect(screen.getByText('Success')).toBeInTheDocument()
    expect(screen.getByText('Error')).toBeInTheDocument()
    expect(screen.getByText('Info')).toBeInTheDocument()
  })

  it('renders dismiss buttons', () => {
    const toasts = [
      { id: '1', message: 'Test', type: 'info' as const },
    ]
    render(<ToastContainer toasts={toasts} onDismiss={vi.fn()} />)
    const dismiss = screen.getByLabelText('Đóng thông báo')
    expect(dismiss).toBeInTheDocument()
  })
})
