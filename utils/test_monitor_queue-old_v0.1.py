#!/usr/bin/env python3
"""
Screen Monitor with OCR for macOS
Monitors specified screen regions for text changes and extracts queue numbers
"""

import os
import sys
import time
import datetime
import hashlib
from typing import Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path

import pyautogui
import cv2
import numpy as np
from PIL import Image
import pytesseract
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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

class ScreenMonitor:
    """Monitor screen regions for text changes and perform OCR"""
    
    def __init__(self, 
                 title_region: ScreenRegion,
                 footer_region: ScreenRegion,
                 queue_region: ScreenRegion,
                 output_dir: str = "screenshots",
                 check_interval: float = 1.0,
                 save_on_change: bool = True):
        """
        Initialize the screen monitor
        
        Args:
            title_region: Region for the title box
            footer_region: Region for the footer button
            queue_region: Region for the queue number
            output_dir: Directory to save screenshots
            check_interval: Time between checks in seconds
            save_on_change: Whether to save screenshots when changes detected
        """
        self.title_region = title_region
        self.footer_region = footer_region
        self.queue_region = queue_region
        self.output_dir = Path(output_dir)
        self.check_interval = check_interval
        self.save_on_change = save_on_change
        
        # State tracking
        self.last_title_text = ""
        self.last_footer_text = ""
        self.last_queue_text = ""
        self.last_title_hash = ""
        self.last_footer_hash = ""
        self.change_count = 0
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different types of screenshots
        self.title_dir = self.output_dir / "title_changes"
        self.footer_dir = self.output_dir / "footer_changes"
        self.queue_dir = self.output_dir / "queue_captures"
        self.full_dir = self.output_dir / "full_captures"
        
        for dir_path in [self.title_dir, self.footer_dir, self.queue_dir, self.full_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Configure Tesseract (adjust path if needed)
        try:
            # For Homebrew installation of tesseract
            if sys.platform == "darwin":
                pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        except:
            pass  # Use default path
        
    def capture_region(self, region: ScreenRegion) -> Image.Image:
        """Capture a specific screen region"""
        screenshot = pyautogui.screenshot(region=(region.x1, region.y1, 
                                                   region.width, region.height))
        return screenshot
    
    def ocr_text(self, image: Image.Image, preprocess: bool = True) -> str:
        """
        Extract text from image using OCR
        
        Args:
            image: PIL Image object
            preprocess: Whether to preprocess the image
        
        Returns:
            Extracted text string
        """
        if preprocess:
            # Convert PIL to OpenCV format
            img_array = np.array(image)
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply preprocessing for better OCR results
            # 1. Apply threshold to get binary image
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 2. Noise removal
            denoised = cv2.medianBlur(thresh, 3)
            
            # 3. Convert back to PIL
            processed_image = Image.fromarray(denoised)
        else:
            processed_image = image
        
        # OCR configuration for better text extraction
        #custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz - '
        custom_config = '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

        try:
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def compute_image_hash(self, image: Image.Image) -> str:
        """Compute a hash of the image for change detection"""
        img_array = np.array(image)
        return hashlib.md5(img_array.tobytes()).hexdigest()
    
    def get_text_hash(self, text: str) -> str:
        """Compute hash of text for change detection"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def save_screenshot(self, image: Image.Image, prefix: str, suffix: str = "") -> str:
        """Save screenshot with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{prefix}_{timestamp}{suffix}.png"
        filepath = self.output_dir / filename
        image.save(filepath)
        return str(filepath)
    
    def extract_queue_number(self, text: str) -> Optional[str]:
        """Extract queue number from OCR text"""
        import re
        
        # Common patterns for queue numbers
        patterns = [
            r'(?:queue|position|number|#)\s*[:.]?\s*([A-Z0-9\-]+)',
            r'([A-Z]{2,3}-\d+)',  # Pattern like AB-123
            r'(\d+-\d+)',  # Pattern like 123-456
            r'#(\d+)',  # Pattern like #123
            r'(\d{2,})'  # Just digits, at least 4
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # If no pattern matches, return the entire cleaned text
        cleaned = re.sub(r'[^A-Za-z0-9\-]', '', text)
        return cleaned if cleaned else None
    
    def monitor(self, stop_event=None):
        """Main monitoring loop"""
        print(f"Starting screen monitor...")
        print(f"Title region: ({self.title_region.x1}, {self.title_region.y1}) to ({self.title_region.x2}, {self.title_region.y2})")
        print(f"Footer region: ({self.footer_region.x1}, {self.footer_region.y1}) to ({self.footer_region.x2}, {self.footer_region.y2})")
        print(f"Queue region: ({self.queue_region.x1}, {self.queue_region.y1}) to ({self.queue_region.x2}, {self.queue_region.y2})")
        print(f"Check interval: {self.check_interval}s")
        print(f"Screenshots saved to: {self.output_dir}")
        print("Monitoring... Press Ctrl+C to stop")
        print("-" * 50)
        
        try:
            while stop_event is None or not stop_event.is_set():
                # Capture all regions
                title_image = self.capture_region(self.title_region)
                footer_image = self.capture_region(self.footer_region)
                queue_image = self.capture_region(self.queue_region)
                full_screenshot = pyautogui.screenshot()
                
                # Extract text using OCR
                title_text = self.ocr_text(title_image)
                footer_text = self.ocr_text(footer_image)
                queue_text = self.ocr_text(queue_image)
                
                # Compute hashes for change detection
                title_hash = self.get_text_hash(title_text)
                footer_hash = self.get_text_hash(footer_text)
                
                # Check for changes
                title_changed = title_hash != self.last_title_hash
                footer_changed = footer_hash != self.last_footer_hash
                
                # Save screenshots on change if enabled
                if self.save_on_change:
                    if title_changed:
                        self.save_screenshot(title_image, "title_change")
                        self.change_count += 1
                        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Title changed: '{self.last_title_text}' -> '{title_text}'")
                    
                    if footer_changed:
                        self.save_screenshot(footer_image, "footer_change")
                        self.change_count += 1
                        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Footer changed: '{self.last_footer_text}' -> '{footer_text}'")
                
                # Check for specific conditions
                title_matches = "VirtualWaitingRoom" in title_text
                footer_matches = "Exit" in footer_text
                
                # Save queue information when conditions are met
                if (title_matches or footer_matches) and queue_text:
                    # Save queue screenshot
                    queue_number = self.extract_queue_number(queue_text)
                    
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    queue_screenshot_path = self.queue_dir / f"queue_{timestamp}_{queue_number}.png"
                    queue_image.save(queue_screenshot_path)
                    
                    # Save full screenshot for context
                    full_screenshot_path = self.full_dir / f"full_{timestamp}_{queue_number}.png"
                    full_screenshot.save(full_screenshot_path)
                    
                    # Save queue information to log file
                    log_file = self.output_dir / "queue_log.txt"
                    with open(log_file, 'a') as f:
                        f.write(f"[{datetime.datetime.now().isoformat()}] Queue Number: {queue_number}\n")
                        f.write(f"  Title Text: '{title_text}'\n")
                        f.write(f"  Footer Text: '{footer_text}'\n")
                        f.write(f"  Full Text: '{queue_text}'\n")
                        f.write(f"  Screenshots: {queue_screenshot_path.name}, {full_screenshot_path.name}\n")
                        f.write("-" * 50 + "\n")
                    
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Queue number captured: {queue_number}")
                
                # Update state
                self.last_title_text = title_text
                self.last_footer_text = footer_text
                self.last_queue_text = queue_text
                self.last_title_hash = title_hash
                self.last_footer_hash = footer_hash
                
                # Wait before next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print(f"\nMonitoring stopped. Total changes detected: {self.change_count}")
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            raise

def get_screen_regions_interactive():
    """Get screen regions interactively from user"""
    print("Screen Region Setup")
    print("You can use mouse to get coordinates or enter them manually")
    print("To use mouse, move mouse to desired position and press Enter")
    
    def get_region(name: str) -> ScreenRegion:
        print(f"\n--- {name} ---")
        try:
            print("Move mouse to top-left corner and press Enter")
            input("Press Enter when mouse is in position...")
            x1, y1 = pyautogui.position()
            print(f"Top-left: ({x1}, {y1})")
            
            print("Move mouse to bottom-right corner and press Enter")
            input("Press Enter when mouse is in position...")
            x2, y2 = pyautogui.position()
            print(f"Bottom-right: ({x2}, {y2})")
            
            return ScreenRegion(x1, y1, x2, y2)
        except Exception as e:
            print(f"Error getting region: {e}")
            return None
    
    title_region = get_region("Title Box Region")
    footer_region = get_region("Footer Button Region")
    queue_region = get_region("Queue Number Region")
    
    return title_region, footer_region, queue_region

def main():
    """Main function with example usage"""
    # Check for required dependencies
    try:
        import pyautogui
        import cv2
        import pytesseract
    except ImportError as e:
        print("Missing required dependencies. Please install:")
        print("pip install pyautogui opencv-python pillow pytesseract")
        print("\nAlso install Tesseract OCR:")
        print("brew install tesseract")
        sys.exit(1)
    
    # Example configuration - you should adjust these coordinates
    # Based on your actual screen layout
    
    # Option 1: Interactive setup (recommended)
    print("Do you want to set up regions interactively? (y/n)")
    if input().lower() == 'y':
        title_region, footer_region, queue_region = get_screen_regions_interactive()
        if not all([title_region, footer_region, queue_region]):
            print("Failed to set up regions. Using default values.")
            return
    else:
        # Option 2: Hardcoded coordinates (adjust to your screen)
        # These are example coordinates - adjust them for your specific application
        screen_width, screen_height = pyautogui.size()
        
        # Example regions (you need to adjust these based on your application)
        title_region = ScreenRegion(
            x1=12,
            y1=95,
            x2=323,
            y2=132
        )
        
        footer_region = ScreenRegion(
            x1=30,
            y1=695,
            x2=309,
            y2=728
        )
        
        queue_region = ScreenRegion(
            x1=110,
            y1=455,
            x2=238,
            y2=486
        )
    
    input("Press enter to start screen monitor...")

    # Create monitor instance
    monitor = ScreenMonitor(
        title_region=title_region,
        footer_region=footer_region,
        queue_region=queue_region,
        output_dir="screenshots",
        check_interval=1.0,
        save_on_change=True
    )
    
    # Start monitoring
    monitor.monitor()

if __name__ == "__main__":
    main()