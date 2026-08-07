#!/usr/bin/env python3

import time
import subprocess
import sys
import os
import argparse
from datetime import datetime, timedelta
import re

# Use full path to cliclick (update this with your actual path)
CLICLICK_PATH = "/usr/local/bin/cliclick"  # Common locations
# Alternative paths to try:
# CLICLICK_PATH = "/opt/homebrew/bin/cliclick"  # Apple Silicon Mac
# CLICLICK_PATH = "/usr/bin/cliclick"

def check_cliclick():
    """Check if cliclick exists using full path"""
    return os.path.exists(CLICLICK_PATH) and os.access(CLICLICK_PATH, os.X_OK)


# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

class CountdownTimer:
    def __init__(self, target_time, offset_ms=0, show_progress=True, sound_alert=False):
        self.target_time_str = target_time
        self.offset_ms = offset_ms
        self.show_progress = show_progress
        self.sound_alert = sound_alert
        self.running = True
        self.target_datetime = None
        self.execution_datetime = None
        self.pre_exec_datetime = None
        self.post_exec_datetime = None
        
    def parse_time(self, time_str):
        """Parse time string in hh:mm:ss format"""
        time_str = time_str.strip()
        
        if not re.match(r'^\d{1,2}:\d{1,2}:\d{1,2}$', time_str):
            raise ValueError(f"Invalid time format: {time_str}. Use hh:mm:ss")
        
        hours, minutes, seconds = map(int, time_str.split(':'))
        
        if hours > 23 or minutes > 59 or seconds > 59:
            raise ValueError(f"Invalid time values: {time_str}")
        
        return hours, minutes, seconds
    
    def get_target_datetime(self):
        """Get target datetime object"""
        today = datetime.now().date()
        hours, minutes, seconds = self.parse_time(self.target_time_str)
        target_time = datetime.strptime(f"{hours:02d}:{minutes:02d}:{seconds:02d}", "%H:%M:%S").time()
        target_datetime = datetime.combine(today, target_time)

        # Apply offset (convert ms to seconds)
        offset_seconds = self.offset_ms / 1000.0
        self.execution_datetime = target_datetime - timedelta(seconds=offset_seconds)

        if target_datetime < datetime.now():
            target_datetime += timedelta(days=1)
            self.execution_datetime += timedelta(days=1)
            print(f"{Colors.YELLOW}⏰ Target time is in the past. Waiting for tomorrow...{Colors.NC}")
        
        return target_datetime

    def get_pre_exec_datetime(self):
        return self.pre_exec_datetime

    def get_post_exec_datetime(self):
        return self.post_exec_datetime
    
    def format_offset(self):
        """Format offset for display"""
        if self.offset_ms == 0:
            return "No offset"
        elif self.offset_ms > 0:
            return f"Executing {self.offset_ms}ms BEFORE target time"
        else:
            return f"Executing {abs(self.offset_ms)}ms AFTER target time"
        
    def get_milliseconds(self):
        """Get current milliseconds as 3-digit string"""
        return f"{int(datetime.now().microsecond / 1000):03d}"
    
    def create_progress_bar(self, percentage, width=30):
        """Create a text-based progress bar"""
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {percentage:.1f}%"
    
    def play_sound(self):
        """Play a sound alert"""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["say", "Time is up!"], check=False)
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            elif sys.platform == "linux":
                subprocess.run(["aplay", "/usr/share/sounds/alsa/Noise.wav"], check=False)
            elif sys.platform == "win32":
                import winsound
                winsound.Beep(1000, 500)
        except:
            pass  # Silent fail if sound can't be played
    
    def countdown(self):
        """Run the countdown timer"""
        self.target_datetime = self.get_target_datetime()
        
        print(f"{Colors.GREEN}⏱  Countdown to {self.target_time_str}{Colors.NC}")
        print(f"{Colors.CYAN}⚡ {self.format_offset()}{Colors.NC}")
        if self.offset_ms != 0:
            execution_time = self.execution_datetime.strftime("%H:%M:%S.%f")[:-3]
            print(f"{Colors.YELLOW}🎯 cliclick will execute at: {execution_time}{Colors.NC}")
        print()
        
        try:
            while self.running:
                now = datetime.now()
                diff = self.execution_datetime - now
                
                if diff.total_seconds() <= 0:
                    break
                
                total_seconds = int(diff.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                milliseconds = self.get_milliseconds()
                
                # Calculate progress
                total_initial = 86400  # 24 hours in seconds
                target_diff = self.target_datetime - now
                target_total = int(target_diff.total_seconds())
                if target_total > 0:
                    elapsed = total_initial - target_total
                    percentage = (elapsed / total_initial) * 100
                else:
                    percentage = 100

                # Build display string
                time_str = f"\r⏱  {hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds}"
                
                if self.show_progress:
                    progress_bar = self.create_progress_bar(min(percentage, 100))
                    time_str += f" {progress_bar}"

                # Show offset indicator
                if self.offset_ms != 0:
                    time_str += f" {Colors.CYAN}[offset: {self.offset_ms}ms]{Colors.NC}"

                print(time_str, end="", flush=True)
                #time.sleep(0.02)
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⏹ Countdown cancelled by user{Colors.NC}")
            sys.exit(0)
        
        # Final display
        print(f"\r⏱  00:00:00.000 {self.create_progress_bar(100)}")
        print()
        
        if self.sound_alert:
            self.play_sound()
    
    def execute_command(self, command, args):
        """Execute a command when countdown finishes"""
        print(f"{Colors.GREEN}✓ Time reached! Executing command...{Colors.NC}")
        
        # Check if command exists
        try:
            subprocess.run([command, "--version"], 
                          capture_output=True, 
                          check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"{Colors.RED}Error: '{command}' command not found{Colors.NC}")
            print(f"Please install '{command}' or check your PATH")
            sys.exit(1)
        
        try:
            if not args:
                # Default: show help
                print(f"{Colors.YELLOW}No arguments provided. Showing {command} help:{Colors.NC}")
                subprocess.run([command, "-h"])
            else:
                print(f"{Colors.GREEN}Running: {command} {' '.join(args)}{Colors.NC}")
                subprocess.run([command] + args)
        except Exception as e:
            print(f"{Colors.RED}Error executing command: {e}{Colors.NC}")
            sys.exit(1)

    def execute_cliclick(self, args):
        """Execute cliclick with full path"""
        
        # Show timing information
        now = datetime.now()

        target_time = self.target_datetime
        time_diff = (now - target_time).total_seconds() * 1000
        self.pre_exec_datetime = now
        print(f"{Colors.NC} {self.pre_exec_datetime} | {Colors.GREEN}✓  Execution time reached!")

        if not check_cliclick():
            print(f"Error: cliclick not found at {CLICLICK_PATH}")
            # Try to find it
            try:
                result = subprocess.run(["which", "cliclick"], capture_output=True, text=True)
                if result.stdout:
                    print(f"Found at: {result.stdout.strip()}")
            except:
                pass
            sys.exit(1)
        
        try:
            if not args:
                print(f"{Colors.YELLOW}No arguments provided. Showing cliclick help:{Colors.NC}")
                subprocess.run([CLICLICK_PATH, "-h"])
            else:
                # print(f"{Colors.GREEN}⚡  Running: cliclick {' '.join(args)}{Colors.NC}")
                subprocess.run([CLICLICK_PATH] + args)
                self.post_exec_datetime = datetime.now()
                print(f"{Colors.NC} {self.post_exec_datetime} | {Colors.GREEN}✓  Completed task: cliclick {' '.join(args)}{Colors.NC}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
            description='Countdown timer with cliclick execution and offset support',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
    Examples:
    %(prog)s -t 14:30:00                    # Run at 2:30 PM
    %(prog)s -t 14:30:00 -o 500             # Run 500ms before 2:30 PM
    %(prog)s -t 14:30:00 -o -200            # Run 200ms after 2:30 PM
    %(prog)s -t 14:30:00 "m" "100,100"      # Click at position 100,100 at 2:30 PM
    %(prog)s -t 14:30:00 -o 1000 "m" "100,100"  # Click 1 second before 2:30 PM
            """
        )
    parser.add_argument('-t', '--time', 
                       default="07:00:00",
                       help='Target time in hh:mm:ss format (default: 07:00:00)')
    parser.add_argument('-o', '--offset', 
                       type=int,
                       default=0,
                       help='Offset in milliseconds (positive = before, negative = after). Default: 0')
    parser.add_argument('--no-progress', 
                       action='store_true',
                       help='Hide progress bar')
    parser.add_argument('--sound', 
                       action='store_true',
                       help='Play sound alert when time is reached')
    parser.add_argument('cliclick_args', 
                       nargs='*',
                       default=["dc:.",],
                       help='Arguments to pass to cliclick (default: dc:.)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"   {Colors.CYAN}Countdown Timer{Colors.NC} to {Colors.WHITE}{args.time}{Colors.NC}")
    if args.offset != 0:
        offset_display = f"{args.offset}ms {'BEFORE' if args.offset > 0 else 'AFTER'} target"
        print(f"   {Colors.YELLOW}Offset: {offset_display}{Colors.NC}")
    print("=" * 60)
    
    # Create and run timer
    timer = CountdownTimer(
        target_time=args.time,
        offset_ms=args.offset,
        show_progress=not args.no_progress,
        sound_alert=args.sound
    )
    
    timer.countdown()
    # timer.execute_command("cliclick", args.cliclick_args)
    timer.execute_cliclick(args.cliclick_args)
    
if __name__ == "__main__":
    main()