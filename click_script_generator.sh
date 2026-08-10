#!/bin/bash

# Check if cliclick is installed
if ! command -v cliclick &> /dev/null; then
    echo "Error: cliclick is not installed."
    echo "Install it using: brew install cliclick"
    exit 1
fi

# Configuration
OUTPUT_DIR="${HOME}/cliclick_recordings"
mkdir -p "$OUTPUT_DIR"

# Generate output filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/cliclick_commands_${TIMESTAMP}.sh"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║        Cliclick Command Recorder v2.0               ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "📁 Commands will be saved to: $OUTPUT_FILE"
echo ""
echo "Instructions:"
echo "  🖱️  Move your mouse to the desired position"
echo "  ↩️  Enter cliclick command to capture the current mouse position (e.g., c, dc)"
echo "  🚪  Press Enter without typing anything to exit"
echo ""

# Array to store commands
commands=()

while true; do
    echo "─────────────────────────────────────────────────────"
    echo "📌 Command #$((${#commands[@]} + 1))"
    
    # Step 1: Ask user to move mouse to desired position
    echo "↩️  Move mouse to desired position then"
    read -p "   Enter cliclick command to run (leave blank to exit): " command
    
    # Check if user wants to quit during position capture
    if [[ -z "$command" ]]; then
        echo "❌ Recording cancelled."
        break
    fi
    
    # Get current mouse position using cliclick
    mouse_position=$(cliclick p 2>/dev/null)
    
    if [[ -z "$mouse_position" ]]; then
        echo "⚠️  Failed to get mouse position. Please try again."
        continue
    fi
    
    # Extract x and y coordinates
    x=$(echo $mouse_position | cut -d',' -f1)
    y=$(echo $mouse_position | cut -d',' -f2)
    
    echo "   📍 Current position: ($x, $y); command: $command"
    
    
    # Store the command with position
    full_command="cliclick $command:$x,$y"
    commands+=("$full_command")
    last_command="$command"
    
    echo "   ✅ Added: $full_command"
    echo ""
    
    # Optionally execute the command immediately for testing
    # 
    
    # Show progress
    echo "   📊 Recorded: ${#commands[@]} command(s) so far"
done

# Step 4: Write all commands to a new file separated by commas
if [[ ${#commands[@]} -gt 0 ]]; then
    # Join commands with commas
    joined_commands=$(IFS='\\n'; echo "${commands[*]}")
    
    # Write to file
    printf "%s\n" "${commands[@]}" > "$OUTPUT_FILE"
    
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "✅ Recording complete!"
    echo "📁 Commands saved to: $OUTPUT_FILE"
    echo "📊 Total commands recorded: ${#commands[@]}"
    echo ""
    echo "📝 File contents:"
    echo "─────────────────────────────────────────────────────"
    cat "$OUTPUT_FILE"
    echo ""
else
    echo "❌ No commands were recorded."
    exit 0
fi