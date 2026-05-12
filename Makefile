# AI Forest — Build Everything from Source
#
# Low-level build targets for every language in the stack.

.PHONY: all clean test fortran c go plato

all: fortran c go

# ── Fortran Compute Claw ──────────────────────────────────────────────────

fortran:
	$(MAKE) -C fortran

fortran-bench: fortran
	$(MAKE) -C fortran bench

# ── C Micro-Agent ─────────────────────────────────────────────────────────

c:
	$(MAKE) -C floor/micro

c-test: c
	echo "512" | floor/micro/micro-agent

# ── Go Floor Agent ────────────────────────────────────────────────────────

go:
	cd floor && go build -o floor ./...

go-test: go
	cd floor && ./floor -dir=/tmp/forest-test -interval=5s -name=make-test

# ── Python Tests ──────────────────────────────────────────────────────────

test: fortran c
	python3 tests/test_lowlevel_stack.py

# ── Full Stack ────────────────────────────────────────────────────────────

full: fortran c go
	@echo ""
	@echo "=== AI Forest — All Builds Passed ==="
	@echo "  Fortran:  $$(wc -c < fortran/libplato_math.so) bytes"
	@echo "  C:        $$(wc -c < floor/micro/micro-agent) bytes"
	@echo "  Go:       $$(wc -c < floor/floor) bytes"

# ── Clean ─────────────────────────────────────────────────────────────────

clean:
	$(MAKE) -C fortran clean
	$(MAKE) -C floor/micro clean
	rm -f floor/floor
