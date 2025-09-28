#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Default path for Kafka Home and the distributed properties file
KAFKA_HOME=${KAFKA_HOME:-/opt/kafka}
CONFIG_FILE="$KAFKA_HOME/config/connect-standalone.properties"

# --- 1. Populate the default config file with environment variables ---
# This function converts environment variables starting with CONNECT_
# (e.g., CONNECT_BOOTSTRAP_SERVERS) into Kafka Connect properties
# (e.g., bootstrap.servers) and updates the configuration file.

update_connect_configs() {
    # Read environment variables starting with CONNECT_
    env | grep '^CONNECT_' | while IFS='=' read -r KEY VALUE; do
        # Transform the variable name: CONNECT_BOOTSTRAP_SERVERS -> bootstrap.servers
        prop_name=$(echo "${KEY#CONNECT_}" | tr '[:upper:]' '[:lower:]' | tr '_' '.')
        
        # Check if the property already exists in the file (commented or uncommented)
        if grep -qE "^#?$prop_name=" "$CONFIG_FILE"; then
            # If it exists, replace the whole line
            sed -i "s|^#\\?$prop_name=.*|$prop_name=$VALUE|" "$CONFIG_FILE"
        else
            # If it doesn't exist, append it to the end
            echo "$prop_name=$VALUE" >> "$CONFIG_FILE"
        fi
    done
}

# --- 2. Create and prepare the configuration file ---
# The Kafka base image usually has a default properties file. 
# We'll copy it to the working directory to safely modify it.
cp "$KAFKA_HOME/config/connect-distributed.properties" "$CONFIG_FILE"

# Apply the custom environment variables to the config file
update_connect_configs

echo "Starting Kafka Connect with configuration from $CONFIG_FILE"
# cat "$CONFIG_FILE" # Uncomment to debug the final configuration

# --- 3. Start the Kafka Connect Distributed Worker ---
# The $@ passes any CMD arguments (like 'start' from the Dockerfile)
exec "$KAFKA_HOME/bin/connect-distributed.sh" "$CONFIG_FILE" "$@"