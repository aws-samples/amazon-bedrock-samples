import React, { useState, useEffect, useRef } from 'react';
import { Thread } from '../api/APIClient';
import ThreadMessage from './ThreadMessage';

interface ChatPanelProps {
  threads: Thread[];
  selectedThreadId: string | null;
  onSendMessage: (message: string, answer?: string, ragContent?: string) => void;
  onSelectThread: (threadId: string) => void;
  onSubmitAnswers: (threadId: string, answers: string[], skipped: boolean) => void;
  error?: string | null;
  prefilledMessage?: string;
  prefilledAnswer?: string;
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
  prefilledAnswer,
  onMessageChange 
}) => {
  const [inputMessage, setInputMessage] = useState<string>('');
  const [answerText, setAnswerText] = useState<string>('');
  const [showAnswerField, setShowAnswerField] = useState<boolean>(false);
  const [ragContent, setRagContent] = useState<string>('');
  const [ragFileName, setRagFileName] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const ragFileInputRef = useRef<HTMLInputElement>(null);

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

  // Handle prefilled answer updates (e.g. from test prompt selection)
  useEffect(() => {
    if (prefilledAnswer !== undefined && prefilledAnswer !== answerText) {
      setAnswerText(prefilledAnswer);
      // Auto-show the answer field when a prefilled answer is provided
      if (prefilledAnswer) {
        setShowAnswerField(true);
      }
    }
  }, [prefilledAnswer]);

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
      const answer = showAnswerField && answerText.trim() ? answerText.trim() : undefined;
      const rag = ragContent.trim() ? ragContent.trim() : undefined;
      onSendMessage(inputMessage.trim(), answer, rag);
      setInputMessage('');
      setAnswerText('');
      setShowAnswerField(false);
      setRagContent('');
      setRagFileName('');
    }
  };

  const handleRagFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setRagContent(content);
      setRagFileName(file.name);
    };
    reader.readAsText(file);

    // Reset the input so the same file can be re-selected
    e.target.value = '';
  };

  const handleClearRag = () => {
    setRagContent('');
    setRagFileName('');
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
        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="message-input"
            value={inputMessage}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Type your question here..."
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
        <div className="answer-section">
          <button
            type="button"
            className={`answer-toggle-button ${showAnswerField ? 'active' : ''}`}
            onClick={() => setShowAnswerField(!showAnswerField)}
            title={showAnswerField ? 'Hide answer field' : 'Provide your own answer (skip LLM generation)'}
          >
            {showAnswerField ? '▾ Hide answer' : '▸ Provide answer'}
          </button>
          {showAnswerField && (
            <textarea
              className="message-input answer-input"
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              placeholder="Provide your own answer (skips LLM generation, enters rewriting loop directly)..."
              rows={3}
            />
          )}
        </div>
        <div className="rag-section">
          <input
            ref={ragFileInputRef}
            type="file"
            accept=".md,.txt,.markdown"
            onChange={handleRagFileUpload}
            style={{ display: 'none' }}
          />
          <button
            type="button"
            className={`answer-toggle-button ${ragContent ? 'active' : ''}`}
            onClick={() => ragFileInputRef.current?.click()}
            title="Upload a markdown file to use as RAG context instead of the policy"
          >
            📄 {ragContent ? 'Replace RAG file' : 'Upload RAG file'}
          </button>
          {ragFileName && (
            <span className="rag-file-indicator">
              <span className="rag-file-name">{ragFileName}</span>
              <button
                type="button"
                className="rag-clear-button"
                onClick={handleClearRag}
                title="Remove RAG file"
              >
                ✕
              </button>
            </span>
          )}
        </div>
      </form>
    </div>
  );
};

export default ChatPanel;
