#!/bin/bash

# Read the test file
CONTENT=$(cat ../test_validation/correct_page_component.tsx | jq -Rs .)

# Create JSON payload
cat << EOF > test_payload.json
{
  "content": $CONTENT,
  "filename": "correct_page_component.tsx"
}
EOF

# Send request to parser
echo "Testing parser with correct_page_component.tsx..."
curl -X POST http://localhost:3456/parse-file \
  -H "Content-Type: application/json" \
  -d @test_payload.json \
  | jq '.components'

# Clean up
rm test_payload.json