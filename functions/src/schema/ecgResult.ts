// Model output contract (design-v1 Section 8.1).
//
// The model reads and describes; it never decides the alert tier. Free-text
// names are kept for display, but every rhythm and finding also carries a
// fixed `code`, so the rules engine (rules/alertRules.ts) can act on it
// deterministically. Any reply that does not match this schema is rejected.
import { z } from "zod";

export const RHYTHM_CODES = [
  "sinus_rhythm",
  "sinus_tachycardia",
  "sinus_bradycardia",
  "sinus_arrhythmia",
  "atrial_fibrillation",
  "atrial_flutter",
  "svt",
  "junctional_rhythm",
  "ectopic_atrial_rhythm",
  "ventricular_tachycardia",
  "polymorphic_vt_torsades",
  "ventricular_fibrillation",
  "idioventricular_rhythm",
  "asystole",
  "paced_rhythm",
  "other",
  "cannot_assess",
] as const;

export const FINDING_CODES = [
  // ST / ischaemia
  "stemi_pattern",
  "st_elevation_not_meeting_stemi",
  "posterior_mi_pattern",
  "de_winter_pattern",
  "wellens_pattern",
  "hyperacute_t_waves",
  "st_depression",
  "diffuse_st_depression_with_avr_elevation",
  "t_wave_inversion",
  "pathological_q_waves",
  "pericarditis_pattern",
  "early_repolarisation",
  // conduction
  "first_degree_av_block",
  "second_degree_av_block_mobitz1",
  "second_degree_av_block_mobitz2",
  "high_grade_av_block",
  "third_degree_av_block",
  "lbbb",
  "rbbb",
  "left_anterior_fascicular_block",
  "left_posterior_fascicular_block",
  "nonspecific_ivcd",
  "wpw_preexcitation",
  "sinus_pause",
  // repolarisation / electrolyte / channel
  "long_qt",
  "short_qt",
  "brugada_type1",
  "hyperkalaemia_pattern",
  "hypokalaemia_pattern",
  // chamber / voltage
  "lvh",
  "rvh",
  "left_atrial_enlargement",
  "right_atrial_enlargement",
  "low_voltage",
  "electrical_alternans",
  // ectopy
  "pvcs",
  "pacs",
  "nsvt",
  // axis
  "left_axis_deviation",
  "right_axis_deviation",
  "extreme_axis_deviation",
  // technical
  "lead_reversal_suspected",
  "artefact",
  "other",
] as const;

export const CATEGORIES = [
  "st_elevation",
  "st_depression",
  "t_wave",
  "conduction",
  "rhythm",
  "other",
] as const;

export const LEADS = [
  "I", "II", "III", "aVR", "aVL", "aVF",
  "V1", "V2", "V3", "V4", "V5", "V6",
  "rhythm_strip", "other",
] as const;

const confidence = z
  .number()
  .describe("0.0 to 1.0: how sure you are that this is really visible on the image");

const nullableMs = z.number().nullable().describe("milliseconds, or null if cannot assess");

export const EcgReadingSchema = z.object({
  image_quality: z.object({
    readable: z.boolean().describe("false if the trace cannot be interpreted reliably"),
    issues: z
      .array(
        z.enum([
          "glare", "skew", "blur", "low_resolution", "cropped_leads",
          "faded_trace", "shadow", "grid_not_visible", "not_an_ecg", "other",
        ]),
      )
      .describe("every quality problem you notice"),
    confidence,
  }),
  calibration: z.object({
    paper_speed_mm_s: z.number().nullable().describe("25 or 50 if printed/visible, else null"),
    gain_mm_mv: z.number().nullable().describe("usually 10; null if not visible"),
    assumed: z.boolean().describe("true if speed/gain were not visible and standard 25 mm/s, 10 mm/mV was assumed"),
  }),
  layout: z.enum(["12-lead standard", "rhythm strip", "other"]),
  rate_bpm: z.object({ value: z.number().nullable(), confidence }),
  rhythm: z.object({
    code: z.enum(RHYTHM_CODES),
    label: z.string().describe("short human-readable rhythm name"),
    regular: z.boolean().nullable(),
    confidence,
  }),
  intervals: z.object({
    pr_ms: nullableMs,
    qrs_ms: nullableMs,
    qt_ms: nullableMs,
    qtc_ms: nullableMs,
  }),
  axis: z.object({
    label: z.enum(["normal", "left", "right", "extreme", "cannot_assess"]),
    confidence,
  }),
  findings: z.array(
    z.object({
      code: z.enum(FINDING_CODES),
      name: z.string().describe("short human-readable description"),
      leads: z.array(z.enum(LEADS)),
      category: z.enum(CATEGORIES),
      confidence,
    }),
  ),
  model_notes: z.string().describe("short free text, at most 3 sentences; supporting detail only, no diagnosis headline"),
});

export type EcgReading = z.infer<typeof EcgReadingSchema>;
export type RhythmCode = (typeof RHYTHM_CODES)[number];
export type FindingCode = (typeof FINDING_CODES)[number];

/** Clamp confidences to [0,1] and drop impossible interval values. */
export function sanitizeReading(r: EcgReading): EcgReading {
  const c = (x: number) => (Number.isFinite(x) ? Math.min(1, Math.max(0, x)) : 0);
  const ms = (x: number | null, max: number) =>
    x === null || !Number.isFinite(x) || x <= 0 || x > max ? null : Math.round(x);
  const rate = r.rate_bpm.value;
  return {
    ...r,
    image_quality: { ...r.image_quality, confidence: c(r.image_quality.confidence) },
    rate_bpm: {
      value: rate === null || !Number.isFinite(rate) || rate < 0 || rate > 400 ? null : Math.round(rate),
      confidence: c(r.rate_bpm.confidence),
    },
    rhythm: { ...r.rhythm, confidence: c(r.rhythm.confidence) },
    intervals: {
      pr_ms: ms(r.intervals.pr_ms, 1000),
      qrs_ms: ms(r.intervals.qrs_ms, 400),
      qt_ms: ms(r.intervals.qt_ms, 1000),
      qtc_ms: ms(r.intervals.qtc_ms, 1000),
    },
    axis: { ...r.axis, confidence: c(r.axis.confidence) },
    findings: r.findings.map((f) => ({ ...f, confidence: c(f.confidence) })),
    model_notes: r.model_notes.slice(0, 600),
  };
}

// ---- Clinical context (design 7.3) ----

export const COMPLAINTS = [
  "chest_pain", "breathlessness", "syncope", "palpitations", "dizziness", "other",
] as const;
export const CONDITIONS = [
  "hypertension", "diabetes", "known_heart_disease", "ckd",
] as const;

export const ClinicalContextSchema = z.object({
  age: z.number().int().min(0).max(120).nullable(),
  sex: z.enum(["male", "female", "other"]).nullable(),
  complaints: z.array(z.enum(COMPLAINTS)).max(COMPLAINTS.length),
  complaint_other: z.string().max(200).nullable(),
  chest_pain_ongoing: z.boolean().nullable(),
  sbp: z.number().int().min(30).max(300).nullable(),
  dbp: z.number().int().min(10).max(200).nullable(),
  heart_rate: z.number().int().min(10).max(300).nullable(),
  spo2: z.number().int().min(40).max(100).nullable(),
  conditions: z.array(z.enum(CONDITIONS)).max(CONDITIONS.length),
});

export type ClinicalContext = z.infer<typeof ClinicalContextSchema>;
