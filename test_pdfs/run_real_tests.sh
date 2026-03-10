#!/bin/bash
# Real-world integration test script for Docstream
set -o pipefail

PASS=0
FAIL=0
OUTPUT_DIR="./real_test_outputs"
mkdir -p "$OUTPUT_DIR"

run_test() {
  local name=$1
  local pdf=$2
  local template=$3

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "TEST: $name"
  echo "PDF:  $pdf | TEMPLATE: $template"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  local outdir="$OUTPUT_DIR/${name}"
  mkdir -p "$outdir"

  uv run docstream convert "$pdf" \
    --template "$template" \
    --output "$outdir" 2>&1

  if [ $? -eq 0 ]; then
    # Verify output files exist
    local tex_count=$(find "$outdir" -name "*.tex" | wc -l)
    local pdf_count=$(find "$outdir" -name "*.pdf" | wc -l)
    if [ "$tex_count" -gt 0 ] && [ "$pdf_count" -gt 0 ]; then
      local tex_size=$(du -h "$outdir"/*.tex 2>/dev/null | cut -f1)
      local pdf_size=$(du -h "$outdir"/*.pdf 2>/dev/null | cut -f1)
      echo "  .tex: $tex_size | .pdf: $pdf_size"
      echo "PASSED: $name"
      PASS=$((PASS + 1))
    else
      echo "FAILED: $name — output files missing (tex=$tex_count, pdf=$pdf_count)"
      FAIL=$((FAIL + 1))
    fi
  else
    echo "FAILED: $name — command exited with error"
    FAIL=$((FAIL + 1))
  fi
}

echo "=============================================="
echo "  DocStream Real-World Integration Tests"
echo "=============================================="

# Normal digital PDFs — all 3 templates
run_test "digital_report"     attention_paper.pdf   report
run_test "digital_ieee"       attention_paper.pdf   ieee
run_test "digital_resume"     attention_paper.pdf   resume

# IEEE multi-column paper
run_test "multicolumn_report" resnet_ieee.pdf       report
run_test "multicolumn_ieee"   resnet_ieee.pdf       ieee

# Scanned PDF (OCR path)
run_test "scanned_report"     scanned_test.pdf      report

echo ""
echo "=============================================="
echo "  RESULTS: $PASS passed | $FAIL failed"
echo "=============================================="
echo ""

# List all outputs
echo "Output files:"
find "$OUTPUT_DIR" -type f \( -name "*.tex" -o -name "*.pdf" \) | sort
