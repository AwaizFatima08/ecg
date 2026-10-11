// interpretEcg: image in, structured reading + ECG-only alert out.
// Stateless. The image exists only in memory for the duration of the call:
// it is never written to disk, Storage, Firestore or logs.
import { HttpsError } from "firebase-functions/v2/https";
import { logger } from "firebase-functions/v2";
import { evaluateEcg, type AlertResult } from "./rules/alertRules";
import type { EcgReading } from "./schema/ecgResult";
import { ProviderError, type VisionProvider } from "./provider/visionProvider";
import { checkImage } from "./guard";

export interface InterpretResponse {
  reading: EcgReading;
  alert: AlertResult;
  model: string;
  promptVersion: string;
  rulesVersion: string;
}

export const RULES_VERSION = "2026-10-12.1-proposed";

export async function handleInterpret(data: unknown, provider: VisionProvider): Promise<InterpretResponse> {
  const d = (data ?? {}) as { image?: unknown; mediaType?: unknown };
  const img = checkImage(d.image, d.mediaType);
  const started = Date.now();
  try {
    const { reading, model, promptVersion } = await provider.readEcg(img);
    const alert = evaluateEcg(reading);
    // Metadata only: no image, no reading, no tier, no user id.
    logger.info("interpretEcg ok", { ms: Date.now() - started, provider: provider.name });
    return { reading, alert, model, promptVersion, rulesVersion: RULES_VERSION };
  } catch (e) {
    if (e instanceof ProviderError) {
      logger.warn("interpretEcg provider error", { retryable: e.retryable, ms: Date.now() - started });
      throw new HttpsError(e.retryable ? "unavailable" : "failed-precondition", e.message);
    }
    logger.error("interpretEcg unexpected error", { name: (e as Error)?.name });
    throw new HttpsError("internal", "Reading failed. Please try again.");
  }
}
