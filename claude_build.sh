#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# claude_build.sh  —  Single-command build for the PLATO compute stack
#
# Builds:
#   1. Fortran shared library  (libplato_math.so)
#   2. Zig bridge library      (libft_zig.so)
#   3. Zig FLUX dispatcher     (libdispatch.so)
#   4. Zig bridge tests
#   5. Install all .so to /usr/local/lib/ + ldconfig
#
# Exits 0 only if everything succeeds.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

readonly RED='\033[91m'
readonly GREEN='\033[92m'
readonly YELLOW='\033[93m'
readonly CYAN='\033[96m'
readonly BOLD='\033[1m'
readonly RESET='\033[0m'

OK=0
FAIL=1

# Working directory (script location)
cd "$(dirname "$0")"
BASE="$(pwd)"
FORT_DIR="${BASE}/fortran"
ZIG_DIR="${BASE}/zig"

success() { echo -e "  ${GREEN}✓${RESET} $1"; }
failure() { echo -e "  ${RED}✗${RESET} $1"; failed=1; }
info()    { echo -e "  ${CYAN}→${RESET} $1"; }
header()  { echo -e "\n${BOLD}$1${RESET}"; }

OVERALL=0

# ─── 1. Fortran shared library ──────────────────────────────────────────────
header "1. Fortran libplato_math.so"
(
  cd "${FORT_DIR}"
  info "Compiling plato_math.f90 → libplato_math.so ..."
  gfortran -O3 -fPIC -fopenmp -Wall -Wextra -shared \
    -o libplato_math.so plato_math.f90
  success "libplato_math.so ($(wc -c < libplato_math.so) bytes)"
) && success "Fortran build OK" || { failure "Fortran build failed"; OVERALL=1; }

# ─── 2. Zig bridge library (ft_zig.zig) ─────────────────────────────────────
header "2. Zig libft_zig.so"
(
  info "Compiling ft_zig.zig → libft_zig.so ..."
  zig build-lib "${ZIG_DIR}/ft_zig.zig" -lc -lplato_math -L/usr/local/lib -I"${ZIG_DIR}" \
    -femit-bin="${ZIG_DIR}/libft_zig.so"
  success "libft_zig.so ($(wc -c < "${ZIG_DIR}/libft_zig.so") bytes)"
) && success "Zig bridge build OK" || { failure "Zig bridge build failed"; OVERALL=1; }

# ─── 3. Zig FLUX dispatcher ─────────────────────────────────────────────────
header "3. Zig libdispatch.so"
(
  info "Compiling dispatch.zig → libdispatch.so ..."
  zig build-lib "${ZIG_DIR}/dispatch.zig" -lc -lplato_math -L/usr/local/lib -I"${ZIG_DIR}" \
    -femit-bin="${ZIG_DIR}/libdispatch.so"
  success "libdispatch.so ($(wc -c < "${ZIG_DIR}/libdispatch.so") bytes)"
) && success "Zig dispatch build OK" || { failure "Zig dispatch build failed"; OVERALL=1; }

# ─── 4. Zig bridge tests ────────────────────────────────────────────────────
header "4. Zig bridge tests"
(
  info "Running zig test bridge.zig ..."
  zig test "${ZIG_DIR}/bridge.zig" -lc -lplato_math -L/usr/local/lib -I"${ZIG_DIR}"
  success "All bridge tests passed"
) && success "Zig tests OK" || { failure "Zig tests failed"; OVERALL=1; }

# ─── 5. Install .so to /usr/local/lib/ ─────────────────────────────────────
header "5. Install shared libraries"
(
  INSTALLED=0
  for lib in libplato_math.so libft_zig.so libdispatch.so; do
    src="${FORT_DIR}/${lib}"
    [ -f "${src}" ] || src="${ZIG_DIR}/${lib}"
    if [ -f "${src}" ]; then
      install -m 644 "${src}" "/usr/local/lib/${lib}" 2>/dev/null || \
        sudo install -m 644 "${src}" "/usr/local/lib/${lib}" 2>/dev/null || \
        { failure "Cannot install ${lib} (permission denied, try: sudo install -m 644 \"${src}\" /usr/local/lib/)"; continue; }
      success "${lib} → /usr/local/lib/"
      INSTALLED=$((INSTALLED + 1))
    else
      failure "${lib} not found at ${src}"
      OVERALL=1
    fi
  done

  # ldconfig
  if command -v ldconfig &>/dev/null; then
    sudo ldconfig 2>/dev/null || ldconfig 2>/dev/null || true
    success "ldconfig updated"
  fi

  [ "${INSTALLED}" -eq 3 ] && success "All 3 libraries installed" || failure "Only ${INSTALLED}/3 libraries installed"
) || OVERALL=1

# ─── Report ─────────────────────────────────────────────────────────────────
echo ""
if [ "${OVERALL}" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}✓ All builds passed${RESET}"
else
  echo -e "${RED}${BOLD}✗ Some builds failed${RESET}"
fi

# Verify the install
echo ""
header "Verification"
for lib in libplato_math.so libft_zig.so libdispatch.so; do
  if [ -f "/usr/local/lib/${lib}" ]; then
    echo -e "  ${GREEN}✓${RESET} /usr/local/lib/${lib}  ($(wc -c < "/usr/local/lib/${lib}") bytes)"
  else
    echo -e "  ${RED}✗${RESET} /usr/local/lib/${lib}  MISSING"
    OVERALL=1
  fi
done

exit ${OVERALL}
