# Exolon → BBC Micro

A version of the Amstrad CPC disc version of *Exolon* (`docs/exolon.dsk`, git-ignored) for the BBC Micro: a
BBC B with two banks of sideways RAM at most, MODE 2 at the CPC's screen size, written in Baron. The owner is
Rich Talbot-Watkins, an expert BBC programmer and the author of BeebAsm and Baron, so pitch explanations at that
level. Use the `beeb-baron` skill for all 6502.

## Read first
- `docs/plan.md`: what the CPC version is (measured), the BBC design, the phases.
- `docs/decisions.md`: the decision log. Record new decisions there in Rich's words, with the date. Never mark
  your own recommendation as decided: it stays Proposed until Rich agrees.
- `JOURNAL.md`: what's been done, with measurements. Keep it up to date.
- `docs/cpc-*.md` (Phase 1): specs of the original, from its code.

## Rules (Rich, 2026-10-31)
- **Emulator: jsbeeb-mcp only** for iteration and testing. Never launch b2 or talk to its HTTP API: other
  sessions use it. Create one jsbeeb machine at a time and destroy it when you're done. The headless tools
  (`tools/jsbeeb*.mjs`) use jsbeeb from jsbeeb-mcp's npm package.
- **Memory and processes:** the machine has 12 GB, shared with other sessions. Be careful not to run it out
  of memory: one heavy process at a time, at most one review agent at a time, never a whole emulator memory
  printed or copied to the terminal.
- **Don't transliterate the Z80.** Get a spec from the code and write the 6502 that suits the 6502: indexed
  tables, self-modification, unrolled hot loops. Where the original is written suboptimally, do better.
- **Optimised from the start**: every routine as fast as it can be from its first line (the skill's
  `optimisation.md`). But **unroll only the hot loops** (the sprite code): main RAM has no room to spare
  (D22). Nothing relied on that the MOS happens to leave (D23).
- **Review:** when a feature works, have a second agent review its code for optimisations.
- **Commits:** commit and push whenever a milestone is reached that you're satisfied with.
- **Release:** a disc worth releasing goes to `~/dev/waitingforvsync.github.io/beeb/exolon.ssd`: `make release
  MSG="..."` copies it there, commits only that file in that repo, and pushes.
- Generated data from the CPC disc goes in `build/` (git-ignored), made from the `.dsk` at build time.

## Toolchain
- **Baron** (`baron` 0.6): `make` builds `build/exolon.ssd` (its title the build's date and time), with a `-v`
  listing in `build/exolon.lst` and symbols in `build/exolon.json`.
- **Python:** `.venv/bin/python` (git-ignored: z80, skoolkit, pillow, py65, numpy). Recreate with
  `python3 -m venv .venv && .venv/bin/pip install z80 skoolkit pillow py65 numpy`.
- **The CPC reference** (`tools/cpc.py`): the original running on kosarev's Z80 with a minimal CPC round it.
  `CPC()` starts at `&0100` with everything loaded; `start_game()` gets past the title; `run_passes(n,
  keys_for)` runs main-loop passes (each to `&06C3`); `time_passes(n, keys_for)` single-steps them with the
  CPC's microseconds; `screen_png(path)` renders what's shown. Keys are the CPC's: O, P, Q, A, SPACE.
- **The Spectrum original** (D24): `docs/Exolon.tzx` (git-ignored), loaded once to `build/spec/exolon.z80` by
  `.venv/bin/tap2sna.py --start 0x6D60 -c finish-tape=1 -c timeout=500 docs/Exolon.tzx build/spec/exolon.z80`.
  `tools/spectrum.py` runs it (`Spectrum()`, `run_frames`, `run_to`, `hold`, `screen_png`);
  `tools/cpc2spec.py [CPC addresses]` maps CPC routines to their Spectrum twins. Mechanics are checked against
  both; where they differ, Rich chooses.
- `tools/cpcdsk.py` reads the disc's files; `tools/gendata.py` makes `build/gen` from them.
- `.venv/bin/sna2skool.py -H -o 0 -s START -e END -c 0 dump.bin` disassembles a 64K dump (named `.bin`; make
  one with `cpc.initial_memory()`).
- `node tools/jsbeeb_time.mjs --label game.loop` times a loop in headless jsbeeb with the real IRQ.
- `python tools/aligncomments.py src/x.6502` puts trailing comments on column 40.
