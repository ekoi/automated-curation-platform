#!/bin/bash

# Function to display usage
usage() {
  echo "Usage: $0 --token=<authorization_token> --user=<user_id> --data=<json_file> --ras_name=<ras_name> --target_creds=<target_creds>"
  exit 1
}

# Parse named arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --token=*) AUTH_TOKEN="${1#*=}"; shift ;;
    --user=*) USER_ID="${1#*=}"; shift ;;
    --data=*) DATA_FILE="${1#*=}"; shift ;;
    --ras_name=*) RAS_NAME="${1#*=}"; shift ;;
    --target_creds=*) TARGET_CREDS="${1#*=}"; shift ;;
    *) echo "Unknown parameter passed: $1"; usage ;;
  esac
done

# Check if all required arguments are provided
if [ -z "$AUTH_TOKEN" ] || [ -z "$USER_ID" ] || [ -z "$DATA_FILE" ] || [ -z "$RAS_NAME" ] || [ -z "$TARGET_CREDS" ]; then
  usage
fi

# Read JSON data from file
if [ ! -f "$DATA_FILE" ]; then
  echo "Data file not found: $DATA_FILE"
  exit 1
fi
DATA=$(cat "$DATA_FILE")

curl --location 'http://localhost:10124/inbox/dataset' \
--header "assistant-config-name: $RAS_NAME" \
--header "targets-credentials: $TARGET_CREDS" \
--header "user-id: $USER_ID" \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer $AUTH_TOKEN" \
--data "$DATA"