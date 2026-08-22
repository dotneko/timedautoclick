from screen_monitor import ScreenMonitorBuilder, OCRMode

# Using builder pattern
monitor = ScreenMonitorBuilder() \
    .with_title_region(87, 83, 291, 121) \
    .with_footer_region(168, 839, 340, 870) \
    .with_queue_region(188, 533, 316, 569) \
    .with_check_interval(1.0) \
    .with_timeout(30.0) \
    .with_excluded_values("1", "one") \
    .with_ocr_mode(OCRMode.STANDARD) \
    .with_callback('on_queue_found', lambda q, r: print(f"Found: {q}")) \
    .build()

# Start monitoring
queue_number = monitor.monitor()

# Check statistics
stats = monitor.get_stats()
print(f"Changes detected: {stats['change_count']}")
print(f"Found queues: {stats['found_queue_numbers']}")