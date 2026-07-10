import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from '../src/components/LoginPage'
import { AuthProvider, useAuth } from '../src/hooks/useAuth'

const mockLogin = vi.fn()
vi.mock('../src/hooks/useAuth', async () => {
  const actual = await vi.importActual('../src/hooks/useAuth')
  return {
    ...actual,
    useAuth: () => ({
      isAuthenticated: false,
      login: mockLogin,
      apiUrl: 'http://localhost:8000',
      setApiUrl: vi.fn(),
      apiFetch: vi.fn(),
      logout: vi.fn(),
      user: null,
      token: null,
      isAdmin: false,
    }),
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    mockLogin.mockReset()
  })

  it('renders login form', () => {
    render(<LoginPage />)
    expect(screen.getByText('LibCounterAI')).toBeInTheDocument()
    expect(screen.getByText('Đăng nhập')).toBeInTheDocument()
  })

  it('renders username and password fields', () => {
    render(<LoginPage />)
    expect(screen.getByPlaceholderText('admin')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
  })

  it('shows error on empty submit', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await user.click(screen.getByText('Đăng nhập'))
    expect(screen.getByText('Vui lòng nhập tên đăng nhập và mật khẩu.')).toBeInTheDocument()
  })
})
