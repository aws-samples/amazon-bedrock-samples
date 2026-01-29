import React from 'react';

export interface FlowNoteProps {
  /** The message to display */
  message: string;
  /** Optional custom icon (defaults to ↓) */
  icon?: string;
  /** Optional additional CSS class */
  className?: string;
}

/**
 * FlowNote Component
 * 
 * Displays a visual flow indicator with an arrow and message,
 * typically used to show the relationship between steps in a process.
 */
const FlowNote: React.FC<FlowNoteProps> = ({
  message,
  icon = '↓',
  className = ''
}) => {
  return (
    <div className={`validation-note ${className}`.trim()}>
      <span className="arrow-down">{icon}</span>
      <span className="note-text">{message}</span>
    </div>
  );
};

export default FlowNote;
