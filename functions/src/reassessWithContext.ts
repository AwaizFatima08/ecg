// reassessWithContext: the reading the app holds in memory + optional clinical
// context in, escalated alert out. No image is resent. The ECG-only tier is
// recomputed here from the reading (the client's tier is never trusted), and
// context can only raise it.
import { HttpsError } from "firebase-functions/v2/https";
import { ClinicalContextSchema, EcgReadingSchema, sanitizeReading } from "./schema/ecgResult";
import { evaluateWithContext } from "./rules/alertRules";
import { RULES_VERSION } from "./interpretEcg";

export function handleReassess(data: unknown) {
  const d = (data ?? {}) as { reading?: unknown; context?: unknown };
  const reading = EcgReadingSchema.safeParse(d.reading);
  const context = ClinicalContextSchema.safeParse(d.context);
  if (!reading.success) throw new HttpsError("invalid-argument", "Reading is missing or invalid.");
  if (!context.success) throw new HttpsError("invalid-argument", "Clinical details are invalid.");
  const result = evaluateWithContext(sanitizeReading(reading.data), context.data);
  return { ...result, rulesVersion: RULES_VERSION };
}
