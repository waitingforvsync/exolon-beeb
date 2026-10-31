# Exolon (CPC): Vitorc, the player

A spec of everything the player does in the CPC original: moving, the laser, grenades, the suit, pickups,
teleports, death, leaving a zone, scoring and the status rows. From its code (`build/exolon.skool`) and the
Spectrum original's (`build/spec/exolon64k.bin`), for the BBC version's game logic. Checked in the harness
(`tools/cpc.py`, and `tools/spectrum.py` for the Spectrum) with the scripts in `work/player/` unless marked
*unverified*. 2026-10-31.

## Summary
- **Walking**: 1 pixel a pass; a 10-frame cycle (frames 0-9) that runs on through stops and turns. A turn
  takes one pass standing still (frame 5) while `&0E04` mirrors all 24 frames in place: that pass takes 146 ms
  against about 50 (96.7 ms more). The BBC needs no stall, but the pass without a step is part of the rules.
- **Jumping**: up held on the ground. 22 passes in the air: up 4, 4, 2, 2, 2, 1, 1, 1, 1 (18 lines), 4 passes
  level, down 1, 1, 1, 1, 2, 2, 2, 4, 4; frame 3. It keeps the direction he was walking the pass before, 1 pixel
  a pass (22 in all), and ignores the keys. Up still held, he jumps again the pass after landing.
- **Falling**: 4 lines a pass straight down, frame 9, no steering. **Ducking**: down held, frame 10, no
  movement; his hit box loses its top 6 lines and he fires 5 lines lower.
- **Scenery** is the solid map at `&BA00` (any non-zero cell), probed only at cell boundaries. The boxes from
  `&219C` aren't for movement: they're the objects a grenade can destroy.
- **The laser**: one bolt a press of fire, 5 pixels a pass, up to 8 at once, 52 pixels' range to the right (48
  to the left), stopped by scenery; 99 shots. With the suit, two bolts a shot.
- **Grenades**: fire held 15 passes (no extra key: D17 stands). One at a time, 10 a life. A slow rise, a level
  flight, then a 45-degree fall, 3 steps a pass after the first 13. It destroys only scenery objects of 10
  types (150 points), and with them any gun built in; it never hits enemies.
- **The suit** (exoskeleton): put on or off by pressing up in its booth. Frames + 12, double laser, immunity to
  mines and popups only. Kept through deaths, taken off at a stage's end.
- **Death**: a 46-pass leap (up through anything, down to the floor), then the respawn at the zone's left edge
  at the height he came in, 20 passes' invulnerability, ammo and grenades refilled. 9 lives, one more at each
  stage's end (9 at most), none for score.
- **Zones**: x reaching 128 is the next zone, x = 0, the same y. x = 0 is a wall: no way back.
- **The time limit**: 700 passes in a zone (counted again from each death), then a time-out missile at his
  height, and another each time one ends.
- **Score**: 50 (launcher missiles, spores), 150 (aliens, scenery), 850 (the homing-missile launcher with its
  missile in flight), 1,000 (the barrier, each launcher bonus cell), and at a stage's end 1,000 a life, 10,000
  without the suit and the bonus screen's 0-7,000. Some arrive through a pool at 25 a pass. Enemies that hit
  him score too.
- **The Spectrum** runs the same code for all of this: 136 passes of walking, jumping, turning, firing,
  grenades and ducking matched the CPC exactly. The only difference in play: the CPC stops the death leap's
  fall at line 192.

## Conventions
- Addresses are the CPC's, `&xxxx`; Spectrum twins "Spectrum `&xxxx`". Time in passes.
- x (`&10EE`) is the left edge of his 12-pixel width in MODE 0 pixels, 0-127 (2 Spectrum pixels each). y
  (`&10EF`) is the top of his 32 lines, 0-191. On the floor of zone 0 he stands at y = 112 (feet on line 143).
- Cells: column = x / 4, row = y / 8, 32 × 24 (the Spectrum's character cells). "Aligned" x is a multiple of
  4, aligned y a multiple of 8.
- Direction bytes are 1 (right), `&FF` (left) or 0.
- Kind n (2-17) is an object's marker in the map; the objects' names are agent C's (`docs/cpc-objects.md`).

## Variables
| Address | Size | Meaning | Range |
|---|---|---|---|
| `&10EE` | 1 | x | 0-127 (128 for the zone exit, never stored) |
| `&10EF` | 1 | y | 0-191 |
| `&10EC`, `&10ED` | 1 + 1 | Respawn x, y: where he entered the zone | |
| `&10F0` | 1 | Jump counter | 22 → 0; 0 = on the ground or falling |
| `&108D` | 1 | Fell last pass | 0 / 9 |
| `&10F1` | 1 | Walking direction this pass, and a jump's | 1, `&FF`, 0 |
| `&10F2` | 1 | Walk cycle | 0-9 |
| `&10F3` | 1 | Facing, for firing | 1, `&FF` |
| `&0E63` | 1 | Frames mirrored (facing left) | 0 / 1 |
| `&10F4` | 1 | Ducking | `&FA` / 0 |
| `&1062` | 1 | Frame last plotted (`&FF` forces a plot) | 0-23 |
| `&2BDB` | 1 | Suit: added to the frame | 0 / 12 |
| `&10EB` | 1 | Left the zone this pass (his y) | 0 / y |
| `&11C4` | 1 | Passes fire held | 0-255 |
| `&1BB4` | 1 | Ammo | 0-99 |
| `&1BC0` | 1 | Grenades | 0-10 |
| `&1BD4` | 1 | Lives | 0-9 |
| `&1239`-`&1250` | 24 | Laser bolts: 8 × (x, y, direction; 0 = free); `&1251` = `&FF` ends | |
| `&1F84`-`&1F88` | 5 | Grenade: counter (32 → 1, 0 = none), x, y, direction, frame (0 right, 1 left) | |
| `&29E7` | 1 | Dying, passes left | 46 → 0 |
| `&078C` | 1 | Invulnerable, passes left | 0-66 |
| `&3B3B`-`&3B40` | 6 | Score, ASCII digits, most significant first | "000000"-"999999" |
| `&2BD9` | 2 | Score pool, 25-point units | |

The Spectrum's: x, y `&82F5`, `&82F6`; jump `&82F7`; frame `&8269`; bolts `&845F`; grenade `&925A`; ammo
`&8E5A`, grenades `&8E66`, lives `&8E7A`.

## A pass of the player: `&0FA2`
Nothing happens while dying (`&2A80` returns from the caller when `&29E7` ≠ 0). Otherwise `&10EB` = 0 and:

1. **Fell last pass** (`&108D` ≠ 0): go to 4.
2. **In a jump** (`&10F0` ≠ 0): the jump step (below), then plot.
3. **On the ground?** Probe below (`&0F4C`); nothing there: go to 4. On the ground:
   - down held: duck. `&10F4` = `&FA`, frame 10, no movement. Plot.
   - else `&10F4` = 0; up held: start a jump (counter 22) and take its first step. Plot.
   - else go to 4.
4. **Fall or walk** (`&1079`): `&108D` = 0; probe below. Nothing there: y + 4, `&108D` = 9, frame 9. Plot.
   Something there: walk (below). Plot.

Then `&1022`: frame + `&2BDB`; if x = 128, the zone exit (below). Else store x, y; if the frame and the place
are both unchanged, nothing; else plot with `&07D9` (plot record `&3FFE`).

So a fall can't turn into a jump or a duck until he has landed and walked a pass, and the landing pass is a
walking pass: he steps on the pass after reaching the floor (`work/player/fall.py`).

## Walking and turning (`&108E`)
- `&10F1` = left XOR right: neither or both, he stands (frame 5, `&10F1` = 0).
- Left held: `&10F1` = `&FF`, `&10F3` = `&FF`. If the frames face right, mirror them (`&0E04`) and stand this
  pass, frame 5, the plot forced. Else probe left; blocked, stand (frame 5); free, x - 1 and the next walking
  frame. Right is the same the other way.
- The walking frame is `&10F2`, 0-9, and then `&10F2` + 1 (10 wraps to 0). Nothing resets it: a stop or a turn
  carries on from the frame before (measured: frames 7, turn, 8, 9, 0...).
- **The turn** (`&0E04`): XORs `&0E63` and reverses all 24 frames in place, 4,608 bytes, each byte through the
  pixel-swap table at `&BD00`. Measured (`work/player/turn.py`): the turn pass takes 146,399 µs against 49,650
  for its neighbours, 96.7 ms more, and x doesn't change. The respawn turns him back to the right the same way.
  The Spectrum does the same (`&7BAA`, 2,304 bytes of 1-bit frames).

For the BBC: one facing kept and mirrored as it's plotted (P5), so the stall goes. The pass without a step is
play, not the stall: a turn costs a pixel. Keep it unless Rich says otherwise.

## Jumping (`&0FE1`)
The arc is the table `&1062`-`&1078` read by the counter before it's decremented (index 22 first, 1 last):

| Counter | 22 | 21 | 20 | 19 | 18 | 17 | 16 | 15 | 14 | 13-10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| y step | -4 | -4 | -2 | -2 | -2 | -1 | -1 | -1 | -1 | 0 | +1 | +1 | +1 | +1 | +2 | +2 | +2 | +4 | +4 |

- Each step: a rising step (table ≥ `&0A`, i.e. negative) probes above, a falling one below, from where he is
  before the step. Blocked: the jump ends (counter 0) and the pass goes on to fall or walk (4 above). Free: y +
  step. Then x + `&10F1` if the probe that way is free. Frame 3 throughout.
- `&10F1` is whatever the last walking pass set: walking right the pass before take-off, he jumps right; standing,
  straight up. Keys are ignored in the air: no steering, no turning, no firing changes (he can fire and throw).
- From the floor at 112: 108, 104, 102, 100, 98, 97, 96, 95, 94, 94 × 4, 95, 96, 97, 98, 100, 102, 104, 108, 112
  (`work/player/walkjump.py`). A running jump covers 22 pixels (`runjump.py`).
- The steps keep y on the probes' grid: from an aligned start the arc is aligned at 104 and 96 both ways, so
  it lands on any floor 8 or 16 lines higher, and can be stopped by a ceiling 8 or 16 lines up.
- Up held: the pass that lands (counter 0, y back on the floor) is the last; the next pass takes off again. A
  22-pass cycle (`runjump.py`).
- A jump under a low ceiling (the teleports' and the suit's booths) fails at its first step: the walking runs
  instead, so pressing up in a booth doesn't jump (checked on zone 2's teleport pad).
- A jump in progress at the zone exit carries on in the next zone (`&10F0` isn't cleared).

## Falling and ducking
- **Falling** (`&1079`): 4 lines a pass, frame 9, x unchanged whatever is held. The probe below only looks at
  aligned y, so he falls in steps of 4 until an aligned y with something under. Checked from y = 80: 84 ... 112,
  then a step on the next pass (`fall.py`).
- **Ducking** (`&0FC5`): down held on the ground. Frame 10, no movement, and left, right and up are ignored.
  `&10F4` = `&FA` while ducking: a bolt starts at y + 19 instead of 14, a grenade at y + 6, and the collision box
  starts 6 lines lower (`&28E0`). Checked (`duck.py`).

## Frames
| State | Frame | With the suit |
|---|---|---|
| Walking | 0-9 in turn | 12-21 |
| Jumping | 3 | 15 |
| Standing (and the turn pass) | 5 | 17 |
| Falling | 9 | 21 |
| Ducking | 10 | 22 |
| Dying | 11 | 23 |

24 frames of 6 bytes × 32 lines at `&93CD` (agent A); frame 24, past them, is the popups'. `&1022` takes the
frame in A, adds `&2BDB` and plots only if the frame or the place changed; `&1062` = `&FF` forces a plot (game
start, zone change, turn, pickups). Checked: walking 0-9, jump 3, stand 5, fall 9, duck 10, death 11, and 12,
13, 17, 22 in the suit.

## Scenery: the solid map
Every probe reads the solid map at `&BA00` (`&0ED8`: `&BA00` + row × 32 + column); any non-zero cell is solid.
The other map, `&B700`, is never read for movement (its lookup `&0EBF` is never called).

| Probe | Routine | Looks at | Only when |
|---|---|---|---|
| Right | `&0EF1` | column x/4 + 3, rows y/8 to y/8 + 3, and y/8 + 4 if y isn't aligned | x aligned and x < 116 (from 116 on, always free) |
| Left | `&0F20` | column x/4 - 1, the same rows | x aligned; x = 0 is always blocked |
| Below | `&0F4C` | row y/8 + 4, columns x/4 to x/4 + 2, and x/4 + 3 if x isn't aligned (x ≥ 116: column x/4 only) | y aligned |
| Above | `&0F77` | row y/8 - 1, the same columns | y aligned |

Off the aligned positions the probes say free: he can only be stopped at cell boundaries, and his box is 3
cells wide by 4 tall when aligned. The probes run before the step they guard.

## The laser (`&1120`, `&1179`, `&11C5`)
- **Firing**: on the first pass fire is seen down (`&11C4` 0 → 1), if not dying, x < 118 and ammo > 0: ammo -
  1 (the `DEC A` at `&1159` is the infinite-ammo poke), the sound, the ammo redrawn, a bolt; with the suit a
  second bolt 6 lines lower. The shot is spent even if no bolt can start. Held, nothing more: release and press
  again (a bolt every second pass at most).
- **A bolt starts** in a free slot of 8 (none free: no bolt) at x + 12 facing right or x - 4 facing left, y +
  14 (+ 19 ducking), moving the way he faces (`&10F3`). It doesn't start if that x is outside 4-119, or either
  cell under it (column x/4 or x/4 + 1, row y/8) is solid. It's a 4-pixel, 1-line dash, XORed (`&10F5`).
- **Each step** (`&11C5`, five a pass): the hit tests run (spores, launcher missiles, flying aliens, the
  barrier: agent C), then each bolt is erased and:
  - right: gone at x = 124; at aligned x, a solid cell at column x/4 + 1, row y/8 stops it with a small
    explosion (`&2521`) and a sound. Left: the same at column x/4 - 1.
  - gone at x = 124 or 1, or when x equals his x + 64 or his x - 52 (his x now, not when fired);
  - else x + 1 or - 1, drawn.
- So a bolt flies 5 pixels a pass; standing, it's seen at x + 17, + 22 ... and dies after 10 passes, 52 pixels
  out to the right, 48 to the left (`fire.py`). He can never outrun it, so the range always ends it, except
  after a teleport moves him (then it flies to the edge).
- Every bolt can hit anything the tests cover, at every pixel.
- **Ammo**: 99 at a game's start, at each death and at each stage's start; set (not added) to 99 by an ammo
  pickup (kind 7).

## Grenades (`&1F32`, `&1F89`, `&20F7`)
- **Throwing**: fire held 15 passes (`&11C4` ≥ 15), not dying, x < 118, grenades > 0, none in flight. Grenades
  - 1 (the `DEC A` at `&1F7A` is the poke), the sound, the count redrawn. Held on, another goes the pass after
  the first ends (checked: thrown on the 15th, 43rd and 77th passes of one hold, `grenades2.py`). The press
  that starts the hold also fired a bolt (if there was ammo). So one fire key is enough: D17 holds, no sixth
  key.
- **Start**: x + 4, y (+ 6 ducking), the way he faces; counter 32; 8-line object frame 0 (right) or 1 (left),
  XORed.
- **A step** (`&1F89`) with counter c (it counts down to 1 and stays): erase; gone at x = 124 or 0; probe the
  cell ahead (column x/4 ± 1, rows y/8 and y/8 + 1 if y isn't aligned; only at aligned x) and end if solid;
  x ± 1; unless the step is -1, probe below (row y/8 + 1 at aligned y) and end if solid; y + step; end at y ≥
  168; draw; while c ≥ 19, a small explosion 4 pixels behind it.
- **The arc** (`&2000`-`&201F` by c):

| c | 32 | 31 | 30 | 29 | 28 | 27-24 | 23-2 | 1 (and after) |
|---|---|---|---|---|---|---|---|---|
| y step | -4 | -4 | -2 | -2 | -2 | -1 | 0 | +1 |

  Up 18 lines in 9 steps, level for 22, then down 1 a step until it hits something: a 45-degree fall. Every step
  is 1 pixel across.
- **Speed**: one step a pass while c ≥ 19 after the first call, so 13 passes (c 32-20), then three a pass.
  Measured from x = 16, y = 112: the throw pass ends at (21, 108); level at 94 from x = 29; three a pass from the
  14th; it fell to (76, 119) and hit the ground there (`fire.py`).
- **The blast** (`&1FF9`, `&20F7`): counter 0; if the cell under its last position, (x/4, y/8), is inside a
  destructible box, that object is destroyed: redrawn in mode 3 (erased, throwing debris), the box marked `&80`,
  a sound, 150 points. One object a grenade. The boxes are made at zone setup (`&219C`, list `&214C`, 7 bytes
  each: x0, x1, y0, y1 in cells, the placement's column, row, object) for the 10 object types in `&21DB`:

| Object | Box (columns, rows from its placement; end exclusive) |
|---|---|
| 5 | -1 to +7, -2 to +3 |
| 13 | -3 to +2, -2 to +8 |
| 15 | -2 to +5, -1 to +8 |
| 16 | -2 to +4, -2 to +6 |
| 18 | -6 to +5, +1 to +8 |
| 21 | -2 to +5, -2 to +6 |
| 31 | -1 to +5, -2 to +4 |
| 40 | -1 to +5, -2 to +6 |
| 44 | -1 to +7, -2 to +2 |
| 46 | -1 to +4, -2 to +4 |

- Nothing else reads the grenade's position: it never hits enemies. But a destroyed object takes its guns with
  it (the gun emplacements and the homing-missile launcher check their cells; agent C). Checked: zone 0's gun
  (object 5 at column 20, row 14) destroyed from x = 36, +150; its alien pod (object 13) from x = 64
  (`exitzone.py`).
- **Grenades**: 10 at a game's start, at each death and each stage's start; set to 10 by a grenade pickup.

## The suit (`&2C30`)
- One booth (kind 12) in some zones: 9, 34, 60, 90, 109 (`work/player/zonescan.py`, `zonescan.txt`).
- Up pressed (latch `&2C70`) with y = (row + 1) × 8 and x - column × 4 between -12 and 8: `&2BDB` XOR 12, a
  sound, a plot. So the same press takes it off again.
- **What it does**: frames + 12; two bolts a shot, at y + 14 and y + 20, for one ammo; and `&29AF` spares him
  from mines (kind 5) and popups (kind 10). Nothing else: gun shots, missiles, spores, aliens, the barrier and
  the time-out missile still kill.
- Kept through deaths and zone changes; taken off at each stage's end, where not wearing it earns 10,000.
- Checked in zone 9 (`suit.py`, `suitdeath.py`).

## Pickups and teleports
- **Ammo** (kind 7, `&26EC`) and **grenades** (kind 8, `&26EF`), at most one of each a zone (`&263C`): taken
  when y = (row - 2) × 8 and x - (column + 1) × 4 is -12 to -1. Ammo = 99 or grenades = 10, the object erased
  (scripts `&1656`, `&1667` in mode 4), a sound, the count redrawn, the player replotted. Gone for good (`&FF`).
  Checked: zone 1's grenades at column 28, row 16, taken at x = 104 (`pickup.py`).
- **Teleports** (kind 6, two pads `&262A`, `&262C`; `&25B4`): up pressed (latch `&262F`) with y = (row + 1) ×
  8 and x - column × 4 between -12 and 8 on one pad: he's put at the other, x = column × 4 - 3, y = (row + 1)
  × 8, frame 5; sparkles at both pads for 20 passes; a sound. Checked in zone 2: (16, 112) to (89, 56) and back
  to (17, 112) (`teleport.py`).

## Death
**Killed** (`&29B4`) unless dying already or invulnerable (`&078C` ≠ 0): the zone timer `&3987` = 0, the jump
ended, `&11C4` = 0, `&29E7` = 46, `&078C` = 66, and frame 11 plotted with y rounded down to a multiple of 4
(y AND `&FC`, stored).

| What kills | Routine | Its box (w × h, pixels × lines) | The suit saves him |
|---|---|---|---|
| Gun shots | `&1E31` | a point | no |
| Spores (from kind 9) | `&28BE` | 4 × 8 | no |
| Popups (kind 10), when up | `&2990` | 12 × 32 | yes |
| Launcher missiles | `&2B67` | 4 × 8 | no |
| The homing missile (kind 13) | `&2F6E` | 8 × 16 | no |
| Flying aliens | `&3320` | 4 × 8 | no |
| The barrier (kind 17): his x + 12 = its x | `&38F5` | | no |
| The time-out missile (the time limit) | `&3989` | 8 × 16 | no |
| Mines (kind 5), stood on | `&1E7C` | | yes |

His box (`&28E0`): an object at (E, D), w × h, hits him if E ≤ x + 12, E + w - 1 ≥ x, D ≤ y + 32 and D + h - 1
≥ y (≥ y + 6 ducking). Agent C has each object.

**The leap** (`&29E8`, 46 passes): the table `&2A52`-`&2A7F` by the counter: -4, -4, -2, -2, -2, -1, -1, -1,
-1, 0 × 4, +1 × 4, +2 × 3, then +4. Rising steps go through anything; falling steps stop on a solid cell below
(aligned y). Frame 11 (23 in the suit); x unchanged. The CPC stops plotting at y ≥ 192 (`&2A0E`); the Spectrum
has no such test. Checked: killed at y = 96, up to 78, down to the floor at 112 (`death.py`).

**The respawn** (the 46th pass, `&2A16`): faces right again (frames unmirrored), lives - 1 (the `DEC A` at
`&2A25`), ammo 99, grenades 10, the three redrawn. No lives left: game over (`docs/cpc-flow.md`). Else he's put
at (`&10EC`, `&10ED`) and dropped a line at a time to the first aligned y with something under him, all in this
pass; frame 5.
- The respawn point is where he entered the zone: x = 0 and the y he left the last zone at; at a game's or a
  stage's start, the stage's start point. In zone 0: (16, 112).
- **Invulnerable** for 20 passes from the respawn pass (`&078C`: 66 - 46), with no sign on screen. Entering a
  zone ends it (`&1278`).
- The zone carries on: what's destroyed or taken stays so; the timer restarts.
- **Lives**: 9 at the start; one more at each stage's end, 9 at most; none for score.
- Pokes: `&2A25` = 0 infinite lives (the ZORBA cheat toggles the same byte: flow doc); `&0779` and
  `&1278`-`&127A` = 0 with `&078C` = 1 invulnerable for ever.

## Leaving a zone
- x reaches 128 (walking or jumping right from 127; the right probe is free from 116 on): `&104C` keeps y
  (`&10EF`, `&10ED`), sets `&10EB`, zone `&12FA` + 1, forces a plot. x isn't stored.
- In the same pass `&125F`: x = 0, respawn x = 0, the zone number redrawn, and the zone set up (`&126E`): the
  timer, the grenade, the invulnerability, the time-out missile and the bolts all cleared, the screen drawn
  (agent A).
- He stands at (0, y) in the new zone, falling if nothing's under him. Measured: 127 → 0, y 112 kept, the pass
  268 ms (`exitzone.py`).
- **No way back**: x = 0 always blocks left. The zone ends at the right edge only.

## The time limit (`&3965`)
- `&3987` counts the passes since he entered the zone or last died. From 700 (`&02BC`), whenever no time-out
  missile is flying, one starts at x = 120 at his y of that moment and flies left 2 pixels a pass at that height
  (agent C). It can't be shot, the suit doesn't help, and it kills; a death resets the count, so the next comes
  700 passes later. Without a death, they keep coming one after another.
- Checked in zone 1 standing still (`timelimit.py`): the count reached 700 on the 700th pass, the missile
  appeared at x = 118 after its first step, and killed him at x = 16 on the 746th pass.
- 700 passes is 33.5 s on the CPC (20.9 passes a second), 28 s on the BBC (25): Rich decides whether to keep
  the passes or the seconds.

## Score
| How | Points | Where | Checked |
|---|---|---|---|
| A launcher missile shot, or hitting him | 50 | `&2B52` | yes, zones 6 and 13 (`shoot.py`) |
| A spore shot, or hitting him | 50 | `&2875` | code |
| A flying alien shot, or hitting him | 150 | `&3359` | yes, zones 3 and 13 |
| A scenery object destroyed by a grenade | 150 | `&20F7` | yes, zone 0 |
| The homing-missile launcher destroyed with its missile in flight | 850 (34 × 25, pool), on top of the scenery's 150 | `&2F6E` | code |
| A launcher bonus cell touched (each once a visit) | 1,000 (pool) | `&303E` | code |
| The barrier destroyed (25 bolt hits) | 1,000 (pool) | `&3910` | code |
| A stage's end: each life left | 1,000 | `&352D` | yes |
| A stage's end without the suit | 10,000 (80 × 125) | `&352D` | yes |
| The bonus screen | 0, 1,000, 3,000, 5,000 or 7,000 | `&35F4` | yes |

- The score is six ASCII digits at `&3B3B`, the text of its own print script (`&3B33`). `&3B04` adds a six-digit
  string from the table `&3B42`-`&3B7D` (25, 50, 100, 125, 150, 200, 250, 300, 350, 1,000) digit by digit and
  reprints all six. A carry out of the top digit is lost: it wraps at 1,000,000.
- The pool `&2BD9` (`&2BB2` adds A units) pays 25 points a pass (`&2BC4`).
- Points for enemies that hit him are added before he's killed, so they count even on the last life.

## The status rows
Drawn by `&078F` at a game's and each stage's start: row 22 the labels (script `&07A1`), row 23 blanked, then
the five numbers. Columns are character cells (2 CPC bytes). The colour byte C is the Spectrum's attribute
(INK in bits 0-2, BRIGHT in bit 6); the CPC takes INK + 8 × BRIGHT as the pen.

| Shows | Variable | Row 23, columns | Pen | Redrawn |
|---|---|---|---|---|
| AMMO | `&1BB4` | 1-2 (`&1BA9`: two digits, the hundreds never printed) | 15 (cycles) | each shot, ammo pickup, respawn |
| GRENADES | `&1BC0` | 8-9 (`&1BB5`) | 11 | each throw, grenade pickup, respawn |
| POINTS | `&3B3B` | 14-19 (`&3B33`) | 13 | each addition |
| LIVES | `&1BD4` | 23, one digit (`&1BC1`) | 14 | respawn |
| ZONES | `&12FA` | 28-30, three digits, the zone's index 0-124 (`&1BD5`) | 14 | zone change |

Labels on row 22: AMMO (columns 0-3, pen 13), GRENADES (5-12, pen 14), POINTS (14-19, pen 12), LIVES (21-25,
pen 15), ZONES (27-31, pen 11). Pen 15 is the one `&39D8` cycles every pass (agent A). Checked against the
harness's screen (`work/player/zone1.png`).

## Against the Spectrum
Compared routine by routine (`work/player/xcheck.sh`, `sidebyside.py`) and run in lockstep (`speccmp.py`: the
same keys into both for 136 passes; x, y, the jump counter, the frame, the bolts, the grenade, ammo and grenades
equal every pass).
- The same code: `&0FA2` (`&81A4`), `&1120` (`&8338`), `&1179`, `&11C5` (`&83DD`), `&1F32` (`&9208`), `&1F89`
  (`&925F`), `&25B4`, `&263C`, `&2C30`, `&29B4`, `&29E8`, `&2BB2`, `&2BC4`, `&3B04`, `&28E0`; and the same
  tables (jump, grenade and death arcs, the score values, the stages' start points).
- Different, outside play: the plot colours (the Spectrum's attribute calls), the sounds (the Spectrum's beeps
  block: 20 × 20 on a bolt's hit, one a shot, one per 25 points of pool), the player's frames (3 bytes of 1-bit
  pixels) and the mirroring (`&7BAA`).
- Different in play: only the death leap's y ≥ 192 test (CPC only). The Spectrum's controls: O, P, Q, A, M
  (fire), or Interface 2 or Kempston.
