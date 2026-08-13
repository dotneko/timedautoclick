"""
Configuration Manager Library for YAML-based profile management
Author: AI Assistant
Version: 1.0.0
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass


class ConfigManager:
    """
    A configuration manager for YAML files with profile support.
    
    Each profile contains exactly 5 parameters:
    - name: str - Profile name
    - cliclick_path: str - Path to cliclick
    - start_coords: text - x,y coordinates of start button
    - close_coords: text - x,y coordinates of close button
    - queue_box: list - Description of parameter 5
    """
    
    # Define the required parameters for each profile
    REQUIRED_PARAMS = ['name', 'cliclick_path', 'start_coords', 'close_coords', 'queue_box']
    
    # Define expected types for validation
    PARAM_TYPES = {
        'name': str,
        'cliclick_path': str,
        'start_coords': str,
        'close_coords': str,
        'queue_box': str,
    }
    
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
        self._config_data = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load the configuration from the YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as file:
                    self._config_data = yaml.safe_load(file) or {}
                logger.info(f"Configuration loaded from {self.config_path}")
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML file: {e}")
                raise ConfigError(f"Invalid YAML format: {e}")
            except Exception as e:
                logger.error(f"Error reading configuration file: {e}")
                raise ConfigError(f"Failed to read configuration: {e}")
        else:
            logger.info(f"Configuration file not found. Creating new configuration at {self.config_path}")
            self._config_data = {}
    
    def _save_config(self) -> None:
        """Save the current configuration to the YAML file."""
        try:
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as file:
                yaml.dump(self._config_data, file, default_flow_style=False, sort_keys=False)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise ConfigError(f"Failed to save configuration: {e}")
    
    def _validate_profile(self, profile_data: Dict[str, Any]) -> bool:
        """
        Validate that a profile has all 5 required parameters with correct types.
        
        Args:
            profile_data: The profile data to validate
            
        Returns:
            bool: True if valid, raises ConfigError if invalid
        """
        # Check if all required parameters exist
        missing_params = [p for p in self.REQUIRED_PARAMS if p not in profile_data]
        if missing_params:
            raise ConfigError(f"Missing required parameters: {missing_params}")
        
        # Check if there are extra parameters
        extra_params = [p for p in profile_data.keys() if p not in self.REQUIRED_PARAMS]
        if extra_params:
            raise ConfigError(f"Extra parameters not allowed: {extra_params}")
        
        # Validate parameter types
        for param, expected_type in self.PARAM_TYPES.items():
            if not isinstance(profile_data[param], expected_type):
                raise ConfigError(
                    f"Parameter '{param}' should be of type {expected_type.__name__}, "
                    f"got {type(profile_data[param]).__name__}"
                )
        
        return True
    
    def get_profiles(self) -> List[str]:
        """
        Get a list of all profile names.
        
        Returns:
            List[str]: List of profile names
        """
        return list(self._config_data.keys())
    
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
        if profile_name not in self._config_data:
            raise ConfigError(f"Profile '{profile_name}' not found")
        
        return self._config_data[profile_name].copy()
    
    def create_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> None:
        """
        Create a new profile.
        
        Args:
            profile_name: The name of the profile to create
            profile_data: Dictionary containing the 5 parameters
            
        Raises:
            ConfigError: If profile already exists or data is invalid
        """
        if profile_name in self._config_data:
            raise ConfigError(f"Profile '{profile_name}' already exists")
        
        # Validate the profile data
        self._validate_profile(profile_data)
        
        self._config_data[profile_name] = profile_data
        self._save_config()
        logger.info(f"Profile '{profile_name}' created successfully")
    
    def update_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> None:
        """
        Update an existing profile.
        
        Args:
            profile_name: The name of the profile to update
            profile_data: Dictionary containing the updated 5 parameters
            
        Raises:
            ConfigError: If profile doesn't exist or data is invalid
        """
        if profile_name not in self._config_data:
            raise ConfigError(f"Profile '{profile_name}' not found")
        
        # Validate the profile data
        self._validate_profile(profile_data)
        
        self._config_data[profile_name] = profile_data
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
        if profile_name not in self._config_data:
            raise ConfigError(f"Profile '{profile_name}' not found")
        
        del self._config_data[profile_name]
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
            ConfigError: If profile or parameter doesn't exist, or type is invalid
        """
        profile = self.get_profile(profile_name)
        
        if parameter_name not in profile:
            raise ConfigError(f"Parameter '{parameter_name}' not found in profile '{profile_name}'")
        
        # Validate the new value type
        expected_type = self.PARAM_TYPES.get(parameter_name)
        if expected_type and not isinstance(value, expected_type):
            raise ConfigError(
                f"Parameter '{parameter_name}' should be of type {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
        
        profile[parameter_name] = value
        self.update_profile(profile_name, profile)
        logger.info(f"Parameter '{parameter_name}' in profile '{profile_name}' updated successfully")
    
    def get_all_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the entire configuration.
        
        Returns:
            Dict[str, Dict[str, Any]]: The complete configuration data
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
                yaml.dump(self._config_data, file, default_flow_style=False, sort_keys=False)
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
            
            # Validate all imported profiles
            for profile_name, profile_data in imported_data.items():
                try:
                    self._validate_profile(profile_data)
                except ConfigError as e:
                    raise ConfigError(f"Invalid profile '{profile_name}': {e}")
            
            if merge:
                self._config_data.update(imported_data)
            else:
                self._config_data = imported_data
            
            self._save_config()
            logger.info(f"Configuration imported from {import_path}")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise ConfigError(f"Invalid YAML format: {e}")
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            raise ConfigError(f"Failed to import configuration: {e}")


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
    Create a default configuration file with example profiles.
    
    Args:
        config_path: Path where to create the configuration file
    """
    default_config = {
        'zmb20': {
            'name': 'zmb20',
            'cliclick_path': '/usr/local/bin/cliclick',
            'start_coords': '179,734',
            'close_coords': '166,594',
            'queue_box': '(72, 473, 293, 511)',
        },
        'gmp24': {
            'name': 'gmp24',
            'cliclick_path': '/opt/homebrew/bin/cliclick',
            'start_coords': '179,734',
            'close_coords': '166,594',
            'queue_box': '(72, 473, 293, 511)',
        },
        'janmbp': {
            'name': 'janmbp',
            'cliclick_path': '/opt/homebrew/bin/cliclick',
            'start_coords': '179,734',
            'close_coords': '166,594',
            'queue_box': '(92, 381, 200, 415)',
        }
    }
    
    config_manager = ConfigManager(config_path)
    for profile_name, profile_data in default_config.items():
        config_manager.create_profile(profile_name, profile_data)
    
    logger.info(f"Default configuration created at {config_path}")