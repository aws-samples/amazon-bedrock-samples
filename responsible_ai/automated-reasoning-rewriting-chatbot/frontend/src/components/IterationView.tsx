import React, { useState } from 'react';
import { TypedIteration, IterationType, ARIterationData, ClarificationIterationData } from '../api/APIClient';
import ValidationBadge from './shared/ValidationBadge';
import FindingsList from './shared/FindingsList';
import FlowNote from './shared/FlowNote';
import SectionHeader from './shared/SectionHeader';
import CollapsibleSection from './shared/CollapsibleSection';

interface IterationViewProps {
  iteration: TypedIteration;
  previousIteration?: TypedIteration;
}

const IterationView: React.FC<IterationViewProps> = ({ iteration, previousIteration }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  // Helper to get iteration type badge label
  const getIterationTypeBadge = () => {
    // Check if this is the initial answer (iteration 0)
    if (iteration.iteration_number === 0 && iteration.iteration_type === IterationType.AR_FEEDBACK) {
      const arData = iteration.type_specific_data as ARIterationData;
      if (arData.llm_decision === 'INITIAL') {
        return 'Initial Answer';
      }
    }
    
    switch (iteration.iteration_type) {
      case IterationType.AR_FEEDBACK:
        return 'AR Feedback';
      case IterationType.USER_CLARIFICATION:
        return 'User Clarification';
      default:
        return 'Unknown';
    }
  };

  // Helper to get validation outputs - shows previous iteration's validation -> current iteration's validation
  const getValidationSummary = () => {
    let previousValidation: string | null = null;
    let currentValidation: string | null = null;

    // Get previous iteration's validation output
    if (previousIteration) {
      if (previousIteration.iteration_type === IterationType.AR_FEEDBACK) {
        const prevArData = previousIteration.type_specific_data as ARIterationData;
        previousValidation = prevArData.validation_output;
      } else if (previousIteration.iteration_type === IterationType.USER_CLARIFICATION) {
        const prevClarData = previousIteration.type_specific_data as ClarificationIterationData;
        previousValidation = prevClarData.validation_output || null;
      }
    }

    // Get current iteration's validation output
    if (iteration.iteration_type === IterationType.AR_FEEDBACK) {
      const arData = iteration.type_specific_data as ARIterationData;
      currentValidation = arData.validation_output;
    } else if (iteration.iteration_type === IterationType.USER_CLARIFICATION) {
      const clarData = iteration.type_specific_data as ClarificationIterationData;
      currentValidation = clarData.validation_output || null;
    }

    return { previousValidation, currentValidation };
  };

  const { previousValidation, currentValidation } = getValidationSummary();

  // Helper to render validation arrow indicator
  const renderValidationArrow = () => {
    if (!previousValidation || !currentValidation) return null;
    
    return (
      <span className="validation-summary">
        <ValidationBadge validationOutput={previousValidation} />
        <span className="validation-arrow">→</span>
        <ValidationBadge validationOutput={currentValidation} showSuccessIcon={true} />
      </span>
    );
  };

  return (
    <div className={`iteration-view ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="iteration-header" onClick={toggleExpanded} style={{ cursor: 'pointer' }}>
        <div className="iteration-header-left">
          <span className="collapse-icon">{isExpanded ? '▼' : '▶'}</span>
          <h4>
            {iteration.iteration_number === 0 ? 'Initial Answer' : `Iteration ${iteration.iteration_number}`}
          </h4>
          <span className="iteration-type-badge">
            {getIterationTypeBadge()}
          </span>
        </div>
        {renderValidationArrow()}
      </div>

      {isExpanded && (
        <div className="iteration-body">
          {/* INITIAL ANSWER (Iteration 0) */}
          {iteration.iteration_number === 0 && iteration.iteration_type === IterationType.AR_FEEDBACK && (
            <>
              {/* 1. Initial Prompt */}
              <div className="iteration-section">
                <CollapsibleSection
                  title={<h5>1. Initial Prompt</h5>}
                  defaultExpanded={false}
                >
                  <div className="iteration-content rewriting-prompt">
                    {iteration.rewriting_prompt}
                  </div>
                </CollapsibleSection>
                <FlowNote message="This prompt produced the initial answer" />
              </div>

              {/* 2. Generated Answer */}
              {(() => {
                const arData = iteration.type_specific_data as ARIterationData;
                const validationOutput = arData.validation_output;
                return (
                  <div className={`iteration-section answer-section ${validationOutput === 'VALID' ? 'validation-passed' : ''}`}>
                    <SectionHeader
                      title="2. Generated Answer"
                      validationOutput={validationOutput}
                      showSuccessIcon={true}
                    />
                    <div className="iteration-content">
                      {iteration.rewritten_answer}
                    </div>
                  </div>
                );
              })()}

              {/* 3. Validation Findings */}
              {(() => {
                const arData = iteration.type_specific_data as ARIterationData;
                const validationOutput = arData.validation_output;
                return arData.findings && arData.findings.length > 0 && (
                  <div className="iteration-section">
                    <h5>3. Validation Findings</h5>
                    <FindingsList findings={arData.findings} title="View Details" />
                    {validationOutput !== 'VALID' && (
                      <FlowNote message="Validation result triggered rewriting" />
                    )}
                  </div>
                );
              })()}
            </>
          )}

          {/* AR FEEDBACK ITERATION (Iteration 1+) */}
          {iteration.iteration_number !== 0 && iteration.iteration_type === IterationType.AR_FEEDBACK && (
            <>
              {/* 1. Validation Findings from Previous Answer */}
              {(() => {
                const arData = iteration.type_specific_data as ARIterationData;
                return arData.findings && arData.findings.length > 0 && (
                  <div className="iteration-section">
                    <h5>1. Validation Findings from Previous Answer</h5>
                    <FindingsList findings={arData.findings} title="View Details" />
                    <FlowNote message="These findings generated the rewriting prompt" />
                  </div>
                );
              })()}

              {/* 2. Rewriting Prompt */}
              <div className="iteration-section">
                <CollapsibleSection
                  title={<h5>2. Rewriting Prompt</h5>}
                  defaultExpanded={false}
                >
                  <div className="iteration-content rewriting-prompt">
                    {iteration.rewriting_prompt}
                  </div>
                </CollapsibleSection>
                <FlowNote message="This prompt produced the rewritten answer" />
              </div>

              {/* 3. Rewritten Answer */}
              {(() => {
                const arData = iteration.type_specific_data as ARIterationData;
                const validationOutput = arData.validation_output;
                return (
                  <div className={`iteration-section answer-section ${validationOutput === 'VALID' ? 'validation-passed' : ''}`}>
                    <SectionHeader
                      title="3. Rewritten Answer"
                      validationOutput={validationOutput}
                      showSuccessIcon={true}
                    />
                    <div className="iteration-content">
                      {iteration.rewritten_answer}
                    </div>
                  </div>
                );
              })()}

              {/* 4. Validation Findings for Rewritten Answer */}
              {(() => {
                const arData = iteration.type_specific_data as ARIterationData;
                // For AR iterations, we need to get the findings from the NEXT iteration
                // or show that this is the final answer if there are no more iterations
                // Since we don't have access to the next iteration here, we'll show a note
                // that this answer was validated as VALID (if it is) or show any available findings
                
                // Note: The findings in arData are from the PREVIOUS answer (what triggered this rewrite)
                // The validation_output is for THIS answer
                const validationOutput = arData.validation_output;
                
                return validationOutput === 'VALID' && (
                  <div className="iteration-section">
                    <h5>4. Validation Findings for This Answer</h5>
                    <div className="iteration-content">
                      <div className="validation-success-note">
                        ✓ This answer passed validation with result: <strong>VALID</strong>
                        {arData.findings.length > 0 && (
                          <div style={{ marginTop: '10px' }}>
                            <em>Note: The findings shown in section 1 are from the previous answer that triggered this rewrite.</em>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </>
          )}

          {/* USER CLARIFICATION ITERATION */}
          {iteration.iteration_type === IterationType.USER_CLARIFICATION && (
            <>
              {/* 1. Validation Findings from Previous Answer */}
              {/* Note: For clarification iterations, we show the findings that triggered the questions */}
              <div className="iteration-section">
                <h5>1. Validation Findings from Previous Answer</h5>
                <div className="iteration-content">
                  <em>The previous answer had validation issues that prompted the LLM to ask for clarification.</em>
                </div>
                <FlowNote message="LLM decided to ask follow-up questions" />
              </div>

              {/* 2. LLM Decision to Ask Follow-up Questions */}
              {(() => {
                const clarData = iteration.type_specific_data as ClarificationIterationData;
                return (
                  <div className="iteration-section">
                    <h5>2. LLM Decision: Ask Follow-up Questions</h5>
                    <div className="qa-exchange">
                      {clarData.qa_exchange.questions.map((question, index) => (
                        <div key={index} className="qa-pair">
                          <div className="question">
                            <strong>Q{index + 1}:</strong> {question}
                          </div>
                        </div>
                      ))}
                    </div>
                    <FlowNote message="User provided answers" />
                  </div>
                );
              })()}

              {/* 3. Rewriting Prompt with User Answers */}
              {(() => {
                const clarData = iteration.type_specific_data as ClarificationIterationData;
                return (
                  <div className="iteration-section">
                    <CollapsibleSection
                      title={<h5>3. Rewriting Prompt with User Answers</h5>}
                      defaultExpanded={false}
                    >
                      {clarData.qa_exchange.answers && !clarData.qa_exchange.skipped && (
                        <div className="qa-answers-summary">
                          <strong>User Answers:</strong>
                          {clarData.qa_exchange.questions.map((question, index) => (
                            <div key={index} className="qa-pair">
                              <div className="question">
                                <strong>Q:</strong> {question}
                              </div>
                              {clarData.qa_exchange.answers && clarData.qa_exchange.answers[index] && (
                                <div className="answer">
                                  <strong>A:</strong> {clarData.qa_exchange.answers[index]}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {clarData.qa_exchange.skipped && (
                        <div className="qa-skipped">
                          <em>(Questions were skipped by user)</em>
                        </div>
                      )}
                      <div className="iteration-content rewriting-prompt">
                        {iteration.rewriting_prompt}
                      </div>
                    </CollapsibleSection>
                    <FlowNote message="This prompt produced the rewritten answer" />
                  </div>
                );
              })()}

              {/* 4. Rewritten Answer with Validation */}
              {(() => {
                const clarData = iteration.type_specific_data as ClarificationIterationData;
                const validationOutput = clarData.validation_output;
                return (
                  <div className={`iteration-section answer-section ${validationOutput === 'VALID' ? 'validation-passed' : ''}`}>
                    <SectionHeader
                      title="4. Rewritten Answer"
                      validationOutput={validationOutput}
                      showSuccessIcon={true}
                    />
                    <div className="iteration-content">
                      {iteration.rewritten_answer}
                    </div>
                  </div>
                );
              })()}

              {/* 5. Validation Findings */}
              {(() => {
                const clarData = iteration.type_specific_data as ClarificationIterationData;
                const validationOutput = clarData.validation_output;
                const hasFindings = clarData.validation_findings && clarData.validation_findings.length > 0;
                
                return (
                  <div className="iteration-section">
                    <h5>5. Validation Findings</h5>
                    {hasFindings ? (
                      <FindingsList findings={clarData.validation_findings!} title="View Details" />
                    ) : validationOutput === 'VALID' ? (
                      <div className="iteration-content">
                        <div className="validation-success-note">
                          ✓ This answer passed validation with result: <strong>VALID</strong>
                        </div>
                      </div>
                    ) : (
                      <div className="iteration-content">
                        <em>No detailed findings available for this validation result.</em>
                      </div>
                    )}
                  </div>
                );
              })()}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default IterationView;
