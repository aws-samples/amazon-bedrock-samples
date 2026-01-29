import { debounce } from './debounce';

describe('debounce', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('should delay function execution', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 300);

    debouncedFn('test');
    expect(mockFn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(300);
    expect(mockFn).toHaveBeenCalledWith('test');
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('should only execute once for multiple rapid calls', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 300);

    debouncedFn('call1');
    debouncedFn('call2');
    debouncedFn('call3');

    jest.advanceTimersByTime(300);

    // Should only be called once with the last argument
    expect(mockFn).toHaveBeenCalledTimes(1);
    expect(mockFn).toHaveBeenCalledWith('call3');
  });

  it('should reset timer on each call', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 300);

    debouncedFn('call1');
    jest.advanceTimersByTime(200);
    
    debouncedFn('call2');
    jest.advanceTimersByTime(200);
    
    // Should not have been called yet
    expect(mockFn).not.toHaveBeenCalled();
    
    jest.advanceTimersByTime(100);
    
    // Now it should be called with the last argument
    expect(mockFn).toHaveBeenCalledTimes(1);
    expect(mockFn).toHaveBeenCalledWith('call2');
  });

  it('should handle multiple arguments', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 300);

    debouncedFn('arg1', 'arg2', 'arg3');
    jest.advanceTimersByTime(300);

    expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2', 'arg3');
  });

  it('should allow multiple executions after delay', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 300);

    debouncedFn('call1');
    jest.advanceTimersByTime(300);
    expect(mockFn).toHaveBeenCalledTimes(1);

    debouncedFn('call2');
    jest.advanceTimersByTime(300);
    expect(mockFn).toHaveBeenCalledTimes(2);
  });
});
