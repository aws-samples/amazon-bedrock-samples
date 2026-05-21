import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import OriginalAnswerSection from './OriginalAnswerSection';
import { Finding } from '../api/APIClient';

describe('OriginalAnswerSection', () => {
  const mockFindings: Finding[] = [
    {
      validation_output: 'INVALID',
      details: {
        premises: [
          { logic: 'p1', natural_language: 'Premise 1' }
        ],
        claims: [
          { logic: 'c1', natural_language: 'Claim 1' }
        ]
      }
    }
  ];

  it('renders original answer text', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="This is the original answer"
        validationOutput="VALID"
        findings={[]}
      />
    );

    expect(screen.getByText('This is the original answer')).toBeInTheDocument();
  });

  it('renders validation output badge', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="VALID"
        findings={[]}
      />
    );

    expect(screen.getByText('Valid')).toBeInTheDocument();
  });

  it('does not render validation output when not provided', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        findings={[]}
      />
    );

    expect(screen.queryByText('Validation Output:')).not.toBeInTheDocument();
  });

  it('renders findings toggle button when findings are present', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="INVALID"
        findings={mockFindings}
      />
    );

    expect(screen.getByText(/View Findings \(1 finding\)/)).toBeInTheDocument();
  });

  it('does not render findings section when no findings', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="VALID"
        findings={[]}
      />
    );

    expect(screen.queryByText(/View Findings/)).not.toBeInTheDocument();
  });

  it('expands findings when toggle button is clicked', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="INVALID"
        findings={mockFindings}
      />
    );

    const toggleButton = screen.getByText(/View Findings/);
    fireEvent.click(toggleButton);

    // Check that findings details are visible
    expect(screen.getByText('Premise 1')).toBeInTheDocument();
    expect(screen.getByText('Claim 1')).toBeInTheDocument();
  });

  it('collapses findings when toggle button is clicked again', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="INVALID"
        findings={mockFindings}
      />
    );

    const toggleButton = screen.getByText(/View Findings/);
    
    // Expand
    fireEvent.click(toggleButton);
    expect(screen.getByText('Premise 1')).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(toggleButton);
    expect(screen.queryByText('Premise 1')).not.toBeInTheDocument();
  });

  it('applies correct CSS class for VALID validation output', () => {
    const { container } = render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="VALID"
        findings={[]}
      />
    );

    const badge = container.querySelector('.validation-valid');
    expect(badge).toBeInTheDocument();
  });

  it('applies correct CSS class for INVALID validation output', () => {
    const { container } = render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="INVALID"
        findings={[]}
      />
    );

    const badge = container.querySelector('.validation-invalid');
    expect(badge).toBeInTheDocument();
  });

  it('renders section header with emoji', () => {
    render(
      <OriginalAnswerSection
        originalAnswer="Test answer"
        validationOutput="VALID"
        findings={[]}
      />
    );

    expect(screen.getByText('Original Answer')).toBeInTheDocument();
  });
});
