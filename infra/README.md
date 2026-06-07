# Infrastructure (Terraform / AWS)

Stubbed. **No AWS services have been chosen yet.** Per CLAUDE.md, the cloud
architecture must be *proposed and confirmed* before it is built (Phase 8) — do
not assume a design.

Likely candidates to confirm later:
- Compute for the FastAPI API
- Object storage for the cached embedding index (vectors.npy / records.pkl)
- A CDN / static host for the React frontend

## Layout

```
infra/
├── modules/        Reusable Terraform modules (empty)
└── envs/
    ├── dev/        Dev environment root module (stub)
    └── prod/       Prod environment root module (stub)
```

Environments are kept separate so dev and prod never share state. Modules are
shared building blocks the env roots compose. Nothing here is runnable yet —
`terraform init` is intentionally not wired up.
