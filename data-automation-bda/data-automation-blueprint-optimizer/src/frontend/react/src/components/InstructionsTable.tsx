import { Table, Header, Textarea } from '@cloudscape-design/components'
import { useAppContext } from '../contexts/AppContext'

interface InstructionsTableProps {
  invalidRows?: number[]
}

export default function InstructionsTable({ invalidRows = [] }: InstructionsTableProps) {
  const { state, dispatch } = useAppContext()

  const updateInstruction = (index: number, field: string, value: string) => {
    const updatedInputs = [...state.config.inputs]
    updatedInputs[index] = { ...updatedInputs[index], [field]: value }
    dispatch({
      type: 'SET_CONFIG',
      payload: { ...state.config, inputs: updatedInputs }
    })
  }

  return (
    <Table
      columnDefinitions={[
        {
          id: 'field_name',
          header: 'Field Name',
          cell: (item, index) => (
            <Textarea
              value={item.field_name}
              readOnly
              rows={2}
            />
          )
        },
        {
          id: 'instruction',
          header: 'Instruction',
          cell: (item, index) => (
            <Textarea
              value={item.instruction}
              readOnly
              rows={2}
            />
          )
        },
        {
          id: 'inference_type',
          header: 'Inference Type',
          cell: (item, index) => (
            <Textarea
              value={item.inference_type}
              readOnly
              rows={2}
            />
          )
        },
        {
          id: 'expected_output',
          header: 'Expected Output',
          cell: (item) => {
            const itemIndex = state.config.inputs.findIndex(input => input.field_name === item.field_name)
            const hasError = invalidRows.includes(itemIndex) && !item.expected_output.trim()
            return (
              <Textarea
                value={item.expected_output}
                onChange={({ detail }) => updateInstruction(itemIndex, 'expected_output', detail.value)}
                rows={2}
                invalid={hasError}
                placeholder={hasError ? 'Expected output is required' : 'Enter expected output...'}
              />
            )
          }
        }
      ]}
      items={state.config.inputs}
      header={<Header variant="h3">Instructions</Header>}
      empty="No instructions available. Fetch a blueprint to populate instructions."
    />
  )
}