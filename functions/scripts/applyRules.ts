// Applies the production alert rules (src/rules/alertRules.ts) to readings
// produced outside the server, e.g. by the on-device engine test.
//   npx tsx scripts/applyRules.ts <in.jsonl> <out.jsonl>
import { readFileSync, writeFileSync } from "node:fs";
import { EcgReadingSchema, sanitizeReading } from "../src/schema/ecgResult";
import { evaluateEcg } from "../src/rules/alertRules";

const [inp, out] = process.argv.slice(2);
const lines = readFileSync(inp, "utf8").split("\n").filter((l) => l.trim());
const result = lines.map((l) => {
  const j = JSON.parse(l);
  const parsed = EcgReadingSchema.safeParse(j.reading);
  if (!parsed.success) return { ...j, error: "reading does not match schema: " + parsed.error.issues[0]?.message };
  const reading = sanitizeReading(parsed.data);
  return { ...j, reading, alert: evaluateEcg(reading) };
});
writeFileSync(out, result.map((r) => JSON.stringify(r)).join("\n") + "\n");
console.log(`${result.length} readings, ${result.filter((r) => r.error).length} schema errors`);
