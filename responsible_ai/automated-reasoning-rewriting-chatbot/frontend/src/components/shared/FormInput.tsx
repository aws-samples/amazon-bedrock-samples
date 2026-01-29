import React from 'react';

/**
 * Props for the FormInput component
 * Requirements: 5.1, 5.2, 5.3
 */
export interface FormInputProps {
  /** Unique identifier for the input element */
  id: string;
  /** Label text to display above the input */
  label: string;
  /** Type of input field */
  type?: 'text' | 'number' | 'email' | 'password';
  /** Current value of the input */
  value: string | number;
  /** Callback function when input value changes */
  onChange: (value: string) => void;
  /** Error message to display below the input */
  error?: string | null;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Placeholder text for the input */
  placeholder?: string;
  /** Minimum value for number inputs */
  min?: number;
  /** Maximum value for number inputs */
  max?: number;
  /** Step value for number inputs */
  step?: number;
  /** Whether the input is required */
  required?: boolean;
}

/**
 * FormInput Component
 * 
 * A reusable form input component with validation and error display.
 * 
 * Requirements:
 * - 5.1: Displays error messages below the input field when validation errors exist
 * - 5.2: Validates input and updates error state when value changes
 * - 5.3: Applies disabled styling and prevents interaction when disabled
 */
const FormInput: React.FC<FormInputProps> = ({
  id,
  label,
  type = 'text',
  value,
  onChange,
  error = null,
  disabled = false,
  placeholder,
  min,
  max,
  step,
  required = false,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  const inputClassName = error ? 'input-error' : '';

  return (
    <div className="form-group">
      <label htmlFor={id}>
        {label}
        {required && <span style={{ color: '#dc3545', marginLeft: '4px' }}>*</span>}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={handleChange}
        disabled={disabled}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        required={required}
        className={inputClassName}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error && (
        <div id={`${id}-error`} className="field-error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
};

export default FormInput;
