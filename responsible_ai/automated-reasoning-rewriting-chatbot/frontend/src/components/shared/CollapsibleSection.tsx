import React, { useState } from 'react';

export interface CollapsibleSectionProps {
  title: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  onToggle?: (expanded: boolean) => void;
  headerClassName?: string;
  contentClassName?: string;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  children,
  defaultExpanded = false,
  onToggle,
  headerClassName = '',
  contentClassName = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggle = () => {
    const newExpandedState = !isExpanded;
    setIsExpanded(newExpandedState);
    if (onToggle) {
      onToggle(newExpandedState);
    }
  };

  return (
    <div className="collapsible-section">
      <div
        className={`collapsible-header ${headerClassName}`}
        onClick={handleToggle}
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleToggle();
          }
        }}
      >
        <span className="toggle-icon">
          {isExpanded ? '▼' : '▶'}
        </span>
        {title}
      </div>
      {isExpanded && (
        <div className={`collapsible-content ${contentClassName}`}>
          {children}
        </div>
      )}
    </div>
  );
};

export default CollapsibleSection;
