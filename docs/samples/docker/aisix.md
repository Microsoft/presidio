# Protect LLM requests with Presidio and AISIX AI Gateway

[AISIX](https://github.com/api7/aisix) can call a self-hosted Presidio
Analyzer and Anonymizer as an input guardrail before forwarding a request to
an LLM provider. This sample configures two outcomes:

- email addresses are replaced with an entity placeholder;
- US Social Security numbers are blocked before the provider is called.

```text
Application --> AISIX --> LLM provider
                  |
                  +--> Presidio Analyzer --> Presidio Anonymizer
```

## Prerequisites

- Docker
- an OpenAI API key, or an OpenAI-compatible endpoint and matching AISIX
  provider configuration
- `curl`

The commands below use AISIX 1.2.0 and Presidio 2.2.364.

## Start Presidio

Create a private Docker network and run both Presidio services:

```bash
docker network create aisix-presidio

docker run -d --name presidio-analyzer --network aisix-presidio \
  -p 127.0.0.1:5002:3000 \
  ghcr.io/data-privacy-stack/presidio-analyzer:2.2.364

docker run -d --name presidio-anonymizer --network aisix-presidio \
  -p 127.0.0.1:5001:3000 \
  ghcr.io/data-privacy-stack/presidio-anonymizer:2.2.364
```

These services do not authenticate callers. Keep them on a private network in
production instead of publishing their ports.

Wait for both services to report healthy before continuing:

```bash
until curl -fsS http://127.0.0.1:5002/health >/dev/null; do sleep 5; done
until curl -fsS http://127.0.0.1:5001/health >/dev/null; do sleep 2; done
```

Confirm that the Analyzer detects an email address:

```bash
curl -sS -X POST http://127.0.0.1:5002/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"Contact alice@example.com","language":"en"}'
```

The response includes an `EMAIL_ADDRESS` result with its character offsets
and confidence score.

## Configure AISIX

Create `config.yaml`:

```yaml
resources_file: /etc/aisix/resources.yaml

proxy:
  addr: "0.0.0.0:3000"

admin:
  enabled: false
```

Create `resources.yaml`:

```yaml
_format_version: "1"

provider_keys:
  - display_name: openai-main
    provider: openai
    api_key: ${OPENAI_API_KEY}

models:
  - display_name: presidio-demo
    provider: openai
    model_name: gpt-4o-mini
    provider_key: openai-main

api_keys:
  - display_name: local-demo
    key_env: CALLER_API_KEY
    allowed_models: ["presidio-demo"]

guardrails:
  - name: presidio-pii-policy
    enabled: true
    hook_point: input
    enforcement_mode: block
    fail_open: false
    kind: presidio
    analyzer_url: http://presidio-analyzer:3000
    anonymizer_url: http://presidio-anonymizer:3000
    entities:
      - type: EMAIL_ADDRESS
        action: mask
      - type: US_SSN
        action: block
    default_action: mask
    operator: replace
    language: en

guardrail_attachments:
  - guardrail_id: presidio-pii-policy
    scope_type: env
    priority: 100
```

Export credentials and start the gateway on the same Docker network:

```bash
export OPENAI_API_KEY="YOUR_PROVIDER_KEY"
export CALLER_API_KEY="sk-local-presidio-demo"

docker run -d --name aisix-presidio-gateway \
  --platform linux/amd64 \
  --network aisix-presidio \
  -v "$(pwd)/config.yaml:/etc/aisix/config.yaml:ro" \
  -v "$(pwd)/resources.yaml:/etc/aisix/resources.yaml:ro" \
  -e OPENAI_API_KEY -e CALLER_API_KEY \
  -p 127.0.0.1:3000:3000 \
  ghcr.io/api7/aisix:1.2.0
```

The guardrail must have an attachment. A configured guardrail with no matching
attachment does not inspect traffic.

## Verify masking and blocking

Send a request containing an email address:

```bash
curl -sS -X POST http://127.0.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer ${CALLER_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "presidio-demo",
    "messages": [
      {"role": "user", "content": "Contact alice@example.com about the order"}
    ]
  }'
```

AISIX asks the Analyzer to locate the email and the Anonymizer to replace it.
The provider receives `Contact <EMAIL_ADDRESS> about the order`; the model's
response remains provider-dependent.

Now send a value configured with the `block` action:

```bash
curl -sSi -X POST http://127.0.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer ${CALLER_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "presidio-demo",
    "messages": [
      {"role": "user", "content": "My SSN is 987-65-4321"}
    ]
  }'
```

The request returns `422 Unprocessable Entity` with a `content_filter` error,
and AISIX does not call the model provider.

This example is fail-closed. If the Analyzer is unavailable, AISIX returns a
`422` `guardrail_unavailable` error instead of forwarding uninspected content.
Set `fail_open: true` only when availability is more important than preventing
unscreened text from reaching the provider.

## Clean up

```bash
docker rm -f aisix-presidio-gateway presidio-analyzer presidio-anonymizer
docker network rm aisix-presidio
```

For entity selection, anonymization operators, output guardrails, streaming
behavior, and deployment guidance, see the
[AISIX Presidio guardrail documentation](https://docs.api7.ai/ai-gateway/traffic-controls/guardrails/presidio).
