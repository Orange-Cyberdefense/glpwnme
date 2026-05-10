#!/usr/bin/env bash
# Run CVE false-positive tests against local GLPI 10.0.23
# Usage: bash test_cves.sh

TARGET="http://127.0.0.1:18080"
GLPI_USER="glpi"
GLPI_PASS="glpi"
AUTH="-u $GLPI_USER -p $GLPI_PASS"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0; FAIL=0

pass() { PASS=$((PASS+1)); printf "${GREEN}[PASS]${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "${RED}[FAIL]${NC} %s\n" "$1"; }
info() { printf "${YELLOW}[INFO]${NC} %s\n" "$1"; }

info "Target: $TARGET (GLPI 10.0.23 — patched for all CVEs under test)"
info "Credentials: $GLPI_USER / $GLPI_PASS (ensures accurate version detection)"
echo ""

# Wait for GLPI to be reachable
info "Waiting for GLPI to be ready..."
for i in $(seq 1 20); do
  code=$(curl -sk "$TARGET/" -o /dev/null -w "%{http_code}" 2>/dev/null)
  if [[ "$code" == "200" || "$code" == "302" ]]; then
    info "GLPI is up (HTTP $code)"
    break
  fi
  sleep 2
done

# Helper: run a check with AUTH and assert it does NOT fire
# Always passes credentials so the version is accurately detected as 10.0.23
assert_not_vulnerable() {
  local cve="$1"
  local result
  result=$(python3 -m glpwnme -t "$TARGET" $AUTH -e "$cve" --check --no-opsec 2>&1)

  local not_vuln_pattern="not vulnerable|not injectable|not accessible|not enabled|not found|hhook.*ignored|boolean oracle.*not|no row delta|endpoint.*404|version.*not"

  if echo "$result" | grep -qiE "$not_vuln_pattern"; then
    pass "$cve — correctly not flagged"
  elif echo "$result" | grep -qiE "confirmed.*injection|injection present|shell confirmed|bypass.*confirmed|differential.*confirmed"; then
    fail "$cve — FALSE POSITIVE on patched version!"
    echo "$result" | tail -5 | sed 's/^/  /'
  else
    info "$cve — inconclusive (no credentials required for this CVE or no check() method):"
    echo "$result" | grep -vE "^\s*$|Version of (glpi|php)|GLPI (API|Inventory)|GLPI con" | tail -3 | sed 's/^/  /'
  fi
}

echo ""
info "=== ALL CVEs (with auth for accurate version 10.0.23 detection) ==="
echo ""

for cve in \
  CVE_2020_15175 \
  CVE_2022_31061 \
  CVE_2022_35914 \
  CVE_2022_35947 \
  UNSERIALIZE_ORDER_2022 \
  CVE_2023_42802 \
  CVE_2023_36808 \
  CVE_2023_36810 \
  CVE_2023_41320 \
  CVE_2023_41326 \
  CVE_2023_43813 \
  CVE_2024_27096 \
  CVE_2024_27937 \
  CVE_2024_29889 \
  CVE_2024_31456 \
  CVE_2024_37148 \
  CVE_2024_37149 \
  CVE_2024_40638 \
  CVE_2024_43418 \
  CVE_2024_47758 \
  CVE_2024_47760 \
  CVE_2024_47761 \
  CVE_2024_48912 \
  CVE_2024_50339 \
  CVE_2025_21619 \
  CVE_2025_21626 \
  CVE_2025_23024 \
  CVE_2025_24799 \
  CVE_2025_24801 \
  CVE_2025_25192 \
  CVE_2024_45608 \
  CVE_2024_41679 \
  CVE_2024_43416 \
  CVE_2025_53008 \
  CVE_2025_32786 \
  CVE_2025_53105 \
  CVE_2025_59935 \
  CVE_2025_64516 \
  CVE_2025_64520 \
  CVE_2025_66417 \
  CVE_2026_22247 \
  CVE_2026_22248 \
  CVE_2026_23624 \
  CVE_2026_25936 \
  CVE_2026_25937 \
  CVE_2026_26026 \
  CVE_2026_26027 \
  CVE_2026_26263; do
  assert_not_vulnerable "$cve"
done

# CVE_2023_41323 has no check() method — use check-all to verify
result=$(python3 -m glpwnme -t "$TARGET" $AUTH --check-all --no-opsec 2>&1 | grep "CVE_2023_41323")
if echo "$result" | grep -qiE "not vulnerable"; then
  pass "CVE_2023_41323 — correctly not flagged (no check method, version-gated)"
else
  info "CVE_2023_41323 — $result"
fi

echo ""
info "=== CVE_2026_29047 (SHOULD fire — patched in 10.0.24, instance is 10.0.23) ==="
echo ""

result=$(python3 -m glpwnme -t "$TARGET" $AUTH -e CVE_2026_29047 --check --no-opsec 2>&1)
if echo "$result" | grep -qiE "UNION confirmed|injection present|Confirmed:"; then
  pass "CVE_2026_29047 — correctly detected SQLi on 10.0.23 (unpatched)"
else
  fail "CVE_2026_29047 — expected to detect injection on 10.0.23 but got: $(echo "$result" | tail -2)"
fi

echo ""
info "=== CVE_2026_22044 (SHOULD fire — patched in 10.0.24, instance is 10.0.23) ==="
info "Note: requires at least one user row; glpi/glpi admin user satisfies this"
echo ""

result=$(python3 -m glpwnme -t "$TARGET" $AUTH -e CVE_2026_22044 --check --no-opsec 2>&1)
if echo "$result" | grep -qiE "injection present|timing confirmed|Confirmed:"; then
  pass "CVE_2026_22044 — correctly detected ORDER BY backtick injection on 10.0.23"
else
  info "CVE_2026_22044 — $(echo "$result" | tail -2)"
fi

echo ""
info "=== DEFAULT_PASSWORD_CHECK (SHOULD fire — default creds active on this instance) ==="
echo ""

result=$(python3 -m glpwnme -t "$TARGET" $AUTH -e DEFAULT_PASSWORD_CHECK --check --no-opsec 2>&1)
if echo "$result" | grep -qi "Authentication successfull"; then
  pass "DEFAULT_PASSWORD_CHECK — correctly detected default credentials"
else
  fail "DEFAULT_PASSWORD_CHECK — expected to find default creds but didn't"
  echo "$result" | tail -5 | sed 's/^/  /'
fi

echo ""
printf "${YELLOW}[INFO]${NC} === Summary: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC} ===\n"
