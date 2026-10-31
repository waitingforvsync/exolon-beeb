// The plotter timed over the original's plots, in headless jsbeeb with the real IRQ.
//
//   make bench
//   .venv/bin/python tools/benchlog.py --zone 0 --passes 400 build/bench/zone0.bin
//   node tools/bench.mjs --zone 0 --cmds build/bench/zone0.bin [--png build/bench/zone0.png --at 200]
//
// The bench build (src/bench.6502) draws the zone, then each pass runs the commands this writes into CmdBuf
// before it starts; the cycles from game.pass to game.passdone are the pass's plotting.

import { readFileSync, writeFileSync } from "node:fs";
import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) =>
    x.startsWith("--") ? [...a, [x.slice(2), all[i + 1]]] : a, []));
const syms = symbols(args.symbols ?? "build/bench.json");
const cmds = readFileSync(args.cmds);
const passes = [];
for (let o = 0; o < cmds.length;) { const n = cmds[o] | cmds[o + 1] << 8; passes.push(cmds.subarray(o + 2, o + 2 + n)); o += 2 + n; }

const s = await bootDisc(args.disc ?? "build/bench.ssd");
if (!(await runTo(s, syms["game"], 80000000))) throw new Error("game never reached");
s.writeMemory(syms["zone"], [Number(args.zone ?? 0)]);
const times = [];
for (let i = 0; i < passes.length; i++) {
    if (!(await runTo(s, syms["game.pass"], 80000000))) throw new Error(`pass ${i}: never reached`);
    s.writeMemory(syms["CmdBuf"], Array.from(passes[i]));
    const t0 = s.elapsedCycles;
    if (!(await runTo(s, syms["game.passdone"], 80000000))) throw new Error(`pass ${i}: never done`);
    times.push(s.elapsedCycles - t0);
    if (args.png && i === Number(args.at ?? passes.length - 1)) {
        await s.runFrames(1);
        writeFileSync(args.png, await s.screenshotActive({ scale: 1 }));
    }
}
const sorted = [...times].sort((a, b) => a - b);
const q = (f) => sorted[Math.floor(f * (sorted.length - 1))];
console.log(`${times.length} passes: plotting median ${q(0.5)}, 90% ${q(0.9)}, 99% ${q(0.99)}, max ${sorted[sorted.length - 1]} cycles`);
console.log(`over 40,000 (half a pass): ${times.filter((t) => t > 40000).length}; the slowest at pass ${times.indexOf(sorted[sorted.length - 1])}`);
s.destroy();
