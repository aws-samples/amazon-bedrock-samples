import React from 'react';
import { getValidationOutputClass, getValidationDisplayText } from '../../utils/validationUtils';

/**
 * Props for the ValidationBadge component
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
 */
export interface ValidationBadgeProps {
  /** The validation output value to display */
  validationOutput: string;
  /** Whether to show a success checkmark icon for VALID status */
  showSuccessIcon?: boolean;
  /** Additional CSS class names to apply */
  className?: string;
}

/**
 * ValidationBadge Component
 * 
 * Renders a styled badge showing validation status with appropriate styling
 * based on the validation output type.
 * 
 * Requirements:
 * - 1.1: Renders badge with appropriate styling based on validation type
 * - 1.2: Displays success checkmark icon for VALID status when showSuccessIcon is true
 * - 1.3: Applies invalid styling for INVALID, IMPOSSIBLE, TRANSLATION_AMBIGUOUS, SATISFIABLE
 * - 1.4: Applies error styling for TOO_COMPLEX
 * - 1.5: Applies warning styling for NO_TRANSLATIONS
 */
const ValidationBadge: React.FC<ValidationBadgeProps> = ({
  validationOutput,
  showSuccessIcon = false,
  className = ''
}) => {
  const validationClass = getValidationOutputClass(validationOutput);
  const displayText = getValidationDisplayText(validationOutput);
  const isValid = validationOutput.toUpperCase() === 'VALID';

  return (
    <span className={`validation-badge ${validationClass} ${className}`.trim()}>
      {displayText}
      {isValid && showSuccessIcon && <span className="validation-success-icon"> ✓</span>}
    </span>
  );
};

export default ValidationBadge;
