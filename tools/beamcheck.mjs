// The plot driver against the beam (src/plotpass.6502): bench.mjs's run of a log's objects (benchlog.py --objects),
// stopping as each item's plot starts (plot_pass.sched_plot) and ends (plot_pass.sched_done), with the beam's line
// from jsbeeb's CRTC counters. An item whose lines the beam scans while it's plotted is a tear.
//
//   node tools/beamcheck.mjs --zone 94 --cmds build/bench/obj94.bin
//
// An item's lines are its window (ItemW0, ItemW1: T1C-H's 4-line steps) turned back into lines, which covers
// them. Prints the tears, where each item was plotted (ahead of the beam, behind it, or in the blanking), and
// the cycles spent waiting.

import { readFileSync } from "node:fs";
import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) =>
    x.startsWith("--") ? [...a, [x.slice(2), all[i + 1]]] : a, []));
const syms = symbols(args.symbols ?? "build/bench.json");
const cmds = readFileSync(args.cmds);
const passes = [];
for (let o = 0; o < cmds.length;) { const n = cmds[o] | cmds[o + 1] << 8; passes.push(cmds.subarray(o + 2, o + 2 + n)); o += 2 + n; }
const BEAMTOP = 30, LINES = 312;

const s = await bootDisc(args.disc ?? "build/bench.ssd");
if (!(await runTo(s, syms["game"], 80000000))) throw new Error("game never reached");
s.writeMemory(syms["zone"], [Number(args.zone ?? 0)]);
const video = s._machine.processor.video;
const beam = () => video.vertCounter * 8 + video.scanlineCounter;
const [start, end, done] = [syms["plot_pass.sched_plot"], syms["plot_pass.sched_done"], syms["game.passdone"]];

let items = 0, tears = 0, ahead = 0, behind = 0, blank = 0, late = 0, long = 0;
const cal = [], beamlog = [];
const rd = (name, i) => s.readMemory(syms[name] + i, 1)[0];
const xorSize = (i) => [rd("NewW", i) * rd("NewH", i)];
// a region's large sprites' bytes and its 8-line sprites (plot_pass's locals are gone by now, its tables not)
const regionSize = (r) => {
    let bytes = 0;
    for (let i = 0; i < rd("LgCount", 0); i++) if (rd("LgReg", i) === r) bytes += rd("NewW", i) * rd("NewH", i);
    return [bytes, rd("RegN", r)];
};
const worst = [];
for (let i = 0; i < passes.length; i++) {
    if (!(await runTo(s, syms["game.pass"], 80000000))) throw new Error(`pass ${i}: never reached`);
    s.writeMemory(syms["CmdBuf"], Array.from(passes[i]));
    const ids = [start, end, done].map((a) => s.addBreakpoint("execute", a));
    let open = null;
    for (;;) {
        s.resetBreakpointHits();
        await s.runFor(200000);
        if (s.hitBreakpoint() === null) continue;
        const pc = s.registers().pc;
        if (pc === done) break;
        const t = s.elapsedCycles, l = beam();
        if (pc === start) {
            const x = s.registers().x;
            const w0 = s.readMemory(syms["ItemW0"] + x, 1)[0], w1 = s.readMemory(syms["ItemW1"] + x, 1)[0];
            const id = s.readMemory(syms["ItemId"] + x, 1)[0], d = s.readMemory(syms["ItemD"] + x, 1)[0];
            if (s.readMemory(syms["ItemLong"] + x, 1)[0]) long++;
            open = { t, l, l0: (w0 - BEAMTOP) * 4, l1: (w1 - BEAMTOP - 1) * 4, id, d };   // (W1 has a step's margin)
            if (args.beam && beamlog.length < Number(args.beam)) beamlog.push([s.readMemory(syms["plot_pass.now"], 1)[0], l]);
        } else if (pc === end && open) {
            items++;
            // the beam's lines over the plot: from open.l on, (t - open.t) / 128 lines, wrapping at LINES
            const n = Math.ceil((t - open.t) / 128) + 1;
            let hit = false;
            for (let k = 0; k <= n && !hit; k++) {
                const line = (open.l + k) % LINES;
                if (line >= open.l0 && line < open.l1) hit = true;
            }
            const steps = (t - open.t) / 512;
            if (args.calibrate) {
                const kind = open.id & 0x80 ? "region" : "xor";
                const sz = open.id & 0x80 ? regionSize(open.id & 0x7f) : xorSize(open.id);
                cal.push([kind, ...sz, steps.toFixed(1), open.d]);
            }
            if (steps > open.d) late++;
            if (hit) { tears++; if (worst.length < 8) worst.push({ pass: i, from: open.l, lines: n, item: [open.l0, open.l1] }); }
            if (open.l >= 192) blank++; else if (open.l < open.l0) ahead++; else behind++;
            open = null;
        }
    }
    ids.forEach((id) => s.removeBreakpoint(id));
}
if (args.calibrate) for (const c of cal) console.log(c.join(" "));
if (args.beam) for (const [n, l] of beamlog) console.log(`now ${n}: the beam on line ${l}, ${(n - BEAMTOP) * 4} by now's step`);
console.log(`${passes.length} passes, ${items} items: ${tears} tears, ${late} over their time, ${long} too long for any gap; plotted in the blanking ${blank}, ahead of the beam ${ahead}, behind it ${behind}`);
for (const w of worst) console.log(`  pass ${w.pass}: the beam from line ${w.from} for ${w.lines} lines, the item on lines ${w.item[0]}-${w.item[1] - 1}`);
s.destroy();
