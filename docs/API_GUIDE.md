# API Guide - Neuro-Symbolic Guardian

This guide covers the complete REST API for the Neuro-Symbolic Guardian, including verification, LLM integration, and multi-provider support.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API is open. For production deployments, add authentication middleware (JWT, API keys, etc.).

## API Endpoints

### Health & Status

#### `GET /healthz`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "neuro-symbolic-guardian"
}
```

#### `GET /readyz`

Readiness check with detailed status.

**Response:**
```json
{
  "status": "ready",
  "policy_version": "2.0.0",
  "llm_enabled": true,
  "active_provider": "openai",
  "rules_count": 15
}
```

#### `GET /api/status`

Comprehensive API status.

**Response:**
```json
{
  "status": "operational",
  "version": "2.0.0",
  "components": {
    "guardian_engine": "ok",
    "policy_system": "ok",
    "llm_integration": "ok",
    "metrics": "ok"
  },
  "policy": {
    "version": "2.0.0",
    "rules_count": 15,
    "enabled_rules": 15
  },
  "llm": {
    "provider": "openai",
    "extraction_enabled": true
  }
}
```

### Verification Endpoints

#### `POST /api/verify`

Verify if an action complies with policies.

**Request:**
```json
{
  "text": "consume 3 apples from inventory of 2",
  "facts": {
    "inventory": 2
  }
}
```

**Response:**
```json
{
  "decision": "deny",
  "reason_codes": ["inventory.negative_result"],
  "human_message": "Physical impossibility: cannot consume more items than exist",
  "policy_version": "2.0.0",
  "request_id": "uuid-here",
  "rule_hits": [
    {
      "rule_id": "inventory.non_negative",
      "ok": false,
      "code": "inventory.negative_result",
      "message": "Would result in negative inventory",
      "details": {}
    }
  ],
  "telemetry": {
    "latency_ms": 15,
    "stages_ms": {
      "input_scan": 1,
      "rules": 14
    }
  }
}
```

#### `POST /api/extract_intent`

Extract structured intent from natural language.

**Request:**
```json
{
  "text": "Delete all user records",
  "facts": {}
}
```

**Response:**
```json
{
  "text": "Delete all user records",
  "action": {
    "op": "delete",
    "args": {
      "target": "user_records",
      "scope": "all"
    },
    "tool": null,
    "risk_class": "critical"
  },
  "facts": {
    "data": {}
  },
  "assumptions": []
}
```

### LLM Settings Endpoints

#### `GET /api/llm/settings`

Get current LLM settings.

**Response:**
```json
{
  "provider": "openai",
  "providers": ["openai", "claude", "watsonx", "ollama"],
  "openai": {
    "api_key": "sk-***",
    "model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1",
    "temperature": 0.3,
    "max_tokens": 1024
  },
  "claude": {...},
  "watsonx": {...},
  "ollama": {...},
  "enable_llm_extraction": true,
  "fallback_to_regex": true
}
```

#### `POST /api/llm/provider`

Set the active LLM provider.

**Request:**
```json
{
  "provider": "claude"
}
```

**Response:** Same as GET /api/llm/settings

#### `PUT /api/llm/settings`

Update LLM settings.

**Request:**
```json
{
  "provider": "openai",
  "openai": {
    "api_key": "sk-newkey",
    "model": "gpt-4o",
    "temperature": 0.5
  },
  "enable_llm_extraction": true
}
```

**Response:** Same as GET /api/llm/settings

### Model Catalog Endpoints

#### `GET /api/llm/models`

List available models for the active provider.

**Query Parameters:**
- `provider` (optional): Override active provider

**Response:**
```json
{
  "provider": "openai",
  "models": [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo"
  ],
  "error": null
}
```

#### `GET /api/llm/models/{provider}`

List available models for a specific provider.

**Example:** `GET /api/llm/models/claude`

**Response:**
```json
{
  "provider": "claude",
  "models": [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229"
  ],
  "error": null
}
```

#### `GET /api/llm/model-info/{provider}/{model_id}`

Get detailed information about a specific model.

**Example:** `GET /api/llm/model-info/openai/gpt-4o-mini`

**Response:**
```json
{
  "provider": "openai",
  "model_id": "gpt-4o-mini",
  "available": true,
  "api_endpoint": "https://api.openai.com/v1"
}
```

### Chat Completion Endpoint

#### `POST /api/llm/chat`

Send chat completion request to the active LLM provider.

**Request:**
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "temperature": 0.7,
  "max_tokens": 100
}
```

**Response:**
```json
{
  "content": "The capital of France is Paris.",
  "provider": "openai",
  "model": "gpt-4o-mini"
}
```

### Policy Endpoints

#### `GET /api/policy`

Get current policy configuration.

**Response:**
```json
{
  "version": "2.0.0",
  "rules": [
    {
      "id": "inventory.non_negative",
      "enabled": true,
      "description": "Inventory must be non-negative",
      "params": {
        "timeout_ms": 50
      },
      "risk_class": "high"
    }
  ],
  "metadata": {
    "description": "Production policy",
    "owner": "Security Team"
  }
}
```

#### `GET /api/policy/rules`

List all available rules.

**Response:**
```json
{
  "total": 15,
  "rules": [
    {
      "id": "inventory.non_negative",
      "description": "Inventory quantities must be non-negative"
    },
    {
      "id": "security.no_secrets",
      "description": "Block API keys and secrets"
    }
  ]
}
```

### Metrics Endpoint

#### `GET /metrics`

Prometheus metrics endpoint.

**Response:**
```
# HELP aegis_requests_total Total Aegis requests
# TYPE aegis_requests_total counter
aegis_requests_total{decision="allow",endpoint="/api/verify"} 42
aegis_requests_total{decision="deny",endpoint="/api/verify"} 8

# HELP aegis_latency_ms Aegis request latency (ms)
# TYPE aegis_latency_ms histogram
aegis_latency_ms_bucket{endpoint="/api/verify",le="10.0"} 30
aegis_latency_ms_bucket{endpoint="/api/verify",le="50.0"} 48
aegis_latency_ms_bucket{endpoint="/api/verify",le="100.0"} 50
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error description here"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `500` - Internal Server Error

## Environment Variables

Configure the API using these environment variables:

### Guardian Configuration
- `AEGIS_ENV` - Environment (dev/staging/production)
- `AEGIS_POLICY_PATH` - Path to policy YAML
- `AEGIS_FAIL_MODE` - Fail mode (open/closed)

### LLM Configuration
- `LLM_PROVIDER` or `AEGIS_LLM_PROVIDER` - Active provider
- `AEGIS_ENABLE_LLM` - Enable LLM extraction (true/false)

### OpenAI
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_MODEL` - Model name
- `OPENAI_BASE_URL` - Base URL (optional)

### Claude
- `ANTHROPIC_API_KEY` - Anthropic API key
- `CLAUDE_MODEL` - Model name
- `ANTHROPIC_BASE_URL` - Base URL (optional)

### Watsonx
- `WATSONX_API_KEY` - Watsonx API key
- `WATSONX_PROJECT_ID` - Project ID
- `WATSONX_MODEL` - Model ID
- `WATSONX_BASE_URL` - Base URL

### Ollama
- `OLLAMA_BASE_URL` - Ollama server URL
- `OLLAMA_MODEL` - Model name

### API Configuration
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated)

## Example Usage

### Python

```python
import requests

# Verify an action
response = requests.post(
    "http://localhost:8000/api/verify",
    json={
        "text": "consume 2 apples",
        "facts": {"inventory": 5}
    }
)
print(response.json())

# List available models
response = requests.get("http://localhost:8000/api/llm/models")
print(response.json())

# Chat completion
response = requests.post(
    "http://localhost:8000/api/llm/chat",
    json={
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
)
print(response.json())
```

### curl

```bash
# Verify action
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{"text": "consume 3 from 2", "facts": {"inventory": 2}}'

# Get LLM settings
curl http://localhost:8000/api/llm/settings

# Set provider to Claude
curl -X POST http://localhost:8000/api/llm/provider \
  -H "Content-Type: application/json" \
  -d '{"provider": "claude"}'

# List Claude models
curl http://localhost:8000/api/llm/models/claude
```

### JavaScript/TypeScript

```typescript
// Verify an action
const verifyAction = async (text: string, facts: Record<string, any>) => {
  const response = await fetch('http://localhost:8000/api/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text, facts }),
  });
  return response.json();
};

// Get LLM settings
const getSettings = async () => {
  const response = await fetch('http://localhost:8000/api/llm/settings');
  return response.json();
};

// Usage
const result = await verifyAction('consume 2 apples', { inventory: 5 });
console.log(result);
```

## Rate Limiting

For production deployments, implement rate limiting using:
- nginx limit_req module
- API gateway (AWS API Gateway, Kong, etc.)
- FastAPI middleware

## Security Recommendations

1. **API Keys**: Store LLM API keys in environment variables or secrets manager
2. **Authentication**: Add JWT or API key authentication
3. **HTTPS**: Always use HTTPS in production
4. **CORS**: Restrict CORS origins to known frontend domains
5. **Rate Limiting**: Implement rate limiting to prevent abuse
6. **Logging**: Enable comprehensive logging for audit trails
7. **Monitoring**: Set up Prometheus + Grafana for monitoring

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
