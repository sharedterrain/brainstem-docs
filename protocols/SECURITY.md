# Security Policy (Public Docs)

## Hard rules (never publish)
- API keys, tokens, credentials of any kind
- Inbound webhook URLs (anything callable from the public internet)
- Signing secrets
- Personal identifiers
- Database connection strings / private endpoints
- Anything enabling unauthenticated triggering or access

## Placeholder rule
- Replace every sensitive value with `<<LIKE_THIS>>`
- Placeholders must be ALL CAPS with underscores
- Example: `<<SLACK_BOT_TOKEN>>`, `<<MAKE_WEBHOOK_URL>>`

## Placeholder registry
| Placeholder | Meaning | Where it appears | Owner |
|---|---|---|---|
| <<MAKE_WEBHOOK_URL>> | Inbound Make webhook URL | (never in public docs) | <<HUMAN_NAME>> |
| <<SLACK_BOT_TOKEN>> | Slack bot token | (never in public docs) | <<HUMAN_NAME>> |
| <<AIRTABLE_PAT>> | Airtable personal access token | (never in public docs) | <<HUMAN_NAME>> |
| <<CLAUDE_API_KEY>> | Anthropic key | (never in public docs) | <<HUMAN_NAME>> |

## Pre-commit checklist (search these exact strings)
Search the repo for each string below before every commit:
- `hook.make.com`
- `https://hook.`
- `Authorization: Bearer`
- `xoxb-`
- `xoxp-`
- `sk-ant-`
- `pat`
- `BEGIN PRIVATE KEY`
- `secret_`
- `api.airtable.com/v0/app`
- `console.anthropic.com`
- `perplexity.ai/settings/api`

If any match is found:
1) Replace with `<<PLACEHOLDER>>`
2) Add the placeholder to the registry table above
3) Re-search until clean

## Public-safe examples rule
- If a doc needs an example URL/token, it must be fake and clearly marked:
  - `<<EXAMPLE_ONLY_NOT_REAL>>`
