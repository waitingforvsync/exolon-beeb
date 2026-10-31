# Journal

What's been done, newest last, with measurements. Decisions are in `docs/decisions.md`; the plan in
`docs/plan.md`.

## 2026-10-31

### The disc and the CPC reference
- `tools/cpcdsk.py` reads `docs/exolon.dsk` (40 tracks, one side, data format) and its AMSDOS headers. The
  loader's own source is on the disc (`EXOLON.DAT`): it loads `EXOLON.1` at `&0100`, `EXOLON.2` at `&6BDD`, and
  `EXOLON.3` at `&C000` before moving it to `&A001`, then `JP &0100`.
- `tools/cpc.py`, after Chase H.Q.'s: the original on kosarev's Z80 from `&0100`, with the gate array, CRTC,
  PPI and AY. The title runs, '1' starts a game, and O, P, Q, A and SPACE play it. It runs with interrupts off
  and never reads vsync, so nothing more is needed.
- `CPC.time_passes` single-steps and charges each instruction the CPC's microseconds (ceil(T / 4) plus the
  known extra slots). Its stretch over plain 4 MHz T-states came to 1.156.

### The CPC's speed (`python tools/cpc.py`, three seeds by hand)
- 2,970 passes of random play (keys changed every 25 passes): the pass median 46.3 ms, 90% 54.6, 99% 102.1,
  max 268.1; 20.9 passes a second from the mean. Over 2 frames 74.1%, over 3 5.6%.
- The padding (`&2B88`, `&2B9C`) left out: median 25.9 ms, 90% 38.3, 99% 86.5, max 245.5.
- An earlier run with keys the game doesn't read (the cursor keys) gave 42.3 ms a pass and 23.6 a second: a
  quiet screen. The figures above are the ones to beat.
- The player walks 1 pixel a pass; a jump rises 1, 1, 1, 2, 2, 2, 4, 4.

### Reading the code
- The main loop (`&06C3`-`&0788`), the padding, the XOR plotters (`&07D9`, `&0B5F`, `&2020`), the generator
  (`&3AE7`), the keys (`&0D20`) and the CRTC set-up (`&3E90`): see `docs/plan.md`.
- Recursive descent from `&0100` reaches 10,277 bytes of code, all below `&6649`.
- The palette's pairs by Chase H.Q.'s D7 rule: seven pens plain, nine dithered (`docs/plan.md`, Colours).

### Rich's direction, and what it needed checking
- Rich chose Teddy Boy's sprites (self-erasing, straight to the screen, masked over non-empty tiles and other
  sprites), one screen raced against the beam, 25 a second, EOR for transient effects, and two banks at most
  (D7-D11).
- The zones are on the Spectrum's character grid: each zone a list of (row 0-19, column 0-31, object) through
  `&490E`, 1,319 placements of 57 objects in 4,082 bytes; each object a script of 2-byte × 8-line blocks. So
  the background is a 32 × 22 tile map, which is what Teddy Boy's method needs (P8).
- ZX02 (Baron's transform, a scratch build): `&6649`-`&B1CC` 19,332 → 6,969; the zone lists 4,055 → 2,500;
  `&0100`-`&6648` 25,929 → 14,170. The whole image at once is too big for one Baron list.
- The longest passes: the zone change (268 ms, zone 0 to 1) and the player turning round (145-155 ms against
  about 46). Turning runs `&0E04` (checked with a breakpoint), which mirrors all 24 player frames in place.

### Packing, keys, sound and the loading screen
- Rich: unpack the next screen's set in the pause between screens (D12), sound at 50 Hz (D13), Z X : / RETURN
  SPACE (D14), the loading screen ported however suits it (D15).
- Sprites packed (scratch: the CPC's frames dithered to BBC bytes, Baron's ZX02 transform, literals counted by
  an instrumented copy of Teddy Boy's `zx02.py`): the player's 24 frames 4,608 → 869 in column order (975 in
  row order, 832 as undithered CPC pens), the 16-line objects 2,880 → 659. Literals are 251 and 194 bytes of
  those, so 6-bit literals would save about 7% (P12).
- The player's pixels by pen: 0 6,135 of 9,216; pens 1 and 4 591 of the 3,081 opaque ones.
- `EXOLON.SCR` unpacked by its own code (`&8000`, to `&4000`) and `FADEIN.BIN`'s copy: a MODE 1 screen in
  black, bright red, bright green and bright white (the BASIC loader's inks), 256 × 192 at columns 32-287.
  53 distinct bytes. It needs no dithering on the BBC (D15).

### Phase 0: the skeleton (`src/`, `Makefile`, `tools/`)
- Git: `waitingforvsync/exolon-beeb`, private, as Chase H.Q.'s (`build/`, `.venv/`, `work/` and the `.dsk`
  ignored). A venv with z80, SkoolKit 10.1, Pillow, py65 and numpy.
- `make` builds `build/exolon.ssd` titled with the date and time: `!BOOT`, `EXOC` and `EXOD` (the banks,
  ZX02), `EXO2` (main RAM's code, ZX02, then the loader, loaded at `&5000` in the screen).
- `!BOOT` (Chase H.Q.'s, no speech bank) finds two banks the OS's ROM table doesn't list, unpacks each bank's
  file into it, and runs `EXO2`. The loader takes the machine over as Chase H.Q.'s and Teddy Boy's do.
- The CRTC: 64 bytes × 24 rows at `&5000` (R1 64, R2 90, R6 24, R7 31, R12/R13 `&0A00`), one 39-row frame,
  the display off until the game's drawn the screen. Palette: logical 0-7 physical, 8-15 the same.
- The IRQ (`irq.6502`): System VIA T1 alone, a frame a period (`&4DFE`), synced once to vsync and set to fire
  as the beam leaves the screen's last line. It counts frames and reads Z, X, `:`, `/` and RETURN.
- The main loop waits for every second frame (`wait_pass`). For now it's a display test (`testcard.6502`): the
  16 pens dithered from `tools/gendata.py` as bands down the playfield, the 8 colours across the status, and a
  marker the keys move.
- jsbeeb (jsbeeb-mcp, Model B, DFS 1.2): boots, banks 6 and 7 found, the test card right, X for 20 frames moved
  the marker 10 bytes (a step a pass), `:` 20 lines up, RETURN its colour. The stack's sentinel intact, 5
  bytes used. A pass: 79,867-79,877 cycles between arrivals at `game.loop` (2.00 frames), in jsbeeb-mcp and
  in `tools/jsbeeb_time.mjs`.
- The first pass started at once, mid-frame; it now waits for the next frame's start as the rest do.
- Sizes: main RAM's code 3,040 bytes (mostly the pad to `&D00`), 109 packed; the code bank 326, 279 packed.
- Rules from Rich recorded in `CLAUDE.md` (jsbeeb-mcp only, memory, reviews, commits, releases); the jsbeeb
  rule added to the beeb-baron skill.
- Where the beam is at the IRQ's first instruction (headless jsbeeb's CRTC counters, six frames): row 23
  scanline 7 characters 125-127, or row 24 scanline 0 character 0. So it runs as line 192 starts, the screen's
  last line just finished, give or take the instruction it interrupted.

### Main RAM's code without gaps (D20), and the skeleton's review
- The main loop and the display test moved from the code's bank into main RAM, placed round IRQ1V, `&258` and
  `&D00` (14 and 2 bytes spare before the first two). The workspace is a virtual section from the code's end
  (`maincode_end`) to `&5000`. The banks hold only placeholders until Phase 2.
- The review (an agent, reading only) found:
  - **A bug**: a pass that ran late started at once, mid-frame. `wait_pass` now waits for the next frame's
    start, so every pass starts at line 192, and takes the keys itself (no SEI: the IRQ's just been). From the
    IRQ's increment to the pass: 50 → 24 cycles (its count); each poll 11 → 6. `read_keys` went.
  - **The IRQ**: no source test (T1 is the only one enabled), T1 acknowledged with X so A stays the MOS's 0
    and the `AND #KeysAll` goes. Faster and smaller, so taken. Unrolling the key scan (about 44 cycles a frame
    for 19 bytes) was Rich's call: "take the approach portalc takes, a loop".
  - Missing ASSERTs added (JMP (ind)'s pointer, the keys' bits, the stack and the code adjoining, the key
    table within a page); `passframe` now `wait_pass`'s own; the plan's stack range corrected.
  - For Phase 2: the beam's place from T1C-H (4-line steps: h means lines 188 - 4h to 191 - 4h, `&FF` the
    border), read between two reads of `irqframes`; or a second free-running timer (User VIA T1) a pass long.
- Measured after (headless jsbeeb, `game.loop` and the handler): the handler's first instruction at line 192
  character 7 every frame; 148 cycles from it to its RTI; passes 79,869 and 79,875 cycles alternately (2.00
  frames); X and `:` for 20 frames each moved the marker (31, 80) → (41, 60); the stack's sentinel intact.
- The IRQ clears A itself (D23), as Portal's does, rather than rely on the MOS's entry leaving it 0: still 148
  cycles to its RTI. Unrolling only for the hot loops (D22).

### The Spectrum original (D24)
- `docs/Exolon.tzx` (Rich's, git-ignored): SkoolKit's `tap2sna.py` loads it through the Hewson loader, run on
  to the game's entry with `--start 0x6D60 -c finish-tape=1` (without them the simulation stops in the
  loader's edge loop at `&FD29` when the tape ends; with a 240 s limit it stopped part-way).
- `tools/spectrum.py` runs it (48K ROM from SkoolKit, IM 1 interrupt every 69,888 T, keyboard on `&FE`): the
  title, then '1' to play.
- Main loop `&75BE`-`&7689` (found as the run of 22 CALLs at `&7623`): the CPC's calls in order plus
  `LD BC,&01F4 : CALL &B0B7`, a fixed delay. Pass counters `&768C`, `&768D`, `&AC7B`; random generator `&AD36`
  (the CPC's code byte for byte).
- 600 passes of random play, uncontended: a pass median 132,546 T (1.90 frames), mean 2.00 frames, 24.9
  passes a second; 90% 154,159 T, max 291,147 T.
- `tools/cpc2spec.py`: 111 of the CPC's 173 routine starts have a single Spectrum twin (the two loops' calls
  aligned by `difflib` on their callees' code, the rest by signature with addresses and branch displacements
  masked). Compared over each CPC routine's length, 5 constants differ before the code diverges, 4 of them
  `&DD`/`&E0` (a table's address byte). Most twins diverge at platform code (screen, colour), so mechanics
  are compared by reading.
- Phase 1's agents B and C were told to cross-reference their mechanics against it.

### Phase 1C: the objects (`docs/cpc-objects.md`, `tools/zoneobjects.py`; an agent)
- Zone set-up makes the objects from markers the scripts write into `&BA00` (`&EB n`), turned into 16 lists by
  `&1BE0`; `tools/zoneobjects.py` derives every zone's objects from the data and matches the harness's set-up
  in all 125 zones.
- Most at once in play (about 270,000 passes): 6 aliens, 5 big explosions, 16 spores, 10 launcher missiles, 20
  small explosions, 62 debris, 3 popups; at most 10 16- and 32-line sprites, 78 objects in all. The largest
  move in a pass: 4 pixels and 8 lines.
- The 16- and 32-line sprites are clipped where `&B700` is 0: they pass behind scenery a cell at a time. P9
  revised for it.
- Against the Spectrum: the same in every rule but the four empty object scripts and one alien path byte (O7).
  Questions O7-O9 for Rich.

### Phase 1B: the loop, the player and the flow (`docs/cpc-loop.md`, `cpc-player.md`, `cpc-flow.md`; an agent)
- The CPC's game logic is the Spectrum's code, unchanged bar the platform's calls: 136 passes of the same keys
  gave the same player, bolts, grenade and counts on both (`work/player/speccmp.py`).
- 53 calls a pass. The laser's bolts move a pixel a call, `&11C5` 5 times a pass; the grenade 1 step a pass
  for 13 passes, then 3 (`&1F89`). The padding `&2B9C` always draws 6 blank objects: its counter `&2BB1` is
  never incremented, on the Spectrum too. Both paddings cost 15.6-22.6 ms a pass.
- Corrections to the plan: the random generator is seed' = 13 × (seed + 7), the result A EOR its high byte; a
  jump rises 4, 4, 2, 2, 2, 1, 1, 1, 1, holds 4 passes and falls 1, 1, 1, 1, 2, 2, 2, 4, 4 (22 passes). My log
  had the fall.
- A grenade is thrown by holding fire 15 passes: no sixth key (D17 stands).
- Stages of 25 zones, each with a start point; 9 lives, one more at a stage's end; 700 passes in a zone before
  a time-out missile; the game loops to zone 0 after 124.
- Questions O10-O14 for Rich.

### Phase 1A: zones and graphics (`docs/cpc-zones.md`, `cpc-graphics.md`, `tools/zonemodel.py`, `tools/plotlog.py`; an agent)
- `tools/zonemodel.py` builds a zone from the data alone and matches the CPC's own drawing in all 125 zones,
  every playfield byte and both cell maps, with the title's seed and with a different seed poked for each
  (checked again here: zones 0-9, 10 of 10).
- One block a cell, exact; 445 distinct blocks, 7,120 bytes, 3,205 packed dithered in column order; 27-161 a
  zone. Placements and scripts pack to 4,046 bytes: the BBC runs the scripts at zone entry (P8).
- The 32- and 16-line plotters drop their bytes in cells whose `&B700` is 0: all scenery but the planets and a
  few others, and the status rows. So sprites go behind almost everything; composing over scenery is rare.
- 66 random stars before the placements; a cell written blank can't show one.
- In play, under a block a pass changes on the grid (flames, muzzles, burning mines, erasures); 26 tiles more.
- Workload (1,599 passes, zones 0, 38, 94, 99, padding left out): plots a pass median 21, 90% 53, max 218;
  bytes a pass 1,040, 1,968, 5,384. Largest move in a plot 4 pixels and 8 lines.
- Zone set-up 190-273 ms of CPC time (median 230), 74 ms of it clearing the screen.
- The disc's poke addresses are `DEC A`s; the variables are ammo `&1BB4`, grenades `&1BC0`, lives `&1BD4`,
  invulnerability `&078C`. The plan corrected.

### Phase 1 done
The spec of the original is in `docs/cpc-zones.md`, `cpc-graphics.md`, `cpc-loop.md`, `cpc-player.md`,
`cpc-flow.md` and `cpc-objects.md`, each checked in the harness and against the Spectrum. Open for Rich:
O7-O14 (`docs/decisions.md`).

### Rich's answers, and the sprite design revised
- D25-D29: the time limit 840 passes; the Spectrum's names, 17 entries; no pause or redefining for now; no
  lockstep at the AF' calls; the turn's still pass kept, mirroring the player's frames in it if it fits.
- D30-D32: frames trimmed to their bounding rectangle with dirty edges cleared first (Teddy Boy's way);
  sprites always behind the map; bit 3 as is useful. P9 and P10 rewritten: bit 3 marks the map's coloured
  pixels and the stars, so drawing and clearing read what's in front from the screen itself, and nothing is
  ever restored from tile data.
