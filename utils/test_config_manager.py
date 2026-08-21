# Example: Reading the provided config.yaml file
from config_manager import ConfigManager

# Load the configuration
config = ConfigManager('test_config.yaml')

# Get all profiles
profiles = config.get_profiles()
print("Profiles:", profiles)
# Output: ['default', 'gmp24', 'janmbp']

# Get a specific profile
default_profile = config.get_profile('default')
print("Default profile:", default_profile)
# Output: {'name': 'default', 'cliclick_path': '/opt/homebrew/bin/cliclick', 'start_coords': '179,734', 'close_coords': '166,594', 'queue_box': '(72,473,293,511)', 'alive_box': '(10,150,336,702)'}

# Get all sequences
sequences = config.get_sequences()
print("Sequences:", sequences)
# Output: ['login', 'sessions_g']

# Get a specific sequence
login_sequence = config.get_sequence('login')
print("Login sequence:", login_sequence)
# Output: {'start_time': '07:00:00', 'cliclick_cmd': 'dc:start_coords dc:close_coords dc:close_coords'}


# Example: Adding a new profile

# Add a new profile
new_profile = {
    'name': 'new_workstation',
    'cliclick_path': '/usr/local/bin/cliclick',
    'start_coords': '100,200',
    'close_coords': '150,250',
    'queue_box': '(50,50,300,400)',
    'alive_box': '(10,10,100,100)'
}
config.create_profile('workstation1', new_profile)

# Get all profiles
profiles = config.get_profiles()
print("Profiles after create:", profiles)
# Output: ['default', 'gmp24', 'janmbp', 'workstation1']

# Delete a profile
config.delete_profile('workstation1')

# Get all profiles
profiles = config.get_profiles()
print("Profiles after delete workstation1:", profiles)
# Output: ['default', 'gmp24', 'janmbp']

# Update an existing profile
updated_profile = {
    'name': 'updated_gmp24',
    'cliclick_path': '/opt/homebrew/bin/cliclick',
    'start_coords': '200,300',
    'close_coords': '180,280',
    'queue_box': '(72,473,293,511)',
    'alive_box': '(10,10,100,100)'
}
config.update_profile('gmp24', updated_profile)

# Update a specific parameter
config.update_profile_parameter('default', 'start_coords', '100,500')


# Example: Managing sequences
# config = ConfigManager('config.yaml')

# Create a new sequence
new_sequence = {
    'start_time': '08:00:00',
    'cliclick_cmd': 'dc:start_coords dc:queue_box',
    'repeat': 1
}
config.create_sequence('new_task', new_sequence)

# Update a sequence
updated_sequence = {
    'start_time': '09:00:00',
    'cliclick_cmd': 'dc:start_coords dc:close_coords',
    'repeat': 2
}
config.update_sequence('login', updated_sequence)

# Get parsed coordinates
start_x, start_y = config.get_parsed_coords('default', 'start_coords')
print(f"Start coords: ({start_x}, {start_y})")

# Get parsed box
x1, y1, x2, y2 = config.get_parsed_box('default', 'queue_box')
print(f"Queue box: ({x1}, {y1}) to ({x2}, {y2})")

## Example: Substituting variables for sequence

# Example: Substituting variables in command strings

# Substitute variables in a sequence command
print(f"Substituting 'default' profile varibles for sequence 'login'")
cmd = config.substitute_variables_for_sequence('login', 'default')
print("Substituted command:", cmd)
# Output: "179,734 166,594 166,594"

# Manually substitute variables in any string
cmd_string = "dc:start_coords dc:close_coords dc:queue_box"
substituted = config.substitute_variables(cmd_string, 'default')
print("Substituted string:", substituted)