import React from 'react';
import { render, screen } from '@testing-library/react';
import IterationView from './IterationView';
import { TypedIteration, IterationType, ARIterationData, ClarificationIterationData } from '../api/APIClient';

describe('IterationView - Validation Arrow', () => {
  test('shows validation arrow from previous iteration to current iteration for AR feedback', () => {
    const previousIteration: TypedIteration = {
      iteration_number: 0,
      iteration_type: IterationType.AR_FEEDBACK,
      original_answer: 'Original answer',
      rewritten_answer: 'First answer',
      rewriting_prompt: 'Initial prompt',
      type_specific_data: {
        findings: [],
        validation_output: 'INVALID',
        llm_decision: 'INITIAL',
      } as ARIterationData,
    };

    const currentIteration: TypedIteration = {
      iteration_number: 1,
      iteration_type: IterationType.AR_FEEDBACK,
      original_answer: 'First answer',
      rewritten_answer: 'Second answer',
      rewriting_prompt: 'Rewrite prompt',
      type_specific_data: {
        findings: [
          {
            validation_output: 'INVALID',
            details: {},
          },
        ],
        validation_output: 'VALID',
      } as ARIterationData,
    };

    const { container } = render(
      <IterationView iteration={currentIteration} previousIteration={previousIteration} />
    );

    // Check that validation arrow is present
    const arrow = container.querySelector('.validation-arrow');
    expect(arrow).toBeInTheDocument();
    expect(arrow?.textContent).toBe('→');

    // Check that both validation badges are present (Invalid -> Valid)
    const badges = container.querySelectorAll('.validation-badge');
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });

  test('shows validation arrow for user clarification iterations', () => {
    const previousIteration: TypedIteration = {
      iteration_number: 0,
      iteration_type: IterationType.AR_FEEDBACK,
      original_answer: 'Original answer',
      rewritten_answer: 'First answer',
      rewriting_prompt: 'Initial prompt',
      type_specific_data: {
        findings: [],
        validation_output: 'SATISFIABLE',
        llm_decision: 'INITIAL',
      } as ARIterationData,
    };

    const currentIteration: TypedIteration = {
      iteration_number: 1,
      iteration_type: IterationType.USER_CLARIFICATION,
      original_answer: 'First answer',
      rewritten_answer: 'Clarified answer',
      rewriting_prompt: 'Rewrite with clarification',
      type_specific_data: {
        qa_exchange: {
          questions: ['What did you mean?'],
          answers: ['I meant this'],
          skipped: false,
        },
        validation_output: 'VALID',
      } as ClarificationIterationData,
    };

    const { container } = render(
      <IterationView iteration={currentIteration} previousIteration={previousIteration} />
    );

    // Check that validation arrow is present
    const arrow = container.querySelector('.validation-arrow');
    expect(arrow).toBeInTheDocument();
    expect(arrow?.textContent).toBe('→');
  });

  test('does not show validation arrow when no previous iteration', () => {
    const currentIteration: TypedIteration = {
      iteration_number: 0,
      iteration_type: IterationType.AR_FEEDBACK,
      original_answer: 'Original answer',
      rewritten_answer: 'First answer',
      rewriting_prompt: 'Initial prompt',
      type_specific_data: {
        findings: [],
        validation_output: 'INVALID',
        llm_decision: 'INITIAL',
      } as ARIterationData,
    };

    const { container } = render(<IterationView iteration={currentIteration} />);

    // Check that validation arrow is NOT present
    const arrow = container.querySelector('.validation-arrow');
    expect(arrow).not.toBeInTheDocument();
  });

  test('does not show validation arrow when previous iteration has no validation output', () => {
    const previousIteration: TypedIteration = {
      iteration_number: 0,
      iteration_type: IterationType.USER_CLARIFICATION,
      original_answer: 'Original answer',
      rewritten_answer: 'First answer',
      rewriting_prompt: 'Initial prompt',
      type_specific_data: {
        qa_exchange: {
          questions: ['Question?'],
          answers: ['Answer'],
          skipped: false,
        },
        // No validation_output
      } as ClarificationIterationData,
    };

    const currentIteration: TypedIteration = {
      iteration_number: 1,
      iteration_type: IterationType.AR_FEEDBACK,
      original_answer: 'First answer',
      rewritten_answer: 'Second answer',
      rewriting_prompt: 'Rewrite prompt',
      type_specific_data: {
        findings: [],
        validation_output: 'VALID',
      } as ARIterationData,
    };

    const { container } = render(
      <IterationView iteration={currentIteration} previousIteration={previousIteration} />
    );

    // Check that validation arrow is NOT present (because previous has no validation)
    const arrow = container.querySelector('.validation-arrow');
    expect(arrow).not.toBeInTheDocument();
  });
});
