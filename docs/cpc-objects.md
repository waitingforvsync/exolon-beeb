# Exolon (CPC): the enemies and every other object

The objects other than the player in the CPC original (Aragorn's 1995 disc of Hewson's 1987 game), from its code
(`build/exolon.skool`) and checked in the harness (`tools/cpc.py`) with the scripts in `work/objects/`, and against
the Spectrum original (`tools/spectrum.py`, `build/spec/`) instruction by instruction, on 2026-10-31. The main loop,
the player, his laser and grenade flight, and the game's flow are agent B's (`cpc-loop.md`, `cpc-player.md`,
`cpc-flow.md`); zones, scripts, blocks and graphics formats are agent A's (`cpc-zones.md`, `cpc-graphics.md`).
Anything not checked in the harness is marked *unverified*.

## Summary

- **Zone set-up makes the objects.** The zone's scripts write marker kinds 2-17 into the cell map `&BA00` with
  their `&EB n` command; `&1BE0` then turns each marker into a record in that kind's list (row-major order) and
  overwrites the cell with a fixed value. Only the flying aliens (a per-zone table at `&33A0`) and the time-out
  missile come from elsewhere. `tools/zoneobjects.py` derives every zone's objects from the data; it matches the
  harness's own set-up in all 125 zones.
- **16 lists, fixed sizes**, each ended by a byte with bit 7 set. The largest seen in play: 6 aliens, 5 big
  explosions, 16 spores, 10 launcher missiles, 5 gun shots, 20 small explosions (the list's size), 62 debris, 3
  popups. At most 10 16- and 32-line sprites at once, and 78 moving objects in all (56 of them debris).
- **Movement is in whole pixels and lines a pass**: aliens up to 4 pixels and 8 lines, debris 4 and 8, popups 8
  lines, launcher missiles, homing and time-out missiles 2 pixels, gun shots 2, spores 1 and 1. The BBC's blank
  borders: 4 pixels (2 bytes) and 8 lines at most; most objects need 1 byte and no lines.
- **What kills**: touching any enemy (a box test against the player, `&28E0`), a gun shot, walking onto a mine,
  a popup, walking into the barrier. The exoskeleton protects only against mines and popups. Enemies that touch
  the player die too, and score as if shot.
- **The laser** kills spores, launcher missiles and aliens (one hit), and the barrier (25 hits). **Grenades** kill
  nothing that moves: they destroy scenery from a table of 10 object types (`&21DB`), which also kills a gun
  emplacement inside it, frees a pod's spores, and stops a homing-missile launcher.
- **Points**: spore or missile 50, alien or destroyed scenery 150, the barrier 1,000, each launcher "bonus" cell
  touched 1,000, the homing launcher destroyed with its missile in flight 850 (plus 150 for the scenery). The
  1,000s and 850 are paid 25 a pass.
- **Drawing is all XOR.** 8-line objects (`&2020`) are never clipped. 16-line (`&0B5F`) and 32-line (`&07D9`)
  objects keep their last image in a buffer, and are clipped cell by cell where `&B700` is 0: they pass behind
  solid scenery. The barrier, flames and burning mines are blocks, stored.
- **The random generator** is called by many objects every pass, some only for a Spectrum colour that's thrown
  away. The BBC must make the same calls in the same order to stay in lockstep.
- **The Spectrum agrees** in every rule, speed, timer, hit count, point and spawn, with two exceptions that change
  play: the CPC's object scripts 41, 48, 49 and 51 are empty (zones 22, 25, 26 and 66 lose scenery, and zones 25
  and 66 an arc generator), and one alien path differs by one byte. The zones' placements are identical.

## Conventions

- Addresses are the CPC's, `&` for hex. A *pass* is one trip round the main loop at `&06C3`.
- x is in MODE 0 pixels (0-127), y in screen lines (0-175 is the playfield), unless said otherwise.
- A *cell* is the Spectrum's character: 4 pixels (2 bytes) by 8 lines; columns 0-31, rows 0-21 of playfield.
  Markers and many records hold (column, row); `&2630` turns that into (x, y) = (4 × column, 8 × row).
- Object records are written (x, y, ...) in the order of their bytes. "Active" is a flag byte non-zero.
- `rand` is a call to `&3AE7` (A = the next 8-bit random number). "6/256" means `rand ≥ 250`.
- The player is at (px, py) = (`&10EE`, `&10EF`), the top-left of his 12 × 32 image; `&10F4` non-zero when ducking.
- Frames: "f8 n" is 8-line frame n (`&921D` + 48n, two pre-shifted copies of 3 bytes × 8), "f16 n" 16-line frame n
  (`&A68D` + 64n, 4 bytes × 16), "f32" the one extra frame of the 32-line plotter (frame 24, `&A5CD`, 6 bytes × 32).
  A block is 2 bytes × 8 lines from a base (`&3BA1`) + 16 × number.

## The maps the objects use

| Map | Bytes | Written by | Meaning |
|---|---|---|---|
| `&B700` | 32 × 24 | each block plotted at set-up: `&3BCF` (0 by default, `&FF` after a script's `&EA`) | 0: the cell is in front of 16- and 32-line sprites (they're not drawn there). `&FF`: empty or background |
| `&BA00` | 32 × 24 | each block: `&3BD5` (1 by default, a script's `&E8 n` sets it); `&EB n` writes a marker | 0: passable. 1: solid to the player, his laser and grenade, and spores. 2-17: a marker, replaced at the end of set-up (below) |

Index = row × 32 + column. The block plotter `&3B92` ignores columns 32-63 (`BIT 5,E`). Destroying a block (`&3C43`)
sets `&B700` to `&FF` and `&BA00` to 0. `&3C94`, the fifth plot mode, does the same without debris (the pickups).

## The kinds of object

| Kind | What | List, record | Most (list's room) | Markers become | Routines (main-loop order) |
|---|---|---|---|---|---|
| 2 | Thruster flames | `&1CE3`: col, row | 5 (5) | 0 | `&1CAE` |
| 3 | Gun emplacement | `&1D7F`: col, row, state | 2 (4) | 3 | `&1CEF`; shots `&1DE9` ×2, `&1E31` |
| 4 | (unused) | `&1E5F`: col, row | 14 (14) | 0 | none |
| 5 | Mine | `&1EDA`: col, row, state | 6 (10) | 1 | `&1E7C` |
| 6 | Teleport pad pair | `&262A`: col, row ×2 | 2 (2) | 1 | `&25B4`; sparkles `&2BF1` |
| 7 | Ammo pickup | `&26EC`: col, row | 1 (1) | 0 | `&263C` |
| 8 | Grenade pickup | `&26EF`: col, row | 1 (1) | 0 | `&263C` |
| 9 | Spore source | `&2855`: col, row | 2 (3) | 0 | set-up `&2811`; spores `&2732`, `&285C`, `&28BE` |
| 10 | Popup | `&2975`: col, row, counter | 3 (4) | 1 | `&291F`, `&2990` |
| 11 | Missile launcher barrel | `&2AC9`: col, row | 4 (10) | 0 | `&2A87`; missiles `&2ADE`, `&2B3A`, `&2B67` |
| 12 | Exoskeleton booth | `&2C71`: col, row | 1 (1) | 1 | `&2C30` |
| 13 | Homing-missile launcher | `&2F69`: col, row | 1 (1) | `&0D` | `&2F3D`, `&2F6E` |
| 14 | Launcher bonus cell | `&3063`: col, row, live | 6 (10) | 0 | `&303E` |
| 15 | Arc generator | `&352A`: col, row | 1 (1) | 0 | `&34FF` |
| 16 | Level end | `&3808`: col, row | 1 (1) | 0 | `&352D` (agent B) |
| 17 | Barrier | `&38E2`: col, row | 1 (1) | 1 | set-up `&38AD`; `&38F5`, `&3910` |
| | Flying alien | `&3234`: 10 bytes | 6 (6) | | `&327F`, `&3090`, `&32F6`, `&3320` |
| | Time-out missile | `&3984`: active, x, y | 1 | | `&3965`, `&3989` |
| | Gun shot | `&1E12`: x, y, dx | 5 (10) | | `&1DE9`, `&1E31` |
| | Spore | `&27A3`: x, y, live, dir | 16 (24) | | `&2732`, `&285C`, `&28BE` |
| | Launcher missile | `&2B1B`: x, y, dx | 10 (10) | | `&2ADE`, `&2B3A`, `&2B67` |
| | Debris | `&22BA`: 6 bytes | 62 (100) | | `&220E`, `&2272` |
| | Small explosion | `&256A`: x, y, timer | 20 (20) | | `&2521`, `&2539` |
| | Big explosion | `&2CFD`: x, y, timer | 5 (5) | | `&2CA6`, `&2CC3` |
| | Teleport sparkle | `&2C16`: x, y, timer | 2 (4) | | `&2BDC`, `&2BF1` |
| | Destructible scenery | `&214C`: 7 bytes | 5 (11) | | set-up `&219C`; grenade `&20F7` |

"Most" is the most in any zone's data for markers, else the most active at once seen in play (below). "Room" is
what fits before the next variable or code: a zone with more would corrupt it. Every zone is within room.

### Making the lists (`&126E`, zone set-up)
1. `&3F10` clears the sprite buffers `&3FFE`-`&490D`; `&1B69` fills `&B700` with `&FF`, `&1B5B` clears `&BA00`.
2. Each dynamic list is emptied (records zeroed, end byte left): `&1252` laser, `&1E52` gun shots, `&1F24` mines
   (state 1), `&2513` debris, `&1D8C` guns (state 2), `&25A7` small explosions, `&2804` spores, `&2982` popups
   (counter 95), `&2B0D` missiles, `&2C23` sparkles, `&3271` aliens, `&2D0D` big explosions, `&3082` bonus cells
   (live 1). `&3E0C` clears the playfield and `&2FF6` draws the stars (below).
3. The placements are drawn (`&12C1`-`&12E4`). For each, `&219C` adds a box to `&214C` if its object is in
   `&21DB`, then `&3CDD` runs its script with `&3BD5` = 1 and `&3BCF` = 0.
4. `&1BE0`: 16 descriptors at `&1C4E` (list, write pointer, record size, replacement), one per kind 2-17, entry
   = `&1C42` + 6 × kind. Each list gets `&FF` at its start; then every cell of rows 0-21 with `&BA00` ≥ 2, in
   row-major order, appends (column, row) and an `&FF`, and the cell takes the replacement value. The third
   byte of 3-byte records is left as step 2 set it.
5. `&2811` spawns the spores, `&336E` reads the zone's alien entry, `&2F3D` arms the homing missile, `&38AD` builds
   the barrier.

## Shared rules

### Touching the player (`&28E0`)
`&28E0` with the object's (x, y) in DE and a box C wide, B tall returns A = 1 on a hit:

- x: hit when px ∈ [x - 12, x + C - 1].
- y, standing (`&10F4` = 0): py ∈ [y - 32, y + B - 1]. Ducking: py ∈ [y - 32, y + B - 7] (his top 6 lines lower).
- All arithmetic is 8-bit, so the ranges wrap at the screen's edges.

| Object | Box at | C × B | On a hit |
|---|---|---|---|
| Gun shot | (x, y) | 0 × 0 | shot removed, death (`&29B4`) |
| Spore | (x, y) | 4 × 8 | spore dies (+50, small explosion), death |
| Popup (up or rising) | (4 col, 8 row) | 12 × 32 | death unless exoskeleton (`&29AF`) |
| Launcher missile | (x, y) | 4 × 8 | missile dies (+50, small explosion), death |
| Bonus cell | (4 col, 8 row) | 4 × 8 | +1,000 once (no death) |
| Homing missile | (x, y) after its move | 8 × 16 | death, big explosion, relaunch |
| Alien | (x + 2, y + 4) | 4 × 8 | alien dies (+150, big explosion), death |
| Time-out missile | (x, y) after its move | 8 × 16 | death, big explosion |

Mines and the barrier have their own tests (below). `&29B4` does nothing while the player is dying (`&29E7` ≠ 0)
or invulnerable after a death (`&078C` ≠ 0); `&29AF` also does nothing with the exoskeleton on (`&2BDB` ≠ 0).
So the exoskeleton saves him from mines and popups only. The enemy still dies and scores either way. What a
death does is agent B's (`&29B4` resets the time-out counter `&3987`, sets `&29E7` = 46 and `&078C` = 66).

### The laser
The player's shots (`&1239`, 8 records of x, y, dir) are agent B's. `&11C5` runs five times a pass; each run first
tests every shot against the spores (`&285C`), launcher missiles (`&2B3A`), aliens (`&32F6`) and the barrier
(`&3910`), then moves each shot 1 pixel. So every pixel a shot passes is tested once. A hit removes the shot.

| Target | Test (shot at bx, by) |
|---|---|
| 8-line objects (`&288C`): spores, launcher missiles | bx ∈ [x - 2, x + 1], by ∈ [y - 1, y + 8] |
| 16-line objects (`&2C74`): aliens | bx ∈ [x - 6, x + 1], by ∈ [y - 1, y + 16] |
| Barrier (`&3910`) | bx = 4 × col - 4, any by |

A shot also stops at a solid cell (`&BA00` ≠ 0) and leaves a small explosion: guns, popups, mines, launchers,
homing launchers, the barrier and all scenery stop it. Nothing else can be shot.

### Grenades and destructible scenery
The grenade's flight is agent B's: it moves once a pass while its timer `&1F84` is 19 or more, then three
times a pass (the main loop calls `&1F89` at `&06E8`, `&070B` and `&0722`), so up to 3 pixels and 4 lines a
pass, and for its first 14 passes (timer 32 down to 19) it leaves a small explosion 4 pixels behind it
(`&1FF0`). When it stops (a solid cell beside or below it, x = 0 or `&7C`, y ≥ 168), `&20F7` takes its cell
(x / 4, y / 8) and looks through `&214C`: the first box containing it is destroyed.

- `&21DB`: (object, x offset, width, y offset, height) for objects 5, 13, 15, 16, 18, 21, 31, 40, 44, 46. A box
  record at `&214C` is (column + x offset, that + width, row + y offset, that + height, column, row, object);
  the cell must satisfy x1 ≤ cx < x2, y1 ≤ cy < y2. Destroyed, the record's first byte becomes `&80`.
- Destruction re-runs the object's script with the plot CALLs patched (`&26F2`, table `&2709`) to `&3C43`: each
  block is XORed off, its cell set to `&B700` = `&FF`, `&BA00` = 0, and two debris thrown from it. +150
  (`&3B5F`), sound `&6579`.
- Debris per object (2 per block): 5 (gun) 36, 13 (the yellow alien growth) 62, 15 56, 16 (rocket) 32, 21 (pod)
  48, 31 (homing launcher) 28, 40 40, 44 (small gun) 20, 46 24. Object 18 has a box but no script and no zone uses it.
- What dies with it: a gun inside (its marker cell loses its 3), a pod's spores are freed (its solid cells go),
  a homing launcher stops (its cell loses `&0D`). Launchers, the barrier and the generator aren't in the table.
- Only one box per grenade. 91 zones have destructible scenery, at most 5 boxes (zone 94).

### Points (`&3B04`)
`&3B04` adds a 6-digit ASCII number ending at DE to the score `&3B3B`-`&3B40` and redraws it. The numbers:
`&3B47` 25, `&3B4D` 50, `&3B53` 100, `&3B59` 125, `&3B5F` 150, `&3B65` 200, `&3B6B` 250, `&3B71` 300, `&3B77` 350,
`&3B7D` 1,000 (125 and 1,000 are also the level end's; 100 and 200-350 are unused). Larger prizes go through
`&2BB2`: A is added to the 16-bit `&2BD9` (sound `&655F`), and `&2BC4` pays 25 a pass while it's non-zero. A
1,000 is A = 40, so 40 passes.

### Drawing
| Plotter | Size | How | Clipped | Used by |
|---|---|---|---|---|
| `&2020` | 3 bytes × 8, two pre-shifted copies | XOR at (E, D), frame A; old image erased by plotting it again | no | spores, missiles, debris, small explosions, grenade |
| `&0B5F` | 4 bytes × 16, shifted at run time to 5 | erase the image held in buffer HL at BC, draw frame A at DE, keep it in HL | yes, by `&B700` | aliens, big explosions, homing and time-out missiles, generator |
| `&07D9` | 6 bytes × 32, to 7 | as `&0B5F` (buffer 224 bytes) | yes | popups (and the player) |
| `&3BDB` / `&3B92` | block | store (`&3B92` also writes the maps) | | flames, burning mines, barrier |
| `&3C0E` | block | XOR | | gun animation |
| `&1D9A` | 1 pixel × 2 lines | XOR `&8A`, `&88` (pens 11 over 3) | no | gun shots |

- **Clipping**: before XORing, `&0B5F` and `&07D9` AND each byte of the new image with the `&B700` value of the
  cell it falls in (0 or `&FF`), so a sprite vanishes behind solid scenery a cell at a time and shows over
  background (`&EA`) objects. The 8-line plotter doesn't, so debris, spores, missiles and explosions show over
  everything, XORed.
- Each buffered sprite's buffer (cleared at set-up): popups `&40DE` + 224n, big explosions `&445E` + 80n, homing
  `&45EE`, aliens `&463E` + 80n, generator `&481E` and `&486E`, time-out `&48BE` (the player's is `&3FFE`).
  Removing a buffered sprite plots f16 0, which is blank: it only erases.
- The padding (`&2B88`, `&2B9C`) tops a pass up to 16 8-line and 6 16-line plots with blank frames (f8 6, f16 0):
  the CPC's budget, which the plot counts below exceed in busy passes.

### The random generator
Calls each pass (lockstep needs them all, in this order of the main loop):

| Routine | Calls |
|---|---|
| `&1E7C` mines | 1 per burning mine (a colour, unused) |
| `&2732` spores | per live spore: 1 (turn chance) unless x is 0 or `&7B`, then 1 (dy) |
| `&291F` popups | 1 when a popup's cycle ends |
| `&1CAE` flames | 1 per flame record (a colour, unused) |
| `&1CEF` guns | 1 per intact gun at rest |
| `&2A87` launchers | 1 per barrel, until the scan stops (below) |
| `&2BF1` sparkles | 2 per sparkle |
| `&327F` alien spawn | 1 per try; a spawn adds 2 or 3 |
| `&2F3D` homing arm | 1 each launch |
| `&34FF` generator | 1 |
| `&3989` time-out missile | 1 while x < `&6F` |
| `&220E` debris | 2 or more per debris (dx, dy; again while both are 0) |
| `&3910` barrier destroyed | 1 per block (a colour, unused) |

At set-up: `&2FF6` stars (66 × 2 or more), `&2811` spores (1 each), `&2F3D` (1). The unused colours are the
Spectrum's attributes (`AND 7 : OR &42`).

## The objects

### Gun emplacement (kind 3)
A gun on a pedestal pointing left (objects 5 and 44; 33 zones, at most 2). Destructible by grenade only.

- Record: col, row, state. State 2 at set-up, 0 when destroyed, 1 at rest, 9-2 recoiling.
- `&1CEF` each pass, blocks from base `&758D`, XOR (`&3C0E`): if the marker cell's `&BA00` is no longer 3 (the
  scenery was destroyed), state = 0 and the current frame and blocks `&12`/`&13` are XORed off (the scenery's own
  blocks went with `&3C43`). State 1: on 6/256 it fires: state = 9, a shot (`&1DBA`), sound `&6579`. States 2-9:
  state - 1, frame of the old state XORed off and of the new on.
- Frames: two blocks across at (col, row): state 1 `&10`/`&11` (rest), 9 `&10`, 8 `&1E`, 7 `&1C`, 6 `&1A`, 5
  `&18`, 4 `&16`, 3 `&14`, 2 `&12` (table `&1D76`). So after firing it shows `&1E` ... `&12` over 8 passes and
  rests on `&10`. The scripts (objects 5, 44) draw it as state 2. Its death by grenade is *unverified* in the
  harness.
- Firing: 6/256 a pass at rest, so on average every 43 passes plus the 8 of recoil (checked over 1,500 passes
  of zone 7: the frames, the shot's start and its 2 pixels a pass).
- Shots (`&1E12`, 10 records of x, y, dx): spawned at (4 col, 8 row + 3), dx = -1. `&1DE9` (twice a pass) XORs
  it off, x += dx, removes it if x ≥ 127 (it ran off the left), else XORs it on. So 2 pixels a pass, through
  scenery, until the edge. Drawn by `&1D9A`: one pixel wide, two lines (white over pink). `&1E31` tests the
  player (box 0 × 0). The shot can't be shot.

### Spores (kind 9)
Red blobs that wander at random (f8 7). Kind 9 comes in two objects: 21, a destructible glass pod that holds
them, and 39, an invisible source that lets them loose at once (33 zones, at most 2 sources, so 16 spores).

- `&2811` at set-up: 8 spores per source, at (4 col + 2, 8 row + 3), live, dir = ±1 from `rand AND 1`. Each is
  XORed on as f8 4 at the same point: 8 of them cancel out. On the first pass each XORs f8 7 at the start point
  as its "erase": 8 again, so nothing is left. The BBC can simply draw them from their first move.
- `&2732` each pass, per live spore: XOR off; turn (dir = -dir) if x is 0 or `&7B`, or on 36/256, or if the cell
  ahead is solid (`&2077`/`&2097`, tested only when x is a multiple of 4, both rows if y isn't on a row); then
  dy = ±1 (`rand AND 1`), 0 if the cell above or below is solid (`&20D7`/`&20B7`, tested when y is a multiple of
  8); x += dir, y += dy, y = 1 if it became 0; XOR on.
- So inside a pod they rattle round its 4-pixel × 8-line hollow; with the pod destroyed they spread over the
  zone. Seen: x 96-100, y 120-128 in zone 5's pod; 85-123 a few passes after a grenade.
- Shot (`&285C`) or touching the player (`&28BE`): XORed off, removed, small explosion, sound `&6586`, +50.

### Popup (kind 10)
A green pillar that rises out of the floor (f32, 6 bytes × 32), object 22, which draws nothing: the marker sits
on the floor (27 zones, at most 3). Not destructible, can't be shot.

- Record: col, row, counter (95 at set-up). `&291F` each pass, with c the counter before it adds 1: c below 101,
  nothing is drawn; 101-104, row - 1 (it rises 8 lines a pass); 105-115, still; 116-119, row + 1; 120 or more,
  counter = `rand AND &3F` + 20 (20-83). For c of 101 on it's plotted every pass with `&07D9` (buffer `&40DE` +
  224n), moving from (4 col, 8 old row) to (4 col, 8 row).
- So it's up or moving for 20 passes, then hidden for 18-81 (first rising 6 passes after the zone starts).
  At rest it's plotted at its marker row, in the floor, where the clipping hides it; it's never erased.
- `&2990` (later in the pass): while the counter, now added to, is 101 or more (so from the pass before it
  first moves to the pass before it hides), box 12 × 32 at (4 col, 8 row): death unless the exoskeleton is on.
- Checked: zone 2's popup rose at passes 6-9, stayed to 20, sank 21-24, hid until 81.

### Missile launcher (kinds 11 and 14)
A green launcher with one barrel (object 45: one kind-11 marker, three kind-14 cells to its right) or two (object
26: two kind-11 above each other, two kind-14 to their right). 33 zones, at most 4 barrels. Not solid (its
cells' `&BA00` is 0: the player walks through it) but in front of 16-line sprites; not destructible, can't be
shot.

- `&2A87` per barrel: on 9/256 a pass, if px < 4 col - 32, a missile at (4 col - 2, 8 row), dx = -2, XORed on
  (f8 8), sound `&656C`. If the roll succeeds but the player isn't far enough left, or all 10 missiles are out,
  the routine returns: barrels later in the list get no roll that pass.
- Missiles (`&2B1B`, 10 of x, y, dx): `&2ADE` XORs off; at x = 0 it's removed; else x += dx and XOR on. So 2
  pixels a pass, left, through scenery. Shot (`&2B3A`) or touching the player (`&2B67`): removed, small
  explosion, sound `&6586`, +50.
- Bonus cells (kind 14, `&3063`, col, row, live): `&303E` tests each live cell against the player (box 4 × 8 at
  (4 col, 8 row)). A touch clears it and pays 1,000 (A = 40 into `&2BB2`). Walking through a double launcher
  touches both cells: 2,000. Each cell pays once a visit. Nothing is drawn or removed.
- Checked in zone 6: a missile at pass 20 with px 33 < 38; walking through the launcher at px 64 paid 80 × 25.

### Homing-missile launcher (kind 13)
A green globe on a red post (object 31, destructible; 13 zones). It launches one missile at a time, which flies
left and steers towards the player's height.

- `&2F3D` arms (at set-up, and again the moment a missile ends): only if the marker cell's `&BA00` is still `&0D`
  and the player isn't dying. Start (120, `rand AND &7F` + 32), so y 32-159; `&2F6D` = active.
- `&2F6E` each pass while active: if the cell isn't `&0D` any more (the launcher was grenaded) the missile
  explodes: 34 into `&2BB2` (850), big explosion, erased; not re-armed. Else x - 1 (and - 1 again while x < 70:
  2 pixels a pass), y ± 1 towards py (0 when equal). If x wraps past 0: erased (f16 0), re-armed. Box 8 × 16:
  death, big explosion, erased, re-armed. Else plotted with `&0B5F` (buffer `&45EE`): f16 10 while x ≥ 70, f16
  11 (the bigger flame) once faster.
- So a missile crosses in about 85 passes; in zone 15, standing, a new one every 71 (they hit the player).
- It can't be shot. Destroying the launcher with it in flight pays 150 + 850 (*unverified*: read from the code).
- Checked in zone 15: launched at once from x 120, 1 pixel a pass to x 70, then 2; y steps 1 a pass towards py.

### Flying aliens (`&3234`)
70 zones have them, by a table at `&33A0`: 5-byte entries (zone, path, first frame, spawn gap), ended `&FF`.
`&336E` at set-up finds the zone's entry and patches the path into `&32D1`, the first frame into `&310C` and the
gap into `&32F0`; `&339F` = 1 if found.

- Record (10 bytes): x, y, live, path pointer (2), loop start (2), repeat counter, animation counter, colour.
- `&327F` (not while dying): if a spawn gap is counting (`&32F5`), count it down. Else, with px < 84 and a free
  record, on 56/256: x = 120; y = py - 10 on 81/256, else py + `rand AND 15`; live; both pointers at the path;
  repeat 0; animation 3; colour `rand AND 7` (4 added if under 2) OR `&40`, unused. Gap = the zone's.
- `&3090` each pass (later in the same pass, so a new alien moves at once): read the path (below), add (dx, dy).
  If x ≥ 128 or y ≥ 176 it's removed (erased with f16 0). Else it's plotted (`&0B5F`, buffer `&463E` + 80n) with
  frame = first + (animation AND 3), animation + 1. So 4 frames, one a pass, starting with the fourth.
- Path bytes: a pair (dx, dy) is one pass's move; `&C4 n dx dy` repeats the move n passes; `&C3` goes back to the
  loop start (the path's start). All six paths, as decoded:

| Path | Zones | Moves | Loop |
|---|---|---|---|
| `&3132` | 17 | (-1, dy) with dy 0,0,-1,-1,-2,-2,-3 ×6,-2,-2,-1,-1,0,1,1,2,2,3 ×6,2,2,1,1: a wave 30 lines deep | 31 passes |
| `&3171` | 11 | the same wave once, then 15 × (-1, 0), 6 × (-2, 0), 100 × (-4, 0) | |
| `&31BC` | 9 | 34 × (-2, 0), then a loop of 72 lines up and back (dy up to ±8), then 100 × (-2, 0) | |
| `&31F1` | 19 | 40 × (-1, 0), 100 × (-4, 0) | |
| `&31FA` | 5 | 18 × (-2, 0), 32 × (0, -1), 8 × (0, 1), 6 × (0, 0), 100 × (-4, 0) | |
| `&320F` | 9 | (-2, ∓4) ×8 three times, 8 × (0, 4), 24 × (-2, 0), 6 × (0, -4), 6 × (2, 0), 6 × (0, 4), 100 × (-4, 0) | |

- Frames by zone: f16 1-4 (green crescents), 16-19 (cyan blobs), 20-23 (yellow-red balls), 24-27 (white jets),
  37-40 (cyan jets), 41-44 (yellow-red birds). Gaps 8-40 passes.
- Shot (`&32F6`) or touching (`&3320`): erased, big explosion (at (x, y), or (x + 1, y + 2) on a touch), +150.
- Checked in zone 15: spawns at x 118 (moved once already), y 118 (py - 10) or py to py + 15; gaps 14-37 (the
  zone's 13 + 1 at least). Moves tracked by the animation counter over 16 zones: largest 4 pixels and 8 lines.

### Time-out missile (`&3984`)
A grey pod (f16 36) sent after a player who lingers: every zone, from 700 passes after the zone started or the
player last died (`&3987`, counted by the main loop).

- `&3965`: if none is active and `&3987` ≥ 700: active, (120, py).
- `&3989`: at x = 0 it's erased and a big explosion made. Else, while x < `&6F`, on 128/256 a small explosion
  at (x + 6, y + 4) (smoke); x - 2; plotted (`&0B5F`, buffer `&48BE`); box 8 × 16: death, erased, big explosion.
- It then comes again at once, at the player's new height, for as long as he stays. It can't be shot.
- Checked in zone 15: first at pass 700, x 118, y = py.

### Barrier (kind 17)
A vertical beam from an emitter (object 1, which also has two flames) down to the floor. 10 zones.

- `&38AD` at set-up: from (col, row + 1) down, block 0 of base `&38E5` (all pen 15) stored with `&3B92` (so the
  cells become `&B700` 0, `&BA00` 1), until the cell below is solid. Height in `&3963`, hits `&3964` = 0.
- `&38F5` each pass: sound `&65DA` (its buzz); if px + 12 = 4 col exactly: death. So it kills a player walking
  into it from the left; it's solid anyway. Checked in zone 35: death at px 68, the beam at x 80.
- `&3910` (in each laser run): each shot at x = 4 col - 4 adds a hit; at 25 the beam is destroyed: each block
  `&3C43` (two debris each), marker `&FF`, sound `&6579`, 1,000 (A = 40). Checked in zone 35: 25 hits, then 40 ×
  25 points.
- Its colour cycles because pen 15 does: `&39D8` sets ink 15 each pass to `&39EF` + (pass AND 7) (hardware
  `&1C, &0C, &07, &0A, &12, &13, &19, &0B`). Every pen-15 pixel on screen cycles with it.

### Mines (kind 5)
A small striped mine on the floor (object 12; 24 zones, at most 6).

- Record: col, row, state (1 armed, 0 gone off). The mine is blocks `&1B`/`&1C` (base `&6F8D`) at the marker
  cell and the one to its right, set into the floor; its marker cell becomes solid.
- `&1E7C` each pass, armed: if py + 31 = 8 row - 1 (standing on it) and px - 4 col ∈ [-7, 2]: state 0, `&1EF9`
  blows it up, sound `&6579`, death unless the exoskeleton is on (`&29AF`).
- `&1EF9` runs a 5-times loop of two blank blocks (`&69DD` + `&20`) over the two cells above the mine in mode 3:
  nothing visible changes, those cells' maps are cleared and 20 debris are thrown. (It also reads a Spectrum
  attribute address, `&5800` + cell, into the script's unused colour.)
- Gone off, it burns for the rest of the visit: each pass blocks `&1D`/`&1E` or `&1F`/`&20` (base `&6F8D`,
  alternating) stored with `&3B92` over the mine's two cells. `&3B92` also writes the maps there with whatever
  `&3BCF` and `&3BD5` hold (0 and 1 in play). The fire is harmless.
- Checked: zone 35's mine went off at px 45 (x 52); zone 7's at px 33 and 53.

### Thruster flames (kind 2)
The flames under thrusters and the barrier's emitter (objects 1, 2, 28; 42 zones, at most 5).

- `&1CAE` each pass: frame f = (f + 1) mod 3 (`&1CEE`, never reset); blocks `&15` + 2f and `&16` + 2f (base
  `&6F8D`) stored with `&3BDB` at (col, row + 1) and (col, row + 2). One cell × two, three frames, all flames
  in step.

### Arc generator (kind 15)
A zig-zag of electricity between two posts (object 42, the level end's teleport, zones 24, 49, 74, 99, 124).

- `&34FF` each pass: f = 28 + `rand AND 3`; f16 f at (4 col, 8 row) and f16 f + 1 at (4 col + 8, 8 row), with
  `&0B5F` (buffers `&481E`, `&486E`). Frames 28-32, a new pair every pass.
- Harmless: nothing tests it. On the Spectrum zones 25 and 66 have one too (below).

### Teleport pads (kind 6)
Two arches (object 17, which also leaves four unused kind-4 markers); 35 zones.

- `&25B4`: up pressed (`&0D6E`), once per press (`&262F`). If py = 8 (row + 1) of the first pad and px - 4 col
  ∈ [-12, 8], sparkles at both pads and the player goes to (4 col - 3, 8 (row + 1)) of the second; and the
  other way. Sound `&6593`; the player's replot `&1022` (A = 5).
- Sparkles (`&2C16`, 4 of x, y, timer): 20 passes each; `&2BF1` puts a small explosion at (x + `rand AND 3`, y +
  `rand AND 15`) every pass. Two pads fill the 20 small explosions.

### Ammo and grenade pickups (kinds 7 and 8)
A small canister each (objects 19 and 20); at most one of each a zone.

- `&263C`: if py = 8 (row - 2) and px - 4 (col + 1) ∈ [-12, -1]: the object's own script (`&1656` ammo,
  `&1667` grenades) is run in mode 4 (`&3C94`: XORed off, cells cleared, no debris), the marker cleared, ammo
  `&1BB4` = 99 or grenades `&1BC0` = 10 (set, not added), sound `&6525`/`&6532`, the panel redrawn, the player
  replotted. Checked in zone 2 (ammo at column 28, row 9): refilled at px 104, py 56.

### Exoskeleton booth (kind 12)
Object 29 (zones 9, 34, 60, 90, 109). `&2C30`: up pressed, once per press; the same position test as a teleport
pad; toggles `&2BDB` between 0 and 12 (added to the player's frame numbers: the suited frames), sound `&6525`.
The rest is agent B's. (*Unverified* in the harness: read from the code.)

### Level end (kind 16)
In the level-end teleport (object 42). `&352D`: when px ≥ 4 col, the level's bonus screens and the next level.
Agent B's (`cpc-flow.md`).

### Unused markers (kind 4)
Objects 11 (zone 0's capsule), 17 (teleports) and 43 write kind 4; `&1BE0` lists them at `&1E5F` and nothing
reads the list. 50 zones; zone 12's 14 exactly fill the room. The Spectrum is the same.

### Debris (`&22BA`)
100 records of 6 bytes: active, x, y, dx, dy, colour (unused). `&2513` zeroes them; `&2512` is the end.

- `&220E` (from `&3C43`, twice a block): a free record; x = 4 col, y = 8 row; dx = `&226A`[`rand AND 7`]
  (-4, -3, -2, 0, 0, 2, 3, 4), dy = 2 × the same table again, both drawn until not both 0; XOR on (f8 2). If all
  100 are in use it's dropped.
- `&2272` each pass: XOR off, x += dx; if x ≥ 120, removed; y += dy; if y ≥ 169, removed; else XOR on. Straight
  lines, no gravity, through everything; leaving by the top or left wraps and is removed the same way.

### Small explosions (`&256A`)
20 records of x, y, timer. `&2521` takes a free one (timer 10), or drops it. `&2539` each pass: timer - 1, XOR
off frame f(old) and on f(new), f from `&255F`: timer 9 f8 3, 8 4, 7 5, 6 3, 5 5, 4 4, 3 5, 2 5, 1 5, 0 blank. So
it shows 3, 4, 5, 3, 5, 4, 5, 5, 5 and is gone after 10 passes. Made by: the laser hitting scenery, spores and
missiles dying, the grenade's trail, sparkles, the time-out missile's smoke.

### Big explosions (`&2CFD`)
5 records of x, y, timer. `&2CA6` takes a free one (timer 11, sound `&6586`), or drops it. `&2CC3` each pass:
plotted at (x, y) with `&0B5F` (buffer `&445E` + 80n), frame from `&2CF1`: f16 5, 5, 6, 6, 7, 7, 8, 8, 9, 9,
then 0 (erased): 11 passes. Made by aliens, homing and time-out missiles.

### Stars (zone set-up)
`&2FF6`, before the placements: for each row 21-0, three tries at a column `rand AND 31`: if the `&B700` cell is
non-zero (always, as no scenery is drawn yet) one byte `rand AND &54` (redrawn until non-zero) is put in line 4
of a blank block (base `&302E`) and the block stored there. So 66 stars, each one right-hand pixel of pen 1-7,
at random cells; scenery drawn after covers some. They differ every visit.

## What each kind draws
For the zone's working set (D12). Every zone needs f8 0-5 (grenade 0/1, debris 2, small explosions 3-5), f16 5-9
(big explosions) and f16 36 (the time-out missile).

| Kind | Graphics | Plotted |
|---|---|---|
| Gun | blocks `&758D`+`&10`-`&1F`; shot drawn by code | blocks on change (8 passes after each shot); shots every pass, twice |
| Spores | f8 7 | every pass, XOR off and on |
| Popup | f32 (192 bytes) | every pass while up (counter 101-120) |
| Launcher missile | f8 8 | every pass |
| Homing missile | f16 10, 11 | every pass |
| Aliens | f16 first to first + 3 (one set of 4 per zone) | every pass |
| Time-out missile | f16 36 | every pass |
| Barrier | block `&38E5`+0 | once, at set-up |
| Mines | blocks `&6F8D`+`&1D`-`&20` | every pass once gone off |
| Flames | blocks `&6F8D`+`&15`-`&1A` | every pass |
| Generator | f16 28-32 | every pass |

f16 0 is blank (erasing only); f16 12-15 and 33-35 aren't drawn by any object (12-15 are the title's sparkles,
`&0248`); f8 6 is blank (padding). The largest set of object graphics a zone needs is 1,520 CPC bytes.

## What's on screen at once
Measured over 270,000 passes: 45 start zones (0-124, about every fifth, and the special ones), 1,500 passes each,
four seeds of scripted random play (mostly right and firing, jumps, ducking, a grenade on 6% of changes; two seeds
invulnerable so the player gets through), lives never running out (`work/objects/measure.py`, `analyse.py`).

| List | Most at once | Where | Room |
|---|---|---|---|
| Aliens | 6 | zone 36 | 6 |
| Big explosions | 5 | zone 0 | 5 |
| Homing, time-out missile, generator | 1 each | | 1 |
| Popups | 3 | zone 47 | 4 |
| Spores | 16 | zone 20 | 24 |
| Launcher missiles | 10 | zone 48 | 10 |
| Gun shots | 5 | zone 46 | 10 |
| Small explosions | 20 | zone 2 (teleporting) | 20 |
| Debris | 62 | zone 25 (object 13 grenaded) | 100 |
| Teleport sparkles | 2 | | 4 |
| Flames, burning mines | 5, 6 | zone 50 | |
| The player's shots | 8 | zone 91 | 8 |

- The most moving objects at once: 78 (56 debris, 16 spores, 4 small explosions, 2 aliens; zone 98). Without
  debris it's far less: the 8-line XOR objects are the bulk.
- The most 16- and 32-line sprites at once: 10 (6 aliens, 2 big explosions, a popup, the time-out missile; zone
  55). The generator's two halves count two.
- Plots in a pass, padding left out: up to 209 8-line, 11 16-line, 5 32-line (with the player), 21 gun-shot.
- The total of moving objects is 0 in 23% of passes, ≤ 5 in 63%, ≤ 10 in 84%, ≤ 20 in 97%, ≤ 40 in 99.5%.
- The largest move in one pass (measured, matching the code): aliens 4 pixels, 8 lines; debris 4 and 8; popup 0
  and 8; launcher, homing and time-out missiles 2 pixels (homing 1 line); gun shots 2; spores 1 and 1; grenade 3
  and 4; the laser 5.

## The zones' object kinds
From `tools/zoneobjects.py --markdown`, which runs every zone's placements through the scripts (checked against the
harness's own set-up for all 125 zones by `work/objects/checkzones.py`: the same records in the same order, the
same boxes and alien entries). Kind-4 markers left out. "Destructible" counts boxes. The 16-line frames column
lists those beyond the always-needed 5-9 and 36; "f8 7" spores, "f8 8" missiles; blocks are base:numbers.

| Zone | Kinds (count if more than 1) | Aliens: path, frames, gap | Destructible | 16-line frames beyond 5-9, 36 | Blocks |
|---|---|---|---|---|---|
| 0 | lights 2, gun |  | 2 |   | &6F8D:&15-&1A &758D:&10-&1F |
| 1 | grenades |  | 4 |   |  |
| 2 | gun, teleport 2, ammo, popup |  | 1 |  popup | &758D:&10-&1F |
| 3 | grenades | &3132, 16-19, 20 | 2 | 16-19  |  |
| 4 | lights 2 | &3132, 16-19, 20 | 1 | 16-19  | &6F8D:&15-&1A |
| 5 | spores | &3132, 16-19, 20 | 1 | 16-19 f8 7 |  |
| 6 | lights 2, teleport 2, ammo, grenades, launcher 2, bonus 2 |  | 1 |  f8 8 | &6F8D:&15-&1A |
| 7 | lights 3, gun 2, mine 3 |  | 2 |   | &6F8D:&15-&1A,&1D-&20 &758D:&10-&1F |
| 8 | lights, teleport 2, spores, homing |  | 2 | 10-11 f8 7 | &6F8D:&15-&1A |
| 9 | ammo, grenades, popup 2, exoskeleton |  | 1 |  popup |  |
| 10 | teleport 2, launcher 2, bonus 2 | &3171, 24-27, 20 | 3 | 24-27 f8 8 |  |
| 11 | ammo, grenades, homing | &3171, 24-27, 40 | 2 | 10-11,24-27  |  |
| 12 | gun, teleport 2, ammo, grenades |  | 1 |   | &758D:&10-&1F |
| 13 | spores, popup, launcher 2, bonus 2 | &3171, 24-27, 20 | 1 | 24-27 f8 7-8 popup |  |
| 14 | teleport 2, popup 3, launcher 2, bonus 2 |  |  |  f8 8 popup |  |
| 15 | homing | &31BC, 1-4, 13 | 1 | 1-4,10-11  |  |
| 16 | gun, mine 2 | &3171, 24-27, 30 | 2 | 24-27  | &6F8D:&1D-&20 &758D:&10-&1F |
| 17 | lights 2, teleport 2, ammo, grenades, popup | &3132, 16-19, 20 |  | 16-19 popup | &6F8D:&15-&1A |
| 18 | mine, teleport 2, ammo, spores |  | 2 |  f8 7 | &6F8D:&1D-&20 |
| 19 | gun | &31F1, 24-27, 20 | 1 | 24-27  | &758D:&10-&1F |
| 20 | spores 2, popup 2, launcher 2, bonus 2 |  |  |  f8 7-8 popup |  |
| 21 | ammo, grenades, spores | &3132, 16-19, 30 | 2 | 16-19 f8 7 |  |
| 22 |  | &31BC, 1-4, 13 | 2 | 1-4  |  |
| 23 | lights 2, gun, popup, launcher, bonus 3 |  | 3 |  f8 8 popup | &6F8D:&15-&1A &758D:&10-&1F |
| 24 | generator, levelend |  | 1 | 28-32  |  |
| 25 |  |  | 3 |   |  |
| 26 | mine | &31F1, 20-23, 8 | 2 | 20-23  | &6F8D:&1D-&20 |
| 27 | lights 5, ammo, grenades |  |  |   | &6F8D:&15-&1A |
| 28 | lights 4, spores, launcher 2, bonus 2 | &3132, 1-4, 16 | 1 | 1-4 f8 7-8 | &6F8D:&15-&1A |
| 29 | lights 3, gun, teleport 2, ammo | &31F1, 24-27, 25 | 1 | 24-27  | &6F8D:&15-&1A &758D:&10-&1F |
| 30 | lights 3, gun, spores, popup | &31F1, 24-27, 15 | 1 | 24-27 f8 7 popup | &6F8D:&15-&1A &758D:&10-&1F |
| 31 | ammo, grenades, popup 3 |  | 2 |  popup |  |
| 32 | gun, mine 2, teleport 2, launcher, bonus 3 |  | 1 |  f8 8 | &6F8D:&1D-&20 &758D:&10-&1F |
| 33 | teleport 2, ammo, grenades, launcher 2, bonus 2 | &3132, 16-19, 20 |  | 16-19 f8 8 |  |
| 34 | mine 3, ammo, grenades, spores 2, exoskeleton |  |  |  f8 7 | &6F8D:&1D-&20 |
| 35 | lights 2, mine, barrier |  |  |   | &38E5:&00 &6F8D:&15-&1A,&1D-&20 |
| 36 | ammo | &31BC, 20-23, 8 |  | 20-23  |  |
| 37 | teleport 2 | &3171, 1-4, 20 | 2 | 1-4  |  |
| 38 | teleport 2, spores 2, launcher 2, bonus 2 | &3171, 1-4, 8 |  | 1-4 f8 7-8 |  |
| 39 | lights 2, gun, popup, barrier | &3132, 16-19, 20 | 1 | 16-19 popup | &38E5:&00 &6F8D:&15-&1A &758D:&10-&1F |
| 40 | ammo, grenades, spores 2 |  | 4 |  f8 7 |  |
| 41 | lights 2, gun, teleport 2, ammo, grenades, spores, barrier |  | 2 |  f8 7 | &38E5:&00 &6F8D:&15-&1A &758D:&10-&1F |
| 42 | mine, popup 2 | &31F1, 24-27, 8 |  | 24-27 popup | &6F8D:&1D-&20 |
| 43 | lights, mine 2, ammo, homing | &31F1, 24-27, 8 | 2 | 10-11,24-27  | &6F8D:&15-&1A,&1D-&20 |
| 44 | grenades | &3132, 16-19, 20 | 2 | 16-19  |  |
| 45 | gun, teleport 2, launcher, bonus 3 |  | 1 |  f8 8 | &758D:&10-&1F |
| 46 | gun 2, ammo, grenades, spores 2, launcher 2, bonus 6 |  | 2 |  f8 7-8 | &758D:&10-&1F |
| 47 | lights 3, gun, spores, popup 3 |  | 2 |  f8 7 popup | &6F8D:&15-&1A &758D:&10-&1F |
| 48 | lights 2, teleport 2, launcher 2, bonus 2 | &31F1, 24-27, 20 | 1 | 24-27 f8 8 | &6F8D:&15-&1A |
| 49 | generator, levelend | &31BC, 16-19, 8 |  | 16-19,28-32  |  |
| 50 | lights 5, mine 6, homing, barrier |  | 1 | 10-11  | &38E5:&00 &6F8D:&15-&1A,&1D-&20 |
| 51 | homing | &31FA, 37-40, 9 | 1 | 10-11,37-40  |  |
| 52 | teleport 2, spores 2, launcher 2, bonus 2 |  |  |  f8 7-8 |  |
| 53 | gun, ammo, grenades, launcher, bonus 3 |  | 3 |  f8 8 | &758D:&10-&1F |
| 54 | ammo | &320F, 41-44, 30 | 1 | 41-44  |  |
| 55 | grenades, popup | &3132, 16-19, 9 | 4 | 16-19 popup |  |
| 56 | lights 2, teleport 2, ammo | &3171, 41-44, 9 |  | 41-44  | &6F8D:&15-&1A |
| 57 | lights 2, gun, ammo, grenades, launcher, bonus 3 |  | 1 |  f8 8 | &6F8D:&15-&1A &758D:&10-&1F |
| 58 |  | &320F, 16-19, 20 |  | 16-19  |  |
| 59 | lights 2, teleport 2, ammo, homing | &31F1, 37-40, 9 | 1 | 10-11,37-40  | &6F8D:&15-&1A |
| 60 | ammo, grenades, exoskeleton |  | 1 |   |  |
| 61 | gun, teleport 2, launcher, bonus 3 |  | 1 |  f8 8 | &758D:&10-&1F |
| 62 | lights 2, barrier | &31FA, 1-4, 9 |  | 1-4  | &38E5:&00 &6F8D:&15-&1A |
| 63 |  | &3132, 37-40, 9 |  | 37-40  |  |
| 64 | popup 2 | &31F1, 24-27, 9 |  | 24-27 popup |  |
| 65 | spores 2 |  | 3 |  f8 7 |  |
| 66 | teleport 2, spores 2 | &320F, 24-27, 30 | 1 | 24-27 f8 7 |  |
| 67 | ammo, spores, popup, launcher 2, bonus 2 |  | 1 |  f8 7-8 popup |  |
| 68 | lights 2, ammo, grenades, popup, barrier | &3132, 20-23, 8 |  | 20-23 popup | &38E5:&00 &6F8D:&15-&1A |
| 69 | spores, popup 3 | &31F1, 24-27, 40 | 2 | 24-27 f8 7 popup |  |
| 70 | mine 3, teleport 2, homing |  | 1 | 10-11  | &6F8D:&1D-&20 |
| 71 | gun, spores 2, launcher, bonus 3 |  | 3 |  f8 7-8 | &758D:&10-&1F |
| 72 | gun, popup | &320F, 16-19, 35 | 1 | 16-19 popup | &758D:&10-&1F |
| 73 | gun, launcher, bonus 3 |  | 1 |  f8 8 | &758D:&10-&1F |
| 74 | generator, levelend | &320F, 24-27, 12 | 1 | 24-32  |  |
| 75 | lights 2 | &3132, 16-19, 9 | 3 | 16-19  | &6F8D:&15-&1A |
| 76 | ammo, grenades | &31F1, 16-19, 9 |  | 16-19  |  |
| 77 | lights 2, teleport 2, launcher 2, bonus 2 | &31FA, 37-40, 9 |  | 37-40 f8 8 | &6F8D:&15-&1A |
| 78 | gun, mine 3, launcher, bonus 3 |  | 3 |  f8 8 | &6F8D:&1D-&20 &758D:&10-&1F |
| 79 | ammo, grenades, spores | &31BC, 1-4, 9 | 1 | 1-4 f8 7 |  |
| 80 | ammo, homing | &320F, 41-44, 30 | 1 | 10-11,41-44  |  |
| 81 | gun, mine, teleport 2, popup 2, launcher, bonus 3 |  | 1 |  f8 8 popup | &6F8D:&1D-&20 &758D:&10-&1F |
| 82 | ammo, grenades, spores, homing |  | 2 | 10-11 f8 7 |  |
| 83 |  | &320F, 41-44, 9 |  | 41-44  |  |
| 84 | ammo, grenades | &31FA, 41-44, 9 | 2 | 41-44  |  |
| 85 |  | &31BC, 16-19, 8 |  | 16-19  |  |
| 86 | teleport 2, ammo | &31F1, 20-23, 9 |  | 20-23  |  |
| 87 | ammo, launcher 4, bonus 4 |  |  |  f8 8 |  |
| 88 | popup, homing |  | 1 | 10-11 popup |  |
| 89 | lights 2, mine 3, ammo, grenades | &3171, 24-27, 9 |  | 24-27  | &6F8D:&15-&1A,&1D-&20 |
| 90 | ammo, grenades, popup 2, exoskeleton | &31F1, 37-40, 8 | 2 | 37-40 popup |  |
| 91 | teleport 2 | &31FA, 41-44, 25 | 2 | 41-44  |  |
| 92 | lights 2, homing, barrier |  | 1 | 10-11  | &38E5:&00 &6F8D:&15-&1A |
| 93 | gun, mine 2, ammo, grenades |  | 1 |   | &6F8D:&1D-&20 &758D:&10-&1F |
| 94 | spores 2 | &3171, 20-23, 16 | 5 | 20-23 f8 7 |  |
| 95 | lights 2, teleport 2, ammo, grenades, launcher 2, bonus 2 |  |  |  f8 8 | &6F8D:&15-&1A |
| 96 | lights 2, mine 5, spores, popup | &320F, 24-27, 30 | 1 | 24-27 f8 7 popup | &6F8D:&15-&1A,&1D-&20 |
| 97 | lights 2, gun 2, ammo, grenades, launcher 2, bonus 6 |  | 2 |  f8 8 | &6F8D:&15-&1A &758D:&10-&1F |
| 98 | lights 2, mine 3, spores 2 | &320F, 41-44, 35 | 1 | 41-44 f8 7 | &6F8D:&15-&1A,&1D-&20 |
| 99 | mine, generator, levelend | &31BC, 16-19, 8 | 1 | 16-19,28-32  | &6F8D:&1D-&20 |
| 100 | lights 2 |  | 1 |   | &6F8D:&15-&1A |
| 101 | mine | &31F1, 20-23, 8 | 2 | 20-23  | &6F8D:&1D-&20 |
| 102 | lights 5, ammo, grenades |  |  |   | &6F8D:&15-&1A |
| 103 | lights 4, spores, launcher 2, bonus 2 | &3132, 1-4, 10 | 1 | 1-4 f8 7-8 | &6F8D:&15-&1A |
| 104 | lights 3, gun, teleport 2, ammo | &31F1, 24-27, 10 | 1 | 24-27  | &6F8D:&15-&1A &758D:&10-&1F |
| 105 | lights 3, gun, spores, popup | &31F1, 24-27, 10 | 1 | 24-27 f8 7 popup | &6F8D:&15-&1A &758D:&10-&1F |
| 106 | ammo, grenades, popup 3 |  | 2 |  popup |  |
| 107 | gun, mine 2, teleport 2, launcher, bonus 3 |  | 1 |  f8 8 | &6F8D:&1D-&20 &758D:&10-&1F |
| 108 | teleport 2, ammo, grenades, launcher 2, bonus 2 | &3132, 16-19, 10 |  | 16-19 f8 8 |  |
| 109 | mine 3, ammo, grenades, spores 2, exoskeleton |  |  |  f8 7 | &6F8D:&1D-&20 |
| 110 | lights 2, mine, barrier |  |  |   | &38E5:&00 &6F8D:&15-&1A,&1D-&20 |
| 111 | ammo | &31BC, 20-23, 8 |  | 20-23  |  |
| 112 | teleport 2 | &3171, 1-4, 20 | 2 | 1-4  |  |
| 113 | teleport 2, spores 2, launcher 2, bonus 2 | &3171, 1-4, 8 |  | 1-4 f8 7-8 |  |
| 114 | lights 2, gun, popup, barrier | &3132, 16-19, 10 | 1 | 16-19 popup | &38E5:&00 &6F8D:&15-&1A &758D:&10-&1F |
| 115 | ammo, grenades, spores 2 |  | 4 |  f8 7 |  |
| 116 | lights 2, gun, teleport 2, ammo, grenades, spores, barrier |  | 2 |  f8 7 | &38E5:&00 &6F8D:&15-&1A &758D:&10-&1F |
| 117 | mine, popup 2 | &31F1, 24-27, 8 |  | 24-27 popup | &6F8D:&1D-&20 |
| 118 | lights, mine 2, ammo, homing | &31F1, 24-27, 8 | 2 | 10-11,24-27  | &6F8D:&15-&1A,&1D-&20 |
| 119 | grenades | &3132, 16-19, 10 | 2 | 16-19  |  |
| 120 | gun, teleport 2, launcher, bonus 3 |  | 1 |  f8 8 | &758D:&10-&1F |
| 121 | gun 2, ammo, grenades, spores 2, launcher 2, bonus 6 |  | 2 |  f8 7-8 | &758D:&10-&1F |
| 122 | lights 3, gun, spores, popup 3 |  | 2 |  f8 7 popup | &6F8D:&15-&1A &758D:&10-&1F |
| 123 | lights 2, teleport 2, launcher 2, bonus 2 | &31F1, 24-27, 10 | 1 | 24-27 f8 8 | &6F8D:&15-&1A |
| 124 | generator, levelend | &31BC, 16-19, 8 |  | 16-19,28-32  |  |

## The Spectrum original
Checked by aligning each CPC routine with its Spectrum twin instruction by instruction (`work/objects/speccmp.py`,
`specall.py`; addresses mapped as they're met, every 8-bit constant compared), the data tables byte by byte, and
the zones' placements and scripts through `tools/zoneobjects.py` with the Spectrum's addresses (zones `&C7F4`,
scripts `&852E`, boxes `&94C6`, aliens `&A677`). One run on the Spectrum (`work/objects/speczone.py`): zone 2's
popup keeps the same timetable.

- **The same**: every object routine above, apart from sound and colour calls; every constant (chances, speeds,
  timers, boxes, hit counts, points); the list sizes and the descriptors (`&8EF4`); the tables (debris speeds,
  explosion frames, gun frames, boxes, grenade arc, death fall, scores, level starts, the alien table's zones,
  frames and gaps). The main loop calls them in the same order.
- **The zones' placements are identical** in all 125 zones (the same rows, columns and objects).
- **Different, affecting play**:
  - CPC objects 41, 48, 49 and 51 are empty scripts (`&FF`); the Spectrum's draw scenery. Zone 22 loses a mound
    (41), zones 25 and 26 diagonal struts (48, 49), zones 25 and 66 a pair of hanging posts with an arc between
    (51, with a kind-15 marker). So the Spectrum has generators in 25 and 66 too, and 9-44 more solid cells in
    those zones. Object 18 is empty on both.
  - Alien path `&31FA` (zones 51, 62, 77, 84, 91): after rising 32 lines it sinks 8 on the CPC (`&3203` = 8) and
    24 on the Spectrum (`&18`). A CPC alien on it ends 24 lines higher than it started; a Spectrum one 8.
- **Different, not affecting the rules**: the Spectrum's big explosion calls the generator twice a pass (a colour
  and a beeper burst), and its stars are placed after the scenery on empty attribute cells with one call each;
  so the random streams differ and lockstep must follow one version. The CPC's `CALL &0E81`/`&0E82` with B = n
  (a RET) are the Spectrum's beeper (`&7C26`) stubbed out.

## For the BBC
- **Clipping instead of masking**: a 16- or 32-line sprite isn't drawn at all in a cell whose `&B700` is 0. With
  the tile map, that's a flag per tile: foreground tiles hide sprites, so they're skipped rather than composed.
  Only `&EA` (background) objects need composing under sprites. The 8-line XOR objects show over everything.
- **The CPC's way that can go**: run-time shifting and the image buffers (the BBC's sprites are self-erasing);
  the 8 spores' cancelling XORs at set-up; the gun's frame-and-blocks XOR dance (a stored frame per state does);
  the dummy `&0E81` calls; the colours the generator is called for (but keep the calls, for lockstep); the
  descriptor table (the BBC can build its lists straight from a packed per-zone list of markers made at build
  time by `tools/zoneobjects.py`).
- **Borders**: 2 bytes and 8 lines covers every object; most need 1 byte (2 pixels) and no lines.
- **Timing**: everything here counts passes, so at 25 a second (D8) it all runs 20% faster than the CPC's 20.9:
  the time-out missile comes after 28 seconds, not 33.
- **Quirks to keep or fix** (Rich decides): the exoskeleton protects only from mines and popups; enemies that kill
  the player still score; the barrier kills only at px + 12 = 4 col exactly; the launcher scan stops early;
  a full explosion or debris list drops the effect; the CPC's four empty objects and its path byte (above).
