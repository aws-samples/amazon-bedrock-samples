import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FormInput from './FormInput';

describe('FormInput Component', () => {
  it('renders label and input', () => {
    const mockOnChange = jest.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Label"
        value=""
        onChange={mockOnChange}
      />
    );

    expect(screen.getByLabelText('Test Label')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('displays error message when error prop is provided', () => {
    const mockOnChange = jest.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Label"
        value=""
        onChange={mockOnChange}
        error="This field is required"
      />
    );

    expect(screen.getByRole('alert')).toHaveTextContent('This field is required');
  });

  it('applies error styling when error is present', () => {
    const mockOnChange = jest.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Label"
        value=""
        onChange={mockOnChange}
        error="Error message"
      />
    );

    const input = screen.getByRole('textbox');
    expect(input).toHaveClass('input-error');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('calls onChange when input value changes', () => {
    const mockOnChange = jest.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Label"
        value=""
        onChange={mockOnChange}
      />
    );

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'new value' } });

    expect(mockOnChange).toHaveBeenCalledWith('new value');
  });

  it('disables input when disabled prop is true', () => {
    const mockOnChange = jest.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Label"
        value=""
        onChange={mockOnChange}
        disabled={true}
      />
    );

    const input = screen.getByRole('textbox');
    expect(input).toBeDisabled();
  });

  it('supports different input types', () => {
    const mockOnChange = jest.fn();
    const { rerender } = render(
      <FormInput
        id="test-input"
        label="Test Label"
        type="email"
        value=""
        onChange={mockOnChange}
      />
    );

    let input = screen.getByLabelText('Test Label');
    expect(input).toHaveAttribute('type', 'email');

    rerender(
      <FormInput
        id="test-input"
        label="Test Label"
        type="password"
        value=""
        onChange={mockOnChange}
      />
    );

    input = screen.getByLabelText('Test Label');
    expect(input).toHaveAttribute('type', 'password');
  });

  it('displays required indicator when required is true', () => {
    const mockOnChange = jest.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Label"
        value=""
        onChange={mockOnChange}
        required={true}
      />
    );

    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('supports number input with min, max, and step', () => {
    const mockOnChange = jest.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Label"
        type="number"
        value={5}
        onChange={mockOnChange}
        min={0}
        max={10}
        step={1}
      />
    );

    const input = screen.getByLabelText('Test Label');
    expect(input).toHaveAttribute('type', 'number');
    expect(input).toHaveAttribute('min', '0');
    expect(input).toHaveAttribute('max', '10');
    expect(input).toHaveAttribute('step', '1');
  });
});
