# Phase 3 assistant setup and use

The assistant selects evidence using a real model, validates the selected source IDs, and renders an extractive summary or technician-based draft. It does not generate unrestricted factual prose. Source statements are attributed, not independently proven. Approval, duration arithmetic and downstream writes remain in the Phase 2 domain service.

## Setup

```sh
python scripts/setup_local.py
docker compose --profile tools build
docker compose -f compose.yaml -f compose.ai.yaml up -d --wait api ollama
docker compose run --rm seed
docker compose -f compose.yaml -f compose.ai.yaml exec ollama ollama pull qwen3:0.6b
```

Initial provisioning downloads the runtime and model. Runtime image and model manifest/layers are pinned in [local-model.json](../contracts/local-model.json). The provider checks the installed model digest before inference. A moved upstream tag causes a pin mismatch rather than silently substituting an artifact. CPU-only inference is limited to two CPUs, 1.5 GiB, one request and one loaded model. Context is 4096 tokens, output at most 512 tokens, and keep_alive=0 unloads the model after use. Other project containers are not managed by these commands.

API/backend services have 384 MiB / one CPU limits and the database 256 MiB / one CPU. Run tests serially; avoid simultaneous load tests on this workstation. Limits contain resource usage but cannot guarantee no contention with other applications.

## Interactive AI workflow

```sh
docker compose run --rm client --ai summary A-100
docker compose run --rm client --ai note A-100
docker compose run --rm client --ai time A-100
```

Note/time commands prompt for technician observations. Time also requires documented minutes, evidence and a timezone-aware start. The client prints a request ID before dispatch; the result includes status, source facts, missing information, versions, model identity, latency and usage. No proposal is approved or externally written during generation.

```sh
docker compose run --rm client --ai run RUN_ID
docker compose run --rm client --ai cancel RUN_ID
docker compose run --rm client --ai prepare RUN_ID
```

Only a completed, unexpired, source-current note/time draft can become a proposal. Materialization is atomic and replay-safe. Then follow [the separate approval workflow](PHASE-2-WORKFLOW.md). Summary and verify skills cannot create proposals. Worker reuse goes through `/skills/{skill}/runs` with the same RunInput contract and implementation; `worker-a` has only a scoped summary grant.

Cancellation is logical: late output is discarded, but upstream inference/billing may continue until the HTTP timeout. No replacement inference starts while that call is active. Interrupted runs retain their IDs and are never automatically regenerated; the next new run clears abandoned slots older than three minutes. Reusing a request ID with changed inputs returns conflict.

## Hosted providers

The ignored root `.env` has empty `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `XAI_API_KEY` entries. Add keys there, not in chat or command arguments. Example model IDs are configurable and availability must be verified against the account. Credentials are passed only to the API container and official endpoints; prompts do not contain them.

Set `AI_HOSTED_ENABLED=true` when ready, then recreate the API container to load the changed environment:

```sh
docker compose -f compose.yaml -f compose.ai.yaml up -d --wait api
docker compose run --rm -e AI_PROVIDER=openai client --ai summary A-100
```

Use `anthropic` or `xai` for the other adapters. `local_only=true` rejects hosted selection, and local failures never fall back to a hosted provider. Each run makes one generation request, with no automatic retries. Provider refusal, truncation, rate limit, missing key, unreachable runtime and invalid selection produce explicit non-success outcomes.

Token usage is recorded only when reported by the provider. `cost_usd=null` means no verified cost calculation is available; it is not zero cost. This release does not estimate hosted billing or local electricity/hardware costs.

## Reproducible checks

```sh
python scripts/test_local.py
python scripts/ai_canary.py --provider ollama
python scripts/ai_canary.py --provider ollama --workflow
python scripts/ai_canary.py --provider openai
```

The regression runner uses an isolated temporary database and a controlled model boundary for assistant tests. It never sends paid API requests. The canary script makes one real inference request. The local `--workflow` variant additionally prepares, approves using a separate synthetic identity, and verifies one simulator note. It is a demo/test harness, not automated human approval for real work. Hosted canaries are summary-only, one request per invocation. Evidence records provider status separately from regression results.

## Upgrade, recovery and retention

Run records live in PostgreSQL and include attributed source text/drafts; logs omit request bodies and credentials. Deleting the project's disposable test stack removes its data; the persistent local database retains runs until explicitly managed. Production retention/export controls remain release-hardening work.

To stop local inference and release its memory: `docker compose -f compose.yaml -f compose.ai.yaml stop ollama`. Restart it with the setup command. A missing runtime produces a failed run with no external write. To remove only the downloaded model, run `docker compose -f compose.yaml -f compose.ai.yaml exec ollama ollama rm qwen3:0.6b` when it is no longer needed. This does not erase application data.

Upgrade model/runtime by changing the pinned manifest and image deliberately, verifying license and digest, and rerunning contract/regression/local canaries. Preserve the previous manifest and model before a rollback. Application migrations are forward-only; do not run an older checkpoint against a newer persistent database. Use isolated checkpoint test stacks or restore a matching backup.

## Official references

Adapters use [OpenAI Responses structured output](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic JSON output](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [xAI structured output](https://docs.x.ai/developers/model-capabilities/text/structured-outputs), and [Ollama chat](https://docs.ollama.com/api/chat). The local model is [Qwen3 0.6B](https://huggingface.co/Qwen/Qwen3-0.6B), Apache-2.0. These sources establish API/model documentation, not proof that a configured account has passed a canary.
