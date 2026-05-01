# Friday Architecture & Workflow

This document outlines the structural components and logical flow of the Friday AI platform.

## Structural Overview

Friday is built on a modular architecture that separates interface concerns from core intelligence and data retrieval.

### 1. The Interaction Layer
- **CLI / Voice Interface:** Handles raw input (text or audio).
- **FridayPipeline:** The central orchestrator that manages the lifecycle of a request.
- **WebSocket Gateway:** Enables real-time streaming of text and audio to frontends.

### 2. Core Pipeline (FridayPipeline)
The pipeline is designed for "Tiered Execution" to balance speed and accuracy:

| Tier | Name | Engine | Purpose |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Fast** | `phi3:mini` | Instant responses, system commands (e.g., "open terminal"). |
| **Tier 2** | **Standard** | `llama3.1:8b` | RAG-based informational queries using Vector DB. |
| **Tier 3** | **Deep** | `llama3.1:8b` + Reasoning | Complex analysis, fact-checking, and cross-referencing. |

### 3. Memory & Context System
- **Conversation History:** Tracks the last 50 exchanges to maintain continuity.
- **Context Summary:** Periodically generates summaries of ongoing topics.
- **Predictive Suggestions:** Proactively suggests actions based on the detected context (e.g., suggesting a flight check if "travel" is mentioned).
- **User Preferences:** Learns and persists user-specific patterns and settings.

### 4. Data Retrieval & Verification
- **Vector Client (Chroma):** Handles semantic search across indexed documents.
- **Graph Client (Neo4j):** Manages relational data and complex entity mapping.
- **Truth Engine:** Computes a "Truth Score" based on vector similarity, graph connectivity, and source reliability.
- **Hallucination Firewall:** Validates LLM outputs against retrieved context before final delivery.

## Operational Workflow

The following steps occur for every user interaction:

1. **Input Classification:** 
   The `SemanticRouter` uses a MiniLM encoder to classify the query. Keyword boosting is used as a fallback to ensure critical commands are never missed.
   
2. **Tier Selection:**
   - **Fast Path:** If the query is a simple command, it bypasses heavy retrieval and executes via MCP (Model Context Protocol) tools or a small LLM.
   - **RAG Path:** For informational queries, relevant chunks are pulled from the Vector DB.
   - **Deep Path:** For complex queries, both Vector and Graph DBs are queried in parallel. Results are blended using Reciprocal Rank Fusion (RRF).

3. **Reasoning & Synthesis:**
   The selected agent generates a response. In Tier 3, a dedicated "Reasoning Agent" performs multiple passes to ensure depth.

4. **Verification (Tier 3 Only):**
   If the Truth Score is low, a "Verification Agent" is invoked to correct the draft against the raw retrieved context.

5. **Post-Processing:**
   - **Emotion Detection:** The personality module adjusts the tone.
   - **TTS Synthesis:** If in voice mode, the text is streamed to the speech engine.
   - **Memory Update:** The exchange is recorded in the persistent memory store.

---
*Document Version: 1.0.0 (Production Release)*
