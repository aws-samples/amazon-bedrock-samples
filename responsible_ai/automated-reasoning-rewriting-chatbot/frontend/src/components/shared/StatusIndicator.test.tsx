import React from 'react';
import { render } from '@testing-library/react';
import StatusIndicator from './StatusIndicator';

/**
 * Basic tests for StatusIndicator Component
 */

describe('StatusIndicator Component', () => {
  test('renders processing status with spinner', () => {
    const { container } = render(<StatusIndicator status="PROCESSING" />);
    const indicator = container.querySelector('.status-indicator.processing');
    expect(indicator).toBeInTheDocument();
    expect(container.querySelector('.loading-spinner')).toBeInTheDocument();
    expect(indicator?.textContent).toContain('Processing...');
  });

  test('renders processing status with custom message', () => {
    const { container } = render(
      <StatusIndicator status="PROCESSING" customMessage="Loading data..." />
    );
    const indicator = container.querySelector('.status-indicator.processing');
    expect(indicator?.textContent).toContain('Loading data...');
  });

  test('renders error status', () => {
    const { container } = render(<StatusIndicator status="ERROR" />);
    const indicator = container.querySelector('.status-indicator.error');
    expect(indicator).toBeInTheDocument();
    expect(indicator?.textContent).toContain('An error occurred');
  });

  test('renders error status with custom message', () => {
    const { container } = render(
      <StatusIndicator status="ERROR" customMessage="Failed to load" />
    );
    const indicator = container.querySelector('.status-indicator.error');
    expect(indicator?.textContent).toContain('Failed to load');
  });

  test('returns null for COMPLETED status', () => {
    const { container } = render(<StatusIndicator status="COMPLETED" />);
    expect(container.firstChild).toBeNull();
  });

  test('returns null for AWAITING_USER_INPUT status', () => {
    const { container } = render(<StatusIndicator status="AWAITING_USER_INPUT" />);
    expect(container.firstChild).toBeNull();
  });
});
