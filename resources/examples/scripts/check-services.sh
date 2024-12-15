#!/bin/bash

# Define the ports to curl
ports=(10124 1745 2810)

# Loop through each port and send a curl request
for port in "${ports[@]}"; do
  echo "Curling localhost on port $port"
  if ! curl -s "http://localhost:$port" > /dev/null; then
    echo "Service on port $port is unavailable."
    exit 1
  fi
  echo -e "\nAll services are available."
done

echo -e "\nChecking demo-cid-to-dv and transformer_cid-dv.xsl..."
# Send a curl request to the specified URL for repositories
response_repos=$(curl -s "http://localhost:2810/repositories")

# Check if the response contains "demo-cid-to-dv"
if echo "$response_repos" | grep -q "demo-cid-to-dv"; then
  echo "'demo-cid-to-dv' is available."
else
  echo "'demo-cid-to-dv' is not available."
  exit 1
fi

# Send a curl request to the specified URL for saved XSL list
response_xsl=$(curl -s "http://localhost:1745/saved-xsl-list-only")

# Check if the response contains "transformer_cid-dv.xsl"
if echo "$response_xsl" | grep -q "transformer_cid-dv.xsl"; then
  echo "'transformer_cid-dv.xsl' is available."
else
  echo "'transformer_cid-dv.xsl' is not available."
  exit 1
fi

echo -e "\nCongratulations! All services are available. You are ready to proceed."