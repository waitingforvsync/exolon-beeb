# Decisions

The log of design decisions for the port. Each entry has one of three statuses:

- **Decided**: Rich has made the call. To change it, add a new entry that supersedes the old one.
- **Proposed**: Claude's recommendation, waiting for Rich to accept, change or reject it. An accepted
  proposal moves to Decided with a new D number, keeping its old number in brackets.
- **Open**: needs a measurement or a preference before anything can be proposed.

---

## Decided

### D1. A MODE 2 version of the CPC disc version, at its screen size, in Baron (2026-10-31)
Rich: "In docs/ you will find a disk image of exolon for the amstrad cpc. I would like to create a version for
the bbc micro in mode 2, using the baron assembler, with the same screen dimensions".
- The CPC's screen is 64 bytes × 24 rows (128 × 192 pixels): R1 = 64 and R6 = 24 in MODE 2.

### D2. Dithered graphics for the CPC's palette (2026-10-31)
Rich: "using dithered graphics to approximate the cpc palette".

### D3. A BBC B, with sideways RAM (2026-10-31)
Rich: "We can use sideways ram but we are targeting a BBC B."
- NMOS opcodes only.

### D4. Beat the original's performance and frame rate (2026-10-31)
Rich: "The aim is to improve on the performance and frame rate of the original."
- The CPC averages 20.9 passes a second, unsynced (`plan.md`, Speed).

### D5. A spec from the Z80, written as 6502 (2026-10-31)
Rich: "The idea is not to transliterate the Z80, but to derive a spec from it which is then implemented in 6502
using regular 6502 paradigms and using the coding standards and optimisations we have previously set out."

### D6. Built the way the earlier projects were (2026-10-31)
Rich: "please use the beeb-baron skill, and draw from previous bbc micro projects like portalc, teddyboy,
criticalmass and the baron examples which can be found in ~/dev."
- Chase H.Q. (`~/dev/chasehq`), another CPC port begun the same day, is the nearest for the reference harness
  and the colour rule. Teddy Boy is the model for the sprites (D7).

### D7. Teddy Boy's sprites: self-erasing, straight to the screen, masked only where needed (2026-10-31)
Rich: "my idea would be a similar approach to teddy boy: self-erasing sprites which are directly rendered to
screen, only applying masking when overlapping with non-empty background tiles or other sprites."
- Supersedes P2 (XOR plotting as the original), apart from D10's transient effects.
- Teddy Boy's D7, P7 and P8; how it fits Exolon's tiles is P8 and P9 below.

### D8. 25 updates a second (2026-10-31, was P1)
Rich: "25 updates per second sounds ok."
- A pass every second frame, locked to vsync, the CPC's padding dropped. It plays about 20% faster than the
  CPC's 20.9 a second (O1 closed).

### D9. One screen, no double buffering, raced against the beam (2026-10-31, was P3)
Rich: "No double buffering, use a single screen, race the beam, and use the self-erasing trick with direct
stores, to minimise the time in which the sprite is erased. Maybe sort them by height if necessary."
- 12K at `&5000`-`&7FFF`, 20,192 bytes of main RAM left below it.

### D10. Mask when there's time; EOR for transient effects (2026-10-31)
Rich: "I think in general we should mask if we have the cpu cycles, it just looks better. I'm not averse to EOR
plotting for things like explosions / particle effects which are transient in nature."
- O2 (the XOR's colours over scenery) closed: masked objects show the CPC's look, or better.

### D11. Two sideways RAM banks at most, ideally one; compress (2026-10-31, was P7)
Rich: "I think we should aim for no more than 2 sideways RAM banks, plus main ram. I expect with compression,
e.g. zx02, we can compress both maps and graphics considerably. Ideally I would not even want to use more than
one 16k sideways ram bank, but this is maybe not viable."
- Measured (Baron's ZX02 transform): the CPC's data at `&6649`-`&B1CC` packs 19,332 → 6,969 bytes, the zones'
  placement lists 4,055 → 2,500, and `&0100`-`&6648` (code and data mixed) 25,929 → 14,170.

### D12. The pause between screens unpacks what the next screen needs (2026-10-31)
Rich: "There is a pause between screens: my thought is to use this to unpack what we need for the next screen:
screen data, map tiles, enemy sprites, etc."
- Takes in the zone-entry work of P5 (shifted frames) and P11 (the working set).
- And on packing: "Think that we also only have 3bpp sprites so a variant on zx02 might store literals in the
  sprite data as 6 bit bytes instead of 8. Just thoughts about how we can pack this." Measured in P12.

### D13. Sound updated at 50 Hz (2026-10-31, was O3)
Rich: "O3: just simple 50 Hz update."

### D14. The BBC's usual keys (2026-10-31, was O4)
Rich: "O4: normal bbc keys please ZX/: Ret Space."
- Z left, X right, `:` up, `/` down. RETURN fires (D17).

### D15. The loading screen ported however suits it (2026-10-31, was O5)
Rich: "O5: just port it however works, if it's a 16 colour screen, use ordered dithering".
- It isn't 16 colours. `EXOLON.SCR`, unpacked by its own code in `tools/cpc.py`'s machine, is a MODE 1 screen
  (the BASIC loader's MODE 1 and inks: black, bright red, bright green, bright white), 256 × 192 pixels,
  columns 32-287 of 320. That's 64 bytes × 24 rows, the game's geometry, in colours the BBC has: it goes
  across exactly in MODE 1, the CPC's pens 1 and 2 swapped, with no dithering.

### D16. Standard ZX02 (2026-10-31, from P12)
Rich: "8 bit byte-aligned literals unpack faster with zx02 and we don't save much in going to 6-bit literals, so
let's stay with standard zx02."
- The 6-bit literals measured about 7% on the sprites (P12). Not tried on the tiles.

### D17. One fire button: RETURN (2026-10-31, from P13)
Rich: "oh, if there's one fire button, just leave it as RETURN."
- Z left, X right, `:` up, `/` down, RETURN fire. SPACE does nothing unless Phase 1 finds a second action.
- Phase 1B found none: a grenade is thrown by holding fire 15 passes (`docs/cpc-player.md`). So it stands.

### D18. Redefining the keys goes in a loader program, later (2026-10-31)
Rich: "I would move redefine keys option into a loader program which you can do just once before the main game
loads, but that's for later."

### D19. Milestone 1: a few zones (2026-10-31)
Rich: "Just do a few zones to start with, though I assume the rest are similar."

### D20. Main RAM's code without gaps from &121; the workspace below the screen (2026-10-31)
Rich: "just a preference: try to put all the code starting from MainCodeOrg onwards without gaps (working around
the things which can't move like IRQ1V, &258, &D00). Use the memory underneath the screen for workspace,
generated tables, decompressed data, etc".
- The main loop moved from the code's bank into main RAM. Each piece is placed to fit round IRQ1V, &258 and
  the RTI at &D00 (6 and 2 bytes spare now); the workspace is one virtual section from the code's end to
  `&5000`.

### D21. Data packed in large blocks, unpacked into the blanked screen, the pieces copied out (2026-10-31)
Rich: "Also feel free to group screens, sprites, etc into larger aggregated compressed blocks (for better
compression), which are decompressed to screen memory while blanked and just the piece we need is copied out."
- So the 12K screen is the unpacking buffer in the pause between screens (D12): a block holding many zones'
  data, or many sprite types, unpacks there whole, and the next zone's pieces are copied to the workspace
  before its screen is drawn.

### D22. Unroll only the hot loops (2026-10-31)
Rich, on the review's offer to unroll the IRQ's key scan: "take the approach portalc takes, a loop. (key
scanning I mean)", and "Unrolling should be reserved for hot loops, like the sprite code. We don't have the
luxury of memory here."

### D23. Nothing assumed of A at the IRQ's entry (2026-10-31)
Rich: "we shouldn't assume A=0 on entry. can we assume that?"
- On OS 1.20 it holds: the IRQ vector's `&DC1C` is `STA &FC : PLA : PHA : AND #&10 : BNE : JMP (&204)`. But
  that's the MOS's code, unchecked on MOS 3.20 and OS 2.00, for 2 cycles and 2 bytes: the handler clears A
  itself (`LDA #0`), as Portal's does.

### D24. The Spectrum original as a second reference for the mechanics (2026-10-31)
Rich: "I have just put a .tzx file of the original spectrum version at docs/Exolon.tzx. Can you cross-reference
against this when writing game mechanics to keep it faithful to both."
- The tape loads (SkoolKit's simulated LOAD, through the Hewson loader) to the game at `&6D60`-`&FFFF`;
  `tools/spectrum.py` runs it, and `tools/cpc2spec.py` maps 111 CPC routines to their Spectrum twins. The two
  main loops make the same calls in the same order; the Spectrum's adds a fixed delay each pass.
- Uncontended, the Spectrum makes about 25 passes a second (a median 1.90 frames a pass), against the CPC's
  20.9: D8's 25 is close to the original's own pace.
- Where the two differ in anything that affects play, the specs give both and Rich chooses.

### D25. The time limit: 840 passes (2026-10-31, was O10)
Rich: "O10: 840 passes."
- The CPC's 33.5 s at 25 passes a second.

### D26. The high-score table: the Spectrum's names, 17 entries (2026-10-31, was O11)
Rich: "O11: Spectrum names, 17 entries."

### D27. No pause or redefining the keys for now (2026-10-31, was O12)
Rich: "O12: don't worry about redefine keys or pause for now."

### D28. No lockstep at the AF' call sites (2026-10-31, was O13)
Rich: "O13: don't worry, not important."
- A lockstep check against the original runs until the first of those calls, or patches round them.

### D29. Keep the turn's still pass; perhaps mirror the player's frames then (2026-10-31, was O14)
Rich: "O14: keep; see if performance permits mirroring all the player graphics at that moment, it will save some
memory!"
- The CPC's 96.7 ms (`&0E04`) is what's to beat: one facing kept, mirrored in place within the turn's pass.

### D30. Sprites trimmed to their bounding rectangle; dirty edges erased first (2026-10-31)
Rich: "Regarding self-erasing sprites: they should not contain the erasing border themselves, they should be sized
to the smallest bounding rectangle on byte boundaries. But in general they should erase anything behind them in
their new position, and will need special "dirty edge" erasing as a first pass, as per teddy boy."
- Supersedes P9's blank border in the frames.

### D31. Sprites always behind the map's graphics (2026-10-31)
Rich: "Let's assume that sprites are always drawn behind the map graphics, hopefully that simplifies things."
- So no tile is ever composed under a sprite: where a cell's empty the sprite is stored straight, and scenery
  stays in front. The CPC hides sprites behind most scenery a whole cell at a time (Phase 1A); this is the same
  rule for all of it.

### D32. Bit 3: whatever serves; overlapping sprites by measurement (2026-10-31)
Rich: "Do with bit 3 whatever is useful. Maybe it's useful to use it as a "draw behind" marker, which even works
for overlapping sprites. Or maybe overlapping sprites being EORed is OK. I don't have a strong opinion,
performance and code complexity will dictate the best option."

---

## Proposed

### P4. Chase H.Q.'s colour rule, the dither baked in at build time
Each pen to its BBC colour, or a checkerboard of the pair closest in brightness (Chase H.Q.'s D7). Seven pens
are plain, nine are pairs; the table is in `plan.md`. The dither is fixed to the sprite or tile and baked in
by the asset pipeline.

### P5. Pre-shifted graphics, made between screens
The CPC shifts the player and the 16-line objects a pixel at run time for odd x. The BBC plots from both
shifts, but stores one and makes the other in the pause between screens for the types the next screen uses
(D12; as Teddy Boy's D11 prepares its enemies at level start).
- The player is the big one: 4,608 bytes a facing unshifted, about 5,376 shifted (a byte wider). Both shifts
  and both facings would be about 20K, so it's one facing in memory and the other mirrored through a 256-byte
  table as it's plotted, or similar: measured in Phase 2. Never the CPC's mirroring in place (a 100 ms stall
  each turn).

### P6. The original as the model
`tools/cpc.py` runs the CPC version. The BBC's logic is checked against it pass by pass with the same keys,
and the plots it logs are the benchmark for the BBC's plotters. No shim is needed: the game reads no clock and
not R.

### P8. The background as a tile map
Measured in Phase 1A (`docs/cpc-zones.md`, `tools/zonemodel.py`, which rebuilds all 125 zones exactly from the
data): one block a cell is exact; a cell written twice takes the later block. 445 distinct blocks in all
(7,120 bytes; 3,205 packed, dithered, in column order), 27-161 a zone, so a byte numbers a zone's tiles. The
placements and scripts pack to 4,046 bytes against about 11,000 for ready-made tile maps: so the BBC runs the
scripts at zone entry (in the pause, D12), as the CPC does, into the tile map.
Every zone is objects placed on the Spectrum's character grid (row 0-19, column 0-31), each drawn by a script of
2-byte × 8-line blocks (`&3BF0`). So in the pause before a zone (D12) the BBC runs the zone's placements into a
32 × 22 map of tile numbers (704 bytes), and draws the screen from it. The tiles are converted (dithered) at
build time and laid out for the plotters (Teddy Boy's line-planar tiles); the empty tile is 0. A sprite's plot
finds the tiles under it in the map, so it knows where it may store straight (D7) and composes from the tile
data, never the screen. Phase 1 confirms that nothing is drawn off the grid.

### P9. How a sprite is drawn (after D30-D32)
- **Frames** trimmed to their bounding rectangle on byte boundaries (D30), dithered, in column order; each
  object's other shift made between screens (P5).
- **The dirty edges first**: the bytes of the old rectangle the new one doesn't cover are cleared of every
  pixel without bit 3 (P10). Scenery and stars keep themselves, so nothing is restored from tile data.
- **Then the new rectangle**: in an empty cell (the tile map says so, a column's band at a time) the sprite's
  bytes are stored straight; in a cell with scenery or stars, each byte keeps the screen's bit-3 pixels and
  takes the sprite's elsewhere (`LDA (scr),Y : TAX : LDA (spr),Y : AND Hole,X : ORA Keep,X : STA (scr),Y`,
  about 26 cycles, against about 11 straight). Sprites are behind all of the map (D31), and seen through its
  black gaps.
- **Overlapping sprites**: all of a pass's edge clearing before its drawing, the drawing back to front, so a
  later sprite simply overwrites an earlier one; or EOR where they meet; or bit 3 on sprites too, as a
  draw-behind marker (D32). Measured in Phase 2.
- **Explosions, debris, particles**: XOR, as the original (D10).
- Each pass's work goes in order of height against the beam; a byte is written once a pass except where
  sprites overlap.

### P10. Bit 3: the map's mark (after D31, D32)
- Every coloured pixel of a tile, and every star, is drawn with bit 3 set (logical 9-15, which the palette
  makes the same as 1-7). Black pixels and sprites never have it.
- So a sprite's plot and its edge clearing find what's in front of it on the screen itself, a pixel at a time,
  with two 256-byte tables (`Keep`: a byte's bit-3 pixels; `Hole`: the rest).
- Transparency doesn't need a value of its own: the background is black, so a sprite's transparent and black
  pixels look alike, and pens 1 and 4's black halves need nothing special (P10's first form dropped).
- Logical 8 (bit 3, black) is then unused: it can be the flashing pen 15 (the barrier, the ammo and LIVES), one
  palette write a pass cycling through the CPC's colours (`&39EF`), each the BBC's nearest.

### P11. Two banks; the graphics and the zones packed, and the next screen's set unpacked between screens
- Main RAM keeps 20,192 bytes below the screen; two banks give 52,960 in all. Main RAM's code runs on from
  `&121` and the workspace follows it (D20).
- Stored packed (ZX02): the zones' placements and scripts, the tiles, the sprites. Between screens (D12) the
  next zone's tile map is made and the tiles and sprite types it uses are unpacked and shifted into working
  buffers. The CPC's zone change took 268 ms in the one measured (zone 0 to 1). Large blocks unpack into the
  blanked screen and the pieces are copied out (D21).
- One bank (36,576 in all) looks possible only if the code comes in near 15K and the working buffers are
  small. Phase 1 measures the data and the zones' needs, and Phase 3 the code, and the case is made then.

### P12. Sprites packed in column order, dithered at build time
Measured (2026-10-31; scratch: the CPC's frames converted, packed by Baron's transform, the streams' literals
counted with Teddy Boy's `zx02.py`):

| Data | Raw | ZX02 | Literal bytes | With 6-bit literals |
|---|---|---|---|---|
| The player's 24 frames, BBC bytes, column order | 4,608 | 869 | 251 | 806 (-7%) |
| The same, row order | 4,608 | 975 | 308 | 898 |
| The same as CPC pen bytes, column order | 4,608 | 832 | 249 | |
| The 16-line objects' 45 frames, BBC bytes, column order | 2,880 | 659 | 194 | 610 (-7%) |

- The sprites pack to 19-23%: two thirds of the player's pixels are transparent and its frames repeat. Matches
  are about 70% of the stream, so 6-bit literals save only about 7% here.
- A MODE 2 byte of colours 0-7 has bits 7 and 6 clear, so a 6-bit literal is just its low six bits.
- Column order (as the plotter reads) packs 11% smaller than row order. The dithered BBC bytes pack within 5%
  of the CPC's undithered pen bytes, so the dither goes in at build time, not at unpacking.
- The catch for 3 bits: pens 1 and 4 dither with black, and in a sprite that black must stay opaque (P10), a
  ninth value. They're 19% of the player's opaque pixels.
- So: frames stored in the plotter's column order, dithered at build time. Standard ZX02 (D16).

---

## Open

### O6. An experiment, later: the Spectrum's graphics in MODE 1 with raster colour splits (2026-10-31)
Rich: "Possibly I would like to try Spectrum type graphics in Mode 1 with raster colour splits as a possible
experiment later on."
- MODE 1 at the same R1 = 64 is 256 pixels across, the Spectrum's own width, in the same 12K screen and the same
  CRTC set-up: only the ULA's control register and the graphics change. Four colours a line against the
  Spectrum's two a character cell, with the palette split per character row (or finer) for its colours.

### O7. Where the CPC and the Spectrum differ in play (2026-10-31, Phase 1C)
`docs/cpc-objects.md`: the two agree in every rule, speed, timer, hit count, point and spawn, and the zones'
placements are identical, but for two things. Follow which?
- The CPC's object scripts 41, 48, 49 and 51 are empty: zones 22, 25, 26 and 66 lose scenery, and zones 25 and
  66 an electric-arc generator. The Spectrum has them.
- One alien path byte (`&3203`): `&08` on the CPC, `&18` on the Spectrum.
- (The random generator is called differently in two places, big explosions and the stars, so a lockstep check
  follows one version or the other.)
- Phase 1A: the CPC's four are single `&FF` bytes, with nothing hidden after them. Restoring them means new
  graphics from the Spectrum's (two-colour cells), drawn in the CPC's style.

### O8. Quirks of the original: keep or fix? (2026-10-31, Phase 1C)
- The exoskeleton protects only against mines and popups.
- An enemy that kills the player by touching him still scores, as if shot.
- The barrier kills only at exactly px + 12 = its x.
- The launchers' scan stops early in a pass.
- Effects are dropped silently when their list is full.

### O9. The stars: random on every visit? (2026-10-31, Phase 1C)
Each visit to a zone scatters 66 one-pixel stars in pens 1-7, from the random generator, before the scenery is
drawn: a zone looks different each time. Keep that, or fix each zone's stars?
