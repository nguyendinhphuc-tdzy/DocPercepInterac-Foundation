# Frontend Contract Projection

This directory contains the deterministic TypeScript projection of the
Foundation Contract v0.1 OpenAPI specification.

## Architecture

```
docs/contracts/foundation.openapi.yaml   (Frozen — authoritative source)
        │
        ▼  openapi-typescript 7.13.0
frontend/src/contracts/generated/foundation.ts   (AUTO-GENERATED — DO NOT EDIT)
        │
        ▼  curated type aliases & derived status projections
frontend/src/contracts/foundation.ts             (Thin type-only facade)
        │
        ▼  re-exports public type surface
frontend/src/contracts/index.ts                  (Public export boundary)
```

### Roles and Boundaries

- **`generated/foundation.ts`**: Machine-owned transport projection generated
  directly from the Frozen OpenAPI contract. Must never be manually edited.
- **`foundation.ts`**: Curated, type-only frontend facade. Re-exports backend
  schemas as convenient type aliases and derives inline status/outcome enums
  from owning generated records.
- **`index.ts`**: Public export boundary for application components and stores.
  Consumers import contract types via this barrel.
- **Presentation/Application DTOs**: UI-specific view models, selection geometry,
  interaction state, and extraction plans remain strictly separate and live in
  their respective application modules outside the contract projection.

### Source of Truth

The Frozen Foundation Contract (`docs/contracts/foundation.openapi.yaml`) is
the single authoritative source for all shared types between backend and
frontend.

Frontend code **must not** define its own copies of contract types. All
contract-derived types must originate from the generated projection.

### Generated File Rules

`generated/foundation.ts` is produced by `openapi-typescript@7.13.0` via the
generator script. This file:

- **MUST NOT** be edited manually
- **MUST** be regenerated whenever the OpenAPI spec changes
- **MUST** pass drift validation before merge

## Commands

| Command | Purpose |
|---|---|
| `npm run contracts:generate` | Regenerate `generated/foundation.ts` from the OpenAPI spec |
| `npm run contracts:check` | Validate the generated file matches the spec (side-effect free) |

## CI Enforcement

The `.github/workflows/frontend-contracts.yml` workflow runs
`npm run contracts:check` and `npm test` on every push and pull request that
touches contract-related paths. A pull request will be blocked if the projection
has drifted.

## Tooling

| File | Purpose |
|---|---|
| `frontend/tools/generate-contracts.mjs` | Generator: OpenAPI → TypeScript via Node API |
| `frontend/tools/check-contracts.mjs` | Drift checker: in-memory regeneration vs committed file |

## Rules

1. **Never edit `generated/foundation.ts` by hand.** Run `contracts:generate`.
2. **Never modify Frozen Contract semantics** to accommodate frontend needs.
3. **If the contract changes**, regenerate and commit the updated projection in
   the same PR.
4. **Drift check is integrated into `npm test`**, so `npm test` will fail if
   the projection is stale.
5. **No authoritative transition authority in frontend.** The frontend never
   defines legal status transition maps or authorization policy.
