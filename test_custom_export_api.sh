#!/bin/bash
# Custom Export API Integration Test Script

API_TOKEN="2c00d45b8318a11f59e04c7233d729f3f17664e8"
BASE_URL="http://localhost:8080"

echo "========================================="
echo "Custom Export API Integration Tests"
echo "========================================="
echo ""

echo "Test 1: Count-only response (should return 3)"
echo "-------------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "count"}' | jq .
echo ""

echo "Test 2: Data response - all tasks (should return 3 tasks)"
echo "-----------------------------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "data"}' | jq '{total: .total, task_count: (.tasks | length), task_ids: [.tasks[].id]}'
echo ""

echo "Test 3: Verify superuser annotations only"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "data"}' | jq '.tasks[] | {task_id: .id, annotation_count: (.annotations | length), completed_by_info: [.annotations[].completed_by_info]}'
echo ""

echo "Test 4: Count with model_version filter (should return 1)"
echo "----------------------------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "count", "model_version": "bert-v1"}' | jq .
echo ""

echo "Test 5: Count with date range filter (should return 2 - tasks 6 and 10)"
echo "------------------------------------------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "count", "search_from": "2025-01-15 00:00:00", "search_to": "2025-01-20 00:00:00"}' | jq .
echo ""

echo "Test 6: Pagination - page 1, size 2"
echo "------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "data", "page": 1, "page_size": 2}' | jq '{total: .total, page: .page, page_size: .page_size, total_pages: .total_pages, has_next: .has_next, has_previous: .has_previous, task_count: (.tasks | length), task_ids: [.tasks[].id]}'
echo ""

echo "Test 7: Pagination - page 2, size 2"
echo "------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "data", "page": 2, "page_size": 2}' | jq '{total: .total, page: .page, page_size: .page_size, total_pages: .total_pages, has_next: .has_next, has_previous: .has_previous, task_count: (.tasks | length), task_ids: [.tasks[].id]}'
echo ""

echo "Test 8: Count with confirm_user_id filter (admin user ID=1)"
echo "------------------------------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "response_type": "count", "confirm_user_id": 1}' | jq .
echo ""

echo "Test 9: Invalid request - page without page_size"
echo "-------------------------------------------------"
curl -s -X POST "${BASE_URL}/api/custom/export/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "page": 1}' | jq .
echo ""

echo "========================================="
echo "All tests completed!"
echo "========================================="
