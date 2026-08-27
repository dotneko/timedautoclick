#!/usr/bin/env python3
"""
Screen Monitor with OCR - A library for monitoring screen regions and extracting queue numbers
"""

import os
import sys
import time
import datetime
import hashlib
import signal
import re
from typing import Optional, Tuple, List, Dict, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import threading

import pyautogui
import cv2
import numpy as np
from PIL import Image
import pytesseract

HOME_ASSIGN_QUEUE="10"

class OCRMode(Enum):
    """OCR preprocessing modes"""
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    LIGHT = "light"
    NONE = "none"


class MonitorStatus(Enum):
    """Status of the monitor"""
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    TIMEOUT = "timeout"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ScreenRegion:
    """Define a screen region with coordinates"""
    x1: int
    y1: int
    x2: int
    y2: int
    
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
    
    def is_valid(self) -> bool:
        """Check if the region has valid coordinates"""
        return self.x1 < self.x2 and self.y1 < self.y2
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to tuple format (x, y, width, height)"""
        return (self.x1, self.y1, self.width, self.height)
    
    @classmethod
    def from_tuple(cls, coords: Tuple[int, int, int, int]) -> 'ScreenRegion':
        """Create from tuple format (x1, y1, x2, y2)"""
        return cls(coords[0], coords[1], coords[2], coords[3])


@dataclass
class OCRResult:
    """Result of OCR processing"""
    text: str = ""  # Default empty string
    confidence: float = 0.0
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    region_name: str = ""
    queue_number: Optional[str] = None
    is_valid: bool = False
    
    def __str__(self) -> str:
        return f"OCRResult(text='{self.text}', queue='{self.queue_number}', valid={self.is_valid})"


@dataclass
class MonitorConfig:
    """Configuration for the screen monitor"""
    # Region definitions
    title_region: Optional[ScreenRegion] = None
    footer_region: Optional[ScreenRegion] = None
    queue_region: Optional[ScreenRegion] = None
    home_region: Optional[ScreenRegion] = None
    
    # Monitoring settings
    check_interval: float = 1.0
    timeout: Optional[float] = None
    save_on_change: bool = True
    save_all_captures: bool = False
    ocr_mode: OCRMode = OCRMode.STANDARD
    
    # Output settings
    output_dir: str = "screenshots"
    log_enabled: bool = True
    log_file: str = "monitor.log"
    
    # Queue number validation
    excluded_values: List[str] = field(default_factory=lambda: ["1"])
    queue_patterns: List[str] = field(default_factory=lambda: [
        #r'(?:queue|position|number|#)\s*[:.]?\s*([A-Z0-9\-]+)',
        #r'([A-Z]{2,3}-\d+)',
        #r'(\d+-\d+)',
        #r'(\d+)',
        r'(\d{3,})'     # At least 3 digits
    ])
    
    # Trigger conditions
    title_triggers: List[str] = field(default_factory=lambda: ["VirtualWaitingRoom"])
    footer_triggers: List[str] = field(default_factory=lambda: ["Exit"])
    home_triggers: List[str] = field(default_factory=lambda: ["YourSchedule"])
    
    # Callbacks
    on_queue_found: Optional[Callable] = None
    on_change_detected: Optional[Callable] = None
    on_error: Optional[Callable] = None
    on_status_change: Optional[Callable] = None


class ScreenMonitor:
    """
    Screen Monitor with OCR capabilities for extracting queue numbers
    
    This class provides a comprehensive solution for monitoring screen regions,
    performing OCR, and extracting queue numbers with validation.
    """
    
    def __init__(self, config: MonitorConfig):
        """
        Initialize the screen monitor
        
        Args:
            config: MonitorConfig object with all settings
        """
        self.config = config
        self._validate_config()
        
        # State tracking
        self.status = MonitorStatus.IDLE
        self.last_ocr_results: Dict[str, OCRResult] = {}
        self.last_hashes: Dict[str, str] = {}
        self.change_count = 0
        self.found_queue_numbers: List[str] = []
        self.start_time: Optional[float] = None
        self._stop_monitoring = False
        self._pause_monitoring = False
        self._result_lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Set up output directories
        self._setup_directories()
        
        # Configure Tesseract
        self._configure_tesseract()
    
    def _validate_config(self):
        """Validate the configuration"""
        if self.config.title_region and not self.config.title_region.is_valid():
            raise ValueError("Invalid title region configuration")
        if self.config.footer_region and not self.config.footer_region.is_valid():
            raise ValueError("Invalid footer region configuration")
        if self.config.queue_region and not self.config.queue_region.is_valid():
            raise ValueError("Invalid queue region configuration")
        if self.config.home_region and not self.config.home_region.is_valid():
            raise ValueError("Invalid home region configuration")
        
        if self.config.check_interval <= 0:
            raise ValueError("Check interval must be positive")
        
        if self.config.timeout is not None and self.config.timeout <= 0:
            raise ValueError("Timeout must be positive")
    
    def _setup_directories(self):
        """Create output directories"""
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'title': self.output_dir / "title_changes",
            'footer': self.output_dir / "footer_changes",
            'queue': self.output_dir / "queue_captures",
            'home': self.output_dir / "home_captures",
            'full': self.output_dir / "full_captures",
            'all': self.output_dir / "all_captures"
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
    
    def _configure_tesseract(self):
        """Configure Tesseract OCR"""
        try:
            if sys.platform == "darwin":
                # Check common Tesseract installation paths
                paths = [
                    '/opt/homebrew/bin/tesseract',
                    '/usr/local/bin/tesseract',
                    '/usr/bin/tesseract'
                ]
                for path in paths:
                    if Path(path).exists():
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
        except Exception:
            pass  # Use default path
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image based on OCR mode"""
        if self.config.ocr_mode == OCRMode.NONE:
            return image
        
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        if self.config.ocr_mode == OCRMode.LIGHT:
            # Light preprocessing: just threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed = thresh
        
        elif self.config.ocr_mode == OCRMode.STANDARD:
            # Standard preprocessing
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed = cv2.medianBlur(thresh, 3)
        
        elif self.config.ocr_mode == OCRMode.AGGRESSIVE:
            # Aggressive preprocessing
            # 1. Apply adaptive threshold
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)
            # 2. Noise removal
            denoised = cv2.medianBlur(thresh, 3)
            # 3. Dilation to connect text
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.dilate(denoised, kernel, iterations=1)
        else:
            processed = gray
        
        # Convert back to PIL
        return Image.fromarray(processed)
    
    def _ocr_text(self, image: Image.Image, region_name: str = "") -> OCRResult:
        """
        Extract text from image using OCR
        
        Args:
            image: PIL Image object
            region_name: Name of the region for tracking
        
        Returns:
            OCRResult object with extracted text
        """
        try:
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Configure OCR
            custom_config = '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz '
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            text = text.strip()
            
            # Extract queue number if this is the queue region
            queue_number = None
            if region_name == "queue":
                queue_number = self._extract_queue_number(text)
            
            return OCRResult(
                text=text,
                timestamp=datetime.datetime.now(),
                region_name=region_name,
                queue_number=queue_number,
                is_valid=self._is_valid_queue_number(queue_number) if queue_number else False
            )
        
        except Exception as e:
            self._handle_error(f"OCR Error for {region_name}: {e}")
            return OCRResult(text="", region_name=region_name)
    
    def _extract_queue_number(self, text: str) -> Optional[str]:
        """Extract queue number from OCR text"""
        if not text:
            return None
        
        for pattern in self.config.queue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # If no pattern matches, return the entire cleaned text
        cleaned = re.sub(r'[^A-Za-z0-9\-]', '', text)
        return cleaned if cleaned else None
    
    def _is_valid_queue_number(self, queue_number: Optional[str]) -> bool:
        """Check if the queue number is valid"""
        if not queue_number:
            return False
        
        queue_number = queue_number.strip()
        
        # Check against excluded values
        for excluded in self.config.excluded_values:
            if queue_number.lower() == excluded.lower():
                return False
        
        # Additional validation: check if it's a reasonable number
        if queue_number.isdigit():
            # If it's just a single digit, it's probably invalid
            if len(queue_number) == 1:
                return False
        
        return True
    
    def _get_text_hash(self, text: str) -> str:
        """Compute hash of text for change detection"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _capture_region(self, region: ScreenRegion) -> Image.Image:
        """Capture a specific screen region"""
        return pyautogui.screenshot(region=region.to_tuple())
    
    def _save_screenshot(self, image: Image.Image, prefix: str, suffix: str = "") -> str:
        """Save screenshot with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{prefix}_{timestamp}{suffix}.png"
        filepath = self.output_dir / filename
        image.save(filepath)
        return str(filepath)
    
    def _save_region_screenshot(self, image: Image.Image, region_name: str, 
                                queue_number: Optional[str] = None) -> str:
        """Save screenshot to region-specific directory"""
        if queue_number:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{region_name}_{timestamp}_{queue_number}.png"
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{region_name}_{timestamp}.png"
        
        filepath = self.dirs.get(region_name, self.output_dir) / filename
        image.save(filepath)
        return str(filepath)
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log events to file"""
        if not self.config.log_enabled:
            return
        
        log_path = self.output_dir / self.config.log_file
        timestamp = datetime.datetime.now().isoformat()
        
        with open(log_path, 'a') as f:
            f.write(f"[{timestamp}] {event_type}\n")
            for key, value in data.items():
                f.write(f"  {key}: {value}\n")
            f.write("-" * 50 + "\n")
    
    def _handle_error(self, error_message: str):
        """Handle errors"""
        if self.config.on_error:
            self.config.on_error(error_message)
        else:
            print(f"Error: {error_message}")
    
    def _handle_status_change(self, new_status: MonitorStatus):
        """Handle status changes"""
        self.status = new_status
        if self.config.on_status_change:
            self.config.on_status_change(new_status)
    
    def _check_triggers(self, title_text: str, footer_text: str) -> bool:
        """Check if trigger conditions are met"""
        title_match = any(trigger in title_text for trigger in self.config.title_triggers)
        footer_match = any(trigger in footer_text for trigger in self.config.footer_triggers)
        return title_match or footer_match
    
    def _check_homepage_trigger(self, home_text: str) -> bool:
        """Check if homepagetrigger conditions are met"""
        home_match = any(trigger in home_text for trigger in self.config.home_triggers)
        return home_match

    def _process_ocr_results(self, results: Dict[str, OCRResult]) -> Optional[str]:
        """
        Process OCR results and check for queue numbers
        
        Returns:
            Queue number if found and valid, None otherwise
        """
        # Use default empty OCRResult if region not found
        title_result = results.get('title', OCRResult(text="", region_name="title"))
        footer_result = results.get('footer', OCRResult(text="", region_name="footer"))
        queue_result = results.get('queue', OCRResult(text="", region_name="queue"))
        home_result = results.get('home', OCRResult(text="", region_name="home"))
        
        # Check for changes
        for region_name, result in results.items():
            text_hash = self._get_text_hash(result.text)
            old_hash = self.last_hashes.get(region_name, "")
            
            if text_hash != old_hash and self.config.save_on_change:
                self.change_count += 1
                if self.config.on_change_detected:
                    self.config.on_change_detected(region_name, result.text)
                
                # Get the region object
                region_obj = getattr(self.config, f"{region_name}_region", None)
                if region_obj:
                    # Save change screenshot
                    self._save_region_screenshot(
                        self._capture_region(region_obj),
                        f"change_{region_name}"
                    )
            
            self.last_hashes[region_name] = text_hash
            self.last_ocr_results[region_name] = result
        
        # Check if home page entered (without needing to queue)
        if self._check_homepage_trigger(home_result.text):
            with self._result_lock:
                self.found_queue_numbers.append(HOME_ASSIGN_QUEUE)

            # Save screenshots
            if self.config.save_on_change:
                # Save queue region
                # if self.config.queue_region:
                #     self._save_region_screenshot(
                #         self._capture_region(self.config.queue_region),
                #         "queue",
                #         queue_result.queue_number
                #     )
                
                # Save full screenshot
                full_screenshot = pyautogui.screenshot()
                self._save_region_screenshot(
                    full_screenshot,
                    "full",
                    HOME_ASSIGN_QUEUE
                )
            
            # Log the event
            self._log_event("HOME_WITHOUT_QUEUE", {
                'queue_number': HOME_ASSIGN_QUEUE,
                'title_text': title_result.text,
                'footer_text': footer_result.text,
                'queue_text': queue_result.text
            })
            
            # Call callback
            if self.config.on_queue_found:
                self.config.on_queue_found(HOME_ASSIGN_QUEUE, results)
            
            return HOME_ASSIGN_QUEUE

        # Check for queue number
        if queue_result.queue_number and queue_result.is_valid:
            # Check trigger conditions
            if self._check_triggers(title_result.text, footer_result.text):
                # Valid queue number found
                with self._result_lock:
                    self.found_queue_numbers.append(queue_result.queue_number)
                
                # Save screenshots
                if self.config.save_on_change:
                    # Save queue region
                    if self.config.queue_region:
                        self._save_region_screenshot(
                            self._capture_region(self.config.queue_region),
                            "queue",
                            queue_result.queue_number
                        )
                    
                    # Save full screenshot
                    full_screenshot = pyautogui.screenshot()
                    self._save_region_screenshot(
                        full_screenshot,
                        "full",
                        queue_result.queue_number
                    )
                
                # Log the event
                self._log_event("QUEUE_FOUND", {
                    'queue_number': queue_result.queue_number,
                    'title_text': title_result.text,
                    'footer_text': footer_result.text,
                    'queue_text': queue_result.text
                })
                
                # Call callback
                if self.config.on_queue_found:
                    self.config.on_queue_found(queue_result.queue_number, results)
                
                return queue_result.queue_number
        
        return None
    
    def monitor(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Main monitoring method
        
        Args:
            timeout: Override timeout from config
        
        Returns:
            Found queue number or None
        """
        # Use provided timeout or config timeout
        actual_timeout = timeout if timeout is not None else self.config.timeout
        
        self._handle_status_change(MonitorStatus.RUNNING)
        self.start_time = time.time()
        self._stop_monitoring = False
        self._stop_event.clear()
        
        # Set up signal handler
        def signal_handler(signum, frame):
            self.stop()
        
        original_handler = signal.signal(signal.SIGINT, signal_handler)
        
        try:
            print(f"Screen Monitor started")
            print(f"Check interval: {self.config.check_interval}s")
            print(f"Timeout: {actual_timeout if actual_timeout else 'No timeout'}")
            print("Monitoring for valid queue numbers...")
            print("Press Ctrl+C to stop monitoring")
            print("-" * 50)
            
            found_queue = None
            
            while not self._stop_monitoring:
                # Check timeout
                if actual_timeout is not None:
                    elapsed = time.time() - self.start_time
                    if elapsed >= actual_timeout:
                        self._handle_status_change(MonitorStatus.TIMEOUT)
                        print(f"\n⏰ Timeout reached ({actual_timeout}s)")
                        break
                
                # Check if paused
                if self._pause_monitoring:
                    time.sleep(0.1)
                    continue
                
                # Capture regions
                regions = {
                    'title': (self.config.title_region, "title"),
                    'footer': (self.config.footer_region, "footer"),
                    'queue': (self.config.queue_region, "queue"),
                    'home': (self.config.home_region, "home")
                }
                
                results = {}
                images = {}
                
                for name, (region, region_name) in regions.items():
                    if region:
                        image = self._capture_region(region)
                        images[name] = image
                        results[name] = self._ocr_text(image, region_name)
                    else:
                        # Create empty result for missing region
                        results[name] = OCRResult(text="", region_name=region_name)
                
                # Process results
                found_queue = self._process_ocr_results(results)
                if found_queue:
                    self._handle_status_change(MonitorStatus.COMPLETED)
                    print(f"\n✅ Valid queue number found: {found_queue}")
                    break
                
                # Wait before next check
                time.sleep(self.config.check_interval)
        
        except Exception as e:
            self._handle_status_change(MonitorStatus.ERROR)
            self._handle_error(f"Monitoring error: {e}")
            raise
        
        finally:
            signal.signal(signal.SIGINT, original_handler)
            if self.status == MonitorStatus.RUNNING:
                self._handle_status_change(MonitorStatus.STOPPED)
        
        return found_queue
    
    def stop(self):
        """Stop monitoring"""
        self._stop_monitoring = True
        self._stop_event.set()
        self._handle_status_change(MonitorStatus.STOPPED)
        print("\n🛑 Monitoring stopped")
    
    def pause(self):
        """Pause monitoring"""
        self._pause_monitoring = True
        print("⏸️ Monitoring paused")
    
    def resume(self):
        """Resume monitoring"""
        self._pause_monitoring = False
        print("▶️ Monitoring resumed")
    
    def get_status(self) -> MonitorStatus:
        """Get current monitor status"""
        return self.status
    
    def get_found_queue_numbers(self) -> List[str]:
        """Get all found queue numbers"""
        with self._result_lock:
            return self.found_queue_numbers.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'status': self.status.value,
            'change_count': self.change_count,
            'found_queue_numbers': self.get_found_queue_numbers(),
            'elapsed_time': elapsed,
            'last_ocr_results': {k: str(v) for k, v in self.last_ocr_results.items()}
        }
    
    def test_regions(self) -> Dict[str, bool]:
        """Test if regions are valid and visible"""
        results = {}
        for name, region in [
            ('title', self.config.title_region),
            ('footer', self.config.footer_region),
            ('queue', self.config.queue_region),
            ('home', self.config.home_region),
        ]:
            if region:
                try:
                    image = self._capture_region(region)
                    results[name] = image.size[0] > 0 and image.size[1] > 0
                except Exception:
                    results[name] = False
            else:
                results[name] = False
        return results
    
    def test_ocr(self) -> Dict[str, OCRResult]:
        """Test OCR on current regions"""
        results = {}
        for name, region in [
            ('title', self.config.title_region),
            ('footer', self.config.footer_region),
            ('queue', self.config.queue_region),
            ('home', self.config.home_region)
        ]:
            if region:
                image = self._capture_region(region)
                results[name] = self._ocr_text(image, name)
            else:
                results[name] = OCRResult(text="", region_name=name)
        return results


class ScreenMonitorBuilder:
    """Builder class for creating ScreenMonitor with fluent API"""
    
    def __init__(self):
        self.config = MonitorConfig()
    
    def with_title_region(self, x1: int, y1: int, x2: int, y2: int) -> 'ScreenMonitorBuilder':
        self.config.title_region = ScreenRegion(x1, y1, x2, y2)
        return self
    
    def with_footer_region(self, x1: int, y1: int, x2: int, y2: int) -> 'ScreenMonitorBuilder':
        self.config.footer_region = ScreenRegion(x1, y1, x2, y2)
        return self
    
    def with_queue_region(self, x1: int, y1: int, x2: int, y2: int) -> 'ScreenMonitorBuilder':
        self.config.queue_region = ScreenRegion(x1, y1, x2, y2)
        return self

    def with_home_region(self, x1: int, y1: int, x2: int, y2: int) -> 'ScreenMonitorBuilder':
        self.config.home_region = ScreenRegion(x1, y1, x2, y2)
        return self
    
    def with_check_interval(self, interval: float) -> 'ScreenMonitorBuilder':
        self.config.check_interval = interval
        return self
    
    def with_timeout(self, timeout: float) -> 'ScreenMonitorBuilder':
        self.config.timeout = timeout
        return self
    
    def with_output_dir(self, output_dir: str) -> 'ScreenMonitorBuilder':
        self.config.output_dir = output_dir
        return self
    
    def with_excluded_values(self, *values: str) -> 'ScreenMonitorBuilder':
        self.config.excluded_values = list(values)
        return self
    
    def with_ocr_mode(self, mode: OCRMode) -> 'ScreenMonitorBuilder':
        self.config.ocr_mode = mode
        return self
    
    def with_title_triggers(self, *triggers: str) -> 'ScreenMonitorBuilder':
        self.config.title_triggers = list(triggers)
        return self
    
    def with_footer_triggers(self, *triggers: str) -> 'ScreenMonitorBuilder':
        self.config.footer_triggers = list(triggers)
        return self
    
    def with_callback(self, callback_type: str, callback: Callable) -> 'ScreenMonitorBuilder':
        if callback_type == 'on_queue_found':
            self.config.on_queue_found = callback
        elif callback_type == 'on_change_detected':
            self.config.on_change_detected = callback
        elif callback_type == 'on_error':
            self.config.on_error = callback
        elif callback_type == 'on_status_change':
            self.config.on_status_change = callback
        return self
    
    def with_save_on_change(self, enabled: bool = True) -> 'ScreenMonitorBuilder':
        self.config.save_on_change = enabled
        return self
    
    def with_logging(self, enabled: bool = True, log_file: str = "monitor.log") -> 'ScreenMonitorBuilder':
        self.config.log_enabled = enabled
        self.config.log_file = log_file
        return self
    
    def with_queue_patterns(self, *patterns: str) -> 'ScreenMonitorBuilder':
        self.config.queue_patterns = list(patterns)
        return self
    
    def build(self) -> ScreenMonitor:
        """Build the ScreenMonitor instance"""
        return ScreenMonitor(self.config)


# Convenience functions
def create_monitor_from_regions(title_region: Optional[Tuple[int, int, int, int]] = None,
                                footer_region: Optional[Tuple[int, int, int, int]] = None,
                                queue_region: Optional[Tuple[int, int, int, int]] = None,
                                home_region: Optional[Tuple[int, int, int, int]] = None,
                                **kwargs) -> ScreenMonitor:
    """
    Create a ScreenMonitor from coordinate tuples
    
    Args:
        title_region: (x1, y1, x2, y2) tuple for title region
        footer_region: (x1, y1, x2, y2) tuple for footer region
        queue_region: (x1, y1, x2, y2) tuple for queue region
        home_region: (x1, y1, x2, y2) tuple for home region
        **kwargs: Additional configuration options
    
    Returns:
        Configured ScreenMonitor instance
    """
    builder = ScreenMonitorBuilder()
    
    if title_region:
        builder.with_title_region(*title_region)
    if footer_region:
        builder.with_footer_region(*footer_region)
    if queue_region:
        builder.with_queue_region(*queue_region)
    if home_region:
        builder.with_queue_region(*home_region)
    
    # Apply additional kwargs
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)
    
    return builder.build()


def get_mouse_position() -> Tuple[int, int]:
    """Get current mouse position"""
    return pyautogui.position()


def get_screen_size() -> Tuple[int, int]:
    """Get screen size"""
    return pyautogui.size()


def get_region_interactive(name: str) -> ScreenRegion:
    """Get region coordinates interactively using mouse"""
    print(f"\n--- Setting up {name} ---")
    print("Move mouse to top-left corner and press Enter")
    input("Press Enter when mouse is in position...")
    x1, y1 = pyautogui.position()
    print(f"Top-left: ({x1}, {y1})")
    
    print("Move mouse to bottom-right corner and press Enter")
    input("Press Enter when mouse is in position...")
    x2, y2 = pyautogui.position()
    print(f"Bottom-right: ({x2}, {y2})")
    
    return ScreenRegion(x1, y1, x2, y2)


def setup_regions_interactive() -> Tuple[ScreenRegion, ScreenRegion, ScreenRegion]:
    """Setup all regions interactively"""
    title_region = get_region_interactive("Title Box")
    footer_region = get_region_interactive("Footer Button")
    queue_region = get_region_interactive("Queue Number")
    home_region = get_region_interactive("Home Trigger")

    return title_region, footer_region, queue_region


# Example usage and CLI
def main():
    """Example usage of the library"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Screen Monitor with OCR")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Use interactive region setup")
    parser.add_argument("--timeout", "-t", type=float, 
                       help="Timeout in seconds")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Check interval in seconds")
    parser.add_argument("--output", "-o", default=".screenshots",
                       help="Output directory")
    parser.add_argument("--title", nargs=4, type=int, metavar=('x1', 'y1', 'x2', 'y2'),
                       help="Title region coordinates")
    parser.add_argument("--footer", nargs=4, type=int, metavar=('x1', 'y1', 'x2', 'y2'),
                       help="Footer region coordinates")
    parser.add_argument("--queue", nargs=4, type=int, metavar=('x1', 'y1', 'x2', 'y2'),
                       help="Queue region coordinates")
    parser.add_argument("--exclude", nargs="+", default=["1"],
                       help="Values to exclude (default: 1)")
    parser.add_argument("--test", action="store_true",
                       help="Test regions and OCR before monitoring")
    
    args = parser.parse_args()
    
    # Setup regions
    if args.interactive:
        title_region, footer_region, queue_region, home_region = setup_regions_interactive()
    elif args.title and args.footer and args.queue:
        title_region = ScreenRegion(*args.title)
        footer_region = ScreenRegion(*args.footer)
        queue_region = ScreenRegion(*args.queue)
        home_region = ScreenRegion(*args.home)
    else:
        print("Please provide regions or use --interactive")
        return
    
    # Create monitor
    monitor = ScreenMonitorBuilder() \
        .with_title_region(title_region.x1, title_region.y1, title_region.x2, title_region.y2) \
        .with_footer_region(footer_region.x1, footer_region.y1, footer_region.x2, footer_region.y2) \
        .with_queue_region(queue_region.x1, queue_region.y1, queue_region.x2, queue_region.y2) \
        .with_home_region(home_region.x1, home_region.y1, home_region.x2, home_region.y2) \
        .with_check_interval(args.interval) \
        .with_timeout(args.timeout) \
        .with_output_dir(args.output) \
        .with_excluded_values(*args.exclude) \
        .with_ocr_mode(OCRMode.STANDARD) \
        .with_save_on_change(True) \
        .with_logging(True) \
        .build()
    
    # Test if requested
    if args.test:
        print("Testing regions...")
        region_test = monitor.test_regions()
        for name, valid in region_test.items():
            print(f"  {name}: {'✓' if valid else '✗'}")
        
        print("\nTesting OCR...")
        ocr_results = monitor.test_ocr()
        for name, result in ocr_results.items():
            print(f"  {name}: '{result.text}'")
            if result.queue_number:
                print(f"    Queue: {result.queue_number} (valid: {result.is_valid})")
    
    # Start monitoring
    print("\n" + "="*50)
    queue_number = monitor.monitor()
    
    if queue_number:
        print(f"\n✅ Queue number found: {queue_number}")
        print(f"Total changes detected: {monitor.change_count}")
        return queue_number
    else:
        print("\n❌ No valid queue number found")
        print(f"Status: {monitor.get_status().value}")
        return None


if __name__ == "__main__":
    main()