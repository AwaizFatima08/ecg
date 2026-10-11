// Cloud Functions entry point (design-v1 Sections 5-6).
import { initializeApp } from "firebase-admin/app";
import { setGlobalOptions } from "firebase-functions/v2";
import { onCall, HttpsError, type CallableRequest } from "firebase-functions/v2/https";
import { defineSecret, defineString } from "firebase-functions/params";
import { handleInterpret } from "./interpretEcg";
import { handleReassess } from "./reassessWithContext";
import { assertEnabled, consumeDailyQuota, runtimeConfig } from "./guard";
import { ClaudeProvider, DEFAULT_CLAUDE_MODEL } from "./provider/claudeProvider";
import { MockProvider } from "./provider/mockProvider";
import type { VisionProvider } from "./provider/visionProvider";

initializeApp();

// Mumbai: closest region to Pakistan.
setGlobalOptions({ region: "asia-south1", maxInstances: 10 });

const ANTHROPIC_API_KEY = defineSecret("ANTHROPIC_API_KEY");
const ECG_PROVIDER = defineString("ECG_PROVIDER", { default: "claude" });
const ECG_MODEL = defineString("ECG_MODEL", { default: DEFAULT_CLAUDE_MODEL });

const isEmulator = () => process.env.FUNCTIONS_EMULATOR === "true";
// App Check is always enforced in production. Only the local emulator, where
// tokens cannot be verified, skips it.
const ENFORCE_APP_CHECK = process.env.FUNCTIONS_EMULATOR !== "true";

function provider(): VisionProvider {
  const name = ECG_PROVIDER.value();
  if (name === "mock") {
    if (!isEmulator()) throw new HttpsError("failed-precondition", "Reading service is not configured.");
    return new MockProvider();
  }
  const key = ANTHROPIC_API_KEY.value();
  if (!key) throw new HttpsError("failed-precondition", "Reading service is not configured.");
  return new ClaudeProvider(key, ECG_MODEL.value());
}

function requireUser(req: CallableRequest): string {
  // Anonymous sign-in gives a stable id for rate limiting; it is not a login.
  const uid = req.auth?.uid;
  if (!uid) throw new HttpsError("unauthenticated", "Please reopen the app and try again.");
  return uid;
}

export const interpretEcg = onCall(
  {
    secrets: [ANTHROPIC_API_KEY],
    enforceAppCheck: ENFORCE_APP_CHECK,
    memory: "512MiB",
    timeoutSeconds: 300,
    concurrency: 20,
  },
  async (req) => {
    const uid = requireUser(req);
    const cfg = await runtimeConfig();
    await assertEnabled(cfg);
    await consumeDailyQuota(uid, cfg.dailyLimit);
    return handleInterpret(req.data, provider());
  },
);

export const reassessWithContext = onCall(
  { enforceAppCheck: ENFORCE_APP_CHECK, memory: "256MiB", timeoutSeconds: 30 },
  async (req) => {
    requireUser(req);
    const cfg = await runtimeConfig();
    await assertEnabled(cfg);
    return handleReassess(req.data);
  },
);
