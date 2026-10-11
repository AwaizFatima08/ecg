// Provider-agnostic interface for the reading engine (design-v1 Section 5).
// One adapter per vendor; the rest of the code only sees VisionProvider.
import type { EcgReading } from "../schema/ecgResult";

export type ImageMediaType = "image/jpeg" | "image/png" | "image/webp";

export interface ReadRequest {
  /** Base64 image data, no data: prefix, no newlines. */
  imageBase64: string;
  mediaType: ImageMediaType;
}

export interface ReadResult {
  reading: EcgReading;
  /** Model that actually produced the reading (shown in results for traceability). */
  model: string;
  promptVersion: string;
}

export class ProviderError extends Error {
  constructor(
    message: string,
    /** true when a retry later might succeed (rate limit, overload, network). */
    readonly retryable: boolean,
  ) {
    super(message);
    this.name = "ProviderError";
  }
}

export interface VisionProvider {
  readonly name: string;
  readEcg(req: ReadRequest): Promise<ReadResult>;
}
