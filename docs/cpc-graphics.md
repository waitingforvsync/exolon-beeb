# CPC Exolon: every graphic and how it's plotted

The formats of every graphic in the CPC original, the routines that put them on the screen, the status rows,
and the plotting workload measured pass by pass, for the BBC's display and sprite engine. From the code of the
CPC disc version, checked in the harness (`tools/cpc.py`): every instruction that writes the screen was found by
running it with the screen write-marked, and `tools/plotlog.py` logs every plot. Scripts and PNG sheets are in
`work/graphics/` (git-ignored). Anything not checked is marked *unverified*. 2026-10-31.

## Summary
- **Everything moving is XORed** and nothing is masked by its own shape: pen 0 in a sprite leaves the screen
  alone. There are three sprite plotters: 32-line (`&07D9`, 6 bytes wide: the player and the popups), 16-line
  (`&0B5F`, 4 bytes: aliens, explosions, missiles, the arc) and 8-line (`&2020`, 3 bytes: grenades, debris,
  spores, launcher missiles, small explosions). Two dots: the laser bolt (`&10F5`) and the guns' shots (`&1D9A`).
- **The 32- and 16-line plotters erase and redraw in one call**: they XOR the saved old image off and the new one
  on, line by line, and keep the new image (shifted and clipped) in the object's save area. They shift odd x a
  pixel at run time into a buffer a byte wider (7 × 32 or 5 × 16).
- **They hide sprites behind scenery**: any cell under the sprite whose `&B700` is 0 has the sprite's bytes in
  it zeroed. So the player, popups and 16-line objects show only over black, stars and a few background objects
  (planets). The 8-line plotter and the dots aren't clipped.
- **The 8-line objects are pre-shifted**: two copies of 3 × 8 a frame (even x, odd x), one XOR a call; the
  caller erases and redraws with two calls. Frame 7's odd copy is a different picture (the spore pulses).
- **Facing**: the player's 24 frames are stored facing right and mirrored in place (`&0E04`, 4,608 bytes through
  the pixel-swap table) when he turns.
- **Frames**: player 0-9 walking (5 standing), 3 jumping, 9 falling, 10 ducking, 11 dying, 12-23 the same in the
  suit; 24 is the popup. 16-line: 0 blank, 1-4, 16-27, 37-44 six alien types, 5-9 the big explosion, 10-11 the
  homing missile, 12-15 the title's twinkle, 28-32 the arc, 36 the time-out missile.
- **Workload** (4 zones, 1,599 passes of random play): 21 plots a pass (median), 53 (90%), 218 (max, a grenade's
  debris); 1,040 bytes XORed a pass (median), 1,968 (90%), 5,384 (max), padding left out.
- **Largest move in one plot**: player 1 pixel and 4 lines; popup 8 lines; aliens 4 pixels and 8 lines; homing
  and time-out missiles 2 pixels; debris 4 pixels and 8 lines; spores 1 and 1; launcher missiles 2; the laser 1
  pixel a plot, 5 plots a pass; guns' shots 1 a plot, 2 a pass. So a blank border of 2 bytes and 8 lines covers
  every sprite (the dots are XORed).
- **Pens 1 and 4** (dithered with black on the BBC): 591 of the player's 3,081 opaque pixels (19%), 167 of the
  16-line frames' 2,043, 1,242 of the zone tiles' 8,346.

## Conventions
- Addresses are the running game's, `&1234`. "Code immediate": a value held in an instruction's operand.
- x is in MODE 0 pixels (0-127), y in screen lines (0-191, the playfield 0-175). A sprite's (x, y) is its
  image's top-left: for the plotters, E = x and D = y.
- MODE 0 bytes: the left pixel's pen in bits 7, 3, 5, 1 (pen bits 0-3), the right pixel's in 6, 2, 4, 0
  (`cpc.mode0_pens`): the BBC MODE 2 layout. A byte is 2 pixels; byte b of a line is x = 2b and 2b + 1.
- Graphics are stored row by row, top line first, left byte first, no padding.
- The screen: line y, byte b at `&C000 + (y AND 7) × &800 + (y >> 3) × 64 + b`. `&3E29` gives it from (D, E)
  through the line tables `&BE00` (high bytes) and `&BF00` (low), made by `&0E64` at start-up, plus E >> 1.
- A pass is one trip round the main loop (`&06C3`). "A plot" is one call of a plotter. Bytes plotted count each
  screen byte a call writes (an XOR's read-modify-write once).

## The palette
`&3E90` sets MODE 0 and the 16 inks from `&3EF0` (hardware numbers), and a black border. Nothing changes them
in play.

| Pen | Ink | Colour | Pen | Ink | Colour |
|---|---|---|---|---|---|
| 0 | 20 | black | 8 | 19 | bright cyan |
| 1 | 28 | red | 9 | 14 | orange |
| 2 | 12 | bright red | 10 | 10 | bright yellow |
| 3 | 7 | pink | 11 | 11 | bright white |
| 4 | 22 | green | 12 | 0 | grey |
| 5 | 18 | bright green | 13 | 24 | magenta |
| 6 | 25 | pastel green | 14 | 5 | purple |
| 7 | 23 | sky blue | 15 | 13 | bright magenta |

## Every routine that writes the screen
Found by write-marking `&C000`-`&FFFF` in the harness (`work/graphics/writers.py`, `writers2.py`): the title for
4,000 frames, define keys, a game of 3,000 passes of random play, a game to its game over, and zone 99's play.
Every write came from these (the address is the writing instruction's):

| Routine | Writes at | What | How | Bytes a call |
|---|---|---|---|---|
| `&07D9` | `&0923`-`&0977` | 32-line sprites: the player, popups | XOR old off, new on, line by line | 448 (7 × 32 twice) |
| `&0B5F` | `&0C41`-`&0C7E` | 16-line sprites | the same | 160 (5 × 16 twice) |
| `&2020` | `&204D`-`&2056` | 8-line sprites | one XOR | 24 |
| `&10F5` | `&1104`-`&111A` | the laser bolt | XOR | 2 (3 at odd x) |
| `&1D9A` | `&1DAD`, `&1DB4` | a gun's shot | XOR | 2 |
| `&3B92` | `&3BB6`, `&3BBA` | block, mode 0 | store, maps | 16 |
| `&3BDB` | `&3BFC`, `&3C00` | block, mode 1 | store | 16 |
| `&3C0E` | `&3C30`, `&3C35` | block, mode 2 | XOR | 16 |
| `&3C43` | `&3C69`, `&3C6E` | block, mode 3 | XOR, maps cleared, debris | 16 |
| `&3C94` | `&3CB7`, `&3CBC` | block, mode 4 | XOR, maps cleared | 16 |
| `&3E0C` | `&3E19`, `&3E1D` | the playfield cleared (rows 0-21) | store 0 | 11,264 |
| `&3DFD` | `&3E05`, `&3E09` | the whole screen cleared | store 0 (LDIR) | 16,384 |

- `&3E54` (an `LDIR` from 0 to 0 of BC bytes, BC = 0 for 65,536) is a delay: it rewrites the screen with its
  own bytes, changing nothing.
- The bonus screen (seen once in zone 99's random play, `work/graphics/stall99.png`) is drawn by `&3DFD`, the
  interpreter in mode 0 and the font; its writes weren't logged (*unverified* that nothing else writes there).

## The 32-line plotter, `&07D9`: the player and the popups
**Call**: A frame, DE the new place (D = y, E = x), BC the old place (B = y, C = x), HL the save area (224
bytes). The player's save area is `&3FFE` (`&1027`); the popups' follow it, 224 bytes each (`&40DE` on, `&291F`).
All the save areas lie in `&3FFE`-`&490D`, cleared at each zone (`&3F10`).

| Step | What |
|---|---|
| 1 | Frame A's 192 bytes at `&93CD + 192A` are read by popping (SP pointed at them) into the buffer `&0A7F`, 7 bytes × 32. Even x: the 6 bytes and a 0. Odd x: shifted a pixel right: byte k = (byte k-1's right pixel, byte k's left pixel), 7 bytes |
| 2 | Right edge: if x ≥ 117 (byte 58), the bytes past screen byte 63 are zeroed (masks at `&09CE`, 6 a row for x = 117-127) |
| 3 | Behind scenery: the `&B700` cells under the buffer (4 rows, 5 if y AND 7 isn't 0; 4 cells across) ANDed; if any is 0, every buffer byte is ANDed with its own cell's value (`&0A18`, masks patched into `&0A54`-`&0A73`) |
| 4 | 32 times: XOR a line of the new buffer onto the new place, then a line of the save area onto the old place (so the old and new images are swapped line by line, not a whole sprite erased) |
| 5 | Unless HL = `&3F1E`, the buffer (224 bytes) is copied to the save area for next time (`LDI` × 16, unrolled) |

- **The frames**: 25 of 6 bytes × 32 lines at `&93CD`-`&A68C`. 0-23 are the player's, stored facing right
  (`&0E63` = 0). 24 (`&A5CD`) is the popup, plotted by `&2926` (from `&296F`), never mirrored.
- `&1027` plots the player only when the frame or the place has changed (`&1062` holds the last frame; `&FF`
  forces a plot). x = 128 there is the zone exit, not a plot.
- An object appears with a save area of zeros (its first plot erases nothing) and disappears by plotting the
  blank frame (16-line frame 0) or with HL = `&3F1E`, whose 224 bytes are zero (nothing erased, nothing saved:
  the 16-line padding uses it).

| Frame | What | Trimmed (w × h px, at x, y) | Opaque px | Pens 1 + 4 px |
|---|---|---|---|---|
| 0 | walking | 12 × 30 at 0, 2 | 127 | 30 |
| 1 | walking | 11 × 27 at 1, 5 | 117 | 22 |
| 2 | walking | 10 × 30 at 1, 2 | 120 | 25 |
| 3 | walking; and every pass of a jump | 9 × 32 at 2, 0 | 114 | 32 |
| 4 | walking | 10 × 31 at 1, 1 | 119 | 24 |
| 5 | walking; standing; the pass of a turn; respawned | 12 × 30 at 0, 2 | 126 | 29 |
| 6 | walking | 11 × 28 at 1, 4 | 117 | 25 |
| 7 | walking | 10 × 30 at 2, 2 | 114 | 26 |
| 8 | walking | 10 × 32 at 2, 0 | 106 | 20 |
| 9 | walking; falling | 11 × 31 at 1, 1 | 121 | 25 |
| 10 | ducking | 12 × 25 at 0, 7 | 125 | 26 |
| 11 | dying (the 46-pass leap) | 12 × 28 at 0, 4 | 138 | 21 |
| 12-23 | 0-11 in the suit (frame + 12 while `&2BDB` = 12) | 9-12 × 25-32 | 123-144 | 18-30 |
| 24 | the popup | 12 × 32 at 0, 0 | 202 | 62 (pen 4) |

- Seen in the harness: walking right cycles 0-9 a pixel a pass; no keys, 5; jumping, 3 throughout; dying, 11 up
  and down then 5 at the respawn. The suit's frames by `&1022`'s `ADD A,C` with `&2BDB` (agent B's
  `cpc-player.md`). Pens: frames 0-10 and 12-22 use 1-13; 11 uses 1-11, 23 1-12; 24 uses 4, 5, 6, 11.
- Frames 0-23: 3,081 opaque pixels of 9,216; pen 1 295, pen 4 296.

### Facing, `&0E04`
Toggles `&0E63` and, for each of the 768 lines of frames 0-23 (`&93CD`-`&A5CC`, 4,608 bytes), passes the 6
bytes through the pixel-swap table `&BD00` (made at start-up: each byte with its two pixels exchanged; checked
for all 256) into `&0E5D` and writes them back in reverse order. Called when a walk key opposes the facing
(`&10B0`, `&10BE`), and at the start of a game and a respawn to face right. The turning pass takes 146 ms
against about 50 (agent B). The popup's frame 24 isn't touched.

## The 16-line plotter, `&0B5F`
The same as the 32-line plotter, for 4 bytes × 16 lines: A frame (`&A68D + 64A`), DE new, BC old, HL an 80-byte
save area (5 × 16); buffer `&0A7F`; the `&B700` test over 3 cells by 2 (3 if y AND 7 isn't 0); 16 lines XORed
new and old; the buffer saved unless HL = `&3F1E`. It has no right-edge clip (the copy of the mask table at
`&0ACE` is never used), so a 16-line object past x = 120 would wrap onto the next row (*unverified* that none
goes there).

45 frames, `&A68D`-`&B1CC`. Callers and kinds are agent C's names (`docs/cpc-objects.md`):

| Frames | What | Plotted from | Trimmed (w × h px) | Opaque px | Pens | Pens 1 + 4 px |
|---|---|---|---|---|---|---|
| 0 | blank: removes an object; the padding's dummy | many; `&2B9C` | | 0 | | |
| 1-4 | alien (green) | `&3112`/`&3122` (`&3090`) | 8 × 16 | 62 each | 1, 2, 4, 5, 6, 11 | 29 each |
| 5 | big explosion | `&2CE4` (`&2CC3`) | 2 × 4 | 6 | 2, 9, 10 | 0 |
| 6 | big explosion | | 6 × 10 | 21 | 1, 2, 9, 10 | 8 |
| 7 | big explosion | | 8 × 14 | 57 | 1, 2, 9, 10 | 7 |
| 8 | big explosion | | 8 × 14 | 21 | 1, 2, 9 | 2 |
| 9 | big explosion | | 8 × 13 | 11 | 1, 2, 9 | 1 |
| 10-11 | homing missile | `&2FBE`, `&2FD0` (`&2F6E`) | 8 × 7, 8 × 13 | 30, 40 | 2, 9, 10, 11, 12 | 0 |
| 12-15 | the title's twinkle | `&0248` (`&01D7`) | 3 × 5 to 7 × 15 | 7-31 | 2, 9, 10, 11 | 0 |
| 16-19 | alien (cyan ball) | `&3112` | 8 × 16, 6 × 14, 6 × 12, 6 × 14 | 100, 68, 56, 68 | 7, 8, 11 | 0 |
| 20-23 | alien (striped ball) | `&3112` | 8 × 16 (22: 8 × 14) | 81 each | 1, 2, 3, 9, 10, 11 | 4 each |
| 24-27 | alien (white ship) | `&3112` | 8 × 16 | 62-66 | 1, 2, 9, 10, 11, 12 | 1 each |
| 28-32 | the arc: two halves, frames 28-31 and 29-32 | `&3517`, `&3527` (`&34FF`) | 8 × 5 to 8 × 10 | 8-13 | one each: 28-29 pen 10, 30-31 pen 11, 32 pen 2 | 0 |
| 33-35 | not seen plotted; drawn like the arc (*unverified*) | | 8 × 7 to 8 × 10 | 11-16 | 33 pen 2, 34-35 pen 9 | 0 |
| 36 | time-out missile | `&39BB`, `&39D2` (`&3989`) | 8 × 16 | 80 | 1, 2, 11, 12 | 5 |
| 37-40 | alien (cyan ship) | `&3112` | 8 × 16 | 50 each | 2, 3, 7, 8, 11 | 0 |
| 41-44 | alien (yellow fish) | `&3112` | 8 × 16 | 74 each | 1, 2, 7, 8, 9, 10, 11 | 2 each |

- All 45: 2,043 opaque pixels; pen 1 59, pen 4 108. Frames used per caller were logged over 150 passes of every
  zone (`work/graphics/moves.py`).
- An alien's 4 frames cycle as it flies; which type a zone has comes from its alien table (`&33A0`, agent C).

## The 8-line plotter, `&2020`
**Call**: A frame, DE the place (D = y, E = x). The frame's 24 bytes (3 × 8) at `&921D + 48A`, or `+ 24` for odd
x, are popped and XORed onto the screen. It counts its calls in `&2B9B` (for the padding). No save area, no
`&B700` test, no clipping: the caller erases with a second call at the old place.

| Frame | What | Plotted from | Trimmed, even copy | Opaque px | Pens | Pens 1 + 4 px |
|---|---|---|---|---|---|---|
| 0 | grenade, thrown facing right | `&1F74`, `&1FA2`, `&1FE1` | 4 × 6 | 14 | 1, 2, 7, 8, 11, 12 | 2 |
| 1 | grenade, thrown facing left | | 4 × 6 | 14 | | 2 |
| 2 | debris | `&224E`, `&228B`, `&22A6` | 5 × 8 | 34 | 1, 9, 10, 11, 12 | 8 |
| 3 | small explosion | `&2554`, `&2559` (`&2539`) | 4 × 8 | 16 | 1, 2, 9, 10 | 5 |
| 4 | small explosion; spores' set-up | `&2554`; `&2835` | 3 × 7 | 11 | 2, 9, 10 | 0 |
| 5 | small explosion | `&2554` | 2 × 4 | 6 | 1, 2, 9, 10 | 2 |
| 6 | blank: the padding's dummy; the explosion's end | `&2B95`; `&2554` | | 0 | | |
| 7 | spore (the odd copy a smaller picture: 4 × 6, 20 px) | `&2744`, `&2791`, `&2877` | 4 × 8 | 28 | 1, 2, 3, 11 | 10 (odd copy 5) |
| 8 | launcher missile | `&2AC0`, `&2AF1`, `&2B03`, `&2B54` | 4 × 4 | 14 | 1, 2, 11, 12 | 1 |

- The odd copy is the even copy shifted a pixel right for every frame but 7 (checked pixel by pixel).
- The small explosion (`&2521` starts it with a timer of 10; `&2539` runs it) shows frames 3, 4, 5, 3, 5, 4, 5,
  5, 5 over 9 passes at a fixed place, then nothing: each pass XORs table `&255E`'s entry t + 1 off and entry t
  on (`&255E`: `&DD`, 6, 5, 5, 5, 4, 5, 3, 5, 4, 3, 6 for t = 0-11; frame 6 is blank).
- All 18 copies: 266 opaque pixels, pen 1 55, pen 4 0.

## The dots
- **The laser bolt**, `&10F5`: one line, 4 pixels: even x `&4D &8E` (pens 2, 11, 11, 2), odd x `&04 &CF &08`.
  XOR, no clipping. `&11C5` runs five times a pass and each run XORs a bolt off and on again a pixel on (`&11E0`,
  `&1221`): 5 pixels and 10 plots a pass a bolt, up to 8 bolts (agent B).
- **A gun's shot**, `&1D9A`: one pixel, two lines: pen 11 over pen 3 (`&8A`, `&88`, or `&45`, `&44` at odd x).
  XOR. `&1DE9` moves the shots twice a pass, a pixel each.
- The laser's hit tests (`&288C`, `&2C74`) XOR a bolt off with `&10F5` when it hits something.

## Blocks drawn in play
The block plotters (`docs/cpc-zones.md`) draw these moving or changing things on the grid:

| What | Set and blocks | Mode | Pens | Pens 1 + 4 px |
|---|---|---|---|---|
| Thruster flames (3 frames a pass) | `&6F8D` 21-26 | 1 | 1, 2, 9, 10 | 15 (pen 1) |
| Burning mines, alternate frames every pass | `&6F8D` 29-32 | 0 | 1, 2, 9, 10 | 7 |
| Gun muzzles, 8 frames when a gun fires | `&758D` 16-31 | 2 | 1, 2, 11, 12 | 8 |
| An object destroyed, a pick-up taken | its own blocks | 3, 4 | | |
| The status digits and score | the font | 1, 0 | | |

## The font, `&69DD`
Characters `&20`-`&5A` (space, `!`, digits, `A`-`Z` and a few symbols; `*` is an arrow) at `&6BDD + 16(c -
&20)`, one block each: 2 bytes × 8 lines, 4 × 8 pixels, coloured in the data (a red-orange-yellow ramp: pens 2,
3, 9, 10, 11, 12; 592 opaque pixels of 944 × 2, no pen 1 or 4). Text is drawn by the interpreter (mode 0) or
`&3BDB` (mode 1). ZX02: 944 → 334 bytes.

## The status rows (22-23)
Drawn at a game's start by `&078F`: the script `&07A1` (row 22 from column 0: `AMMO GRENADES POINTS LIVES
ZONES`; row 23 blanked with `&E4 32 &20`, then the score's script `&3B33`), then each number.

| What | Variable | Row, columns | Digits | Drawn by | Updated |
|---|---|---|---|---|---|
| Ammo | `&1BB4` (99 at start) | 23, 1-2 | tens, units (`&1B77`, hundreds skipped) | `&1BA9`, mode 1 | each shot (`&115D`), a pick-up (`&267A`), a life (`&2A33`) |
| Grenades | `&1BC0` (10) | 23, 8-9 | tens, units | `&1BB5`, mode 1 | each throw (`&1F81`), a pick-up (`&26D0`), a life (`&2A36`) |
| Points | `&3B3B`-`&3B40` (6 ASCII digits) | 23, 14-19 | 6 | `&3B04`: adds, then the script `&3B33`, mode 0 | each score (`&2142`, `&2889`, `&2B64`, `&2BD1`, `&336B`, the bonus screen) |
| Lives | `&1BD4` (9) | 23, 23 | 1 | `&1BC1`, mode 1 | a death (`&2A39`) |
| Zone | `&12FA` | 23, 28-30 | 3 | `&1BD5` (`&3E63`), mode 1 | each zone's set-up (`&126B`) |

- 70 blocks for the whole panel; an update redraws 1-6 characters (16 bytes each), well under 1% of a pass on
  average (0.10 mode-1 blocks a pass and 0.44 score digits a pass over every zone's play).
- The score's mode-0 writes put `&B700`/`&BA00` values at offsets 750-755 (row 23), outside the 704 the maps use.
- The labels are in the font's ramp; nothing in rows 22-23 is animated.
- Rows 22-23's `&B700` bytes (`&B9C0`-`&B9FF`) are 0 in the image and nothing sets them, so the 32- and 16-line
  plotters clip their sprites out of the status rows cell by cell (the death leap goes down to line 192, agent
  B). The 8-line objects aren't clipped; debris is removed at y ≥ `&A9` (169).

## Other screens
Drawn by the interpreter (`&3CDD`) and the font; the first three after `&3DFD` clears the screen.

| Screen | Script | Block sets | Blocks | Also |
|---|---|---|---|---|
| Title | `&0174` | the logo `&86FD` (50 blocks by `&0491`), the font | 121 | twinkles: 16-line frames 12-15 in free cells (`&01D7`; 12 slots at `&0281`, save areas from `&3FFE`) |
| High score table | `&051A` | the logo, `&82AD` (36), `&744D` (80, the planets) | 166 | 17 rows × 16 characters from `&056C` by `&3BDB` |
| Bonus screen | `&3758`, `&380B` | the border `&915D` (208), the logo, `&8E5D` (128), the font | 727 | the pointer and points (*unverified*) |
| Game over | | the font | | `GAME OVER` over the playfield, mode 1 |

The logo set `&86FD` uses pens 7, 8 and 11 only (965 opaque pixels, none of 1 or 4).

## Pen use
Pens 1 (red) and 4 (green) are dithered with black on the BBC (plan, Colours), so their pixels matter:

| Graphic | Opaque px | Pen 1 | Pen 4 | Share |
|---|---|---|---|---|
| Player frames 0-23 | 3,081 | 295 | 296 | 19% |
| Popup (frame 24) | 202 | 0 | 62 | 31% |
| 16-line frames | 2,043 | 59 | 108 | 8% |
| 8-line frames (both copies) | 266 | 55 | 0 | 21% |
| Zone tiles (445) | 8,346 | 611 | 631 | 15% |
| Font, logo | 1,557 | 0 | 0 | 0 |
| The bonus screen's sets | 328 | 19 | 0 | 6% |

Per frame in the tables above; the laser and gun shots use neither.

## Sizes and packing
ZX02 by Baron's transform, the CPC's bytes as stored:

| Data | Address | Bytes | ZX02 |
|---|---|---|---|
| 32-line frames (25) | `&93CD`-`&A68C` | 4,800 | 989 |
| 16-line frames (45) | `&A68D`-`&B1CC` | 2,880 | 707 |
| 8-line frames (9, both copies) | `&921D`-`&93CC` | 432 | 237 |
| The font | `&6BDD`-`&6F8C` | 944 | 334 |
| All block sets | `&6F8D`-`&921C` | 8,848 | 4,051 |
| All of it | `&6BDD`-`&B1CC` | 17,904 | 6,253 |

The plan's own measures (dithered BBC bytes, column order): the player's 24 frames 4,608 → 869, the 16-line
frames 2,880 → 659.

## The plot log, `tools/plotlog.py`
Runs the harness n passes with given keys (random as `cpc.py`'s own run, or held keys), optionally from another
zone and invulnerable (the disc's poke), and breaks on every plotter's entry. Each call is logged: kind, routine,
caller, frame or block, set, new x and y, old x and y and save area (32- and 16-line), whether the erase and the
draw each did anything (a save area of zeros erases nothing; a blank frame draws nothing), padding (calls from
`&2B88`, `&2B9C`), and the bytes written. 8-line calls are classed erase or draw by their call site (table in the
tool); erase-then-draw pairs give the moves. `--log` writes every plot as text; the summary gives the counts.

### Measured: plots and bytes a pass
Random keys (seed 7), 400 passes in each of zones 0, 38, 94 and 99 (`work/graphics/plotlog_summary.txt`); the
one zone-change pass (zone 0 to 1) left out:

| Zone | Plots a pass: median, 90%, max | Bytes a pass: median, 90%, max | Padding plots, median |
|---|---|---|---|
| 0 | 14, 33, 218 | 537, 1,040, 5,384 | 16 |
| 38 | 23, 46, 69 | 1,080, 1,872, 2,440 | 6 |
| 94 | 34, 118, 183 | 1,392, 3,392, 4,984 | 6 |
| 99 | 11, 30, 117 | 1,120, 1,768, 3,688 | 20 |
| **All 1,599** | **21, 53, 218** | **1,040, 1,968, 5,384** | |

| Kind | Bytes a pass: mean, 90%, max |
|---|---|
| Player | 298, 448, 896 |
| 16-line | 324, 800, 1,120 |
| 8-line | 530, 1,152, 4,392 |
| Blocks | 29, 64, 720 |
| Laser bolts | 2, 0, 28 |

- The padding adds a median 984 bytes (max 1,344) of dummy XORs.
- The peaks are debris: a grenade's hit spawns 2 per block of the object (62 for object 13), each erased and
  redrawn every pass.
- The 32- and 16-line plotters always XOR both images in full (7 or 5 bytes × every line), even when one is
  blank.

### Measured: the largest move in one plot
150 passes of every zone, random keys, invulnerable (`work/graphics/moves.py`; `moves_inv.txt`). For the 32- and
16-line plotters, new against old in the same call; for 8-line objects, an erase and the next draw of its pair.
Moves over 8 pixels or 16 lines are respawns and teleports, counted apart.

| Object | Plotter, frames | dx px | dy lines | Plots |
|---|---|---|---|---|
| Player | 32-line 0-10 | 1 | 4 | 9,867 |
| Popup | 32-line 24 | 0 | 8 | 2,112 |
| Alien (cyan ball, green, striped) | 16-line 16-19, 1-4, 20-23 | 4 | 8 | 12,754 |
| Alien (white ship, yellow fish) | 16-line 24-27, 41-44 | 4 | 4 | 7,742 |
| Alien (cyan ship) | 16-line 37-40 | 4 | 3 | 2,079 |
| Homing missile | 16-line 10-11 | 2 | 1 | 1,323 |
| Time-out missile | 16-line 36 | 2 | 0 | (from the code: x - 2 a pass) |
| Big explosion, arc | 16-line 5-9, 28-32 | 0 | 0 | 3,256 |
| Debris | 8-line 2 | 4 | 8 | 51,487 |
| Grenade | 8-line 0, 1 | 1 | 4 | 16,191 |
| Launcher missile | 8-line 8 | 2 | 0 | 7,773 |
| Spore | 8-line 7 | 1 | 1 | 42,029 |
| Small explosion | 8-line 3-6 | 0 | 0 | 61,834 |
| Laser bolt | dot | 1 a plot, 5 a pass | 0 | |
| Gun shot | dot | 1 a plot, 2 a pass | 0 | |

- The debris velocities come from the table `&226A` (x: -4, -3, -2, 0, 0, 2, 3, 4; y twice that), so 4 and 8
  are the true limits, not just the most seen.
- The player's 4 lines are a jump's steps (4, 4, 2, ...) and falling (4 a pass); a respawn moves him to the zone's
  entry point (a jump: 1-5 a zone in the logs).
- So for the BBC's self-erasing sprites: a blank border of 1 byte across and 4 lines for the player, 2 bytes and
  8 lines for the aliens and debris, 1 byte for the others.

## For the BBC
- The CPC's run-time shifting, mirroring in place, line-interleaved XOR swap, save areas and padding are all
  incidental: the BBC stores both shifts of the frames it needs (P5), mirrors as it plots, and draws once a pass.
- What must carry over: the `&B700` clipping (a sprite's bytes in a hidden cell aren't drawn), the 8-line
  objects' lack of it, frame 7's different odd copy, frame 24 as the popups', and XOR for the transient
  8-line objects and dots if D10's EOR is taken for them.
- Pen 0 is transparent everywhere; there are no stored masks, so the mask table (P10) is all the BBC needs.
