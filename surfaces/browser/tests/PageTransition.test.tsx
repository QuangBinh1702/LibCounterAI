import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageTransition } from '../src/components/PageTransition'

describe('PageTransition', () => {
  it('renders children', () => {
    render(
      <PageTransition className="test-view" testId="my-view">
        <div>Content</div>
      </PageTransition>,
    )
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('applies className and testId', () => {
    const { container } = render(
      <PageTransition className="my-page" testId="page-1">
        <span>Hi</span>
      </PageTransition>,
    )
    expect(screen.getByTestId('page-1')).toBeInTheDocument()
    expect(container.firstChild).toHaveProperty('className')
  })
})
