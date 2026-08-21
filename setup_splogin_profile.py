#!/usr/bin/env python3
"""
SPlogin Profile Setup
Sets up or modifies a profile
"""

import os
import subprocess
import pyautogui

from utils.config_manager import ConfigManager

DEFAULT_CONFIG = "splogin_config.yaml"

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

def get_cliclick_path(cliclick_path="") -> str:
    """
    Check if cliclick exists using full path
    Tries to get path if not exists and returns path
    """
    if os.path.exists(cliclick_path) and os.access(cliclick_path, os.X_OK):
        return cliclick_path
    else:
        try:
            result = subprocess.run(["which", "cliclick"], capture_output=True, text=True)
            if result.stdout:
                cliclick_path = result.stdout.strip()
                print(f"Found at: {cliclick_path}")
                return cliclick_path
        except:
            print("Error locating cliclick path")
    return ""

def get_screen_regions_interactive(key_name):
    """Get screen regions interactively from user"""
    print("Screen Region Setup")
    print("You can use mouse to get coordinates or enter them manually")
    print("To use mouse, move mouse to desired position and press Enter")

def get_coords(name: str) -> tuple:
    print(f"{Colors.WHITE}{name}: {Colors.NC}Set coordinates:")
    try:
        input("  Move mouse to location, press ENTER to grab position...")
        x1, y1 = pyautogui.position()
        pos = (x1, y1)
        #print(f"=> Coords: {pos}")
        return pos
    except Exception as e:
            print(f"Error getting region: {e}")
            return None
    
def get_region(name: str) -> tuple:
    print(f"{Colors.WHITE}{name}: {Colors.NC}Setup region:")
    try:
        input("  Move mouse to TOP-LEFT corner, press ENTER to grab position...")
        x1, y1 = pyautogui.position()        
        input("  Move mouse to BOTTOM-RIGHT corner, press ENTER to grab position...")
        x2, y2 = pyautogui.position()
        region = (x1, y1, x2, y2)
        #print(f"=> Region {str(region)}")
        return region
    except Exception as e:
        print(f"Error getting region: {e}")
        return None

def main():
    print("=" * 60)
    print("SPLogin Profile Setup")
    print("=" * 60)
    config = ConfigManager(DEFAULT_CONFIG)
    profiles = config.get_profiles()
    template_params = config.get_profile('template')
    print(f"Existing Profiles: {profiles}")
    print(f"Template profile parameters:")
    for key in template_params.keys():
        print(f". {key}")
    print("=" * 60)

    name = input("Enter name of profile to create/modify : ")
    existing_profile = (name in profiles)

    if existing_profile:
        print(f"Modifying profile `{name}`")
        profile_data = config.get_profile(name)
        print(f"Checking cliclick_path... ", end="")
        cliclick_path = get_cliclick_path(profile_data['cliclick_path'])
    else:
        print(f"Configuring new profile `{name}`")
        print(f"Checking cliclick_path... ", end="")
        cliclick_path = get_cliclick_path("")
        profile_data = {
            'name': name,
            'cliclick_path': cliclick_path,
        }

    # Loop through template parameters
    for key in template_params.keys():
        if key in ['name', 'cliclick_path']:
            continue
        print("=" * 60)
        if existing_profile:
            try:
                old_value = config.get_profile_parameter(name, key)
            except Exception as e:
                print(f"{Colors.WHITE}{key}{Colors.NC} not set in profile {Colors.GREEN}{name}{Colors.NC}")
            else:
                do_modify = True if (input(f"Modify existing {Colors.WHITE}{key}:{Colors.GREEN} {old_value}{Colors.NC} [y/N] ? ")).lower() == "y" else False
                if not do_modify:
                    profile_data[key] = old_value
                    continue
        if key.endswith("_coords"):
            new_value = ",".join(map(str,get_coords(key)))     # x1,y1
        if key.endswith("_box"):            
            new_value = str(get_region(key))     # (x1, y1, x2, y2)
        profile_data[key] = new_value
        print(f"Set {key} to {new_value}")

    print("=" * 60)
    if existing_profile:
        print(f"Please confirm the changes to profile {Colors.WHITE}{name}{Colors.NC}:")
        for key, value in profile_data.items():
            try:
                old_value = config.get_profile_parameter(name, key)
            except Exception:
                old_value = None
            if not old_value:
                print(f"⏹ {key:<15}: {Colors.WHITE}{value:<30}{Colors.NC} ")
            elif old_value == value and value != 'name':
                print(f"⏹ {key:<15}: {Colors.WHITE}{value:<30}{Colors.NC} (unchanged)")
            else:
                print(f"⏹ {key:<15}: {Colors.WHITE}{value:<27}{Colors.NC} <= [OLD]: {old_value}")
    else:
        print(f"Please confirm the parameters for new profile {Colors.WHITE}{name}{Colors.NC}:")
        for key, value in profile_data.items():
            print(f"⏹ {key:<15}: {Colors.WHITE}{value:<30}{Colors.NC}")

    confirm_write = input(f"Write data to {DEFAULT_CONFIG} [y/N] ? ")
    if confirm_write.lower() == "y" or confirm_write.lower() == "yes":
        if existing_profile:
            config.update_profile(name, profile_data)
            print(f"Profile {Colors.WHITE}{name}{Colors.NC} updated.")
        else:
            config.create_profile(name, profile_data)
        
if __name__ == "__main__":
    main()