import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/utils'
import userEvent from '@testing-library/user-event'
import { TextInput } from './TextInput'

describe('TextInput', () => {
  it('renders an input element by default', () => {
    render(<TextInput placeholder="Enter text" />)
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter text').tagName).toBe('INPUT')
  })

  it('renders a textarea when rows prop is provided', () => {
    render(<TextInput rows={4} placeholder="Enter description" />)
    const textarea = screen.getByPlaceholderText('Enter description')
    expect(textarea.tagName).toBe('TEXTAREA')
    expect(textarea).toHaveAttribute('rows', '4')
  })

  it('applies error styling when error prop is true', () => {
    render(<TextInput error placeholder="Error input" />)
    expect(screen.getByPlaceholderText('Error input')).toHaveClass('border-red-500')
  })

  it('does not apply error styling when error prop is false', () => {
    render(<TextInput placeholder="Normal input" />)
    expect(screen.getByPlaceholderText('Normal input')).toHaveClass('border-gray-300')
  })

  it('handles user input', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(<TextInput placeholder="Type here" onChange={handleChange} />)

    const input = screen.getByPlaceholderText('Type here')
    await user.type(input, 'Hello')

    expect(handleChange).toHaveBeenCalled()
    expect(input).toHaveValue('Hello')
  })

  it('accepts custom className', () => {
    render(<TextInput placeholder="Custom" className="custom-class" />)
    expect(screen.getByPlaceholderText('Custom')).toHaveClass('custom-class')
  })

  it('passes through additional props', () => {
    render(<TextInput placeholder="Required" required aria-label="Test input" />)
    const input = screen.getByPlaceholderText('Required')
    expect(input).toBeRequired()
    expect(input).toHaveAttribute('aria-label', 'Test input')
  })
})
