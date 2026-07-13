import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AdminPage } from '../src/components/AdminPage'

const apiFetch = vi.fn()
const showToast = vi.fn()

vi.mock('../src/hooks/useAuth', () => ({
  useAuth: () => ({ apiFetch }),
}))

vi.mock('../src/hooks/useToast', () => ({
  useToast: () => ({ show: showToast }),
}))

describe('AdminPage', () => {
  beforeEach(() => {
    apiFetch.mockReset()
    showToast.mockReset()
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    })
  })

  it('calls onBack when Quay lại is clicked', async () => {
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<AdminPage onBack={onBack} />)
    await user.click(screen.getByTestId('admin-back'))
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('asks for cleanup confirmation before running', async () => {
    apiFetch.mockImplementation(async (url: string) => {
      if (String(url).includes('/api/admin/retention/config')) {
        return {
          ok: true,
          json: async () => ({
            retention: {
              unknown_expire_hours: 24,
              session_timeout_hours: 48,
            },
            retention_cleanup_interval_seconds: 3600,
            audit_log_enabled: true,
          }),
        }
      }
      return { ok: true, json: async () => ({ items: [] }) }
    })

    const user = userEvent.setup()
    render(<AdminPage />)
    await user.click(screen.getByRole('tab', { name: /Lưu trữ/i }))
    await screen.findByText('Hết hạn danh tính lạ')
    await user.click(screen.getByTestId('admin-cleanup'))
    expect(screen.getByText('Chạy dọn dẹp ngay?')).toBeInTheDocument()
    expect(apiFetch).not.toHaveBeenCalledWith('/api/admin/retention/cleanup', expect.anything())
  })
})
