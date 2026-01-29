import React from 'react';

export interface SidePanelProps {
  /** Panel title */
  title: string;
  /** Icon to display before the title */
  icon: string;
  /** Whether the panel is open */
  isOpen: boolean;
  /** Callback when toggle button is clicked */
  onToggle: () => void;
  /** Panel content */
  children: React.ReactNode;
  /** Optional badge to show in header (e.g., count) */
  badge?: React.ReactNode;
  /** Base CSS class for the panel (used to generate child class names) */
  className?: string;
  /** Additional CSS classes to add to the container */
  extraClassName?: string;
  /** Custom class name prefix for child elements (defaults to className) */
  classPrefix?: string;
}

/**
 * SidePanel Component
 * 
 * A reusable collapsible side panel with a header containing
 * an icon, title, optional badge, and toggle button.
 * 
 * Generates class names based on the classPrefix prop (or className if not provided):
 * - {className} - main container
 * - {prefix}-header - header section
 * - {prefix}-title - title container
 * - {prefix}-icon - icon span (uses 'icon' suffix, not full className)
 * - {prefix}-content - content section
 */
const SidePanel: React.FC<SidePanelProps> = ({
  title,
  icon,
  isOpen,
  onToggle,
  children,
  badge,
  className = 'side-panel',
  extraClassName = '',
  classPrefix
}) => {
  const stateClass = isOpen ? 'open' : 'closed';
  const fullClassName = `${className} ${stateClass}${extraClassName ? ` ${extraClassName}` : ''}`;
  
  // Use classPrefix if provided, otherwise derive from className
  // For "test-prompt-browser", we want "test-prompt" as prefix
  const prefix = classPrefix || className.replace(/-browser$/, '').replace(/-panel$/, '');

  return (
    <div className={fullClassName}>
      <div className={`${prefix}-header`}>
        <div className={`${prefix}-title`}>
          <span className={`${prefix}-icon`}>{icon}</span>
          <h3>{title}</h3>
          {!isOpen && badge}
        </div>
        <button
          className="toggle-button"
          onClick={onToggle}
          aria-label={isOpen ? `Close ${title.toLowerCase()}` : `Open ${title.toLowerCase()}`}
        >
          {isOpen ? '✕' : '☰'}
        </button>
      </div>

      {isOpen && (
        <div className={`${prefix}-content`}>
          {children}
        </div>
      )}
    </div>
  );
};

export default SidePanel;
