#!/bin/bash

# Function to display usage
usage() {
  echo "Usage: $0 --token=<authorization_token> --user=<user_id> --data=<json_data>"
  exit 1
}

# Parse named arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --token=*) AUTH_TOKEN="${1#*=}"; shift ;;
    --user=*) USER_ID="${1#*=}"; shift ;;
    --data=*) DATA="${1#*=}"; shift ;;
    *) echo "Unknown parameter passed: $1"; usage ;;
  esac
done

# Check if all required arguments are provided
if [ -z "$AUTH_TOKEN" ] || [ -z "$USER_ID" ] || [ -z "$DATA" ]; then
  usage
fi

curl --location 'http://localhost:10124/inbox/dataset' \
--header 'assistant-config-name: demo-cid-to-file' \
--header 'targets-credentials: [{"target-repo-name": "demo-cid-to-file"}]' \
--header "user-id: $USER_ID" \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer $AUTH_TOKEN" \
--data "$DATA"

echo '\nIngest finished'