import React, { useState } from 'react';
import { Finding } from '../api/APIClient';
import ValidationBadge from './shared/ValidationBadge';
import FindingsList from './shared/FindingsList';
import SectionHeader from './shared/SectionHeader';
import FlowNote from './shared/FlowNote';

interface InitialAnswerViewProps {
  originalAnswer: string;
  originalValidationOutput: string;
  originalFindings: Finding[];
}

const InitialAnswerView: React.FC<InitialAnswerViewProps> = ({
  originalAnswer,
  originalValidationOutput,
  originalFindings
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className={`iteration-view initial-answer-view ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="iteration-header" onClick={toggleExpanded} style={{ cursor: 'pointer' }}>
        <div className="iteration-header-left">
          <span className="collapse-icon">{isExpanded ? '▼' : '▶'}</span>
          <h4>Initial Answer</h4>
          <span className="iteration-type-badge">Initial Response</span>
        </div>
        <span className="validation-summary">
          <ValidationBadge 
            validationOutput={originalValidationOutput}
            showSuccessIcon={true}
          />
        </span>
      </div>

      {isExpanded && (
        <div className="iteration-body">
          {/* 1. Initial Answer */}
          <div className={`iteration-section answer-section ${originalValidationOutput !== 'VALID' ? 'validation-failed' : 'validation-passed'}`}>
            <SectionHeader
              title="1. Initial Answer"
              validationOutput={originalValidationOutput}
              showSuccessIcon={true}
            />
            <div className="iteration-content">
              {originalAnswer}
            </div>
            {originalValidationOutput !== 'VALID' && originalFindings.length > 0 && (
              <FlowNote message="This validation result triggered the rewriting loop" />
            )}
          </div>

          {/* 2. AR Findings */}
          {originalFindings && originalFindings.length > 0 && (
            <div className="iteration-section">
              <h5>2. AR Findings</h5>
              <FindingsList 
                findings={originalFindings}
                title="View Details"
                defaultExpanded={false}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default InitialAnswerView;
