import React from 'react';
import { Thread } from '../api/APIClient';
import IterationView from './IterationView';
import WarningMessage from './shared/WarningMessage';
import SidePanel from './shared/SidePanel';

interface DebugPanelProps {
  thread: Thread | null;
  isOpen: boolean;
  onToggle: () => void;
}

const DebugPanel: React.FC<DebugPanelProps> = ({ thread, isOpen, onToggle }) => {
  // Debug logging
  React.useEffect(() => {
    if (thread) {
      console.log('DebugPanel - Thread updated:', {
        thread_id: thread.thread_id,
        status: thread.status,
        iterations_count: thread.iterations?.length || 0,
        iterations: thread.iterations,
        has_iterations: thread.iterations && thread.iterations.length > 0
      });
    }
  }, [thread]);

  const renderContent = () => {
    if (!thread) {
      return (
        <div className="debug-empty-state">
          <p>Select a thread from the chat panel to view its validation and rewriting process.</p>
        </div>
      );
    }

    return (
      <div className="debug-thread-info">
        <div className="debug-thread-header">
          <h4>Thread: {thread.thread_id.substring(0, 8)}...</h4>
          <span className="debug-thread-status">{thread.status}</span>
        </div>

        <div className="debug-thread-prompt">
          <strong>Original Prompt:</strong>
          <p>{thread.user_prompt}</p>
        </div>

        {/* Note: Original answer is now shown as iteration 0 in the iterations list */}
        
        {thread.iterations && thread.iterations.length > 0 ? (
          <div className="iterations-container">
            <h4>Validation & Rewriting Iterations:</h4>
            <div className="iterations-list">
              {thread.iterations.map((iteration, index) => (
                <IterationView 
                  key={iteration.iteration_number}
                  iteration={iteration}
                  previousIteration={index > 0 ? thread.iterations[index - 1] : undefined}
                />
              ))}
            </div>
          </div>
        ) : (
          <div className="debug-no-iterations">
            <p>No iterations yet. The thread is still being processed.</p>
          </div>
        )}

        {thread.final_response && (
          <div className="debug-final-response">
            <h4>Final Response:</h4>
            <p>{thread.final_response}</p>
          </div>
        )}

        {thread.warning_message && (
          <WarningMessage message={thread.warning_message} className="debug-warning" />
        )}
      </div>
    );
  };

  return (
    <SidePanel
      title="Debug Panel - Behind the Scenes"
      icon="🔍"
      isOpen={isOpen}
      onToggle={onToggle}
      className="debug-panel"
      classPrefix="debug-panel"
    >
      {renderContent()}
    </SidePanel>
  );
};

export default DebugPanel;
