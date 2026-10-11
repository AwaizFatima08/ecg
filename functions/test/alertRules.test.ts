import { describe, expect, it } from "vitest";
import { evaluateEcg, evaluateWithContext, SEVERITY, type Tier } from "../src/rules/alertRules";
import type { ClinicalContext, EcgReading } from "../src/schema/ecgResult";
import { MOCK_READINGS } from "../src/provider/mockProvider";

const clean = MOCK_READINGS.none;
const reading = (patch: Partial<EcgReading>): EcgReading => ({ ...clean, ...patch });
const finding = (code: EcgReading["findings"][number]["code"], confidence = 0.8, category: EcgReading["findings"][number]["category"] = "other") =>
  ({ code, name: code, leads: [], category, confidence }) as EcgReading["findings"][number];
const noCtx: ClinicalContext = {
  age: null, sex: null, complaints: [], complaint_other: null, chest_pain_ongoing: null,
  sbp: null, dbp: null, heart_rate: null, spo2: null, conditions: [],
};
const ctx = (patch: Partial<ClinicalContext>): ClinicalContext => ({ ...noCtx, ...patch });

describe("ECG-only tier", () => {
  it("never says normal: a clean reading is NO_CRITICAL_PATTERN", () => {
    const r = evaluateEcg(clean);
    expect(r.tier).toBe("NO_CRITICAL_PATTERN");
    expect(r.reasons).toEqual([]);
  });

  it.each([
    ["stemi_pattern"], ["posterior_mi_pattern"], ["de_winter_pattern"],
    ["third_degree_av_block"], ["high_grade_av_block"], ["brugada_type1"], ["hyperkalaemia_pattern"],
  ] as const)("%s is CRITICAL", (code) => {
    expect(evaluateEcg(reading({ findings: [finding(code)] })).tier).toBe("CRITICAL");
  });

  it.each([["ventricular_fibrillation"], ["ventricular_tachycardia"], ["polymorphic_vt_torsades"], ["asystole"]] as const)(
    "rhythm %s is CRITICAL",
    (code) => {
      expect(evaluateEcg(reading({ rhythm: { code, label: code, regular: null, confidence: 0.6 } })).tier).toBe("CRITICAL");
    },
  );

  it("asymmetric confidence: a CRITICAL pattern counts at 0.30, others need 0.50", () => {
    expect(evaluateEcg(reading({ findings: [finding("stemi_pattern", 0.3)] })).tier).toBe("CRITICAL");
    expect(evaluateEcg(reading({ findings: [finding("stemi_pattern", 0.29)] })).tier).toBe("NO_CRITICAL_PATTERN");
    expect(evaluateEcg(reading({ findings: [finding("rbbb", 0.45)] })).tier).toBe("NO_CRITICAL_PATTERN");
    expect(evaluateEcg(reading({ findings: [finding("rbbb", 0.5)] })).tier).toBe("ABNORMAL");
  });

  it("rate rules", () => {
    const at = (v: number, qrs = 90): Tier =>
      evaluateEcg(reading({ rate_bpm: { value: v, confidence: 0.9 }, intervals: { ...clean.intervals, qrs_ms: qrs } })).tier;
    expect(at(35)).toBe("CRITICAL");
    expect(at(45)).toBe("URGENT");
    expect(at(55)).toBe("ABNORMAL");
    expect(at(80)).toBe("NO_CRITICAL_PATTERN");
    expect(at(120)).toBe("ABNORMAL");
    expect(at(160)).toBe("URGENT");
    expect(at(160, 140)).toBe("CRITICAL");
  });

  it("low-confidence rate is ignored", () => {
    expect(evaluateEcg(reading({ rate_bpm: { value: 30, confidence: 0.3 } })).tier).toBe("NO_CRITICAL_PATTERN");
  });

  it("QTc rules", () => {
    const q = (v: number) => evaluateEcg(reading({ intervals: { ...clean.intervals, qtc_ms: v } })).tier;
    expect(q(520)).toBe("CRITICAL");
    expect(q(480)).toBe("URGENT");
    expect(q(440)).toBe("NO_CRITICAL_PATTERN");
  });

  it("AF with pre-excitation is CRITICAL; fast AF is URGENT; controlled AF is ABNORMAL", () => {
    const af = { code: "atrial_fibrillation", label: "AF", regular: false, confidence: 0.8 } as const;
    expect(evaluateEcg(reading({ rhythm: af, findings: [finding("wpw_preexcitation", 0.4)] })).tier).toBe("CRITICAL");
    expect(evaluateEcg(reading({ rhythm: af, rate_bpm: { value: 130, confidence: 0.8 } })).tier).toBe("URGENT");
    expect(evaluateEcg(reading({ rhythm: af, rate_bpm: { value: 85, confidence: 0.8 } })).tier).toBe("ABNORMAL");
  });

  it("unreadable image gives UNREADABLE with retake advice", () => {
    const r = evaluateEcg(MOCK_READINGS.unreadable);
    expect(r.tier).toBe("UNREADABLE");
    expect(r.reasons[0].text).toMatch(/retake/i);
  });

  it("very low image confidence counts as unreadable even if flagged readable", () => {
    const r = evaluateEcg(reading({ image_quality: { readable: true, issues: [], confidence: 0.2 } }));
    expect(r.tier).toBe("UNREADABLE");
  });

  it("a critical pattern on a poor image is still CRITICAL, with a quality warning", () => {
    const r = evaluateEcg(
      reading({ image_quality: { readable: false, issues: ["blur"], confidence: 0.2 }, findings: [finding("stemi_pattern", 0.5)] }),
    );
    expect(r.tier).toBe("CRITICAL");
    expect(r.reasons.some((x) => x.rule === "Q2")).toBe(true);
  });

  it("reasons are sorted highest tier first", () => {
    const r = evaluateEcg(MOCK_READINGS.stemi);
    for (let i = 1; i < r.reasons.length; i++) {
      expect(SEVERITY[r.reasons[i - 1].tier]).toBeGreaterThanOrEqual(SEVERITY[r.reasons[i].tier]);
    }
  });

  it("early repolarisation and artefact alone do not raise the tier", () => {
    expect(evaluateEcg(reading({ findings: [finding("early_repolarisation"), finding("artefact")] })).tier).toBe(
      "NO_CRITICAL_PATTERN",
    );
  });
});

describe("clinical context can only escalate", () => {
  const all: EcgReading[] = Object.values(MOCK_READINGS);
  const contexts: ClinicalContext[] = [
    noCtx,
    ctx({ complaints: ["chest_pain"], age: 25 }),
    ctx({ sbp: 120, dbp: 80, spo2: 98, heart_rate: 70 }),
    ctx({ complaints: ["dizziness"] }),
  ];

  it("final tier is never below the ECG-only tier (all fixtures x contexts)", () => {
    for (const e of all) for (const c of contexts) {
      const r = evaluateWithContext(e, c);
      expect(SEVERITY[r.tier]).toBeGreaterThanOrEqual(SEVERITY[r.ecgTier]);
      expect(r.ecgTier).toBe(evaluateEcg(e).tier);
    }
  });

  it("ABNORMAL ECG + chest pain + hypotension → CRITICAL (design 7.3 example)", () => {
    const r = evaluateWithContext(MOCK_READINGS.abnormal, ctx({ complaints: ["chest_pain"], sbp: 80 }));
    expect(r.ecgTier).toBe("ABNORMAL");
    expect(r.tier).toBe("CRITICAL");
    expect(r.escalations.map((e) => e.rule)).toEqual(expect.arrayContaining(["C1", "C2"]));
  });

  it("ST/T change + chest pain → at least URGENT", () => {
    const e = reading({ findings: [finding("t_wave_inversion", 0.7, "t_wave")] });
    expect(evaluateWithContext(e, ctx({ complaints: ["chest_pain"], age: 25 })).tier).toBe("URGENT");
  });

  it("syncope + conduction abnormality → at least URGENT", () => {
    expect(evaluateWithContext(MOCK_READINGS.abnormal, ctx({ complaints: ["syncope"] })).tier).toBe("URGENT");
  });

  it("LiveHealthy thresholds: BP above 180/120 and SpO2 below 90 escalate", () => {
    expect(evaluateWithContext(clean, ctx({ sbp: 181 })).tier).toBe("URGENT");
    expect(evaluateWithContext(clean, ctx({ sbp: 180, dbp: 120 })).tier).toBe("NO_CRITICAL_PATTERN");
    expect(evaluateWithContext(clean, ctx({ dbp: 121 })).tier).toBe("URGENT");
    expect(evaluateWithContext(clean, ctx({ spo2: 89 })).tier).toBe("URGENT");
    expect(evaluateWithContext(clean, ctx({ spo2: 84 })).tier).toBe("CRITICAL");
    expect(evaluateWithContext(clean, ctx({ spo2: 90 })).tier).toBe("NO_CRITICAL_PATTERN");
  });

  it("chest pain in an older patient with a quiet ECG is still URGENT (ACS not excluded)", () => {
    expect(evaluateWithContext(clean, ctx({ complaints: ["chest_pain"], age: 55 })).tier).toBe("URGENT");
  });

  it("a CRITICAL ECG stays CRITICAL with reassuring context", () => {
    expect(evaluateWithContext(MOCK_READINGS.stemi, ctx({ sbp: 125, spo2: 99, heart_rate: 80 })).tier).toBe("CRITICAL");
  });

  it("escalations explain themselves", () => {
    const r = evaluateWithContext(clean, ctx({ sbp: 85 }));
    expect(r.escalations[0].text).toMatch(/hypotension/i);
  });
});
