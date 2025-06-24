#!/bin/bash


# --- Unraid Disk Temperature Monitoring Script ---
# This script reads disk temperature data from Unraid's disks.ini file and sends it to Datadog.
# It captures disk slot, ID, temperature, and type, and sends these as metrics to a Datadog Agent.
# The script is designed to run periodically, collecting and sending disk temperature metrics.
# --- Setup Instructions --- (These instructions assume you have the Datadog Agent installed.)
# 1) Download/install user script plugin from Unraid Apps
# 2) Create a new script with this content
# 3) Set the script to run periodically (e.g., every 5m "*/5 * * * *")
# 4) Ensure the Datadog Agent is running and configured to receive metrics: 
#   a) Set the variable "DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true"
#   b) Ensure the port 8125 -> 8125 UDP is forwarded to the host.
# 5) Update Unraid's default disk polling interval:
#   a) Go to Settings -> Disk Settings -> Tunable (poll_attributes)"
#   b) Set "Tunable (poll_attributes)" to match the cron schedule (e.g., 5 minutes)


# --- Datadog Agent Configuration ---
DATADOG_HOST="localhost"
DATADOG_PORT="8125"
METRIC_PREFIX="unraid.disk"

# --- Logging Configuration ---
# Set to true to see console output, false for silent operation.
LOG_ENABLED=true

# --- System Configuration ---
# Location of the Unraid disk information file
DISKS_INI="/var/local/emhttp/disks.ini"


# --- Functions ---

# Function to write messages to the console (stdout).
log() {
    if [ "$LOG_ENABLED" = true ]; then
        # Prepend a timestamp and echo to standard output.
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}


# --- Main Script Execution ---

log "--- Script execution started. ---"

if [ ! -f "$DISKS_INI" ]; then
    log "ERROR: $DISKS_INI not found. Exiting."
    exit 1
fi
log "Found disk info file, starting parsing: $DISKS_INI"

disk_count=0
current_slot=""
current_id=""
current_temp=""
current_type="" # Variable to store the disk type

# This function processes the collected data for a single disk
process_metric() {
    # Check if we have a slot and a temperature. The ID and Type are good but not essential.
    if [[ -n "$current_slot" && -n "$current_temp" ]]; then
        # Check for valid numeric temperature, skip if not (e.g., flash drive temp="*")
        if [[ "$current_temp" =~ ^[0-9]+$ ]]; then
            log "Processing: Slot='${current_slot}', ID='${current_id}', Type='${current_type}', Temp='${current_temp}'"
            
            metric_name="${METRIC_PREFIX}.temperature"
            
            # Lowercase the type for a clean, consistent tag
            type_tag=$(echo "$current_type" | tr '[:upper:]' '[:lower:]')
            tags="disk_slot:${current_slot},disk_id:${current_id},disk_type:${type_tag}"
            
            metric="${metric_name}:${current_temp}|g|#${tags}"
            
            echo -n "$metric" >/dev/udp/"$DATADOG_HOST"/"$DATADOG_PORT"
            log "Sent metric: ${metric}"
            
            ((disk_count++))
        else
            log "Skipping disk '${current_slot}' because temperature ('${current_temp}') is not a valid number."
        fi
    fi
}

# Read the disks.ini file line by line
while IFS= read -r line; do
    # --- MODIFIED LINE: Replaced faulty 'xargs' with 'sed' for safe whitespace trimming ---
    clean_line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

    # Check for a new disk section header (e.g. ["disk1"])
    if [[ "$clean_line" =~ ^\[\".+\"\]$ ]]; then
        # When we find a new disk, process the data for the *previous* one
        process_metric

        # Reset variables for the new disk, removing brackets and quotes
        current_slot=$(echo "$clean_line" | tr -d '[]"')
        current_id=""
        current_temp=""
        current_type="" # Reset the type for the new section
    
    # Check for id, temp, and type lines within a section
    elif [[ "$clean_line" == id=* ]]; then
        current_id=$(echo "$clean_line" | cut -d'=' -f2 | tr -d '"')
    elif [[ "$clean_line" == temp=* ]]; then
        current_temp=$(echo "$clean_line" | cut -d'=' -f2 | tr -d '"')
    elif [[ "$clean_line" == type=* ]]; then # Capture the disk type
        current_type=$(echo "$clean_line" | cut -d'=' -f2 | tr -d '"')
    fi
done < "$DISKS_INI"

# The loop has finished, but the very last disk's data is still in memory.
# We need to process it now.
process_metric

log "Processed and sent metrics for ${disk_count} disks."
log "--- Script execution finished. ---"