# Example 1: Basic operations
from config_manager import ConfigManager, create_default_config

# Create a configuration with default profiles
create_default_config('my_config.yaml')

# Load the configuration
config = ConfigManager('my_config.yaml')

# Get all profiles
print("All profiles:", config.get_profiles())

# Get a specific profile
zmb_profile = config.get_profile('zmb20')
print("zmb20 profile:", zmb_profile)

# Create a new profile
print("Create a new profile...")
new_profile = {
    'name': 'test1',
    'cliclick_path': '/opt/homebrew/bin/cliclick',
    'start_coords': '120,720',
    'close_coords': '160,590',
    'queue_box': '(92, 381, 200, 415)',
}
config.create_profile('test1', new_profile)

print("All profiles:", config.get_profiles())

# # Update a profile
# updated_profile = {
    # 'name': 'test1',
    # 'cliclick_path': '/opt/homebrew/bin/cliclick',
    # 'start_coords': '120,720',
    # 'close_coords': '160,590',
    # 'queue_box': '(92, 381, 200, 415)',
# }
# config.update_profile('development', updated_profile)

# Delete a profile
print("Deleting profile test1")
config.delete_profile('test1')

print("All profiles:", config.get_profiles())
