// Every zone drawn by the BBC against the original's, byte for byte, in headless jsbeeb with the real IRQ.
//
//   .venv/bin/python tools/genzones.py build/gen --expect      (once: build/gen/zones-expected.bin)
//   make viewer; node tools/check_zones.mjs [--first 0] [--last 124] [--dump build/zone-bad.bin]
//
// The zone viewer (game.6502) shows zone 0 first, each with the CPC's seed at a zone's set-up (&6512), and X
// steps on. At each arrival at game.shown the playfield (&5000-&7BFF) is compared with the expected bytes
// (zonemodel's tile map through the BBC's tiles), and zone_enter's time from the JSR to there is reported.

import { readFileSync, writeFileSync } from "node:fs";
import { bootDisc, runTo, symbols, BBC } from "./jsbeeb.mjs";

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) =>
    x.startsWith("--") ? [...a, [x.slice(2), all[i + 1]]] : a, []));
const first = Number(args.first ?? 0), last = Number(args.last ?? 124);
const syms = symbols("build/viewer.json");
const expected = readFileSync("build/gen/zones-expected.bin");
const PLAY = 0x5000, BYTES = 22 * 512;

const s = await bootDisc("build/viewer.ssd");
const shown = syms["game.shown"], enter = syms["zone_enter"];
let bad = 0;
const times = [];
for (let z = 0; z <= last; z++) {
    // zone_enter's time: from its first instruction (paged in: the code bank) to game.shown
    if (!(await runTo(s, enter, 80000000))) throw new Error(`zone ${z}: zone_enter never reached`);
    const t0 = s.elapsedCycles;
    if (!(await runTo(s, shown, 80000000))) throw new Error(`zone ${z}: never shown`);
    times.push(s.elapsedCycles - t0);
    const zoneNow = s.readMemory(syms["zone"], 1)[0];
    if (zoneNow !== z) throw new Error(`expected zone ${z}, the viewer shows ${zoneNow}`);
    if (z >= first) {
        const got = new Uint8Array(BYTES);
        for (let a = 0; a < BYTES; a += 256) got.set(s.readMemory(PLAY + a, 256), a);
        const want = expected.subarray(z * BYTES, (z + 1) * BYTES);
        let diff = 0, firstDiff = -1;
        for (let i = 0; i < BYTES; i++) if (got[i] !== want[i]) { diff++; if (firstDiff < 0) firstDiff = i; }
        if (diff) {
            bad++;
            const cell = firstDiff >> 4;
            console.log(`zone ${z}: ${diff} bytes differ, the first in cell (${cell >> 5}, ${cell & 31}) line ${firstDiff & 7}`);
            if (args.dump && bad === 1) writeFileSync(args.dump, got);
        }
    }
    if (z === last) break;
    s.keyDownRaw(BBC.X);
    await s.runFor(4 * 39936);
    s.keyUpRaw(BBC.X);
}
const ts = times.slice(first).sort((a, b) => a - b);
const ms = (c) => (c / 2000).toFixed(0);
console.log(`${last - first + 1 - bad} of ${last - first + 1} zones match; zone_enter ${ms(ts[0])}-${ms(ts[ts.length - 1])} ms, ` +
    `median ${ms(ts[ts.length >> 1])} ms`);
s.destroy();
process.exit(bad ? 1 : 0);
