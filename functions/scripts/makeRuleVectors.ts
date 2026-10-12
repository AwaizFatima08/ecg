// Generates rule-engine test vectors for the Dart port (app/lib/engine/rules.dart).
//   npx tsx scripts/makeRuleVectors.ts ../app/test/vectors/rules.json
import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { evaluateEcg, evaluateWithContext } from "../src/rules/alertRules";
import { FINDING_CODES, RHYTHM_CODES, CATEGORIES, COMPLAINTS, CONDITIONS, type EcgReading, type ClinicalContext } from "../src/schema/ecgResult";

let seed = 42;
const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const pick = <T,>(a: readonly T[]) => a[Math.floor(rnd() * a.length)];
const maybe = <T,>(v: T, p = 0.5): T | null => (rnd() < p ? v : null);

const readings: EcgReading[] = [];
// real engine readings from the Phase 0 runs, plus random ones
const real = "../validation/images/readings_engine-v3.jsonl";
if (existsSync(real)) {
  for (const l of readFileSync(real, "utf8").split("\n").filter(Boolean).slice(0, 120)) readings.push(JSON.parse(l).reading);
}
for (let i = 0; i < 200; i++) {
  const nf = Math.floor(rnd() * 4);
  readings.push({
    image_quality: { readable: rnd() > 0.1, issues: [], confidence: rnd() },
    calibration: { paper_speed_mm_s: null, gain_mm_mv: null, assumed: true },
    layout: "12-lead standard",
    rate_bpm: { value: maybe(Math.round(20 + rnd() * 200), 0.9), confidence: rnd() },
    rhythm: { code: pick(RHYTHM_CODES), label: "x", regular: rnd() > 0.5, confidence: rnd() },
    intervals: {
      pr_ms: maybe(Math.round(80 + rnd() * 300)), qrs_ms: maybe(Math.round(60 + rnd() * 120)),
      qt_ms: null, qtc_ms: maybe(Math.round(350 + rnd() * 200)),
    },
    axis: { label: "normal", confidence: 0.5 },
    findings: Array.from({ length: nf }, () => ({
      code: pick(FINDING_CODES), name: "f", leads: [], category: pick(CATEGORIES), confidence: rnd(),
    })),
    model_notes: "",
  });
}
const contexts: ClinicalContext[] = Array.from({ length: 6 }, () => ({
  age: maybe(Math.round(18 + rnd() * 70)), sex: maybe(pick(["male", "female"] as const)),
  complaints: COMPLAINTS.filter(() => rnd() < 0.3), complaint_other: null, chest_pain_ongoing: maybe(rnd() > 0.5),
  sbp: maybe(Math.round(70 + rnd() * 140)), dbp: maybe(Math.round(40 + rnd() * 90)),
  heart_rate: maybe(Math.round(30 + rnd() * 150)), spo2: maybe(Math.round(80 + rnd() * 20)),
  conditions: CONDITIONS.filter(() => rnd() < 0.3),
}));
const cases = readings.map((r, i) => {
  const ctx = contexts[i % contexts.length];
  const e = evaluateEcg(r);
  const c = evaluateWithContext(r, ctx);
  return { reading: r, context: ctx, ecg: { tier: e.tier, rules: e.reasons.map((x) => x.rule) },
           ctx: { tier: c.tier, escalations: c.escalations.map((x) => x.rule) } };
});
writeFileSync(process.argv[2], JSON.stringify(cases));
console.log(`${cases.length} rule cases`);
