import { useState, useEffect } from 'react'
import {
  Container,
  Header,
  Select,
  Button,
  SpaceBetween,
  Textarea,
  Toggle
} from '@cloudscape-design/components'
import { useAppContext } from '../contexts/AppContext'
import { apiService } from '../services/api'

export default function LogViewer() {
  const { state, dispatch } = useAppContext()
  const [logContent, setLogContent] = useState('')
  const [isTailing, setIsTailing] = useState(false)
  const [tailInterval, setTailInterval] = useState<NodeJS.Timeout | null>(null)

  useEffect(() => {
    loadLogFiles()
  }, [])

  const loadLogFiles = async () => {
    try {
      const response = await apiService.listLogs()
      dispatch({ type: 'SET_LOGS', payload: response.data.log_files || [] })
    } catch (error) {
      console.error('Error loading log files:', error)
    }
  }

  const loadLogFile = async (logFile: string) => {
    try {
      const response = await apiService.viewLog(logFile)
      setLogContent(response.data.content)
    } catch (error) {
      console.error('Error loading log file:', error)
    }
  }

  const toggleTailing = () => {
    if (isTailing) {
      if (tailInterval) {
        clearInterval(tailInterval)
        setTailInterval(null)
      }
      setIsTailing(false)
    } else {
      if (state.currentLogFile) {
        setIsTailing(true)
        // Load immediately
        loadLogFile(state.currentLogFile)
        // Then update every 1 second for faster updates
        const interval = setInterval(() => {
          if (state.currentLogFile) {
            loadLogFile(state.currentLogFile)
          }
        }, 1000)
        setTailInterval(interval)
      }
    }
  }

  // Auto-start tailing when optimizer is running
  useEffect(() => {
    if (state.status.status === 'running' && state.currentLogFile && !isTailing) {
      toggleTailing()
    }
  }, [state.status.status, state.currentLogFile])

  const cleanLogs = async () => {
    try {
      await apiService.cleanLogs()
      setLogContent('')
      dispatch({ type: 'SET_LOGS', payload: [] })
      dispatch({ type: 'SET_CURRENT_LOG', payload: null })
    } catch (error) {
      console.error('Error cleaning logs:', error)
    }
  }

  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={loadLogFiles}>Refresh</Button>
              <Toggle
                checked={isTailing}
                onChange={toggleTailing}
                disabled={!state.currentLogFile}
                description="Auto-refresh log content every second for real-time updates"
              >
                Auto-Refresh
              </Toggle>
              <Button onClick={cleanLogs}>Clean Logs</Button>
            </SpaceBetween>
          }
        >
          Optimizer Log
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="m">
        <Select
          selectedOption={
            state.currentLogFile
              ? { label: state.currentLogFile, value: state.currentLogFile }
              : null
          }
          onChange={({ detail }) => {
            const logFile = detail.selectedOption.value!
            dispatch({ type: 'SET_CURRENT_LOG', payload: logFile })
            loadLogFile(logFile)
          }}
          options={state.logs.map(log => ({ label: log, value: log }))}
          placeholder="Select a log file..."
        />
        <Textarea
          value={logContent}
          readOnly
          rows={20}
          placeholder="Logs will appear here when you run the optimizer..."
        />
      </SpaceBetween>
    </Container>
  )
}