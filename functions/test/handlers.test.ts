import { describe, expect, it, vi } from "vitest";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { checkImage, stripJpegMetadata } from "../src/guard";
import { handleInterpret } from "../src/interpretEcg";
import { handleReassess } from "../src/reassessWithContext";
import { MockProvider, MOCK_READINGS } from "../src/provider/mockProvider";
import { EcgReadingSchema, sanitizeReading } from "../src/schema/ecgResult";

vi.mock("firebase-functions/v2", () => ({ logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() } }));

// Minimal JPEG: SOI, APP0 JFIF, APP1 "Exif" with a fake name, COM, SOS + data, EOI.
function jpegWithExif(): Buffer {
  const seg = (marker: number, payload: Buffer) => {
    const h = Buffer.alloc(4);
    h[0] = 0xff; h[1] = marker; h.writeUInt16BE(payload.length + 2, 2);
    return Buffer.concat([h, payload]);
  };
  return Buffer.concat([
    Buffer.from([0xff, 0xd8]),
    seg(0xe0, Buffer.from("JFIF\0\x01\x01\0\0\x01\0\x01\0\0", "binary")),
    seg(0xe1, Buffer.from("Exif\0\0PATIENT NAME GPS 31.5,74.3")),
    seg(0xfe, Buffer.from("comment: MRN 123456")),
    seg(0xda, Buffer.from([0, 0, 0, 0])),
    Buffer.alloc(200, 0x11),
    Buffer.from([0xff, 0xd9]),
  ]);
}

describe("image checks", () => {
  it("strips EXIF and comments, keeps JFIF and scan data", () => {
    const out = stripJpegMetadata(jpegWithExif());
    const s = out.toString("binary");
    expect(s).not.toMatch(/PATIENT|MRN|Exif/);
    expect(s).toMatch(/JFIF/);
    expect(out.subarray(-2)).toEqual(Buffer.from([0xff, 0xd9]));
  });

  it("checkImage strips metadata and returns JPEG", () => {
    const r = checkImage(jpegWithExif().toString("base64"), "image/jpeg");
    expect(r.mediaType).toBe("image/jpeg");
    expect(Buffer.from(r.imageBase64, "base64").toString("binary")).not.toMatch(/PATIENT/);
  });

  it("rejects non-images, mismatched type, missing data and oversize", () => {
    expect(() => checkImage(Buffer.alloc(300, 0x41).toString("base64"), undefined)).toThrow(/JPEG, PNG or WebP/);
    expect(() => checkImage(jpegWithExif().toString("base64"), "image/png")).toThrow();
    expect(() => checkImage(undefined, undefined)).toThrow(/No image/);
    const big = Buffer.concat([Buffer.from([0xff, 0xd8, 0xff]), Buffer.alloc(4 * 1024 * 1024)]);
    expect(() => checkImage(big.toString("base64"), "image/jpeg")).toThrow(/too large/);
  });
});

describe("handlers", () => {
  it("interpret returns reading + alert + versions", async () => {
    const res = await handleInterpret({ image: jpegWithExif().toString("base64"), mediaType: "image/jpeg" }, new MockProvider());
    expect(EcgReadingSchema.safeParse(res.reading).success).toBe(true);
    expect(res.alert.tier).toBeTruthy();
    expect(res.rulesVersion).toMatch(/proposed/);
  });

  it("reassess recomputes the ECG tier server-side and escalates", () => {
    const r = handleReassess({
      reading: MOCK_READINGS.abnormal,
      context: {
        age: 60, sex: "male", complaints: ["chest_pain"], complaint_other: null, chest_pain_ongoing: true,
        sbp: 82, dbp: 50, heart_rate: 110, spo2: 93, conditions: ["diabetes"],
      },
    });
    expect(r.ecgTier).toBe("ABNORMAL");
    expect(r.tier).toBe("CRITICAL");
  });

  it("reassess rejects bad input", () => {
    expect(() => handleReassess({ reading: { x: 1 }, context: {} })).toThrow(/Reading/);
  });
});

describe("schema", () => {
  it("converts to a structured-output format without error", () => {
    expect(() => zodOutputFormat(EcgReadingSchema)).not.toThrow();
  });

  it("sanitize clamps confidences and drops impossible values", () => {
    const r = sanitizeReading({
      ...MOCK_READINGS.none,
      rate_bpm: { value: 900, confidence: 3 },
      intervals: { pr_ms: -5, qrs_ms: 100.4, qt_ms: 5000, qtc_ms: 420 },
    });
    expect(r.rate_bpm).toEqual({ value: null, confidence: 1 });
    expect(r.intervals).toEqual({ pr_ms: null, qrs_ms: 100, qt_ms: null, qtc_ms: 420 });
  });
});
