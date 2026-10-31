// bench.mjs plus a hash of the screen (&5000-&7FFF) after each pass, written to --hashes (one per line)
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
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
const times = [], hashes = [];
for (let i = 0; i < passes.length; i++) {
    if (!(await runTo(s, syms["game.pass"], 80000000))) throw new Error(`pass ${i}: never reached`);
    s.writeMemory(syms["CmdBuf"], Array.from(passes[i]));
    const t0 = s.elapsedCycles;
    if (!(await runTo(s, syms["game.passdone"], 80000000))) throw new Error(`pass ${i}: never done`);
    times.push(s.elapsedCycles - t0);
    const h = createHash("sha1");
    for (let a = 0x5000; a < 0x8000; a += 0x400) h.update(Uint8Array.from(s.readMemory(a, 0x400)));
    hashes.push(h.digest("hex").slice(0, 12));
    if (args.dump && i === Number(args.dumpat ?? 0)) { const m = []; for (let a = 0x5000; a < 0x8000; a += 0x400) m.push(...s.readMemory(a, 0x400)); writeFileSync(args.dump, Uint8Array.from(m)); }
}
const sorted = [...times].sort((a, b) => a - b);
const q = (f) => sorted[Math.floor(f * (sorted.length - 1))];
console.log(`${times.length} passes: plotting median ${q(0.5)}, 90% ${q(0.9)}, 99% ${q(0.99)}, max ${sorted[sorted.length - 1]} cycles`);
console.log(`over 40,000 (half a pass): ${times.filter((t) => t > 40000).length}; the slowest at pass ${times.indexOf(sorted[sorted.length - 1])}`);
if (args.hashes) writeFileSync(args.hashes, hashes.join("\n") + "\n");
if (args.times) writeFileSync(args.times, times.join("\n") + "\n");
s.destroy();
