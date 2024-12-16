#!/bin/bash

# Function to display usage
usage() {
  echo "Usage: $0 --acp_token=<acp_authorization_token> --user=<user_id> --data=<json_file> --ras_name=<ras_name> --target_creds=<target_creds> [--content-type=<content_type>] [--dataset_id=<unique_dataset_id>]"
  exit 1
}

# Default content type
CONTENT_TYPE="application/json"

# Parse named arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --acp_token=*) AUTH_TOKEN="${1#*=}"; shift ;;
    --user=*) USER_ID="${1#*=}"; shift ;;
    --data=*) DATA_FILE="${1#*=}"; shift ;;
    --ras_name=*) RAS_NAME="${1#*=}"; shift ;;
    --target_creds=*) TARGET_CREDS_FILE="${1#*=}"; shift ;;
    --content-type=*) CONTENT_TYPE="${1#*=}"; shift ;;
    --dataset_id=*) DATASET_ID="${1#*=}"; shift ;;
    *) echo "Unknown parameter passed: $1"; usage ;;
  esac
done

# Check if all required arguments are provided
if [ -z "$AUTH_TOKEN" ] || [ -z "$USER_ID" ] || [ -z "$DATA_FILE" ] || [ -z "$RAS_NAME" ] || [ -z "$TARGET_CREDS_FILE" ]; then
  usage
fi

# Read JSON data from file
if [ ! -f "$DATA_FILE" ]; then
  echo "Data file not found: $DATA_FILE"
  exit 1
fi
DATA=$(cat "$DATA_FILE")

# Read target credentials from file
if [ ! -f "$TARGET_CREDS_FILE" ]; then
  echo "Target credentials file not found: $TARGET_CREDS_FILE"
  exit 1
fi
TARGET_CREDS=$(cat "$TARGET_CREDS_FILE")

# Prepare curl command
CURL_CMD="curl --location 'http://localhost:10124/inbox/dataset' \
--header \"Content-Type: $CONTENT_TYPE\" \
--header \"assistant-config-name: $RAS_NAME\" \
--header \"targets-credentials: $TARGET_CREDS\" \
--header \"user-id: $USER_ID\" \
--header \"Authorization: Bearer $AUTH_TOKEN\" \
--data \"$DATA\""

# Add dataset_id header if provided
if [ -n "$DATASET_ID" ]; then
  CURL_CMD="$CURL_CMD --header \"dataset-id: $DATASET_ID\""
fi

# Execute curl command
eval $CURL_CMD