import { useState } from 'react'
import {
  Container,
  Header,
  Button,
  SpaceBetween,
  StatusIndicator,
  Alert
} from '@cloudscape-design/components'
import { useAppContext } from '../contexts/AppContext'
import { apiService } from '../services/api'

export default function OptimizerControls() {
  const { state, dispatch } = useAppContext()
  const [loading, setLoading] = useState(false)
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  const validateOptimizerRequirements = () => {
    const errors = []
    if (!state.config.project_arn.trim()) errors.push('Project ARN')
    if (!state.config.blueprint_id.trim()) errors.push('Blueprint ID')
    if (!state.config.project_stage.trim()) errors.push('Project Stage')
    if (!state.config.input_document.trim()) errors.push('Input Document')
    if (!state.config.bda_s3_output_location.trim()) errors.push('BDA S3 Output Location')
    
    if (state.config.inputs.length === 0) {
      errors.push('At least one instruction')
    } else {
      const invalidInstructions = state.config.inputs.filter(
        (input, index) => !input.field_name.trim() || !input.instruction.trim() || !input.expected_output.trim()
      )
      if (invalidInstructions.length > 0) {
        errors.push('All instructions must have field name, instruction, and expected output filled')
      }
    }
    
    return errors
  }

  const runOptimizer = async () => {
    const errors = validateOptimizerRequirements()
    setValidationErrors(errors)
    if (errors.length > 0) {
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'error',
          message: `Cannot start optimizer. Please fix: ${errors.join(', ')}`
        }
      })
      return
    }
    
    // Clear validation errors on successful validation
    setValidationErrors([])

    setLoading(true)
    try {
      const response = await apiService.runOptimizer(state.settings)
      dispatch({ type: 'SET_STATUS', payload: { status: 'running' } })
      if (response.data.log_file) {
        dispatch({ type: 'SET_CURRENT_LOG', payload: response.data.log_file })
      }
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'success',
          message: 'Optimizer started successfully!'
        }
      })
      // Start polling for status updates
      startStatusPolling()
    } catch (error) {
      console.error('Error running optimizer:', error)
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'error',
          message: 'Failed to start optimizer. Please try again.'
        }
      })
    } finally {
      setLoading(false)
    }
  }

  const startStatusPolling = () => {
    const interval = setInterval(async () => {
      try {
        const response = await apiService.getOptimizerStatus()
        dispatch({ type: 'SET_STATUS', payload: response.data })
        
        if (response.data.status === 'completed' || response.data.status === 'not_running') {
          clearInterval(interval)
        }
      } catch (error) {
        console.error('Error checking status:', error)
        clearInterval(interval)
      }
    }, 2000) // Check every 2 seconds
  }

  const stopOptimizer = async () => {
    setLoading(true)
    try {
      await apiService.stopOptimizer()
      dispatch({ type: 'SET_STATUS', payload: { status: 'not_running' } })
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'success',
          message: 'Optimizer stopped successfully!'
        }
      })
    } catch (error) {
      console.error('Error stopping optimizer:', error)
      dispatch({
        type: 'ADD_NOTIFICATION',
        payload: {
          type: 'error',
          message: 'Failed to stop optimizer. Please try again.'
        }
      })
    } finally {
      setLoading(false)
    }
  }

  const getStatusIndicator = () => {
    switch (state.status.status) {
      case 'running':
        return <StatusIndicator type="in-progress">Running</StatusIndicator>
      case 'completed':
        return <StatusIndicator type="success">Completed</StatusIndicator>
      default:
        return <StatusIndicator type="stopped">Not Running</StatusIndicator>
    }
  }

  return (
    <Container header={<Header variant="h2">Optimizer Controls</Header>}>
      <SpaceBetween direction="vertical" size="m">
        {validationErrors.length > 0 && (
          <Alert type="error" header="Cannot start optimizer">
            Please fix the following issues:
            <ul style={{ marginTop: '8px', marginBottom: '0' }}>
              {validationErrors.map((error, index) => (
                <li key={index}>{error} is required</li>
              ))}
            </ul>
          </Alert>
        )}
        <SpaceBetween direction="horizontal" size="m">
          <Button
            variant="primary"
            onClick={runOptimizer}
            loading={loading}
            disabled={state.status.status === 'running'}
          >
            Run Optimizer
          </Button>
          <Button
            onClick={stopOptimizer}
            loading={loading}
            disabled={state.status.status !== 'running'}
          >
            Stop Optimizer
          </Button>
          {getStatusIndicator()}
        </SpaceBetween>
      </SpaceBetween>
    </Container>
  )
}