import React, { useState } from 'react';
import { TestPrompt } from '../api/APIClient';
import SidePanel from './shared/SidePanel';
import { EmptyState, LoadingState, ErrorState } from './shared/StateDisplay';
import './TestPromptBrowser.css';

interface TestPromptBrowserProps {
  testPrompts: TestPrompt[];
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;
  onToggle: () => void;
  onPromptSelect: (prompt: string) => void;
  onRetry?: () => void;
}

const TestPromptBrowser: React.FC<TestPromptBrowserProps> = ({
  testPrompts,
  isOpen,
  isLoading,
  error,
  onToggle,
  onPromptSelect,
  onRetry,
}) => {
  const [expandedPromptId, setExpandedPromptId] = useState<string | null>(null);
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [showNewTestsAnimation, setShowNewTestsAnimation] = useState(false);
  const prevTestPromptsCount = React.useRef(0);

  // Trigger animation when new tests are loaded
  React.useEffect(() => {
    if (testPrompts.length > 0 && testPrompts.length !== prevTestPromptsCount.current) {
      setShowNewTestsAnimation(true);
      const timer = setTimeout(() => setShowNewTestsAnimation(false), 3000);
      prevTestPromptsCount.current = testPrompts.length;
      return () => clearTimeout(timer);
    }
  }, [testPrompts.length]);

  const handlePromptClick = (testCaseId: string, guardContent: string) => {
    setSelectedPromptId(testCaseId);
    onPromptSelect(guardContent);
  };

  const handleKeyDown = (e: React.KeyboardEvent, testCaseId: string, guardContent: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handlePromptClick(testCaseId, guardContent);
    }
  };

  const handleToggleExpand = (testCaseId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedPromptId(expandedPromptId === testCaseId ? null : testCaseId);
  };

  const truncateText = (text: string, maxLength: number = 100): { truncated: string; isTruncated: boolean } => {
    if (text.length <= maxLength) {
      return { truncated: text, isTruncated: false };
    }
    return { truncated: text.substring(0, maxLength) + '...', isTruncated: true };
  };

  // Map error messages to user-friendly messages and determine if retryable
  const getErrorInfo = (errorMessage: string | null): { message: string; isRetryable: boolean } => {
    if (!errorMessage) {
      return { message: 'An unknown error occurred', isRetryable: true };
    }

    const lowerError = errorMessage.toLowerCase();

    if (lowerError.includes('network') || lowerError.includes('connection') || lowerError.includes('timeout')) {
      return { message: 'Unable to connect to server. Please check your network connection and try again.', isRetryable: true };
    }
    if (lowerError.includes('unavailable') || lowerError.includes('503')) {
      return { message: 'The service is temporarily unavailable. Please try again in a few moments.', isRetryable: true };
    }
    if (lowerError.includes('credentials') || lowerError.includes('authentication') || lowerError.includes('unauthorized')) {
      return { message: 'Authentication error. Please check your AWS credentials configuration.', isRetryable: false };
    }
    if (lowerError.includes('invalid') && lowerError.includes('arn')) {
      return { message: 'Invalid policy selected. Please select a different policy.', isRetryable: false };
    }
    if (lowerError.includes('rate') || lowerError.includes('throttl') || lowerError.includes('too many')) {
      return { message: 'Too many requests. Please wait a moment and try again.', isRetryable: true };
    }
    if (lowerError.includes('500') || lowerError.includes('server error')) {
      return { message: 'A server error occurred. Please try again.', isRetryable: true };
    }

    return { message: errorMessage, isRetryable: true };
  };

  const renderPromptItem = (testPrompt: TestPrompt) => {
    const { truncated, isTruncated } = truncateText(testPrompt.guard_content);
    const isExpanded = expandedPromptId === testPrompt.test_case_id;
    const isSelected = selectedPromptId === testPrompt.test_case_id;
    const displayText = isExpanded ? testPrompt.guard_content : truncated;

    return (
      <div
        key={testPrompt.test_case_id}
        className={`prompt-item ${isSelected ? 'selected' : ''}`}
        onClick={() => handlePromptClick(testPrompt.test_case_id, testPrompt.guard_content)}
        onKeyDown={(e) => handleKeyDown(e, testPrompt.test_case_id, testPrompt.guard_content)}
        tabIndex={0}
        role="button"
        aria-pressed={isSelected}
        title={isTruncated && !isExpanded ? testPrompt.guard_content : undefined}
      >
        <div className="prompt-content">
          <div className="prompt-text">{displayText}</div>
          {isTruncated && (
            <button
              className="expand-button"
              onClick={(e) => handleToggleExpand(testPrompt.test_case_id, e)}
              aria-label={isExpanded ? 'Collapse text' : 'Expand text'}
            >
              {isExpanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
        <div className="prompt-id">ID: {testPrompt.test_case_id}</div>
      </div>
    );
  };

  const renderContent = () => {
    if (isLoading) {
      return <LoadingState message="Loading test prompts..." className="test-prompt-loading-state" />;
    }
    if (error) {
      const errorInfo = getErrorInfo(error);
      return (
        <ErrorState
          message={errorInfo.message}
          onRetry={errorInfo.isRetryable ? onRetry : undefined}
          className="test-prompt-error-state"
        />
      );
    }
    if (testPrompts.length === 0) {
      return (
        <EmptyState
          message="No test prompts available. Please select a policy to view test cases."
          className="test-prompt-empty-state"
        />
      );
    }
    return (
      <>
        <div className="prompt-count">
          {testPrompts.length} {testPrompts.length === 1 ? 'prompt' : 'prompts'} available
        </div>
        <div className="prompt-list">
          {testPrompts.map((testPrompt) => renderPromptItem(testPrompt))}
        </div>
      </>
    );
  };

  const countBadge = testPrompts.length > 0 ? (
    <span className="test-count-badge">{testPrompts.length}</span>
  ) : undefined;

  return (
    <SidePanel
      title="Test Prompts"
      icon="📋"
      isOpen={isOpen}
      onToggle={onToggle}
      className="test-prompt-browser"
      classPrefix="test-prompt"
      extraClassName={showNewTestsAnimation ? 'new-tests-loaded' : ''}
      badge={countBadge}
    >
      {renderContent()}
    </SidePanel>
  );
};

export default TestPromptBrowser;
