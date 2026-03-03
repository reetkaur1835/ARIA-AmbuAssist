#!/bin/bash
# ============================================================
# ARIA Agent Test Script
# Usage: bash test_agents.sh [agent_name]
# Example: bash test_agents.sh general
#          bash test_agents.sh all
# ============================================================

BASE="http://127.0.0.1:8000/api/chat"
HEADERS='-H "accept: application/json" -H "Content-Type: application/json"'
SESSION="debug-session-$(date +%s)"

# Pretty-print helper — strips audio to keep output readable
pretty() {
  /Applications/anaconda3/bin/python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    d.pop('audio_base64', None)
    print(json.dumps(d, indent=2))
except Exception as e:
    print('RAW:', sys.stdin.read()[:500])
"
}

run_test() {
  local label="$1"
  local message="$2"
  local session="${3:-$SESSION}"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🧪  TEST: $label"
  echo "💬  Message: $message"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  curl -s -X POST "$BASE" \
    -H "accept: application/json" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$message\", \"session_id\": \"$session\"}" | pretty
  echo ""
}

AGENT="${1:-all}"

# ─────────────────────────────────────────────
# 1. GENERAL AGENT
# ─────────────────────────────────────────────
test_general() {
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: GENERAL"
  echo "══════════════════════════════════════════════════"
  run_test "General greeting" "Hello ARIA, how can you help me today?"
  run_test "General admin question" "What is ARIA and what can you do for me?"
  run_test "Clinical question (should redirect)" "What is the correct dose of epinephrine for anaphylaxis?"
}

# ─────────────────────────────────────────────
# 2. WEATHER AGENT
# ─────────────────────────────────────────────
test_weather() {
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: WEATHER"
  echo "══════════════════════════════════════════════════"
  run_test "Weather check" "What is the weather like today?"
  run_test "Weather for ops" "Should I be concerned about road conditions on shift?"
}

# ─────────────────────────────────────────────
# 3. SCHEDULE AGENT — own schedule
# ─────────────────────────────────────────────
test_schedule() {
  local S="sched-session-$(date +%s)"
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: SCHEDULE"
  echo "══════════════════════════════════════════════════"
  run_test "Own schedule today" "What shift am I working today?" "$S"
  run_test "Own schedule this week" "Can you show me my schedule for this week?" "$S"
  run_test "Station schedule" "Who is working at the Main St station tomorrow?" "$S"
  run_test "Partner lookup" "Who is my partner on shift today?" "$S"
}

# ─────────────────────────────────────────────
# 4. SHIFT CHANGE REQUEST (SCR) — multi-turn form
# ─────────────────────────────────────────────
test_shift_change() {
  local S="scr-session-$(date +%s)"
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: SHIFT CHANGE REQUEST (multi-turn)"
  echo "══════════════════════════════════════════════════"
  run_test "SCR - trigger" "I need to request a shift change" "$S"
  sleep 2
  run_test "SCR - provide date & action" "I want to swap my shift on March 10th from 7am to 7pm" "$S"
  sleep 2
  run_test "SCR - provide email" "Please send it to supervisor@ems.ca" "$S"
}

# ─────────────────────────────────────────────
# 5. OCCURRENCE REPORT — multi-turn form
# ─────────────────────────────────────────────
test_occurrence() {
  local S="occ-session-$(date +%s)"
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: OCCURRENCE REPORT (multi-turn)"
  echo "══════════════════════════════════════════════════"
  run_test "Occurrence - trigger" "I need to file an occurrence report" "$S"
  sleep 2
  run_test "Occurrence - describe incident" "There was a vehicle incident. Unit 4521 was involved in a minor collision at Main and King at 14:30. No injuries. Requested by dispatch." "$S"
  sleep 2
  run_test "Occurrence - provide email" "Send it to dispatch@ems.ca" "$S"
}

# ─────────────────────────────────────────────
# 6. TEDDY BEAR FORM — multi-turn form
# ─────────────────────────────────────────────
test_teddy_bear() {
  local S="tb-session-$(date +%s)"
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: TEDDY BEAR (multi-turn)"
  echo "══════════════════════════════════════════════════"
  run_test "Teddy bear - trigger" "I need to request a teddy bear for a patient" "$S"
  sleep 2
  run_test "Teddy bear - patient details" "It is for a 7 year old girl, she is a patient" "$S"
  sleep 2
  run_test "Teddy bear - provide email" "Please send the form to nurse@hospital.ca" "$S"
}

# ─────────────────────────────────────────────
# 7. STATUS CHECKLIST — read
# ─────────────────────────────────────────────
test_checklist_read() {
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: STATUS CHECKLIST (read)"
  echo "══════════════════════════════════════════════════"
  run_test "Checklist - full status" "What is my current compliance status?"
  run_test "Checklist - outstanding items" "Do I have any outstanding items or missing documents?"
  run_test "Checklist - specific item" "Is my ACR completed?"
}

# ─────────────────────────────────────────────
# 8. UPDATE CHECKLIST — write
# ─────────────────────────────────────────────
test_checklist_update() {
  echo ""; echo "══════════════════════════════════════════════════"
  echo "  AGENT: UPDATE CHECKLIST (write)"
  echo "══════════════════════════════════════════════════"
  run_test "Update - mark ACR done" "I just completed my ACR"
  run_test "Update - mark vaccination done" "My vaccination records have been submitted"
  run_test "Update - mark driver license done" "I have renewed my driver's licence"
}

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
case "$AGENT" in
  general)       test_general ;;
  weather)       test_weather ;;
  schedule)      test_schedule ;;
  shift_change)  test_shift_change ;;
  occurrence)    test_occurrence ;;
  teddy_bear)    test_teddy_bear ;;
  checklist)     test_checklist_read; test_checklist_update ;;
  all)
    test_general
    test_weather
    test_schedule
    test_shift_change
    test_occurrence
    test_teddy_bear
    test_checklist_read
    test_checklist_update
    ;;
  *)
    echo "Usage: bash test_agents.sh [general|weather|schedule|shift_change|occurrence|teddy_bear|checklist|all]"
    ;;
esac

echo ""
echo "✅  Tests complete."
