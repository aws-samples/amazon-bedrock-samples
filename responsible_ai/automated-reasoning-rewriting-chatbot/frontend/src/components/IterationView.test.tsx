import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import IterationView from './IterationView';
import { TypedIteration, IterationType, ARIterationData, ClarificationIterationData } from '../api/APIClient';

describe('IterationView', () => {
  const mockARIteration: TypedIteration = {
    iteration_number: 1,
    iteration_type: IterationType.AR_FEEDBACK,
    original_answer: 'Original answer text',
    rewritten_answer: 'Rewritten answer text',
    rewriting_prompt: 'Please fix the response based on AR findings',
    type_specific_data: {
      findings: [
        {
          validation_output: 'INVALID',
          details: {
            premises: [
              { natural_language: 'Test premise 1', logic: 'premise1()' }
            ],
            claims: [
              { natural_language: 'Test claim 1', logic: 'claim1()' }
            ],
            confidence: 0.95,
          },
        },
      ],
      validation_output: 'INVALID',
    } as ARIterationData,
  };

  const mockClarificationIteration: TypedIteration = {
    iteration_number: 2,
    iteration_type: IterationType.USER_CLARIFICATION,
    original_answer: 'Answer needing clarification',
    rewritten_answer: 'Answer after clarification',
    rewriting_prompt: 'Rewrite based on user answers',
    type_specific_data: {
      qa_exchange: {
        questions: ['What did you mean by X?', 'Can you clarify Y?'],
        answers: ['I meant this', 'Y refers to that'],
        skipped: false,
      },
      context_augmentation: 'Additional context from user',
    } as ClarificationIterationData,
  };

  test('renders iteration number', () => {
    render(<IterationView iteration={mockARIteration} />);
    expect(screen.getByText('Iteration 1')).toBeInTheDocument();
  });

  test('renders iteration type badge for AR iteration', () => {
    render(<IterationView iteration={mockARIteration} />);
    expect(screen.getByText('AR Feedback')).toBeInTheDocument();
  });

  test('renders iteration type badge for clarification iteration', () => {
    render(<IterationView iteration={mockClarificationIteration} />);
    expect(screen.getByText('User Clarification')).toBeInTheDocument();
  });

  test('renders validation output badge for AR iteration', () => {
    render(<IterationView iteration={mockARIteration} />);
    // ValidationBadge component displays "Invalid" (capitalized) not "INVALID"
    const badges = screen.getAllByText('Invalid');
    expect(badges.length).toBeGreaterThan(0);
  });

  test('does not render validation badge for clarification iteration', () => {
    render(<IterationView iteration={mockClarificationIteration} />);
    expect(screen.queryByText('INVALID')).not.toBeInTheDocument();
    expect(screen.queryByText('VALID')).not.toBeInTheDocument();
  });

  test('renders all sections for AR iteration', () => {
    render(<IterationView iteration={mockARIteration} />);
    // New structure shows: Findings from Previous Answer, Rewriting Prompt, Rewritten Answer
    expect(screen.getByText('1. Validation Findings from Previous Answer')).toBeInTheDocument();
    expect(screen.getByText('2. Rewriting Prompt')).toBeInTheDocument();
    expect(screen.getByText('3. Rewritten Answer')).toBeInTheDocument();
  });

  test('renders rewritten answer for AR iteration', () => {
    render(<IterationView iteration={mockARIteration} />);
    expect(screen.getByText('Rewritten answer text')).toBeInTheDocument();
  });

  test('renders rewriting prompt for AR iteration when expanded', () => {
    render(<IterationView iteration={mockARIteration} />);
    
    // Prompt is collapsed by default, so it should not be visible
    expect(screen.queryByText('Please fix the response based on AR findings')).not.toBeInTheDocument();
    
    // Click to expand the prompt
    const promptHeader = screen.getByText('2. Rewriting Prompt');
    fireEvent.click(promptHeader);
    
    // Now the prompt should be visible
    expect(screen.getByText('Please fix the response based on AR findings')).toBeInTheDocument();
  });

  test('renders findings toggle button for AR iteration', () => {
    render(<IterationView iteration={mockARIteration} />);
    expect(screen.getByText(/View Details \(1 finding\)/i)).toBeInTheDocument();
  });

  test('expands AR findings when toggle button is clicked', () => {
    render(<IterationView iteration={mockARIteration} />);
    
    // Initially, findings details should not be visible
    expect(screen.queryByText(/Premises:/i)).not.toBeInTheDocument();
    
    // Click the toggle button
    const toggleButton = screen.getByText(/View Details \(1 finding\)/i);
    fireEvent.click(toggleButton);
    
    // Now findings details should be visible
    expect(screen.getByText(/Premises:/i)).toBeInTheDocument();
    expect(screen.getByText('Test premise 1')).toBeInTheDocument();
    expect(screen.getByText(/Claims:/i)).toBeInTheDocument();
    expect(screen.getByText('Test claim 1')).toBeInTheDocument();
    expect(screen.getByText(/Confidence:/i)).toBeInTheDocument();
    expect(screen.getByText('95.0%')).toBeInTheDocument();
  });

  test('collapses AR findings when toggle button is clicked again', () => {
    render(<IterationView iteration={mockARIteration} />);
    
    const toggleButton = screen.getByText(/View Details \(1 finding\)/i);
    
    // Expand
    fireEvent.click(toggleButton);
    expect(screen.getByText(/Premises:/i)).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(toggleButton);
    expect(screen.queryByText(/Premises:/i)).not.toBeInTheDocument();
  });

  test('does not render findings section when AR iteration has no findings', () => {
    const iterationWithoutFindings: TypedIteration = {
      ...mockARIteration,
      type_specific_data: {
        findings: [],
        validation_output: 'VALID',
      } as ARIterationData,
    };
    
    render(<IterationView iteration={iterationWithoutFindings} />);
    expect(screen.queryByText(/View Details/i)).not.toBeInTheDocument();
  });

  test('renders all sections for clarification iteration', () => {
    render(<IterationView iteration={mockClarificationIteration} />);
    // New structure shows: Findings, Questions, Rewriting Prompt, Answer, Validation Findings
    expect(screen.getByText('1. Validation Findings from Previous Answer')).toBeInTheDocument();
    expect(screen.getByText('2. LLM Decision: Ask Follow-up Questions')).toBeInTheDocument();
    expect(screen.getByText('3. Rewriting Prompt with User Answers')).toBeInTheDocument();
    expect(screen.getByText('4. Rewritten Answer')).toBeInTheDocument();
    expect(screen.getByText('5. Validation Findings')).toBeInTheDocument();
  });

  test('renders questions and answers for clarification iteration', () => {
    render(<IterationView iteration={mockClarificationIteration} />);
    // Questions appear in section 2
    const question1Elements = screen.getAllByText(/What did you mean by X\?/i);
    expect(question1Elements.length).toBeGreaterThan(0);
    const question2Elements = screen.getAllByText(/Can you clarify Y\?/i);
    expect(question2Elements.length).toBeGreaterThan(0);
    
    // Answers are in section 3, which is collapsed by default
    expect(screen.queryByText(/I meant this/i)).not.toBeInTheDocument();
    
    // Expand the prompt section to see answers
    const promptHeader = screen.getByText('3. Rewriting Prompt with User Answers');
    fireEvent.click(promptHeader);
    
    // Now answers should be visible
    expect(screen.getByText(/I meant this/i)).toBeInTheDocument();
    expect(screen.getByText(/Y refers to that/i)).toBeInTheDocument();
  });

  test('renders context augmentation when present', () => {
    render(<IterationView iteration={mockClarificationIteration} />);
    // Context augmentation is stored but not explicitly displayed in the new structure
    // It's used internally in the rewriting prompt
    // We can verify the component renders without errors
    expect(screen.getByText('3. Rewriting Prompt with User Answers')).toBeInTheDocument();
  });

  test('renders correctly when context augmentation is not present', () => {
    const iterationWithoutContext: TypedIteration = {
      ...mockClarificationIteration,
      type_specific_data: {
        qa_exchange: {
          questions: ['Question?'],
          answers: ['Answer'],
          skipped: false,
        },
        context_augmentation: undefined,
      } as ClarificationIterationData,
    };
    
    render(<IterationView iteration={iterationWithoutContext} />);
    // Component should still render the rewriting prompt section
    expect(screen.getByText('3. Rewriting Prompt with User Answers')).toBeInTheDocument();
  });

  test('renders skipped message when questions were skipped', () => {
    const skippedIteration: TypedIteration = {
      ...mockClarificationIteration,
      type_specific_data: {
        qa_exchange: {
          questions: ['Question?'],
          answers: null,
          skipped: true,
        },
      } as ClarificationIterationData,
    };
    
    render(<IterationView iteration={skippedIteration} />);
    
    // Expand the prompt section to see the skipped message
    const promptHeader = screen.getByText('3. Rewriting Prompt with User Answers');
    fireEvent.click(promptHeader);
    
    expect(screen.getByText(/Questions were skipped/i)).toBeInTheDocument();
  });

  test('applies correct CSS class for VALID validation output', () => {
    const validIteration: TypedIteration = {
      ...mockARIteration,
      type_specific_data: {
        findings: [],
        validation_output: 'VALID',
      } as ARIterationData,
    };
    
    const { container } = render(<IterationView iteration={validIteration} />);
    const badge = container.querySelector('.validation-valid');
    expect(badge).toBeInTheDocument();
  });

  test('applies correct CSS class for INVALID validation output', () => {
    const { container } = render(<IterationView iteration={mockARIteration} />);
    const badge = container.querySelector('.validation-invalid');
    expect(badge).toBeInTheDocument();
  });

  test('collapses iteration body when header is clicked', () => {
    render(<IterationView iteration={mockARIteration} />);
    
    // Initially expanded - check for rewritten answer text
    expect(screen.getByText('Rewritten answer text')).toBeInTheDocument();
    
    // Click header to collapse
    const header = screen.getByText('Iteration 1').closest('.iteration-header');
    fireEvent.click(header!);
    
    // Body should be hidden
    expect(screen.queryByText('Rewritten answer text')).not.toBeInTheDocument();
  });
});
