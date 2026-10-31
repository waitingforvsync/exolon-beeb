# CPC Exolon: how a zone's background is made

The zone set-up (`&126E`-`&12F7`), the placement lists, the object scripts and their interpreter (`&3CDD`), the
block plotters, the block sets and the two cell maps, from the code of the CPC disc version. Checked in the
harness (`tools/cpc.py`): `tools/zonemodel.py` builds every zone from the data alone and matches the CPC's own
drawing of all 125 zones byte for byte, screen and both cell maps. Scripts are in `work/zones/` (git-ignored).
Anything not checked is marked *unverified*. 2026-10-31.

## Summary
- **A zone is a list of placements**: (row 0-21, column, object 0-61), `&FF` ends. 1,319 placements in 125 zones
  (3-21 a zone), 4,082 bytes. 103 placements start left of the screen (columns 230-251, read as -26 to -5).
- **An object is a script of 2-byte × 8-line blocks** on the Spectrum's character grid, run by `&3CDD`. The
  bytecodes: a block (`&00`-`&60`), moves, newlines, loops, sub-scripts, repeats, a block-set switch, and the
  values the cell maps get. `&CF`-`&E0`'s Spectrum attributes do nothing on the CPC.
- **Every zone is a tile map, one block a cell.** The zone is drawn by whole-cell stores only, never XOR and
  never part of a cell, on the 32 × 22 grid. A cell written twice (738 times in all zones) just takes the later
  block. Blocks left of column 0 or right of column 31 are dropped whole.
- **445 distinct blocks** (16 bytes each, 7,120 bytes) make all 125 zones; 27-161 in one zone (73 on average).
  ZX02: 3,421 bytes as CPC bytes, 3,205 dithered to BBC bytes in column order.
- **Stars come first**: 66 random one-pixel stars (three a row) are stored before the placements, which overwrite
  them. They follow from the generator's seed, which the BBC must keep in step (66 or more calls).
- **Two cell maps**, 32 a row. `&B700`: `&FF` lets the player and 16-line sprites show in the cell, 0 hides them
  (every scenery block is 0 but the planets and a few others). `&BA00`: 0 open, 1 solid, 3 a gun, 13 a missile
  launcher; at set-up, values 2-17 mark special cells, which are listed by kind for the object routines.
- **The barrier** (10 zones) is a column of one block stored under its emitter down to the floor.
- **In play the grid changes only a whole cell at a time**: thruster flames, guns firing, burning mines, and
  objects erased whole. Under 1 block a pass on average; each change can be a new tile number in the map.
- **Drawing a zone takes 190-273 ms** of the CPC's time (median 230), of which 74 ms clears the screen.

## Conventions
- Addresses are the running game's, in hex as `&1234`. "Code immediate" means a value held in an instruction's
  operand (the code modifies itself); its address is the operand's.
- A **cell** is the Spectrum's character: 2 CPC bytes (4 MODE 0 pixels) × 8 lines. **Row** 0-23 (0-21 the
  playfield, 22-23 the status) and **column** 0-31. The cell maps index a cell as `row × 32 + column`.
- x is in MODE 0 pixels (0-127), y in screen lines (0-191). A cell's top-left pixel is (4 × column, 8 × row).
- The screen is one buffer at `&C000`, 64 bytes a line: line y, byte b is at `&C000 + (y AND 7) × &800 +
  (y >> 3) × 64 + b`. A cell's line l is at `&C000 + l × &800 + row × 64 + 2 × column`.
- Times are the CPC's microseconds as `tools/cpc.py` charges them (`time_passes`); a frame is 19,968 µs.
- "Model" means `tools/zonemodel.py`; "the check" means its `--check` against the harness.

## The placement lists

| Address | Size | Meaning |
|---|---|---|
| `&490E` | 125 words | Zone n's list at `(&490E + 2n)`. Zone 0's at `&4A08`; the lists follow each other in zone order to `&59F9` |
| list | 3 bytes an entry | row, column, object; `&FF` ends the list |

| Field | Range | Notes |
|---|---|---|
| row | 0-21 | the object's origin; its script may move up from it (object 2 draws from row - 2) |
| column | 0-31, 230-251 | 8 bits; 230-251 is -26 to -5, an object that starts off the left edge and comes on screen |
| object | 0-61 | 57 used; 8, 9, 18, 56 and 57 never placed |

- 1,319 placements, 3-21 a zone; the lists are 4,082 bytes (with their 125 `&FF`s), the table 250.
- `&12FA` holds the zone (0-124). `&12FB` is the word-table lookup (`HL = (BC + 2A)`), shared with the scripts'
  table.
- Nothing is placed in rows 22-23 and no block lands below row 21 (the check, and the model's count: 0 of
  28,159 block writes).

## The zone set-up, `&126E`-`&12F7`
Called at the start of a game (`&06C0`) and at each zone change (`&1027` sees x = `&80`, `&104C` adds one to
the zone; `&125F` runs the set-up from the main loop). In order:

| Step | Code | What |
|---|---|---|
| 1 | `&126E`-`&127B` | Zeroes the pass-counter word `&3987`, `&1F84`, `&078C` (invulnerability), `&3984` |
| 2 | `&3F10` | Zeroes `&3FFE`-`&490D` (2,320 bytes): the sprites' save areas |
| 3 | `&1B69`, `&1B5B` | `&B700`-`&B9BF` to `&FF`, `&BA00`-`&BCBF` to 0 (704 bytes each: 32 × 22) |
| 4 | `&1252`-`&2D0D` | Resets the object routines' tables: `&1239`, `&1E12`, `&22BA`, `&256A`, `&27A3`, `&2B1B`, `&2C16`, `&3234`, `&2CFD` to 0; `&1EDA` to 1, `&1D7F` to 2, `&2975` to `&5F` (these are lists 5, 3 and 10: their state bytes start at those values) |
| 5 | `&3082` | `&3063`-`&306E` (list 14) to 1 |
| 6 | `&3E0C` | Clears the playfield, rows 0-21 (176 lines of 64 bytes) |
| 7 | `&2FF6` | The stars (below) |
| 8 | `&12B4`-`&12E4` | Each placement: its collision box (`&219C`), then its script (`&3CDD`) with `&3BD5` = 1, `&3BCF` = 0 and C = 0 |
| 9 | `&12E7` | Ends the collision-box list (`&FF`) |
| 10 | `&1BE0` | The special cells listed by kind (below) |
| 11 | `&2811` | For each list-9 cell, sets up 8 movers and XORs 8-line frame 4 there 8 times: an even count, so nothing shows (agent C's area) |
| 12 | `&336E`, `&2F3D` | Object set-up (agent C's area) |
| 13 | `&38AD` | The barrier (below) |

### The stars, `&2FF6`
- For rows 21 down to 0, three times a row: column = generator AND `&1F`; if that cell's `&B700` is non-zero
  (always so: the map is all `&FF` until the placements) a pen byte = generator AND `&54`, again until non-zero.
  The byte goes into byte 8 of the blank block at `&302E` and that block is stored (mode 1) at the cell.
- So a star is one pixel, the right pixel of the cell's left byte (x = 4 × column + 1) on its line 4, in pen 1-7
  (the bits of `&54` are the right pixel's pen bits 0, 1 and 2). Mode 1 leaves both maps alone, so a star's
  cell stays open (`&B700` = `&FF`, `&BA00` = 0).
- 66 stars a zone, some on the same cell; the placements overwrite those under scenery (2,500 of the 8,250 in
  all zones), so a star shows only in a cell no block was written to. Writing the blank block (the font's space)
  over a cell removes its star: "never written" and "written blank" differ.
- The generator (`&3AE7`): seed = (seed + 7) × 13, and it returns **the caller's A XOR the new seed's high
  byte**, not a byte of the seed alone. Here A is `&C5` at the first call (left in A' by `&3E0C`'s last
  `&3E38`), 0 for every later column, `&FF` (the `&B700` cell) for each star's first pen and 0 for any retry.
  The model does exactly this and its stars match the CPC's in all 125 zones, with the title's seed and with
  125 other seeds poked into `&3B02` at `&126E`.

## The object scripts and the interpreter, `&3CDD`
`&1305` is a table of 62 words, one script an object (`&1381`-`&1B5A`, 2,010 bytes; table and scripts 2,134).
`&3CDD` runs a script from HL with the position in D (row) and E (column). Each byte:

| Byte | Operands | Meaning |
|---|---|---|
| `&00`-`&60` | | Plot block n of the current set at (D, E) through the patched CALL `&3CE4`; E + 1 |
| `&61`-`&8F` | c | Move: D + (byte - `&78`) (-23 to +23 rows), E + c (8 bits) |
| `&90`-`&CE` | | Newline: D + 1, E + (byte - `&AF`) (-31 to +31) |
| `&CF`-`&DE` | | Spectrum ink: C = (C AND `&38`) OR ink, `&D7`-`&DE` with BRIGHT (`&40`). No effect on the CPC |
| `&DF` | r, c | Move to row r, column c |
| `&E0` | a | C = a (a Spectrum attribute byte). No effect |
| `&E1` | n | Loop start: the body to the matching `&E2` runs n times (0 is 256). Pushes HL and BC, so loops nest |
| `&E2` | | Loop end |
| `&E3` | lo, hi | Run the script at hi:lo; D, E, B and C restored after (the block set and map values are not) |
| `&E4` | n, b | Block b n times across (E + 1 each); through the patched CALL `&3D71` |
| `&E5` | n, b | Block b n times down (D + 1 each); through the patched CALL `&3D83` |
| `&E6` | lo, hi | The block set: the word at `&3BA1` (code immediate in `&3B92`'s `LD BC,&69DD`) |
| `&E7` | | Block `&20` of the font (`&69DD`, the space: blank) through the patched CALL `&3DAF`; E + 1. The set is restored after |
| `&E8` | v | The `&BA00` value mode 0 writes (`&3BD5`, code immediate) |
| `&E9` | | The `&B700` value mode 0 writes (`&3BCF`, code immediate) = 0 |
| `&EA` | | The same = `&FF` |
| `&EB` | v | If the plot mode is 0: `&BA00` at (D AND 31, E AND 31) = v, nothing drawn |
| `&EC`-`&FF` | | End of script (`&FF` in every script) |

- E wraps at 8 bits, so a script that starts at column 230 runs on to 0, 1, ... and is drawn from there.
- A block number is doubled in 8 bits before it's scaled (`ADD A,A`), so block n is at `set + 16n` for n < 128
  and `set + 16n - 4096` above. Only `&E4`/`&E5`'s operand could exceed `&60`; none does.
- What the scripts use (each script and sub-script once): 969 blocks, 178 newlines, 38 moves, 543 attribute
  codes, 64 `&E6`, 69 `&E8`, 7 `&EA`, 1 `&E9`, 4 `&EB`, 4 `&E7`, 21 `&E3`, 10 loops, 2 `&E4`, 1 `&E5`, 1 `&E0`.
  No object script uses `&DF` (the title and status scripts do).
- 11 sub-scripts: `&1484`, `&14A3`, `&14C3`, `&14E3` and `&1AAC`-`&1B0B` are the rock pieces (objects 6-9,
  56-59) that the rock floors (10, 14, 60, 61) are made of; `&154E`, `&1927`, `&19C2`.
- Every object's script sets its block set before its first block (checked over all 62), so nothing depends on
  the set left by the previous object.
- **The attributes are Spectrum leftovers.** C is never read by a plotter (each pushes BC and uses C as its line
  count). The model ignores them all and matches every zone. Elsewhere C is set from the generator for
  animated blocks (`&1CC9`, `&1E99`: AND 7, OR `&42`, a random bright ink) and `&1EF9` reads the Spectrum's
  attribute memory (`&5800` + the cell) into its script's `&E0`: both have no effect on the CPC.

### The plot modes, `&2709` and `&26F2`
`&26F2` with A = 0-4 patches the interpreter's four plot CALLs (`&3CE5`, `&3D72`, `&3D84`, `&3DB0`) from the
table at `&2709`. Its callers set 3 or 4 for one script and then 0 again.

| Mode | Routine | Writes | Column test | `&B700` | `&BA00` | Used for |
|---|---|---|---|---|---|---|
| 0 | `&3B92` | store | columns 32-63, 224-255 skipped | `&3BCF` | `&3BD5` | **Every zone**, the title, high score and bonus screens, the score; called directly by `&1E7C` and `&38AD` |
| 1 | `&3BDB` | store | none | - | - | Stars, the status digits, the high score text, the thruster flames (`&1CAE`) |
| 2 | `&3C0E` | XOR | none | - | - | The guns' muzzles (`&1CEF`) |
| 3 | `&3C43` | XOR | as mode 0 | `&FF` | 0 | An object destroyed (`&20F7`); a mine set off (`&1EF9`); each block also spawns 2 debris (`&220E`) |
| 4 | `&3C94` | XOR | none | `&FF` | 0 | A pick-up taken (`&263C`) |

- The block set for all five is the word at `&3BA1`. Mode 0 holds it as the operand of its own `LD BC`; the
  others `LD BC,(&3BA1)`. The image starts with `&69DD` there.
- The column test is `BIT 5,E`: columns 32-63 and 224-255 return at once, drawing nothing and touching neither
  map. Columns 64-223 aren't tested (`SLA E` would wrap them onto the screen) but no script reaches them. In all
  zones 7,639 block plots are dropped by the test, none at 64-223.
- Rows: line l of row r is reached by adding 8 to the address's high byte until it carries, so a block is 8
  lines for rows 0-31. Rows past 23 would write the maps' `&B700` value into `&BA00`'s range and the `&BA00`
  value into the pixel-swap table at `&BD00`; no script does.
- Mode 0's map writes go to `&B700 + (row × 32 + column)` and `&BA00` at the same offset (the screen address of
  the cell's top line, halved).

## The block sets
A block is 16 bytes: line 0's left byte, line 0's right byte, line 1's left ... line 7's right. MODE 0 bytes:
the left pixel's pen in bits 7, 3, 5, 1 (pen bits 0-3), the right pixel's in 6, 2, 4, 0 (`cpc.mode0_pens`).
The sets lie end to end from `&6BDD` to `&921C`; each set's size below is up to the next.

| Set | Blocks | Used by zones | Elsewhere |
|---|---|---|---|
| `&69DD` | the font: characters `&20`-`&5A` at `&6BDD`-`&6F8C` (blocks 0-`&1F` below it are other data) | block `&20` (space) by `&E7` | text: title, status, high score, bonus |
| `&6F8D` | 34 | 23 (0-20, 27, 28) | 21-26 the thruster flames (`&1CAE`); 29-32 a burning mine (`&1E7C`) |
| `&71AD` | 42 | 42 | |
| `&744D` | 20 | 20 | high score screen |
| `&758D` | 32 | 18 (0-15, 18, 19) | 16-31 the guns' muzzle frames (`&1CEF`) |
| `&778D` | 20 | 16 (0-3, 8-19) | |
| `&78CD` | 20 | 20 | |
| `&7A0D` | 31 | 31 | |
| `&7BFD` | 42 | 42 | |
| `&7E9D` | 12 | 12 | |
| `&7F5D` | 8 | 8 | the pick-ups |
| `&7FDD` | 20 | 20 | |
| `&811D` | 25 | 25 | |
| `&82AD` | 18 | 18 | high score screen |
| `&83CD` | 29 | 29 | |
| `&859D` | 22 | 22 | |
| `&86FD` | 50 | | the EXOLON logo (script `&0491`): title, high score, bonus |
| `&8A1D` | 3 | 3 | |
| `&8A4D` | 19 | 19 | |
| `&8B7D` | 29 | 29 | |
| `&8D4D` | 17 | 17 | |
| `&8E5D` | 8 | | the bonus screen (script `&380B`) |
| `&8EDD` | 21 | 21 | |
| `&902D` | 19 | 19 | |
| `&915D` | 12 | | the bonus screen's border (script `&3758`) |
| `&302E` | 1 | the star (byte 8 set per star) | |
| `&38E5` | 1 | the barrier | |

- **All zones' backgrounds use 456 (set, block) pairs, 445 distinct patterns** (9 pairs repeat another's data;
  one pattern is blank, drawn as the font's space and as `&7BFD` block 27). 7,120 bytes.
- **ZX02** (Baron's transform): the 445 as CPC bytes in row order 7,120 → 3,421; in column order (each block's
  left byte's 8 lines, then the right's) 3,351; dithered to BBC MODE 2 bytes (plan's colour rule) in column order
  3,205. The whole region `&6F8D`-`&921C` (every set) 8,848 → 4,051; the font 944 → 334.
- **One zone** needs 27-161 distinct blocks (mean 73.2), plus the 7 possible stars and its animations' blocks:
  at most 2,576 bytes of tiles, so a zone's tiles fit a byte's numbering.
- The zone data as stored (the script table and scripts `&1305`-`&1B5A`, the zone table and lists
  `&490E`-`&59F9`, 6,466 bytes) packs to 4,046. Precomputed tile maps would be 88,000 bytes (125 × 704) and
  about 11,000 packed (four blocks of 22,000: 2,885, 2,753, 2,780, 2,607), so running the scripts at zone
  entry is the smaller form.

### Overlaps
- Within a zone, a cell is written by two different blocks 738 times in all (always a later placement's block
  over an earlier's; never the same block twice). Both are whole-cell stores, so the cell is the later block.
- The barrier (`&38AD`) is stored after the placements, over stars only (it stops at the first cell whose
  `&BA00` isn't 0).
- No XOR, no part of a cell, nothing off the grid: **a tile map of one tile number a cell is exact**, with the
  placements run in order (last write wins), stars first.
- The objects that are erased in play (the ten with collision boxes and the two pick-ups) are never overwritten
  by a later placement (checked over all zones), so XORing their script off leaves their cells blank.

## The cell maps, `&B700` and `&BA00`
Each is 704 bytes (32 × 22), `row × 32 + column`; the code reserves `&300` for each. The set-up clears only the
704: `&B9C0`-`&B9FF` (rows 22-23 of `&B700`) stay 0 from the image, so sprites are clipped out of the status
rows, and `&BCC0`-`&BCFF` is spare. They are filled by the set-up's clears and by modes 0, 3 and 4.

### `&B700`: where sprites show

| Value | Meaning | Written by |
|---|---|---|
| `&FF` | the player's plotter (`&07D9`) and the 16-line plotter (`&0B5F`) draw in this cell | the set-up's clear; mode 0 after `&EA`; modes 3 and 4 |
| 0 | those plotters draw nothing in this cell | mode 0 (the default: `&12DA` sets `&3BCF` = 0 before each object, `&3B25` before the score) |

- **So scenery hides sprites**: the player, the 16-line objects and the popups are cut away, a whole cell at a
  time, wherever a block was stored with `&B700` = 0, which is every scenery block but those after an `&EA`
  (objects 3, 4, 30, 35, 36, 37 and 8 cells of 29: the planets and the like; 1,107 block writes of 28,159). A
  blank block stored with 0 is an invisible screen in front of the sprites (`&7BFD` block 27, 29 cells; the
  font's space after `&E9`, 88 cells).
- Checked (`work/graphics/mask_check.py`): in zone 0, plotting 16-line frame 16 and player frame 5 over scenery
  changed only bytes in cells whose `&B700` is `&FF` (0 of 6, 56, 2, 3, 4 and 88 changed bytes lay in a 0 cell).
- How: before XORing, each plotter ANDs the `&B700` cells under the sprite (4 or 5 rows by 4 cells for the
  player, 2 or 3 by 3 for the 16-line objects); if any is 0 it ANDs every byte of its shifted buffer with the
  value of the cell that byte falls in (`&0A18`, `&0CD5`, masks patched into the code). The masked buffer is
  what's saved, so the next erase matches.
- The 8-line plotter (`&2020`), the shot (`&10F5`) and the guns' sparks (`&1D9A`) don't look at `&B700`: they
  XOR over anything.
- Read also by `&2FF6` (stars; always `&FF` then).

### `&BA00`: what the cell is

| Value | Meaning |
|---|---|
| 0 | open: nothing to stand on or bump into |
| 1 | solid (the default for every scenery block: `&12D5` sets `&3BD5` = 1 before each object) |
| 2-17 | at set-up only: a special cell, written by `&E8 v` or `&EB v`. `&1BE0` lists it and replaces the value |
| 3 | after set-up: a gun's muzzle, while the gun stands (`&1CEF` tests it) |
| 13 | after set-up: a missile launcher (`&2F3D`, `&2F6E` test it) |

**`&1BE0`'s lists.** For each cell of value v ≥ 2 it appends (column, row) to list v and gives the cell the
list's own value. The descriptors are 6 bytes at `&1C42 + 6v`: list address, write pointer, stride (2, or 3 with
a state byte), new cell value.

| v | List | Stride | Cell becomes | Objects | Cells (zones, most in one) | Used by |
|---|---|---|---|---|---|---|
| 2 | `&1CE3` | 2 | 0 | 1, 2, 28 | 101 (42, 5) | `&1CAE`: thruster flames |
| 3 | `&1D7F` | 3 | 3 | 5, 44 | 37 (33, 2) | `&1CEF`: gun emplacements |
| 4 | `&1E5F` | 2 | 0 | 11, 17, 43 | 341 (50, 14) | none: unused |
| 5 | `&1EDA` | 3 | 1 | 12 | 53 (24, 6) | `&1E7C`: mines |
| 6 | `&262A` | 2 | 1 | 17 | 70 (35, 2) | `&25B4`: teleport pads |
| 7 | `&26EC` | 2 | 0 | 19 | 48 (48, 1) | `&263C`: ammo pick-up |
| 8 | `&26EF` | 2 | 0 | 20 | 38 (38, 1) | `&263C`: grenade pick-up |
| 9 | `&2855` | 2 | 0 | 21, 39 (`&EB`) | 48 (33, 2) | `&2811`, `&2732`: spore sources |
| 10 | `&2975` | 3 | 1 | 22 (`&EB`) | 46 (27, 3) | `&291F`, `&2990`: popups (32-line frame 24) |
| 11 | `&2AC9` | 2 | 0 | 26, 45 | 56 (33, 4) | `&2A87`: missile launcher barrels |
| 12 | `&2C71` | 2 | 1 | 29 | 5 (5, 1) | `&2C30`: the exoskeleton booth |
| 13 | `&2F69` | 2 | 13 | 31 | 13 (13, 1) | `&2F3D`, `&2F6E`: the homing-missile launcher |
| 14 | `&3063` | 3 | 0 | 26, 45 | 92 (33, 6) | `&303E`: launcher bonus cells |
| 15 | `&352A` | 2 | 0 | 42 (`&EB`) | 5 (5, 1) | `&34FF`: the arc generator |
| 16 | `&3808` | 2 | 0 | 42 (`&EB`) | 5 (5, 1) | `&352D`: the level end |
| 17 | `&38E2` | 2 | 1 | 1 | 10 (10, 1) | `&38AD`, `&38F5`: the barrier |

- The names are agent C's (`docs/cpc-objects.md`), where the lists' room and what each object does are.
- Objects 22 and 39 draw nothing: they only mark a cell with `&EB` (invisible markers).
- Objects 41, 48, 49 and 51 are empty scripts (a lone `&FF`) on the CPC, though placed in zones 22, 25, 26 and
  66; the Spectrum draws them (decisions O7). Restoring them would need CPC blocks the disc doesn't have.
- The largest list (14 entries of list 4) ends exactly at `&1E7B`, before `&1E7C`'s code.

**Readers of `&BA00`**: the player's floor and wall tests (`&0EF1`, `&0F20`, `&0F4C`, `&0F77`, through
`&0ED8`), the shot (`&11B5`), objects against walls (`&2077` right, `&2097` left, `&20B7` below, `&20D7` above),
the guns (`&1D04`), the homing-missile launcher (`&2F4D`, `&2F79`), the barrier (`&38D0`), `&EB` (`&3DF2`), and the title's
twinkles (`&0208`: a twinkle starts only where four cells are all 0, so not on the text). `&0ED8` turns a pixel
position into a cell: `&BA00 + (y >> 3) × 32 + (x >> 2)`.

## The collision boxes, `&219C`
At each placement, before its script, `&219C` looks the object up in `&21DB` (5 bytes an entry: object, column
offset, width, row offset, height; signed offsets; bit 7 ends) and, if found, appends 7 bytes at IX (from
`&214C`): left column, right column (exclusive), top row, bottom row, column, row, object. `&12E7` ends the
list with `&FF`; a destroyed object's entry becomes `&80`.

| Object | Box (columns, rows from the origin) |
|---|---|
| 5 | -1..+7, -2..+3 |
| 13 | -3..+2, -2..+8 |
| 15 | -2..+5, -1..+8 |
| 16 | -2..+4, -2..+6 |
| 18 | -6..+5, +1..+8 (never placed) |
| 21 | -2..+5, -2..+6 |
| 31 | -1..+5, -2..+4 |
| 40 | -1..+5, -2..+6 |
| 44 | -1..+7, -2..+2 |
| 46 | -1..+4, -2..+4 |

At most 5 boxes in a zone (zone 94); the list has room for 11. `&20F7` tests a grenade's cell against the boxes
and erases a hit object whole (mode 3, debris, points by `&3B04`).

## The barrier, `&38AD`
If list 17 has an entry (the emitter, object 1, in zones 35, 39, 41, 50, 62, 68, 92, 110, 114, 116), block 0
of `&38E5` (every line `&55 &AA`: pixels 0, 15, 15, 0, a stripe of bright magenta) is stored with mode 0
(`&B700` 0, `&BA00` 1) from the row under the emitter downwards until the next row's `&BA00` isn't 0. 13-16
cells. The length goes to `&3963`. It isn't redrawn in play (agent C: shot 25 times, it goes). List 17 holds
one entry: a second emitter would overwrite the list's end and the barrier's block (none does).

## In play: what changes on the grid
Measured over every zone (`work/zones/grid_play.py`, 150 passes each with random keys and invulnerability;
18,445 passes of play, zone changes left out):

| What | Routine | How | Blocks | Rate |
|---|---|---|---|---|
| Thruster flames (list 2) | `&1CAE` | mode 1, two cells under the mark, frame (`&1CEE`) 0, 1, 2 a pass | `&6F8D` 21/22, 23/24, 25/26 | 2 a mark a pass, in the 42 zones with marks |
| A gun emplacement firing (list 3) | `&1CEF` | mode 2: each pass XORs the muzzle's frame off and the next on, 8 passes | `&758D` 16-31 (pairs) | a burst of 32 when it fires (generator ≥ `&FA`, about 1 pass in 43) |
| A gun destroyed | `&1CEF` | mode 2: XORs its frame and `&758D` 18/19 off, leaving the cells blank | | once |
| A burning mine (list 5, after it's set off) | `&1E7C` | mode 0 (`&3B92` direct), alternating every pass (`&1ED9` XOR 2) | `&6F8D` 29/30, 31/32 | 2 a mine a pass |
| An object hit by a grenade | `&20F7` | mode 3: its whole script XORed off; maps to `&FF`/0; 2 debris a block | its own | once |
| A mine set off | `&1EF9` | mode 3 over 2 cells of the font's space 5 times: no visible change, maps cleared, 20 debris | | once |
| A pick-up taken (lists 7, 8) | `&263C` | mode 4: object 19's script XORed off | `&7F5D` | once |
| The score | `&3B04` | the script `&3B33`, mode 0, row 23 | font digits | at each score |

- The animation blocks add 26 tiles (`&6F8D` 21-26, 29-32; `&758D` 16-31) to the 445.
- Each change is a whole cell going from one known block to another, or to blank, so the BBC can keep the tile
  map current and redraw the cell from it. The gun's XOR pairs and the XOR erasures always find exactly the
  block they remove (checked for the erasures: no erasable object's cell is overwritten at set-up).
- Mode 0's map writes in play use whatever `&3BCF`/`&3BD5` hold (0 and 1 after the set-up's `&38AD`): a burning
  mine's cells stay hidden and solid. The score's mode-0 writes fall at offsets 750-755 of each map, past the 704 used.

## How long a zone takes
`work/zones/timing.py` single-steps the harness from `&126E` to the first pass for every zone:

| Part | min | median | max |
|---|---|---|---|
| Clears (steps 1-5) | 28,549 µs | 28,549 | 28,549 |
| The playfield cleared (`&3E0C`) | 73,957 | 73,957 | 73,957 |
| Stars (`&2FF6`, the title's seed) | 28,404 | 28,404 | 28,404 |
| Placements | 45,066 | 84,019 | 127,204 |
| Lists, objects, beam | 11,975 | 14,326 | 24,466 |
| **Total** | **189,927** | **230,427** | **272,974** |

That's 9.5-13.7 frames; the whole zone-change pass is longer (the plan measured 268 ms, zone 0 to 1).

## The model, `tools/zonemodel.py`
- `build(mem, zone, seed)` runs steps 3 and 6-13 as above (the clears, the stars from the seed, the scripts
  with the Z80's wraps and tests, `&1BE0`'s lists and conversion, the beam) and returns the tile map, both maps
  and the screen. `image()` renders with the inks at `&3EF0` through `cpc.HWRGB`.
- `--check` starts the harness at each zone with the disc's poke (`&010E`-`&0110` NOPs, `&12FA` = zone), holds
  '1' from the title until `&126E`, takes the seed from `&3B02` there, and runs to the first pass (`&06C3`),
  before anything moves. It compares rows 0-21 byte for byte and both maps' 704 bytes. With the screen
  write-marked, the bytes any sprite plotter (`&07D9`, `&0B5F`, `&2020`) writes during the set-up are left out:
  0 in most zones, 24-48 in 31 zones (`&2811`'s 8-line frame 4, XORed an even number of times, so they'd
  match anyway). The player isn't drawn before the first pass.
- **Result: 125 of 125 zones match**, screen and maps, with the title's seed (`&6512` for every zone) and again
  with a different seed poked for each zone (`--seeds`). A wrong seed gives 83 differing bytes in zone 7, so
  the stars are really compared.

## For the BBC
- Build the tile map by running the placements' scripts at zone entry (the stored form is the smallest), stars
  first, last write wins, columns outside 0-31 dropped. Keep per cell: the tile number, the `&B700` bit and the
  `&BA00` value (0, 1, 3 or 13, with the lists made as `&1BE0` does).
- "Never written" (a star may show) and "written with the blank block" differ; both draw as tile 0 unless a star.
- Sprites through the player's and 16-line plotters show only in `&B700` = `&FF` cells: over black, stars, and
  the few `&EA` objects (planets). Everywhere else they're cut away by whole cells, so the Teddy Boy plotter's
  "non-empty tile" case is only those few tiles; most scenery is a mask of zeros for the sprite.
- The attribute bytecodes, the colour in C and the `&5800` read are Spectrum leftovers to drop. The generator
  calls are not: the stars' 66 or more calls (and A's value at each) must be kept for lockstep.
