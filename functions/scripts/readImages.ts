// Phase 0 batch reader: runs every image in a folder through the SAME provider
// code as the Cloud Function and appends one JSON line per image.
// Resumable: images already in the output file are skipped.
//
//   ANTHROPIC_API_KEY=... npx tsx scripts/readImages.ts <imagesDir> <out.jsonl> [--model claude-opus-5-5] [--only scan|photo] [--limit N] [--concurrency 3]
import { readFileSync, readdirSync, existsSync, appendFileSync } from "node:fs";
import { join, extname } from "node:path";
import { ClaudeProvider, DEFAULT_CLAUDE_MODEL } from "../src/provider/claudeProvider";
import { evaluateEcg } from "../src/rules/alertRules";
import { checkImage } from "../src/guard";

const args = process.argv.slice(2);
const opt = (name: string, dflt?: string) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : dflt;
};
const [dir, out] = args;
if (!dir || !out) {
  console.error("usage: readImages.ts <imagesDir> <out.jsonl> [--model M] [--only scan|photo] [--limit N] [--concurrency N]");
  process.exit(2);
}
const key = process.env.ANTHROPIC_API_KEY;
if (!key) {
  console.error("ANTHROPIC_API_KEY is not set (source secrets/anthropic.env)");
  process.exit(2);
}
const model = opt("model", DEFAULT_CLAUDE_MODEL)!;
const only = opt("only");
const limit = Number(opt("limit", "0"));
const concurrency = Number(opt("concurrency", "3"));

const done = new Set<string>();
if (existsSync(out)) {
  for (const line of readFileSync(out, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try { const j = JSON.parse(line); if (!j.error) done.add(j.image); } catch { /* ignore */ }
  }
}

let files = readdirSync(dir)
  .filter((f) => [".jpg", ".jpeg", ".png", ".webp"].includes(extname(f).toLowerCase()))
  .filter((f) => !only || f.includes(`_${only}.`))
  .sort()
  .filter((f) => !done.has(f));
if (limit > 0) files = files.slice(0, limit);
console.log(`${files.length} images to read with ${model} (${done.size} already done)`);

const provider = new ClaudeProvider(key, model);
let next = 0, ok = 0, failed = 0;

async function worker() {
  while (next < files.length) {
    const f = files[next++];
    const started = Date.now();
    try {
      const img = checkImage(readFileSync(join(dir, f)).toString("base64"), undefined);
      const r = await provider.readEcg(img);
      const alert = evaluateEcg(r.reading);
      appendFileSync(out, JSON.stringify({ image: f, model: r.model, promptVersion: r.promptVersion, ms: Date.now() - started, reading: r.reading, alert }) + "\n");
      ok++;
      console.log(`ok   ${f} -> ${alert.tier} (${((Date.now() - started) / 1000).toFixed(1)} s)`);
    } catch (e) {
      appendFileSync(out, JSON.stringify({ image: f, model, error: (e as Error).message }) + "\n");
      failed++;
      console.log(`FAIL ${f}: ${(e as Error).message}`);
    }
  }
}

Promise.all(Array.from({ length: concurrency }, worker)).then(() => {
  console.log(`done: ${ok} ok, ${failed} failed`);
});
