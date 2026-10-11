// Claude (Anthropic) vision adapter.
// The API key comes only from the function's secret ANTHROPIC_API_KEY; it is
// never sent to or stored in the app. Image bytes are never logged.
import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { EcgReadingSchema, sanitizeReading } from "../schema/ecgResult";
import { PROMPT_VERSION, SYSTEM_PROMPT, USER_INSTRUCTION } from "./prompt";
import { ProviderError, type ReadRequest, type ReadResult, type VisionProvider } from "./visionProvider";

export const DEFAULT_CLAUDE_MODEL = "claude-opus-5-5";

export class ClaudeProvider implements VisionProvider {
  readonly name = "claude";
  private readonly client: Anthropic;

  constructor(
    apiKey: string,
    private readonly model: string = DEFAULT_CLAUDE_MODEL,
    private readonly effort: "low" | "medium" | "high" | "xhigh" | "max" = "high",
  ) {
    // 2 SDK-level retries for 429/5xx/network; 100 s per attempt.
    this.client = new Anthropic({ apiKey, maxRetries: 2, timeout: 100_000 });
  }

  async readEcg(req: ReadRequest): Promise<ReadResult> {
    // Design 8.1: reject anything off-contract and retry once.
    let lastProblem = "";
    for (let attempt = 0; attempt < 2; attempt++) {
      const res = await this.call(req);
      if (res.stop_reason === "refusal") {
        throw new ProviderError("The model declined to read this image.", false);
      }
      if (res.stop_reason === "max_tokens") {
        lastProblem = "reply was cut off";
        continue;
      }
      const parsed = res.parsed_output;
      const check = parsed ? EcgReadingSchema.safeParse(parsed) : null;
      if (check?.success) {
        return { reading: sanitizeReading(check.data), model: res.model, promptVersion: PROMPT_VERSION };
      }
      lastProblem = "reply did not match the result schema";
    }
    throw new ProviderError(`Reading failed: ${lastProblem}.`, true);
  }

  private async call(req: ReadRequest) {
    try {
      return await this.client.messages.parse({
        model: this.model,
        max_tokens: 16000,
        system: SYSTEM_PROMPT,
        output_config: { effort: this.effort, format: zodOutputFormat(EcgReadingSchema) },
        messages: [
          {
            role: "user",
            content: [
              { type: "image", source: { type: "base64", media_type: req.mediaType, data: req.imageBase64 } },
              { type: "text", text: USER_INSTRUCTION },
            ],
          },
        ],
      });
    } catch (e) {
      // Most specific first; never include request content in messages.
      if (e instanceof Anthropic.RateLimitError) throw new ProviderError("Reading service is busy.", true);
      if (e instanceof Anthropic.AuthenticationError) throw new ProviderError("Reading service is not configured.", false);
      if (e instanceof Anthropic.BadRequestError) throw new ProviderError("The image could not be processed.", false);
      if (e instanceof Anthropic.APIConnectionError) throw new ProviderError("Could not reach the reading service.", true);
      if (e instanceof Anthropic.APIError) throw new ProviderError(`Reading service error (${e.status ?? "?"}).`, true);
      throw e;
    }
  }
}
