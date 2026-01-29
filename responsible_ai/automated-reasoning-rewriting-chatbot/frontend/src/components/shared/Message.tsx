import React from 'react';

export type MessageType = 'user' | 'assistant' | 'error';

export interface MessageProps {
  /** Type of message which determines styling */
  type: MessageType;
  /** Label to display in the header (e.g., "You", "Assistant", "Error") */
  label: string;
  /** Message content */
  children: React.ReactNode;
  /** Optional metadata to display in the header (e.g., model ID, validation badge) */
  headerContent?: React.ReactNode;
  /** Optional additional CSS class */
  className?: string;
}

/**
 * Message Component
 * 
 * Displays a styled message with a header containing a label and optional metadata.
 * Used for chat messages, responses, and error displays.
 */
const Message: React.FC<MessageProps> = ({
  type,
  label,
  children,
  headerContent,
  className = ''
}) => {
  const typeClass = `${type}-message`;

  return (
    <div className={`message ${typeClass} ${className}`.trim()}>
      <div className="message-header">
        <span className="message-label">{label}</span>
        {headerContent}
      </div>
      <div className="message-text">{children}</div>
    </div>
  );
};

export default Message;
