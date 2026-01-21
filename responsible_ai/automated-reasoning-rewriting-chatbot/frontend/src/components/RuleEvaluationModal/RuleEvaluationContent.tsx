import React, { useState } from 'react';
import { Finding, Rule } from '../../api/APIClient';
import styles from './RuleEvaluationModal.module.css';

interface RuleEvaluationContentProps {
  finding: Finding;
}

interface RuleCondition {
  id: string;
  text: string;
  satisfied: boolean;
  matchingPremises: string[];
  matchingClaims: string[];
}

const RuleEvaluationContent: React.FC<RuleEvaluationContentProps> = ({ finding }) => {
  const premises = finding.details.premises || [];
  const claims = finding.details.claims || [];
  const supportingRules = finding.details.supporting_rules || [];
  const confidence = finding.details.confidence || 1.0;

  // Only expand first rule by default
  const [expandedRules, setExpandedRules] = useState<Set<string>>(
    new Set(supportingRules.length > 0 ? [supportingRules[0].identifier] : [])
  );

  const toggleRule = (ruleId: string) => {
    setExpandedRules(prev => {
      const next = new Set(prev);
      if (next.has(ruleId)) {
        next.delete(ruleId);
      } else {
        next.add(ruleId);
      }
      return next;
    });
  };

  // Parse rule conditions and match them to premises/claims
  const parseRuleConditions = (rule: any): RuleCondition[] => {
    const conditions: RuleCondition[] = [];
    const naturalLanguage = rule.alternateExpression || rule.natural_language || '';

    if (!naturalLanguage) {
      return conditions;
    }

    // Simple parsing - split by numbered conditions
    // This is a basic implementation - can be enhanced based on actual rule format
    const parts = naturalLanguage.split(/\d+\)/);
    
    parts.forEach((part: string, index: number) => {
      if (index === 0 || !part.trim()) return; // Skip empty parts
      
      const conditionText = part.trim();
      
      // Find matching premises
      const matchingPremises = premises
        .filter(p => {
          const premiseText = (p.natural_language || '').toLowerCase();
          const condText = conditionText.toLowerCase();
          // Simple keyword matching
          return condText.split(' ').some((word: string) => 
            word.length > 3 && premiseText.includes(word)
          );
        })
        .map(p => p.natural_language || p.logic);

      // Find matching claims
      const matchingClaims = claims
        .filter(c => {
          const claimText = (c.natural_language || '').toLowerCase();
          const condText = conditionText.toLowerCase();
          return condText.split(' ').some((word: string) => 
            word.length > 3 && claimText.includes(word)
          );
        })
        .map(c => c.natural_language || c.logic);

      conditions.push({
        id: `${rule.identifier}-${index}`,
        text: conditionText,
        satisfied: true, // All conditions are satisfied for VALID findings
        matchingPremises,
        matchingClaims
      });
    });

    return conditions;
  };

  // Determine which claims a rule proves
  const getRuleProvenClaims = (rule: any): any[] => {
    const naturalLanguage = (rule.alternateExpression || rule.natural_language || '').toLowerCase();
    return claims.filter(claim => {
      const claimText = (claim.natural_language || claim.logic || '').toLowerCase();
      return naturalLanguage.includes(claimText);
    });
  };

  return (
    <div className={styles.container}>
      <p className={styles.subtitle}>
        Click rules to see how premises and claims map to conditions
      </p>

      {/* Facts Grid */}
      <div className={styles.factsGrid}>
        <div className={`${styles.factsBox} ${styles.premisesBox}`}>
          <h3 className={styles.factsTitle}>Premises (Given Facts)</h3>
          <div className={styles.factsList}>
            {premises.map((premise, idx) => (
              <div key={idx} className={styles.factItem}>
                {premise.natural_language || premise.logic}
              </div>
            ))}
          </div>
        </div>

        <div className={`${styles.factsBox} ${styles.claimsBox}`}>
          <h3 className={styles.factsTitle}>Claims (To Prove)</h3>
          <div className={styles.factsList}>
            {claims.map((claim, idx) => (
              <div key={idx} className={styles.factItem}>
                {claim.natural_language || claim.logic}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={styles.infoText}>
        <strong>How it works:</strong> Each rule defines conditions that must be satisfied. 
        Premises satisfy input conditions, and when all conditions pass, the rule proves the claims.
      </div>

      {/* Rules */}
      {supportingRules.map((rule, idx) => {
        const isExpanded = expandedRules.has(rule.identifier);
        const conditions = parseRuleConditions(rule);
        const provenClaims = getRuleProvenClaims(rule);

        return (
          <div key={rule.identifier} className={styles.ruleSection}>
            <div
              className={styles.ruleHeader}
              onClick={() => toggleRule(rule.identifier)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggleRule(rule.identifier);
                }
              }}
            >
              <span className={styles.ruleHeaderText}>
                Rule {idx + 1}: {rule.identifier}
              </span>
              <span className={styles.expandIcon}>
                {isExpanded ? '▼' : '▶'}
              </span>
            </div>

            {isExpanded && (
              <div className={styles.ruleBody}>
                {provenClaims.length > 0 && (
                  <div className={styles.ruleProves}>
                    <strong>This rule proves:</strong>
                    <div className={styles.ruleProvesList}>
                      {provenClaims.map((claim, cIdx) => (
                        <div key={cIdx}>→ {claim.natural_language || claim.logic}</div>
                      ))}
                    </div>
                  </div>
                )}

                {(rule.alternateExpression || rule.natural_language) && (
                  <div className={styles.ruleDescription}>
                    <strong>Rule Definition:</strong>
                    <div>{rule.alternateExpression || rule.natural_language}</div>
                  </div>
                )}

                {conditions.length > 0 && (
                  <div className={styles.conditionsList}>
                    {conditions.map((condition) => (
                      <div key={condition.id} className={styles.condition}>
                        <div className={styles.conditionHeader}>
                          <span className={styles.conditionStatus}>✓</span>
                          <div className={styles.conditionText}>{condition.text}</div>
                        </div>
                        {(condition.matchingPremises.length > 0 || condition.matchingClaims.length > 0) && (
                          <div className={styles.conditionMatches}>
                            {condition.matchingPremises.map((premise, pIdx) => (
                              <span key={`p-${pIdx}`} className={styles.matchTag}>
                                {premise}
                              </span>
                            ))}
                            {condition.matchingClaims.map((claim, cIdx) => (
                              <span key={`c-${cIdx}`} className={`${styles.matchTag} ${styles.matchTagClaim}`}>
                                {claim}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {!rule.alternateExpression && !rule.natural_language && (
                  <div className={styles.noRuleDescription}>
                    <em>Rule description not available. Only rule ID is shown.</em>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Conclusion */}
      <div className={styles.conclusionSection}>
        <div className={styles.conclusionIcon}>✓</div>
        <div className={styles.conclusionText}>All conditions satisfied - Claims proven valid</div>
        <div className={styles.confidenceBadge}>
          {Math.round(confidence * 100)}% Confidence
        </div>
      </div>
    </div>
  );
};

export default RuleEvaluationContent;
