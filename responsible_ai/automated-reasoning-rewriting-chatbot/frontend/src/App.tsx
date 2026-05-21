import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import APIClient, { Config, Thread, TestPrompt } from './api/APIClient';
import ConfigPanel from './components/ConfigPanel';
import ChatPanel from './components/ChatPanel';
import DebugPanel from './components/DebugPanel';
import TestPromptBrowser from './components/TestPromptBrowser';
import ConfirmationDialog from './components/ConfirmationDialog';
import { debounce } from './utils/debounce';

interface AppState {
  config: Config | null;
  threads: Thread[];
  selectedThreadId: string | null;
  debugPanelOpen: boolean;
  chatError: string | null;
  testPrompts: TestPrompt[];
  testPromptsLoading: boolean;
  testPromptsError: string | null;
  testPromptBrowserOpen: boolean;
  prefilledMessage: string;
  currentInputMessage: string;
  confirmationDialog: {
    isOpen: boolean;
    pendingPrompt: string;
  };
  testCasesAbortController: AbortController | null;
}

function App() {
  const [state, setState] = useState<AppState>({
    config: null,
    threads: [],
    selectedThreadId: null,
    debugPanelOpen: false,
    chatError: null,
    testPrompts: [],
    testPromptsLoading: false,
    testPromptsError: null,
    testPromptBrowserOpen: false,
    prefilledMessage: '',
    currentInputMessage: '',
    confirmationDialog: {
      isOpen: false,
      pendingPrompt: '',
    },
    testCasesAbortController: null,
  });

  const [apiClient] = useState(() => new APIClient());

  // Create a ref to store the abort controller for the current state
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Load initial configuration
    const loadConfig = async () => {
      try {
        const config = await apiClient.getConfig();
        setState(prev => ({ ...prev, config }));
      } catch (error) {
        console.error('Failed to load configuration:', error);
      }
    };

    loadConfig();

    // Cleanup: abort any in-flight test cases request on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [apiClient]);

  // Polling mechanism for thread updates
  useEffect(() => {
    const pollThreads = async () => {
      // Find all threads that are currently processing or awaiting user input
      const activeThreads = state.threads.filter(
        thread => thread.status === 'PROCESSING' || thread.status === 'AWAITING_USER_INPUT'
      );

      // Also include the selected thread if it exists and is active
      const threadsToPoll = new Set<string>();
      activeThreads.forEach(t => threadsToPoll.add(t.thread_id));
      
      // Always poll the selected thread if it's active
      if (state.selectedThreadId) {
        const selectedThread = state.threads.find(t => t.thread_id === state.selectedThreadId);
        if (selectedThread && (selectedThread.status === 'PROCESSING' || selectedThread.status === 'AWAITING_USER_INPUT')) {
          threadsToPoll.add(state.selectedThreadId);
        }
      }

      // If no threads need polling, skip
      if (threadsToPoll.size === 0) {
        return;
      }

      // Poll each thread
      const pollPromises = Array.from(threadsToPoll).map(async (threadId) => {
        try {
          const updatedThread = await apiClient.getThread(threadId);
          return updatedThread;
        } catch (error) {
          console.error(`Failed to poll thread ${threadId}:`, error);
          return null;
        }
      });

      const updatedThreads = await Promise.all(pollPromises);
      
      // Debug logging
      updatedThreads.forEach(ut => {
        if (ut && ut.iterations && ut.iterations.length > 0) {
          console.log('Poll - Thread with iterations:', {
            thread_id: ut.thread_id,
            iterations_count: ut.iterations.length,
            status: ut.status
          });
        }
      });
      
      // Update all threads at once to minimize re-renders
      setState(prev => ({
        ...prev,
        threads: prev.threads.map(t => {
          const updated = updatedThreads.find(ut => ut && ut.thread_id === t.thread_id);
          return updated || t;
        }),
      }));
    };

    // Set up polling interval (1 second for more responsive updates)
    const intervalId = setInterval(pollThreads, 1000);

    // Clean up interval on unmount
    return () => clearInterval(intervalId);
  }, [state.threads, state.selectedThreadId, apiClient]);

  const handleConfigChange = async (newConfig: Config) => {
    try {
      await apiClient.updateConfig(newConfig);
      setState(prev => ({ ...prev, config: newConfig }));
    } catch (error) {
      console.error('Failed to update configuration:', error);
    }
  };

  const handleSendMessage = async (message: string) => {
    try {
      setState(prev => ({ ...prev, chatError: null, currentInputMessage: '' }));
      const threadId = await apiClient.sendMessage(message);
      // Create a placeholder thread while we wait for the actual data
      const newThread: Thread = {
        thread_id: threadId,
        user_prompt: message,
        model_id: state.config?.model_id || '',
        status: 'PROCESSING',
        final_response: '',
        warning_message: null,
        iterations: [],
        created_at: new Date().toISOString(),
        completed_at: null,
      };
      setState(prev => ({ ...prev, threads: [...prev.threads, newThread] }));
    } catch (error: any) {
      console.error('Failed to send message:', error);
      const errorMessage = error.response?.data?.error?.message || 
                          'Failed to send message. Please try again.';
      setState(prev => ({ ...prev, chatError: errorMessage }));
    }
  };

  const handleSelectThread = async (threadId: string) => {
    setState(prev => ({ 
      ...prev, 
      selectedThreadId: threadId,
      debugPanelOpen: true // Open debug panel when thread is selected
    }));

    // Immediately fetch the latest thread data when selected
    try {
      const updatedThread = await apiClient.getThread(threadId);
      console.log('Selected thread data:', {
        thread_id: updatedThread.thread_id,
        status: updatedThread.status,
        iterations_count: updatedThread.iterations?.length || 0,
        iterations: updatedThread.iterations
      });
      setState(prev => ({
        ...prev,
        threads: prev.threads.map(t =>
          t.thread_id === updatedThread.thread_id ? updatedThread : t
        ),
      }));
    } catch (error) {
      console.error(`Failed to fetch thread ${threadId}:`, error);
    }
  };

  const handleToggleDebugPanel = () => {
    setState(prev => ({ ...prev, debugPanelOpen: !prev.debugPanelOpen }));
  };

  const handleSubmitAnswers = async (threadId: string, answers: string[], skipped: boolean) => {
    try {
      await apiClient.submitAnswers(threadId, answers, skipped);
      // Immediately fetch the updated thread
      const updatedThread = await apiClient.getThread(threadId);
      setState(prev => ({
        ...prev,
        threads: prev.threads.map(t =>
          t.thread_id === updatedThread.thread_id ? updatedThread : t
        ),
      }));
    } catch (error: any) {
      console.error('Failed to submit answers:', error);
      const errorMessage = error.response?.data?.error?.message || 
                          'Failed to submit answers. Please try again.';
      setState(prev => ({ ...prev, chatError: errorMessage }));
      throw error; // Re-throw so ThreadMessage can handle it
    }
  };

  // Map error types to user-friendly messages
  const mapErrorMessage = (error: any): string => {
    // Handle axios errors
    if (error.response) {
      const errorData = error.response.data?.error;
      
      if (errorData) {
        // Use the error details from the backend
        const details = errorData.details || errorData.message;
        
        // Map specific error codes to user-friendly messages
        switch (errorData.code) {
          case 'AUTHENTICATION_ERROR':
            return 'Authentication error. Please check your AWS credentials.';
          case 'SERVICE_UNAVAILABLE':
            return 'The AWS Bedrock service is temporarily unavailable. Please try again later.';
          case 'BAD_REQUEST':
            return `Invalid request: ${details}`;
          case 'INTERNAL_ERROR':
            return 'A server error occurred. Please try again.';
          default:
            return details || 'Failed to load test cases';
        }
      }
      
      // Fallback to status code
      if (error.response.status === 503) {
        return 'The service is temporarily unavailable. Please try again later.';
      } else if (error.response.status === 500) {
        return 'A server error occurred. Please try again.';
      } else if (error.response.status === 400) {
        return 'Invalid policy selected. Please select a different policy.';
      }
    }
    
    // Handle network errors
    if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
      return 'Unable to connect to server. Please check your network connection.';
    }
    
    // Handle timeout errors
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return 'Request timed out. Please try again.';
    }
    
    // Default error message
    return error.message || 'Failed to load test cases';
  };

  // The actual implementation of fetching test cases
  const fetchTestCases = useCallback(async (policyArn: string) => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create a new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Clear existing test prompts and set loading state
    setState(prev => ({
      ...prev,
      testPrompts: [],
      testPromptsLoading: true,
      testPromptsError: null,
      testCasesAbortController: abortController,
    }));

    try {
      console.log(`Fetching test cases for policy: ${policyArn}`);
      const testCases = await apiClient.getTestCases(policyArn, abortController.signal);
      console.log(`Successfully fetched ${testCases.length} test cases`);
      
      // Only update state if this request wasn't cancelled
      setState(prev => {
        // Check if this is still the current request
        if (prev.testCasesAbortController === abortController) {
          // Auto-open the test prompt browser if tests were loaded and it's currently closed
          const shouldAutoOpen = testCases.length > 0 && !prev.testPromptBrowserOpen;
          
          return {
            ...prev,
            testPrompts: testCases,
            testPromptsLoading: false,
            testCasesAbortController: null,
            testPromptBrowserOpen: shouldAutoOpen || prev.testPromptBrowserOpen,
          };
        }
        return prev;
      });
    } catch (error: any) {
      // Don't update state if the request was cancelled
      if (error.code === 'ERR_CANCELED') {
        console.log('Test cases request was cancelled');
        return;
      }

      // Log the error with details
      console.error('Failed to fetch test cases:', {
        policyArn,
        error: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      
      const errorMessage = mapErrorMessage(error);
      setState(prev => {
        // Only update error state if this is still the current request
        if (prev.testCasesAbortController === abortController) {
          return {
            ...prev,
            testPromptsLoading: false,
            testPromptsError: errorMessage,
            testCasesAbortController: null,
          };
        }
        return prev;
      });
    }
  }, [apiClient]);

  // Create a debounced version of the policy change handler (300ms delay)
  const debouncedFetchTestCases = useRef(
    debounce((policyArn: string) => {
      fetchTestCases(policyArn);
    }, 300)
  ).current;

  const handlePolicyChange = (policyArn: string) => {
    // Use the debounced version to prevent excessive API calls
    debouncedFetchTestCases(policyArn);
  };

  const handleTestPromptSelect = (prompt: string) => {
    // Check if there's unsent text in the chat input
    if (state.currentInputMessage.trim()) {
      // Show confirmation dialog
      setState(prev => ({
        ...prev,
        confirmationDialog: {
          isOpen: true,
          pendingPrompt: prompt,
        },
      }));
    } else {
      // No unsent text, directly populate the chat input
      setState(prev => ({
        ...prev,
        prefilledMessage: prompt,
      }));
    }
  };

  const handleConfirmReplace = () => {
    // User confirmed, replace the text
    setState(prev => ({
      ...prev,
      prefilledMessage: prev.confirmationDialog.pendingPrompt,
      confirmationDialog: {
        isOpen: false,
        pendingPrompt: '',
      },
    }));
  };

  const handleCancelReplace = () => {
    // User cancelled, preserve existing text
    setState(prev => ({
      ...prev,
      confirmationDialog: {
        isOpen: false,
        pendingPrompt: '',
      },
    }));
  };

  const handleMessageChange = (message: string) => {
    // Track the current input message for confirmation dialog logic
    setState(prev => ({
      ...prev,
      currentInputMessage: message,
      prefilledMessage: message,
    }));
  };

  const handleTestPromptBrowserToggle = () => {
    setState(prev => ({
      ...prev,
      testPromptBrowserOpen: !prev.testPromptBrowserOpen,
    }));
  };

  const handleRetryTestCases = () => {
    // Retry fetching test cases with the current policy
    if (state.config?.policy_arn) {
      console.log('Retrying test case fetch for policy:', state.config.policy_arn);
      fetchTestCases(state.config.policy_arn);
    }
  };

  const selectedThread = state.threads.find(t => t.thread_id === state.selectedThreadId) || null;

  return (
    <div className="App">
      <TestPromptBrowser
        testPrompts={state.testPrompts}
        isOpen={state.testPromptBrowserOpen}
        isLoading={state.testPromptsLoading}
        error={state.testPromptsError}
        onToggle={handleTestPromptBrowserToggle}
        onPromptSelect={handleTestPromptSelect}
        onRetry={handleRetryTestCases}
      />

      <div className={`app-container ${state.debugPanelOpen ? 'with-debug-panel' : ''} ${state.testPromptBrowserOpen ? 'with-test-prompt-browser' : ''}`}>
        <h1>Automated Reasoning checks chatbot</h1>
        
        <ConfigPanel 
          config={state.config}
          onConfigChange={handleConfigChange}
          onPolicyChange={handlePolicyChange}
        />
        
        <ChatPanel
          threads={state.threads}
          selectedThreadId={state.selectedThreadId}
          onSendMessage={handleSendMessage}
          onSelectThread={handleSelectThread}
          onSubmitAnswers={handleSubmitAnswers}
          error={state.chatError}
          prefilledMessage={state.prefilledMessage}
          onMessageChange={handleMessageChange}
        />
      </div>

      <DebugPanel
        thread={selectedThread}
        isOpen={state.debugPanelOpen}
        onToggle={handleToggleDebugPanel}
      />

      <ConfirmationDialog
        isOpen={state.confirmationDialog.isOpen}
        title="Replace existing text?"
        message="You have unsent text in the chat input. Do you want to replace it with the selected test prompt?"
        confirmLabel="Replace"
        cancelLabel="Cancel"
        onConfirm={handleConfirmReplace}
        onCancel={handleCancelReplace}
      />
    </div>
  );
}

export default App;
