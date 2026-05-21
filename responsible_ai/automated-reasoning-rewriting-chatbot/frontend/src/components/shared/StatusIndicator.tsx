import React from 'react';

interface StatusIndicatorProps {
  status: 'PROCESSING' | 'ERROR' | 'COMPLETED' | 'AWAITING_USER_INPUT';
  customMessage?: string;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status, customMessage }) => {
  switch (status) {
    case 'PROCESSING':
      return (
        <div className="status-indicator processing">
          <span className="loading-spinner"></span>
          <span>{customMessage || 'Processing...'}</span>
        </div>
      );
    case 'ERROR':
      return (
        <div className="status-indicator error">
          <span>{customMessage || 'An error occurred'}</span>
        </div>
      );
    case 'COMPLETED':
    case 'AWAITING_USER_INPUT':
      return null;
    default:
      return null;
  }
};

export default StatusIndicator;
