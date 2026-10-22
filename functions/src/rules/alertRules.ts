// =============================================================================
//  ALERT RULES — the only place where the alert tier is decided.
//  (design-v1 Section 7). Owner: Homi. Every rule below is [PROPOSED] until
//  Homi approves this file. Edit the tables; the code underneath just runs them.
//
//  How it works
//  ------------
//  1. The model returns a structured reading (schema/ecgResult.ts).
//  2. ECG_RULES are checked. Every rule that matches adds its tier + reason.
//     ECG-only tier = the highest matching tier.
//  3. If the doctor adds clinical context, CONTEXT_RULES are checked too.
//     Final tier = max(ECG-only tier, context tier). Context can RAISE the tier,
//     never lower it.
//  4. There is no "Normal" output. Nothing matched => NO_CRITICAL_PATTERN.
//
//  Confidence: a CRITICAL pattern counts from confidence 0.30 (we would rather
//  over-call than miss a STEMI). All other findings count from 0.50.
// =============================================================================

import type { ClinicalContext, EcgReading, FindingCode, RhythmCode } from "../schema/ecgResult";

export type Tier = "CRITICAL" | "URGENT" | "ABNORMAL" | "NO_CRITICAL_PATTERN" | "UNREADABLE";

/** Severity order used for max(). UNREADABLE sits above "no critical pattern":
 *  an unreadable image is less reassuring than a readable one. */
export const SEVERITY: Record<Tier, number> = {
  NO_CRITICAL_PATTERN: 0,
  UNREADABLE: 1,
  ABNORMAL: 2,
  URGENT: 3,
  CRITICAL: 4,
};

export const CRITICAL_MIN_CONFIDENCE = 0.3;
export const OTHER_MIN_CONFIDENCE = 0.5;
/** Below this overall image-quality confidence the image is treated as unreadable. */
export const MIN_IMAGE_CONFIDENCE = 0.3;

// -----------------------------------------------------------------------------
// TABLE 1 — findings → tier
// -----------------------------------------------------------------------------
export const FINDING_TIERS: Partial<Record<FindingCode, Tier>> = {
  // CRITICAL — pattern consistent with immediate life threat
  stemi_pattern: "CRITICAL",
  posterior_mi_pattern: "CRITICAL",
  de_winter_pattern: "CRITICAL",
  diffuse_st_depression_with_avr_elevation: "CRITICAL",
  third_degree_av_block: "CRITICAL",
  high_grade_av_block: "CRITICAL",
  brugada_type1: "CRITICAL",
  hyperkalaemia_pattern: "CRITICAL",

  // URGENT — significant abnormality needing prompt review
  st_elevation_not_meeting_stemi: "URGENT",
  wellens_pattern: "URGENT",
  hyperacute_t_waves: "URGENT",
  st_depression: "URGENT",
  second_degree_av_block_mobitz2: "URGENT",
  long_qt: "URGENT",
  nsvt: "URGENT",
  sinus_pause: "URGENT",
  electrical_alternans: "URGENT",
  pericarditis_pattern: "URGENT",
  // Homi, 21 Oct 2026: an old infarct is not an emergency — Q/QS with persistent ST elevation, inverted T and no
  // reciprocal depression (aneurysm pattern) is URGENT, never CRITICAL.
  old_mi_persistent_st_elevation: "URGENT",

  // ABNORMAL — abnormal, not time-critical on this image alone
  t_wave_inversion: "ABNORMAL",
  pathological_q_waves: "ABNORMAL",
  first_degree_av_block: "ABNORMAL",
  second_degree_av_block_mobitz1: "ABNORMAL",
  lbbb: "ABNORMAL",
  rbbb: "ABNORMAL",
  left_anterior_fascicular_block: "ABNORMAL",
  left_posterior_fascicular_block: "ABNORMAL",
  nonspecific_ivcd: "ABNORMAL",
  wpw_preexcitation: "ABNORMAL",
  short_qt: "ABNORMAL",
  hypokalaemia_pattern: "ABNORMAL",
  lvh: "ABNORMAL",
  rvh: "ABNORMAL",
  left_atrial_enlargement: "ABNORMAL",
  right_atrial_enlargement: "ABNORMAL",
  low_voltage: "ABNORMAL",
  pvcs: "ABNORMAL",
  pacs: "ABNORMAL",
  left_axis_deviation: "ABNORMAL",
  right_axis_deviation: "ABNORMAL",
  extreme_axis_deviation: "ABNORMAL",
  lead_reversal_suspected: "ABNORMAL",
  other: "ABNORMAL",

  // No tier on their own (shown in the list only):
  //   early_repolarisation, artefact
};

// -----------------------------------------------------------------------------
// TABLE 2 — rhythm → tier
// -----------------------------------------------------------------------------
export const RHYTHM_TIERS: Partial<Record<RhythmCode, Tier>> = {
  ventricular_fibrillation: "CRITICAL",
  ventricular_tachycardia: "CRITICAL",
  polymorphic_vt_torsades: "CRITICAL",
  asystole: "CRITICAL",

  idioventricular_rhythm: "URGENT",
  svt: "URGENT",

  atrial_fibrillation: "ABNORMAL",
  atrial_flutter: "ABNORMAL",
  junctional_rhythm: "ABNORMAL",
  ectopic_atrial_rhythm: "ABNORMAL",
  paced_rhythm: "ABNORMAL",
  sinus_tachycardia: "ABNORMAL",
  other: "ABNORMAL",
  // sinus_rhythm, sinus_bradycardia (rate rules apply), sinus_arrhythmia,
  // cannot_assess: no tier on their own
};

// -----------------------------------------------------------------------------
// TABLE 3 — measurement rules (rate, intervals, combinations)
// -----------------------------------------------------------------------------
export interface Rule<T> {
  id: string;
  tier: Tier;
  reason: string;
  when: (x: T) => boolean;
}

const rate = (r: EcgReading) => (r.rate_bpm.confidence >= OTHER_MIN_CONFIDENCE ? r.rate_bpm.value : null);
const has = (r: EcgReading, code: FindingCode, min = OTHER_MIN_CONFIDENCE) =>
  r.findings.some((f) => f.code === code && f.confidence >= min);
const rhythmIs = (r: EcgReading, ...codes: RhythmCode[]) =>
  codes.includes(r.rhythm.code) && r.rhythm.confidence >= OTHER_MIN_CONFIDENCE;

export const MEASUREMENT_RULES: Rule<EcgReading>[] = [
  {
    id: "M1",
    tier: "CRITICAL",
    reason: "Severe bradycardia (rate below 40/min)",
    when: (r) => { const v = rate(r); return v !== null && v < 40; },
  },
  {
    id: "M2",
    tier: "CRITICAL",
    reason: "Wide-complex tachycardia (rate 150/min or more with QRS 120 ms or more)",
    when: (r) => { const v = rate(r); return v !== null && v >= 150 && (r.intervals.qrs_ms ?? 0) >= 120; },
  },
  {
    id: "M3",
    tier: "CRITICAL",
    reason: "Atrial fibrillation or flutter with pre-excitation (WPW)",
    when: (r) => rhythmIs(r, "atrial_fibrillation", "atrial_flutter") && has(r, "wpw_preexcitation", CRITICAL_MIN_CONFIDENCE),
  },
  {
    id: "M4",
    tier: "CRITICAL",
    reason: "Markedly prolonged QTc (500 ms or more)",
    when: (r) => (r.intervals.qtc_ms ?? 0) >= 500,
  },
  {
    id: "M5",
    tier: "URGENT",
    reason: "Very fast rate (150/min or more)",
    when: (r) => { const v = rate(r); return v !== null && v >= 150; },
  },
  {
    id: "M6",
    tier: "URGENT",
    reason: "Marked bradycardia (rate 40–49/min)",
    when: (r) => { const v = rate(r); return v !== null && v >= 40 && v < 50; },
  },
  {
    id: "M7",
    tier: "URGENT",
    reason: "Atrial fibrillation or flutter with fast ventricular rate (120/min or more)",
    when: (r) => { const v = rate(r); return rhythmIs(r, "atrial_fibrillation", "atrial_flutter") && v !== null && v >= 120; },
  },
  {
    id: "M8",
    tier: "ABNORMAL",
    reason: "Rate above 100/min",
    when: (r) => { const v = rate(r); return v !== null && v > 100 && v < 150; },
  },
  {
    id: "M9",
    tier: "ABNORMAL",
    reason: "Rate 50–59/min",
    when: (r) => { const v = rate(r); return v !== null && v >= 50 && v < 60; },
  },
  {
    id: "M10",
    tier: "ABNORMAL",
    reason: "Broad QRS (120 ms or more)",
    when: (r) => (r.intervals.qrs_ms ?? 0) >= 120,
  },
  {
    id: "M11",
    tier: "ABNORMAL",
    reason: "Prolonged PR interval (more than 200 ms)",
    when: (r) => (r.intervals.pr_ms ?? 0) > 200,
  },
  {
    id: "M12",
    tier: "URGENT",
    reason: "Prolonged QTc (470–499 ms)",
    when: (r) => { const q = r.intervals.qtc_ms ?? 0; return q >= 470 && q < 500; },
  },
];

// -----------------------------------------------------------------------------
// TABLE 4 — clinical-context escalation (optional step, design 7.3)
// Thresholds for BP and SpO2 match the LiveHealthy Vitals design (Section 6):
// "Very high" BP = above 180 / above 120; SpO2 "Critical" = below 90 %.
// -----------------------------------------------------------------------------
export interface ContextInput {
  ctx: ClinicalContext;
  ecg: EcgReading;
  ecgTier: Tier;
}

const chestPain = (c: ClinicalContext) => c.complaints.includes("chest_pain");
const hypotension = (c: ClinicalContext) => c.sbp !== null && c.sbp < 90;
const stOrT = (r: EcgReading) =>
  r.findings.some(
    (f) =>
      ["st_elevation", "st_depression", "t_wave"].includes(f.category) &&
      f.confidence >= CRITICAL_MIN_CONFIDENCE,
  );
const CONDUCTION_CODES: FindingCode[] = [
  "first_degree_av_block", "second_degree_av_block_mobitz1", "second_degree_av_block_mobitz2",
  "high_grade_av_block", "third_degree_av_block", "lbbb", "rbbb",
  "left_anterior_fascicular_block", "left_posterior_fascicular_block", "nonspecific_ivcd",
  "wpw_preexcitation", "sinus_pause", "long_qt", "brugada_type1",
];
const conduction = (r: EcgReading) =>
  r.findings.some(
    (f) => (f.category === "conduction" || CONDUCTION_CODES.includes(f.code)) && f.confidence >= CRITICAL_MIN_CONFIDENCE,
  ) || (r.intervals.qrs_ms ?? 0) >= 120 || (r.intervals.pr_ms ?? 0) > 200 || (r.intervals.qtc_ms ?? 0) >= 470;

export const CONTEXT_RULES: Rule<ContextInput>[] = [
  {
    id: "C1",
    tier: "CRITICAL",
    reason: "Hypotension (systolic below 90) with an abnormal ECG",
    when: ({ ctx, ecgTier }) => hypotension(ctx) && SEVERITY[ecgTier] >= SEVERITY.ABNORMAL,
  },
  {
    id: "C2",
    tier: "CRITICAL",
    reason: "Chest pain with hypotension (systolic below 90)",
    when: ({ ctx }) => chestPain(ctx) && hypotension(ctx),
  },
  {
    id: "C3",
    tier: "URGENT",
    reason: "Hypotension (systolic below 90)",
    when: ({ ctx }) => hypotension(ctx),
  },
  {
    id: "C4",
    tier: "URGENT",
    reason: "Chest pain with ST/T changes",
    when: ({ ctx, ecg }) => chestPain(ctx) && stOrT(ecg),
  },
  {
    id: "C5",
    tier: "URGENT",
    reason: "Syncope or near-syncope with a conduction abnormality",
    when: ({ ctx, ecg }) => ctx.complaints.includes("syncope") && conduction(ecg),
  },
  {
    id: "C6",
    tier: "URGENT",
    reason: "Syncope or near-syncope with a rate below 50/min",
    when: ({ ctx, ecg }) =>
      ctx.complaints.includes("syncope") &&
      ((ecg.rate_bpm.value ?? 999) < 50 || (ctx.heart_rate ?? 999) < 50),
  },
  {
    id: "C7",
    tier: "URGENT",
    reason: "Very high blood pressure (above 180/120)",
    when: ({ ctx }) => (ctx.sbp ?? 0) > 180 || (ctx.dbp ?? 0) > 120,
  },
  {
    id: "C8",
    tier: "CRITICAL",
    reason: "Severe hypoxia (SpO2 below 85%)",
    when: ({ ctx }) => ctx.spo2 !== null && ctx.spo2 < 85,
  },
  {
    id: "C9",
    tier: "URGENT",
    reason: "Low oxygen saturation (SpO2 below 90%)",
    when: ({ ctx }) => ctx.spo2 !== null && ctx.spo2 < 90,
  },
  {
    id: "C10",
    tier: "URGENT",
    reason: "Measured heart rate below 40 or above 150/min",
    when: ({ ctx }) => ctx.heart_rate !== null && (ctx.heart_rate < 40 || ctx.heart_rate > 150),
  },
  {
    id: "C11",
    tier: "URGENT",
    reason:
      "Chest pain in a higher-risk patient (age 40+, diabetes or known heart disease): " +
      "a non-diagnostic ECG does not exclude ACS — repeat ECGs and troponin",
    when: ({ ctx }) =>
      chestPain(ctx) &&
      ((ctx.age ?? 0) >= 40 ||
        ctx.conditions.includes("diabetes") ||
        ctx.conditions.includes("known_heart_disease")),
  },
  {
    id: "C12",
    tier: "URGENT",
    reason: "Palpitations or syncope with pre-excitation (WPW)",
    when: ({ ctx, ecg }) =>
      (ctx.complaints.includes("palpitations") || ctx.complaints.includes("syncope")) &&
      has(ecg, "wpw_preexcitation", CRITICAL_MIN_CONFIDENCE),
  },
  {
    id: "C13",
    tier: "URGENT",
    reason: "Breathlessness with low voltage or electrical alternans (consider effusion/tamponade)",
    when: ({ ctx, ecg }) =>
      ctx.complaints.includes("breathlessness") &&
      (has(ecg, "low_voltage", CRITICAL_MIN_CONFIDENCE) || has(ecg, "electrical_alternans", CRITICAL_MIN_CONFIDENCE)),
  },
  {
    id: "C14",
    tier: "URGENT",
    reason: "Kidney disease with T-wave or conduction changes (check potassium)",
    when: ({ ctx, ecg }) =>
      ctx.conditions.includes("ckd") &&
      (ecg.findings.some((f) => f.category === "t_wave" && f.confidence >= CRITICAL_MIN_CONFIDENCE) ||
        (ecg.intervals.qrs_ms ?? 0) >= 120),
  },
];

// =============================================================================
//  Engine (no clinical content below this line)
// =============================================================================

export interface AlertReason {
  rule: string;
  tier: Tier;
  text: string;
}

export interface AlertResult {
  tier: Tier;
  reasons: AlertReason[];
}

export const maxTier = (a: Tier, b: Tier): Tier => (SEVERITY[a] >= SEVERITY[b] ? a : b);

const byTier = (a: AlertReason, b: AlertReason) => SEVERITY[b.tier] - SEVERITY[a.tier];

/** ECG-only tier from the model's reading. */
export function evaluateEcg(r: EcgReading): AlertResult {
  const reasons: AlertReason[] = [];

  for (const f of r.findings) {
    const tier = FINDING_TIERS[f.code];
    if (!tier) continue;
    const min = tier === "CRITICAL" ? CRITICAL_MIN_CONFIDENCE : OTHER_MIN_CONFIDENCE;
    if (f.confidence < min) continue;
    const leads = f.leads.length ? ` (${f.leads.join(", ")})` : "";
    reasons.push({ rule: `F:${f.code}`, tier, text: `${f.name}${leads}` });
  }

  const rt = RHYTHM_TIERS[r.rhythm.code];
  if (rt) {
    const min = rt === "CRITICAL" ? CRITICAL_MIN_CONFIDENCE : OTHER_MIN_CONFIDENCE;
    if (r.rhythm.confidence >= min) {
      reasons.push({ rule: `R:${r.rhythm.code}`, tier: rt, text: `Rhythm: ${r.rhythm.label}` });
    }
  }

  for (const m of MEASUREMENT_RULES) {
    if (m.when(r)) reasons.push({ rule: m.id, tier: m.tier, text: m.reason });
  }

  // Keep one reason per text, highest tier first.
  const seen = new Set<string>();
  const unique = reasons.sort(byTier).filter((x) => (seen.has(x.text) ? false : (seen.add(x.text), true)));

  const unreadable = !r.image_quality.readable || r.image_quality.confidence < MIN_IMAGE_CONFIDENCE;
  const hasCritical = unique.some((x) => x.tier === "CRITICAL");

  if (unreadable && !hasCritical) {
    return {
      tier: "UNREADABLE",
      reasons: [
        {
          rule: "Q1",
          tier: "UNREADABLE",
          text: "Image quality too low for a reliable reading — retake the photo",
        },
      ],
    };
  }

  let tier: Tier = "NO_CRITICAL_PATTERN";
  for (const x of unique) tier = maxTier(tier, x.tier);
  if (unreadable && hasCritical) {
    unique.push({
      rule: "Q2",
      tier: "UNREADABLE",
      text: "Image quality is poor — critical pattern flagged anyway; confirm on the original ECG",
    });
  }
  return { tier, reasons: unique };
}

/** Final tier with clinical context. Never lower than the ECG-only tier. */
export function evaluateWithContext(
  ecg: EcgReading,
  ctx: ClinicalContext,
): AlertResult & { ecgTier: Tier; escalations: AlertReason[] } {
  const base = evaluateEcg(ecg);
  const input: ContextInput = { ctx, ecg, ecgTier: base.tier };
  const escalations: AlertReason[] = CONTEXT_RULES.filter((c) => c.when(input))
    .map((c) => ({ rule: c.id, tier: c.tier, text: c.reason }))
    .sort(byTier);

  let tier = base.tier;
  for (const e of escalations) tier = maxTier(tier, e.tier);
  return { tier, ecgTier: base.tier, reasons: base.reasons, escalations };
}
