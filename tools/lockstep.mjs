// The BBC's half of tools/lockstep.py: the game in headless jsbeeb with a pass's keys from --keys (one line a
// pass: GameKeys' bits), each set just after the pass before has read its own (game.keyed), so the IRQ's scans
// in between give the next pass exactly them. At each pass's game.passed, the state named by --vars (symbols,
// a byte each) is written as a line of numbers.
import { readFileSync } from "node:fs";
import { bootDisc, runTo, symbols, BBC } from "./jsbeeb.mjs";

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) =>
    x.startsWith("--") ? [...a, [x.slice(2), all[i + 1]]] : a, []));
const syms = symbols(args.symbols ?? "build/exolon.json");
const keys = readFileSync(args.keys, "utf8").trim().split("\n").map(Number);
const vars = args.vars.split(",");
const KEY = [BBC.Z, BBC.X, BBC.COLON_STAR, BBC.SLASH, BBC.RETURN];
const s = await bootDisc(args.disc ?? "build/exolon.ssd");
let down = 0;
const hold = (k) => { KEY.forEach((c, b) => { const on = k >> b & 1; if (on !== (down >> b & 1)) on ? s.keyDownRaw(c) : s.keyUpRaw(c); }); down = k; };
hold(keys[0]);
const out = [];
for (let i = 0; i < keys.length; i++) {
    if (!(await runTo(s, syms["game.keyed"], 80000000))) throw new Error(`pass ${i}: never keyed`);
    hold(i + 1 < keys.length ? keys[i + 1] : 0);
    if (!(await runTo(s, syms["game.passed"], 80000000))) throw new Error(`pass ${i}: never passed`);
    out.push(vars.map((v) => s.readMemory(syms[v], 1)[0]).join(" "));
}
console.log(out.join("\n"));
s.destroy();
