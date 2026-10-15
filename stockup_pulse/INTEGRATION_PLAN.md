# External Provider Integration Plan

Integrate AMD image extraction and explanations, Evolus PDF extraction, and Twilio inbound approval messaging through the existing Python adapter/API boundaries. Keep prices, quantities, and orders deterministic. Route images to AMD and PDFs to Evolus, normalize both outputs into one validated schema for user review, and keep provider calls disabled until credentials and contracts are verified. Keep outbound supplier dispatch disabled until each supplier has a verified, opted-in recipient number.

## Implementation Steps

1. **Confirm provider contracts and configuration**
   - Use the supplied AMD Token Factory contract: shared Radeon Cloud API base URL `https://developer.amd.com.cn/radeon/api/v1`, OpenAI-compatible chat completions, Bearer authentication, dynamic model catalog, image capability flags, shared rate limits, and documented error semantics. The team key uses the `rc-` plus 48 hex character format and is revealed only after every team member redeems it; obtain it directly through Token Factory and keep it out of chat and source control.
   - Configure the Evolus REST API at `https://api.evolus.ai/api/v1`; send `X-ApiKey` and `X-Application-Id` headers, with both values held in server-side configuration only. Never put secrets in workflow `parameters`, because Evolus stores parameters with the run. The separate OpenAI-compatible agent-chat API (`https://api.evolus.ai/v1`, Bearer auth) is not used for this integration.
   - Per the [Evolus developer docs](https://evolus.ai/developers), use the account-specific workflow endpoint `POST /workflows/{workflowId}/execute`, sending `input` and `file` as multipart form fields and only declared flat JSON `parameters`. The endpoint returns `202 Accepted` with an `executionId` (also in `X-Workflow-Execution-Id`), plus `jobId`, `enqueuedAt`, and `traceId`.
   - Poll `GET /workflows/{workflowId}/executions/{executionId}` using the same REST headers. Handle `Pending` and `Running` as non-terminal, `Completed` as success, and `Failed` as failure. The execution contains the workflow result; configure the workflow to produce JSON conforming to the shared candidate schema and verify its result field and failure payload in a sandbox run.
   - Poll rather than use callbacks for the initial upload flow. The provider also supports callbacks when a workflow includes a Webhook step, including optional `callbackUrl`, `callbackMethod`, `callbackApiKey`, and `callbackApiKeyName`; callback handling is deferred.
   - Confirm the Twilio sandbox sender and public callback URL. Outbound supplier dispatch remains disabled until verified supplier numbers and opt-ins are available.
   - Add explicit provider enablement and configuration for hosts, keys, timeouts, retry policy, public webhook URL, Twilio sender, and recipient mapping. Keep secrets in local environment only; fail closed when an integration is enabled but incomplete.
   - Preserve the default-off behavior and truthful `not_configured` status. Do not restore demo credentials or label fixture data as provider output.

2. **Define the shared extraction/import contract and upload flow**
   - Add validated leaflet product candidates covering product name, pack/variant and count, supplier, currency, observed supplier pack price, derivable supplier unit price, store retail `our_price`, availability/evidence, confidence/source, and warnings. Keep extracted observations distinct from computed planning values. Follow the existing `ProductItem` semantics: `supplier_price` is the supplier's pack price, `unit_price` and `our_price` are per sellable unit, and sales, stock, and recommended quantity use that same sellable unit.
   - Derive supplier unit price only when the pack count and observed price are explicit and unambiguous; otherwise require user completion during review. Require a verified/imported or user-entered retail `our_price` for each candidate before optimization. Do not use the optimizer's silent 1.35× retail-price fallback for file-derived plans.
   - Add a structured sales/stock importer; the current React upload UI only lists CSV/XLSX selections locally and has no parser/import path yet. Sales rows use `date, product, quantity_sold`; stock rows use `product, current_stock`, with quantities expressed in the product's sellable unit. Require ISO `YYYY-MM-DD` sales dates. XLSX files use sheets named `sales` and `stock` with the corresponding headers. Support separate files or a workbook containing both sheets.
   - Validate headers, dates, nonnegative finite quantities, and stock counts. Aggregate duplicate sales rows deterministically by normalized product and date; zero-fill missing calendar days only within the explicitly supplied history interval. Reject duplicate/conflicting stock rows. Normalize product names for joins without silently merging ambiguous names.
   - Require at least one sales dataset, one current-stock dataset, and one leaflet/PDF/image input for upload-based forecasting. Join leaflet candidates to sales and stock by normalized product name; send unmatched candidates to review for mapping/completion and do not assign them guessed demand or stock values. If a matched product has no sales history, block it for manual sales input or explicit exclusion; never use the forecaster's synthetic fallback data.
   - Use configured per-supplier lead times for deterministic `DemandForecaster.forecast_item` recommendations. If a candidate's supplier has no configured lead time, require the user to supply one during review; do not assume a default. Use the existing deterministic optimizer only after the owner reviews the extracted prices, verified retail price, resolved product matches, and computed quantities.
   - Add authenticated multipart `POST /api/plan/from-files` accepting 1–5 mixed input files, at most 10 MB each and 25 MB total. Parse CSV/XLSX locally; route images (JPG/JPEG/PNG) to AMD and PDFs to Evolus. Do not send CSV/XLSX to providers. Reject unsupported formats and enforce limits on both the application and proxy.
   - Process local imports and provider files as one all-or-nothing submission. Run provider files independently with bounded concurrency, preserving per-file source attribution and result order. Return a job ID immediately and expose owner-scoped status through `GET /api/plan/from-files/{job_id}` so slow provider work does not hold the frontend request open. Bound each Evolus execution using the configured deadline; any parse, extraction, validation failure, or timeout fails the whole job without producing a partial candidate set or plan.
   - Return normalized candidates, imported sales/stock data, and deterministic forecast recommendations to the dashboard for user review/editing. Only after review should the UI call the existing JSON `POST /api/plan`; never persist a plan directly from raw provider output. Keep deterministic optimization and owner-scoped plan persistence in the existing plan route.
   - Update `stockup_pulse/ingest/extract/leaflet_extractor.py`, add a focused CSV/XLSX importer, and update `src/services/api.ts` and `src/components/Step1Upload.tsx` to retain actual file objects, upload multipart bytes, and present editable extraction/import results before plan generation. Ensure `server.ts` streams multipart request bodies, including their original boundary/content type, to FastAPI; the existing JSON/urlencoded proxy path does not forward multipart bodies.

3. **Connect AMD inference**
   - Configure the OpenAI SDK base URL as `https://developer.amd.com.cn/radeon/api/v1`; send the team key as Bearer auth via `AMD_ROCM_API_KEY` from environment configuration only.
   - Query `GET /v1/models` at runtime and validate the configured `AMD_ROCM_MODEL` preference against the live catalog's image capability. Fail clearly when the preference is absent or unsupported; do not silently choose a different model or hard-code a stale model default. Vision-capable examples in the supplied documentation include `DeepSeek-V4.1-Flash`, `DeepSeek-V4-Flash-Vision-Exp`, `MiMo-V2.6-Flash`, and Qwen3.8 vision models.
   - Send image content as a chat-completions `image_url` data URI containing base64 image bytes. Keep PDFs routed to Evolus; AMD's separate `/v1/ocr` endpoint is outside this scope.
   - Use `/v1/chat/completions` for image extraction and explanations. `response_format: {"type":"json_object"}` is supported across chat models; strict JSON Schema is only guaranteed for MiMo-V2.6-Flash. Validate all fields locally regardless of output mode.
   - Respect the documented 10-minute maximum request window but use an app-configured timeout. Handle 429 with `Retry-After` and bounded exponential backoff/jitter; do not blindly retry 400/401/403, and retry 502/503 only within policy. Treat key usage as team-wide: documented limits include 30 RPM and 8 concurrent requests per key, 20 RPM per account, per-IP limits, and a daily spend cap. Use response rate-limit headers and `GET /v1/usage?include_recent=true` for operator diagnostics.
   - Keep catalogue adjudication deterministic. The explanation request receives the completed plan only and cannot alter numeric fields. If explanation generation fails, use the deterministic local summary and record a fallback, not a successful model call.
   - Record measured latency and provider-supplied token usage only. Add mocked tests for model discovery/capability selection, image request encoding, valid/malformed output, timeout, 429/`Retry-After`, 401/403/502/503, disabled configuration, and fallback trace accuracy.

4. **Connect Evolus document extraction**
   - Configure `EVOLUS_ENDPOINT=https://api.evolus.ai/api/v1`, `EVOLUS_APPLICATION_ID`, `EVOLUS_API_KEY`, and `EVOLUS_WORKFLOW_ID`. Keep provider enablement off by default and require all settings before making a call.
   - Implement the workflow contract in `EvolusAdapter`: multipart `POST /workflows/{workflowId}/execute` with the PDF file part and declared input/parameters; capture `executionId` from the JSON body or response header, then poll `GET /workflows/{workflowId}/executions/{executionId}` with the same authentication headers. Configure the workflow to return structured JSON matching the candidate contract.
   - Bound each execution to an environment-configurable timeout (default 600 seconds), poll using a bounded interval/backoff, and stop on `Completed`, `Failed`, or deadline expiry. Keep concurrent file runs bounded by the batch/provider limits. A provider failure, malformed result, or timeout fails the entire job; a valid empty extraction remains distinct from failure.
   - Restrict execution to the configured document-extraction workflow. Keep arbitrary workflow execution, agent/chat APIs, callbacks, and knowledge-library methods out of scope. Add mocked multipart/auth/202/poll/result/error tests and an optional sandbox contract test.

5. **Connect Twilio inbound approval messaging**
   - Implement `POST /api/whatsapp/webhook` with Twilio signature validation against a configured canonical public URL. Ensure `server.ts` forwards the signature and form parameters without changing the signed URL contract. Never trust an unverified `From` value.
   - Normalize the sender to E.164 and resolve it only to the registered owner's account. Preserve the simulator's existing `APPROVE`, `CONFIRM`, and `YES` approval aliases for consistent behavior. Approval must use the existing persisted owner-scoped approval gate and reject when no eligible plan exists.
   - Keep outbound supplier dispatch disabled until each supplier has an explicit, verified, opted-in number. Do not use placeholder/test recipients or auto-dispatch in the initial integration. When real dispatch is later enabled, send only after approval and order persistence, with idempotent delivery state separate from order creation.
   - Retain `/api/whatsapp/simulate` as an authenticated local simulator. Update the React panel to distinguish simulator, inbound webhook, queued/sent, and failed delivery states.

6. **Harden, verify, and roll out**
   - Redact tokens, full phone numbers, message bodies, and uploaded document contents from logs/traces. Enforce upload limits and provider timeouts; return sanitized API errors.
   - Expose configured/disabled provider capability status without leaking credentials.
   - Add provider-disabled startup tests, webhook sender-isolation tests, Twilio valid/invalid signature tests, approval/order idempotency tests, and outbound retry/delivery-state tests. Keep real-provider checks opt-in and sandbox-only.
   - Update `.env.example`, README setup/run instructions, and test instructions, including the accepted sales/stock CSV and XLSX templates. Enable each provider only after mocked contract tests and its sandbox smoke test pass.

## Relevant Files

- `stockup_pulse/core/config.py` and `stockup_pulse/.env.example`: safe defaults and provider/webhook configuration.
 `stockup_pulse/adapters/amd_llm.py`: Radeon Cloud Token Factory chat-completions client for image extraction/explanations; discover image-capable models dynamically and retain deterministic matching.
- `stockup_pulse/adapters/evolus.py`: Evolus PDF workflow adapter, using the [Evolus developer workflow inputs and execution API](https://evolus.ai/developers).
- `stockup_pulse/ingest/extract/leaflet_extractor.py` and a new CSV/XLSX importer: provider routing, structured file parsing, upload bytes, and shared candidate/import schema.
- `stockup_pulse/api/main.py`: authenticated multipart ingestion endpoint, deterministic forecasting/plan endpoint, and Twilio webhook.
- `stockup_pulse/core/db.py`: owner lookup and provider delivery/idempotency persistence, unless that state belongs in a dedicated orders module.
- `stockup_pulse/orders/manager.py`: reuse the existing approval guard and generated supplier messages.
- `server.ts`: preserve Twilio signature inputs and canonical public callback URL; stream multipart upload bodies through to FastAPI.
- `src/components/Step1Upload.tsx`, `src/services/api.ts`, and `src/components/WhatsAppSimulator.tsx`: preserve file bytes, provide editable extraction review, submit reviewed candidates, and reflect simulator/provider statuses.
- `stockup_pulse/tests/test_adapters.py`, `stockup_pulse/tests/test_api_security.py`, and focused extraction/Twilio tests: unit, API, and mocked-provider coverage.
- `stockup_pulse/requirements.txt`: add/pin the Twilio SDK only if its validator/client is used; the OpenAI-compatible dependency is already present.

## Verification

1. From the workspace root, run `python -m pytest -v stockup_pulse/tests/`. Mocked adapter, CSV/XLSX parsing, validation, security, approval, idempotency, and fallback tests should pass without provider credentials.
2. After React upload/status changes, run `npx tsc --noEmit` and `npm run build`.
3. With provider flags disabled, confirm upload/webhook paths fail closed or use the documented simulator, and `/health` reports configured state accurately.
4. In AMD sandbox, call `GET /v1/models`, verify selection of a vision-capable catalog entry, and upload a representative image using a base64 image data URI. Verify the extraction schema, measured trace latency/provider token usage, deterministic optimizer output, and budget ceiling. Exercise 429/`Retry-After` and confirm model output cannot change numeric plan fields.
5. In the Evolus sandbox, verify multipart file submission and the `202 Accepted` execution identifiers; poll the configured execution route through `Pending`/`Running` to `Completed` and `Failed`; verify the workflow's JSON result shape, normalization, timeout behavior, and that no plan is persisted until the owner reviews candidates.
6. In mixed-file mocked uploads, verify per-file provider routing, CSV/XLSX schema parsing, deterministic duplicate aggregation, product matching, supplier lead-time and retail-price requirements, pack-to-unit conversions, concurrency bounds, source attribution, 10 MB per-file/25 MB total/5-file limits, and all-or-nothing failure behavior. Confirm multipart passes through `server.ts`.
7. In the Twilio sandbox, test invalid-signature rejection, sender-to-owner mapping, unauthorized senders, all three approval aliases, approval-before-plan rejection, and one-time order creation. Verify outbound sending remains disabled without verified supplier numbers and opt-ins.

## Agreed Scope and Decisions

- AMD: image vision extraction and plain-language explanation; catalogue adjudication remains deterministic.
- Evolus: PDF document extraction through a dedicated workflow, using the documented execute/status polling API; synchronous execution, callbacks, general workflow orchestration, agent/chat APIs, and knowledge-library integration are excluded.
- Extraction/import routing: images to AMD, PDFs to Evolus, CSV/XLSX parsed locally. Keep all inputs normalized into validated candidate and sales/stock structures; do not send CSV/XLSX to providers.
- Uploads: process 1–5 mixed input files per request (10 MB/file, 25 MB total) with bounded provider concurrency and all-or-nothing behavior. Require sales, current stock, and at least one leaflet input for upload-based forecasting. Users review/edit matches, prices, and recommendations before plan generation.
- Structured file contract: sales columns `date, product, quantity_sold` with ISO dates; stock columns `product, current_stock` in sellable units; XLSX sheet names `sales` and `stock`. Join by normalized product name and require manual mapping/completion for unmatched leaflet candidates. Missing product sales history blocks forecasting rather than invoking synthetic fallback data.
- Price/quantity contract: supplier pack price is distinct from supplier per-unit cost; compute per-unit cost only from a clear pack count. Require verified/user-entered store retail `our_price` before optimization and do not use the 1.35× implicit fallback for file-derived plans.
- Forecast inputs: configured supplier lead time is required; missing lead time is completed by the user during review rather than guessed.
- AMD model selection: require a configured model preference and validate its image capability using the live catalog; fail clearly rather than silently switching models.
- Evolus: poll execution status with the configured per-file deadline. Configure workflow output to match the candidate schema; use only server-side credentials and never pass secrets as workflow parameters.
- Twilio: inbound sandbox webhook preserves `APPROVE`, `CONFIRM`, and `YES`. Outbound supplier dispatch remains disabled until verified supplier recipient numbers and opt-ins are recorded.
- No model may generate or change purchase quantities, prices, totals, or other order-driving numeric values. Provider output is validated input; deterministic Python remains the money authority.
- External calls and delivery remain off by default until configuration and sandbox gates pass.

## Further Considerations

1. The AMD Token Factory key and its RPM, concurrency, and daily spend limits are shared by the whole team. Coordinate key redemption, stagger calls, honor `Retry-After`, and never log the key.
2. Supplier dispatch requires verified, opted-in WhatsApp numbers; current supplier records contain names but no numbers. Use explicit per-supplier mappings and do not auto-dispatch when one is missing.
3. Twilio signature checks require the externally visible callback URL. Configure a stable public URL instead of reconstructing it from the internal proxy host.
4. Define an upload retention policy. Default recommendation: process in memory or temporary storage and delete after extraction unless audit requirements mandate retention.