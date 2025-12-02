#!/bin/bash

API="http://localhost:8000"

echo "=== TEST 1: List Projects ==="
curl -s "$API/projects" | jq

echo "=== TEST 2: Create Project ==="
PROJECT=$(curl -s -X POST "$API/projects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Test Project", "description": "Integration test"}')

echo "$PROJECT" | jq

PROJECT_ID=$(echo "$PROJECT" | jq -r '.id')

echo "=== TEST 3: Create Task ==="
TASK=$(curl -s -X POST "$API/tasks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"title\": \"Test Task\",
    \"description\": \"Testing task\",
    \"priority\": 1
  }")

echo "$TASK" | jq

TASK_ID=$(echo "$TASK" | jq -r '.id')

echo "=== TEST 4: Update Task Status (Drag & Drop Simulation) ==="
curl -s -X PUT "$API/tasks/$TASK_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "completed"}' | jq

echo "=== TEST 5: Add Comment ==="
curl -s -X POST "$API/comments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"task_id\": \"$TASK_ID\",
    \"author_id\": null,
    \"text\": \"This is automated comment\"
  }" | jq

echo "=== TEST 6: Add Timeline Item ==="
curl -s -X POST "$API/timeline" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"task_id\": \"$TASK_ID\",
    \"title\": \"Progress updated\",
    \"description\": \"Task moved to completed\"
  }" | jq

echo "=== TEST 7: Delete Task ==="
curl -s -X DELETE "$API/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq

echo "=== TEST 8: Delete Project ==="
curl -s -X DELETE "$API/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq

echo "=== ALL DONE ==="
