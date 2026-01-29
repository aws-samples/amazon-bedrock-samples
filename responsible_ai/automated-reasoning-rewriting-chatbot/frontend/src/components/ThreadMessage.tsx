import React, { useState, useEffect } from 'react';
import { Thread, isClarificationIteration, isARIteration, Finding } from '../api/APIClient';
import ValidationBadge from './shared/ValidationBadge';
import StatusIndicator from './shared/StatusIndicator';
import WarningMessage from './shared/WarningMessage';
import Message from './shared/Message';
import RuleEvaluationModal from './RuleEvaluationModal';

interface ThreadMessageProps {
  thread: Thread;
  isSelected: boolean;
  onSelectThread: (threadId: string) => void;
  onSubmitAnswers: (threadId: string, answers: string[], skipped: boolean) => void;
}

const ThreadMessage: React.FC<ThreadMessageProps> = ({ thread, isSelected, onSelectThread, onSubmitAnswers }) => {
  const [answers, setAnswers] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [verificationModalFinding, setVerificationModalFinding] = useState<Finding | null>(null);

  // Reset state when thread status changes to AWAITING_USER_INPUT
  // This handles the case where new questions appear after previous answers were submitted
  useEffect(() => {
    if (thread.status === 'AWAITING_USER_INPUT') {
      setIsSubmitting(false);
      setAnswers([]);
    }
  }, [thread.status, thread.iterations.length]); // Reset when status changes or new iteration added

  const handleClick = () => {
    onSelectThread(thread.thread_id);
  };

  const handleAnswerChange = (index: number, value: string) => {
    const newAnswers = [...answers];
    newAnswers[index] = value;
    setAnswers(newAnswers);
  };

  const handleSubmit = async () => {
    if (isSubmitting) return;
    
    const lastIteration = thread.iterations[thread.iterations.length - 1];
    if (!lastIteration || !isClarificationIteration(lastIteration)) return;
    
    const qaExchange = lastIteration.type_specific_data.qa_exchange;
    if (!qaExchange?.questions) return;
    
    // Validate all questions have answers
    const questionCount = qaExchange.questions.length;
    if (answers.filter(a => a && a.trim()).length !== questionCount) {
      alert('Please answer all questions before submitting.');
      return;
    }
    
    setIsSubmitting(true);
    try {
      await onSubmitAnswers(thread.thread_id, answers, false);
      // Reset state after successful submission
      setAnswers([]);
    } catch (error) {
      console.error('Failed to submit answers:', error);
      alert('Failed to submit answers. Please try again.');
      setIsSubmitting(false);
    }
  };

  const handleSkip = async () => {
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    try {
      await onSubmitAnswers(thread.thread_id, [], true);
      // Reset state after successful skip
      setAnswers([]);
    } catch (error) {
      console.error('Failed to skip questions:', error);
      alert('Failed to skip questions. Please try again.');
      setIsSubmitting(false);
    }
  };



  const hasNoTranslationsFindings = () => {
    if (thread.status !== 'COMPLETED' || !thread.iterations || thread.iterations.length === 0) {
      return false;
    }
    
    // Get the final validation result
    const validationData = getFinalValidationData();
    
    // If the final validation is VALID, don't show the warning
    if (validationData && validationData.validationOutput === 'VALID') {
      return false;
    }
    
    // Check if any AR iteration has NO_TRANSLATIONS findings
    return thread.iterations.some(iteration => {
      if (isARIteration(iteration)) {
        return iteration.type_specific_data.findings.some(finding => 
          finding.validation_output === 'NO_TRANSLATIONS'
        );
      }
      return false;
    });
  };

  const getWarningDisplay = () => {
    // Show backend warning message if present
    if (thread.warning_message) {
      return <WarningMessage message={thread.warning_message} />;
    }
    
    // Show NO_TRANSLATIONS warning if applicable
    if (thread.status === 'COMPLETED' && hasNoTranslationsFindings()) {
      return (
        <WarningMessage 
          message="Note: This response could not be fully validated by the automated reasoning system. Some aspects of your question may not be covered by the validation policy."
        />
      );
    }
    
    return null;
  };



  const getFinalValidationData = () => {
    if (thread.status !== 'COMPLETED' || !thread.iterations || thread.iterations.length === 0) {
      return null;
    }

    const lastIteration = thread.iterations[thread.iterations.length - 1];
    
    if (isARIteration(lastIteration)) {
      return {
        validationOutput: lastIteration.type_specific_data.validation_output,
        findings: lastIteration.type_specific_data.findings || []
      };
    } else if (isClarificationIteration(lastIteration)) {
      return {
        validationOutput: lastIteration.type_specific_data.validation_output,
        findings: lastIteration.type_specific_data.validation_findings || []
      };
    }
    
    return null;
  };

  const getValidFindingWithRules = () => {
    const validationData = getFinalValidationData();
    if (!validationData || !validationData.findings) return null;

    return validationData.findings.find(
      f => f.validation_output === 'VALID' && 
           f.details.supporting_rules && 
           f.details.supporting_rules.length > 0
    );
  };

  const renderFinalValidationBadge = () => {
    const validationData = getFinalValidationData();
    if (!validationData || !validationData.validationOutput) return null;

    const validFinding = getValidFindingWithRules();
    const showVerificationButton = validationData.validationOutput === 'VALID' && validFinding;

    return (
      <div className="validation-badge-container">
        <ValidationBadge 
          validationOutput={validationData.validationOutput}
          showSuccessIcon={true}
        />
        {showVerificationButton && (
          <button
            className="verification-button-inline"
            onClick={(e) => {
              e.stopPropagation(); // Prevent thread selection
              setVerificationModalFinding(validFinding);
            }}
          >
            🔍 View Verification
          </button>
        )}
      </div>
    );
  };

  const renderQuestions = () => {
    if (thread.status !== 'AWAITING_USER_INPUT') return null;
    
    const lastIteration = thread.iterations[thread.iterations.length - 1];
    if (!lastIteration || !isClarificationIteration(lastIteration)) return null;
    
    const qaExchange = lastIteration.type_specific_data.qa_exchange;
    if (!qaExchange?.questions) return null;
    
    const questions = qaExchange.questions;
    
    // Initialize answers array if needed
    if (answers.length === 0 && questions.length > 0 && !isSubmitting) {
      setAnswers(new Array(questions.length).fill(''));
    }
    
    return (
      <div className="follow-up-questions">
        <div className="questions-header">
          <h4>The LLM needs clarification:</h4>
          <p className="questions-instruction">Please answer the following questions to help improve the response:</p>
        </div>
        
        <div className="questions-list">
          {questions.map((question, index) => (
            <div key={index} className="question-item">
              <label htmlFor={`question-${index}`}>
                <strong>Question {index + 1}:</strong> {question}
              </label>
              <input
                id={`question-${index}`}
                type="text"
                value={answers[index] || ''}
                onChange={(e) => handleAnswerChange(index, e.target.value)}
                disabled={isSubmitting}
                placeholder="Type your answer here..."
                className="question-input"
              />
            </div>
          ))}
        </div>
        
        <div className="question-actions">
          <button 
            onClick={handleSubmit} 
            disabled={isSubmitting}
            className="submit-answers-button"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Answers'}
          </button>
          <button 
            onClick={handleSkip} 
            disabled={isSubmitting}
            className="skip-questions-button"
          >
            {isSubmitting ? 'Skipping...' : 'Skip'}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div 
      className={`thread-message ${isSelected ? 'selected' : ''}`} 
      onClick={thread.status === 'AWAITING_USER_INPUT' ? undefined : handleClick}
    >
      <div className="thread-content">
        {/* User prompt */}
        <Message 
          type="user" 
          label="You"
          headerContent={<span className="model-id">Model: {thread.model_id}</span>}
        >
          {thread.user_prompt}
        </Message>

        {/* Status indicator for processing threads */}
        <StatusIndicator status={thread.status} />

        {/* Follow-up questions for AWAITING_USER_INPUT status */}
        {renderQuestions()}

        {/* Final response for completed threads */}
        {thread.status === 'COMPLETED' && thread.final_response && (
          <Message 
            type="assistant" 
            label="Assistant"
            headerContent={renderFinalValidationBadge()}
          >
            {thread.final_response}
          </Message>
        )}

        {/* Error message for failed threads */}
        {thread.status === 'ERROR' && (
          <Message type="error" label="Error">
            {thread.final_response || 'An error occurred while processing your request.'}
          </Message>
        )}

        {/* Warning messages */}
        {getWarningDisplay()}
      </div>

      <div className="thread-metadata">
        <span className="thread-id" title={thread.thread_id}>
          Thread ID: {thread.thread_id.substring(0, 8)}...
        </span>
        <span className="thread-timestamp">
          {new Date(thread.created_at).toLocaleString()}
        </span>
      </div>

      {/* Verification Modal */}
      {verificationModalFinding && (
        <RuleEvaluationModal
          finding={verificationModalFinding}
          isOpen={verificationModalFinding !== null}
          onClose={() => setVerificationModalFinding(null)}
        />
      )}
    </div>
  );
};

export default ThreadMessage;
