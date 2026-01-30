import React from 'react';
import { render, screen } from '@testing-library/react';
import * as fc from 'fast-check';
import ValidationBadge from './ValidationBadge';
import { getValidationOutputClass } from '../../utils/validationUtils';

/**
 * Property-Based Tests for ValidationBadge Component
 * Using fast-check for property-based testing with minimum 100 iterations
 */

describe('ValidationBadge Component - Property-Based Tests', () => {
  /**
   * Feature: frontend-component-refactoring, Property 1: Validation badge styling consistency
   * 
   * For any validation output value, rendering a ValidationBadge component should produce
   * output containing the appropriate CSS class for that validation type
   * 
   * Validates: Requirements 1.1
   */
  test('Property 1: Validation badge styling consistency', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.constantFrom('VALID', 'INVALID', 'IMPOSSIBLE', 'TRANSLATION_AMBIGUOUS', 'SATISFIABLE', 'TOO_COMPLEX', 'NO_TRANSLATIONS'),
          fc.string() // Also test arbitrary strings
        ),
        (validationOutput) => {
          const { container } = render(
            <ValidationBadge validationOutput={validationOutput} />
          );
          
          const badge = container.querySelector('.validation-badge');
          expect(badge).toBeInTheDocument();
          
          // Get the expected CSS class from the utility function
          const expectedClass = getValidationOutputClass(validationOutput);
          
          // Verify the badge has the expected CSS class
          expect(badge).toHaveClass(expectedClass);
        }
      ),
      { numRuns: 100 }
    );
  });
});
