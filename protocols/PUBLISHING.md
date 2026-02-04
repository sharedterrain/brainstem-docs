# Publishing Protocol (Public Mirror)

## Definition: public-safe
A document is public-safe only if it contains:
- sanitized markdown
- placeholders instead of sensitive values
- no inbound webhook URLs
- no credentials or tokens
- no personal identifiers

## Mirror workflow (manual for now)
1) Copy content from Notion
2) Remove anything sensitive
3) Replace sensitive values with placeholders `<<LIKE_THIS>>`
4) Run the security pre-commit checklist in `protocols/SECURITY.md`
5) Commit with a descriptive message

## Commit message format
- `docs: ...` for documentation
- `chore: ...` for structure/housekeeping
- `spec: ...` for contract/spec changes
- `security: ...` for redaction or security fixes

## Rollback if secrets leak
1) Immediately delete the secret at the source (rotate/revoke)
2) Remove the secret from the repo (replace with placeholder)
3) Commit the fix
4) (Optional) Rewrite history if required by the provider policy
