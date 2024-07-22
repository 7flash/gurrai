#!/bin/bash

# Function to generate a random float between 0.0 and 1.0
generate_random_temperature() {
  temp=$(echo "scale=2; $RANDOM/32767" | bc)
  echo "$temp"
}

# Function to find the root directory containing the 'prompts' folder
find_root_dir() {
  current_path=$(pwd)
  while [ "$current_path" != "/" ]; do
    if [ -d "$current_path/prompts" ]; then
      echo "$current_path"
      return
    fi
    current_path=$(dirname "$current_path")
  done
  echo "Error: 'prompts' folder not found in any parent directory."
  exit 1
}

# Get the root directory
root_dir=$(find_root_dir)

# Define the directory to store prompt files
prompt_dir="$root_dir/prompts"
[ ! -d "$prompt_dir" ] && mkdir -p "$prompt_dir"

# Path to the AI script
# ai_script="$(pwd)/src/ai.py"
ai_script="$AI_SCRIPT_PATH"

# Default model and temperature
model="gpt-4-0613"
temperature=0.0

# Check if a model parameter was provided
if [ "$#" -gt 0 ]; then
  model="$1"
fi

# Check if a temperature parameter was provided
if [ "$#" -gt 1 ]; then
  temperature="$2"
else
  temperature=$(generate_random_temperature)
fi

echo "temperature $temperature"

# Generate a timestamp for file naming
timestamp=$(date +"%b%d-%H%M%S")

# Define input and output file paths
input_file="$prompt_dir/$timestamp-in.txt"
output_file="$prompt_dir/$timestamp-out.txt"

# Handle input: from a file, stdin, or create an empty file
if [ -n "$3" ]; then
  cp "$3" "$input_file"
elif [ -p /dev/stdin ]; then
  cat - > "$input_file"
else
  > "$input_file"
fi

# Open the input file for editing
hx -w "$prompt_dir" "$input_file"

# Display the input file path
echo "Input file: $input_file"

# Function to handle cleanup on exit
cleanup() {
  echo "Cleaning up..."
  exit 0
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

# Run the AI script and handle errors
if ! python3 "$ai_script" "$input_file" --model="$model" --temperature="$temperature"; then
  echo "Error: Failed to run the AI script."
  # exit 1
fi

# Open the output file for viewing
hx "$output_file"

# Display the output file path
echo "Output file: $output_file"

# Infinite loop for continuous interaction
while true; do
  # Generate a new timestamp for file naming
  timestamp=$(date +"%b%d-%H%M%S")

  # Define new input and output file paths
  new_input_file="$prompt_dir/$timestamp-in.txt"
  new_output_file="$prompt_dir/$timestamp-out.txt"

  echo "New input file: $new_input_file"

  # Copy the previous output to the new input file
  cp "$output_file" "$new_input_file"

  # Run the AI script and handle errors
  if ! python3 "$ai_script" "$new_input_file" --model="$model" --temperature="$temperature"; then
    echo "Error: Failed to run the AI script."
    # exit 1
  fi

  # Open the new output file for viewing
  hx -w "$prompt_dir" "$new_output_file"

  # Update the output file path for the next iteration
  output_file="$new_output_file"

  echo "New output file: $output_file"
done
