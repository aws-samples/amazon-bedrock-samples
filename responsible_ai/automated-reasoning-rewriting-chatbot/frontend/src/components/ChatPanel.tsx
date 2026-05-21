import React, { useState, useEffect, useRef } from 'react';
import { Thread } from '../api/APIClient';
import ThreadMessage from './ThreadMessage';

interface ChatPanelProps {
  threads: Thread[];
  selectedThreadId: string | null;
  onSendMessage: (message: string) => void;
  onSelectThread: (threadId: string) => void;
  onSubmitAnswers: (threadId: string, answers: string[], skipped: boolean) => void;
  error?: string | null;
  prefilledMessage?: string;
  onMessageChange?: (message: string) => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ 
  threads,
  selectedThreadId,
  onSendMessage, 
  onSelectThread, 
  onSubmitAnswers, 
  error,
  prefilledMessage,
  onMessageChange 
}) => {
  const [inputMessage, setInputMessage] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Handle prefilled message updates
  useEffect(() => {
    if (prefilledMessage !== undefined && prefilledMessage !== inputMessage) {
      setInputMessage(prefilledMessage);
      // Focus the textarea when a prefilled message is set
      if (prefilledMessage && textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [prefilledMessage]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setInputMessage(newValue);
    // Notify parent of message changes
    if (onMessageChange) {
      onMessageChange(newValue);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (inputMessage.trim()) {
      onSendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-panel">
      {error && (
        <div className="chat-error-message" role="alert">
          {error}
        </div>
      )}
      
      <div className="thread-list">
        {threads.length === 0 ? (
          <div className="empty-state">
            <p>No conversations yet. Start by sending a message below.</p>
          </div>
        ) : (
          threads.map((thread) => (
            <ThreadMessage
              key={thread.thread_id}
              thread={thread}
              isSelected={thread.thread_id === selectedThreadId}
              onSelectThread={onSelectThread}
              onSubmitAnswers={onSubmitAnswers}
            />
          ))
        )}
      </div>

      <form className="message-input-form" onSubmit={handleSubmit}>
        <div className="input-container">
          <textarea
            ref={textareaRef}
            className="message-input"
            value={inputMessage}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            rows={3}
            disabled={false}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!inputMessage.trim()}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatPanel;
