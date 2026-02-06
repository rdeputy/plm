# PLM Checkpoint — 2026-02-06

## Last Action
Applied critical security fixes (path traversal, auth bypass, IP spoofing). Uncommitted.

## Current State
- Security audit completed, CRITICAL/HIGH issues fixed
- GitHub repo: https://github.com/rdeputy/plm
- 3 commits pushed, security fixes pending commit

## Recent Commits
```
d823c8c Add structured logging, rate limiting, and production PostgreSQL
2a32bc1 Add GitHub repository configuration
01713ea Add entity forms, Supabase auth, CAD upload, and Pydantic v2 migration
bb6a874 Add detail pages and CRUD forms for all PLM entities
```

## Security Fixes Applied (uncommitted)
- **Path traversal** — `security_utils.py` with filename sanitization
- **Auth bypass** — Require explicit `PLM_ALLOW_DEV_MODE=true`
- **IP spoofing** — Trusted proxy validation in rate limiter
- **File size limits** — 50MB docs, 200MB CAD models
- **user_id auth** — All endpoints now use session auth (workflows, notifications, documents)

## Next Steps When Resuming
1. Commit security fixes
2. Set up frontend testing (Vitest + React Testing Library)
3. Create Kubernetes/Helm deployment manifests
4. Add CSRF protection and CSP headers

## Environment Notes
- PostgreSQL production stack: `docker-compose -f docker-compose.prod.yml up`
- PgAdmin available: `docker-compose -f docker-compose.prod.yml --profile tools up`
- Logging: Set `PLM_LOG_FORMAT=json` for structured logs
- Rate limiting: 60 req/min default, configurable via `PLM_RATE_LIMIT_RPM`
- **Dev mode**: Set `PLM_ALLOW_DEV_MODE=true` to disable auth (NEVER in production)

## User Preferences
- PLM is industry-agnostic (not just AEC/construction)
- Supports DevOps, PD&E, AEC, regulated and unregulated industries
