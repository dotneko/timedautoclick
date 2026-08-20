#!/usr/bin/env python3
"""
Screen Monitor Library for macOS
Modified to detect and return the first queue number not equal to "1"
"""

import os
import sys
import time
import datetime
import hashlib
import re
import shutil
from typing import Optional, Tuple, List, Dict, Callable, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import threading
from queue import Queue, Empty

import pyautogui
import cv2
import numpy as np
from PIL import Image
import pytesseract

# Version
__version__ = "1.0.0"

class MonitorStatus(Enum):
    """Status of the monitor"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"  # NEW: When target queue number is found

@dataclass
class ScreenRegion:
    """Define a screen region with coordinates"""
    x1: int
    y1: int
    x2: int
    y2: int
    name: str = "Unnamed Region"
    
    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within this region"""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'x1': self.x1, 'y1': self.y1,
            'x2': self.x2, 'y2': self.y2,
            'name': self.name
        }

@dataclass
class MonitorConfig:
    """Configuration for the screen monitor"""
    check_interval: float = 1.0
    save_on_change: bool = True
    save_full_screenshots: bool = True
    output_dir: str = "screenshots"
    enable_ocr: bool = True
    enable_logging: bool = True
    ocr_preprocess: bool = True
    max_concurrent_checks: int = 1
    min_text_length: int = 1
    change_threshold: float = 0.1
    # NEW: Target queue number to find (skip "1")
    target_queue_number: str = "1"  # The number to skip
    stop_on_found: bool = True  # Stop when target is found
    require_exact_match: bool = False  # If True, exact match; if False, not equal to

@dataclass
class DetectionResult:
    """Result of a detection event"""
    timestamp: datetime.datetime
    title_text: str
    footer_text: str
    queue_text: str
    queue_number: Optional[str]
    title_changed: bool
    footer_changed: bool
    conditions_met: bool
    screenshot_paths: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_target_found: bool = False  # NEW: Whether this is the target queue number

class OCRProcessor:
    """Handles OCR operations with multiple fallback strategies"""
    
    def __init__(self, language: str = 'eng', config: Optional[str] = None):
        self.language = language
        self.config = config
        self._setup_tesseract()
    
    def _setup_tesseract(self):
        """Set up Tesseract path with multiple fallback options"""
        if pytesseract.pytesseract.tesseract_cmd and os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            return
        
        if shutil.which('tesseract'):
            return
        
        possible_paths = [
            '/opt/homebrew/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/usr/bin/tesseract',
            '/opt/local/bin/tesseract',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return
        
        raise RuntimeError("Tesseract not found. Please install with: brew install tesseract")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        denoised = cv2.medianBlur(thresh, 3)
        
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.dilate(denoised, kernel, iterations=1)
        processed = cv2.erode(processed, kernel, iterations=1)
        
        return Image.fromarray(processed)
    
    def extract_text(self, image: Image.Image, preprocess: bool = True) -> str:
        """Extract text from image using OCR"""
        try:
            if preprocess:
                processed_image = self.preprocess_image(image)
            else:
                processed_image = image
            
            configs = [
                self.config,
                '--psm 6',
                '--psm 7',
                '--psm 8',
                '--psm 3 --oem 3',
                '--psm 6 --oem 3',
                None
            ]
            
            for config in configs:
                try:
                    if config:
                        text = pytesseract.image_to_string(processed_image, lang=self.language, config=config)
                    else:
                        text = pytesseract.image_to_string(processed_image, lang=self.language)
                    
                    if text and text.strip():
                        return text.strip()
                except Exception:
                    continue
            
            try:
                text = pytesseract.image_to_string(image, lang=self.language)
                return text.strip()
            except:
                return ""
                
        except Exception as e:
            raise RuntimeError(f"OCR failed: {e}")
    
    def extract_queue_number(self, text: str) -> Optional[str]:
        """Extract queue number from OCR text"""
        cleaned_text = text.strip()
        
        patterns = [
            (r'queue\s*(?:number|#)?\s*[:.]?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            (r'position\s*(?:number|#)?\s*[:.]?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            (r'waiting\s*(?:number|#)?\s*[:.]?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            (r'([A-Z]{2,3}[-]?\d+)', re.IGNORECASE),
            (r'(\d+[-]\d+)', re.IGNORECASE),
            (r'#\s*(\d+)', re.IGNORECASE),
            (r'(\d{4,})', re.IGNORECASE),
            (r'(\d{3})', re.IGNORECASE),
        ]
        
        for pattern, flags in patterns:
            match = re.search(pattern, cleaned_text, flags)
            if match:
                return match.group(1)
        
        word_match = re.search(r'\b([A-Z0-9]{3,})\b', cleaned_text, re.IGNORECASE)
        return word_match.group(1) if word_match else None

class ScreenMonitor:
    """Main screen monitoring class with event-driven architecture"""
    
    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.regions: Dict[str, ScreenRegion] = {}
        self.ocr_processor = OCRProcessor()
        
        # State
        self.status = MonitorStatus.IDLE
        self.last_results: Dict[str, str] = {}
        self.last_hashes: Dict[str, str] = {}
        self.detection_count = 0
        self._running = False
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._event_queue = Queue()
        
        # NEW: Store the found queue number
        self.found_queue_number = None
        self.target_found = False
        
        # Callbacks
        self._callbacks: List[Callable] = []
        self._completion_callback: Optional[Callable] = None  # NEW
        
        # Setup directories
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary directories"""
        output_dir = Path(self.config.output_dir)
        self.dirs = {
            'root': output_dir,
            'title': output_dir / 'title_changes',
            'footer': output_dir / 'footer_changes',
            'queue': output_dir / 'queue_captures',
            'full': output_dir / 'full_captures'
        }
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def add_region(self, name: str, region: ScreenRegion) -> None:
        """Add a region to monitor"""
        if name in self.regions:
            raise ValueError(f"Region '{name}' already exists")
        
        region.name = name
        self.regions[name] = region
        self.last_results[name] = ""
        self.last_hashes[name] = ""
    
    def remove_region(self, name: str) -> None:
        """Remove a monitored region"""
        if name in self.regions:
            del self.regions[name]
            del self.last_results[name]
            del self.last_hashes[name]
    
    def set_callback(self, callback: Callable[[DetectionResult], None]) -> None:
        """Set callback function for detection events"""
        self._callbacks.append(callback)
    
    def set_completion_callback(self, callback: Callable[[Optional[str], DetectionResult], None]) -> None:
        """
        NEW: Set callback for when the target queue number is found
        
        Args:
            callback: Function that accepts (queue_number, detection_result)
        """
        self._completion_callback = callback
    
    def clear_callbacks(self) -> None:
        """Clear all registered callbacks"""
        self._callbacks.clear()
    
    def start(self) -> None:
        """Start monitoring in a separate thread"""
        if self.status == MonitorStatus.RUNNING:
            raise RuntimeError("Monitor is already running")
        
        if not self.regions:
            raise RuntimeError("No regions added. Use add_region() first.")
        
        # Reset state
        self.found_queue_number = None
        self.target_found = False
        
        self._running = True
        self._stop_event.clear()
        self._pause_event.clear()
        self.status = MonitorStatus.RUNNING
        
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop monitoring"""
        if self.status in [MonitorStatus.RUNNING, MonitorStatus.PAUSED]:
            self._running = False
            self._stop_event.set()
            self.status = MonitorStatus.STOPPED
            if self._thread:
                self._thread.join(timeout=5.0)
    
    def pause(self) -> None:
        """Pause monitoring"""
        if self.status == MonitorStatus.RUNNING:
            self.status = MonitorStatus.PAUSED
            self._pause_event.set()
    
    def resume(self) -> None:
        """Resume monitoring"""
        if self.status == MonitorStatus.PAUSED:
            self._pause_event.clear()
            self.status = MonitorStatus.RUNNING
    
    def get_status(self) -> MonitorStatus:
        """Get current monitor status"""
        return self.status
    
    def get_found_queue_number(self) -> Optional[str]:
        """NEW: Get the queue number that was found"""
        return self.found_queue_number
    
    def is_target_found(self) -> bool:
        """NEW: Check if target queue number was found"""
        return self.target_found
    
    def get_statistics(self) -> Dict:
        """Get monitoring statistics"""
        return {
            'status': self.status.value,
            'detection_count': self.detection_count,
            'regions_monitored': len(self.regions),
            'target_found': self.target_found,
            'found_queue_number': self.found_queue_number,
            'total_time': time.time() - getattr(self, '_start_time', time.time())
        }
    
    def _capture_region(self, region: ScreenRegion) -> Image.Image:
        """Capture a specific screen region"""
        return pyautogui.screenshot(region=(region.x1, region.y1, region.width, region.height))
    
    def _save_screenshot(self, image: Image.Image, prefix: str, suffix: str = "") -> str:
        """Save screenshot with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{prefix}_{timestamp}{suffix}.png"
        filepath = self.dirs['root'] / filename
        image.save(filepath)
        return str(filepath)
    
    def _save_to_category(self, image: Image.Image, category: str, suffix: str = "") -> str:
        """Save screenshot to category directory"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{category}_{timestamp}{suffix}.png"
        filepath = self.dirs[category] / filename
        image.save(filepath)
        return str(filepath)
    
    def _compute_text_hash(self, text: str) -> str:
        """Compute hash of text for change detection"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _log_detection(self, result: DetectionResult) -> None:
        """Log detection result to file"""
        if not self.config.enable_logging:
            return
        
        log_file = self.dirs['root'] / "detection_log.txt"
        with open(log_file, 'a') as f:
            f.write(f"[{result.timestamp.isoformat()}] Detection #{self.detection_count}\n")
            f.write(f"  Title: '{result.title_text}'\n")
            f.write(f"  Footer: '{result.footer_text}'\n")
            f.write(f"  Queue Number: {result.queue_number}\n")
            f.write(f"  Conditions Met: {result.conditions_met}\n")
            f.write(f"  Target Found: {result.is_target_found}\n")
            f.write(f"  Screenshots: {', '.join(result.screenshot_paths)}\n")
            f.write("-" * 50 + "\n")
    
    def _check_conditions(self, title_text: str, footer_text: str) -> bool:
        """Check if conditions are met for queue detection"""
        return "Virtual Waiting Room" in title_text and "Exit" in footer_text
    
    def _is_target_queue_number(self, queue_number: str) -> bool:
        """
        NEW: Check if this is the target queue number (not equal to "1")
        """
        if not queue_number:
            return False
        
        # Clean the queue number
        cleaned = queue_number.strip()
        
        # Check if it's not equal to "1"
        if self.config.require_exact_match:
            # Exact match required
            return cleaned == self.config.target_queue_number
        else:
            # Not equal to target (skip "1")
            return cleaned != self.config.target_queue_number
    
    def _process_detection(self, title_text: str, footer_text: str, 
                          title_image: Image.Image, footer_image: Image.Image,
                          queue_image: Image.Image, full_screenshot: Image.Image) -> Optional[DetectionResult]:
        """Process a detection event"""
        result = DetectionResult(
            timestamp=datetime.datetime.now(),
            title_text=title_text,
            footer_text=footer_text,
            queue_text="",
            queue_number=None,
            title_changed=False,
            footer_changed=False,
            conditions_met=False,
            screenshot_paths=[],
            is_target_found=False
        )
        
        # Check for changes
        title_hash = self._compute_text_hash(title_text)
        footer_hash = self._compute_text_hash(footer_text)
        
        result.title_changed = title_hash != self.last_hashes.get('title', '')
        result.footer_changed = footer_hash != self.last_hashes.get('footer', '')
        
        # Update last values
        self.last_hashes['title'] = title_hash
        self.last_hashes['footer'] = footer_hash
        self.last_results['title'] = title_text
        self.last_results['footer'] = footer_text
        
        # Save screenshots on change
        if self.config.save_on_change:
            if result.title_changed:
                path = self._save_to_category(title_image, 'title')
                result.screenshot_paths.append(path)
            
            if result.footer_changed:
                path = self._save_to_category(footer_image, 'footer')
                result.screenshot_paths.append(path)
        
        # Check conditions
        result.conditions_met = self._check_conditions(title_text, footer_text)
        
        if result.conditions_met and self.config.enable_ocr:
            # Process queue
            queue_text = self.ocr_processor.extract_text(queue_image, self.config.ocr_preprocess)
            result.queue_text = queue_text
            result.queue_number = self.ocr_processor.extract_queue_number(queue_text)
            
            if result.queue_number:
                # Check if this is the target queue number
                result.is_target_found = self._is_target_queue_number(result.queue_number)
                
                if result.is_target_found:
                    # NEW: Store the found queue number
                    self.found_queue_number = result.queue_number
                    self.target_found = True
                    print(f"\n🎯 TARGET FOUND: Queue number '{result.queue_number}' detected!")
                    print(f"   (Skipped '1' as requested)")
                
                # Save queue screenshots
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                suffix = f"_{result.queue_number}" if result.queue_number else ""
                
                queue_path = self._save_to_category(queue_image, 'queue', suffix)
                result.screenshot_paths.append(queue_path)
                
                if self.config.save_full_screenshots:
                    full_path = self._save_to_category(full_screenshot, 'full', suffix)
                    result.screenshot_paths.append(full_path)
                
                self.detection_count += 1
                
                # Log detection
                self._log_detection(result)
                
                # NEW: If target found and auto-stop is enabled, stop monitoring
                if result.is_target_found and self.config.stop_on_found:
                    print(f"🛑 Stopping monitor - target queue number found: {result.queue_number}")
                    self._running = False
                    self._stop_event.set()
                    self.status = MonitorStatus.COMPLETED
                    
                    # Call completion callback if set
                    if self._completion_callback:
                        self._completion_callback(result.queue_number, result)
        
        return result
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        self._start_time = time.time()
        print(f"Screen Monitor started. Monitoring {len(self.regions)} regions...")
        print(f"Looking for queue number not equal to '{self.config.target_queue_number}'")
        print(f"Output directory: {self.config.output_dir}")
        
        while self._running and not self._stop_event.is_set():
            # Check pause
            if self._pause_event.is_set():
                time.sleep(0.1)
                continue
            
            try:
                # Capture all regions
                captured_images = {}
                for name, region in self.regions.items():
                    captured_images[name] = self._capture_region(region)
                
                # Get title and footer text
                title_text = ""
                footer_text = ""
                queue_image = None
                
                if 'title' in captured_images:
                    title_text = self.ocr_processor.extract_text(
                        captured_images['title'], self.config.ocr_preprocess
                    )
                
                if 'footer' in captured_images:
                    footer_text = self.ocr_processor.extract_text(
                        captured_images['footer'], self.config.ocr_preprocess
                    )
                
                if 'queue' in captured_images:
                    queue_image = captured_images['queue']
                
                # Get full screenshot if needed
                full_screenshot = pyautogui.screenshot() if self.config.save_full_screenshots else None
                
                # Process detection
                result = self._process_detection(
                    title_text, footer_text,
                    captured_images.get('title', None),
                    captured_images.get('footer', None),
                    queue_image,
                    full_screenshot
                )
                
                # Trigger callbacks
                if result and (result.title_changed or result.footer_changed or result.conditions_met):
                    for callback in self._callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            print(f"Callback error: {e}")
                
                # If target was found and we stopped, break the loop
                if self.target_found and not self._running:
                    break
                
            except Exception as e:
                self.status = MonitorStatus.ERROR
                print(f"Monitor error: {e}")
                if not self._running:
                    break
            
            # Wait before next check
            time.sleep(self.config.check_interval)
        
        if self.target_found:
            self.status = MonitorStatus.COMPLETED
            print(f"✅ Monitor completed successfully - found queue number: {self.found_queue_number}")
        else:
            self.status = MonitorStatus.STOPPED
            print("Screen Monitor stopped without finding target.")

class MonitorBuilder:
    """Builder class for easy configuration of ScreenMonitor"""
    
    def __init__(self):
        self.config = MonitorConfig()
        self.regions: Dict[str, ScreenRegion] = {}
        self.callbacks: List[Callable] = []
    
    def set_check_interval(self, interval: float) -> 'MonitorBuilder':
        self.config.check_interval = interval
        return self
    
    def set_output_dir(self, directory: str) -> 'MonitorBuilder':
        self.config.output_dir = directory
        return self
    
    def enable_saving(self, enable: bool = True) -> 'MonitorBuilder':
        self.config.save_on_change = enable
        return self
    
    def enable_full_screenshots(self, enable: bool = True) -> 'MonitorBuilder':
        self.config.save_full_screenshots = enable
        return self
    
    def enable_ocr(self, enable: bool = True) -> 'MonitorBuilder':
        self.config.enable_ocr = enable
        return self
    
    def enable_logging(self, enable: bool = True) -> 'MonitorBuilder':
        self.config.enable_logging = enable
        return self
    
    # NEW: Auto-stop methods
    def set_max_detections(self, max_detections: int) -> 'MonitorBuilder':
        """Set maximum number of detections before auto-stopping"""
        self.config.max_detections = max_detections
        self.config.auto_stop = True
        return self
    
    def enable_auto_stop(self, enable: bool = True) -> 'MonitorBuilder':
        """Enable or disable auto-stop feature"""
        self.config.auto_stop = enable
        return self
    
    def add_region(self, name: str, x1: int, y1: int, x2: int, y2: int) -> 'MonitorBuilder':
        region = ScreenRegion(x1, y1, x2, y2, name)
        self.regions[name] = region
        return self
    
    def add_callback(self, callback: Callable) -> 'MonitorBuilder':
        self.callbacks.append(callback)
        return self
    
    def build(self) -> ScreenMonitor:
        monitor = ScreenMonitor(self.config)
        for name, region in self.regions.items():
            monitor.add_region(name, region)
        for callback in self.callbacks:
            monitor.set_callback(callback)
        return monitor

# Convenience functions
def create_monitor_with_regions(title_region: ScreenRegion, 
                               footer_region: ScreenRegion,
                               queue_region: ScreenRegion,
                               **kwargs) -> ScreenMonitor:
    """Create a monitor with the three standard regions"""
    builder = MonitorBuilder()
    
    # Apply configuration
    for key, value in kwargs.items():
        if hasattr(builder, f"set_{key}"):
            getattr(builder, f"set_{key}")(value)
    
    builder.add_region("title", title_region.x1, title_region.y1, title_region.x2, title_region.y2)
    builder.add_region("footer", footer_region.x1, footer_region.y1, footer_region.x2, footer_region.y2)
    builder.add_region("queue", queue_region.x1, queue_region.y1, queue_region.x2, queue_region.y2)
    
    return builder.build()