"""
Configuration Manager Library for YAML-based configuration
Specifically designed for the provided config.yaml format
Author: AI Assistant
Version: 2.0.0
"""

import os
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass


class ConfigManager:
    """
    A configuration manager for YAML files with profiles and sequences support.
    
    The configuration structure is:
    profiles:
      profile_name:
        name: str
        cliclick_path: str
        start_coords: str
        close_coords: str
        queue_box: str (format: x1,y1,x2,y2 or (x1,y1,x2,y2))
        alive_box: str (format: x1,y1,x2,y2 or (x1,y1,x2,y2))
    sequences:
      sequence_name:
        start_time: str (HH:MM:SS or "now")
        cliclick_cmd: str (command string with variable placeholders)
        repeat: int
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the YAML configuration file.
                        If not provided, defaults to 'config.yaml' in current directory.
        """
        if config_path is None:
            config_path = 'config.yaml'
        
        self.config_path = Path(config_path)
        self._config_data = {
            'profiles': {},
            'sequences': {}
        }
        self._load_config()
    
    def _load_config(self) -> None:
        """Load the configuration from the YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as file:
                    loaded_data = yaml.safe_load(file) or {}
                    self._config_data = loaded_data
                    
                    # Ensure required sections exist
                    if 'profiles' not in self._config_data:
                        self._config_data['profiles'] = {}
                    if 'sequences' not in self._config_data:
                        self._config_data['sequences'] = {}
                    
                logger.info(f"Configuration loaded from {self.config_path}")
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML file: {e}")
                raise ConfigError(f"Invalid YAML format: {e}")
            except Exception as e:
                logger.error(f"Error reading configuration file: {e}")
                raise ConfigError(f"Failed to read configuration: {e}")
        else:
            logger.info(f"Configuration file not found. Creating new configuration at {self.config_path}")
            self._config_data = {
                'profiles': {},
                'sequences': {}
            }
            self._save_config()
    
    def _save_config(self) -> None:
        """Save the current configuration to the YAML file."""
        try:
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as file:
                yaml.dump(self._config_data, file, default_flow_style=False, sort_keys=False, allow_unicode=True)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise ConfigError(f"Failed to save configuration: {e}")
    
    def _parse_positive_int(self, value_str) -> int:
        """
        Parse value str to integer, ensure is positive integer

        Args:
            value_str: 
        """
        if not isinstance(value_str, int):
            raise TypeError(f"Expected an int, got {type(value).__name__}")
            
        if value <= 0:
            raise ValueError(f"Expected a positive non-zero int, got {value}")
        return int(value_str)

    def _parse_coords(self, coords_str: str) -> tuple:
        """
        Parse coordinate string to tuple of integers.
        Supports formats: "x,y", "(x,y)", "x, y", "(x, y)"
        
        Args:
            coords_str: Coordinate string to parse
            
        Returns:
            tuple: (x, y) as integers
        """
        # Remove parentheses and whitespace
        cleaned = re.sub(r'[()\s]', '', coords_str)
        parts = cleaned.split(',')
        if len(parts) != 2:
            raise ConfigError(f"Invalid coordinate format: {coords_str}. Expected 'x,y'")
        return (int(parts[0]), int(parts[1]))
    
    def _parse_box(self, box_str: str) -> tuple:
        """
        Parse box string to tuple of integers.
        Supports formats: "(x1,y1,x2,y2)", "x1,y1,x2,y2", "(x1, y1, x2, y2)"
        
        Args:
            box_str: Box string to parse
            
        Returns:
            tuple: (x1, y1, x2, y2) as integers
        """
        # Remove parentheses and whitespace
        cleaned = re.sub(r'[()\s]', '', box_str)
        parts = cleaned.split(',')
        if len(parts) != 4:
            raise ConfigError(f"Invalid box format: {box_str}. Expected 'x1,y1,x2,y2'")
        return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
    
    def get_profiles(self) -> List[str]:
        """
        Get a list of all profile names.
        
        Returns:
            List[str]: List of profile names
        """
        return list(self._config_data.get('profiles', {}).keys())
    
    def get_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Get a specific profile by name.
        
        Args:
            profile_name: The name of the profile to retrieve
            
        Returns:
            Dict[str, Any]: The profile data
            
        Raises:
            ConfigError: If the profile doesn't exist
        """
        if profile_name not in self._config_data.get('profiles', {}):
            raise ConfigError(f"Profile '{profile_name}' not found")
        
        return self._config_data['profiles'][profile_name].copy()
    
    def create_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> None:
        """
        Create a new profile.
        
        Args:
            profile_name: The name of the profile to create
            profile_data: Dictionary containing the profile parameters
            
        Raises:
            ConfigError: If profile already exists or data is invalid
        """
        if 'profiles' not in self._config_data:
            self._config_data['profiles'] = {}
            
        if profile_name in self._config_data['profiles']:
            raise ConfigError(f"Profile '{profile_name}' already exists")
        
        # Validate required fields
        required_fields = ['name', 'cliclick_path', 'start_coords', 'close_coords', 'queue_box', 'alive_box']
        for field in required_fields:
            if field not in profile_data:
                raise ConfigError(f"Missing required field '{field}' in profile")
        
        # Parse coordinates and boxes to ensure they're valid
        try:
            self._parse_coords(profile_data['start_coords'])
            self._parse_coords(profile_data['close_coords'])
            self._parse_box(profile_data['queue_box'])
            self._parse_box(profile_data['alive_box'])
        except (ValueError, ConfigError) as e:
            raise ConfigError(f"Invalid coordinates format: {e}")
        
        self._config_data['profiles'][profile_name] = profile_data
        self._save_config()
        logger.info(f"Profile '{profile_name}' created successfully")
    
    def update_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> None:
        """
        Update an existing profile.
        
        Args:
            profile_name: The name of the profile to update
            profile_data: Dictionary containing the updated profile parameters
            
        Raises:
            ConfigError: If profile doesn't exist or data is invalid
        """
        if 'profiles' not in self._config_data or profile_name not in self._config_data['profiles']:
            raise ConfigError(f"Profile '{profile_name}' not found")
        
        # Validate required fields
        required_fields = ['name', 'cliclick_path', 'start_coords', 'close_coords', 'queue_box', 'alive_box']
        for field in required_fields:
            if field not in profile_data:
                raise ConfigError(f"Missing required field '{field}' in profile")
        
        # Parse coordinates and boxes to ensure they're valid
        try:
            self._parse_coords(profile_data['start_coords'])
            self._parse_coords(profile_data['close_coords'])
            self._parse_box(profile_data['queue_box'])
            self._parse_box(profile_data['alive_box'])
        except (ValueError, ConfigError) as e:
            raise ConfigError(f"Invalid coordinates format: {e}")
        
        self._config_data['profiles'][profile_name] = profile_data
        self._save_config()
        logger.info(f"Profile '{profile_name}' updated successfully")
    
    def delete_profile(self, profile_name: str) -> None:
        """
        Delete a profile.
        
        Args:
            profile_name: The name of the profile to delete
            
        Raises:
            ConfigError: If profile doesn't exist
        """
        if 'profiles' not in self._config_data or profile_name not in self._config_data['profiles']:
            raise ConfigError(f"Profile '{profile_name}' not found")
        
        del self._config_data['profiles'][profile_name]
        self._save_config()
        logger.info(f"Profile '{profile_name}' deleted successfully")
    
    def get_profile_parameter(self, profile_name: str, parameter_name: str) -> Any:
        """
        Get a specific parameter from a profile.
        
        Args:
            profile_name: The name of the profile
            parameter_name: The name of the parameter
            
        Returns:
            Any: The parameter value
            
        Raises:
            ConfigError: If profile or parameter doesn't exist
        """
        profile = self.get_profile(profile_name)
        
        if parameter_name not in profile:
            raise ConfigError(f"Parameter '{parameter_name}' not found in profile '{profile_name}'")
        
        return profile[parameter_name]
    
    def update_profile_parameter(self, profile_name: str, parameter_name: str, value: Any) -> None:
        """
        Update a specific parameter in a profile.
        
        Args:
            profile_name: The name of the profile
            parameter_name: The name of the parameter
            value: The new value for the parameter
            
        Raises:
            ConfigError: If profile or parameter doesn't exist
        """
        profile = self.get_profile(profile_name)
        
        if parameter_name not in profile:
            raise ConfigError(f"Parameter '{parameter_name}' not found in profile '{profile_name}'")
        
        # Validate coordinates if updating coordinate fields
        if parameter_name in ['start_coords', 'close_coords']:
            try:
                self._parse_coords(value)
            except (ValueError, ConfigError) as e:
                raise ConfigError(f"Invalid coordinate format: {e}")
        elif parameter_name in ['queue_box', 'alive_box']:
            try:
                self._parse_box(value)
            except (ValueError, ConfigError) as e:
                raise ConfigError(f"Invalid box format: {e}")

        profile[parameter_name] = value
        self.update_profile(profile_name, profile)
        logger.info(f"Parameter '{parameter_name}' in profile '{profile_name}' updated successfully")
    
    # ===== SEQUENCE METHODS =====
    
    def get_sequences(self) -> List[str]:
        """
        Get a list of all sequence names.
        
        Returns:
            List[str]: List of sequence names
        """
        return list(self._config_data.get('sequences', {}).keys())
    
    def get_sequence(self, sequence_name: str) -> Dict[str, Any]:
        """
        Get a specific sequence by name.
        
        Args:
            sequence_name: The name of the sequence to retrieve
            
        Returns:
            Dict[str, Any]: The sequence data
            
        Raises:
            ConfigError: If the sequence doesn't exist
        """
        if sequence_name not in self._config_data.get('sequences', {}):
            raise ConfigError(f"Sequence '{sequence_name}' not found")
        
        return self._config_data['sequences'][sequence_name].copy()
    
    def create_sequence(self, sequence_name: str, sequence_data: Dict[str, Any]) -> None:
        """
        Create a new sequence.
        
        Args:
            sequence_name: The name of the sequence to create
            sequence_data: Dictionary containing the sequence parameters
            
        Raises:
            ConfigError: If sequence already exists or data is invalid
        """
        if 'sequences' not in self._config_data:
            self._config_data['sequences'] = {}
            
        if sequence_name in self._config_data['sequences']:
            raise ConfigError(f"Sequence '{sequence_name}' already exists")
        
        # Validate required fields
        required_fields = ['start_time', 'cliclick_cmd', 'repeat']
        for field in required_fields:
            if field not in sequence_data:
                raise ConfigError(f"Missing required field '{field}' in sequence")

        # Parse repeat value to ensure it is valid
        try:
            self._parse_positive_int(sequence_data['repeat'])
        except (ValueError, TypeError) as e:
            raise ConfigError(f"Invalid repeat number: {e}")
        
        self._config_data['sequences'][sequence_name] = sequence_data
        self._save_config()
        logger.info(f"Sequence '{sequence_name}' created successfully")
    
    def update_sequence(self, sequence_name: str, sequence_data: Dict[str, Any]) -> None:
        """
        Update an existing sequence.
        
        Args:
            sequence_name: The name of the sequence to update
            sequence_data: Dictionary containing the updated sequence parameters
            
        Raises:
            ConfigError: If sequence doesn't exist or data is invalid
        """
        if 'sequences' not in self._config_data or sequence_name not in self._config_data['sequences']:
            raise ConfigError(f"Sequence '{sequence_name}' not found")
        
        # Validate required fields
        required_fields = ['start_time', 'cliclick_cmd', 'repeat']
        for field in required_fields:
            if field not in sequence_data:
                raise ConfigError(f"Missing required field '{field}' in sequence")
        
        # Parse repeat value to ensure it is valid
        try:
            self._parse_positive_int(sequence_data['repeat'])
        except (ValueError, TypeError) as e:
            raise ConfigError(f"Invalid repeat number: {e}")
        
        self._config_data['sequences'][sequence_name] = sequence_data
        self._save_config()
        logger.info(f"Sequence '{sequence_name}' updated successfully")
    
    def delete_sequence(self, sequence_name: str) -> None:
        """
        Delete a sequence.
        
        Args:
            sequence_name: The name of the sequence to delete
            
        Raises:
            ConfigError: If sequence doesn't exist
        """
        if 'sequences' not in self._config_data or sequence_name not in self._config_data['sequences']:
            raise ConfigError(f"Sequence '{sequence_name}' not found")
        
        del self._config_data['sequences'][sequence_name]
        self._save_config()
        logger.info(f"Sequence '{sequence_name}' deleted successfully")
    
    def get_sequence_parameter(self, sequence_name: str, parameter_name: str) -> Any:
        """
        Get a specific parameter from a sequence.
        
        Args:
            sequence_name: The name of the sequence
            parameter_name: The name of the parameter
            
        Returns:
            Any: The parameter value
            
        Raises:
            ConfigError: If sequence or parameter doesn't exist
        """
        sequence = self.get_sequence(sequence_name)
        
        if parameter_name not in sequence:
            raise ConfigError(f"Parameter '{parameter_name}' not found in sequence '{sequence_name}'")
        
        return sequence[parameter_name]
    
    def update_sequence_parameter(self, sequence_name: str, parameter_name: str, value: Any) -> None:
        """
        Update a specific parameter in a sequence.
        
        Args:
            sequence_name: The name of the sequence
            parameter_name: The name of the parameter
            value: The new value for the parameter
            
        Raises:
            ConfigError: If sequence or parameter doesn't exist
        """
        sequence = self.get_sequence(sequence_name)
        
        if parameter_name not in sequence:
            raise ConfigError(f"Parameter '{parameter_name}' not found in sequence '{sequence_name}'")
        
        sequence[parameter_name] = value
        self.update_sequence(sequence_name, sequence)
        logger.info(f"Parameter '{parameter_name}' in sequence '{sequence_name}' updated successfully")
    
    # ===== UTILITY METHODS =====
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get the entire configuration.
        
        Returns:
            Dict[str, Any]: The complete configuration data
        """
        return self._config_data.copy()
    
    def export_config(self, export_path: str) -> None:
        """
        Export the configuration to a different file.
        
        Args:
            export_path: Path to export the configuration to
        """
        try:
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w') as file:
                yaml.dump(self._config_data, file, default_flow_style=False, sort_keys=False, allow_unicode=True)
            logger.info(f"Configuration exported to {export_path}")
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            raise ConfigError(f"Failed to export configuration: {e}")
    
    def import_config(self, import_path: str, merge: bool = False) -> None:
        """
        Import configuration from another file.
        
        Args:
            import_path: Path to import the configuration from
            merge: If True, merge with existing configuration; if False, replace
            
        Raises:
            ConfigError: If import fails
        """
        try:
            import_path = Path(import_path)
            if not import_path.exists():
                raise ConfigError(f"Import file not found: {import_path}")
            
            with open(import_path, 'r') as file:
                imported_data = yaml.safe_load(file) or {}
            
            if merge:
                # Merge profiles and sequences
                if 'profiles' in imported_data:
                    self._config_data.setdefault('profiles', {}).update(imported_data['profiles'])
                if 'sequences' in imported_data:
                    self._config_data.setdefault('sequences', {}).update(imported_data['sequences'])
            else:
                self._config_data = imported_data
                if 'profiles' not in self._config_data:
                    self._config_data['profiles'] = {}
                if 'sequences' not in self._config_data:
                    self._config_data['sequences'] = {}
            
            self._save_config()
            logger.info(f"Configuration imported from {import_path}")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise ConfigError(f"Invalid YAML format: {e}")
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            raise ConfigError(f"Failed to import configuration: {e}")
    
    def get_parsed_coords(self, profile_name: str, coord_type: str) -> tuple:
        """
        Get parsed coordinates from a profile.
        
        Args:
            profile_name: The profile name
            coord_type: 'start_coords' or 'close_coords'
            
        Returns:
            tuple: (x, y) as integers
        """
        coords_str = self.get_profile_parameter(profile_name, coord_type)
        return self._parse_coords(coords_str)
    
    def get_parsed_box(self, profile_name: str, box_type: str) -> tuple:
        """
        Get parsed box from a profile.
        
        Args:
            profile_name: The profile name
            box_type: 'queue_box' or 'alive_box'
            
        Returns:
            tuple: (x1, y1, x2, y2) as integers
        """
        box_str = self.get_profile_parameter(profile_name, box_type)
        return self._parse_box(box_str)
    
    def substitute_variables(self, cmd_string: str, profile_name: str) -> str:
        """
        Substitute variables in a command string with profile values.
        Variables are in format: "$variable_name"
        
        Args:
            cmd_string: The command string with variables
            profile_name: The profile name to use for substitution
            
        Returns:
            str: The command string with variables substituted
        """
        profile = self.get_profile(profile_name)
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name in profile:
                return str(profile[var_name])
            return match.group(0)  # Keep original if not found
        
        import re
        pattern = r'\$([a-zA-Z_][a-zA-Z0-9_]*)'
        return re.sub(pattern, replace_var, cmd_string)
    
    def substitute_variables_for_sequence(self, sequence_name: str, profile_name: str) -> str:
        """
        Get a sequence command with variables substituted using a profile.
        
        Args:
            sequence_name: The sequence name
            profile_name: The profile name to use for substitution
            
        Returns:
            str: The command string with variables substituted
        """
        cmd = self.get_sequence_parameter(sequence_name, 'cliclick_cmd')
        return self.substitute_variables(cmd, profile_name)


# Convenience functions for quick operations

def load_config(config_path: Optional[str] = None) -> ConfigManager:
    """
    Convenience function to load a configuration.
    
    Args:
        config_path: Path to the configuration file
    
    Returns:
        ConfigManager: The configuration manager instance
    """
    return ConfigManager(config_path)


def create_default_config(config_path: str) -> None:
    """
    Create a default configuration file with example profiles and sequences.
    
    Args:
        config_path: Path where to create the configuration file
    """
    default_config = {
        'profiles': {
            'default': {
                'name': 'default',
                'cliclick_path': '/opt/homebrew/bin/cliclick',
                'start_coords': '179,734',
                'close_coords': '166,594',
                'queue_box': '(72,473,293,511)',
                'alive_box': '(10,150,336,702)'
            },
            'profile1': {
                'name': 'janmbp',
                'cliclick_path': '/opt/homebrew/bin/cliclick',
                'start_coords': '179,734',
                'close_coords': '166,594',
                'queue_box': '(92,381,200,415)'
            }
        },
        'sequences': {
            'login': {
                'start_time': '08:00:00',
                'cliclick_cmd': 'dc:start_coords dc:close_coords dc:close_coords'
            },
            'sessions_g': {
                'start_time': 'now',
                'cliclick_cmd': 'dc:111,744 dc:70,228 dc:65,243 dc:173,708'
            }
        }
    }
    
    config_manager = ConfigManager(config_path)
    # Since we already have the full config, we can set it directly
    config_manager._config_data = default_config
    config_manager._save_config()
    
    logger.info(f"Default configuration created at {config_path}")