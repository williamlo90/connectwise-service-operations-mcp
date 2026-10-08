# Local critical-control coverage

The Phase 6 regression run re-executes the production API, PostgreSQL, HTTP simulator, MCP and scheduler paths covered below. Model-boundary failures use controlled provider responses; model quality uses separate real-provider cases. All records are synthetic. Connected tenant acceptance remains Phase 8A.

| Required project failure | Regression evidence |
| --- | --- |
| Similar company names across tenants | `test_scope_and_direct_id`, `test_transport_auth_and_tenant_partition`, `test_schedule_two_tenants_checkpoint_and_no_side_effects`, MCP scope cases |
| Internal note incorrectly made public | `test_note_exact_approved_payload_and_replay`, `test_duration_and_field_validation`, MCP malformed visibility rejection |
| Status unavailable on the service board | `test_recommendations_validate_board_and_member_without_write` |
| API limit, pagination and sync resume | `test_sync_checkpoint_retry_staleness_and_refresh`, `test_transient_rate_limit_backoff_then_recovery`, `test_partial_scan_failure_preserves_committed_page` |
| Time entry without duration evidence | `test_duration_and_field_validation`, `test_time_never_invents_duration`, real-provider pre-inference rejection cases |
| Timeout after a note was created | `test_timeout_unknown_recovery_without_duplicate`, `test_ambiguous_marker_requires_review`, MCP interrupted-response recovery |
| External update before approval/execution | `test_stale_ticket_and_mapping_invalidate_approval`, `test_stale_context_blocks_materialization` |

Additional cases cover expired/revoked identity, separate-user approval, output/schema rejection, no local-to-hosted fallback, cancellation, duplicate concurrent writes, wrong downstream read-back, worker process death, permanent credentials failure and administrator-only job recovery. Evaluator mutation checks reject fabricated facts, wrong references, incomplete uncertainty disclosure, public draft visibility and duplicate read-back effects.

The application enforces resolution uncertainty after model selection. The regression `test_resolution_uncertainty_is_enforced_when_model_omits_it` checks that a structurally valid model response cannot omit this domain limitation. The selected evidence is still attributed source text, not independently proven incident resolution.

The [Phase 6 regression artifact](evidence/phase-6-regression.json) lists exact case names and source hashes. Success means zero observed critical violations on this finite suite. Forced OOM, backup restoration, peak/soak performance, delivered alerts and release rollback are Phase 7 work; this report does not close those gates. An installation review and connected sandbox validation likewise remain their respective later phases.
