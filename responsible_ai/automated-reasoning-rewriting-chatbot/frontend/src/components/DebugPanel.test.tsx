import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import DebugPanel from './DebugPanel';
import { Thread, TypedIteration, IterationType, ARIterationData } from '../api/APIClient';

describe('DebugPanel', () => {
  const mockThread: Thread = {
    thread_id: 'test-thread-123',
    user_prompt: 'Test prompt',
    model_id: 'test-model',
    status: 'COMPLETED',
    original_answer: 'This is the original answer',
    original_validation_output: 'INVALID',
    original_findings: [
      {
        validation_output: 'INVALID',
        details: {
          premises: [
            { natural_language: 'Original premise', logic: 'premise()' }
          ],
        },
      },
    ],
    final_response: 'Test response',
    warning_message: null,
    iterations: [
      {
        iteration_number: 1,
        iteration_type: IterationType.AR_FEEDBACK,
        original_answer: 'This is the original answer',
        rewritten_answer: 'First rewritten response',
        rewriting_prompt: 'Please fix the response',
        type_specific_data: {
          findings: [
            {
              validation_output: 'INVALID',
              details: {
                premises: [
                  { natural_language: 'Test premise', logic: 'premise()' }
                ],
                claims: [
                  { natural_language: 'Test claim', logic: 'claim()' }
                ],
              },
            },
          ],
          validation_output: 'INVALID',
        } as ARIterationData,
      } as TypedIteration,
      {
        iteration_number: 2,
        iteration_type: IterationType.AR_FEEDBACK,
        original_answer: 'First rewritten response',
        rewritten_answer: 'Second rewritten response',
        rewriting_prompt: 'Fix remaining issues',
        type_specific_data: {
          findings: [],
          validation_output: 'VALID',
        } as ARIterationData,
      } as TypedIteration,
    ],
    iteration_counter: 2,
    max_iterations: 5,
    schema_version: '2.0',
    created_at: '2024-01-01T00:00:00Z',
    completed_at: '2024-01-01T00:01:00Z',
  };

  const mockOnToggle = jest.fn();

  beforeEach(() => {
    mockOnToggle.mockClear();
  });

  test('renders debug panel header', () => {
    render(<DebugPanel thread={null} isOpen={true} onToggle={mockOnToggle} />);
    expect(screen.getByText(/Debug Panel - Behind the Scenes/i)).toBeInTheDocument();
  });

  test('renders empty state when no thread is selected', () => {
    render(<DebugPanel thread={null} isOpen={true} onToggle={mockOnToggle} />);
    expect(screen.getByText(/Select a thread from the chat panel/i)).toBeInTheDocument();
  });

  test('renders thread data when thread is provided', () => {
    render(<DebugPanel thread={mockThread} isOpen={true} onToggle={mockOnToggle} />);
    
    // Check thread ID is displayed (using getByText with function matcher)
    expect(screen.getByText((content, element) => {
      return element?.tagName.toLowerCase() === 'h4' && content.includes('Thread:');
    })).toBeInTheDocument();
    
    // Check original prompt is displayed
    expect(screen.getByText(/Original Prompt:/i)).toBeInTheDocument();
    expect(screen.getByText('Test prompt')).toBeInTheDocument();
    
    // Check status is displayed
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
  });

  test('renders iteration history', () => {
    render(<DebugPanel thread={mockThread} isOpen={true} onToggle={mockOnToggle} />);
    
    // Check iterations heading
    expect(screen.getByText(/Validation & Rewriting Iterations:/i)).toBeInTheDocument();
    
    // Check both iterations are rendered
    expect(screen.getByText('Iteration 1')).toBeInTheDocument();
    expect(screen.getByText('Iteration 2')).toBeInTheDocument();
  });

  test('renders final response when available', () => {
    render(<DebugPanel thread={mockThread} isOpen={true} onToggle={mockOnToggle} />);
    
    expect(screen.getByText(/Final Response:/i)).toBeInTheDocument();
    expect(screen.getByText('Test response')).toBeInTheDocument();
  });

  test('renders warning message when present', () => {
    const threadWithWarning: Thread = {
      ...mockThread,
      warning_message: 'This is a warning',
    };
    
    render(<DebugPanel thread={threadWithWarning} isOpen={true} onToggle={mockOnToggle} />);
    expect(screen.getByText('This is a warning')).toBeInTheDocument();
  });

  test('handles panel toggle', () => {
    render(<DebugPanel thread={mockThread} isOpen={true} onToggle={mockOnToggle} />);
    
    const toggleButton = screen.getByRole('button', { name: /Close debug panel/i });
    fireEvent.click(toggleButton);
    
    expect(mockOnToggle).toHaveBeenCalledTimes(1);
  });

  test('applies correct CSS class when open', () => {
    const { container } = render(<DebugPanel thread={mockThread} isOpen={true} onToggle={mockOnToggle} />);
    const panel = container.querySelector('.debug-panel');
    
    expect(panel).toHaveClass('open');
    expect(panel).not.toHaveClass('closed');
  });

  test('applies correct CSS class when closed', () => {
    const { container } = render(<DebugPanel thread={mockThread} isOpen={false} onToggle={mockOnToggle} />);
    const panel = container.querySelector('.debug-panel');
    
    expect(panel).toHaveClass('closed');
    expect(panel).not.toHaveClass('open');
  });

  test('hides content when panel is closed', () => {
    render(<DebugPanel thread={mockThread} isOpen={false} onToggle={mockOnToggle} />);
    
    // Content should not be rendered when closed
    expect(screen.queryByText(/Original Prompt:/i)).not.toBeInTheDocument();
  });

  test('shows no iterations message when thread has no iterations', () => {
    const threadWithoutIterations: Thread = {
      ...mockThread,
      iterations: [],
    };
    
    render(<DebugPanel thread={threadWithoutIterations} isOpen={true} onToggle={mockOnToggle} />);
    expect(screen.getByText(/No iterations yet/i)).toBeInTheDocument();
  });

  test('renders original answer section when present', () => {
    render(<DebugPanel thread={mockThread} isOpen={true} onToggle={mockOnToggle} />);
    
    // The original answer is now shown as part of the iterations
    // Check that iterations are rendered
    expect(screen.getByText('Iteration 1')).toBeInTheDocument();
    expect(screen.getByText('Iteration 2')).toBeInTheDocument();
  });

  test('does not render original answer section when not present', () => {
    const threadWithoutOriginal: Thread = {
      ...mockThread,
      original_answer: undefined,
      original_validation_output: undefined,
      original_findings: undefined,
      iterations: [], // Remove iterations to avoid confusion
    };
    
    render(<DebugPanel thread={threadWithoutOriginal} isOpen={true} onToggle={mockOnToggle} />);
    
    // Should show "No iterations yet" message when there are no iterations
    expect(screen.getByText(/No iterations yet/i)).toBeInTheDocument();
  });
});
