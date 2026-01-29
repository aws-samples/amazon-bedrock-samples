/**
 * Integration test to verify debouncing works correctly with rapid policy changes
 */
import { debounce } from './debounce';

describe('debounce integration', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('should only make one API call for rapid policy changes', () => {
    const mockApiCall = jest.fn();
    const debouncedApiCall = debounce(mockApiCall, 300);

    // Simulate rapid policy changes
    debouncedApiCall('policy-1');
    debouncedApiCall('policy-2');
    debouncedApiCall('policy-3');
    debouncedApiCall('policy-4');
    debouncedApiCall('policy-5');

    // No calls should have been made yet
    expect(mockApiCall).not.toHaveBeenCalled();

    // Advance time by 300ms
    jest.advanceTimersByTime(300);

    // Only one call should have been made with the last policy
    expect(mockApiCall).toHaveBeenCalledTimes(1);
    expect(mockApiCall).toHaveBeenCalledWith('policy-5');
  });

  it('should handle policy changes with delays between them', () => {
    const mockApiCall = jest.fn();
    const debouncedApiCall = debounce(mockApiCall, 300);

    // First policy change
    debouncedApiCall('policy-1');
    jest.advanceTimersByTime(300);
    expect(mockApiCall).toHaveBeenCalledTimes(1);
    expect(mockApiCall).toHaveBeenCalledWith('policy-1');

    // Second policy change after delay
    debouncedApiCall('policy-2');
    jest.advanceTimersByTime(300);
    expect(mockApiCall).toHaveBeenCalledTimes(2);
    expect(mockApiCall).toHaveBeenCalledWith('policy-2');
  });

  it('should reset timer on each rapid change', () => {
    const mockApiCall = jest.fn();
    const debouncedApiCall = debounce(mockApiCall, 300);

    // First change
    debouncedApiCall('policy-1');
    jest.advanceTimersByTime(200);
    expect(mockApiCall).not.toHaveBeenCalled();

    // Second change before first completes
    debouncedApiCall('policy-2');
    jest.advanceTimersByTime(200);
    expect(mockApiCall).not.toHaveBeenCalled();

    // Third change before second completes
    debouncedApiCall('policy-3');
    jest.advanceTimersByTime(300);

    // Only the last call should execute
    expect(mockApiCall).toHaveBeenCalledTimes(1);
    expect(mockApiCall).toHaveBeenCalledWith('policy-3');
  });
});
