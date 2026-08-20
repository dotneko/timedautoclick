#!/usr/bin/env python3
"""
Example using MonitorBuilder with custom configuration
"""

import pyautogui
import time
from screen_monitor import MonitorBuilder, MonitorConfig, ScreenRegion, MonitorStatus

def get_first_non_one_queue_custom():
    """Get first queue number not equal to '1' using custom configuration"""
    
    screen_width, screen_height = pyautogui.size()
    
    # Create monitor with custom configuration
    monitor = (MonitorBuilder()
        .set_check_interval(0.5)  # Check every 0.5 seconds
        .set_output_dir("queue_detection")
        .enable_saving(True)
        .enable_full_screenshots(True)
        .enable_logging(True)
        .add_region("title", 12, 95, 323, 132)
        .add_region("footer", 30, 695, 309, 728)
        .add_region("queue", 110, 455, 238, 486)
        .build())
    
    # Customize the config for our specific needs
    monitor.config.target_queue_number = "1"  # Skip this number
    monitor.config.stop_on_found = True
    monitor.config.require_exact_match = False
    
    # Variable to store result
    result_queue = None
    
    def on_completion(queue_number, detection_result):
        nonlocal result_queue
        result_queue = queue_number
        print(f"🎯 Target found! Queue number: {queue_number}")
    
    # Set completion callback
    monitor.set_completion_callback(on_completion)
    
    # Start monitoring
    print("🔍 Searching for queue number not equal to '1'...")
    monitor.start()
    
    try:
        # Wait for completion or timeout
        timeout = 120  # 2 minutes timeout
        start_time = time.time()
        
        while monitor.get_status() != MonitorStatus.COMPLETED:
            if time.time() - start_time > timeout:
                print(f"⏱️ Timeout after {timeout} seconds")
                break
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n⚠️ Stopped by user")
    finally:
        monitor.stop()
    
    # Get the found queue number
    found = monitor.get_found_queue_number()
    return found

# Usage
queue_number = get_first_non_one_queue_custom()
if queue_number:
    print(f"\n✅ Found: {queue_number}")
    # Store as variable
    my_queue = queue_number
    print(f"💾 Stored in variable 'my_queue': {my_queue}")
else:
    print("❌ No queue number found")