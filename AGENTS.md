# JITIS Wiki Agent Guide

## Scope

- This is the reviewed JITIS Frappe Wiki fork used for customer documentation.
- Preserve upstream compatibility and keep the JITIS diff small. Do not duplicate portal authorization logic inside ad-hoc API methods.
- Customer documentation must remain scoped to the validated portal identity and customer grant; missing or ambiguous scope fails closed.

## Verification

Run both disposable Frappe gates:

```text
docker compose -f ci/compose.yaml run --build --rm quality
docker compose -f ci/compose.yaml run --build --rm integration
docker compose -f ci/compose.yaml down --volumes --remove-orphans
```

Require negative cross-customer tests for document, attachment, search, and navigation changes. Treat any unauthorized document or attachment disclosure as P0.

## Code Review Rules

- Treat any unauthorized document, attachment, search result, or navigation
  disclosure across customers as P0.
- Treat a change that duplicates or bypasses the shared portal authorization
  boundary as P1; require a negative cross-customer regression test.
- Keep the private fork diff minimal and compatible with the pinned upstream
  release; flag unrelated vendoring or mutable production references.
