# Exolon (CPC): the main loop and a pass

A spec of the CPC original's main loop (`&06C3`-`&0788`) and what one pass does, from its code (the image
`&0100`-`&B1CC`, `build/exolon.skool`) and the Spectrum original it was ported from (`build/spec/exolon64k.bin`),
for the BBC version's game logic. Checked in the harness (`tools/cpc.py`, `tools/spectrum.py`) with the scripts
in `work/player/` unless marked *unverified*. 2026-10-31.

## Summary
- **A pass** is one trip round `&06C3`-`&0788`: 53 calls (two of them conditional), then three counters. No
  interrupts, no clock, no vsync: everything is timed in passes. The player, the objects and the effects are
  all moved and plotted inside their own routines; there is no separate draw phase.
- **The order**: sound, keys, the player (move, zone change, fire), then the objects and effects with five
  laser steps and up to three grenade steps among them, then every collision test against the player, the
  restart and pause keys, the colour cycle, sound, padding.
- **Several steps a pass**: `&11C5` moves every laser bolt 1 pixel and is called five times, so bolts fly 5
  pixels a pass with the hit tests before every pixel. `&1F89` moves the grenade one step, three times a pass
  once its counter is below 19. The gun shots (`&1DE9`) step twice a pass.
- **Padding**: `&2B9C` plots a blank 16-line object 6 times every pass (its counter `&2BB1` is never
  incremented, in the Spectrum too), `&2B88` a blank 8-line object 16 - n times (n = 8-line plots so far this
  pass). Nothing visible changes. It costs 15.6 to 22.6 ms of a pass of about 50. The BBC drops it.
- **Counters**: `&078B` (8-bit, every pass; drives only the colour cycle of pen 15), `&078C` (the player's
  invulnerability, 66 at a death), `&3987` (passes in this zone or since the last death; at 700 the time
  limit's time-out missile starts).
- **Keys** are read once a pass (`&0D20`) into five flags. Left, right and down act while held. Up acts while
  held for jumping (jumps repeat), but on the press only for the teleports (latch `&262F`) and the suit's booth
  (latch `&2C70`). Fire acts on the press for the laser; held 15 passes it throws a grenade.
- **ESC pauses** (`&3A8F`); **CTRL+SHIFT+ESC restarts** at `&0100` (`&2713`). The Spectrum: 3 pauses,
  0+9+8+7 together quit.
- **Random numbers** (`&3AE7`): seed' = 13 × (seed + 7) mod 65536; it returns A XOR (seed' >> 8), where A is
  the caller's A on entry. The seed (`&3B02`) is never reset: at the first pass it depends on how long the
  title ran. 24 live call sites.
- **The Spectrum** makes the same calls in the same order, except a fixed delay where the CPC cycles pen 15,
  and an attribute flasher the CPC drops. The game logic is the same code: 136 passes of the same keys gave the
  same player, bolts, grenade, ammo and grenades on both machines every pass.

## Conventions
- Addresses are the CPC's, `&xxxx`. A Spectrum twin is written "Spectrum `&xxxx`" (from `tools/cpc2spec.py`
  and `work/player/sidebyside.py`).
- Time is in passes. Milliseconds are the harness's CPC timing (`time_passes`: each instruction's T-states
  rounded up to microseconds, with the CPC's extra wait states).
- x is in MODE 0 pixels (0-127), which are 2 Spectrum pixels; y in screen lines (0-191). The cell maps are
  32 × 24 cells of 4 pixels × 8 lines (the Spectrum's character cells): column = x / 4, row = y / 8.
- "Kind n" (2-17) is an object's marker, the code its zone script writes into the solid map at `&BA00`; at
  zone setup `&1BE0` collects each kind's positions into a list. The objects' names are agent C's
  (`docs/cpc-objects.md`: gun emplacements and their shots, spores, popups, missile launchers, the time-out
  missile...). Lists are named by their address.
- "Area": **player** (`docs/cpc-player.md`), **objects** and **effects** (agent C, `docs/cpc-objects.md`),
  **sound**, **status** (the score and the bottom rows), **flow** (`docs/cpc-flow.md`).

## The pass, call by call
`&06C3` first clears the padding counters `&2B9B` and `&2BB1`.

| # | Call at | Routine | Spectrum | Area | What it does |
|---|---|---|---|---|---|
| 1 | `&06CA` | `&63AF` | `&BF7E` | sound | Services the 16 effect slots at `&6A1C` (1 of 3 a pass) |
| 2 | `&06CD` | `&0D20` | `&7B72` | player | Reads the keyboard; sets `&0D6C`-`&0D70` (left, right, up, down, fire) |
| 3 | `&06D0` | `&0FA2` | `&81A4` | player | Walks, turns, jumps, falls, ducks; animates; plots; flags a zone exit |
| 4 | `&06D3` | `&125F` | `&8485` | flow | If the player left the zone: x = 0, shows the zone number, sets up the next zone (`&126E`) |
| 5 | `&06D6` | `&1120` | `&8338` | player | Fire: a laser bolt on the press (two with the suit) |
| 6 | `&06D9` | `&11C5` | `&83DD` | player | Laser step 1: hit tests (below), then every bolt 1 pixel |
| 7 | `&06DC` | `&1DE9` | `&90A2` | objects | Gun shots (list `&1E12`) from the gun emplacements: step 1 of 2 |
| 8 | `&06DF` | `&29E8` | `&9CE3` | player | The death leap; the respawn when it ends |
| 9 | `&06E2` | `&1E7C` | `&9152` | objects | Mines (kind 5, list `&1EDA`): animate; stood on, explode and kill unless the suit |
| 10 | `&06E5` | `&1F32` | `&9208` | player | Throws a grenade when fire has been held 15 passes |
| 11 | `&06E8` | `&1F89` | `&925F` | player | Grenade step 1 |
| 12 | `&06EB` | `&11C5` | `&83DD` | player | Laser step 2 |
| 13 | `&06EE` | `&2732` | `&9A23` | objects | Spores (list `&27A3`, from kind-9 sources): move |
| 14 | `&06F1` | `&291F` | `&9C15` | objects | Popups (kind 10, list `&2975`): rise and sink (drawn by the player's plotter, frame 24) |
| 15 | `&06F4` | `&2539` | `&9835` | effects | Small explosions (list `&256A`): animate, 10 passes each |
| | | | `&9118` | | Spectrum only: flashes the attributes of the kind-4 list with the pass counter's colour |
| 16 | `&06F7` | `&263C` | `&9942` | player | Pickups: ammo (kind 7, `&26EC`), grenades (kind 8, `&26EF`) |
| 17 | `&06FA` | `&2272` | `&955D` | effects | Debris (list `&22BA`) from destroyed scenery: move |
| 18 | `&06FD` | `&11C5` | `&83DD` | player | Laser step 3 |
| 19 | `&0700` | `&25B4` | `&98BA` | player | Teleports (kind 6, `&262A`): up pressed on a pad |
| 20 | `&0703` | `&63AF` | `&BF7E` | sound | Effect slots (2 of 3) |
| 21 | `&070B` | `&1F89` | `&925F` | player | If `&1F84` < 19: grenade step 2 |
| 22 | `&070E` | `&11C5` | `&83DD` | player | Laser step 4 |
| 23 | `&0711` | `&1DE9` | `&90A2` | objects | Gun shots: step 2 of 2 |
| 24 | `&0714` | `&1CAE` | `&8F54` | objects | Thruster flames (kind 2, list `&1CE3`): 3 frames in turn, a random colour each pass |
| 25 | `&0717` | `&1CEF` | `&8F95` | objects | Gun emplacements (kind 3, list `&1D7F`): fire at random; erased once destroyed |
| 26 | `&071A` | `&11C5` | `&83DD` | player | Laser step 5 |
| 27 | `&0722` | `&1F89` | `&925F` | player | If `&1F84` < 19: grenade step 3 |
| 28 | `&0725` | `&2A87` | `&9D7F` | objects | Missile launchers (kind 11, list `&2AC9`): fire at random while the player is to their left |
| 29 | `&0728` | `&2ADE` | `&9DD6` | objects | Launcher missiles (list `&2B1B`): 2 pixels left |
| 30 | `&072B` | `&2BC4` | `&9EC1` | status | The score pool `&2BD9`: 25 points a pass while it lasts |
| 31 | `&072E` | `&2BF1` | `&9EEE` | effects | Teleport sparkles (list `&2C16`): a small explosion at random by each, 20 passes |
| 32 | `&0731` | `&327F` | `&A553` | objects | Flying aliens: start one now and then |
| 33 | `&0734` | `&2CC3` | `&9FBD` | effects | Big explosions (list `&2CFD`): animate, 11 passes |
| 34 | `&0737` | `&2C30` | `&9F2D` | player | The suit's booth (kind 12, `&2C71`): up pressed in it puts the suit on or off |
| 35 | `&073A` | `&2F6E` | `&A26B` | objects | The homing missile (kind 13, `&2F69`) |
| 36 | `&073D` | `&303E` | `&A30B` | objects | Launcher bonus cells (kind 14, list `&3063`): 1,000 points each, touched |
| 37 | `&0740` | `&3090` | `&A360` | objects | Flying aliens (list `&3234`): move along their paths |
| 38 | `&0743` | `&34FF` | `&A7D6` | objects | The arc generator (kind 15, `&352A`) in a stage's last zone: random frames |
| 39 | `&0746` | `&352D` | `&A817` | flow | The level end (kind 16, `&3808`): bonuses, the bonus screen, the next stage |
| 40 | `&0749` | `&38F5` | `&ABCF` | objects | The barrier (kind 17, `&38E2`): its sound; kills on touch |
| 41 | `&074C` | `&3965` | `&AC59` | player | The time limit: after 700 passes, starts the time-out missile |
| 42 | `&074F` | `&3989` | `&AC7D` | objects | The time-out missile: 2 pixels left a pass; kills |
| 43 | `&0752` | `&1E31` | `&90EA` | objects | Gun shots against the player |
| 44 | `&0755` | `&28BE` | `&9BB4` | objects | Spores against the player |
| 45 | `&0758` | `&2990` | `&9C8B` | objects | Popups against the player (the suit protects) |
| 46 | `&075B` | `&2B67` | `&9E64` | objects | Launcher missiles against the player |
| 47 | `&075E` | `&3320` | `&A5F4` | objects | Flying aliens against the player |
| 48 | `&0761` | `&2713` | (`&9A19`) | flow | CTRL+SHIFT+ESC: restart at `&0100` (the Spectrum's twin quits on 0+9+8+7) |
| 49 | `&0764` | `&3A8F` | (`&AD21`) | flow | ESC: pause (the Spectrum's twin pauses on 3; the two calls are in the other order) |
| | | | `&B0B7` | | Spectrum only: `LD BC,&01F4 : CALL &B0B7`, a delay (a 500-byte LDIR, about 10,500 T) |
| 50 | `&0767` | `&39D8` | none | status | Pen 15's colour: entry `&078B` AND 7 of the 8 at `&39EF`, a new one every pass |
| 51 | `&076A` | `&63AF` | `&BF7E` | sound | Effect slots (3 of 3) |
| 52 | `&076D` | `&2B88` | `&9E85` | padding | 16 - n blank 8-line plots |
| 53 | `&0770` | `&2B9C` | `&9E99` | padding | 6 blank 16-line plots |

Then `&0773`: `&078C` - 1 if not 0; `&078B` + 1; `&3987` + 1; `JP &06C3`.

The laser's hit tests, called by `&11C5` before each step: `&285C` (spores, +50 each), `&2B3A` (launcher
missiles, +50), `&32F6` (flying aliens, +150), `&3910` (the barrier: 25 hits destroy it, +1,000). Bolts against
scenery are tested inside the step itself.

Order that matters: the player moves (3) before anything is tested against him (43-47), so the tests see this
pass's position. Fire (5) comes after the move, so a bolt starts from the new x. The zone change (4) happens
inside the same pass as the exit, before fire, and the zone's first pass of objects runs at once. The pickups
(16), the teleport (19) and the suit (34) all test the position after the move.

## Why some routines run several times a pass
- **`&11C5`, five times**: a bolt moves 1 pixel a call, so 5 pixels a pass, and the four hit tests run before
  every pixel. A bolt can't jump over a 4-pixel target. Measured: a bolt fired at x = 16 shows at 33, 38, 43
  ... 78 at the ends of passes (`work/player/fire.py`).
- **`&1F89`, up to three times**: the first call is unconditional; the other two run only while the grenade's
  counter `&1F84` is below 19 (it counts down from 32 and stops at 1). So the throw rises slowly (one step a
  pass for 13 passes) and then flies three steps a pass. Measured (`fire.py`): steps per pass 1 × 13, then 3.
- **`&1DE9`, twice**: the gun shots move 1 pixel a call, so 2 a pass.
- **`&63AF`, three times**: the sound effects are stepped three times a pass, about every third of a pass.
  The BBC services sound at 50 Hz instead (D13), about four times a 2-frame pass.

Everything else moves once a pass.

## The padding
| Routine | Plots | Of | Counter | Cost a pass |
|---|---|---|---|---|
| `&2B88` | 16 - n, none if n ≥ 16 | 8-line object frame 6 (48 zero bytes) at whatever DE holds | `&2B9B`: n, the 8-line plots so far this pass (`&2020` increments it at `&206E`) | 0 to 7.0 ms |
| `&2B9C` | 6 - `&2BB1`, so always 6 | 16-line object frame 0 (64 zero bytes), plot record `&3F1E` | `&2BB1`: never incremented anywhere | 15.6 ms |

- The game has no clock, so the padding holds the pass near its worst case: each pass pays for 16 small and 6
  large objects whether they're there or not. The 16-line half was meant to do the same but its counter is
  dead, so it's a flat 15.6 ms. The Spectrum's twin (`&9E99`, counter `&9EAE`) has the same bug.
- Both frames are all zeros, so the XOR plots change nothing on screen.
- Measured over 300 passes in zones 0, 6 and 12 (`work/player/padding.py`): `&2BB1` was 0 at `&2B9C` every
  time; n ranged 0 to 111 (grenades, small explosions and debris are 8-line objects); padding took 15,597 to
  22,612 µs.
- The BBC locks a pass to 2 frames (D8) and drops both routines and both counters.

## Counters and timers
| Address | Size | Meaning | Range | Set | Read |
|---|---|---|---|---|---|
| `&078B` | 1 | Pass counter | 0-255, wraps | + 1 every pass (`&077D`); never reset | `&39D8` only: pen 15's colour, `&078B` AND 7 |
| `&078C` | 1 | Invulnerability, passes | 0-66 | 66 (`&2E` + `&14`) at a death (`&29D4`); 0 at zone setup (`&1278`) | - 1 a pass if not 0 (`&0779`); not 0 means the player can't be killed (`&29B9`) |
| `&3987` | 2 | Passes in this zone, or since the last death | 0-65535 | 0 at zone setup (`&1271`) and at a death (`&29C3`); + 1 every pass | `&3965`: at 700 (`&02BC`) and above, the time-out missile starts if none is running |
| `&3984` | 1 | The time-out missile running | 0/1 | | `&3965`, `&3989` |
| `&29E7` | 1 | Dying, passes left | 46 → 0 | 46 at a death | not 0: the player's routines return at once (`&2A80`) |
| `&11C4` | 1 | Passes fire has been held | 0-255, stops at 255 | 0 when fire is up; 1 on the press | `&1120` (bolt on 1), `&1F32` (grenade at 15 or more) |
| `&1F84` | 1 | Grenade counter | 32 → 1, 0 = none | 32 at a throw | the arc's index; under 19, 3 steps a pass |
| `&10F0` | 1 | Jump counter | 22 → 0 | 22 at take-off | the arc's index |
| `&10F2` | 1 | Walk cycle | 0-9 | + 1 a step | the walking frame |
| `&2BD9` | 2 | Score pool, in 25-point units | | `&2BB2` adds A | `&2BC4`: - 1 and 25 points a pass |
| `&32F5` | 1 | Passes before another flying alien may start | 9 → 0 | 9 at each start | `&327F` |
| `&1CEE` | 1 | Thruster flames' frame | 0-2 | + 1 a pass | `&1CAE` |
| `&1ED9` | 1 | Mines' frame | 0/2 | XOR 2 a pass | `&1E7C` |

The Spectrum's twins: `&768C`, `&768D`, `&AC7B` (pass counter, invulnerability, zone timer). The Spectrum's pass
counter drives its attribute flasher (`&9118`) the same way.

700 passes is 33.5 s at the CPC's 20.9 passes a second, 28 s at the BBC's 25.

## Keys
`&0D20` clears the five flags (`&0D5E`), reads the matrix's ten rows into `&3AA5`-`&3AAE` (`&3AAF`, through the
AY's port A), and sets a flag to 1 for each key down. Each test is `LD A,(IX+row) : AND mask` with IX = `&3AA5`;
define keys patches the row (at `&0D34`, `&0D3D`, `&0D46`, `&0D4F`, `&0D58`) and the mask (one byte on).

| Flag | Default key (row, mask) | Defined as | Used |
|---|---|---|---|
| `&0D6C` | O (4, `&04`) | LEFT | Held: walk left (`&108E`, which reads `&0D6C` and `&0D6D` as one word) |
| `&0D6D` | P (3, `&08`) | RIGHT | Held: walk right |
| `&0D6E` | Q (8, `&08`) | JUMP | Held: jump from the ground (`&0FD2`), again on every landing. Pressed: teleport (`&25B4`, latch `&262F`) and the suit's booth (`&2C30`, latch `&2C70`) |
| `&0D6F` | A (8, `&20`) | DUCK | Held: duck (`&0FC5`), over everything else on the ground |
| `&0D70` | SPACE (5, `&80`) | FIRE | Pressed: a bolt (`&1120`, `&11C4` = 0 → 1). Held 15 passes: a grenade (`&1F32`); still held, another when it lands |

- A latch is set by the pass that sees the key down and cleared by the first pass that sees it up, so the
  action happens once a press. The teleport and the booth have separate latches, both on up.
- Left and right together cancel (`H XOR L` = 0): he stands.
- The Spectrum's defaults (`&7AE9`): O, P, Q, A and M for fire, plus Interface 2 and Kempston (title keys
  3-5). The same flags (`&7B92`-`&7B96`) and the same uses.
- `&0E83` (a Spectrum keyboard read, `IN A,(&FE)`) and `&0D7A` (random keys, as for an attract demo) are never
  called.

## Pause and restart
- **`&2713`**: scans the matrix and compares all ten rows with `&2728`: only CONTROL and SHIFT (row 2 = `&5F`)
  and ESC (row 8 = `&FB`) down, nothing else. Then `JP &0100`: a restart from the top (the title, the score and
  lives reset). Checked: holding them reaches `&0100` within the pass (`work/player/pause.py`).
- **`&3A8F`**: ESC down (row 8 bit 2): a delay (1,000-byte LDIR), wait until no key is down (`&3A76`), then
  wait for any key (`&39F7`). The pass stops there and resumes. Checked: the pass doesn't finish while ESC is
  held, nor after it's released, until another key.
- The Spectrum: `&AD21` pauses the same way on 3 alone (half-row `&F7` = `&1B`); `&9A19` quits to `&6D60` on
  0, 9, 8 and 7 held together.
- So ESC alone pauses on the CPC, and pressing CTRL and SHIFT before ESC restarts instead (`&2713` runs first).

## Random numbers
`&3AE7` (Spectrum `&AD36`, the same code):

    seed' = 13 × (seed + 7) mod 65536        (seed at &3B02, a word)
    A     = A on entry XOR (seed' >> 8)

- Checked over 200 calls in zone 6 (`work/player/rngcheck.py`): every call obeys it, with A on entry taking 20
  different values. The plan's "seed × 13 + 7" was wrong.
- The seed is written only by `&3AE7`, and never reset. It's 0 in the image, and the title's twinkling stars
  call the generator, so the seed at the first pass depends on how long the title ran: `&89C7`, `&321A`,
  `&1824`, `&6918` after 60, 100, 101 and 150 frames of title (`work/player/rng.py`).
- **For lockstep**: start the BBC with the harness's seed at the first pass and compare the seed every pass. The
  result also depends on the caller's A, so the BBC must pass the same A at each site to get the same numbers.
  Two sites take it from AF' (marked below): their first call in a pass sees whatever AF' held, which the BBC
  can't mirror without copying the Z80's use of AF'. Both are cosmetic (a colour, a background star), but a
  different star changes how many calls `&3017` makes, and so the seed after.

| Call at | Routine | For | A on entry |
|---|---|---|---|
| `&01F8`, `&01FE` | `&01D7` title stars | column (A AND `&1E`), row (A AND `&1F`, under 22) | 0; the previous result AND `&1E` |
| `&1CCA` | `&1CAE` thruster flames | colour (A AND 7) OR `&42`, each flame each pass | AF' (the previous flame's colour) |
| `&1D34` | `&1CEF` gun emplacement | fires if A ≥ `&FA` | 1 |
| `&1E99` | `&1E7C` mines | colour, each mine each pass | the mine's state - 1 |
| `&2233`, `&223E` | `&220E` debris (called from the mode-3 plotter at `&3C8E` as scenery is destroyed) | dx, dy from the table `&226A`, again until not both 0 | the debris's y; the previous result |
| `&274F`, `&276C` | `&2732` spores | turn if A ≥ `&DC`; up or down 1 by A AND 1 | x; the new x |
| `&283C` | `&2811` spores' setup | direction | 4 |
| `&2957` | `&291F` popups | the next wait, 20-83 passes | the counter (`&78` or more) |
| `&2A91` | `&2A87` missile launchers | fires if A ≥ `&F7` | the A left by the previous call or launcher |
| `&2C03`, `&2C0A` | `&2BF1` teleport sparkles | x + (A AND 3), y + (A AND `&0F`) | the timer; the new x |
| `&2F5B` | `&2F3D` homing missile | its y, 32-159 | 13 |
| `&3002`, `&3017` | `&2FF6` background stars, at zone setup | column; colour (A AND `&54`, again until not 0) | AF' (the loop's); the cell, then 0 |
| `&32AC`, `&32B9`, `&32C5`, `&32E1` | `&327F` flying aliens | start if A ≥ `&C8`; height; colour | various, from the code before |
| `&3510` | `&34FF` arc generator | frame `&1C` + (A AND 3) | whatever `&3090` left in A |
| `&3946` | `&3910` the barrier destroyed | colours, a block at a time | the barrier's height, then what the plotter left |
| `&399C` | `&3989` the time-out missile | a small explosion if A ≥ `&80` | the time-out missile's x |

Not live: `&0D72`, `&0D7D` (in `&0D7A`, never called), and the calls inside the debris and explosion tables
(`&2333`, `&233E`, `&2433`, `&243E`, `&2D03`: leftover code bytes that the tables overwrite).

In zone 0, 600 passes of random play made 2 to 3 calls a pass (`&1CCA` and `&1D34`). A zone change makes many
more (the background stars), and destroying scenery more again (debris).

## The Spectrum's loop
`&75BE`-`&7689`: the same 53 calls in the same order with the same arguments, plus:
- `&9118` after the small explosions: for each cell of a list at `&9135` (the kind-4 positions), sets its
  attribute to bright ink (pass counter AND 7). The CPC keeps the kind-4 list (`&1E5F`) but never reads it;
  instead `&39D8` cycles pen 15 through the hardware colours `&1C`, `&0C`, `&07`, `&0A`, `&12`, `&13`, `&19`,
  `&0B`, so whatever is drawn in pen 15 flashes.
- `LD BC,&01F4 : CALL &B0B7` before the last sound call: a fixed delay of about 10,500 T, where the CPC calls
  `&39D8`.
- The pause and quit keys (above).

The routines it calls are the same code with addresses moved, apart from plotting, colour and sound. The
Spectrum beeps by blocking loops (`&7C26` with B as the length), which the CPC replaced with `RET` stubs at
`&0E81` and `&0E82` (still called with B set: when firing, scoring, collecting).

## What the BBC can drop
- The padding (`&2B88`, `&2B9C`, `&2B9B`, `&2BB1`).
- The `&0E81`/`&0E82` stubs, `&0E83`, `&0D7A`, the write to `&0DF0` in `&1120` (never read).
- `&39D8` as code: pen 15's cycle is a colour effect for the BBC's palette or dither to reproduce or not.
- The three sound calls, for the IRQ's 50 Hz service (D13), with effects posted by the logic.
