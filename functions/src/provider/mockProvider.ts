// Mock adapter for emulator and end-to-end tests without an API key.
// NEVER used in production: index.ts refuses it unless running in the emulator.
// The reading is chosen by image size so the app can exercise every tier:
// it is a test fixture, not an interpretation.
import type { EcgReading } from "../schema/ecgResult";
import type { ReadRequest, ReadResult, VisionProvider } from "./visionProvider";

const base: EcgReading = {
  image_quality: { readable: true, issues: [], confidence: 0.9 },
  calibration: { paper_speed_mm_s: 25, gain_mm_mv: 10, assumed: true },
  layout: "12-lead standard",
  rate_bpm: { value: 72, confidence: 0.9 },
  rhythm: { code: "sinus_rhythm", label: "Sinus rhythm", regular: true, confidence: 0.9 },
  intervals: { pr_ms: 160, qrs_ms: 90, qt_ms: 380, qtc_ms: 410 },
  axis: { label: "normal", confidence: 0.8 },
  findings: [],
  model_notes: "MOCK READING — test fixture, not an interpretation.",
};

export const MOCK_READINGS: Record<string, EcgReading> = {
  none: base,
  stemi: {
    ...base,
    rate_bpm: { value: 96, confidence: 0.85 },
    findings: [
      { code: "stemi_pattern", name: "ST elevation, anterior leads", leads: ["V2", "V3", "V4"], category: "st_elevation", confidence: 0.8 },
      { code: "st_depression", name: "Reciprocal ST depression", leads: ["II", "III", "aVF"], category: "st_depression", confidence: 0.7 },
    ],
  },
  abnormal: {
    ...base,
    intervals: { ...base.intervals, qrs_ms: 130 },
    findings: [{ code: "rbbb", name: "Right bundle branch block", leads: ["V1", "V6", "I"], category: "conduction", confidence: 0.8 }],
  },
  unreadable: {
    ...base,
    image_quality: { readable: false, issues: ["glare", "blur"], confidence: 0.2 },
    rate_bpm: { value: null, confidence: 0 },
    rhythm: { code: "cannot_assess", label: "Cannot assess", regular: null, confidence: 0 },
    intervals: { pr_ms: null, qrs_ms: null, qt_ms: null, qtc_ms: null },
    axis: { label: "cannot_assess", confidence: 0 },
  },
};

const ORDER = ["none", "stemi", "abnormal", "unreadable"];

export class MockProvider implements VisionProvider {
  readonly name = "mock";
  async readEcg(req: ReadRequest): Promise<ReadResult> {
    const key = ORDER[req.imageBase64.length % ORDER.length];
    return { reading: MOCK_READINGS[key], model: `mock:${key}`, promptVersion: "mock" };
  }
}
