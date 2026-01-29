import React from 'react';
import ValidationBadge from './ValidationBadge';

export interface SectionHeaderProps {
  /** The title text to display */
  title: string;
  /** Optional validation output to display as a badge */
  validationOutput?: string;
  /** Label for the validation result (e.g., "Validation Result:") */
  validationLabel?: string;
  /** Whether to show success icon on valid badge */
  showSuccessIcon?: boolean;
  /** Heading level to use */
  level?: 'h4' | 'h5' | 'h6';
  /** Optional additional CSS class */
  className?: string;
}

/**
 * SectionHeader Component
 * 
 * Renders a section header with an optional validation badge.
 * Used for iteration sections that display validation results.
 */
const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  validationOutput,
  validationLabel = 'Validation Result:',
  showSuccessIcon = false,
  level = 'h5',
  className = ''
}) => {
  const HeadingTag = level;

  return (
    <div className={`section-header-with-validation ${className}`.trim()}>
      <HeadingTag>{title}</HeadingTag>
      {validationOutput && (
        <div className="validation-result">
          <span className="validation-label">{validationLabel}</span>
          <ValidationBadge 
            validationOutput={validationOutput} 
            showSuccessIcon={showSuccessIcon} 
          />
        </div>
      )}
    </div>
  );
};

export default SectionHeader;
