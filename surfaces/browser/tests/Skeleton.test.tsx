import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { SkeletonRows } from '../src/components/Skeleton'

describe('SkeletonRows', () => {
  it('renders specified number of rows', () => {
    const { container } = render(<SkeletonRows rows={5} />)
    const items = container.querySelectorAll('.skeleton-row')
    expect(items.length).toBe(5)
  })

  it('renders minimum 1 row', () => {
    const { container } = render(<SkeletonRows rows={0} />)
    const items = container.querySelectorAll('.skeleton-row')
    expect(items.length).toBe(1)
  })

  it('handles large row count', () => {
    const { container } = render(<SkeletonRows rows={100} />)
    const items = container.querySelectorAll('.skeleton-row')
    expect(items.length).toBe(100)
  })
})
