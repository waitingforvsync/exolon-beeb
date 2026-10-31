# Makefile - the BBC Micro build.
#
#   make           build/exolon.ssd: !BOOT (*OPT 4,2); EXOC and EXOD, the sideways RAM banks packed; EXO2, main
#                  RAM's code and the loader. Its title is when it was built
#   make release MSG="what's new"
#                  the disc to the site (SITE/beeb/exolon.ssd), committed there alone with this repo's commit
#                  named, and pushed
#   make clean
#
# The data (build/gen) comes from the CPC disc, docs/exolon.dsk (git-ignored), through tools/gendata.py.
# Claude's emulator is jsbeeb, through jsbeeb-mcp only.

BARON ?= baron
PY ?= .venv/bin/python
SITE ?= $(HOME)/dev/waitingforvsync.github.io
RELEASE = beeb/exolon.ssd
BUILD = build
GEN = $(BUILD)/gen
DSK = docs/exolon.dsk

# the disc's title: when it was built, YYMMDD-HHMM
TITLE := $(shell date +%y%m%d-%H%M)

SRC = src/boot.6502 src/exolon.6502
GENOUT = $(GEN)/pens.6502
DEPS = $(wildcard src/*.6502) $(GENOUT)

all: $(BUILD)/exolon.ssd

$(GENOUT) &: tools/gendata.py tools/cpc.py tools/cpcdsk.py $(DSK) | $(BUILD)
	$(PY) tools/gendata.py $(GEN)

$(BUILD)/exolon.ssd: $(DEPS) | $(BUILD)
	$(BARON) -v --symbols $(BUILD)/exolon.json -o $@ --title $(TITLE) --opt 2 $(SRC) > $(BUILD)/exolon.lst

$(BUILD):
	mkdir -p $@

# Only the disc is committed there (other projects' releases share the repo): pulled first, so the push goes
# on top of theirs.
release: $(BUILD)/exolon.ssd
	@test -n "$(MSG)" || { echo 'make release MSG="what changed"'; exit 1; }
	git -C $(SITE) pull --ff-only --quiet
	cp $< $(SITE)/$(RELEASE)
	git -C $(SITE) add $(RELEASE)
	git -C $(SITE) commit --quiet -m "Exolon: $(MSG) (exolon-beeb $$(git describe --always --dirty 2>/dev/null || echo uncommitted))" -- $(RELEASE)
	git -C $(SITE) push --quiet

clean:
	rm -rf $(BUILD)

.PHONY: all release clean
