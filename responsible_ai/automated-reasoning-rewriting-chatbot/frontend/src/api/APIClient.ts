import axios, { AxiosInstance } from 'axios';

export interface Config {
  model_id: string;
  policy_arn: string;
  guardrail_id?: string;
  guardrail_version?: string;
  max_iterations?: number;
}

export interface LogicStatement {
  logic: string;
  natural_language: string;
}

export interface Scenario {
  statements: LogicStatement[];
}

export interface Rule {
  identifier: string;
  policy_version_arn?: string;
  // Enriched fields (added when policy definition is available)
  content?: string;
  natural_language?: string;  // Legacy field name
  alternateExpression?: string;  // AWS field name (preferred)
  expression?: string;  // Formal logic expression
  description?: string;
}

export interface LogicWarning {
  type: string;
  premises?: LogicStatement[];
  claims?: LogicStatement[];
}

export interface TranslationOption {
  translations: Array<{
    premises?: LogicStatement[];
    claims?: LogicStatement[];
  }>;
}

export interface Finding {
  validation_output: string;
  details: {
    // Common fields
    premises?: LogicStatement[];
    claims?: LogicStatement[];
    untranslated_premises?: string[];
    untranslated_claims?: string[];
    confidence?: number;
    
    // SATISFIABLE specific
    claims_true_scenario?: Scenario;
    claims_false_scenario?: Scenario;
    
    // VALID specific
    supporting_rules?: Rule[];
    
    // INVALID/IMPOSSIBLE specific
    contradicting_rules?: Rule[];
    
    // TRANSLATION_AMBIGUOUS specific
    translation_options?: TranslationOption[];
    difference_scenarios?: Scenario[];
    
    // Logic warnings (can appear in multiple types)
    logic_warning?: LogicWarning;
  };
}

export interface QuestionAnswerExchange {
  questions: string[];
  answers: string[] | null;
  skipped: boolean;
}

// Legacy iteration format (for backward compatibility)
export interface Iteration {
  iteration_number: number;
  llm_response: string;
  validation_output: string;
  findings: Finding[];
  rewriting_prompt: string | null;
  qa_exchange: QuestionAnswerExchange | null;
}

// New typed iteration format
export enum IterationType {
  AR_FEEDBACK = "ar_feedback",
  USER_CLARIFICATION = "user_clarification"
}

export interface ARIterationData {
  findings: Finding[];
  validation_output: string;
  processed_finding_index?: number | null;
  llm_decision?: string;
  iteration_type?: string;
}

export interface ClarificationIterationData {
  qa_exchange: QuestionAnswerExchange;
  context_augmentation?: string;
  processed_finding_index?: number | null;
  llm_decision?: string;
  validation_output?: string;
  validation_findings?: Finding[];
}

export interface TypedIteration {
  iteration_number: number;
  iteration_type: IterationType;
  original_answer: string;
  rewritten_answer: string;
  rewriting_prompt: string;
  type_specific_data: ARIterationData | ClarificationIterationData;
}

// Type guard functions for iteration type checking
export function isARIteration(iteration: TypedIteration): iteration is TypedIteration & { type_specific_data: ARIterationData } {
  return iteration.iteration_type === IterationType.AR_FEEDBACK;
}

export function isClarificationIteration(iteration: TypedIteration): iteration is TypedIteration & { type_specific_data: ClarificationIterationData } {
  return iteration.iteration_type === IterationType.USER_CLARIFICATION;
}

export interface TestPrompt {
  test_case_id: string;
  guard_content: string;
}

export interface Thread {
  thread_id: string;
  user_prompt: string;
  model_id: string;
  status: 'PROCESSING' | 'COMPLETED' | 'ERROR' | 'AWAITING_USER_INPUT';
  original_answer?: string;
  original_validation_output?: string;
  original_findings?: Finding[];
  final_response: string;
  warning_message: string | null;
  iterations: TypedIteration[];
  iteration_counter?: number;
  max_iterations?: number;
  schema_version?: string;
  created_at: string;
  completed_at: string | null;
}

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = '/api') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async getConfig(): Promise<Config> {
    const response = await this.client.get('/config');
    return response.data;
  }

  async updateConfig(config: Config): Promise<void> {
    await this.client.post('/config', config);
  }

  async sendMessage(message: string): Promise<string> {
    const response = await this.client.post('/chat', { prompt: message });
    return response.data.thread_id;
  }

  async getThread(threadId: string): Promise<Thread> {
    const response = await this.client.get(`/thread/${threadId}`);
    return response.data.thread; 
  }

  async listThreads(): Promise<Thread[]> {
    const response = await this.client.get('/threads');
    return response.data.threads;
  }

  async getModels(): Promise<Array<{ id: string; name: string }>> {
    const response = await this.client.get('/config/models');
    return response.data.models;
  }

  async getPolicies(): Promise<Array<{ arn: string; name: string; description: string }>> {
    const response = await this.client.get('/config/policies');
    return response.data.policies;
  }

  async submitAnswers(threadId: string, answers: string[], skipped: boolean): Promise<void> {
    await this.client.post(`/thread/${threadId}/answer`, {
      answers,
      skipped
    });
  }

  async getTestCases(policyArn: string, signal?: AbortSignal): Promise<TestPrompt[]> {
    try {
      const encodedPolicyArn = encodeURIComponent(policyArn);
      const response = await this.client.get(`/policy/${encodedPolicyArn}/test-cases`, {
        signal
      });
      return response.data.test_cases;
    } catch (error) {
      // Don't throw error messages for cancelled requests
      if (axios.isAxiosError(error) && error.code === 'ERR_CANCELED') {
        throw error; // Let the caller handle cancellation
      }
      
      // Re-throw with the original error object for better error handling
      // The App component will extract the appropriate error message
      throw error;
    }
  }
}

export default APIClient;
