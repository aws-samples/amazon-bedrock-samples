import { useState, useEffect } from 'react'
import {
  Container,
  Header,
  Button,
  Textarea
} from '@cloudscape-design/components'
import { apiService } from '../services/api'
import { useAppContext } from '../contexts/AppContext'

export default function SchemaViewer() {
  const { state } = useAppContext()
  const [schema, setSchema] = useState('')
  const [loading, setLoading] = useState(false)

  const loadFinalSchema = async () => {
    setLoading(true)
    try {
      const response = await apiService.getFinalSchema()
      console.log('Schema response:', response.data)
      
      if (response.data.status === 'success' && response.data.schema) {
        try {
          const parsedSchema = JSON.parse(response.data.schema)
          const formattedSchema = JSON.stringify(parsedSchema, null, 2)
          setSchema(formattedSchema)
        } catch (parseError) {
          setSchema(response.data.schema) // Show raw content if not valid JSON
        }
      } else {
        setSchema(response.data.message || 'No final schema found. The optimizer may not have completed successfully.')
      }
    } catch (error) {
      console.error('Error loading final schema:', error)
      setSchema('Error loading final schema. Make sure the optimizer has completed successfully.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Only load schema when optimizer completes
    if (state.status.status === 'completed') {
      loadFinalSchema()
    }
  }, [state.status.status])

  // Load schema when optimizer completes or when component mounts
  useEffect(() => {
    if (state.status.status === 'completed' || state.status.status === 'not_running') {
      loadFinalSchema()
    }
  }, [state.status.status])

  // Also try to load on mount
  useEffect(() => {
    loadFinalSchema()
  }, [])

  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={
            <Button onClick={loadFinalSchema} loading={loading}>
              Refresh Schema
            </Button>
          }
        >
          Final Schema
        </Header>
      }
    >
      <Textarea
        value={schema}
        readOnly
        rows={20}
        placeholder="Final schema will appear here after optimizer completes..."
      />
    </Container>
  )
}