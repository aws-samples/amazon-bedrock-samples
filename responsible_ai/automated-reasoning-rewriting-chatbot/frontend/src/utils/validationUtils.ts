/**
 * Validation utility functions for AR Chatbot frontend
 * Provides centralized logic for validation output handling and styling
 */

/**
 * Valid validation output types
 */
export type ValidationOutput =
  | 'VALID'
  | 'INVALID'
  | 'IMPOSSIBLE'
  | 'TRANSLATION_AMBIGUOUS'
  | 'SATISFIABLE'
  | 'TOO_COMPLEX'
  | 'NO_TRANSLATIONS';

/**
 * CSS class names for validation outputs
 */
export type ValidationCSSClass =
  | 'validation-valid'
  | 'validation-invalid'
  | 'validation-error'
  | 'validation-warning'
  | 'validation-default';

/**
 * Maps validation output to appropriate CSS class name
 * 
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
 * 
 * @param output - The validation output string
 * @returns The appropriate CSS class name for styling
 */
export function getValidationOutputClass(output: string): ValidationCSSClass {
  const normalizedOutput = output.toUpperCase();

  switch (normalizedOutput) {
    case 'VALID':
      return 'validation-valid';
    case 'INVALID':
    case 'IMPOSSIBLE':
    case 'TRANSLATION_AMBIGUOUS':
    case 'SATISFIABLE':
      return 'validation-invalid';
    case 'TOO_COMPLEX':
      return 'validation-error';
    case 'NO_TRANSLATIONS':
      return 'validation-warning';
    default:
      return 'validation-default';
  }
}

/**
 * Type guard to check if a string is a valid validation output
 * 
 * @param output - The string to check
 * @returns True if the output is a recognized validation output type
 */
export function isValidValidationOutput(output: string): output is ValidationOutput {
  const validOutputs: ValidationOutput[] = [
    'VALID',
    'INVALID',
    'IMPOSSIBLE',
    'TRANSLATION_AMBIGUOUS',
    'SATISFIABLE',
    'TOO_COMPLEX',
    'NO_TRANSLATIONS'
  ];
  
  return validOutputs.includes(output.toUpperCase() as ValidationOutput);
}

/**
 * Returns human-readable display text for validation output
 * 
 * @param output - The validation output string
 * @returns Formatted display text for the validation output
 */
export function getValidationDisplayText(output: string): string {
  const normalizedOutput = output.toUpperCase();

  switch (normalizedOutput) {
    case 'VALID':
      return 'Valid';
    case 'INVALID':
      return 'Invalid';
    case 'IMPOSSIBLE':
      return 'Impossible';
    case 'TRANSLATION_AMBIGUOUS':
      return 'Translation Ambiguous';
    case 'SATISFIABLE':
      return 'Satisfiable';
    case 'TOO_COMPLEX':
      return 'Too Complex';
    case 'NO_TRANSLATIONS':
      return 'No Translations';
    default:
      return output;
  }
}
