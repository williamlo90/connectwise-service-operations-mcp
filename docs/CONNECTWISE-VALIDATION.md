# ConnectWise integration and validation

The current implementation targets a documented PSA reference subset through a stateful HTTP simulator. It has not been tested against a live ConnectWise tenant. The [subset contract](../contracts/PSA-SUBSET.md) and [reference manifest](../contracts/reference-manifest.json) record the routes, fields, pinned community reference and assumptions.

## Access requirements

Connected validation requires authorized PSA documentation, a permitted test tenant and an identified owner. Documentation access, a client identifier and tenant credentials are separate prerequisites. The project currently has no test tenant; independent-developer eligibility and access arrangements remain unconfirmed.

The registration flow directed the project owner to contact the API team about access without a corporate email address. That correspondence and registration drafts are local administrative material. Once access is available, record only non-secret details in the integration evidence: product, tenant/API version, region, approved scopes, permitted test data and owner approval.

## Acceptance sequence

1. Confirm the PSA product/version and official authentication requirements. Configure a dedicated test identity and company/board allowlists.
2. Reconcile every implemented route and field with the official tenant contract, including private-note flags, time billing/mappings, timestamps, pagination, rate limits and read-back normalization.
3. Implement an explicit connected configuration with trusted origins and validated secrets. The current application rejects connected mode.
4. Run a read-only canary that proves allowed access and denial outside scope.
5. Prepare an internal note with synthetic data, obtain a separate authorized approval, execute once and verify the returned record and visibility.
6. Repeat for a time entry using documented minutes and an explicit start time. Verify billing/work/member mappings and notification behavior.
7. Exercise stale approval, permission loss, rate limits, uncertain outcomes and reconciliation within the tenant owner's permitted test plan.
8. Re-run affected regression and quality checks, then record the adapter revision, sanitized results and deployment configuration.

Vendor omissions or normalization require explicit comparison rules; a successful HTTP response alone is insufficient. Keep credentials, customer records and private vendor documentation out of the repository.

Azure deployment can be validated first using the simulator. The two milestones prove different things: cloud execution and real vendor compatibility.
