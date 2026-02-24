# Infrastructure Chat Feature — Research Report

## 1. LLM Provider Comparison

| Provider | Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Tool Calling Maturity | Latency |
|---|---|---|---|---|---|
| **Google Gemini 2.5 Flash** | gemini-2.5-flash | **$0.30** | $2.50 | Good (improving) | ~263 tok/s |
| Google Gemini 2.5 Pro | gemini-2.5-pro | $1.25 | $10.00 | Good | Higher (Deep Think) |
| Google Gemini 3 Flash | gemini-3-flash | $0.50 | $3.00 | Newest | Sub-200ms p95 |
| **OpenAI GPT-4o mini** | gpt-4o-mini | **$0.15** | $0.60 | Most mature | Fast |
| OpenAI GPT-4o | gpt-4o | $2.50 | $10.00 | Most mature | Moderate |
| Anthropic Claude 3.5 Sonnet | claude-3.5-sonnet | $3.00 | $15.00 | Good | Moderate |

### Recommendation for Prescale

**Primary: Gemini 2.5 Flash** — Prescale is already a GCP-native platform, so Gemini keeps the ecosystem consistent. At $0.30/1M input tokens, it's extremely cost-effective for a monitoring tool that makes many small tool-call queries.

**Fallback consideration: GPT-4o mini** — Cheapest option overall and has the most mature tool-calling. Worth supporting as an alternative if users prefer OpenAI.

> **Key Insight**: For Prescale's use case (short queries + tool calls + short answers), each chat turn will use roughly **500–2,000 tokens**. At ~1,000 tokens/turn with Gemini Flash, that's **$0.0003 per question** — effectively free for individual developers.

---

## 2. Architecture Patterns

### Option A: Raw Google Gemini SDK (Recommended for Prescale)

```
User → FastAPI endpoint → Gemini SDK (with tool defs) → Tool execution → Response
```

**Pros**: Simplest, no extra dependencies, full control, lowest latency
**Cons**: Must handle conversation state and tool-call loops manually
**Best for**: Prescale — our use case is straightforward (single-agent, ~7 tools, no multi-agent coordination)

### Option B: LangChain

**Pros**: Quick prototyping, many integrations, familiar ecosystem
**Cons**: Opaque control flow, debugging is harder, overkill for our tool count
**Best for**: RAG-heavy applications, rapid prototyping

### Option C: LangGraph

**Pros**: Graph-based state machine, production-grade, human-in-the-loop, multi-agent support
**Cons**: Steeper learning curve, heavier dependency, unnecessary complexity for <10 tools
**Best for**: Complex multi-agent systems, applications requiring branching workflows

### Verdict for Prescale

**Use raw Gemini SDK (`google-genai`).** Our chat feature is a single agent with ~7 well-defined tools querying internal Prescale data. LangGraph's state machine and multi-agent coordination are overkill. We can always migrate later if complexity grows.

The tool-call loop is simple:
1. Send user message + tool definitions to Gemini
2. If Gemini returns a tool call → execute it against Prescale internals → send result back
3. Repeat until Gemini returns a text response
4. Stream the final text to the frontend via SSE

---

## 3. Competitor Analysis

### Datadog — Bits AI (Market Leader)

- Acts as an **autonomous SRE agent** that can investigate outages, suggest code changes, and execute remediation playbooks
- Users can trigger safe, audited **actions from chat** (restart services, flush caches, quarantine accounts)
- All actions are validated against **role-based policies** and logged for accountability
- GA since Dec 2025, 1,000+ customers using AI products
- **Takeaway for Prescale**: The "action" layer (executing changes from chat) is the next frontier. We should start with **read-only** queries and consider actions later.

### New Relic — AI / Grok

- Conversational interface for natural language queries across telemetry data
- Root cause hypothesis generation and impact surface mapping
- **Predictive analytics** (forecast anomalies from chat) — directly relevant to Prescale
- **Agentic integrations** with external tools (ServiceNow, etc.)
- **Takeaway for Prescale**: Their approach of surfacing predictions and forecasts through chat is exactly what we should do. Our ML models give us a differentiator here.

### Positioning for Prescale

| Feature | Datadog Bits AI | New Relic Grok | Prescale Chat (Proposed) |
|---|---|---|---|
| Natural language queries | ✅ | ✅ | ✅ |
| Anomaly explanation | ✅ | ✅ | ✅ |
| **Predictive forecasting from chat** | ❌ | ✅ (limited) | **✅ (core strength)** |
| Execute remediation actions | ✅ | ❌ | ❌ (v1, future) |
| Multi-cloud support | ✅ | ✅ | ✅ (6+ sources) |
| Self-hosted / Open-source | ❌ | ❌ | **✅** |
| Cost | $$$$ | $$$ | **Free (self-hosted)** |

**Prescale's edge**: Open-source + built-in ML predictions. No other open-source observability tool has an LLM chat grounded in its own forecasting models.

---

## 4. UX Research — What SREs Actually Ask

Research shows SRE questions fall into **5 categories**:

### Category 1: Incident Investigation (Most Common)
> "What caused the latency spike in the auth service?"
> "Show me error logs from the last 30 minutes"
> "Correlate recent deployments with CPU spikes"

**Prescale tools needed**: `get_metric_data`, `get_latest_anomalies`

### Category 2: Health & Performance Monitoring
> "What's the current health of my cluster?"
> "Show P99 latency for the search service"
> "Are any services exceeding their error budget?"

**Prescale tools needed**: `get_metric_latest`, `get_agent_status`, `get_metric_names`

### Category 3: Capacity Planning & Prediction
> "Will my database handle next month's traffic?"
> "When will disk usage hit 90%?"
> "What scaling do you recommend?"

**Prescale tools needed**: `get_predictions`, `get_recommendations` — **this is our strongest category**

### Category 4: Alert Management
> "What are the top alerts from the last 12 hours?"
> "Summarize incidents while I was off-call"

**Prescale tools needed**: `get_latest_anomalies` (with time filters)

### Category 5: System Understanding
> "Explain the data flow between service A and B"
> "What monitoring is configured for the dashboard?"

**Prescale tools needed**: `get_deployments`, `get_agent_status`, `get_metric_names`

### Suggested Starter Prompts for Prescale Chat

```
"Any anomalies right now?"
"How's CPU looking across my agents?"
"Predict memory usage for the next 6 hours"
"What scaling changes do you recommend?"
"Which agents are offline?"
"Summarize the health of my infrastructure"
```

---

## 5. Cost & Feasibility Analysis

### Token Usage Estimates

| Interaction Type | Input Tokens | Output Tokens | Cost (Gemini 2.5 Flash) |
|---|---|---|---|
| Simple query ("any anomalies?") | ~800 | ~200 | $0.0007 |
| Tool-call query (1 tool) | ~1,500 | ~500 | $0.002 |
| Complex query (3 tools) | ~3,000 | ~800 | $0.003 |
| Heavy session (20 questions) | ~30,000 | ~8,000 | $0.03 |

**Monthly cost estimates** (per user):
- Light use (5 questions/day): **~$0.50/month**
- Medium use (20 questions/day): **~$2.00/month**
- Heavy use (50 questions/day): **~$5.00/month**

### Latency Expectations

- **Gemini 2.5 Flash**: ~263 tokens/sec → a 200-token answer streams in <1 second
- **With 1 tool call**: Add ~200ms for internal Prescale query → total ~1.5s
- **With 3 tool calls**: Add ~600ms → total ~2.5s
- **SSE streaming**: User sees first tokens within ~500ms, creating a responsive feel

### Implementation Effort

| Component | Estimated Effort | Complexity |
|---|---|---|
| `chat.py` backend module | 2–3 hours | Medium (tool-call loop, SSE streaming) |
| Chat API endpoints in `app.py` | 30 min | Low |
| `InfraChat.vue` frontend | 2–3 hours | Medium (streaming UI, markdown rendering) |
| Router + sidebar updates | 15 min | Low |
| Testing & polish | 1–2 hours | Low |
| **Total** | **~6–8 hours** | — |

### Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| LLM hallucination (wrong metric values) | Medium | Ground all answers in real tool-call data; never let LLM guess values |
| API key exposure | Low | Server-side only; key never reaches frontend |
| Cost runaway | Low | Rate limiting on `/api/chat` endpoint |
| Gemini API downtime | Low | Feature is optional; rest of Prescale works without it |
| Slow responses on complex queries | Medium | Stream tokens via SSE; show "thinking" indicator |
