import React, { useState, useEffect } from 'react';
import APIClient from '../api/APIClient';
import FormInput from './shared/FormInput';

interface ConfigPanelProps {
  config: {
    model_id: string;
    policy_arn: string;
    max_iterations?: number;
  } | null;
  onConfigChange: (config: { model_id: string; policy_arn: string; max_iterations: number }) => void;
  onPolicyChange?: (policyArn: string) => void;
}

interface Model {
  id: string;
  name: string;
}

interface Policy {
  arn: string;
  name: string;
  description: string;
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({ config, onConfigChange, onPolicyChange }) => {
  const [models, setModels] = useState<Model[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [selectedPolicyArn, setSelectedPolicyArn] = useState<string>('');
  const [maxIterations, setMaxIterations] = useState<number>(5);
  const [maxIterationsError, setMaxIterationsError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingPolicies, setLoadingPolicies] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [apiClient] = useState(() => new APIClient());

  // Load available models and policies on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch models and policies in parallel
        const [modelsResponse, policiesResponse] = await Promise.all([
          apiClient.getModels(),
          apiClient.getPolicies(),
        ]);

        setModels(modelsResponse);
        setPolicies(policiesResponse);
      } catch (err) {
        console.error('Failed to load configuration options:', err);
        setError('Failed to load configuration options. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadOptions();
  }, [apiClient]);

  // Update local state when config prop changes
  useEffect(() => {
    if (config) {
      setSelectedModelId(config.model_id);
      setSelectedPolicyArn(config.policy_arn);
      setMaxIterations(config.max_iterations ?? 5);
    }
  }, [config]);

  const handleMaxIterationsChange = (value: string) => {
    setMaxIterationsError(null);
    
    // Allow empty string for user to clear the field
    if (value === '') {
      setMaxIterations(5);
      return;
    }
    
    const numValue = parseInt(value, 10);
    
    // Validate positive integer
    if (isNaN(numValue) || numValue <= 0 || !Number.isInteger(parseFloat(value))) {
      setMaxIterationsError('Must be a positive integer');
      setMaxIterations(numValue || 5);
      return;
    }
    
    setMaxIterations(numValue);
  };

  const handleRefreshPolicies = async () => {
    try {
      setLoadingPolicies(true);
      setError(null);
      
      const policiesResponse = await apiClient.getPolicies();
      setPolicies(policiesResponse);
    } catch (err) {
      console.error('Failed to refresh policies:', err);
      setError('Failed to refresh policies. Please try again.');
    } finally {
      setLoadingPolicies(false);
    }
  };

  const handleApplyConfig = async () => {
    if (!selectedModelId || !selectedPolicyArn) {
      setError('Please select both a model and a policy.');
      return;
    }

    // Validate max_iterations before submitting
    if (maxIterationsError || maxIterations <= 0) {
      setError('Please provide a valid positive integer for max iterations.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const newConfig = {
        model_id: selectedModelId,
        policy_arn: selectedPolicyArn,
        max_iterations: maxIterations,
      };

      await onConfigChange(newConfig);
      
      // Trigger policy change callback if policy has changed
      if (onPolicyChange && config && selectedPolicyArn !== config.policy_arn) {
        onPolicyChange(selectedPolicyArn);
      }
    } catch (err: any) {
      console.error('Failed to update configuration:', err);
      setError(
        err.response?.data?.error?.message ||
        'Failed to update configuration. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const hasChanges = 
    config && 
    (selectedModelId !== config.model_id || 
     selectedPolicyArn !== config.policy_arn ||
     maxIterations !== (config.max_iterations ?? 5));

  return (
    <div className="config-panel">
      <h2>Configuration</h2>
      
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      <div className="config-form">
        <div className="form-group">
          <label htmlFor="model-select">LLM Model:</label>
          <select
            id="model-select"
            value={selectedModelId}
            onChange={(e) => setSelectedModelId(e.target.value)}
            disabled={loading || models.length === 0}
          >
            <option value="">Select a model...</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="policy-select">AR Policy:</label>
          <div className="policy-select-container">
            <select
              id="policy-select"
              value={selectedPolicyArn}
              onChange={(e) => setSelectedPolicyArn(e.target.value)}
              disabled={loading || loadingPolicies || policies.length === 0}
            >
              <option value="">Select a policy...</option>
              {policies.map((policy) => (
                <option key={policy.name} value={policy.arn} title={policy.description}>
                  {policy.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={handleRefreshPolicies}
              disabled={loading || loadingPolicies}
              className="refresh-button"
              title="Refresh policy list"
              aria-label="Refresh policy list"
            >
              {loadingPolicies ? '⟳' : '↻'}
            </button>
          </div>
        </div>

        <FormInput
          id="max-iterations-input"
          label="Max Iterations:"
          type="number"
          min={1}
          step={1}
          value={maxIterations}
          onChange={handleMaxIterationsChange}
          error={maxIterationsError}
          disabled={loading}
        />

        <button
          onClick={handleApplyConfig}
          disabled={loading || !hasChanges || !selectedModelId || !selectedPolicyArn || !!maxIterationsError}
          className="apply-button"
        >
          {loading ? 'Applying...' : 'Apply Configuration'}
        </button>
      </div>

      {loading && <div className="loading-indicator">Loading...</div>}
    </div>
  );
};

export default ConfigPanel;
