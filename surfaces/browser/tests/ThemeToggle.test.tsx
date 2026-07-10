import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ThemeToggle } from '../src/components/ThemeToggle'

describe('ThemeToggle', () => {
  it('renders toggle switch', () => {
    const onToggle = vi.fn()
    render(<ThemeToggle theme="dark" onToggle={onToggle} />)
    const btn = screen.getByRole('switch')
    expect(btn).toBeInTheDocument()
  })

  it('calls onToggle when clicked', () => {
    const onToggle = vi.fn()
    render(<ThemeToggle theme="light" onToggle={onToggle} />)
    screen.getByRole('switch').click()
    expect(onToggle).toHaveBeenCalledOnce()
  })

  it('renders with dark theme', () => {
    render(<ThemeToggle theme="dark" onToggle={vi.fn()} />)
    const btn = screen.getByRole('switch')
    expect(btn).toHaveAttribute('aria-checked', 'true')
  })

  it('renders with light theme', () => {
    render(<ThemeToggle theme="light" onToggle={vi.fn()} />)
    const btn = screen.getByRole('switch')
    expect(btn).toHaveAttribute('aria-checked', 'false')
  })
})
