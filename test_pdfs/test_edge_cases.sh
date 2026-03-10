#!/bin/bash
# Edge case tests for Docstream
set -o pipefail

PASS=0
FAIL=0
EDGE_DIR="./edge_test_outputs"
mkdir -p "$EDGE_DIR"

edge_test() {
  local name=$1
  local expected_exit=$2  # 0=success, 1=error expected
  shift 2
  local cmd="$@"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "EDGE: $name"
  echo "CMD:  $cmd"
  echo "EXPECTED EXIT: $expected_exit"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  output=$(eval "$cmd" 2>&1)
  actual_exit=$?

  echo "$output" | tail -5

  if [ "$actual_exit" -eq "$expected_exit" ]; then
    # Check: no raw Python traceback in error output (should be clean messages)
    if echo "$output" | grep -q "Traceback (most recent call last)"; then
      echo "FAILED: $name — raw Python traceback leaked to user"
      FAIL=$((FAIL + 1))
    else
      echo "PASSED: $name (exit=$actual_exit)"
      PASS=$((PASS + 1))
    fi
  else
    echo "FAILED: $name — expected exit=$expected_exit, got exit=$actual_exit"
    FAIL=$((FAIL + 1))
  fi
}

echo "=============================================="
echo "  DocStream Edge Case Tests"
echo "=============================================="

# 1. Empty/invalid file
echo "not a pdf" > "$EDGE_DIR/fake.pdf"
edge_test "invalid_pdf" 1 \
  "uv run docstream convert $EDGE_DIR/fake.pdf --template report --output $EDGE_DIR/invalid"

# 2. Non-existent file
edge_test "nonexistent_file" 1 \
  "uv run docstream convert /tmp/does_not_exist_12345.pdf --template report --output $EDGE_DIR/nofile"

# 3. Wrong template name
edge_test "wrong_template" 1 \
  "uv run docstream convert attention_paper.pdf --template doesnotexist --output $EDGE_DIR/wrongtpl"

# 4. Nested output directory (should auto-create)
edge_test "nested_output_dir" 0 \
  "uv run docstream extract attention_paper.pdf --output $EDGE_DIR/brand/new/nested/dir/blocks.json"

# 5. Extract command (no API needed)
edge_test "extract_only" 0 \
  "uv run docstream extract attention_paper.pdf --output $EDGE_DIR/extract_out.json"

# 6. Templates list command
edge_test "templates_list" 0 \
  "uv run docstream templates list"

# 7. Version command
edge_test "version" 0 \
  "uv run docstream --version"

echo ""
echo "=============================================="
echo "  RESULTS: $PASS passed | $FAIL failed"
echo "=============================================="
