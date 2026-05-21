import React from 'react';

export interface WarningMessageProps {
  /** The warning message to display */
  message: string;
  /** Optional custom icon (defaults to ⚠️) */
  icon?: string;
  /** Optional additional CSS class */
  className?: string;
}

/**
 * WarningMessage Component
 * 
 * Displays a warning message with an icon.
 * Used for displaying validation warnings, error states, or important notices.
 */
const WarningMessage: React.FC<WarningMessageProps> = ({
  message,
  icon = '⚠️',
  className = ''
}) => {
  return (
    <div className={`warning-message ${className}`.trim()}>
      <span className="warning-icon">{icon}</span>
      <span>{message}</span>
    </div>
  );
};

export default WarningMessage;
