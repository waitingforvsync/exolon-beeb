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

### Phase 2: the zones drawn on the BBC (the zone viewer)
- `tools/genzones.py`: the placement lists and object scripts as Baron source (labels for every pointer; the
  Spectrum's 543 attribute bytes dropped; block-set switches as global tile numbers), and the 492 tiles
  (blank, 7 stars, the barrier, the 21 sets whole) dithered to MODE 2 in the screen's order for a cell, bit 3
  on every pixel of a pen but 0 (P10). `--check` runs the rewritten scripts as the 6502 does and agrees with
  zonemodel in every cell of all 125 zones. Packed: zones' data 6,031 → 3,557, tiles 7,872 → 3,498.
- `src/zone.6502` (the code's bank): the display off; the zones' data unpacked into the screen; the stars (the
  original's generator, `src/rand.6502`, with its A at each call); each placement's script run into the tile
  map (local tile numbers given on first use, at most 195 a zone) and the cell map; the special cells and the
  barrier; the tiles unpacked into the screen and the zone's copied out; the playfield drawn, a cell 16
  consecutive bytes (cell n at `&5000 + 16n`).
- The main loop is a zone viewer for now: X and Z step through the zones, each with the CPC's seed `&6512`.
- `tools/check_zones.mjs` (headless jsbeeb): **all 125 zones match the original byte for byte**, stars
  included (so `rand` is right too).
- Too slow: `zone_enter` 599-647 ms against the CPC's 190-273 (unpacking 440 of it). P13 for Rich.
- The loader clears the status rows (the OS's MODE 7 screen was there).
- D33: the scripts raw (1,699 bytes), the placement lists packed a stage a block (5 blocks, 3,274), the tiles a
  set a block (21 blocks, 3,950; the 9 fixed tiles raw). A zone change unpacks its stage's lists and the sets
  its tiles are from (each local tile notes its set). The drawing stores zeros for blank cells.
- `tools/check_zones.mjs`: 125 of 125 zones byte-exact; `zone_enter` 182-337 ms, median 244 (was 599-647, 620;
  the CPC's 190-273, 230). The code's bank: 10,682 bytes (9,007 packed on the disc).

### Phase 2: the sprite plotter, first version, and its benchmark
- D35: faithful explosions at a steady 25. Rich on the layout: "check that column-major is the best way"; on bit 3:
  only the map's (as P10), and overlaps to be tracked and drawn differently (to come).
- `tools/gensprites.py`: the three sets' frames trimmed to their byte-aligned bounding rectangles for each shift,
  dithered (fixed to the sprite), in the screen's own cell layout: band j (lines 8j to 8j + 7) is the columns'
  8 bytes each, so column k line l is at 8k + l as on the screen. 158 sprites; 15,152 bytes with every frame,
  9,984 with the suit's, the title's twinkles and three unused frames left out for now (packs to come).
- The layout chosen by a model over the logged plots (zones 0, 38, 94, 99, 1,599 passes): column-major with a
  realign every column (as Chase H.Q.'s) median 19,944 cycles a pass, max 106,630; the cell layout with two
  pointers 17,062, 95,324; the cell layout writing whole cells 23,183, 108,956.
- `src/sprites.6502` (the data's bank): `walk` does a rectangle a band at a time, Y = 8k + l on the screen and
  in the sprite, the steps' operands patched for the sprite's phase (the band above for lines under it), so a
  whole band needs no realigning; the first and last bands are entered at their first line and left after
  their last by a JMP patched over the next step. Five unrolled step blocks: draw straight, draw behind the map
  (`Keep`/`Hole`, made by the loader), clear straight, clear behind the map, XOR. `large_edges` (phase 1: the
  old rectangle less the new, cleared), `large_draw` (phase 2), `xor_plot`.
- `tools/benchlog.py` turns the CPC's plot log into the plotter's commands; `make bench` and `tools/bench.mjs`
  replay them in headless jsbeeb, the host writing each pass's commands before it starts. Zone 0, 380 passes of
  random play: plotting median 9,458 cycles a pass, 90% 35,676, 99% 90,128, max 116,315; 34 passes over 40,000.
  The screen looks right (the player clean and dithered, shots and explosions XORed).
- The worst pass is 104 8-line XORs (52 debris, off and on): about 1,100 cycles a plot, 430 of them bytes. The
  rest is the general walker's set-up (the phase patch, two bands, the exit patch). The debris needs its own
  path.

### The plotter reviewed, and adopted
- A second agent reviewed the plotter for speed, measuring each change over the logs of four zones (0, 38, 94,
  99; 1,580 passes), with the screen's hash after every pass the same as the first version's.
- `walk` is now for the large sprites only (draw and clear, straight or behind the map). Its pointers step a
  band at a time, V is set for the whole bands, and the last band is left by a 2-byte BNE patched over the next
  step (was a JMP). `set_phase` patches the two draw blocks only, since the clear blocks read no sprite.
- The 8-line sprites have their own path, `xor8`: for each phase an unrolled run of 24 XOR steps (the lines
  under the phase through `xb`, the cell row below), entered at the sprite's width (`XEnt`).
- The debris (frame 2) is compiled: XOR immediates for each even phase, through `debris_xor` and `DebJmps`.
  Clearing it instead of XORing it was measured, and lost.
- The order in a pass: 8-line sprites off, large sprites' edges, large sprites drawn, 8-line sprites on.
- The srca bug: the draw steps were all assembled reading `(srcb),Y` and `set_phase` patched some to `(srca)`,
  so Baron saw srca never read and gave its bytes to other variables. That's Baron's documented limit (an
  operand patched at run time is invisible to it), not a bug in it. Steps 0-3 of both draw blocks are now
  assembled reading `(srca),Y`, with `StepsPhase` starting at 4 to match. The listing has srca at `&0E`, apart
  from srcb (`&02`), scr (`&04`) and the walk's own.
- The sprite tables: each of the six (`SprW`, `SprH`, `SprDX`, `SprDY`, `SprLo`, `SprHi`) is a page to
  itself, so no indexed read of one crosses a page, with whole sprites in the 98 bytes after each of the first
  five (480 bytes, the 8-line set first, so `xor8`'s reads never cross a page). The review's had all six
  `INPAGE`: the data bank is 512 bytes smaller (15,831 → 15,319 bytes in the benchmark's build) and 4-150
  cycles a pass faster than the review's at each measure below. Packed it's 49 bytes bigger (4,400 → 4,449), the padding having
  packed to nearly nothing. The game's build: 15,172 bytes (4,333 packed), 700 free below DataVars.

Plotting, cycles a pass (the first version → now), the screens hash-identical every pass:

| Zone | Median | 90% | 99% | Max | Passes over 40,000 |
|---|---|---|---|---|---|
| 0 | 9,458 → 7,003 | 35,676 → 19,174 | 90,128 → 36,160 | 116,315 → 49,529 | 34 → 1 of 380 |
| 38 | 55,871 → 29,988 | 82,494 → 42,772 | 92,549 → 48,989 | 106,092 → 57,140 | 343 → 77 of 400 |
| 94 | 62,422 → 32,293 | 130,844 → 59,223 | 178,925 → 78,488 | 207,866 → 86,967 | 400 → 117 of 400 |
| 99 | 31,244 → 25,747 | 48,817 → 37,230 | 106,417 → 59,245 | 144,780 → 75,706 | 120 → 26 of 400 |

- A pass has 79,872 cycles (two frames) less the IRQ's, and the game's logic must fit as well, so zone 94's worst
  passes are still too slow. Next, measured one at a time: small explosions as changes between frames, never
  plotting the blank frame 6, compiled spores and missiles, one walk for the dirty edges, and the game keeping
  each sprite's rectangle rather than `sprite_rect` working it out twice.
- A risk to keep in mind: the 8-line paths don't clip, so y must stay at most 168 (from 185 they would write
  past `&8000`).

### Overlaps: the Spectrum checked, and XOR where sprites meet
- Rich asked whether the Spectrum masks. It doesn't: single-stepping 60-80 passes of zones 1, 38 and 94 and
  noting every write to its bitmap, the only writers are XOR loops (the 32-line plotter `&7814`, 16-line
  `&7A37`, 8-line `&9325`, the bolt `&8313`) and the tiles' and characters' stores (`&AE04`, `&AE47`). It
  shifts each sprite at run time into a buffer, ANDs the buffer with a whole cell's mask from its cell map
  (`&5B00`, `&789E`) to hide it behind scenery, clips the right edge, and XORs it on, as the CPC does.
- Overlaps are common: in the logs the large sprites' rectangles meet in 0 of zone 0's passes, 109 of 38's,
  284 of 94's and 231 of 99's, mostly the player dying with aliens on him (random play overstates them).
- The logs had two quirks of the original's, now smoothed by `tools/benchlog.py`: a large sprite plotted twice
  in a pass (1-15 a log; the last kept, as the BBC plots once a pass), and a new 8-line object XORed off before
  it's first drawn (122-199 a log; it cancels the pass's XOR on of the same image). Both left debris in the
  self-erasing screens wherever a store fell between them. The 8-line set's blank frame (6) is left out (it
  XORs nothing), and each pass is in the review's order (8-line sprites off, edges, draws, 8-line sprites on):
  the logs had kept the CPC's order within each phase.
- `walk` has two more blocks, XOR straight and XOR behind the map (`LDA (scr),Y:TAX:LDA Hole,X:AND (src),Y:
  EOR (scr),Y:STA (scr),Y`, 29 cycles a byte): a pixel without bit 3 stays so, so the same pixels are masked
  when it's XORed off. Each pair of blocks that reads the sprite has its own phase (`SETPHASE`, a macro), and
  `xor8`'s `XEnt` went into the first sprite table's page (gensprites). `large_xor_off` and `large_xor_on`
  XOR a slot's sprite off its old place and on at its new; each slot keeps its sprite (`SlotS`). The bench has
  commands 5 and 6 for them; `tools/benchmode.py` recasts a log as all-XOR or hybrid.
- Hybrid: a large sprite whose box (old rectangle and new) meets another large sprite's is XORed that pass; the
  rest self-erase. **Every pass's screen is the same as all-XOR's** in all four logs (1,580 passes), and as
  self-erasing's in zone 0, which has no overlaps; self-erasing alone differs in 14, 13 and 116 passes of
  zones 38, 94 and 99.

Plotting, cycles a pass (median / 90% / worst; passes over 40,000), the touch test not yet in (it's the host's):

| Zone | Self-erasing (wrong where sprites meet) | All XOR | Hybrid |
|---|---|---|---|
| 0 | 6,776 / 18,441 / 48,629; 1 | 11,126 / 22,864 / 53,314; 8 | 6,776 / 18,441 / 48,629; 1 |
| 38 | 29,763 / 42,560 / 57,131; 69 | 35,744 / 48,090 / 62,277; 137 | 29,937 / 42,634 / 60,894; 70 |
| 94 | 32,355 / 57,986 / 79,604; 114 | 38,077 / 66,409 / 91,511; 187 | 32,355 / 58,686 / 79,604; 122 |
| 99 | 25,376 / 35,946 / 76,195; 24 | 34,162 / 46,973 / 88,494; 104 | 27,647 / 39,002 / 80,039; 38 |

- XORing everything costs 18-64% more than self-erasing at the median and 9-16% at the worst: each byte is read
  and written twice, against one store. The hybrid XORs 0-16% of the large plots (91 of 800 in zone 38, 84 of
  986 in 94, 386 of 2,444 in 99) and costs 0-9% at the median, 0-7% at the worst.
- The cost: `walk` 1 cycle more a draw, 4 a clear (the mode's dispatch), `large_draw` 7 (`SlotS`); the data
  bank 256 bytes more (15,172 → 15,428; packed 4,333 → 4,499), 444 free below DataVars.
- Rich's question on a broad phase that uses the small moves: the pairwise test of boxes is about 14-22 cycles a
  pair (at most 9 large sprites live in these logs: 36 pairs, about 800 cycles), and per-pair bookkeeping costs
  as much as the test. Sweep and prune on a y-sorted list, kept by an insertion sort, is the form worth having,
  since the beam ordering needs that list anyway. To be measured when it's written.

### The 8-line sprites compiled
- D37 recorded: Rich chose the XOR mix where large sprites meet, "for authenticity if nothing else".
- A profile of zone 94's slowest passes (185-220, PC sampled every 23 cycles): the debris 27.7% (its compiled
  code 23.3%), the other 8-line sprites 26.7% (`XorRuns` 21.5%), the large sprites about 29% (the behind-the-map
  draw 11.4%, `walk` 10.9%), the bench's own decoding 14.6%. The spores (frame 7) are the most XORed object in
  the logs (22,541 XORs, the debris 8,415), and 37% of the bytes `XorRuns` XORed were zero.
- `xor8` now runs compiled copies (gensprites' `xor8_code`) for every 8-line sprite but the debris (compiled per
  even phase already) and the blank: `LDY #8k+j:LDA (p),Y:EOR #v:STA (p),Y` for each byte that isn't zero (15
  cycles), two copies a sprite: lines 7 to 0 through `xt`, then lines 0 to 7 through `xb`, each to an RTS. With
  `xt` at the sprite's top-left byte and `xb = xt + 504`, column k line j is at Y = 8k + j through either, so a
  phase p runs the first from line 7 - p and the second from line 8 - p: two copies serve all 8 phases (1,647
  bytes for the spores per phase, 452 as two). The entries come from `XtLo`/`XtHi`/`XbLo`/`XbHi` by the
  sprite's `XcSlot` (in the first sprite table's page) and the phase. The dispatch is about 12 cycles more than
  `XorRuns`' (no sprite pointer to set), so a 16-byte sprite with no zero bytes is no faster; the spores' odd
  copy (24 bytes, 11 zero) goes from 432 cycles of XORing to 195.
- `XorRuns`, `RunLo`/`RunHi`, `XEnt` and the 8-line set's data left the data bank: 15,428 → 13,892 bytes
  (packed 4,499 → 4,233), about 1,980 free below DataVars. The compiled code and its tables (2,652 bytes) fill
  main RAM's padding at `&259`-`&CB4` (75 bytes left before `&D00`); EXO2's packed code 215 → 1,072 bytes.
  So 1,116 bytes more in all, for now in what was padding. `INPAGE` blocks (a high byte a sprite) were tried
  and wasted about 940 bytes of padding; per-entry high bytes cost 4 cycles a call and no padding.
- Every pass's screen as before in all 12 runs (self-erasing, all-XOR and hybrid, four zones). The hybrid:

| Zone | Median | 90% | Worst | Passes over 40,000 |
|---|---|---|---|---|
| 0 | 6,776 → 6,461 | 18,441 → 15,681 | 48,629 → 48,367 | 1 → 1 |
| 38 | 29,937 → 24,690 | 42,634 → 32,926 | 60,894 → 49,119 | 70 → 15 |
| 94 | 32,355 → 27,983 | 58,686 → 54,308 | 79,604 → 75,306 | 122 → 85 |
| 99 | 27,647 → 26,774 | 39,002 → 38,991 | 80,039 → 79,993 | 38 → 38 |

- The worst passes left in 94 and 99 are a grenade's debris (95-100 XORs, 50 particles off and on) with the
  spores; the debris is already compiled. Next: the behind-the-map draw chosen a cell at a time rather than a
  band (by cell 22-52% of the draws' bytes are over a tile, by band 52-80%; stars alone 2-25%), and the bench's
  decoding (about 70 cycles a command) brought nearer what the game's object loop will cost.

### The plotting alone, and what's left in it
- `make benchnull` builds the bench with the plotter's routines a bare RTS (`BENCHNULL`): its times are the
  bench's own decoding, a median 400-4,000 cycles a pass and up to 14,000, which every figure so far included.
  Taken off (the hybrid, D37):

| Zone | Median | 90% | Worst | Passes over 40,000 |
|---|---|---|---|---|
| 0 | 6,057 | 13,150 | 38,171 | 0 |
| 38 | 20,504 | 27,399 | 42,970 | 6 of 400 |
| 94 | 23,217 | 45,665 | 61,413 | 57 of 400 |
| 99 | 24,704 | 37,214 | 68,995 | 36 of 400 |

- The worst passes are a grenade's debris: about 100 XORs (50 particles off and on) at about 335 cycles each (52
  of set-up, 18 bytes at 15, the JSR and RTS), some 33,500 cycles. Debris flies in straight lines at a constant
  velocity (dx -4 to 4 pixels, dy -8 to 8 lines, `docs/cpc-objects.md`), but an old and a new image rarely
  overlap much and a delta for each move would be 384 variants: no gain there.
- A profile of zone 99's worst passes (122-131): `walk`'s own code 26.6%, as much as its step blocks (about
  30%), the debris 25%. By the listing a band costs the walk about 200 cycles besides its bytes, and zone 99
  averages 14 walks and 29 bands a pass (11 of them dirty edges, 6 of those one or two columns wide).
- Choosing straight or behind a cell at a time, worked out before it was written: a bitmap of 8-cell windows
  (154 bytes, any 4 cells in one byte) tests a band in 15-23 cycles against 16-52 now, about 26 a band, but costs
  about 40 more a walk to set up (its mask, its window): net about 200 cycles a pass in zone 99. A mixed band
  done as runs of cells costs about 250 cycles of handling and saves 120-480: about even. Neither was kept.
- Left in the walk: the middle bands' lines and entries worked out again each band (about 50 cycles of about
  200), sprites kept within a page (no high byte to step, no read crossing a page; some packing waste). About
  1,000-2,000 cycles a pass between them.

### The plot driver: each object a unit, in order (plot_pass)
- Racing the beam needs each object plotted as a unit, its 8-line XOR off and on together, not every 8-line
  sprite off at a pass's start and on at its end (each would be missing for most of a pass: a flicker at 25 Hz).
  Then no store may meet an 8-line sprite. XORing every large sprite an 8-line one's box meets (D37 extended)
  was measured first (`benchmode.py hybrid8`): exact, but zone 94's worst pass 61,413 → 72,208 cycles, zone 0's
  38,171 → 43,094. Not kept.
- `src/plotpass.6502`'s `plot_pass` (the data bank) takes a pass's objects as the game will give them: the
  large sprites plotted (slot, sprite, x, y, or gone), the debris (off at, on at) and the other 8-line sprites
  (by sprite). It works out the large sprites' new rectangles and boxes (old and new together), the touch
  test (D37), and then regions: the self-erasing ones by their tops, a region running on over gaps under 24
  lines. An 8-line sprite whose y (where it goes, else where it was) is from 15 lines above a region's top to 8
  below its bottom is on that region's list (an 8-line sprite moves at most 8 lines a pass and is 8 high, so
  that's all it can reach; regions 24 lines apart have disjoint reaches); the rest are XORed off and on as
  they're found (they commute with everything). Then the large sprites by their tops: an XORed one alone, a
  self-erasing one's region whole (its 8-line sprites off, its large sprites' edges and draws, the 8-line
  sprites on). The bench (moved to main RAM, `&D01` on, as the data bank is nearly full) decodes
  `benchlog.py --objects` streams (commands 10-14) into its lists.
- Binding each 8-line sprite to the large sprites its box meets, with row masks and exact tests, was written
  first: about 390 cycles a bound debris particle, and in zone 0's grenade passes all 62 particles are in the
  player's rows (+18,000 cycles). The regions cost about 110.
- The object streams: each image a pass XORs is taken off if it's on the screen before the pass and put on if
  it is after, each record's off and on paired where both are kept. A first version reduced each pass to its
  net XORs and dropped images XORed twice (an object put back where it was; one particle moving onto the
  spot another left), which left them on the screen unknown to the driver: zones 38 and 94 went wrong in 25
  and 276 passes. Images put on and taken off within a pass are left out (3,574 XORs against 3,882 in zone 0,
  15,067 against 18,739 in 94); every pass XORs the same images as before, mod 2.
- **Every pass's screen is the same as all-XOR's in all four logs** (1,580 passes).
- Two things the game must give: every 8-line sprite on the screen is in a pass's list (so no store meets one
  the driver doesn't know of), and an 8-line sprite moves at most 8 lines and 8 pixels a pass (the logs: never
  more).

Plotting alone (the bench's decoding off), cycles a pass, the hybrid's commands → plot_pass's objects:

| Zone | Median | 90% | Worst | Passes over 40,000 |
|---|---|---|---|---|
| 0 | 6,091 → 7,346 | 13,150 → 15,608 | 38,171 → 33,334 | 0 → 0 |
| 38 | 20,514 → 25,385 | 27,399 → 34,150 | 42,970 → 50,051 | 6 → 18 |
| 94 | 23,240 → 26,513 | 45,665 → 49,759 | 61,413 → 68,153 | 57 → 71 |
| 99 | 24,789 → 30,929 | 37,214 → 44,201 | 68,995 → 69,522 | 36 → 72 |

- The hybrid's figures had no per-object work at all (the bench called the plotter); a game's loop over its
  objects would spend some 40-50 cycles each. The driver's own work is about 23% of a typical zone 99 pass
  (the rectangles and boxes, a scan of all 16 slots, the touch test, the order, the regions, each rectangle
  fetched twice), about 1,000 cycles a large sprite, and about 110 a bound 8-line one.
- The data bank: 15,073 bytes (5,027 packed), 799 free below DataVars. Not yet: waiting for the beam (the order
  is there), and a check in jsbeeb that no object is plotted while the beam is on its lines.

### The plot driver waits for the beam
- D39 recorded. Each item (an XORed large sprite, a self-erasing one whose region has no 8-line sprites, or a
  region with them) gets the window when the beam is on its lines, in T1C-H's steps (4 lines, 256 us) since
  the frame's interrupt at line 192 (line 0 is step 30), and a time, at most: an XORed large sprite 4 steps and
  1.25 a band-column (8 bytes), a self-erasing one 2 and 1, a region 2, 1 a band-column of its large sprites
  and 2 an 8-line sprite (fitted to 1,060 items timed in zone 99). The driver plots the first item, by its top,
  that will be done before the beam reaches its top, or that the beam is past and that will be done before the
  beam is back; else it waits. An item too long for any gap in the beam goes once the beam is past it.
- A region's 8-line sprites now need its columns too (from 6 left of its large sprites to 4 right: an 8-line
  sprite is 3 wide and moves 4), else they're free: in zone 0's grenade passes the debris was all in the
  player's rows, so his region took more than a frame.
- `tools/beamcheck.mjs` stops at each item's start and end and reads the beam from jsbeeb's CRTC counters: an
  item whose lines the beam scans while it's plotted is a tear. Its first runs had my mistakes: a window's
  bottom one step short (T1C-H's resolution), time estimates of a fixed 4 steps (a self-erasing player takes
  12 or more), and a scheduler that waited for ever on an item too long for any gap.
- Tears: zone 0 none of 226 items; zone 38 10 of 473; 94 61 of 496; 99 23 of 2,062. Every one is an item too
  long for any gap (80, 138 and 53 of them): regions with many spores or debris by the player, which take more
  than a frame. Every pass's screen is still the same as all-XOR's in all four logs.
- Pass times with the waits (the bench's decoding off): zone 0 median 7,623, worst 45,614; 38 35,860, 92,767;
  94 47,804, 94,069; 99 42,261, 101,997. Passes over two frames: 0, 5, 10 and 8 of 380-400.
- Left for the frame-time work: long regions (bind an 8-line sprite only to the large sprites its box meets,
  or split a region's work), and the waiting itself (the game's logic could run in it).
