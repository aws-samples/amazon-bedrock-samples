import React from 'react';
import { Finding } from '../api/APIClient';
import ValidationBadge from './shared/ValidationBadge';
import FindingsList from './shared/FindingsList';

interface OriginalAnswerSectionProps {
  originalAnswer: string;
  validationOutput?: string;
  findings?: Finding[];
}

const OriginalAnswerSection: React.FC<OriginalAnswerSectionProps> = ({
  originalAnswer,
  validationOutput,
  findings
}) => {
  return (
    <div className="original-answer-section">
      <h4>Original Answer</h4>
      
      <div className="original-answer-content">
        <p>{originalAnswer}</p>
      </div>
      
      {validationOutput && (
        <div className="original-validation">
          <strong>Validation Output:</strong>
          <ValidationBadge validationOutput={validationOutput} />
        </div>
      )}
      
      {findings && findings.length > 0 && (
        <div className="original-findings-section">
          <FindingsList 
            findings={findings}
            title="View Findings"
            defaultExpanded={false}
          />
        </div>
      )}
    </div>
  );
};

export default OriginalAnswerSection;
