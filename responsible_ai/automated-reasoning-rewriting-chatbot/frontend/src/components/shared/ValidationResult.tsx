import React from 'react';
import ValidationBadge from './ValidationBadge';

/**
 * Props for the ValidationResult component
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 */
export interface ValidationResultProps {
  /** The validation output value to display */
  validationOutput: string;
  /** Optional label to display before the badge */
  label?: string;
  /** Whether to use inline layout (default: false for header layout) */
  inline?: boolean;
  /** Whether to show success icon for VALID results */
  showSuccessIcon?: boolean;
}

/**
 * ValidationResult Component
 * 
 * Renders validation results with a label and badge, supporting both
 * inline and header layout styles.
 * 
 * Requirements:
 * - 8.1: Displays label and validation badge
 * - 8.2: Shows success icon for VALID validation output
 * - 8.3: Displays label before badge
 * - 8.4: Applies inline styling when inline=true
 * - 8.5: Applies header styling when inline=false
 */
const ValidationResult: React.FC<ValidationResultProps> = ({
  validationOutput,
  label,
  inline = false,
  showSuccessIcon = false
}) => {
  const isValid = validationOutput.toUpperCase() === 'VALID';
  const containerClass = inline ? 'validation-result validation-result-inline' : 'validation-result validation-result-header';

  return (
    <div className={containerClass}>
      {label && <span className="validation-label">{label}</span>}
      <ValidationBadge 
        validationOutput={validationOutput}
        showSuccessIcon={isValid && showSuccessIcon}
      />
      {isValid && showSuccessIcon && <span className="validation-success-icon">✓</span>}
    </div>
  );
};

export default ValidationResult;
