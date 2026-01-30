import React from 'react';
import { Finding } from '../../api/APIClient';

interface FindingDetailsProps {
  finding: Finding;
}

const FindingDetails: React.FC<FindingDetailsProps> = ({ finding }) => {
  return (
    <div className="finding-details">
      {/* Premises */}
      {finding.details.premises && finding.details.premises.length > 0 && (
        <div className="finding-detail">
          <strong>Premises:</strong>
          <ul className="logic-list">
            {finding.details.premises.map((premise, i) => (
              <li key={i}>
                {premise.natural_language || premise.logic}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Claims */}
      {finding.details.claims && finding.details.claims.length > 0 && (
        <div className="finding-detail">
          <strong>Claims:</strong>
          <ul className="logic-list">
            {finding.details.claims.map((claim, i) => (
              <li key={i}>
                {claim.natural_language || claim.logic}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Confidence */}
      {finding.details.confidence !== undefined && (
        <div className="finding-detail">
          <strong>Confidence:</strong> {(finding.details.confidence * 100).toFixed(1)}%
        </div>
      )}
      
      {/* Supporting Rules (VALID) */}
      {finding.details.supporting_rules && finding.details.supporting_rules.length > 0 && (
        <div className="finding-detail">
          <strong>Supporting Rules:</strong>
          <ul className="rules-list">
            {finding.details.supporting_rules.map((rule, i) => (
              <li key={i}>
                <strong>Rule ID:</strong> {rule.identifier}
                {rule.natural_language && (
                  <div className="rule-content">
                    <em>{rule.natural_language}</em>
                  </div>
                )}
                {rule.content && (
                  <div className="rule-content">
                    <code>{rule.content}</code>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Contradicting Rules (INVALID/IMPOSSIBLE) */}
      {finding.details.contradicting_rules && finding.details.contradicting_rules.length > 0 && (
        <div className="finding-detail">
          <strong>Contradicting Rules:</strong>
          <ul className="rules-list">
            {finding.details.contradicting_rules.map((rule, i) => (
              <li key={i}>
                <strong>Rule ID:</strong> {rule.identifier}
                {rule.natural_language && (
                  <div className="rule-content">
                    <em>{rule.natural_language}</em>
                  </div>
                )}
                {rule.content && (
                  <div className="rule-content">
                    <code>{rule.content}</code>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* True Scenario (SATISFIABLE/VALID) */}
      {finding.details.claims_true_scenario && (
        <div className="finding-detail">
          <strong>Scenario Where Claims Are True:</strong>
          <ul className="scenario-list">
            {finding.details.claims_true_scenario.statements.map((stmt, i) => (
              <li key={i}>{stmt.natural_language || stmt.logic}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* False Scenario (SATISFIABLE) */}
      {finding.details.claims_false_scenario && (
        <div className="finding-detail">
          <strong>Scenario Where Claims Are False:</strong>
          <ul className="scenario-list">
            {finding.details.claims_false_scenario.statements.map((stmt, i) => (
              <li key={i}>{stmt.natural_language || stmt.logic}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Translation Options (TRANSLATION_AMBIGUOUS) */}
      {finding.details.translation_options && finding.details.translation_options.length > 0 && (
        <div className="finding-detail">
          <strong>Possible Interpretations:</strong>
          {finding.details.translation_options.map((option, i) => (
            <div key={i} className="translation-option">
              <em>Interpretation {i + 1}:</em>
              {option.translations.map((trans, j) => (
                <div key={j} className="translation-detail">
                  {trans.premises && trans.premises.length > 0 && (
                    <div>
                      <strong>Premises:</strong>
                      <ul className="logic-list">
                        {trans.premises.map((p, k) => (
                          <li key={k}>{p.natural_language || p.logic}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {trans.claims && trans.claims.length > 0 && (
                    <div>
                      <strong>Claims:</strong>
                      <ul className="logic-list">
                        {trans.claims.map((c, k) => (
                          <li key={k}>{c.natural_language || c.logic}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      
      {/* Logic Warning */}
      {finding.details.logic_warning && (
        <div className="finding-detail logic-warning">
          <strong>⚠️ Logic Warning:</strong> {finding.details.logic_warning.type}
          {finding.details.logic_warning.premises && finding.details.logic_warning.premises.length > 0 && (
            <div>
              <em>Premises:</em>
              <ul className="logic-list">
                {finding.details.logic_warning.premises.map((p, i) => (
                  <li key={i}>{p.natural_language || p.logic}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FindingDetails;
