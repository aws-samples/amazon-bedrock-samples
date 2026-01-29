import React from 'react';

/**
 * EmptyState Component
 * Displays a message when no content is available.
 */
export interface EmptyStateProps {
  message: string;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ 
  message, 
  className = '' 
}) => {
  return (
    <div className={`empty-state ${className}`.trim()}>
      <p>{message}</p>
    </div>
  );
};

/**
 * LoadingState Component
 * Displays a loading spinner with an optional message.
 */
export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ 
  message = 'Loading...', 
  className = '' 
}) => {
  return (
    <div className={`loading-state ${className}`.trim()}>
      <div className="loading-spinner"></div>
      <p>{message}</p>
    </div>
  );
};

/**
 * ErrorState Component
 * Displays an error message with an optional retry button.
 */
export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  icon?: string;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ 
  message, 
  onRetry, 
  retryLabel = 'Retry',
  icon = '⚠️',
  className = '' 
}) => {
  return (
    <div className={`error-state ${className}`.trim()}>
      <span className="error-icon">{icon}</span>
      <p className="error-message">{message}</p>
      {onRetry && (
        <button className="retry-button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
};
