import React, { useState } from 'react';
import { Finding } from '../../api/APIClient';
import FindingDetails from './FindingDetails';
import RuleEvaluationModal from '../RuleEvaluationModal';
import { getValidationOutputClass } from '../../utils/validationUtils';

export interface FindingsListProps {
  findings: Finding[];
  title?: string;
  defaultExpanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}

const FindingsList: React.FC<FindingsListProps> = ({
  findings,
  title = 'View Details',
  defaultExpanded = false,
  onToggle,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [verificationModalFinding, setVerificationModalFinding] = useState<Finding | null>(null);

  const handleToggle = () => {
    const newExpandedState = !isExpanded;
    setIsExpanded(newExpandedState);
    if (onToggle) {
      onToggle(newExpandedState);
    }
  };

  // Handle empty findings array
  if (!findings || findings.length === 0) {
    return null;
  }

  // Check if any finding is VALID with supporting rules
  const hasValidFindingWithRules = findings.some(
    f => f.validation_output === 'VALID' && 
         f.details.supporting_rules && 
         f.details.supporting_rules.length > 0
  );

  // Get the first VALID finding with supporting rules for the verification button
  const validFindingWithRules = findings.find(
    f => f.validation_output === 'VALID' && 
         f.details.supporting_rules && 
         f.details.supporting_rules.length > 0
  );

  return (
    <div className="findings-list">
      <div className="findings-buttons">
        <button 
          className="findings-toggle-button"
          onClick={handleToggle}
        >
          {isExpanded ? '▼' : '▶'} {title} ({findings.length} finding{findings.length !== 1 ? 's' : ''})
        </button>
        
        {hasValidFindingWithRules && validFindingWithRules && (
          <button
            className="verification-button-inline"
            onClick={() => setVerificationModalFinding(validFindingWithRules)}
          >
            🔍 View Verification
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="findings-expanded">
          {findings.map((finding, index) => (
            <div key={index} className="finding-item">
              <div className="finding-header">
                <span className={`finding-badge ${getValidationOutputClass(finding.validation_output)}`}>
                  {finding.validation_output}
                </span>
              </div>
              <FindingDetails finding={finding} />
            </div>
          ))}
        </div>
      )}

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

export default FindingsList;
