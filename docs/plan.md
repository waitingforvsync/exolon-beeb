# Exolon for the BBC Micro: plan

A version of the Amstrad CPC disc version of *Exolon* (Raffaele Cecco, Hewson, 1987; this disc is Aragorn's
1995 conversion of the tape) for a BBC B with sideways RAM: MODE 2 at the CPC's screen size, its colours
dithered, written in Baron. Everything under "The CPC version" was measured from `docs/exolon.dsk` on
2026-10-31 with `tools/cpcdsk.py`, `tools/cpc.py` (the original running on kosarev's Z80, as Chase H.Q.'s
reference does), SkoolKit's disassembler and Baron's ZX02 transform. Anything marked "Phase 1" is a reading of
the code still to be confirmed. The BBC's sizes and speeds are estimates until Phase 2 measures them.

## Verdict

**Feasible on a BBC B with two banks of sideways RAM, at a steady 25 passes a second where the CPC averages
20.9, with Teddy Boy's sprites.**

- The CPC's screen is 64 bytes × 24 rows (128 × 192 pixels), one buffer at `&C000`. MODE 2 takes it as it is:
  R1 = 64, 512 bytes a character row, 12K a screen. CPC MODE 0 bytes have the BBC MODE 2 layout.
- Every zone is built on the Spectrum's character grid from 2-byte × 8-line blocks: a 32 × 22 tile map. That's
  what Teddy Boy's method needs: stores straight over empty tiles, composed from the tile data elsewhere.
- The game is deterministic and never waits for vsync. It pads every pass to its worst case to hold its speed,
  and still averages 2.39 frames a pass; nearly half of a typical pass is padding. It stalls about 100 ms each
  time the player turns round.
- The data packs well with ZX02 (the graphics region to 36%). The code's size, and so whether one bank could
  do, is the open question.

## The CPC version

### The disc
| File | Loads at | Bytes | What it is |
|---|---|---|---|
| `EXOLON.BAS` | | 733 | BASIC: MODE 1, `MEMORY &1FFF`, loads `EXOLON.LDR` and `FADEIN.BIN`, offers pokes, `CALL &BE80` |
| `EXOLON.LDR` | `&BE80` | 196 | Loads the four files below, moves `&C000`-`&D1CE` to `&A001`, `JP &0100` (or the pokes) |
| `EXOLON.DAT` | | 1,280 | The loader's source (Maxam), with the pokes' addresses |
| `FADEIN.BIN` | `&2000` | 35 | Copies the loading screen from `&4000` to `&C000` in a scattered order |
| `FADEIN.DAT` | | 512 | Its source |
| `EXOLON.SCR` | `&8000` | 6,172 | The loading screen, packed, with its own unpacker (run at `&8000`, unpacking to `&4000`) |
| `EXOLON.1` | `&0100` | 27,357 | Code and data, `&0100`-`&6BDC`; entry `&0100` |
| `EXOLON.2` | `&6BDD` | 13,348 | Data, `&6BDD`-`&A000` |
| `EXOLON.3` | `&C000` → `&A001` | 4,556 | Data, `&A001`-`&B1CC` |

The pokes give a few variables: ammo `&1159`, grenades `&1F7A`, lives `&2A25`, invulnerability `&0779`,
start zone `&12FA` (0-124).

### Start-up and the hardware
- `&0100`: `DI`, SP = `&0100`. `&3E90` sets the CRTC (R1 = 32, R2 = 43, R6 = 24, R7 = 29, start `&C000`),
  MODE 0, a black border and a fixed palette of 16 inks (table at `&3EF0`). No firmware, no interrupts, and
  nothing reads vsync.
- One screen: 22 rows of playfield over 2 rows of status (ammo, grenades, points, lives, zones).
- Tables made at start-up: each screen line's address (`&BE00` high, `&BF00` low, 192 lines) and a byte's two
  pixels swapped (`&BD00`).
- Keys: O, P, Q, A and SPACE (left, right, up, down, fire; the title offers to redefine them), read from the
  keyboard matrix into `&3AA5` and decoded at `&0D20`. A Spectrum keyboard read (`IN A,(&FE)`) survives at
  `&0E83`: the code came from the Spectrum version.
- Random numbers: `&3AE7`, a 16-bit generator (seed' = 13 × (seed + 7), at `&3B02`; the result is the caller's
  A EOR the new seed's high byte: `docs/cpc-loop.md`). The R register isn't read, so the
  game's play follows from its keys alone.
- Sound: the AY written directly. `&63AF` services 16 slots of 16 bytes at `&6A1C` and is called three times
  a pass (Phase 1).

### Zones
- 125 zones. Zone n's list of placements is found through a word table at `&490E`: entries of row (0-19),
  column (0-31) and object, ending `&FF`. 1,319 placements of 57 objects in all, 4,082 bytes.
- An object is a script of blocks (scripts through a table at `&1305`, `&1381`-`&1B43`), drawn by `&3CDD`;
  `&3BF0` stores a block of 2 bytes × 8 lines. A column is 2 CPC bytes (4 pixels): the Spectrum's character.
  Solid objects also get a collision box (`&219C`, sizes in a table at `&21DB`).
- So the background is a grid of 32 × 22 cells of 16 bytes (Phase 1: that no script draws off the grid, and
  how many distinct blocks there are).

### The main loop, `&06C3`-`&0788`
- About 55 calls a pass, then a pass counter at `&078B`. Each object's routine moves it and plots it.
  `&11C5` is called five times a pass, `&63AF` three times (Phase 1: what each is).
- **Every pass is padded to its worst case.** `&2B9C` plots a dummy 16-line object 6 - n times (n counted in
  `&2BB1`) and `&2B88` a dummy 8-line object 16 - n times (`&2B9B`). With no clock, that's what holds the game's
  speed steady whatever is on screen.

### Drawing
- **XOR, no masks.** The zone's background is drawn once and never restored: an object's old image is XORed
  off and its new one on. Over black, most of the screen, that's exact; over scenery the pens mix. Pen 0 in a
  sprite changes nothing, so it's transparent.
- `&07D9`, the player: 24 frames of 6 bytes × 32 lines (192 bytes each) at `&93CD`. When the player turns
  round, `&0E04` mirrors all 4,608 bytes in place through the swap table.
- `&0B5F`: 16-line objects, 4 bytes wide (64 bytes a frame, at `&A68D`).
- Both shift an odd x by a pixel at run time (`AND &AA : RRCA` and so on) into a buffer a byte wider at `&0A7F`,
  then XOR the old image off and the new on, line by line, to keep the flicker down. The data is read by
  pointing SP at it and popping.
- `&2020`: 8-line objects, 3 bytes wide, pre-shifted (two copies of 24 bytes at `&921D`).
- Collisions seem to read a coarse map at `&B700` (the screen address halved) and the boxes from `&219C`, not
  the screen (Phase 1).

### Speed
`tools/cpc.py` single-steps the Z80 and charges each instruction the CPC's microseconds. Three seeds, 2,970
passes of random play with the game's keys (walking, jumping, firing, turning, dying, two zones):

| Per pass | Median | 90% | 99% | Max |
|---|---|---|---|---|
| The pass | 46.3 ms (2.32 frames) | 54.6 ms | 102.1 ms | 268.1 ms |
| Its work, padding left out | 25.9 ms | 38.3 ms | 86.5 ms | 245.5 ms |

- **20.9 passes a second** (from the mean pass). 74% of passes take more than 2 frames, 5.6% more than 3.
- The longest: the zone change (268 ms, zone 0 to 1) and the player turning round (145-155 ms a pass, against
  about 46: the mirroring).
- The player walks 1 pixel a pass, the finest step MODE 0 has. A jump rises 4, 4, 2, 2, 2, 1, 1, 1, 1, holds 4
  passes, and falls 1, 1, 1, 1, 2, 2, 2, 4, 4: 22 passes (`docs/cpc-player.md`).

### Sizes, and ZX02
| Block | Bytes | ZX02 |
|---|---|---|
| The whole image, `&0100`-`&B1CC` | 45,261 | |
| `&0100`-`&6648`: all the code, and data | 25,929 | 14,170 |
| of which Z80 code reached from `&0100` | 10,277 at least (one computed jump, at `&64A7`, isn't followed) | |
| of which the zones' placement lists | 4,055 | 2,500 |
| `&6649`-`&B1CC`: data (`EXOLON.2`, `EXOLON.3` and the end of `EXOLON.1`) | 19,332 | 6,969 |

## The Spectrum original (D24)

The CPC version was ported from it: a Spectrum keyboard read survives in the CPC code, and the two main loops
make the same calls in the same order. Measured 2026-10-31 from `docs/Exolon.tzx` (git-ignored):
- The tape ("Hewson II" loader) loads through SkoolKit's simulated LOAD to `build/spec/exolon.z80`: the loader
  decrypts itself, loads a 4K block (the loading screen's countdown) and the 37,538-byte game, moves it up to
  `&6D60`-`&FFFF`, sets SP = `&6D5E`, `EI`, `JP &6D60`.
- `tools/spectrum.py` runs it: the 48K ROM, an interrupt a frame, the keyboard. The title offers keyboard,
  Interface 2 or Kempston.
- Its main loop is `&75BE`-`&7689`: the CPC's calls in the CPC's order, plus a fixed delay each pass
  (`&B0B7`: an LDIR of 500 bytes, ROM onto ROM, about 10,500 T), and the same padding (`&9E85`, `&9E99`).
- Uncontended, a pass takes a median 1.90 frames, about 25 passes a second over 600 passes of play. Contended
  memory would slow it somewhat. The CPC averages 20.9, so the BBC's 25 (D8) is about the original's pace.
- `tools/cpc2spec.py` maps 111 CPC routines to their Spectrum twins and lists the constants that differ: the
  mechanics are compared routine by routine in the specs, and any difference that affects play goes to Rich.

## The BBC version

### Display (D9)
- MODE 2 timing (ULA `&F4`, R0 = 127, R3 = `&28`, R9 = 7) with the CPC's size: **R1 = 64, R2 = 90**
  (exhale's `98 - (80 - 64) / 2`), R6 = 24, R7 = 31 (`35 - (32 - 24) / 2`).
- **One screen, 12K at `&5000`-`&7FFF`**, playfield and status together. Nothing crosses `&8000`. No double
  buffer and no rupture.
- The pass is locked to every second vsync (D8). T1 runs a frame a period and gives the beam's place for the
  plotting order (read from T1C-H, never T1C-L).

### Sprites (D7, D10; P8, P9, P10)
- **The background is a tile map.** In the pause before a zone (D12) its placements are run into a 32 × 22 map
  of tile numbers (704 bytes) and the screen is drawn from it. The tiles are 2 bytes × 8 lines, dithered at
  build time and laid out for the plotters (Teddy Boy's line-planar tiles). The empty tile is 0.
- **Over empty tiles**, under both the old place and the new: the sprite's bytes stored straight, its
  transparent pixels as 0, and zeros over the bytes it left (a blank border in the frames as wide as its
  furthest move a pass, or the vacated strip cleared: whichever measures cheaper).
- **Over a non-empty tile**: `(tile AND mask) OR sprite`, the tile byte from the tile data, never the screen;
  the vacated bytes from the tile data too.
- **Over another sprite**: back to front, the one behind drawn whole and the one in front masked where they
  meet (Teddy Boy's P24).
- **Each screen byte is written once a pass**, so nothing is ever seen erased. Sprites go in order of height
  against the beam, each before the beam reaches its top or after it has left its bottom.
- **XOR for explosions and particles** (D10), as the original draws them.
- Mask when there are the cycles (D10). If a pass can't fit, what gives (an unmasked overlap, an object held a
  pass) is measured and decided then, as in Teddy Boy's D25 and D27.
- **Transparency** (P10): logical 0, as pen 0 in the original. The mask comes from a 256-byte table indexed by
  the sprite byte. Pens 1 and 4 dither with black; their black pixels in a sprite are logical 8 (shown black)
  so they stay opaque. Bit 3 marks opaque pixels otherwise, so a wholly opaque byte skips its mask (Teddy
  Boy's D24, adapted).
- **Shifts and facings** (P5): plotted from pre-shifted frames, made in the pause between screens for the types
  the next screen uses (D12). The player is never mirrored in place: one facing is kept and the plotter
  mirrors the other through a 256-byte swap table (a few cycles a byte, against the CPC's 100 ms stall), or
  similar. Measured in Phase 2.
- **The workload comes from the CPC**: the harness logs every object plotted each pass (which graphic, where),
  and the BBC's plotters are timed over the same passes in jsbeeb.

### Colours (P4)
The palette has 16 inks. Each goes to a BBC colour, or to a checkerboard of the two BBC colours whose average
it is, taking the pair closest in brightness (Chase H.Q.'s D7, Rec. 601 luma). BBC colours: 0 black, 1 red,
2 green, 3 yellow, 4 blue, 5 magenta, 6 cyan, 7 white.

| CPC pens | Colour | BBC | Luma apart |
|---|---|---|---|
| 0 | black | black | |
| 1 | red | black / red | 0.30 |
| 2 | bright red | red | |
| 3 | pink | magenta / yellow | 0.47 |
| 4 | green | black / green | 0.59 |
| 5 | bright green | green | |
| 6 | pastel green | cyan / yellow | 0.18 |
| 7 | sky blue | blue / cyan | 0.59 |
| 8 | bright cyan | cyan | |
| 9 | orange | red / yellow | 0.59 |
| 10 | bright yellow | yellow | |
| 11 | bright white | white | |
| 12 | grey | green / magenta | 0.17 |
| 13 | magenta | blue / red | 0.18 |
| 14 | purple | red / magenta | 0.11 |
| 15 | bright magenta | magenta | |

- Seven pens are plain BBC colours and nine are pairs. There's no plain blue in the palette.
- The dither is baked into the tiles and sprites at build time, fixed to the sprite so it moves with it. The
  palette: logical 0-7 physical 0-7, and 8-15 the same again.

### Frame rate (D8)
- A pass every second frame, locked to vsync: 25 a second, steady, about 20% faster than the CPC's mean.
  79,872 cycles a pass, less the IRQ's.
- The CPC's work, padding left out, has its 90th percentile at 38.3 ms on a Z80 at about 3.5 MHz effective.
  Its XOR pair costs about 12 µs a byte (read, XOR, write, twice). A straight store on the BBC is about 6 µs
  (Teddy Boy's 11-13 cycles), a composed byte 12-16 µs (24-32 cycles). And there's no run-time shift and no
  mirroring stall.
- A pass over budget (a zone change, a death) holds the picture a frame longer.

### Memory (D11, P11)

| Range | Use |
|---|---|
| `&0000`-`&00FF` | The banks' numbers, then `ZA_POOL`; `&FC` the MOS's |
| `&0100`-`&0120` | The stack's sentinel, then the stack (32 bytes) |
| `&0121`-... | Main RAM's code, with no gaps (D20): the IRQ, keys and sound, the main loop and the logic, what must see two banks; placed round IRQ1V at `&204`, `&258` = 2 and an `RTI` at `&D00` |
| ...-`&4FFF` | The workspace (D20): variables, the loader's tables, the tile map, the zone's tiles and sprites unpacked |
| `&5000`-`&7FFF` | The screen (24 rows) |
| `&8000`-`&BFFF` × 2 | Each bank: routines with the data they read (Teddy Boy's rule) |

| Need | Bytes | Basis |
|---|---|---|
| 6502 code | 15,000-19,000 | An estimate: 10,277+ bytes of Z80 × 1.5-1.8, less the padding and run-time shifting; unrolled plotters on top |
| Data, packed | about 12,000-15,000 | The CPC's: 6,969 for `&6649` up, plus the data among the code (Phase 1) |
| The zone's working set, unpacked | Phase 1 | Tile map 704, the zone's tiles, its sprite types shifted |
| Tables made by the loader | about 1,500 | Line addresses, the mask table, the swap table, collision |

- **Two banks** (52,960 bytes with main RAM) hold that with room, if the graphics and zones stay packed and the
  next zone's working set is unpacked in the pause between screens (D12).
- **One bank** (36,576 bytes) needs the code near 15K and a small working set. Phase 1 sizes the data and the
  working set, Phase 3 the code; the case is made then.

### Packing (D11, D12, D16, P12)
- Standard ZX02 throughout (D16), unpacked by `dzx02` as in Teddy Boy and Chase H.Q.: the banks and main
  RAM's code at load, and the next screen's set in the pause between screens: its tile map from the
  placements, its tiles, and its sprite types, shifted.
- Packed in large blocks for the better ratio (D21): many zones' data, or many sprite types, in one stream.
  In the pause the display is blanked, a block unpacks into the screen's 12K, and the next zone's pieces are
  copied out to the workspace before its screen is drawn.
- Measured on the CPC's sprites: the player's 24 frames 4,608 → 869 bytes, the 16-line objects 2,880 → 659,
  as dithered BBC bytes in column order. Column order packs 11% smaller than row order, and dithered packs
  within 5% of the CPC's undithered pens, so the dither goes in at build time.
- 6-bit literals (a MODE 2 byte of colours 0-7 is six bits) measured about 7% on the sprites, where matches
  are 70% of the stream: not worth the slower unpacking (D16).

### Sound (D13)
- The AY's effects re-voiced for the SN76489 (no envelopes, no noise mixed with tone), written by the IRQ at
  50 Hz, which owns port A and the latch (Teddy Boy's rule). The main loop posts requests.

### Keys (D14, D17, D18)
- Z left, X right, `:` up, `/` down, RETURN fire, read by the IRQ. Redefining them moves out of the game into
  a loader program run once before the game loads (later).

### The loading screen (D15)
- `EXOLON.SCR` is a MODE 1 screen in black, bright red, bright green and bright white, 256 × 192 pixels: 64
  bytes × 24 rows, the game's geometry. It goes across exactly in BBC MODE 1 (the CPC's pens 1 and 2 swapped,
  laid out in the BBC's character cells), packed by ZX02, with no dithering.

### How the port gets checked
- **The original is the model** (P6). `tools/cpc.py` runs it: from it, each pass, the game's variables, every
  plot, the AY's writes, and the time.
- **Lockstep**: the same keys into the harness and the BBC build, and the state compared each pass:
  positions, counters, the generator's seed, the collision boxes. No shim is needed: nothing reads a clock or
  R. Logic in py65; anything timed in headless jsbeeb with the real IRQ (Teddy Boy's tools).
- **Screens**: a model of the BBC's screen (the tile map, then the pass's sprites over it, masked) checked
  against the BBC's each pass, as Teddy Boy's `screenmodel.py`; and against the CPC's through the colour map
  wherever nothing overlaps scenery. Beam glitches counted in jsbeeb (Teddy Boy's `beam_glitches.mjs`).

## Phases

### Phase 0: housekeeping
- `git init` (Rich), `build/` ignored. `src/` as Teddy Boy's and Chase H.Q.'s: `boot.6502`, `exolon.6502`,
  `constants.6502`, `memory.6502`, `macros.6502`, `entry.6502`, `irq.6502`. A Makefile: Baron to
  `build/exolon.ssd` with a `-v` listing and symbols. A venv (z80, skoolkit, pillow, py65, numpy). `CLAUDE.md`
  with the rules carried over (jsbeeb only, one machine at a time, Rich commits).

### Phase 1: the spec
- A SkoolKit control file (`cpc/exolon.ctl`) over the code and the data: every routine named and described,
  every data block typed. Follow the computed jump at `&64A7`.
- `docs/cpc-*.md`, the spec: the main loop and each object's behaviour; the player (walking, jumping, ducking,
  firing, grenades, the exoskeleton); the zones, the object scripts and the blocks; the graphics' formats;
  collisions; scoring, lives, ammo and grenades; the sound; the title and define keys.
- Measured: the distinct blocks (tiles) and their packed size; the sprite types each zone uses and their
  sizes (the working set); each object's furthest move a pass (the self-erasing border); the plot log; the
  data's packed sizes; how grenades are thrown.

### Phase 2: display and sprites
- `!BOOT` (banks, the loading screen in MODE 1), the loader, the IRQ (vsync lock, T1 for the beam, keys,
  sound at 50 Hz).
- The pause between screens: the next zone's map, tiles and sprites unpacked and prepared.
- The asset pipeline: dither, tiles, frames with their borders, the opaque mark.
- The zone drawer (map and screen from the placements), the plotters (straight, composed, overlapped, XOR) and
  their order against the beam, timed over the logged passes.
- **Check**: the logged passes drawn well inside 2 frames, every screen byte as the model's, and no sprite
  shown torn, in jsbeeb.

### Phase 3: the game
- The logic from the spec, routine by routine, each checked in lockstep.
- **Milestone 1**: a few zones playable at 25 passes a second (D19).

### After milestone 1 (reviewed then)
- Sound effects, the title, every zone, the loader program that redefines the keys (D18).
- Optimisation reviews, measured as Teddy Boy's were. One bank looked at again with the real sizes.
- Tests on jsbeeb, b2 and real hardware; a Master 128 (`JMP (abs)` and `BIT` timings in the IRQ's latency).

## Risks
| Risk | What decides it |
|---|---|
| The code and working set too big for two banks | Phase 1's data sizes, Phase 3's code |
| Busy passes over 2 frames with masking | Phase 2's timings over the logged passes; then what gives (P9) |
| Sprites torn by the beam | Phase 2's order and checks |
| Code larger than 1.8 × the Z80 | Phase 3's first block |
