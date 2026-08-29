import { useState } from 'react'
import {
  Container,
  Header,
  Form,
  FormField,
  Input,
  Button,
  SpaceBetween,
  Grid,
  Select,
  Checkbox
} from '@cloudscape-design/components'
import { useAppContext } from '../contexts/AppContext'
import { apiService } from '../services/api'
import InstructionsTable from './InstructionsTable'
import InputDocumentField from './InputDocumentField'

export default function ConfigurationForm() {
  const { state, dispatch } = useAppContext()
  const [loading, setLoading] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [instructionErrors, setInstructionErrors] = useState<number[]>([])

  const validateBlueprintFields = () => {
    const errors: Record<string, string> = {}
    if (!state.config.project_arn.trim()) errors.project_arn = 'Project ARN is required'
    if (!state.config.blueprint_id.trim()) errors.blueprint_id = 'Blueprint ID is required'
    return errors
  }

  const validateAllRequiredFields = () => {
    const errors: Record<string, string> = {}
    if (!state.config.project_arn.trim()) errors.project_arn = 'Project ARN is required'
    if (!state.config.blueprint_id.trim()) errors.blueprint_id = 'Blueprint ID is required'
    if (!state.config.project_stage.trim()) errors.project_stage = 'Project Stage is required'
    if (!state.config.input_document.trim()) errors.input_document = 'Input Document is required'
    if (!state.config.bda_s3_output_location.trim()) errors.bda_s3_output_location = 'BDA S3 Output Location is required'
    
    // Validate instructions and track which ones have errors
    const invalidInstructionIndexes: number[] = []
    if (state.config.inputs.length === 0) {
      errors.instructions = 'At least one instruction is required'
    } else {
      state.config.inputs.forEach((input, index) => {
        if (!input.field_name.trim() || !input.instruction.trim() || !input.expected_output.trim()) {
          invalidInstructionIndexes.push(index)
        }
      })
      if (invalidInstructionIndexes.length > 0) {
        errors.instructions = 'All instructions must have field name, instruction, and expected output filled'
      }
    }
    
    setInstructionErrors(invalidInstructionIndexes)
    return errors
  }

  const handleInputChange = (field: string, value: string) => {
    const updatedConfig = { ...state.config, [field]: value }
    
    // Auto-populate document name from input document S3 URI
    if (field === 'input_document' && value.startsWith('s3://')) {
      const fileName = value.split('/').pop() || ''
      updatedConfig.document_name = fileName
    }
    
    // Auto-populate data automation profile ARN from project ARN
    if (field === 'project_arn' && value.includes('data-automation-project')) {
      const arnParts = value.split(':')
      if (arnParts.length >= 5) {
        const region = arnParts[3]
        const accountId = arnParts[4]
        updatedConfig.dataAutomation_profilearn = `arn:aws:bedrock:${region}:${accountId}:data-automation-profile/us.data-automation-v1`
      }
    }
    
    dispatch({
      type: 'SET_CONFIG',
      payload: updatedConfig
    })
  }

  // Function to extract S3 bucket from S3 URI and auto-populate output location
  const handleS3UriChange = (s3Uri: string) => {
    if (s3Uri.startsWith('s3://')) {
      try {
        const url = new URL(s3Uri)
        const bucketName = url.hostname
        const outputLocation = `s3://${bucketName}/output/`
        
        // Auto-populate the BDA S3 Output Location
        const updatedConfig = { 
          ...state.config, 
          input_document: s3Uri,
          bda_s3_output_location: outputLocation
        }
        
        // Auto-populate document name
        const fileName = s3Uri.split('/').pop() || ''
        updatedConfig.document_name = fileName
        
        dispatch({
          type: 'SET_CONFIG',
          payload: updatedConfig
        })
      } catch (error) {
        console.error('Error parsing S3 URI:', error)
      }
    }
  }

  const handleSettingsChange = (field: string, value: any) => {
    dispatch({
      type: 'SET_SETTINGS',
      payload: { ...state.settings, [field]: value }
    })
  }

  const saveConfig = async () => {
    const errors = validateAllRequiredFields()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'error',
          message: `Please fill in required fields: ${Object.values(errors).join(', ')}`
        }
      })
      return
    }
    
    // Clear errors on successful validation
    setFieldErrors({})
    setInstructionErrors([])

    setLoading(true)
    try {
      await apiService.updateConfig(state.config)
      setFieldErrors({}) // Clear any previous errors
      setInstructionErrors([])
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'success',
          message: 'Configuration saved successfully!'
        }
      })
    } catch (error) {
      console.error('Error saving config:', error)
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'error',
          message: 'Failed to save configuration. Please try again.'
        }
      })
    } finally {
      setLoading(false)
    }
  }

  const fetchBlueprint = async () => {
    const errors = validateBlueprintFields()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'error',
          message: `Please fill in required fields: ${Object.values(errors).join(', ')}`
        }
      })
      return
    }
    
    setLoading(true)
    try {
      const response = await apiService.fetchBlueprint({
        project_arn: state.config.project_arn,
        blueprint_id: state.config.blueprint_id,
        project_stage: state.config.project_stage
      })
      
      if (response.data.properties) {
        dispatch({
          type: 'SET_CONFIG',
          payload: {
            ...state.config,
            inputs: response.data.properties.map((prop: any) => ({
              field_name: prop.field_name,
              instruction: prop.instruction,
              expected_output: prop.expected_output || '',
              inference_type: prop.inference_type || 'explicit',
              data_point_in_document: true
            }))
          }
        })
        dispatch({
          type: 'ADD_NOTIFICATION',
          payload: {
            type: 'success',
            message: `Blueprint fetched successfully! Found ${response.data.properties.length} fields.`
          }
        })
      }
    } catch (error) {
      console.error('Error fetching blueprint:', error)
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'error',
          message: 'Failed to fetch blueprint. Please check your configuration and try again.'
        }
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container header={<Header variant="h2">Configuration</Header>}>
      <Form>
        <SpaceBetween direction="vertical" size="l">
          <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
            <FormField 
              label="Project ARN" 
              constraintText="Required"
              errorText={fieldErrors.project_arn}
            >
              <Input
                value={state.config.project_arn}
                onChange={({ detail }) => {
                  handleInputChange('project_arn', detail.value)
                  if (fieldErrors.project_arn) {
                    setFieldErrors(prev => ({ ...prev, project_arn: '' }))
                  }
                }}
                placeholder="ARN of a DataAutomationProject"
                invalid={!!fieldErrors.project_arn}
              />
            </FormField>
            <FormField 
              label="Blueprint ID" 
              constraintText="Required"
              errorText={fieldErrors.blueprint_id}
            >
              <Input
                value={state.config.blueprint_id}
                onChange={({ detail }) => {
                  handleInputChange('blueprint_id', detail.value)
                  if (fieldErrors.blueprint_id) {
                    setFieldErrors(prev => ({ ...prev, blueprint_id: '' }))
                  }
                }}
                placeholder="ID of the blueprint to optimize"
                invalid={!!fieldErrors.blueprint_id}
              />
            </FormField>
          </Grid>

          <Button variant="primary" onClick={fetchBlueprint} loading={loading}>
            Fetch Blueprint
          </Button>

          <Grid gridDefinition={[{ colspan: 4 }]}>
            <FormField 
              label="Project Stage" 
              constraintText="Required"
              errorText={fieldErrors.project_stage}
            >
              <Input
                value={state.config.project_stage}
                onChange={({ detail }) => {
                  handleInputChange('project_stage', detail.value)
                  if (fieldErrors.project_stage) {
                    setFieldErrors(prev => ({ ...prev, project_stage: '' }))
                  }
                }}
                placeholder="Stage of the project (default: LIVE)"
                invalid={!!fieldErrors.project_stage}
              />
            </FormField>
          </Grid>

          <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
            <InputDocumentField
              value={state.config.input_document}
              onChange={(value) => handleInputChange('input_document', value)}
              onS3UriChange={handleS3UriChange}
              errorText={fieldErrors.input_document}
              invalid={!!fieldErrors.input_document}
              onErrorClear={() => {
                if (fieldErrors.input_document) {
                  setFieldErrors(prev => ({ ...prev, input_document: '' }))
                }
              }}
            />
            <FormField 
              label="BDA S3 Output Location" 
              constraintText="Required - Auto-populated from input document bucket"
              errorText={fieldErrors.bda_s3_output_location}
            >
              <Input
                value={state.config.bda_s3_output_location}
                onChange={({ detail }) => {
                  handleInputChange('bda_s3_output_location', detail.value)
                  if (fieldErrors.bda_s3_output_location) {
                    setFieldErrors(prev => ({ ...prev, bda_s3_output_location: '' }))
                  }
                }}
                placeholder="S3 location for BDA output (auto-populated)"
                invalid={!!fieldErrors.bda_s3_output_location}
              />
            </FormField>
          </Grid>

          <Header variant="h3">Optimizer Settings</Header>
          <Grid gridDefinition={[{ colspan: 2 }, { colspan: 2 }, { colspan: 4 }, { colspan: 2 }, { colspan: 2 }]}>
            <FormField label="Threshold" constraintText="Value between 0 and 1">
              <Input
                type="number"
                value={state.settings.threshold.toString()}
                onChange={({ detail }) => {
                  const value = parseFloat(detail.value)
                  if (value >= 0 && value <= 1) {
                    handleSettingsChange('threshold', value)
                  }
                }}
                step="0.1"
                min="0"
                max="1"
              />
            </FormField>
            <FormField label="Max Iterations">
              <Input
                type="number"
                value={state.settings.maxIterations.toString()}
                onChange={({ detail }) => handleSettingsChange('maxIterations', parseInt(detail.value))}
              />
            </FormField>
            <FormField label="Model">
              <Select
                selectedOption={{ label: state.settings.model, value: state.settings.model }}
                onChange={({ detail }) => handleSettingsChange('model', detail.selectedOption.value)}
                options={[
                  { label: 'Anthropic', options: [
                    { label: 'Claude 3 Sonnet', value: 'anthropic.claude-3-sonnet-20240229-v1:0' },
                    { label: 'Claude 3 Haiku', value: 'anthropic.claude-3-haiku-20240307-v1:0' },
                    { label: 'Claude 3 Opus', value: 'anthropic.claude-3-opus-20240229-v1:0' },
                    { label: 'Claude 3.5 Sonnet', value: 'anthropic.claude-3-5-sonnet-20241022-v2:0' },
                    { label: 'Claude 3.7 Sonnet', value: 'anthropic.claude-3-7-sonnet-20250219-v1:0' },
                    { label: 'Claude 3.5 Haiku', value: 'anthropic.claude-3-5-haiku-20241022-v1:0' },
                    { label: 'Claude 4 Opus', value: 'anthropic.claude-opus-4-20250514-v1:0' },
                    { label: 'Claude 4 Sonnet', value: 'anthropic.claude-sonnet-4-20250514-v1:0' }
                  ]},
                  { label: 'Amazon', options: [
                    { label: 'Nova Premier', value: 'amazon.nova-premier-v1:0' },
                    { label: 'Nova Pro', value: 'amazon.nova-pro-v1:0' },
                    { label: 'Nova Lite', value: 'amazon.nova-lite-v1:0' },
                    { label: 'Nova Micro', value: 'amazon.nova-micro-v1:0' }
                  ]},
                  { label: 'Meta', options: [
                    { label: 'Llama 3 8B', value: 'meta.llama3-8b-instruct-v1:0' },
                    { label: 'Llama 3 70B', value: 'meta.llama3-70b-instruct-v1:0' }
                  ]}
                ]}
              />
            </FormField>
            <FormField label="Options">
              <SpaceBetween direction="vertical" size="xs">
                <Checkbox
                  checked={state.settings.useDoc}
                  onChange={({ detail }) => handleSettingsChange('useDoc', detail.checked)}
                >
                  Use document strategy
                </Checkbox>
                <Checkbox
                  checked={state.settings.clean}
                  onChange={({ detail }) => handleSettingsChange('clean', detail.checked)}
                >
                  Clean previous runs
                </Checkbox>
              </SpaceBetween>
            </FormField>
          </Grid>

          <InstructionsTable invalidRows={instructionErrors} />

          <Button variant="primary" onClick={saveConfig} loading={loading}>
            Save Configuration
          </Button>
        </SpaceBetween>
      </Form>
    </Container>
  )
}