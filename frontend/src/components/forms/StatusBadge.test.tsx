import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders the status text', () => {
    render(<StatusBadge status="draft" />)
    expect(screen.getByText('draft')).toBeInTheDocument()
  })

  it('replaces underscores with spaces', () => {
    render(<StatusBadge status="in_review" />)
    expect(screen.getByText('in review')).toBeInTheDocument()
  })

  it('applies correct color class for known statuses', () => {
    render(<StatusBadge status="released" />)
    const badge = screen.getByText('released')
    expect(badge).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('applies default color class for unknown statuses', () => {
    render(<StatusBadge status="unknown_status" />)
    const badge = screen.getByText('unknown status')
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800')
  })

  it('accepts custom color map', () => {
    const customColors = { custom: 'bg-pink-100 text-pink-800' }
    render(<StatusBadge status="custom" colorMap={customColors} />)
    const badge = screen.getByText('custom')
    expect(badge).toHaveClass('bg-pink-100', 'text-pink-800')
  })
})
