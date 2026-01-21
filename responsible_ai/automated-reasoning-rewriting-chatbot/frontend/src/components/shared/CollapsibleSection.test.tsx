import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import * as fc from 'fast-check';
import CollapsibleSection from './CollapsibleSection';

/**
 * Property-Based Tests for CollapsibleSection Component
 * Using fast-check for property-based testing with minimum 100 iterations
 */

describe('CollapsibleSection Component - Property-Based Tests', () => {
  /**
   * Feature: frontend-component-refactoring, Property 12: Collapsible section state toggle
   * 
   * For any collapsible section, clicking the header should toggle the expanded state
   * from true to false or false to true
   * 
   * Validates: Requirements 3.2
   */
  test('Property 12: Collapsible section state toggle', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }), // title
        fc.string({ minLength: 1 }), // content
        fc.boolean(), // initial expanded state
        (title, content, initialExpanded) => {
          const { container } = render(
            <CollapsibleSection title={title} defaultExpanded={initialExpanded}>
              {content}
            </CollapsibleSection>
          );
          
          const header = container.querySelector('.collapsible-header');
          expect(header).toBeInTheDocument();
          
          // Check initial state
          const initialContent = container.querySelector('.collapsible-content');
          if (initialExpanded) {
            expect(initialContent).toBeInTheDocument();
          } else {
            expect(initialContent).not.toBeInTheDocument();
          }
          
          // Click to toggle
          fireEvent.click(header!);
          
          // Check toggled state (should be opposite of initial)
          const toggledContent = container.querySelector('.collapsible-content');
          if (initialExpanded) {
            expect(toggledContent).not.toBeInTheDocument();
          } else {
            expect(toggledContent).toBeInTheDocument();
          }
          
          // Click again to toggle back
          fireEvent.click(header!);
          
          // Check state is back to initial
          const finalContent = container.querySelector('.collapsible-content');
          if (initialExpanded) {
            expect(finalContent).toBeInTheDocument();
          } else {
            expect(finalContent).not.toBeInTheDocument();
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Feature: frontend-component-refactoring, Property 13: Collapsible section state persistence
   * 
   * For any collapsible section, after toggling the state, the state should remain
   * unchanged until the next user interaction
   * 
   * Validates: Requirements 3.5
   */
  test('Property 13: Collapsible section state persistence', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }), // title
        fc.string({ minLength: 1 }), // content
        fc.boolean(), // initial expanded state
        (title, content, initialExpanded) => {
          const { container, rerender } = render(
            <CollapsibleSection title={title} defaultExpanded={initialExpanded}>
              {content}
            </CollapsibleSection>
          );
          
          const header = container.querySelector('.collapsible-header');
          expect(header).toBeInTheDocument();
          
          // Toggle the state
          fireEvent.click(header!);
          
          // Get the state after toggle
          const contentAfterToggle = container.querySelector('.collapsible-content');
          const isExpandedAfterToggle = contentAfterToggle !== null;
          
          // Re-render with same props (simulating component update without user interaction)
          rerender(
            <CollapsibleSection title={title} defaultExpanded={initialExpanded}>
              {content}
            </CollapsibleSection>
          );
          
          // State should persist (remain the same as after toggle)
          const contentAfterRerender = container.querySelector('.collapsible-content');
          const isExpandedAfterRerender = contentAfterRerender !== null;
          
          expect(isExpandedAfterRerender).toBe(isExpandedAfterToggle);
        }
      ),
      { numRuns: 100 }
    );
  });
});
