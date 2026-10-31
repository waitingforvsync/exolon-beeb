# Exolon (CPC): the game outside play

A spec of the CPC original's flow around the main loop: start-up, the title and its timeouts, define keys and
the cheat, a game's start, the stages through the 125 zones, a stage's end and the bonus screen, game over, the
high-score table and name entry. From its code (`build/exolon.skool`) and the Spectrum original's
(`build/spec/exolon64k.bin`), for the BBC version. Checked in the harness (`tools/cpc.py`) with the scripts in
`work/player/` unless marked *unverified*. 2026-10-31.

## Summary
- **Start-up** (`&0100`) sets up the hardware and tables, zone 0, score 0, 9 lives, no suit, and runs again
  after every game over or restart. Then the title, or first the high-score page after a name was entered.
- **The title** (`&0136`) twinkles 12 stars at random and plays a tune; 1 starts, 2 defines keys. After 3,000
  loops (about 98 s at 4 MHz) the high-score page, for 20,000 key reads (about 24 s), then the title again. No
  attract demo.
- **Define keys** (`&02B4`) asks for LEFT, RIGHT, JUMP, DUCK, FIRE. Typing Z, O, R, B, A toggles infinite lives
  (the `DEC A` at `&2A25`), with a tune when it turns on. The Spectrum has the same cheat.
- **Stages**: 125 zones in 5 stages of 25 (0-24, 25-49, 50-74, 75-99, 100-124), each starting at a fixed
  point. The only checkpoints are the zones' left edges (the respawn point).
- **A stage's end** is a marker (kind 16) in its last zone: walking past it gives 1,000 a life, 10,000 if not in
  the suit, the bonus screen (a pointer to stop: 0 to 7,000), a life (9 at most), and a full refill.
- **After zone 124**: a congratulations page, the bonus screen, and zone 0 again with the score and lives kept.
  The game never ends but by game over.
- **Game over**: a GAME OVER box and tune, then a score above any of the 17 in the table asks for a name of 8
  characters, and the table is shown before the title.
- **The table** on this disc is the hacker's: ARAGORN 900000 and greetings. The originals are in the Spectrum
  version, 50 names at 1,000 each (RAFFAELE, SURYANI, SCRAGGY...); a leftover "SURYANI" past the CPC table's end
  suggests the CPC started with the same names.
- **The Spectrum** has the same flow except the title's length (2,500 loops), its extra input options (keyboard,
  Interface 2, Kempston), a 50-entry table, and 3 to pause, 0+9+8+7 to quit.

## Conventions
- Addresses are the CPC's, `&xxxx`; Spectrum twins "Spectrum `&xxxx`".
- Times outside play are given in CPC frames (20 ms) of plain Z80 T-states at 4 MHz, as the harness's
  `run_to` counts them: a real CPC's wait states make them somewhat longer (*unverified* by how much here; the
  passes' timing model in `time_passes` is too slow to single-step minutes of title).
- Text positions are character rows (0-23) and columns (0-31) of 2 CPC bytes × 8 lines.
- Delays are `&3E54`: an LDIR of BC bytes from `&0000` onto itself (BC = 0 is 65,536), about 6 µs a byte on
  the CPC. "A long delay" below is BC = 0, about 0.4 s.

## Start-up: `&0100`
1. `DI`, SP = `&0100`, `&3E90`: the CRTC, MODE 0, black border, the 16 inks (agent A).
2. Not dying (`&29E7` = 0), no suit (`&2BDB` = 0), zone 0 (`&12FA`, at `&010E`: the start-zone poke NOPs this),
   score pool 0 (`&2BD9`).
3. The tables: screen line addresses (`&0E64`, `&BE00`/`&BF00`), the pixel swap (`&0DF1`, `&BD00`).
4. Score "000000" (`&3B3B`-`&3B40`), lives 9 (`&1BD4`).
5. If a name was just entered (`&056B` ≠ 0): the high-score page (`&04D7`). Else the title.

It's entered at power-on, after each game over (`&2D4C`, `&2D54`), after a name entry (`&2E45`), and by
CTRL+SHIFT+ESC in play (`&2713`). The memory is never reloaded, so anything poked (the ZORBA cheat) stays.

## The title: `&0136`-`&0171`
- Clears the screen (`&3DFD`), the cell maps (`&1B5B`: `&BA00` = 0; `&1B69`: `&B700` = `&FF`), the plot records
  (`&3F10`) and the star slots (`&02A6`); draws the script `&0174`: the logo, BY RAFFAELE CECCO, 1 START GAME,
  2 DEFINE KEYS, EXOLON HACKED BY ARAGORN! 89 (the Spectrum: 1. START GAME ... 5. KEMPSTON, EXOLON COPYRIGHT 1987
  HEWSON). Starts the title tune (`&5A15`; the sound code is not examined here).
- Then up to 3,000 (`&0BB8`) loops of: the stars (`&01D7`), a key read (`&39F7`). '1' starts a game (`&068F`),
  '2' defines keys (`&02B4`). After 3,000, the high-score page (`&04DB`).
- **The stars** (`&01D7`): 12 slots at `&0281` (x, y, timer; `&02A5` = `&FF` ends). A free slot picks a column
  (random AND `&1E`, even, 0-30) and row (random AND `&1F`; 22 or more and it waits) and takes it if the 2 × 2
  cells there are all 0 in `&BA00` (the text has marked its cells), timer 16. A live one counts down and plots
  16-line object frame `&0270`[timer] (12-15, rising and falling; 0 at the end, which clears it) with its own plot
  record (`&3FFE` + 80 × slot).
- Every fourth star plotted, the tune takes a step (`&0248` calls `&5A90`): its tempo follows the stars.
- The stars use the random generator, so the seed at a game's start depends on how long the title ran
  (`docs/cpc-loop.md`).
- Measured (`work/player/title.py`): 4,889 frames (98 s) from the loop's start to the high-score page; the
  Spectrum loops 2,500 times (`&6DDA`).

## The high-score page: `&04D7`/`&04DB`
- `&056B` = 0, the screen cleared, its frame drawn (`&051A`), then the table: 17 rows of 16 characters (the
  name's 10, the score's 6) at rows 5-21, columns 8-23.
- Waits for no key (`&3A76`), then up to 20,000 (`&4E20`) key reads; a key, or the end, goes to the title
  (`&0136`, not `&0100`). Measured: 1,224 frames (24 s).
- The Spectrum shows 50 entries, scrolled (`&7149`; *unverified* in detail).

### The table: `&056C`-`&067B`
17 entries of 16 bytes: 10 bytes of name, 6 ASCII digits of score; `&FF` at `&067C` ends it.

| On this disc | Score |
|---|---|
| ARAGORN | 900000 |
| GREETZ, RAFFAELE, DJ TONY T, NOSTROMO, AND THE, AUTHORS, OF CPC, EMULATORS, WHO MAKE, IT ALL, POSSIBLE, M VIETH, B SCHMIDT, WHERE IS, RAFF NOW?, (blank) | 001000 each |

- The originals aren't in the CPC image, but past the `&FF` lie "URYANI   001000" (`&067D`-`&068B`) and "S"
  (`&068C`): the last 15 bytes of an entry pushed off the end by an insertion, "SURYANI". That's the second name
  of the Spectrum's table.
- The Spectrum's table (`&71F1`, 50 × 16 bytes, all 001000): RAFFAELE, SURYANI, SCRAGGY, SABATTA!, PADDY, LOFTY,
  JIMBO, LEO, GLEN, MORANGE, PUPPY, ONION, RIP, FIGARO, INK, PEN, DUMBO, MEPHISTO, QUEEN, UNYIL ?, EQUINOX,
  REALMS, MAJALA, LENGKAP, JAZZ, HEWSON, TIM.M, CECCO, LUCY, ANTONY, NIAEREH, \*!/?!@, POD, HUTNEE, BUTNEE,
  JOHN.O, CARROT, COLIN, FLASH, SEVILLE, T-STATE, CLUB, HWP, CDP, TACHYON, KILLER, DROOPY, R 4 S, RZASM2, HUMPTY.
- So the CPC's original was probably the Spectrum's first 17 (RAFFAELE to DUMBO), all at 1,000 (*unverified*).

## Define keys: `&02B4`
- Sound off, the screen and maps cleared, the script `&0428`: SELECT KEY FOR.... LEFT, RIGHT, JUMP, DUCK, FIRE,
  and EXOLON COPYRIGHT 1987 HEWSON at the foot.
- For each of the five: a '?' at its line; wait for no key, then a key (`&39F7`: the first down in a scan of
  the 80); its row and bit patched into `&0D20` (`docs/cpc-loop.md`, Keys); its code saved at `&041E`-`&0422`;
  its name shown: the character, or for the codes from `&61` up a name from `&0379` (UP, RIGHT, DOWN, F9, F6,
  F3, ENTER, '.', LEFT, COPY, F7, F8, F5, F1, F2, F0, CLR, RETURN, F4, SHIFT, CONTROL, ESC, TAB, CAPS LOCK,
  JOY UP, JOY DOWN, JOY LEFT, JOY RIGHT, FIRE, FIRE2, SPARE, DELETE).
- Then two long delays, and the cheat: if the five codes are "ZORBA" (`&0423`), the byte at `&2A25` is XORed
  with `&3D`: the lives' `DEC A` becomes `NOP` (infinite lives) or back. Turned on, a tune plays (40 steps of
  the sound with delays). Either way, back to the title; the keys stay Z, O, R, B, A until defined again.
- The Spectrum (`&6FAB`): the same five, the same cheat (`&704A`, XOR `&3D` at `&9D1D`, a tune when on), and the
  title's options 3-5 choose the keyboard, Interface 2 or Kempston.
- The BBC moves defining keys to a loader (D18); the cheat would go with it (Rich decides).

## A game's start: `&068F`
Sound off, the screen cleared; the player's frame record `&FF`; the frames unmirrored; no jump; facing right;
x, y = 16, 112 and the respawn point the same; ammo 99, grenades 10; the status rows (`&078F`); the zone set up
(`&126E`) for `&12FA` (0, or the poked start zone: then he still starts at 16, 112 and falls or stands there);
the main loop.

### A zone's setup: `&126E`
Called at a game's start, at each zone change (from `&125F`) and at a stage's start. For the player and the
loop: the zone timer `&3987`, the grenade `&1F84`, the invulnerability `&078C` and the time-out missile
`&3984` all 0; the plot records, both cell maps and every object and effect list cleared; the playfield cleared
(`&3E0C`, 176 lines); the background stars (`&2FF6`, random); each placement of the zone drawn (and its
destructible box made, `&219C`); the markers gathered (`&1BE0`); the spores, the zone's aliens, the homing
missile and the barrier prepared. Agents A and C have the details. It takes one long pass: 268 ms from zone 0
to 1.

## The stages
- 125 zones, 0-124, in five stages of 25. Leaving a zone at the right edge goes to the next
  (`docs/cpc-player.md`).
- A death respawns him at the left edge of the zone he's in, at the height he came in. There are no other
  checkpoints, and game over starts again from zone 0.
- Each stage's last zone (24, 49, 74, 99, 124) holds the level end marker (kind 16, at `&3808`) and the arc
  generator (kind 15, `&352A`: two 16-line frames from `&1C`-`&1F` at random each pass, side by side). The
  markers are at column 15 in zones 24, 74 and 99, column 20 in 49 and 124 (`work/player/zonescan.txt`).
- Zones 102-124 (all but 118) have the same special cells, in the same places, as zones 27-49
  (`zonescan.txt`), though only 4 of their placement lists are byte for byte the same (103, 115, 121, 122): the
  fifth stage looks like the second's layout dressed differently (agent A).

### A stage's end: `&352D`
When x ≥ the marker's column × 4 (all inside the one pass):
1. Sound off; the panel (script `&380B`).
2. The lives shown at row 12, column 13, and 1,000 points for each, the score reprinted each time.
3. Not in the suit: a '1' at row 8, column 14, and 125 points 80 times: 10,000.
4. In zone 124: two long delays, the screen cleared, CONGRATULATIONS! YOU HAVE PROVEN YOUR COMBAT ABILITIES TO
   THE FULL. PRESS FIRE TO RESUME PLAY (`&3758`), zone = `&FF`, four long delays. (It says press fire, but the
   bonus screen next is what waits.)
5. **The bonus screen** (`&35F4`): six long delays, the screen cleared, EXOLON BONUS SCREEN! PRESS FIRE TO STOP
   POINTER, and eight lines: 00000, 01000, 00000, 03000, 00000, 05000, 00000, 07000 POINTS (rows 13-20). Waits
   for no key, then loops: a counter `&3679` + 1; a '\*' at row 13 + (counter AND 7), column 22, the last one
   rubbed out; the keys read; a 6,000-byte delay; until fire. Three long delays; then if the counter is odd,
   1,000 × (counter AND 7) points: exactly the line it stopped on.
   - The pointer steps every 1.62 frames (31 a second): fast enough to be luck. The counter is never reset, so
     it carries on from where the last stage's stopped.
6. A life if under 9; the suit off; ammo 99; grenades 10.
7. The next zone (`&104C`, zone + 1: from `&FF` that's 0), set up (`&125F`), the status rows redrawn (`&078F`),
   no jump, and the stage's start point from `&37F9` (zone, x, y) as his place and respawn point:

| Stage | Zones | Start x, y |
|---|---|---|
| 1 | 0-24 | 16, 112 |
| 2 | 25-49 | 0, 120 |
| 3 | 50-74 | 0, 32 |
| 4 | 75-99 | 40, 128 |
| 5 | 100-124 | 16, 112 |

Checked (`work/player/stage.py`, the player poked to the marker with 5 lives): zone 24's end scored 5,000 for
lives, 10,000 without the suit, and 5,000 for the pointer stopped on counter 5 (20,000); zone 25 began at (0,
120) with 6 lives, 99 ammo, 10 grenades. From zone 124: the same, then zone 0 at (16, 112).

**After zone 124** the game simply goes round again from zone 0, keeping the score, the lives and the bonus
counter. The Spectrum's is the same code and data (`&A817`, `&A8DB`; the texts and the start points equal).

## Game over: `&2D1B`
When the respawn finds no lives left (`&2A40`):
1. A GAME OVER box at row 9, column 10 (script `&2D57`); sound off; a tune, 40 steps each with an 8,000-byte
   delay; sound off; a long delay. Measured: 105 frames from `&2D1B` to the table check.
2. The table check and name entry (`&2D73`, below).
3. Waits for no key, then up to 20,000 key reads; a key or the end restarts at `&0100` (the title).

### The name entry: `&2D73`
- Walks the 17 entries; the first whose score is lower than the player's, digit by digit (an equal score goes
  below), is where it goes. None: back to game over's wait.
- The entries from there shift down one (`LDDR`), the last falls off past the `&FF` (which is put back at
  `&067C`), and the score is copied in.
- The screen cleared: CONGRATULATIONS! PLEASE ENTER YOUR NAME INTO THE EXOLON HALL OF FAME, a line of 8 dashes,
  PRESS DEL TO DELETE, PRESS RETURN TO END (`&2E59`).
- Up to 8 characters at row 15, columns 12-19, a '?' as the cursor, a delay and a wait for no key between keys:
  any key with a code below `&61` (letters, digits, space, punctuation) is typed (at the 8th place it replaces
  the last); DEL rubs out the last; RETURN ends.
- The 8 characters (spaces after) become the entry's first 8 bytes. Its 9th and 10th keep what the shifted entry
  had there (a stray letter when that name was 9 or 10 long: a small bug).
- `&056B` = 1, wait for no key, `JP &0100`: the high-score page comes before the title.
- Checked (`work/player/gameover.py`): with 5,000 points and one life, killed in zone 0: N, A, DEL, A, M,
  RETURN put NAM 005000 second, under ARAGORN; then `&04D7` ran.
- The Spectrum (`&A073`): the same, its keys ENTER and DELETE, into its 50 entries.

## Pause and quitting
ESC pauses and CTRL+SHIFT+ESC restarts, tested once a pass at the end of the loop (`docs/cpc-loop.md`). The
Spectrum: 3 pauses, 0+9+8+7 together quit to the title. There's no other way out of a game.

## For the BBC
- The flow is small: title (with the timeout to the table), game, stage ends, game over, table. The title's
  stars and tune, the panel and the bonus screen are presentation; only the bonus screen's pointer and its
  never-reset counter, the bonuses and the start points are rules.
- The bonus screen's speed is set by delays, not passes: on the BBC the pointer's rate is a choice (about 31
  steps a second on the CPC).
- Lockstep through a stage's end needs the same fire timing on the bonus screen, and the same seed at the first
  pass (the title's length sets it).
