// Request guards: kill switch, per-user daily limit, image checks.
// Nothing here stores ECG data. The only Firestore write is a counter:
//   usage/{anonUid}_{yyyymmdd} = { count, expireAt }   (design-v1 Section 6, D1)
import { getFirestore, FieldValue, Timestamp } from "firebase-admin/firestore";
import { getRemoteConfig } from "firebase-admin/remote-config";
import { HttpsError } from "firebase-functions/v2/https";
import type { ImageMediaType } from "./provider/visionProvider";

export interface RuntimeConfig {
  enabled: boolean;
  dailyLimit: number;
  disabledMessage: string;
}

const DEFAULTS: RuntimeConfig = {
  enabled: true,
  dailyLimit: 30,
  disabledMessage: "ECG reading is temporarily unavailable. Please try again later.",
};

let cached: { at: number; cfg: RuntimeConfig } | null = null;

/** Reads the server-side Remote Config template (kill switch, limits), cached 60 s. */
export async function runtimeConfig(): Promise<RuntimeConfig> {
  if (process.env.FUNCTIONS_EMULATOR === "true") return DEFAULTS;
  if (cached && Date.now() - cached.at < 60_000) return cached.cfg;
  try {
    const t = await getRemoteConfig().getServerTemplate({
      defaultConfig: {
        ecg_enabled: DEFAULTS.enabled,
        ecg_daily_limit: DEFAULTS.dailyLimit,
        ecg_disabled_message: DEFAULTS.disabledMessage,
      },
    });
    const c = t.evaluate();
    const cfg: RuntimeConfig = {
      enabled: c.getBoolean("ecg_enabled"),
      dailyLimit: Math.max(0, Math.floor(c.getNumber("ecg_daily_limit"))),
      disabledMessage: c.getString("ecg_disabled_message") || DEFAULTS.disabledMessage,
    };
    cached = { at: Date.now(), cfg };
    return cfg;
  } catch {
    // Remote Config unreachable: keep last known values, else defaults.
    return cached?.cfg ?? DEFAULTS;
  }
}

export async function assertEnabled(cfg: RuntimeConfig) {
  if (!cfg.enabled) throw new HttpsError("unavailable", cfg.disabledMessage);
}

/** Atomically counts one reading for this anonymous user today; throws when over the limit. */
export async function consumeDailyQuota(uid: string, limit: number): Promise<void> {
  // Local testing without the Firestore emulator (it needs Java 21): no counter.
  if (process.env.FUNCTIONS_EMULATOR === "true" && !process.env.FIRESTORE_EMULATOR_HOST) return;
  const day = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const ref = getFirestore().doc(`usage/${uid}_${day}`);
  // TTL policy on `expireAt` deletes counters after 2 days (set once in the console).
  const expireAt = Timestamp.fromMillis(Date.now() + 2 * 86_400_000);
  const ok = await getFirestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const count = (snap.get("count") as number | undefined) ?? 0;
    if (count >= limit) return false;
    tx.set(ref, { count: FieldValue.increment(1), expireAt }, { merge: true });
    return true;
  });
  if (!ok) {
    throw new HttpsError("resource-exhausted", `Daily limit of ${limit} readings reached. Please try again tomorrow.`);
  }
}

export const MAX_IMAGE_BYTES = 4 * 1024 * 1024;

/** Validates the uploaded image and returns cleaned base64 + media type. */
export function checkImage(b64: unknown, declared: unknown): { imageBase64: string; mediaType: ImageMediaType } {
  if (typeof b64 !== "string" || b64.length < 100) {
    throw new HttpsError("invalid-argument", "No image received.");
  }
  const clean = b64.replace(/^data:[^,]*,/, "").replace(/\s/g, "");
  let buf: Buffer;
  try {
    buf = Buffer.from(clean, "base64");
  } catch {
    throw new HttpsError("invalid-argument", "Image could not be decoded.");
  }
  if (buf.length > MAX_IMAGE_BYTES) {
    throw new HttpsError("invalid-argument", "Image is too large (max 4 MB).");
  }
  const sniffed = sniff(buf);
  if (!sniffed || (declared !== undefined && declared !== sniffed)) {
    throw new HttpsError("invalid-argument", "Only JPEG, PNG or WebP images are accepted.");
  }
  const out = sniffed === "image/jpeg" ? stripJpegMetadata(buf) : buf;
  return { imageBase64: out.toString("base64"), mediaType: sniffed };
}

function sniff(b: Buffer): ImageMediaType | null {
  if (b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return "image/jpeg";
  if (b.length > 8 && b.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return "image/png";
  if (b.length > 12 && b.toString("ascii", 0, 4) === "RIFF" && b.toString("ascii", 8, 12) === "WEBP") return "image/webp";
  return null;
}

/**
 * Removes identifying metadata segments (EXIF, XMP, IPTC, comments) from a JPEG.
 * Defence in depth: the app already strips EXIF before upload.
 */
export function stripJpegMetadata(b: Buffer): Buffer {
  const parts: Buffer[] = [b.subarray(0, 2)];
  let i = 2;
  while (i + 4 <= b.length) {
    if (b[i] !== 0xff) return b; // not a well-formed segment stream: leave untouched
    const marker = b[i + 1];
    if (marker === 0xda) { // start of scan: rest is image data
      parts.push(b.subarray(i));
      return Buffer.concat(parts);
    }
    const len = b.readUInt16BE(i + 2);
    if (len < 2 || i + 2 + len > b.length) return b;
    // APP1 EXIF/XMP, APP12 Ducky/picture info, APP13 IPTC, COM comments.
    // APP0 (JFIF), APP2 (ICC colour) and APP14 (Adobe colour transform) are kept
    // because removing them can change how the image decodes.
    const isMeta = marker === 0xe1 || marker === 0xec || marker === 0xed || marker === 0xfe;
    if (!isMeta) parts.push(b.subarray(i, i + 2 + len));
    i += 2 + len;
  }
  return b;
}
