# Security & Safety Layer

<cite>
**Referenced Files in This Document**
- [security.py](file://veritas-ai/core/security.py)
- [firewall.py](file://veritas-ai/core/firewall.py)
- [validation_engine.py](file://veritas-ai/core/validation_engine.py)
- [alert_engine.py](file://veritas-ai/core/alert_engine.py)
- [predictive_engine.py](file://veritas-ai/core/predictive_engine.py)
- [schemas.py](file://veritas-ai/models/schemas.py)
- [router.py](file://veritas-ai/core/router.py)
- [settings.py](file://veritas-ai/config/settings.py)
- [history_store.py](file://veritas-ai/core/history_store.py)
- [cache_layer.py](file://veritas-ai/core/cache_layer.py)
- [redis_cache.py](file://veritas-ai/core/redis_cache.py)
- [explainability_layer.py](file://veritas-ai/core/explainability_layer.py)
- [observability.py](file://veritas-ai/core/observability.py)
- [main.py](file://veritas-ai/app/main.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document describes the multi-layered security and safety layer of Veritas AI. It covers the hallucination firewall, content validation engines, threat detection mechanisms, security boundary enforcement, input sanitization, output filtering, alerting, trust scoring, anomaly detection, and compliance-enforcement patterns. It also outlines threat modeling, attack surface analysis, security audit integration, incident response procedures, security metrics collection, and regulatory compliance features.

## Project Structure
The security and safety layer spans several modules:
- Authentication and API key enforcement
- Query routing and caching
- Validation and truth computation
- Hallucination firewall and output filtering
- Alerting and predictive intelligence
- Observability and drift detection
- Persistent history and configuration

```mermaid
graph TB
subgraph "API Boundary"
A["FastAPI App<br/>main.py"]
B["Security Middleware<br/>security.py"]
C["Router & Cache<br/>router.py / cache_layer.py / redis_cache.py"]
end
subgraph "Safety Engines"
D["Validation Engine<br/>validation_engine.py"]
E["Truth Engine (via Explainability)<br/>explainability_layer.py"]
F["Hallucination Firewall<br/>firewall.py"]
G["Alert Engine<br/>alert_engine.py"]
H["Predictive Intelligence<br/>predictive_engine.py"]
end
subgraph "Persistence & Config"
I["History Store<br/>history_store.py"]
J["Settings<br/>settings.py"]
end
A --> B
B --> C
C --> D
D --> E
E --> F
F --> G
F --> H
F --> I
C --> J
```

**Diagram sources**
- [main.py:106-208](file://veritas-ai/app/main.py#L106-L208)
- [security.py:51-129](file://veritas-ai/core/security.py#L51-L129)
- [router.py:83-182](file://veritas-ai/core/router.py#L83-L182)
- [cache_layer.py:10-41](file://veritas-ai/core/cache_layer.py#L10-L41)
- [redis_cache.py:18-232](file://veritas-ai/core/redis_cache.py#L18-L232)
- [validation_engine.py:9-18](file://veritas-ai/core/validation_engine.py#L9-L18)
- [explainability_layer.py:4-52](file://veritas-ai/core/explainability_layer.py#L4-L52)
- [firewall.py:4-47](file://veritas-ai/core/firewall.py#L4-L47)
- [alert_engine.py:20-67](file://veritas-ai/core/alert_engine.py#L20-L67)
- [predictive_engine.py:5-63](file://veritas-ai/core/predictive_engine.py#L5-L63)
- [history_store.py:23-106](file://veritas-ai/core/history_store.py#L23-L106)
- [settings.py:13-83](file://veritas-ai/config/settings.py#L13-L83)

**Section sources**
- [main.py:106-208](file://veritas-ai/app/main.py#L106-L208)
- [settings.py:13-83](file://veritas-ai/config/settings.py#L13-L83)

## Core Components
- API key enforcement and rate limiting
- Query classification and routing
- Response caching (local and Redis-backed)
- Truth and validation scoring
- Hallucination firewall and output filtering
- Alert generation and recent alert storage
- Predictive intelligence for trend detection
- Observability and drift detection
- Persistent query history

**Section sources**
- [security.py:51-129](file://veritas-ai/core/security.py#L51-L129)
- [router.py:83-182](file://veritas-ai/core/router.py#L83-L182)
- [cache_layer.py:10-41](file://veritas-ai/core/cache_layer.py#L10-L41)
- [redis_cache.py:18-232](file://veritas-ai/core/redis_cache.py#L18-L232)
- [validation_engine.py:9-18](file://veritas-ai/core/validation_engine.py#L9-L18)
- [explainability_layer.py:4-52](file://veritas-ai/core/explainability_layer.py#L4-L52)
- [firewall.py:4-47](file://veritas-ai/core/firewall.py#L4-L47)
- [alert_engine.py:20-67](file://veritas-ai/core/alert_engine.py#L20-L67)
- [predictive_engine.py:5-63](file://veritas-ai/core/predictive_engine.py#L5-L63)
- [observability.py:6-75](file://veritas-ai/core/observability.py#L6-L75)
- [history_store.py:23-106](file://veritas-ai/core/history_store.py#L23-L106)

## Architecture Overview
The security and safety layer enforces strict boundaries around inputs and outputs, validates content through multiple engines, and filters unsafe or unreliable outputs before returning them to clients. It integrates alerting and predictive intelligence to monitor anomalies and misinformation trends, while observability captures drift and performance metrics.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI App<br/>main.py"
participant Sec as "Security<br/>security.py"
participant R as "Router<br/>router.py"
participant Cache as "Cache<br/>cache_layer.py / redis_cache.py"
participant V as "Validation<br/>validation_engine.py"
participant T as "Truth/Explain<br/>explainability_layer.py"
participant F as "Firewall<br/>firewall.py"
participant A as "Alerts<br/>alert_engine.py"
participant P as "Predictive<br/>predictive_engine.py"
participant H as "History<br/>history_store.py"
Client->>API : "Query"
API->>Sec : "Validate API key + rate limit"
Sec-->>API : "Authorized or 401/429"
API->>R : "Route query"
R->>Cache : "Lookup cached response"
alt "Cache miss"
R-->>API : "Decision : fast/full pipeline"
API->>V : "Validate claim"
V->>T : "Compute truth/bias/agreement"
T-->>V : "Scores and breakdown"
V-->>API : "Validation result"
API->>F : "Apply hallucination firewall"
F-->>API : "Filtered response"
API->>A : "Evaluate alerts"
A-->>API : "Alerts list"
API->>P : "Ingest payload for trends"
P-->>API : "Predictive alerts"
API->>H : "Log history"
H-->>API : "OK"
else "Cache hit"
Cache-->>API : "Cached response"
end
API-->>Client : "Response"
```

**Diagram sources**
- [main.py:106-208](file://veritas-ai/app/main.py#L106-L208)
- [security.py:51-129](file://veritas-ai/core/security.py#L51-L129)
- [router.py:83-182](file://veritas-ai/core/router.py#L83-L182)
- [cache_layer.py:10-41](file://veritas-ai/core/cache_layer.py#L10-L41)
- [redis_cache.py:18-232](file://veritas-ai/core/redis_cache.py#L18-L232)
- [validation_engine.py:9-18](file://veritas-ai/core/validation_engine.py#L9-L18)
- [explainability_layer.py:4-52](file://veritas-ai/core/explainability_layer.py#L4-L52)
- [firewall.py:4-47](file://veritas-ai/core/firewall.py#L4-L47)
- [alert_engine.py:20-67](file://veritas-ai/core/alert_engine.py#L20-L67)
- [predictive_engine.py:5-63](file://veritas-ai/core/predictive_engine.py#L5-L63)
- [history_store.py:46-63](file://veritas-ai/core/history_store.py#L46-L63)

## Detailed Component Analysis

### API Key Enforcement and Rate Limiting
- Enforces API key presence and validity via a header.
- Provides a fixed-window rate limiter per key tier (free vs enterprise).
- Generates ephemeral keys when none are configured (development mode).
- Logs unauthorized attempts and invalid keys.

```mermaid
flowchart TD
Start(["Incoming Request"]) --> CheckKey["Check X-API-KEY header"]
CheckKey --> HasKey{"Key present?"}
HasKey --> |No| Unauthorized["401 Unauthorized"]
HasKey --> |Yes| Lookup["Lookup client in in-memory DB"]
Lookup --> Found{"Client found?"}
Found --> |No| InvalidKey["401 Invalid key"]
Found --> |Yes| ResetCheck["Reset window if expired"]
ResetCheck --> LimitCheck{"Requests < limit?"}
LimitCheck --> |No| TooMany["429 Too Many Requests"]
LimitCheck --> |Yes| Allow["Proceed to endpoint"]
```

**Diagram sources**
- [security.py:51-84](file://veritas-ai/core/security.py#L51-L84)

**Section sources**
- [security.py:51-129](file://veritas-ai/core/security.py#L51-L129)

### Query Routing and Caching
- Classifies queries as simple/factual/complex using regex heuristics and trigger words.
- Implements a two-tier cache: local TTL cache and Redis-backed cache.
- Routes to fast-path or full multi-agent pipeline based on classification.
- Logs routing metrics and persists cache entries asynchronously.

```mermaid
flowchart TD
Q["User Query"] --> Class["Classify Query"]
Class --> Simple{"Simple?"}
Simple --> |Yes| Fast["Fast Path Pipeline"]
Simple --> |No| Full["Full Multi-Agent Pipeline"]
Class --> Fact{"Factual/Complex"}
Fact --> Route["Route Decision"]
Route --> CacheHit{"Cache Hit?"}
CacheHit --> |Yes| Return["Return Cached Response"]
CacheHit --> |No| Execute["Execute Pipeline"]
Execute --> Store["Store in Redis (background)"]
Fast --> Store
Return --> End(["Response"])
Store --> End
```

**Diagram sources**
- [router.py:51-182](file://veritas-ai/core/router.py#L51-L182)
- [cache_layer.py:10-41](file://veritas-ai/core/cache_layer.py#L10-L41)
- [redis_cache.py:18-232](file://veritas-ai/core/redis_cache.py#L18-L232)

**Section sources**
- [router.py:83-182](file://veritas-ai/core/router.py#L83-L182)
- [cache_layer.py:10-41](file://veritas-ai/core/cache_layer.py#L10-L41)
- [redis_cache.py:18-232](file://veritas-ai/core/redis_cache.py#L18-L232)

### Validation and Trust Scoring
- Validates claims using a thread-pool executor to avoid blocking the event loop.
- Delegates truth computation to the TruthEngine via the ExplainabilityLayer.
- Produces structured explanations and confidence breakdowns.

```mermaid
sequenceDiagram
participant API as "API"
participant VE as "Validation Engine"
participant TE as "Truth Engine"
API->>VE : "validate_claim(data)"
VE->>TE : "compute_truth_score(data)"
TE-->>VE : "scores and breakdown"
VE-->>API : "validated result"
```

**Diagram sources**
- [validation_engine.py:9-18](file://veritas-ai/core/validation_engine.py#L9-L18)
- [explainability_layer.py:10-52](file://veritas-ai/core/explainability_layer.py#L10-L52)

**Section sources**
- [validation_engine.py:9-18](file://veritas-ai/core/validation_engine.py#L9-L18)
- [explainability_layer.py:4-52](file://veritas-ai/core/explainability_layer.py#L4-L52)

### Hallucination Firewall and Output Filtering
- Applies deterministic rules to filter or downgrade unsafe/unverified outputs.
- Overrides status based on contradiction counts, trusted source thresholds, and truth scores.
- Logs firewall overrides for auditability.

```mermaid
flowchart TD
In["QueryResponse"] --> Count["Count trusted sources"]
In --> Contra["Count contradictions"]
In --> Truth["Read truth_score"]
Count --> Trusted{"trusted_count < 2?"}
Contra --> Spike{"contradictions > threshold?"}
Truth --> Verify{"truth_score > 0.75?"}
Trusted --> |Yes| Spike --> Verify --> Out["Set status accordingly"]
Trusted --> |No| Override1["Status = uncertain"]
Spike --> |Yes| Override2["Status = likely_false"]
Verify --> |Yes| Override3["Status = verified"]
Verify --> |No| Baseline["Status = uncertain"]
```

**Diagram sources**
- [firewall.py:13-47](file://veritas-ai/core/firewall.py#L13-L47)

**Section sources**
- [firewall.py:4-47](file://veritas-ai/core/firewall.py#L4-L47)
- [schemas.py:14-26](file://veritas-ai/models/schemas.py#L14-L26)

### Alert Engine and Recent Alerts
- Detects anomalies and suspicious patterns in structured responses.
- Emits alerts with severity and timestamps.
- Maintains a bounded deque of recent alerts for inspection.

```mermaid
flowchart TD
Resp["QueryResponse"] --> Check1["Contradictions >= 2?"]
Resp --> Check2["fake_probability > 0.7?"]
Resp --> Check3["truth_score < 0.4?"]
Resp --> Check4["Summary contains 'breaking/urgent/alert'?"]
Check1 --> |Yes| Emit1["Add high severity alert"]
Check2 --> |Yes| Emit2["Add high severity alert"]
Check3 --> |Yes| Emit3["Add medium severity alert"]
Check4 --> |Yes| Emit4["Add low severity alert"]
Emit1 --> Store["Append to recent alerts"]
Emit2 --> Store
Emit3 --> Store
Emit4 --> Store
```

**Diagram sources**
- [alert_engine.py:26-67](file://veritas-ai/core/alert_engine.py#L26-L67)

**Section sources**
- [alert_engine.py:20-67](file://veritas-ai/core/alert_engine.py#L20-L67)

### Predictive Intelligence Engine
- Tracks keyword-topic spikes over a sliding window to detect emerging misinformation trends.
- Emits predictive alerts with risk levels and narratives.

```mermaid
flowchart TD
Ingest["Ingest raw query"] --> Tokenize["Tokenize + filter"]
Tokenize --> Streams["Append to payload streams"]
Streams --> Flush["Flush old telemetry"]
Flush --> Count["Count topic frequencies"]
Count --> High{"Count >= 15?"}
Count --> Medium{"Count >= 5?"}
High --> |Yes| AlertHigh["Emit high-risk alert"]
Medium --> |Yes| AlertMed["Emit medium-risk alert"]
High --> |No| Done["Done"]
Medium --> |No| Done
```

**Diagram sources**
- [predictive_engine.py:14-63](file://veritas-ai/core/predictive_engine.py#L14-L63)

**Section sources**
- [predictive_engine.py:5-63](file://veritas-ai/core/predictive_engine.py#L5-L63)

### Observability and Drift Detection
- Logs inference metrics and truth computations to JSONL files.
- Computes moving average drift for truth scores and emits drift logs when thresholds are exceeded.

```mermaid
flowchart TD
Log["Log truth score + breakdown"] --> Append["Append to metrics file"]
Append --> Window{"History >= window?"}
Window --> |Yes| Avg["Compute moving average"]
Avg --> Dev["Compute deviation"]
Dev --> Drift{"Deviation > threshold?"}
Drift --> |Yes| DriftLog["Write drift alert to drift file"]
Drift --> |No| End["End"]
Window --> |No| End
```

**Diagram sources**
- [observability.py:45-72](file://veritas-ai/core/observability.py#L45-L72)

**Section sources**
- [observability.py:6-75](file://veritas-ai/core/observability.py#L6-L75)

### Persistent History Store
- Initializes a SQLite database for query history.
- Inserts query results with metadata and supports retrieval by owner or public.

```mermaid
flowchart TD
Insert["log_query_result(payload)"] --> Open["Open DB connection"]
Open --> Exec["INSERT INTO query_history ..."]
Exec --> Commit["Commit transaction"]
Commit --> Close["Close connection"]
Select["fetch_recent_history(limit, owner)"] --> Open2["Open DB connection"]
Open2 --> Query["SELECT ... ORDER BY id DESC LIMIT ?"]
Query --> Rows["Map to HistoryEntry list"]
Rows --> Close2["Close connection"]
```

**Diagram sources**
- [history_store.py:46-102](file://veritas-ai/core/history_store.py#L46-L102)

**Section sources**
- [history_store.py:23-106](file://veritas-ai/core/history_store.py#L23-L106)

## Dependency Analysis
- The API layer depends on security enforcement and router for policy enforcement.
- Router coordinates cache and pipeline selection.
- Validation and truth engines feed the hallucination firewall and explainability layer.
- Firewall feeds alerts and history persistence.
- Predictive engine consumes raw queries independently.
- Observability writes to logs and monitors drift.

```mermaid
graph LR
Sec["security.py"] --> API["main.py"]
API --> R["router.py"]
R --> CL["cache_layer.py"]
R --> RC["redis_cache.py"]
API --> VE["validation_engine.py"]
VE --> EX["explainability_layer.py"]
EX --> FW["firewall.py"]
FW --> AE["alert_engine.py"]
FW --> HS["history_store.py"]
API --> PR["predictive_engine.py"]
FW --> OBS["observability.py"]
```

**Diagram sources**
- [main.py:106-208](file://veritas-ai/app/main.py#L106-L208)
- [security.py:51-129](file://veritas-ai/core/security.py#L51-L129)
- [router.py:83-182](file://veritas-ai/core/router.py#L83-L182)
- [cache_layer.py:10-41](file://veritas-ai/core/cache_layer.py#L10-L41)
- [redis_cache.py:18-232](file://veritas-ai/core/redis_cache.py#L18-L232)
- [validation_engine.py:9-18](file://veritas-ai/core/validation_engine.py#L9-L18)
- [explainability_layer.py:4-52](file://veritas-ai/core/explainability_layer.py#L4-L52)
- [firewall.py:4-47](file://veritas-ai/core/firewall.py#L4-L47)
- [alert_engine.py:20-67](file://veritas-ai/core/alert_engine.py#L20-L67)
- [history_store.py:46-102](file://veritas-ai/core/history_store.py#L46-L102)
- [predictive_engine.py:5-63](file://veritas-ai/core/predictive_engine.py#L5-L63)
- [observability.py:6-75](file://veritas-ai/core/observability.py#L6-L75)

**Section sources**
- [schemas.py:14-26](file://veritas-ai/models/schemas.py#L14-L26)

## Performance Considerations
- Asynchronous Redis cache with graceful fallback to local cache reduces latency and improves resilience.
- Thread-pool execution for truth scoring prevents blocking the event loop.
- Fixed-window rate limiting and sliding-window predictive analytics bound resource usage.
- Local TTL cache complements Redis for hot-path responses.
- Streaming and chunked responses are configurable for throughput tuning.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- API key errors: Verify X-API-KEY header and tier limits; check warning logs for invalid attempts.
- Rate limit exceeded: Confirm tier-specific limits and reset windows.
- Cache connectivity: Redis failures fall back to local cache; inspect logs for warnings.
- Timeout handling: Global middleware returns 504 on exceeding pipeline timeouts.
- Drift detection: Review drift logs for truth score deviations.
- Alerts: Retrieve recent alerts via the alert engine’s recent list.

**Section sources**
- [security.py:87-129](file://veritas-ai/core/security.py#L87-L129)
- [redis_cache.py:30-56](file://veritas-ai/core/redis_cache.py#L30-L56)
- [main.py:127-151](file://veritas-ai/app/main.py#L127-L151)
- [observability.py:55-72](file://veritas-ai/core/observability.py#L55-L72)
- [alert_engine.py:17-18](file://veritas-ai/core/alert_engine.py#L17-L18)

## Conclusion
Veritas AI’s security and safety layer combines strong API boundary enforcement, intelligent query routing, robust caching, multi-stage validation, deterministic output filtering, proactive alerting, predictive trend detection, and observability-driven drift monitoring. Together, these components form a resilient, auditable, and scalable defense against hallucinations, misinformation, and anomalous behavior.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Threat Modeling and Attack Surface
- Injection vectors: Unsanitized queries routed to external APIs; mitigated by router classification and firewall filtering.
- API abuse: Brute force, rate limit bypass attempts; mitigated by API key enforcement and fixed-window rate limiting.
- Misinformation amplification: Propaganda or fake content; mitigated by fake probability checks, contradiction detection, and predictive trend alerts.
- Denial of service: High-volume queries; mitigated by caching, timeouts, and rate limiting.
- Data exposure: Unauthorized access; mitigated by API key enforcement and CORS configuration.

[No sources needed since this section provides general guidance]

### Compliance and Audit Integration
- Persistent history store enables audit trails for queries and outcomes.
- Observability logs capture drift and performance metrics for continuous monitoring.
- Alert engine records suspicious activity with timestamps and severity for incident review.
- Configuration-driven settings support environment-specific controls (CORS, timeouts, limits).

**Section sources**
- [history_store.py:23-106](file://veritas-ai/core/history_store.py#L23-L106)
- [observability.py:25-72](file://veritas-ai/core/observability.py#L25-L72)
- [alert_engine.py:12-18](file://veritas-ai/core/alert_engine.py#L12-L18)
- [settings.py:69-83](file://veritas-ai/config/settings.py#L69-L83)

### Incident Response Procedures
- Immediate: Inspect recent alerts and drift logs; confirm firewall overrides.
- Forensics: Review history store entries and observability metrics.
- Mitigation: Temporarily adjust thresholds, pause predictive ingestion, or scale caches.
- Recovery: Restore cache connectivity, reinitialize databases, and resume monitoring.

[No sources needed since this section provides general guidance]

### Security Metrics Collection
- Latency, token usage, and confidence scores recorded via observability layer.
- Routing metrics (cache hit, fast path, full pipeline) maintained by router.
- Redis statistics exposed via cache layer for operational insights.

**Section sources**
- [observability.py:33-44](file://veritas-ai/core/observability.py#L33-L44)
- [router.py:138-149](file://veritas-ai/core/router.py#L138-L149)
- [redis_cache.py:146-163](file://veritas-ai/core/redis_cache.py#L146-L163)