export interface Instruction {
  instruction: string
  data_point_in_document: boolean
  field_name: string
  expected_output: string
  inference_type: string
}

export interface OptimizerConfig {
  project_arn: string
  blueprint_id: string
  document_name: string
  dataAutomation_profilearn: string
  project_stage: string
  input_document: string
  bda_s3_output_location: string
  inputs: Instruction[]
}

export interface OptimizerSettings {
  threshold: number
  maxIterations: number
  model: string
  useDoc: boolean
  clean: boolean
}

export interface OptimizerStatus {
  status: 'not_running' | 'running' | 'completed'
  return_code?: number
  error?: string
}

export interface Notification {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  dismissible?: boolean
  autoDismiss?: boolean
}

export interface AppState {
  config: OptimizerConfig
  settings: OptimizerSettings
  status: OptimizerStatus
  logs: string[]
  currentLogFile: string | null
  notifications: Notification[]
}