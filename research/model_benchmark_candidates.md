# Low-cost semantic-mapping model shortlist

Checked: 22 August 2026. Prices are OpenRouter catalog/provider-route prices per one million tokens and can change. Pin model snapshots and save actual per-run usage/cost rather than treating this table as a permanent quote.

| Priority | OpenRouter model ID | Approx. input / output | Why it belongs in the benchmark |
|---|---|---:|---|
| 1 | `deepseek/deepseek-v4-flash-0731` | $0.065 / $0.18 at the lowest listed route | Pinned GA snapshot, 1M+ context, JSON-schema structured output, thinking/non-thinking modes, very low price. DeepSeek documents the underlying `DeepSeek-V4-Flash-0731` snapshot and JSON output. |
| 2 | `openai/gpt-5.4-nano` | $0.20 / $1.25 | 400K context; explicitly positioned for high-volume data extraction and low latency. |
| 3 | `mistralai/mistral-small-2603` | about $0.15 / $0.60 | Structured output, 256K-class context and high observed throughput; use as the speed challenger. |
| 4 | `google/gemini-3.7-flash` | about $0.375 / $1.875 on the checked discounted route | 1M context, native JSON Schema and adjustable thinking. Newer route history makes it an accuracy challenger, not the default. |
| 5 | `qwen/qwen3.7-plus` | about $0.32 / $1.28 | 1M context, structured output and switchable reasoning; slower observed throughput, so use as an accuracy challenger. |

Primary comparison: DeepSeek V4 Flash 0731 versus GPT-5.4 Nano. Add Mistral Small 2603 if latency matters. Require provider parameter support and strict JSON Schema; schema enforcement proves response shape, not financial correctness.

## Evaluation contract

- Use the same answer-free prompt, schema and Strategy 3 evidence pages for every model.
- Use temperature 0.0/non-thinking for the reproducible fast lane, plus one documented reasoning-enabled lane per model.
- Run three repeats in screening; take the best two models into ten-repeat confirmation.
- Report row exact accuracy, document-perfect accuracy, schema validity, seven arithmetic identities, missing/extra rows, year-column swaps, p50/p95 latency, actual cost and cached-token usage.
- Do not discard values below a model-confidence threshold. Confidence is review metadata; deterministic source/year/unit/sign/total checks and verified gold determine correctness.
- Caching helps only byte-identical prefixes. Keep the stable instructions/schema prefix unchanged and verify cached tokens from provider usage records.

Sources: [DeepSeek model and pricing documentation](https://api-docs.deepseek.com/quick_start/pricing/), [OpenRouter DeepSeek V4 Flash 0731 routes and capabilities](https://openrouter.ai/deepseek/deepseek-v4-flash-0731), [OpenRouter GPT-5.4 Nano](https://openrouter.ai/openai/gpt-5.4-nano/api), [Gemini 3.7 Flash model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash), [Mistral model guide](https://docs.mistral.ai/inference/model-selection-guide?models=mistral-small-4-0-26-03).
