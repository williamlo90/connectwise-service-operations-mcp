# PSA reference subset 1.0.0

This is a local simulator contract, not an official ConnectWise specification. Source URLs, exact revision, SHA-256 digests, access date and license are recorded in [reference-manifest.json](reference-manifest.json). The sole structural reference is [k-grube/connectwise-rest at b62dad9](https://github.com/k-grube/connectwise-rest/tree/b62dad91be3a5a4a6578278c832b76a4581928b3), an MIT-licensed community SDK by Kevin Grube. No SDK implementation is bundled or installed. Local downloaded reference material is ignored by Git.

The source README claims Manage 2026.11, while older defaults/comments retain 2021.1. Neither label is accepted as a verified tenant API version. Connected version negotiation, official documentation and conformance remain Phase 8A requirements.

## Wire subset

Base path: `/v4_6_release/apis/3.0`. Basic authentication uses `company+publicKey:privateKey`, with `clientId` header. The simulator accepts only explicit synthetic credentials from environment. The adapter permits only the internal simulator host; no real vendor can be addressed in this release.

| Method / path | Fields or parameters used | Reference |
| --- | --- | --- |
| GET `/service/tickets` | page, pageSize, orderBy=`id asc`; id, summary, company, board, status, owner, `_info.lastUpdated` | ServiceAPI `getServiceTickets`, ManageTypes Ticket/CommonParameters |
| GET `/service/tickets/{id}` | Same ticket fields | ServiceAPI `getServiceTicketsById` |
| GET/POST `/service/tickets/{id}/notes` | ticketId, text, internalAnalysisFlag, detailDescriptionFlag, resolutionFlag, internalFlag, externalFlag, processNotifications | ServiceAPI note methods; ManageTypes ServiceNote |
| GET `/service/tickets/{id}/notes/{noteId}` | Note plus external id | ServiceAPI `getServiceTicketsByParentIdNotesById` |
| GET `/company/companies/{id}` | id, identifier, name | ManageTypes Company; company route is a local assumption pending official confirmation |
| GET `/service/boards/{id}` and `/statuses` | id, name, inactiveFlag; board-specific status ids | ServiceAPI board methods |
| GET `/system/members/{id}` | id, identifier, name | ManageTypes Member; system route is a local assumption pending official confirmation |
| GET/POST `/time/entries`; GET `/time/entries/{id}` | chargeToId/type, member, workType/Role, timeStart/End, actualHours, billableOption, notes, internal/detail/resolution flags, email flags | TimeAPI time-entry methods; ManageTypes TimeEntry |

Time search accepts only `chargeToId=N AND chargeToType="ServiceTicket"`. It is server-generated from a scoped numeric ticket ID. Pagination starts at 1; local maximum page size is 100. Notes/time reads stop after 100 pages and fail if output remains incomplete. Local search `/tickets` searches the seeded scope registry, while context and all write preconditions read the HTTP source. The sync source cache has a separate scoped endpoint and never authorizes a write.

## Explicit local policies and assumptions

- Local ticket references `A-100` and `B-100` map to remote numeric ticket 100 within separate tenant connections. Company/board/member IDs are server-owned configuration, not caller inputs. General discovery/import of new ticket mappings is outside this subset.
- Only internal notes can be prepared. Internal analysis/internal flags are true; detail description, resolution, external and notification flags are false. Existing public notes remain visibly labeled in context.
- Time entries require integer documented minutes, a nonblank evidence description and timezone-aware start. Convert to UTC; end = start + minutes; actualHours = minutes / 60. Use configured member/work type/work role, `ServiceTicket`, `DoNotBill`, internal analysis only and no email flags. This is a local policy, not a statement about required PSA billing practice.
- Required fields, accepted flags, timestamp formatting, visibility semantics and whether request-only fields appear on read-back need official verification. Local read-back compares every submitted field exactly. A vendor that omits or normalizes a field will require an explicitly documented normalization rule before connected writes are enabled.
- Proposals expire after 30 minutes. A different active approver must approve the exact payload hash. Ticket and mapping snapshots must still match at approval and execution. Status/assignment outputs are recommendations only.
- There is no native downstream idempotency key or compare-and-swap in this simulator. The app persists a single dispatch per proposal before POST. POST is never retried automatically. The visible `[cw-op:UUID]` marker is part of the approved payload and enables read-only reconciliation after timeout. Exactly one matching record with all expected fields is required for success.
- A crash before POST may leave `dispatched` without a side effect. Absence during reconciliation remains `unknown`; it does not trigger another POST. Unknown/review cases require investigation before a new proposal. This favors avoiding duplicates over automatic completion.
- GET retries at most three times on transport errors/429/502/503/504 with short bounded simulator backoff. Real Retry-After handling and tenant rate policies remain connected work. POST acknowledgment alone never means verified.
- A source can change between the final GET and POST because there is no atomic vendor precondition. Local freshness checks reduce this window but cannot eliminate it. No distributed exactly-once claim is made.

## Synchronization

`POST /workflow/sync` is administrator-only and processes one ordered page (two records in the fixture). Cache rows and next-page checkpoint commit together. A failed page preserves the checkpoint. A completed scan increments the generation and records completion time. Repeated scans refresh changes; this is a full scan, not a vendor delta cursor.

`GET /workflow/sync/status` marks a scan stale after five minutes or before first completion. Operators can read `/workflow/tickets/{id}/cached` only for scoped records; each response includes source hash, fetched time and stale flag. Records absent from a later completed scan eventually become stale and are retained; there is no automatic deletion. Page-number scans do not provide a snapshot under concurrent source changes. Context/approval/execute therefore always re-read the source.

## Failure injection

The isolated acceptance suite inserts bounded `simulator_faults` rows through its database fixture, not a public fault-control endpoint. Supported modes: 429, unauthorized credentials, 503, timeout after committed write, and mismatching read-back. Tables survive process restarts in the local PostgreSQL volume. The simulator does not implement all PSA validation, notification delivery, billing, scheduling, ticket updates or permission semantics.
