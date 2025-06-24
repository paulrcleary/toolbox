#!/bin/bash

# =================================================================================
# Unraid Disk Temperature Monitoring Script for Datadog
# =================================================================================
#
# Description:
# This script reads disk data (temperature, ID, type, device, transport, etc.)
# from Unraid's disks.ini file and sends it as metrics to a Datadog agent.
#
# --- Setup Instructions ---
#
# 1. Install "User Scripts" Plugin:
#    In the Unraid UI, go to Apps and install the "User Scripts" plugin.
#
# 2. Create the Script:
#    Go to Settings -> User Scripts and create a new script. Paste the
#    entire content of this file into it.
#
# 3. Schedule the Script:
#    Set the script to run periodically using a cron schedule.
#    Recommended: Every 5 minutes -> */5 * * * *
#
# 4. Configure Datadog Agent:
#    Your Datadog Docker container must be configured to receive these metrics.
#    a) Set Environment Variable: DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true
#    b) Map Port: Ensure port 8125/udp is mapped from the container to the host.
#
# 5. Configure Unraid Polling Interval:
#    Match Unraid's disk polling interval to your script's schedule.
#    a) Go to Settings -> Disk Settings.
#    b) Set "Tunable (poll_attributes)" to your schedule in seconds (e.g., 300 for 5 minutes).
#
# =================================================================================


# --- Configuration ---
DATADOG_HOST="localhost"    # Host where the Datadog Agent is running
DATADOG_PORT="8125"         # Default DogStatsD port
METRIC_PREFIX="unraid.disk" # Prefix for all metrics
LOG_ENABLED=true            # Set to 'true' to see console output, 'false' for silent operation

# --- System File ---
DISKS_INI="/var/local/emhttp/disks.ini"


# --- Functions ---

# Function to write timestamped messages to the console (stdout).
log() {
    if [ "$LOG_ENABLED" = true ]; then
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
current_name=""
current_id=""
current_temp=""
current_type=""
current_device=""
current_transport=""
current_rotational=""

# This function processes the collected data for a single disk block
process_metric() {
    # Check if we have the essential pieces of information: a name and a temperature.
    if [[ -n "$current_name" && -n "$current_temp" ]]; then
        # Check for a valid numeric temperature, skipping if not (e.g., flash drive has temp="*")
        if [[ "$current_temp" =~ ^[0-9]+$ ]]; then
            log "Processing: Name='${current_name}', ID='${current_id}', Type='${current_type}', Temp='${current_temp}', Device='${current_device}', Rotational='${current_rotational}'"
            
            metric_name="${METRIC_PREFIX}.temperature"
            
            # --- Sanitize tag values for Datadog compatibility ---
            # Lowercase the type tag
            type_tag=$(echo "$current_type" | tr '[:upper:]' '[:lower:]')
            # Sanitize the disk_id: convert to lowercase and replace hyphens with underscores.
            sanitized_id=$(echo "$current_id" | tr '[:upper:]' '[:lower:]')
            
            # Determine drive_kind based on rotational status
            drive_kind=""
            if [[ "$current_rotational" == "1" ]]; then
                drive_kind="hdd"
            elif [[ "$current_rotational" == "0" ]]; then
                drive_kind="ssd"
            fi
            
            # Construct the tags string using the sanitized ID.
            tags="disk_name:${current_name},disk_id:${sanitized_id},disk_type:${type_tag},device:${current_device},transport:${current_transport}"
            if [[ -n "$drive_kind" ]]; then
                tags="${tags},drive_kind:${drive_kind}"
            fi
            
            metric="${metric_name}:${current_temp}|g|#${tags}"
            
            # Send the metric to the Datadog Agent via UDP
            echo -n "$metric" >/dev/udp/"$DATADOG_HOST"/"$DATADOG_PORT"
            log "Sent metric: ${metric}"
            
            ((disk_count++))
        else
            log "Skipping disk '${current_name}' because temperature ('${current_temp}') is not a valid number."
        fi
    fi
}

# Read the disks.ini file line by line
while IFS= read -r line; do
    # Use sed to safely trim leading/trailing whitespace without removing quotes
    clean_line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

    # Check for a new disk section header (e.g. ["disk1"])
    # This now only serves as a delimiter to trigger processing the previous block.
    if [[ "$clean_line" =~ ^\[\".+\"\]$ ]]; then
        # When we find a new disk section, process the data for the *previous* one
        process_metric

        # Reset all variables for the new disk block
        current_name=""
        current_id=""
        current_temp=""
        current_type=""
        current_device=""
        current_transport=""
        current_rotational=""
    
    # --- MODIFIED: Using a robust 'case' statement for parsing key-value pairs ---
    else
      # Extract the key and value from the line
      key=$(echo "$clean_line" | cut -d'=' -f1)
      value=$(echo "$clean_line" | cut -d'=' -f2- | tr -d '"')

      # Assign the value to the correct variable
      case "$key" in
          name)         current_name="$value" ;;
          id)           current_id="$value" ;;
          temp)         current_temp="$value" ;;
          type)         current_type="$value" ;;
          device)       current_device="$value" ;;
          transport)    current_transport="$value" ;;
          rotational)   current_rotational="$value" ;;
      esac
    fi
done < "$DISKS_INI"

# The loop has finished, but the data for the very last disk in the file
# is still in memory. We need to process it now.
process_metric

log "Processed and sent metrics for ${disk_count} disks."
log "--- Script execution finished. ---"
