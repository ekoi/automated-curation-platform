#!/bin/bash

# Function to display usage
usage() {
  echo "Usage: $0 --token=<authorization_token> --user=<user_id> --id=<record_id>"
  exit 1
}

# Parse named arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --token=*) AUTH_TOKEN="${1#*=}"; shift ;;
    --user=*) USER_ID="${1#*=}"; shift ;;
    --id=*) RECORD_ID="${1#*=}"; shift ;;
    *) echo "Unknown parameter passed: $1"; usage ;;
  esac
done

# Check if all required arguments are provided
if [ -z "$AUTH_TOKEN" ] || [ -z "$USER_ID" ] || [ -z "$RECORD_ID" ]; then
  usage
fi

curl --location "http://localhost:10124/inbox/dataset/$RECORD_ID" \
--request DELETE \
--header "user-id: $USER_ID" \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer $AUTH_TOKEN"

# The response will be a 200 OK status code if the delete was successful
echo '\nDelete finished'